"""Shot-type router — dispatches each shot through the correct pipeline path."""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.adapters import mock as adapters
from app.loader import LoadedSku
from app.models import STATUS_LABELS, JobRecord, JobStatus, ShotRecord, ShotStatus
from app.pipeline import compose, hero, lint

logger = logging.getLogger(__name__)


async def run_shot(
    *,
    job: JobRecord,
    shot_rec: ShotRecord,
    shot_cfg: dict[str, Any],
    sku: LoadedSku,
    ruleset: dict[str, Any],
    mock_mode: bool,
    output_root: Path,
    on_update: Callable[[], None],
) -> None:
    shot_dir = output_root / sku.sku / ("_MOCK" if mock_mode else "run") / job.job_id / shot_rec.shot_id
    shot_dir.mkdir(parents=True, exist_ok=True)

    stype = shot_cfg["type"]
    try:
        if stype == "hero_passthrough":
            await _hero(shot_rec, sku, shot_dir, on_update)
        elif stype == "graphic_only":
            await _graphic_only(shot_rec, shot_cfg, sku, ruleset, mock_mode, shot_dir, on_update)
        elif stype == "graphic_only_with_generated_tiles":
            await _graphic_tiles(shot_rec, shot_cfg, sku, ruleset, mock_mode, shot_dir, on_update)
        elif stype == "photo_overlay":
            await _photo_overlay(shot_rec, shot_cfg, sku, ruleset, mock_mode, shot_dir, on_update)
        elif stype == "photo_only":
            await _photo_only(shot_rec, shot_cfg, sku, mock_mode, shot_dir, on_update)
        elif stype == "asset_passthrough":
            _set_status(shot_rec, ShotStatus.needs_review, on_update)
            shot_rec.flags.append("asset_passthrough disabled / not implemented in Stage 0")
        else:
            raise ValueError(f"Unknown shot type: {stype}")
    except Exception as exc:
        logger.exception("Shot %s failed", shot_rec.shot_id)
        shot_rec.error = str(exc)
        _set_status(shot_rec, ShotStatus.failed, on_update)


def _set_status(shot: ShotRecord, status: ShotStatus, on_update: Callable[[], None]) -> None:
    shot.status = status
    shot.status_label = STATUS_LABELS[status]
    on_update()


def _scene_references(sku: LoadedSku, cfg: dict[str, Any]) -> list[Path]:
    """The product references this shot declared, hero first.

    scene_prompt.input_images is the documented contract for which angles each
    shot gets; previously only the hero was ever sent.
    """
    paths = [Path(p) for p in cfg.get("_scene_reference_abs") or []]
    existing = [p for p in paths if p.exists()]
    if not existing:
        return [sku.hero_abs]
    return existing


def _record_provider(shot: ShotRecord, result: Any) -> None:
    """Stamp the shot with the model that actually generated it."""
    shot.scene_provider = result.provider
    shot.scene_model = result.model
    shot.scene_reference_count = result.reference_count
    for note in result.notes:
        if note not in shot.scene_notes:
            shot.scene_notes.append(note)
    if result.provider == "gemini":
        shot.flags.append("generated_by_fallback_provider")


async def _hero(
    shot: ShotRecord,
    sku: LoadedSku,
    shot_dir: Path,
    on_update: Callable[[], None],
) -> None:
    _set_status(shot, ShotStatus.scaling, on_update)
    out = shot_dir / "RT_MAIN_WHITE.png"
    meta = hero.hero_passthrough(sku.hero_abs, out, png_fallback=sku.png_fallback_abs)
    shot.artifacts["RT_MAIN_WHITE"] = str(out)
    shot.artifacts["meta"] = json.dumps(meta)
    _thumb(shot, out)
    _set_status(shot, ShotStatus.done, on_update)


async def _graphic_only(
    shot: ShotRecord,
    cfg: dict[str, Any],
    sku: LoadedSku,
    ruleset: dict[str, Any],
    mock_mode: bool,
    shot_dir: Path,
    on_update: Callable[[], None],
) -> None:
    _set_status(shot, ShotStatus.designing_overlay, on_update)
    html = await adapters.design_overlay(
        mock_mode=mock_mode, shot=cfg, photo_path=None, brand_ruleset=ruleset
    )
    (shot_dir / "overlay.html").write_text(html, encoding="utf-8")
    shot.artifacts["overlay.html"] = str(shot_dir / "overlay.html")

    lint_results = lint.lint_overlay_markup(html, cfg, ruleset)
    shot.lint_results = lint_results
    if any(r.get("status") == "FAIL" for r in lint_results):
        shot.flags.append("lint_failed")
        _set_status(shot, ShotStatus.needs_review, on_update)
        return

    _set_status(shot, ShotStatus.rendering, on_update)
    accent = "#FF8200" if ruleset.get("ruleset_id") == "coastwide" else "#E42A11"
    text = "#414140" if ruleset.get("ruleset_id") == "coastwide" else "#262020"
    overlay_png = shot_dir / "overlay.png"
    await compose.rasterize_overlay_html(html, overlay_png, accent=accent, text_color=text)
    # Prefer acceptance reference as the finished graphic in mock mode when present.
    ref = cfg.get("_acceptance_reference_abs")
    finished = shot_dir / "composite.png"
    if mock_mode and ref and Path(ref).exists():
        scene = await adapters.generate_scene(
            mock_mode=True,
            prompt="",
            input_image_paths=[],
            aspect_ratio="1:1",
            acceptance_reference=Path(ref),
            out_path=finished,
        )
        img_path = scene.path
    else:
        compose.flatten_graphic(overlay_png, finished)
        img_path = finished

    shot.artifacts["overlay.png"] = str(overlay_png)
    shot.artifacts["composite.png"] = str(img_path)

    _set_status(shot, ShotStatus.scaling, on_update)
    secondary = shot_dir / "RT_SECONDARY_SQUARE.png"
    compose.scale_square(Path(img_path), secondary, 2000)
    shot.artifacts["RT_SECONDARY_SQUARE"] = str(secondary)
    _thumb(shot, secondary)
    _set_status(shot, ShotStatus.done, on_update)


async def _graphic_tiles(
    shot: ShotRecord,
    cfg: dict[str, Any],
    sku: LoadedSku,
    ruleset: dict[str, Any],
    mock_mode: bool,
    shot_dir: Path,
    on_update: Callable[[], None],
) -> None:
    _set_status(shot, ShotStatus.generating_scene, on_update)
    tiles = shot_dir / "raw_attempt_1.png"
    ref = cfg.get("_acceptance_reference_abs")
    scene = await adapters.generate_scene(
        mock_mode=mock_mode,
        prompt=(cfg.get("scene_prompt") or {}).get("template", ""),
        input_image_paths=_scene_references(sku, cfg),
        aspect_ratio=(cfg.get("scene_prompt") or {}).get("aspect_ratio", "3:2"),
        acceptance_reference=Path(ref) if ref else None,
        out_path=tiles,
    )
    _record_provider(shot, scene)
    shot.artifacts["raw_attempt_1.png"] = str(tiles)
    shot.attempts = 1
    await _graphic_only(shot, cfg, sku, ruleset, mock_mode, shot_dir, on_update)


async def _photo_overlay(
    shot: ShotRecord,
    cfg: dict[str, Any],
    sku: LoadedSku,
    ruleset: dict[str, Any],
    mock_mode: bool,
    shot_dir: Path,
    on_update: Callable[[], None],
) -> None:
    _set_status(shot, ShotStatus.generating_scene, on_update)
    raw = shot_dir / "raw_attempt_1.png"
    ref = cfg.get("_acceptance_reference_abs")
    scene = await adapters.generate_scene(
        mock_mode=mock_mode,
        prompt=(cfg.get("scene_prompt") or {}).get("template", ""),
        input_image_paths=_scene_references(sku, cfg),
        aspect_ratio=(cfg.get("scene_prompt") or {}).get("aspect_ratio", "1:1"),
        acceptance_reference=Path(ref) if ref else None,
        out_path=raw,
    )
    _record_provider(shot, scene)
    shot.artifacts["raw_attempt_1.png"] = str(raw)
    shot.attempts = 1

    _set_status(shot, ShotStatus.checking, on_update)
    gate = cfg.get("fidelity_gate") or {}
    verdict = await adapters.fidelity_gate(
        mock_mode=mock_mode,
        photo_path=raw,
        hero_path=sku.hero_abs,
        check_product_identity=gate.get("check_product_identity", True),
    )
    shot.gate_verdicts.append(verdict)
    if verdict.get("verdict") != "PASS":
        shot.flags.append("fidelity_gate_failed")
        _set_status(shot, ShotStatus.needs_review, on_update)
        return

    _set_status(shot, ShotStatus.designing_overlay, on_update)
    html = await adapters.design_overlay(
        mock_mode=mock_mode, shot=cfg, photo_path=raw, brand_ruleset=ruleset
    )
    (shot_dir / "overlay.html").write_text(html, encoding="utf-8")
    shot.artifacts["overlay.html"] = str(shot_dir / "overlay.html")

    lint_results = lint.lint_overlay_markup(html, cfg, ruleset)
    shot.lint_results = lint_results
    if any(r.get("status") == "FAIL" for r in lint_results):
        shot.flags.append("lint_failed")
        _set_status(shot, ShotStatus.needs_review, on_update)
        return

    _set_status(shot, ShotStatus.rendering, on_update)
    accent = "#FF8200" if ruleset.get("ruleset_id") == "coastwide" else "#E42A11"
    text = "#414140" if ruleset.get("ruleset_id") == "coastwide" else "#262020"
    overlay_png = shot_dir / "overlay.png"
    await compose.rasterize_overlay_html(html, overlay_png, accent=accent, text_color=text)
    shot.artifacts["overlay.png"] = str(overlay_png)

    # In mock mode the acceptance reference already includes text — use it as the
    # finished composite so the demo side-by-side is meaningful, still watermarked.
    _set_status(shot, ShotStatus.compositing, on_update)
    composite = shot_dir / "composite.png"
    if mock_mode and ref and Path(ref).exists():
        await adapters.generate_scene(
            mock_mode=True,
            prompt="",
            input_image_paths=[],
            aspect_ratio="1:1",
            acceptance_reference=Path(ref),
            out_path=composite,
        )
    else:
        compose.composite_overlay(raw, overlay_png, composite)
    shot.artifacts["composite.png"] = str(composite)

    _set_status(shot, ShotStatus.scaling, on_update)
    secondary = shot_dir / "RT_SECONDARY_SQUARE.png"
    compose.scale_square(composite, secondary, 2000)
    shot.artifacts["RT_SECONDARY_SQUARE"] = str(secondary)
    _thumb(shot, secondary)
    _set_status(shot, ShotStatus.done, on_update)


async def _photo_only(
    shot: ShotRecord,
    cfg: dict[str, Any],
    sku: LoadedSku,
    mock_mode: bool,
    shot_dir: Path,
    on_update: Callable[[], None],
) -> None:
    _set_status(shot, ShotStatus.generating_scene, on_update)
    raw = shot_dir / "raw_attempt_1.png"
    ref = cfg.get("_acceptance_reference_abs")
    scene = await adapters.generate_scene(
        mock_mode=mock_mode,
        prompt=(cfg.get("scene_prompt") or {}).get("template", ""),
        input_image_paths=_scene_references(sku, cfg),
        aspect_ratio=(cfg.get("scene_prompt") or {}).get("aspect_ratio", "1:1"),
        acceptance_reference=Path(ref) if ref else None,
        out_path=raw,
    )
    _record_provider(shot, scene)
    shot.artifacts["raw_attempt_1.png"] = str(raw)
    shot.attempts = 1

    _set_status(shot, ShotStatus.checking, on_update)
    verdict = await adapters.fidelity_gate(
        mock_mode=mock_mode, photo_path=raw, hero_path=sku.hero_abs
    )
    shot.gate_verdicts.append(verdict)
    if verdict.get("verdict") != "PASS":
        shot.flags.append("fidelity_gate_failed")
        _set_status(shot, ShotStatus.needs_review, on_update)
        return

    _set_status(shot, ShotStatus.scaling, on_update)
    secondary = shot_dir / "RT_SECONDARY_SQUARE.png"
    compose.scale_square(raw, secondary, 2000)
    shot.artifacts["composite.png"] = str(raw)
    shot.artifacts["RT_SECONDARY_SQUARE"] = str(secondary)
    _thumb(shot, secondary)
    _set_status(shot, ShotStatus.done, on_update)


def _thumb(shot: ShotRecord, path: Path) -> None:
    # URL is filled by the API layer using job/sku/shot/filename routing.
    name = path.name
    shot.thumbnail_url = f"{shot.shot_id}/{name}"


def write_manifest(job: JobRecord, sku: LoadedSku, job_dir: Path) -> Path:
    providers: dict[str, int] = {}
    for s in job.shots:
        if s.scene_provider:
            providers[s.scene_provider] = providers.get(s.scene_provider, 0) + 1
    payload = {
        "job_id": job.job_id,
        "sku": job.sku,
        "display_name": job.display_name,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "mock_mode": job.mock_mode,
        "placeholder_count": job.placeholder_count,
        "counts": job.counts.model_dump(),
        "scene_providers": providers,
        "shots": [s.model_dump() for s in job.shots],
    }
    path = job_dir / "manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_package_readme(job: JobRecord, job_dir: Path) -> Path:
    lines = [
        f"Staples / Coastwide image package — SKU {job.sku}",
        f"Run: {job.job_id}",
        f"Created: {job.created_at.isoformat()}",
        f"Status: {job.status.value}",
        f"Mock mode: {job.mock_mode}",
        f"Shots: {job.counts.total} total, {job.counts.done} done, "
        f"{job.counts.needs_review} needs review, {job.counts.failed} failed",
        "",
        "SCENE GENERATION PROVIDER",
        "=========================",
    ]
    generated = [s for s in job.shots if s.scene_provider]
    if not generated:
        lines.append("(no generated scenes in this package)")
    else:
        for s in generated:
            lines.append(f"- {s.shot_id}: {s.scene_provider} / {s.scene_model} "
                         f"({s.scene_reference_count} product reference(s))")
        fallbacks = [s for s in generated if s.scene_provider == "gemini"]
        if fallbacks:
            lines.append("")
            lines.append(
                f"NOTE: {len(fallbacks)} shot(s) were NOT generated by Higgsfield. Reason:"
            )
            for note in dict.fromkeys(n for s in fallbacks for n in s.scene_notes):
                lines.append(f"  {note}")
    lines.extend(
        [
            "",
            "PLACEHOLDER COPY (POC only — not Staples-approved)",
            "================================================",
        ]
    )
    placeholders = []
    for s in job.shots:
        for p in s.placeholder_strings:
            placeholders.append(f'- [{s.shot_id}] "{p}"')
    if placeholders:
        lines.extend(placeholders)
    else:
        lines.append("(none)")
    lines.extend(
        [
            "",
            "Flagged shots",
            "-------------",
        ]
    )
    flagged = [s for s in job.shots if s.status in (ShotStatus.needs_review, ShotStatus.failed)]
    if not flagged:
        lines.append("(none)")
    else:
        for s in flagged:
            lines.append(f"- {s.shot_id}: {s.status.value} — {'; '.join(s.flags) or s.error}")
    path = job_dir / "README.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def zip_package(job_dir: Path, zip_path: Path, include_intermediates: bool = False) -> Path:
    keep_names = {
        "RT_MAIN_WHITE.png",
        "RT_SECONDARY_SQUARE.png",
        "composite.png",
        "manifest.json",
        "README.txt",
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in job_dir.rglob("*"):
            if not path.is_file():
                continue
            if not include_intermediates and path.name not in keep_names:
                if path.suffix.lower() in {".png", ".html"} and path.name not in keep_names:
                    continue
            arc = path.relative_to(job_dir).as_posix()
            zf.write(path, arc)
    return zip_path

"""Load and validate SKU configs, brand rulesets, and platform targets at startup."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import DEMO_ORDER, HEX_RE, Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class LoadedSku:
    sku: str
    raw: dict[str, Any]
    path: Path
    enabled_shots: list[dict[str, Any]]
    hero_abs: Path | None
    png_fallback_abs: Path | None = None
    missing_assets: list[str] = field(default_factory=list)
    brand_ruleset: str = "staples"
    display_name: str = ""
    short_name: str = ""
    card_label: str = ""
    resolved_refs: dict[str, Path | None] = field(default_factory=dict)

    @property
    def can_generate(self) -> bool:
        """A run needs the hero image; everything else can be missing."""
        return self.hero_abs is not None


@dataclass
class AppConfig:
    skus: dict[str, LoadedSku]
    rulesets: dict[str, dict[str, Any]]
    platform_targets: dict[str, Any]
    settings: Settings

    @property
    def missing_assets(self) -> dict[str, list[str]]:
        return {
            sku: loaded.missing_assets
            for sku, loaded in self.skus.items()
            if loaded.missing_assets
        }


def _strip_path_note(value: str | None) -> str | None:
    if not value:
        return None
    return value.split("  (")[0].strip()


def _collect_hexes(obj: Any, found: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "hex" and isinstance(v, str):
                found.append(v.upper())
            else:
                _collect_hexes(v, found)
    elif isinstance(obj, list):
        for item in obj:
            _collect_hexes(item, found)


def _validate_hexes(ruleset: dict[str, Any], ruleset_id: str) -> None:
    found: list[str] = []
    _collect_hexes(ruleset.get("palette", {}), found)
    _collect_hexes(ruleset.get("infographic_palette", {}), found)
    for hx in found:
        if not HEX_RE.match(hx):
            raise ValueError(f"Invalid hex in ruleset {ruleset_id}: {hx}")


def _resolve_product_references(
    settings: Settings, sku_raw: dict[str, Any]
) -> dict[str, Path | None]:
    """Map the symbolic names used by scene_prompt.input_images to real paths.

    Names are `hero_image` and `additional_product_references.<key>`, per
    _DEV_HANDOFF/prompts/01_nano_banana_scene_prompt.md.
    """
    refs: dict[str, Path | None] = {}
    hero = settings.resolve_asset(sku_raw["hero_image"]["path"])
    refs["hero_image"] = hero
    for key, value in (sku_raw.get("additional_product_references") or {}).items():
        if key.startswith("_") or not isinstance(value, str):
            continue
        path = settings.resolve_asset(value)
        refs[f"additional_product_references.{key}"] = (
            path if path and path.exists() else None
        )
    return refs


def _resolve_shot_paths(
    settings: Settings,
    sku_raw: dict[str, Any],
    shot: dict[str, Any],
    product_refs: dict[str, Path | None],
    missing: list[str],
) -> None:
    ref = shot.get("acceptance_reference")
    if ref:
        abs_path = settings.resolve_asset(ref)
        if abs_path and not abs_path.exists():
            if settings.strict_assets:
                raise FileNotFoundError(
                    f"acceptance_reference missing for {sku_raw['sku']}/{shot['shot_id']}: {abs_path}"
                )
            missing.append(str(ref))
            abs_path = None
        shot["_acceptance_reference_abs"] = abs_path
    else:
        shot["_acceptance_reference_abs"] = None

    # Resolve the shot's declared product references, hero always first.
    wanted = (shot.get("scene_prompt") or {}).get("input_images") or []
    resolved: list[Path] = []
    for name in wanted:
        path = product_refs.get(name)
        if path is None:
            if name in product_refs:
                logger.warning(
                    "%s/%s references missing asset '%s' — skipping",
                    sku_raw["sku"],
                    shot.get("shot_id"),
                    name,
                )
            else:
                logger.warning(
                    "%s/%s references unknown symbolic name '%s'",
                    sku_raw["sku"],
                    shot.get("shot_id"),
                    name,
                )
            continue
        if path not in resolved:
            resolved.append(path)
    hero = product_refs.get("hero_image")
    if hero and hero in resolved:
        resolved.remove(hero)
    if hero:
        resolved.insert(0, hero)
    shot["_scene_reference_abs"] = [str(p) for p in resolved]


def load_app_config(settings: Settings | None = None) -> AppConfig:
    settings = settings or get_settings()
    config_dir = settings.config_dir
    if not config_dir.is_absolute():
        config_dir = (settings.project_root / config_dir).resolve()

    rulesets: dict[str, dict[str, Any]] = {}
    for name in ("staples_ruleset.json", "coastwide_ruleset.json"):
        path = config_dir / name
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        rid = data["ruleset_id"]
        _validate_hexes(data, rid)
        rulesets[rid] = data
        logger.info("Loaded ruleset %s", rid)

    with (config_dir / "platform_targets.json").open(encoding="utf-8") as f:
        platform_targets = json.load(f)

    target_ids = {t["id"] for t in platform_targets["render_targets"]}

    skus: dict[str, LoadedSku] = {}
    for path in sorted(config_dir.glob("sku_*.json")):
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)

        sku = raw["sku"]
        brand = raw["brand_ruleset"]
        if brand not in rulesets:
            raise ValueError(f"Unknown brand_ruleset '{brand}' for SKU {sku}")

        missing: list[str] = []
        hero_rel = raw["hero_image"]["path"]
        hero_abs = settings.resolve_asset(hero_rel)
        if hero_abs is None or not hero_abs.exists():
            if settings.strict_assets:
                raise FileNotFoundError(f"Hero missing for {sku}: {hero_rel}")
            missing.append(str(hero_rel))
            hero_abs = None

        fallback_rel = _strip_path_note(raw["hero_image"].get("png_fallback"))
        fallback_abs = settings.resolve_asset(fallback_rel) if fallback_rel else None

        enabled = [s for s in raw["shots"] if s.get("enabled", True)]
        if not 6 <= len(enabled) <= 8:
            raise ValueError(
                f"SKU {sku} enabled shot count {len(enabled)} outside 6–8 range"
            )

        product_refs = _resolve_product_references(settings, raw)

        for shot in enabled:
            if "text_provenance" not in shot:
                raise ValueError(f"{sku}/{shot.get('shot_id')} missing text_provenance")
            if str(shot["text_provenance"]).startswith("PLACEHOLDER_POC"):
                if "placeholder_declaration" not in shot:
                    raise ValueError(
                        f"{sku}/{shot['shot_id']} PLACEHOLDER_POC missing declaration"
                    )
            for tid in shot.get("render_targets", []):
                if tid not in target_ids:
                    raise ValueError(f"{sku}/{shot['shot_id']} unknown target {tid}")
            if shot.get("brand_ruleset") and shot["brand_ruleset"] not in rulesets:
                raise ValueError(f"{sku}/{shot['shot_id']} bad brand_ruleset")
            _resolve_shot_paths(settings, raw, shot, product_refs, missing)

        loaded = LoadedSku(
            sku=sku,
            raw=raw,
            path=path,
            enabled_shots=enabled,
            hero_abs=hero_abs,
            png_fallback_abs=fallback_abs if fallback_abs and fallback_abs.exists() else None,
            brand_ruleset=brand,
            display_name=raw.get("display_name", sku),
            short_name=raw.get("short_name", raw.get("display_name", sku)),
            card_label=raw.get(
                "card_label_for_landing_page", raw.get("short_name", sku)
            ),
            resolved_refs=product_refs,
            missing_assets=missing,
        )
        skus[sku] = loaded
        logger.info(
            "Loaded SKU %s — %s enabled / %s total",
            sku,
            len(enabled),
            len(raw["shots"]),
        )
        if missing:
            logger.warning(
                "SKU %s is degraded — %s source asset(s) not on disk, generation disabled: %s",
                sku,
                len(missing),
                missing[0],
            )

    expected = {"24639471", "24321408", "24636223", "990119"}
    missing = expected - set(skus)
    if missing:
        raise ValueError(f"Missing SKU configs: {missing}")

    return AppConfig(
        skus=skus,
        rulesets=rulesets,
        platform_targets=platform_targets,
        settings=settings,
    )


def brand_accent(ruleset_id: str) -> str:
    return "#FF8200" if ruleset_id == "coastwide" else "#E42A11"


def demo_ordered_skus(app_config: AppConfig) -> list[LoadedSku]:
    return sorted(
        app_config.skus.values(),
        key=lambda s: DEMO_ORDER.get(s.sku, 99),
    )

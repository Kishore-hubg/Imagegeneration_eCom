"""FastAPI entrypoint — SKU cards, jobs, assets, package download."""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Playwright needs a Proactor event loop for subprocesses on Windows.
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import DEMO_ORDER, get_settings
from app.loader import AppConfig, brand_accent, demo_ordered_skus, load_app_config
from app.models import CreateJobRequest, ReferenceShot, SkuCard, SkuDetail
from app.orchestrator import Orchestrator
from app.pipeline.hero import ensure_thumbnail

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("staples.poc")

app_config: AppConfig | None = None
orchestrator: Orchestrator | None = None
thumb_dir: Path | None = None
higgsfield_status: dict | None = None


async def _preflight_higgsfield(settings) -> None:
    """Report Higgsfield reachability at boot instead of discovering it per shot."""
    global higgsfield_status
    from app.adapters.live import probe_higgsfield

    try:
        higgsfield_status = await probe_higgsfield()
    except Exception:
        logger.exception("Higgsfield preflight failed to run")
        return

    for model, state in (higgsfield_status.get("models") or {}).items():
        logger.info("Higgsfield %s: %s", model, state)

    if higgsfield_status.get("available"):
        logger.info(
            "Higgsfield is the active scene provider (%s)",
            ", ".join(higgsfield_status["usable_models"]),
        )
        return

    reason = higgsfield_status.get("reason")
    if reason == "credits":
        logger.error(
            "HIGGSFIELD UNAVAILABLE — account has no API credit balance. API credits are "
            "billed separately from a Higgsfield web subscription; top up at "
            "https://cloud.higgsfield.ai/. Scenes will come from the Gemini fallback."
        )
    elif reason == "auth":
        logger.error(
            "HIGGSFIELD UNAVAILABLE — credentials rejected. Regenerate the key/secret "
            "pair at https://cloud.higgsfield.ai/."
        )
    else:
        logger.error(
            "HIGGSFIELD UNAVAILABLE — no model in HIGGSFIELD_MODEL_CHAIN is provisioned "
            "for this account (%s). Scenes will come from the Gemini fallback.",
            reason,
        )
    if settings.higgsfield_required:
        logger.error("HIGGSFIELD_REQUIRED=true — photo shots will fail rather than fall back.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_config, orchestrator, thumb_dir
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level.upper())

    if settings.mock_mode:
        logger.warning("MOCK_MODE=true — using acceptance-reference images, not live generation")
    else:
        await _preflight_higgsfield(settings)

    app_config = load_app_config(settings)
    for sku, loaded in app_config.skus.items():
        logger.info(
            "Boot SKU %s: %s enabled shots",
            sku,
            len(loaded.enabled_shots),
        )

    thumb_dir = settings.project_root / "assets" / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    for loaded in app_config.skus.values():
        dest = thumb_dir / f"{loaded.sku}.png"
        try:
            ensure_thumbnail(loaded.hero_abs, dest, png_fallback=loaded.png_fallback_abs)
        except Exception:
            logger.exception("Failed to build thumbnail for %s", loaded.sku)

    from app.pipeline import compose

    try:
        await compose.start_browser()
    except Exception:
        logger.exception(
            "Playwright Chromium failed to start — overlay rasterization will fail until fixed"
        )

    orchestrator = Orchestrator(app_config)
    yield

    await compose.stop_browser()


app = FastAPI(title="Staples Image Generation POC", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


def _sku_card(loaded) -> SkuCard:
    assert app_config
    approved = loaded.raw.get("approved_source_strings") or {}
    ref_count = sum(
        1 for s in loaded.enabled_shots if s.get("_acceptance_reference_abs")
    )
    return SkuCard(
        sku=loaded.sku,
        display_name=loaded.display_name,
        short_name=loaded.short_name,
        card_label=loaded.card_label,
        brand_ruleset=loaded.brand_ruleset,
        hero_thumbnail_url=f"/api/thumbs/{loaded.sku}.png",
        shot_count=len(loaded.enabled_shots),
        demo_order=DEMO_ORDER.get(loaded.sku, 99),
        brand_accent=brand_accent(loaded.brand_ruleset),
        reference_count=ref_count,
        headliner=approved.get("headliner"),
    )


@app.get("/api/skus")
def list_skus() -> list[SkuCard]:
    assert app_config and thumb_dir
    return [_sku_card(loaded) for loaded in demo_ordered_skus(app_config)]


@app.get("/api/skus/{sku}")
def get_sku(sku: str) -> SkuDetail:
    """Product detail with Staples Assets hero + production references."""
    assert app_config
    loaded = app_config.skus.get(sku)
    if not loaded:
        raise HTTPException(404, "Unknown SKU")

    ruleset = app_config.rulesets[loaded.brand_ruleset]
    voice = ruleset.get("brand_voice") or {}
    approved = loaded.raw.get("approved_source_strings") or {}
    bullets = approved.get("marketplace_bullets") or []
    if isinstance(bullets, str):
        bullets = [bullets]

    refs: list[ReferenceShot] = []
    for sc in loaded.enabled_shots:
        abs_ref = sc.get("_acceptance_reference_abs")
        has = bool(abs_ref and Path(abs_ref).exists())
        rel = sc.get("acceptance_reference")
        refs.append(
            ReferenceShot(
                shot_id=sc["shot_id"],
                label=sc.get("brief_shot_name") or sc["shot_id"],
                type=sc["type"],
                has_reference=has,
                reference_url=f"/api/reference/{sku}/{sc['shot_id']}" if has else None,
                reference_path=rel,
            )
        )

    hero_rel = loaded.raw.get("hero_image", {}).get("path", "")
    return SkuDetail(
        sku=loaded.sku,
        display_name=loaded.display_name,
        short_name=loaded.short_name,
        card_label=loaded.card_label,
        brand_ruleset=loaded.brand_ruleset,
        brand_accent=brand_accent(loaded.brand_ruleset),
        brand_voice_summary=voice.get("summary"),
        brand_voice_tone=voice.get("tone"),
        hero_thumbnail_url=f"/api/thumbs/{loaded.sku}.png",
        hero_path=hero_rel,
        headliner=approved.get("headliner"),
        marketplace_bullets=list(bullets)[:6],
        approved_source_note=approved.get("_note"),
        reference_shots=refs,
    )


@app.get("/api/thumbs/{filename}")
def get_thumb(filename: str):
    assert thumb_dir
    path = thumb_dir / filename
    if not path.exists():
        raise HTTPException(404, "Thumbnail not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/channels")
def list_channels():
    assert app_config
    channels = [
        c
        for c in app_config.platform_targets.get("channels", [])
        if c.get("show_in_ui", True)
    ]
    return channels


@app.post("/api/jobs", status_code=201)
async def create_job(body: CreateJobRequest):
    assert orchestrator and app_config
    if body.sku not in app_config.skus:
        raise HTTPException(404, {"error": "Unknown SKU"})
    job = await orchestrator.create_job(body.sku)
    return {"job_id": job.job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    assert orchestrator
    job = orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    # Rewrite thumbnail URLs to API asset routes
    payload = job.model_dump()
    for shot in payload["shots"]:
        if shot.get("thumbnail_url") and not str(shot["thumbnail_url"]).startswith("/"):
            shot["thumbnail_url"] = (
                f"/api/assets/{job.sku}/{job.job_id}/{shot['shot_id']}/{shot['thumbnail_url'].split('/')[-1]}"
            )
        elif shot.get("thumbnail_url") and shot["shot_id"] in str(shot["thumbnail_url"]):
            # already relative like SKU_0/file.png from router
            name = str(shot["thumbnail_url"]).split("/")[-1]
            shot["thumbnail_url"] = (
                f"/api/assets/{job.sku}/{job.job_id}/{shot['shot_id']}/{name}"
            )
    payload["status"] = job.status.value
    payload["counts"] = job.counts.model_dump()
    return payload


@app.get("/api/assets/{sku}/{job_id}/{shot_id}/{filename}")
def get_asset(sku: str, job_id: str, shot_id: str, filename: str):
    assert orchestrator
    job = orchestrator.get_job(job_id)
    if not job or job.sku != sku:
        raise HTTPException(404, "Job not found")
    path = orchestrator.job_dir(job) / shot_id / filename
    if not path.exists():
        raise HTTPException(404, "Asset not found")
    return FileResponse(path)


@app.get("/api/reference/{sku}/{shot_id}")
def get_reference(sku: str, shot_id: str):
    assert app_config
    loaded = app_config.skus.get(sku)
    if not loaded:
        raise HTTPException(404, "Unknown SKU")
    for sc in loaded.enabled_shots:
        if sc["shot_id"] == shot_id:
            ref = sc.get("_acceptance_reference_abs")
            if not ref or not Path(ref).exists():
                raise HTTPException(404, "No acceptance reference")
            return FileResponse(ref)
    raise HTTPException(404, "Shot not found")


@app.get("/api/jobs/{job_id}/package")
def download_package(
    job_id: str,
    include_intermediates: bool = Query(False),
):
    assert orchestrator
    job = orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status.value in ("queued", "running"):
        raise HTTPException(409, "Job is not finished")
    job_dir = orchestrator.job_dir(job)
    zip_path = job_dir / "package.zip"
    if include_intermediates:
        from app.pipeline import router as shot_router

        zip_path = job_dir / "package_full.zip"
        shot_router.zip_package(job_dir, zip_path, include_intermediates=True)
    if not zip_path.exists():
        raise HTTPException(404, "Package not ready")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{job.sku}_{job_id[:8]}_package.zip",
    )


@app.get("/api/health")
def health():
    assert app_config
    return {
        "ok": True,
        "mock_mode": app_config.settings.mock_mode,
        "scene_provider": (
            "mock"
            if app_config.settings.mock_mode
            else ("higgsfield" if (higgsfield_status or {}).get("available") else "gemini (fallback)")
        ),
        "higgsfield": higgsfield_status,
        "skus": {
            sku: len(loaded.enabled_shots) for sku, loaded in app_config.skus.items()
        },
    }

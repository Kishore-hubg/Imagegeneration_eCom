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
from app.orchestrator import AssetsUnavailableError, Orchestrator
from app.pipeline.hero import ensure_thumbnail

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("staples.poc")

app_config: AppConfig | None = None
orchestrator: Orchestrator | None = None
thumb_dir: Path | None = None
higgsfield_status: dict | None = None
boot_error: str | None = None
browser_ready: bool = False


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


async def _boot() -> None:
    """Build app state. Individual failures degrade features, never the process."""
    global app_config, orchestrator, thumb_dir, browser_ready
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level.upper())

    if settings.mock_mode:
        logger.warning("MOCK_MODE=true — using acceptance-reference images, not live generation")
    elif settings.is_serverless:
        # Nothing here can generate, so don't spend credentialed calls per cold start.
        logger.warning("Serverless runtime — skipping Higgsfield preflight")
    else:
        await _preflight_higgsfield(settings)

    app_config = load_app_config(settings)
    for sku, loaded in app_config.skus.items():
        logger.info("Boot SKU %s: %s enabled shots", sku, len(loaded.enabled_shots))

    thumb_dir = settings.thumbnail_dir
    try:
        thumb_dir.mkdir(parents=True, exist_ok=True)
        for loaded in app_config.skus.values():
            if loaded.hero_abs is None:
                continue
            dest = thumb_dir / f"{loaded.sku}.png"
            try:
                ensure_thumbnail(loaded.hero_abs, dest, png_fallback=loaded.png_fallback_abs)
            except Exception:
                logger.exception("Failed to build thumbnail for %s", loaded.sku)
    except OSError:
        logger.exception("Thumbnail directory %s is not writable", thumb_dir)

    # Chromium has no binary and no room inside a serverless bundle.
    if settings.is_serverless:
        logger.warning("Serverless runtime — skipping Playwright, overlay shots are unavailable")
    else:
        from app.pipeline import compose

        try:
            await compose.start_browser()
            browser_ready = True
        except Exception:
            logger.exception(
                "Playwright Chromium failed to start — overlay rasterization will fail until fixed"
            )

    orchestrator = Orchestrator(app_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global boot_error
    try:
        await _boot()
    except Exception as exc:
        boot_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Startup failed — serving in degraded mode")

    yield

    if browser_ready:
        from app.pipeline import compose

        try:
            await compose.stop_browser()
        except Exception:
            logger.exception("Error stopping Playwright")


app = FastAPI(title="Staples Image Generation POC", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"
BUNDLED_THUMB_DIR = STATIC_DIR / "thumbnails"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.error("Static directory %s is missing from this deployment", STATIC_DIR)


def _require_config() -> AppConfig:
    if app_config is None:
        raise HTTPException(503, boot_error or "Application configuration is not loaded")
    return app_config


def _require_orchestrator() -> Orchestrator:
    if orchestrator is None:
        raise HTTPException(503, boot_error or "Job orchestrator is not available")
    return orchestrator


@app.get("/")
def index():
    path = STATIC_DIR / "index.html"
    if not path.exists():
        raise HTTPException(503, "UI assets are missing from this deployment")
    return FileResponse(path)


def _sku_card(loaded) -> SkuCard:
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
        can_generate=loaded.can_generate,
        unavailable_reason=(
            None
            if loaded.can_generate
            else "Source imagery is not available on this deployment"
        ),
    )


@app.get("/api/skus")
def list_skus() -> list[SkuCard]:
    config = _require_config()
    return [_sku_card(loaded) for loaded in demo_ordered_skus(config)]


@app.get("/api/skus/{sku}")
def get_sku(sku: str) -> SkuDetail:
    """Product detail with Staples Assets hero + production references."""
    app_config = _require_config()
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
    if thumb_dir is not None:
        generated = thumb_dir / filename
        if generated.exists():
            return FileResponse(generated, media_type="image/png")

    # Deployments without `Staples Assets/` still get a catalogue image.
    bundled = BUNDLED_THUMB_DIR / filename
    if bundled.exists():
        return FileResponse(bundled, media_type="image/png")
    raise HTTPException(404, "Thumbnail not found")


@app.get("/api/channels")
def list_channels():
    app_config = _require_config()
    channels = [
        c
        for c in app_config.platform_targets.get("channels", [])
        if c.get("show_in_ui", True)
    ]
    return channels


@app.post("/api/jobs", status_code=201)
async def create_job(body: CreateJobRequest):
    app_config = _require_config()
    orchestrator = _require_orchestrator()
    if body.sku not in app_config.skus:
        raise HTTPException(404, {"error": "Unknown SKU"})
    try:
        job = await orchestrator.create_job(body.sku)
    except AssetsUnavailableError as exc:
        raise HTTPException(
            503,
            "Source imagery for this SKU is not deployed, so generation cannot run here. "
            f"Missing: {exc.missing[0] if exc.missing else 'hero image'}",
        ) from exc
    return {"job_id": job.job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    orchestrator = _require_orchestrator()
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
    orchestrator = _require_orchestrator()
    job = orchestrator.get_job(job_id)
    if not job or job.sku != sku:
        raise HTTPException(404, "Job not found")
    path = orchestrator.job_dir(job) / shot_id / filename
    if not path.exists():
        raise HTTPException(404, "Asset not found")
    return FileResponse(path)


@app.get("/api/reference/{sku}/{shot_id}")
def get_reference(sku: str, shot_id: str):
    app_config = _require_config()
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
    orchestrator = _require_orchestrator()
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
    settings = get_settings()
    if app_config is None:
        return {
            "ok": False,
            "boot_error": boot_error or "Configuration did not load",
            "mock_mode": settings.mock_mode,
            "serverless": settings.is_serverless,
            "skus": {},
        }

    missing = app_config.missing_assets
    return {
        "ok": True,
        "mock_mode": app_config.settings.mock_mode,
        "serverless": app_config.settings.is_serverless,
        "generation_available": not missing and (browser_ready or app_config.settings.mock_mode),
        "overlay_rasterization": browser_ready,
        "degraded_reason": (
            "Product source imagery is not deployed with this build, so image "
            "generation is disabled. The catalogue and brand rules are read-only here."
            if missing
            else None
        ),
        "missing_asset_skus": sorted(missing),
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

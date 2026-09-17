"""Rasterize HTML overlays (Playwright) and composite onto photos (Pillow).

Uses sync Playwright on a dedicated worker thread so it works under uvicorn
on Windows (SelectorEventLoop cannot spawn subprocesses).
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Any, Callable

from PIL import Image

logger = logging.getLogger(__name__)

_request_q: queue.Queue[tuple[str, dict[str, Any], queue.Queue[Any]] | None] = queue.Queue()
_worker: threading.Thread | None = None
_started = threading.Event()
_start_error: BaseException | None = None


def _worker_main() -> None:
    global _start_error
    browser = None
    pw = None
    try:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        _started.set()
        logger.info("Playwright Chromium ready for overlay rasterization")

        while True:
            item = _request_q.get()
            if item is None:
                break
            op, payload, reply = item
            try:
                if op == "rasterize":
                    html: str = payload["html"]
                    out_path: Path = payload["out_path"]
                    size: int = payload["size"]
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    page = browser.new_page()
                    try:
                        page.set_viewport_size({"width": size, "height": size})
                        page.set_content(html, wait_until="load")
                        page.wait_for_timeout(250)
                        page.screenshot(path=str(out_path), omit_background=True, type="png")
                    finally:
                        page.close()
                    reply.put(("ok", out_path))
                else:
                    reply.put(("err", RuntimeError(f"Unknown op: {op}")))
            except BaseException as exc:  # noqa: BLE001 - surface to caller
                reply.put(("err", exc))
    except BaseException as exc:  # noqa: BLE001
        _start_error = exc
        _started.set()
        logger.exception("Playwright worker failed to start")
    finally:
        try:
            if browser is not None:
                browser.close()
            if pw is not None:
                pw.stop()
        except Exception:
            logger.exception("Error shutting down Playwright")


def _ensure_worker() -> None:
    global _worker, _start_error
    if _worker is not None and _worker.is_alive():
        return
    _start_error = None
    _started.clear()
    _worker = threading.Thread(target=_worker_main, name="playwright-raster", daemon=True)
    _worker.start()
    if not _started.wait(timeout=60):
        raise RuntimeError("Playwright worker did not start within 60s")
    if _start_error is not None:
        raise RuntimeError(f"Playwright failed to start: {_start_error}") from _start_error


def _call_worker(op: str, **payload: Any) -> Any:
    _ensure_worker()
    reply: queue.Queue[Any] = queue.Queue()
    _request_q.put((op, payload, reply))
    status, value = reply.get()
    if status == "err":
        raise value
    return value


async def start_browser() -> None:
    """Launch a shared Chromium once at app startup (Stage 7)."""
    await asyncio_to_thread(_ensure_worker)


async def stop_browser() -> None:
    global _worker
    if _worker is not None and _worker.is_alive():
        _request_q.put(None)
        _worker.join(timeout=15)
        _worker = None


async def rasterize_overlay_html(
    html: str,
    out_path: Path,
    size: int = 1500,
    accent: str = "#FF8200",
    text_color: str = "#414140",
) -> Path:
    """
    Rasterize Claude's HTML/CSS/SVG overlay via headless Chromium.
    `accent` / `text_color` retained for call-site compatibility.
    """
    del accent, text_color
    return await asyncio_to_thread(
        _call_worker, "rasterize", html=html, out_path=out_path, size=size
    )


async def asyncio_to_thread(func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    import asyncio

    return await asyncio.to_thread(func, *args, **kwargs)


def composite_overlay(photo_path: Path, overlay_path: Path, out_path: Path) -> Path:
    base = Image.open(photo_path).convert("RGBA")
    over = Image.open(overlay_path).convert("RGBA")
    if over.size != base.size:
        over = over.resize(base.size, Image.LANCZOS)
    base.alpha_composite(over)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, "PNG")
    return out_path


def scale_square(src: Path, out_path: Path, size: int) -> Path:
    img = Image.open(src).convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


def flatten_graphic(overlay_png: Path, out_path: Path, bg: tuple[int, int, int] = (255, 255, 255)) -> Path:
    over = Image.open(overlay_png).convert("RGBA")
    canvas = Image.new("RGBA", over.size, bg + (255,))
    canvas.alpha_composite(over)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, "PNG")
    return out_path

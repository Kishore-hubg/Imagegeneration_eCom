"""One-off: re-rasterize existing overlay.html files with Playwright and rebuild composites."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.pipeline import compose  # noqa: E402

RUN = ROOT / "outputs_live/24639471/run/284017c4-75be-4ad3-9cb4-e7fe6ce094f5"

# photo_overlay shots that still have usable raw photos + Claude HTML
PHOTO_OVERLAY = ("SKU_1", "SKU_3", "SKU_5")
# graphic_only that only need flatten (will look correct after Playwright)
GRAPHIC_ONLY = ("SKU_2", "SKU_6")


async def main() -> None:
    await compose.start_browser()
    try:
        for shot_id in PHOTO_OVERLAY + GRAPHIC_ONLY:
            shot_dir = RUN / shot_id
            html_path = shot_dir / "overlay.html"
            if not html_path.exists():
                print(f"SKIP {shot_id}: no overlay.html")
                continue
            html = html_path.read_text(encoding="utf-8")
            overlay_png = shot_dir / "overlay.png"
            await compose.rasterize_overlay_html(html, overlay_png)
            print(f"OK raster {shot_id} -> {overlay_png.name}")

            if shot_id in PHOTO_OVERLAY:
                raw = shot_dir / "raw_attempt_1.png"
                composite = shot_dir / "composite.png"
                compose.composite_overlay(raw, overlay_png, composite)
                secondary = shot_dir / "RT_SECONDARY_SQUARE.png"
                compose.scale_square(composite, secondary, 2000)
                print(f"OK composite {shot_id}")
            else:
                composite = shot_dir / "composite.png"
                compose.flatten_graphic(overlay_png, composite)
                secondary = shot_dir / "RT_SECONDARY_SQUARE.png"
                compose.scale_square(composite, secondary, 2000)
                print(f"OK flatten {shot_id}")
    finally:
        await compose.stop_browser()


if __name__ == "__main__":
    asyncio.run(main())

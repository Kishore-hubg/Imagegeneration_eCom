"""Repair SKU_3 truncated overlay in run 54437027 and refresh package zip."""

from __future__ import annotations

import asyncio
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.pipeline import compose, lint  # noqa: E402

RUN = ROOT / "outputs_live/24639471/run/54437027-bd13-47ba-ba87-94aab16135d4"
SHOT = RUN / "SKU_3"
ZIP_OUTER = ROOT / "outputs_live/24639471_54437027_package.zip"
ZIP_INNER = RUN / "package.zip"

SHOT_CFG = {
    "type": "photo_overlay",
    "text_provenance": "APPROVED - declared shortenings, see shortening_rule",
    "overlay_text": {
        "callouts": [
            {"label": "Ergonomic spray trigger"},
            {"label": "Easy fill tank"},
            {"label": "7k sq. ft. per refill"},
            {"label": "Pre-measured refill cartridges"},
        ]
    },
}
RULESET = {
    "palette": {
        "orange": {"hex": "#FF8200"},
        "charcoal": {"hex": "#414140"},
        "white": {"hex": "#FFFFFF"},
    }
}


async def main() -> None:
    html = (SHOT / "overlay.html").read_text(encoding="utf-8")
    ok, reason = lint.overlay_html_is_complete(html)
    assert ok, reason
    results = lint.lint_overlay_markup(html, SHOT_CFG, RULESET)
    fails = [r for r in results if r.get("status") == "FAIL"]
    assert not fails, fails

    await compose.start_browser()
    try:
        overlay_png = SHOT / "overlay.png"
        await compose.rasterize_overlay_html(html, overlay_png)
        raw = SHOT / "raw_attempt_1.png"
        composite = SHOT / "composite.png"
        compose.composite_overlay(raw, overlay_png, composite)
        secondary = SHOT / "RT_SECONDARY_SQUARE.png"
        compose.scale_square(composite, secondary, 2000)
        print(f"OK rebuilt {secondary}")
    finally:
        await compose.stop_browser()

    # Refresh both package zips with deliverables from this run
    for zip_path in (ZIP_INNER, ZIP_OUTER):
        _rewrite_run_zip(zip_path)
        print(f"OK zip {zip_path.name}")


def _rewrite_run_zip(zip_path: Path) -> None:
    keep_names = {
        "RT_MAIN_WHITE.png",
        "RT_SECONDARY_SQUARE.png",
        "composite.png",
        "manifest.json",
        "README.txt",
    }
    tmp = zip_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in RUN.rglob("*"):
            if not path.is_file():
                continue
            if path.name not in keep_names and path.suffix.lower() in {".png", ".html"}:
                continue
            if path.name not in keep_names and path.suffix.lower() not in {".json", ".txt"}:
                if path.name not in keep_names:
                    continue
            arc = path.relative_to(RUN).as_posix()
            zf.write(path, arc)
    tmp.replace(zip_path)


if __name__ == "__main__":
    asyncio.run(main())

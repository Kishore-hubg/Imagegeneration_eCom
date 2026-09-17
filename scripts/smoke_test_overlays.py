"""
Cross-SKU overlay smoke test — any product category.

For each enabled photo_overlay / graphic_only shot with overlay_text:
  1. Call Claude design_overlay (live) or mock
  2. Assert HTML is complete (</html>)
  3. Assert every approved string appears in the markup
  4. Optionally rasterize with Playwright

Usage:
  .\\.venv\\Scripts\\python.exe scripts\\smoke_test_overlays.py
  .\\.venv\\Scripts\\python.exe scripts\\smoke_test_overlays.py --mock
  .\\.venv\\Scripts\\python.exe scripts\\smoke_test_overlays.py --sku 24321408 --limit 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.loader import load_app_config
from app.pipeline import compose, lint
from app.adapters import mock as adapters


# Representative text shots across product categories (mop / cleaner / pen / chair)
DEFAULT_SAMPLES = {
    "24639471": ["SKU_1", "SKU_3"],  # ExpressMop: contents + feature callouts
    "24321408": ["SKU_1", "SKU_5"],  # Power Cleaner: yield + dispenser
    "24636223": ["SKU_1", "SKU_2", "SKU_3"],  # ProGel: pack + features
    "990119": ["SKU_1", "SKU_2", "SKU_3"],  # Hyken: dimensions + adjustments + mesh
}


async def test_shot(
    *,
    sku: str,
    shot: dict,
    ruleset: dict,
    hero: Path,
    mock_mode: bool,
    rasterize: bool,
    out_dir: Path,
) -> dict:
    shot_id = shot["shot_id"]
    stype = shot["type"]
    photo = None
    if stype == "photo_overlay":
        ref = shot.get("_acceptance_reference_abs")
        photo = Path(ref) if ref and Path(ref).exists() else hero

    html = await adapters.design_overlay(
        mock_mode=mock_mode,
        shot=shot,
        photo_path=photo,
        brand_ruleset=ruleset,
    )

    shot_out = out_dir / sku / shot_id
    shot_out.mkdir(parents=True, exist_ok=True)
    (shot_out / "overlay.html").write_text(html, encoding="utf-8")

    ok, reason = lint.overlay_html_is_complete(html)
    results = lint.lint_overlay_markup(html, shot, ruleset)
    fails = [r for r in results if r.get("status") == "FAIL"]

    raster_ok = None
    if rasterize and not fails and ok:
        await compose.start_browser()
        try:
            await compose.rasterize_overlay_html(html, shot_out / "overlay.png")
            raster_ok = True
        except Exception as exc:  # noqa: BLE001
            raster_ok = False
            fails.append({"check": "rasterize", "status": "FAIL", "detail": str(exc)})

    status = "PASS" if ok and not fails else "FAIL"
    return {
        "sku": sku,
        "shot_id": shot_id,
        "type": stype,
        "status": status,
        "html_complete": ok,
        "complete_reason": reason,
        "lint_fails": fails,
        "html_bytes": len(html.encode("utf-8")),
        "rasterize": raster_ok,
        "out": str(shot_out / "overlay.html"),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--sku", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0, help="Max shots per SKU (0=use samples)")
    parser.add_argument("--all-text-shots", action="store_true")
    parser.add_argument("--no-rasterize", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    # Force live unless --mock
    if args.mock:
        settings.mock_mode = True

    cfg = load_app_config(settings)
    out_dir = ROOT / "outputs_live" / "_overlay_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)

    skus = args.sku or list(DEFAULT_SAMPLES.keys())
    report = []
    try:
        for sku in skus:
            loaded = cfg.skus.get(sku)
            if not loaded:
                report.append({"sku": sku, "status": "FAIL", "detail": "SKU not loaded"})
                continue
            ruleset = cfg.rulesets[loaded.brand_ruleset]
            wanted = None if args.all_text_shots else set(DEFAULT_SAMPLES.get(sku, []))
            count = 0
            for shot in loaded.enabled_shots:
                if shot["type"] not in {"photo_overlay", "graphic_only", "graphic_only_with_generated_tiles"}:
                    continue
                if not shot.get("overlay_text"):
                    continue
                if wanted is not None and shot["shot_id"] not in wanted:
                    continue
                if args.limit and count >= args.limit:
                    break
                count += 1
                print(f"Testing {sku}/{shot['shot_id']} ({shot['type']}) ...")
                result = await test_shot(
                    sku=sku,
                    shot=shot,
                    ruleset=ruleset,
                    hero=loaded.hero_abs,
                    mock_mode=args.mock or settings.mock_mode,
                    rasterize=not args.no_rasterize,
                    out_dir=out_dir,
                )
                report.append(result)
                print(f"  -> {result['status']} complete={result['html_complete']} fails={len(result['lint_fails'])}")
                for f in result["lint_fails"]:
                    print(f"     FAIL {f.get('check')}: {f.get('detail')}")
    finally:
        await compose.stop_browser()

    summary = {
        "total": len(report),
        "passed": sum(1 for r in report if r.get("status") == "PASS"),
        "failed": sum(1 for r in report if r.get("status") != "PASS"),
        "results": report,
    }
    out_path = out_dir / "SMOKE_REPORT.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = [
        "# Overlay smoke test",
        "",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        "",
        "| SKU | Shot | Type | Status | Notes |",
        "|---|---|---|---|---|",
    ]
    for r in report:
        notes = r.get("complete_reason") or ""
        if r.get("lint_fails"):
            notes = "; ".join(f"{x.get('check')}: {x.get('detail')}" for x in r["lint_fails"])[:120]
        md.append(
            f"| {r.get('sku')} | {r.get('shot_id')} | {r.get('type')} | **{r.get('status')}** | {notes} |"
        )
    (out_dir / "SMOKE_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"PASS {summary['passed']} / FAIL {summary['failed']}")
    if summary["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

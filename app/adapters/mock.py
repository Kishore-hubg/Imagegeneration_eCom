"""Stage 0 mock adapters — one module, three functions, branch at the top."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from app.adapters.live import SceneResult

FIXTURE_OVERLAY_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1500px; height: 1500px;
    font-family: 'Poppins', 'Helvetica Neue', Arial, sans-serif;
    background: transparent;
    color: #414140;
  }
  .root {
    width: 1500px; height: 1500px;
    position: relative;
    padding: 80px;
  }
  .badge {
    position: absolute; top: 48px; left: 48px;
    font-size: 28px; letter-spacing: 0.04em;
    color: #FF8200; font-weight: 700;
  }
  .headline {
    position: absolute; top: 120px; left: 80px; right: 80px;
    font-size: 72px; line-height: 1.15; font-weight: 700;
    color: #FF8200;
  }
  .body {
    position: absolute; top: 320px; left: 80px; right: 40%;
    font-size: 48px; line-height: 1.3; font-weight: 400;
    color: #414140;
  }
</style>
</head>
<body>
  <div class="root">
    <div class="badge">Mock overlay</div>
    <div class="headline">__HEADLINE__</div>
    <div class="body">__BODY__</div>
  </div>
</body>
</html>
"""


async def generate_scene(
    *,
    mock_mode: bool,
    prompt: str,
    input_image_paths: list[Path],
    aspect_ratio: str,
    acceptance_reference: Path | None,
    out_path: Path,
) -> "SceneResult":
    """Higgsfield (nano-banana / Soul chain) or mock."""
    from app.adapters.live import SceneResult

    if mock_mode:
        await asyncio.sleep(random.uniform(2.0, 3.5))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if acceptance_reference and acceptance_reference.exists():
            img = Image.open(acceptance_reference).convert("RGB")
        else:
            img = _placeholder_card(
                out_path.stem,
                "No acceptance reference — mock placeholder",
            )
        img = _watermark_mock(img)
        img.save(out_path, "PNG")
        return SceneResult(path=out_path, provider="mock", model="acceptance_reference")

    from app.adapters import live as live_adapters

    return await live_adapters.generate_scene(
        prompt=prompt,
        input_image_paths=input_image_paths,
        aspect_ratio=aspect_ratio,
        out_path=out_path,
    )


async def fidelity_gate(
    *,
    mock_mode: bool,
    photo_path: Path,
    hero_path: Path,
    check_product_identity: bool = True,
) -> dict[str, Any]:
    """Gemini vision gate or mock."""
    if mock_mode:
        await asyncio.sleep(1.0)
        return {
            "verdict": "PASS",
            "product_identity": "PASS" if check_product_identity else "SKIPPED",
            "setting": "PASS",
            "brand_safety": "PASS",
            "reserved_space": "PASS",
            "notes": "Mock mode — automatic pass",
        }
    from app.adapters import live as live_adapters

    return await live_adapters.fidelity_gate(
        photo_path=photo_path,
        hero_path=hero_path,
        check_product_identity=check_product_identity,
    )


async def design_overlay(
    *,
    mock_mode: bool,
    shot: dict[str, Any],
    photo_path: Path | None,
    brand_ruleset: dict[str, Any],
) -> str:
    """Claude overlay HTML or mock fixture."""
    if mock_mode:
        await asyncio.sleep(2.0)
        overlay = shot.get("overlay_text") or {}
        accent = "#FF8200"
        text_color = "#414140"
        if brand_ruleset.get("ruleset_id") == "staples":
            accent = "#E42A11"
            text_color = "#262020"

        # Emit EVERY approved string so mock mode cannot "miss the text part"
        lines: list[str] = []
        headline = overlay.get("resolved_headline") or overlay.get("headline")
        if headline:
            lines.append(f'<div class="headline">{headline}</div>')
        if overlay.get("headline_line_2"):
            lines.append(f'<div class="sub">{overlay["headline_line_2"]}</div>')
        sub = overlay.get("sub_headline") or overlay.get("subhead") or overlay.get("body")
        if sub and not isinstance(sub, list):
            lines.append(f'<div class="sub">{sub}</div>')
        if overlay.get("resolved_footnote"):
            lines.append(f'<div class="sub">{overlay["resolved_footnote"]}</div>')
        for item in overlay.get("items") or []:
            if isinstance(item, dict):
                count = item.get("count") or item.get("value") or ""
                label = item.get("label") or ""
                lines.append(f'<div class="row"><span class="num">{count}</span> {label}</div>')
        if overlay.get("supporting_line"):
            lines.append(f'<div class="sub">{overlay["supporting_line"]}</div>')
        for callout in overlay.get("callouts") or []:
            if isinstance(callout, dict):
                value = callout.get("value") or ""
                label = callout.get("label") or ""
                lines.append(f'<div class="row"><span class="num">{value}</span> {label}</div>')
            elif isinstance(callout, str):
                lines.append(f'<div class="row">{callout}</div>')
        for benefit in overlay.get("benefits") or []:
            if isinstance(benefit, dict):
                title = benefit.get("title") or ""
                body = benefit.get("body") or ""
                lines.append(f'<div class="row"><strong>{title}</strong> {body}</div>')
        for step in overlay.get("steps") or []:
            if isinstance(step, dict):
                lines.append(
                    f'<div class="row"><span class="num">{step.get("number") or ""}</span> '
                    f'{step.get("caption") or ""}</div>'
                )
        for swatch in overlay.get("swatches") or []:
            if isinstance(swatch, str):
                lines.append(f'<div class="row">{swatch}</div>')
        if overlay.get("disclaimer"):
            lines.append(f'<div class="sub">{overlay["disclaimer"]}</div>')
        if not lines:
            lines.append('<div class="headline">Brand layer</div>')
            lines.append('<div class="sub">Deterministic mock overlay for Stage 0.</div>')

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  body {{ width:1500px; height:1500px; margin:0; background:transparent;
         font-family:'Poppins','Helvetica Neue',Arial,sans-serif; color:{text_color}; }}
  .root {{ position:relative; width:1500px; height:1500px; padding:80px; box-sizing:border-box; }}
  .headline {{ color:{accent}; font-weight:700; font-size:64px; line-height:1.15; margin:0 0 24px 0; }}
  .sub {{ font-size:44px; line-height:1.3; margin:0 0 18px 0; }}
  .row {{ font-size:42px; line-height:1.25; margin:0 0 14px 0; }}
  .num {{ color:{accent}; font-weight:700; }}
</style></head>
<body><div class="root">{"".join(lines)}</div></body></html>
"""
    from app.adapters import live as live_adapters

    return await live_adapters.design_overlay(
        shot=shot,
        photo_path=photo_path,
        brand_ruleset=brand_ruleset,
    )


def _watermark_mock(img: Image.Image) -> Image.Image:
    """Mark mock artifacts so they are never mistaken for generated work."""
    rgba = img.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = rgba.size
    try:
        font = ImageFont.truetype("arial.ttf", max(24, w // 40))
    except OSError:
        font = ImageFont.load_default()
    label = "MOCK — NOT GENERATED"
    draw.rectangle([0, h - 56, w, h], fill=(228, 42, 17, 180))
    draw.text((24, h - 44), label, fill=(255, 255, 255, 255), font=font)
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def _placeholder_card(shot_id: str, message: str) -> Image.Image:
    img = Image.new("RGB", (1500, 1500), (245, 243, 240))
    draw = ImageDraw.Draw(img)
    try:
        font_lg = ImageFont.truetype("arial.ttf", 64)
        font_sm = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font_lg = ImageFont.load_default()
        font_sm = font_lg
    draw.text((80, 200), shot_id, fill=(228, 42, 17), font=font_lg)
    draw.text((80, 320), message, fill=(38, 32, 32), font=font_sm)
    draw.text((80, 400), "Mock mode placeholder", fill=(163, 160, 156), font=font_sm)
    return img

"""Render the Staples marketplace image studio complete workflow as PNG."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "COMPLETE_WORKFLOW.png"

# Brand tokens (no gradients per style guide)
PAPER = (245, 243, 240)
WHITE = (255, 255, 255)
SLATE = (38, 32, 32)
CHARCOAL = (65, 65, 64)
STAPLES_RED = (228, 42, 17)
COASTWIDE_ORANGE = (255, 130, 0)
MUTED = (120, 110, 105)
LINE = (200, 190, 180)
SOFT = (250, 248, 245)
ACCENT_BG = (255, 240, 235)
ORANGE_BG = (255, 246, 235)
GREEN_BG = (236, 245, 238)
BLUE_BG = (235, 242, 248)
YELLOW_BG = (255, 248, 230)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=None, radius=14, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw, box, text, fnt, fill=SLATE):
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((x0 + x1 - tw) / 2, (y0 + y1 - th) / 2), text, font=fnt, fill=fill)


def multiline_center(draw, cx, y, lines, fnt, fill=SLATE, gap=4):
    total = 0
    sizes = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        sizes.append((tw, th))
        total += th + gap
    total -= gap
    cy = y
    for (tw, th), line in zip(sizes, lines):
        draw.text((cx - tw / 2, cy), line, font=fnt, fill=fill)
        cy += th + gap
    return cy


def arrow_down(draw, x, y0, y1, color=MUTED):
    draw.line((x, y0, x, y1 - 8), fill=color, width=3)
    draw.polygon([(x - 7, y1 - 10), (x + 7, y1 - 10), (x, y1)], fill=color)


def arrow_right(draw, x0, y, x1, color=MUTED):
    draw.line((x0, y, x1 - 8, y), fill=color, width=3)
    draw.polygon([(x1 - 10, y - 7), (x1 - 10, y + 7), (x1, y)], fill=color)


def box(
    draw,
    x,
    y,
    w,
    h,
    title,
    subtitle=None,
    fill=WHITE,
    outline=LINE,
    title_color=SLATE,
    badge=None,
    badge_fill=STAPLES_RED,
):
    rounded(draw, (x, y, x + w, y + h), fill=fill, outline=outline, radius=16, width=2)
    f_title = font(20, bold=True)
    f_sub = font(14)
    f_badge = font(12, bold=True)
    if badge:
        bb = draw.textbbox((0, 0), badge, font=f_badge)
        bw, bh = bb[2] - bb[0] + 16, bb[3] - bb[1] + 8
        bx, by = x + 14, y + 12
        rounded(draw, (bx, by, bx + bw, by + bh), fill=badge_fill, outline=None, radius=8)
        draw.text((bx + 8, by + 3), badge, font=f_badge, fill=WHITE)
        ty = by + bh + 8
    else:
        ty = y + 16
    draw.text((x + 16, ty), title, font=f_title, fill=title_color)
    if subtitle:
        draw.text((x + 16, ty + 28), subtitle, font=f_sub, fill=MUTED)
    return (x, y, x + w, y + h)


def main() -> None:
    W, H = 2200, 2800
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # Header bar
    rounded(draw, (40, 40, W - 40, 180), fill=WHITE, outline=LINE, radius=20, width=2)
    draw.rectangle((40, 40, 56, 180), fill=STAPLES_RED)
    draw.text((80, 62), "Staples / Coastwide Marketplace Image Studio", font=font(36, True), fill=SLATE)
    draw.text(
        (80, 112),
        "Complete workflow — how a product click becomes a compliant image stack",
        font=font(20),
        fill=MUTED,
    )
    # brand chips
    for label, color, bx in [("Staples #E42A11", STAPLES_RED, W - 420), ("Coastwide #FF8200", COASTWIDE_ORANGE, W - 220)]:
        rounded(draw, (bx, 90, bx + 160, 130), fill=color, outline=None, radius=10)
        center_text(draw, (bx, 90, bx + 160, 130), label.split()[0], font(14, True), WHITE)

    # ── Phase 1: UI entry ──────────────────────────────────────────────
    y = 220
    draw.text((80, y), "1 · DEMO UI", font=font(16, True), fill=STAPLES_RED)
    y = 250
    box(
        draw,
        80,
        y,
        640,
        110,
        "Landing page — four product cards",
        "ExpressMop · Power Cleaner · ProGel · Hyken",
        fill=WHITE,
        outline=STAPLES_RED,
        badge="USER",
        badge_fill=STAPLES_RED,
    )
    box(
        draw,
        780,
        y,
        620,
        110,
        "Click a card  →  POST /api/jobs",
        '{ "sku": "24639471" }  — no upload, no form, no settings',
        fill=ACCENT_BG,
        outline=STAPLES_RED,
        badge="API",
        badge_fill=SLATE,
    )
    box(
        draw,
        1460,
        y,
        660,
        110,
        "Poll GET /api/jobs/{id} every 1.5s",
        "Checklist ticks as each shot finishes → zip download",
        fill=SOFT,
        outline=LINE,
        badge="UI",
        badge_fill=MUTED,
    )
    arrow_right(draw, 720, y + 55, 780)
    arrow_right(draw, 1400, y + 55, 1460)

    # ── Phase 2: Orchestrator ──────────────────────────────────────────
    y = 410
    draw.text((80, y), "2 · ORCHESTRATOR", font=font(16, True), fill=STAPLES_RED)
    y = 440
    box(
        draw,
        80,
        y,
        2040,
        130,
        "Load SKU config  →  create Job (queued→running)  →  spawn concurrent shots (max 3)",
        "Config from _DEV_HANDOFF/config  ·  Rulesets Staples / Coastwide  ·  6–8 shots per SKU  ·  Artifacts → outputs/{sku}/_MOCK|run/{job_id}/",
        fill=WHITE,
        outline=LINE,
        badge="JOB",
        badge_fill=COASTWIDE_ORANGE,
    )
    arrow_down(draw, W // 2, y + 130, y + 170)

    # ── Phase 3: Shot-type router ──────────────────────────────────────
    y = 630
    draw.text((80, y), "3 · SHOT-TYPE ROUTER  (dispatch on shot.type)", font=font(16, True), fill=STAPLES_RED)
    y = 665

    types = [
        ("hero_passthrough", "Recompose real hero\nonto pure white square", "No model calls", BLUE_BG, (80, y)),
        ("graphic_only", "Claude HTML/SVG → lint\n→ rasterize → scale", "No photo / no gate", ORANGE_BG, (480, y)),
        ("graphic + tiles", "Nano Banana tile sheet\n→ Claude graphic path", "No fidelity gate", ORANGE_BG, (880, y)),
        ("photo_overlay", "Generate → gate → overlay\n→ lint → composite → scale", "Main path (most shots)", ACCENT_BG, (1280, y)),
        ("photo_only", "Generate → gate → scale\nPhoto IS the finish", "No Claude overlay", GREEN_BG, (1680, y)),
    ]
    f_t = font(16, True)
    f_b = font(13)
    for title, body, note, fill, (x, top) in types:
        w, h = 360, 150
        rounded(draw, (x, top, x + w, top + h), fill=fill, outline=LINE, radius=14, width=2)
        draw.text((x + 16, top + 14), title, font=f_t, fill=SLATE)
        for i, line in enumerate(body.split("\n")):
            draw.text((x + 16, top + 44 + i * 20), line, font=f_b, fill=CHARCOAL)
        draw.text((x + 16, top + 110), note, font=font(12, True), fill=MUTED)

    # Highlight photo_overlay as primary
    draw.text(
        (1280, y + 158),
        "▼ Primary path detailed below",
        font=font(14, True),
        fill=STAPLES_RED,
    )

    # ── Phase 4: Primary path detail ───────────────────────────────────
    y = 880
    draw.text((80, y), "4 · PHOTO_OVERLAY PIPELINE  (the four real-work steps)", font=font(16, True), fill=STAPLES_RED)
    y = 920

    steps = [
        (
            "01",
            "Nano Banana",
            "Higgsfield /nano-banana",
            "Generate scene from hero\nreference photo.\nLeave one corner empty\nfor brand text.",
            ACCENT_BG,
            STAPLES_RED,
        ),
        (
            "02",
            "Gemini Gate",
            "Gemini Pro vision",
            "Is this still the right\nproduct? Sensible setting?\nNo stray logos?\nRetry once → else flag.",
            BLUE_BG,
            (40, 100, 160),
        ),
        (
            "03",
            "Claude Overlay",
            "Claude + brand ruleset",
            "Sees the real photo.\nPlaces approved copy in\nthe empty corner.\nOutputs HTML / SVG.",
            ORANGE_BG,
            COASTWIDE_ORANGE,
        ),
        (
            "04",
            "Lint → Composite",
            "Claim lint + Pillow",
            "Validate claims & brand.\nRasterize overlay PNG.\nComposite onto photo.\nScale to 2000² square.",
            GREEN_BG,
            (40, 130, 90),
        ),
    ]
    sx = 80
    for i, (num, title, model, body, fill, accent) in enumerate(steps):
        w, h = 460, 240
        rounded(draw, (sx, y, sx + w, y + h), fill=WHITE, outline=accent, radius=18, width=3)
        rounded(draw, (sx + 16, y + 16, sx + 70, y + 70), fill=accent, outline=None, radius=12)
        center_text(draw, (sx + 16, y + 16, sx + 70, y + 70), num, font(22, True), WHITE)
        draw.text((sx + 86, y + 22), title, font=font(24, True), fill=SLATE)
        draw.text((sx + 86, y + 54), model, font=font(14), fill=MUTED)
        rounded(draw, (sx + 16, y + 90, sx + w - 16, y + h - 16), fill=fill, outline=None, radius=12)
        for j, line in enumerate(body.split("\n")):
            draw.text((sx + 32, y + 104 + j * 26), line, font=font(16), fill=CHARCOAL)
        if i < len(steps) - 1:
            arrow_right(draw, sx + w + 4, y + h // 2, sx + w + 40, accent)
        sx += w + 50

    # Mock mode callout
    y = 1200
    rounded(draw, (80, y, W - 80, y + 90), fill=YELLOW_BG, outline=COASTWIDE_ORANGE, radius=16, width=2)
    draw.text((110, y + 18), "MOCK MODE (default)", font=font(18, True), fill=COASTWIDE_ORANGE)
    draw.text(
        (110, y + 48),
        "No API keys needed. Nano Banana returns watermarked acceptance-reference images · Gemini always PASS · Claude returns fixture HTML. "
        "Orchestrator, lint, composite, API, UI, and zip all run for real.",
        font=font(15),
        fill=CHARCOAL,
    )

    # ── Phase 5: Outputs ───────────────────────────────────────────────
    y = 1330
    draw.text((80, y), "5 · OUTPUTS & PACKAGE", font=font(16, True), fill=STAPLES_RED)
    y = 1365

    outs = [
        ("Per-shot artifacts", "raw_attempt · overlay.html/png\ncomposite.png · thumbnails", SOFT),
        ("Render targets", "RT_MAIN_WHITE (hero)\nRT_SECONDARY_SQUARE 2000²", BLUE_BG),
        ("manifest.json", "Statuses · gate verdicts · lint\nplaceholder strings · flags", ORANGE_BG),
        ("Zip package", "GET /api/jobs/{id}/package\nFinished images + README", GREEN_BG),
    ]
    ox = 80
    for title, body, fill in outs:
        w, h = 480, 130
        rounded(draw, (ox, y, ox + w, y + h), fill=fill, outline=LINE, radius=14, width=2)
        draw.text((ox + 20, y + 18), title, font=font(20, True), fill=SLATE)
        for j, line in enumerate(body.split("\n")):
            draw.text((ox + 20, y + 56 + j * 24), line, font=font(15), fill=CHARCOAL)
        if ox < 1520:
            arrow_right(draw, ox + w + 6, y + h // 2, ox + w + 40)
        ox += w + 50

    # ── Phase 6: Hard rules ────────────────────────────────────────────
    y = 1550
    draw.text((80, y), "6 · THREE HARD RULES", font=font(16, True), fill=STAPLES_RED)
    y = 1585
    rules = [
        ("1", "Never invent product copy", "Every word traces to APPROVED,\nPUBLISHED_ART, or declared\nPLACEHOLDER_POC. No invented\nnumbers, claims, or certs."),
        ("2", "Never cover the product", "Style guides forbid text on\nthe product. Empty-corner\nprompt + vision overlay\nplacement enforce this."),
        ("3", "Never pass off Staples art", "Production references are for\nside-by-side comparison only.\nMock outputs stay watermarked\nand under outputs/.../_MOCK/."),
    ]
    rx = 80
    for num, title, body in rules:
        w, h = 660, 200
        rounded(draw, (rx, y, rx + w, y + h), fill=WHITE, outline=STAPLES_RED, radius=16, width=2)
        rounded(draw, (rx + 20, y + 20, rx + 70, y + 70), fill=STAPLES_RED, outline=None, radius=12)
        center_text(draw, (rx + 20, y + 20, rx + 70, y + 70), num, font(24, True), WHITE)
        draw.text((rx + 90, y + 28), title, font=font(22, True), fill=SLATE)
        for j, line in enumerate(body.split("\n")):
            draw.text((rx + 90, y + 72 + j * 26), line, font=font(16), fill=CHARCOAL)
        rx += w + 40

    # ── Status legend ──────────────────────────────────────────────────
    y = 1840
    draw.text((80, y), "7 · SHOT STATUS MACHINE", font=font(16, True), fill=STAPLES_RED)
    y = 1875
    statuses = [
        ("pending", "Waiting"),
        ("generating_scene", "Generating"),
        ("checking", "Checking"),
        ("designing_overlay", "Brand layer"),
        ("rendering", "Drawing"),
        ("compositing", "Compositing"),
        ("scaling", "Sizing"),
        ("done", "Done"),
        ("needs_review", "Review"),
        ("failed", "Failed"),
    ]
    sx = 80
    for key, label in statuses:
        fill = GREEN_BG if key == "done" else YELLOW_BG if key == "needs_review" else ACCENT_BG if key == "failed" else WHITE
        outline = (40, 130, 90) if key == "done" else COASTWIDE_ORANGE if key == "needs_review" else STAPLES_RED if key == "failed" else LINE
        w = 190
        rounded(draw, (sx, y, sx + w, y + 70), fill=fill, outline=outline, radius=12, width=2)
        center_text(draw, (sx, y, sx + w, y + 40), label, font(14, True), SLATE)
        center_text(draw, (sx, y + 28, sx + w, y + 62), key, font(11), MUTED)
        if sx < 1900:
            draw.line((sx + w + 2, y + 35, sx + w + 18, y + 35), fill=MUTED, width=2)
        sx += w + 22

    # ── Architecture strip ─────────────────────────────────────────────
    y = 2010
    draw.text((80, y), "8 · APP ARCHITECTURE", font=font(16, True), fill=STAPLES_RED)
    y = 2045
    arch = [
        ("app/main.py", "FastAPI routes"),
        ("loader.py", "Config at boot"),
        ("orchestrator.py", "Jobs + concurrency"),
        ("pipeline/", "hero · router\ncompose · lint"),
        ("adapters/", "mock + live\nnano / Gemini / Claude"),
        ("static/", "Brand-styled UI"),
        ("_DEV_HANDOFF/", "Configs · prompts\nrulesets · refs"),
    ]
    ax = 80
    for title, body in arch:
        w, h = 280, 120
        rounded(draw, (ax, y, ax + w, y + h), fill=SOFT, outline=LINE, radius=12, width=2)
        draw.text((ax + 16, y + 16), title, font=font(16, True), fill=STAPLES_RED)
        for j, line in enumerate(body.split("\n")):
            draw.text((ax + 16, y + 50 + j * 22), line, font=font(14), fill=CHARCOAL)
        ax += w + 20

    # Footer
    y = 2220
    rounded(draw, (80, y, W - 80, y + 120), fill=WHITE, outline=LINE, radius=16, width=2)
    draw.text((110, y + 24), "End-to-end loop", font=font(20, True), fill=SLATE)
    draw.text(
        (110, y + 60),
        "Card click  →  Job  →  Concurrent shots (by type)  →  Models / mock adapters  →  Lint & composite  →  "
        "Results grid + side-by-side refs  →  Zip package",
        font=font(16),
        fill=CHARCOAL,
    )
    draw.text(
        (110, y + 90),
        "Source of truth: _DEV_HANDOFF/00_START_HERE.md · 01_BUILD_INSTRUCTIONS.md · app/pipeline/router.py",
        font=font(13),
        fill=MUTED,
    )

    # Trim unused bottom whitespace by cropping to content
    # Keep a clean margin
    cropped = img.crop((0, 0, W, 2400))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(OUT, format="PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

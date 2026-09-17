"""Hero passthrough and image helpers."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def open_rgb(path: Path) -> Image.Image:
    """Open PNG/JPG/PSD flattened composite as RGB."""
    img = Image.open(path)
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def product_bbox(img: Image.Image, white_thresh: int = 248) -> tuple[int, int, int, int]:
    """Bounding box of non-near-white pixels."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    pixels = rgb.load()
    min_x, min_y, max_x, max_y = w, h, 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            if r < white_thresh or g < white_thresh or b < white_thresh:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if not found:
        return (0, 0, w, h)
    return (min_x, min_y, max_x + 1, max_y + 1)


def hero_passthrough(
    hero_path: Path,
    out_path: Path,
    canvas: int = 2400,
    fill_min: float = 0.85,
    png_fallback: Path | None = None,
) -> dict:
    """Recompose hero onto pure-white RT_MAIN_WHITE canvas."""
    try:
        src = open_rgb(hero_path)
        used_fallback = False
    except Exception:
        if not png_fallback or not png_fallback.exists():
            raise
        src = open_rgb(png_fallback)
        used_fallback = True

    box = product_bbox(src)
    product = src.crop(box)
    pw, ph = product.size
    longest = max(pw, ph)
    target = int(canvas * fill_min)
    scale = target / longest if longest else 1.0
    new_size = (max(1, int(pw * scale)), max(1, int(ph * scale)))
    product = product.resize(new_size, Image.LANCZOS)

    canvas_img = Image.new("RGB", (canvas, canvas), (255, 255, 255))
    ox = (canvas - product.size[0]) // 2
    oy = (canvas - product.size[1]) // 2
    canvas_img.paste(product, (ox, oy))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas_img.save(out_path, "PNG")
    return {
        "scale_factor": round(scale, 4),
        "used_fallback": used_fallback,
        "product_bbox": list(box),
        "output_size": [canvas, canvas],
    }


def ensure_thumbnail(
    source: Path,
    dest: Path,
    size: int = 640,
    png_fallback: Path | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return dest
    try:
        img = open_rgb(source)
    except Exception:
        if png_fallback and png_fallback.exists():
            img = open_rgb(png_fallback)
        else:
            raise
    img.thumbnail((size, size), Image.LANCZOS)
    square = Image.new("RGB", (size, size), (255, 255, 255))
    ox = (size - img.size[0]) // 2
    oy = (size - img.size[1]) // 2
    square.paste(img, (ox, oy))
    square.save(dest, "PNG")
    return dest

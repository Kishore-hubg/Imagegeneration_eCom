"""Lightweight claim / brand lint for Stage 0."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any


def overlay_html_is_complete(html: str) -> tuple[bool, str]:
    """
    Return (ok, reason). Catches truncated Claude responses that still pass palette lint
    (e.g. mid-SVG cutoffs that paint leader lines with no labels).
    """
    text = (html or "").strip()
    if not text:
        return False, "empty HTML"
    lower = text.lower()
    if "<html" not in lower:
        return False, "missing <html>"
    if "</html>" not in lower:
        return False, "missing </html> (likely truncated)"
    if "<body" in lower and "</body>" not in lower:
        return False, "missing </body> (likely truncated)"
    stripped = text.rstrip()
    if stripped.endswith(("=", '"', "'", "<", "/", ",")) or re.search(
        r"<(?:circle|path|rect|text|div|span|p)\b[^>]*$", stripped
    ):
        return False, "HTML appears cut mid-tag"
    # Empty shell like <body></body> is not a valid overlay for any product
    body_m = re.search(r"<body[^>]*>(.*)</body>", text, flags=re.I | re.S)
    if body_m is not None:
        body_inner = re.sub(r"<[^>]+>", " ", body_m.group(1))
        body_inner = re.sub(r"\s+", " ", body_inner).strip()
        if len(body_inner) < 8:
            return False, "empty <body> — no visible text content"
    return True, "OK"


def lint_overlay_markup(
    html: str,
    shot: dict[str, Any],
    ruleset: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    provenance = str(shot.get("text_provenance", ""))

    ok, reason = overlay_html_is_complete(html)
    if not ok:
        results.append(
            {
                "check": "html_complete",
                "status": "FAIL",
                "detail": reason,
            }
        )

    missing = _missing_approved_strings(html, shot.get("overlay_text") or {})
    for item in missing:
        results.append(
            {
                "check": "approved_text_present",
                "status": "FAIL",
                "detail": f"Approved string not found in overlay HTML: {item!r}",
            }
        )

    # Palette check — brand UI colors must be in ruleset.
    # Decorative SVG fills (flooring swatches, texture tiles) are exempt.
    allowed = _palette_hexes(ruleset)
    allowed.update({"#000000", "#FFFFFF", "#EEEEEE", "#D9D9D9"})
    skip_palette = shot.get("type") == "graphic_only_with_generated_tiles"
    if not skip_palette:
        for hx in set(re.findall(r"#[0-9A-Fa-f]{6}", html)):
            if hx.upper() not in allowed:
                results.append(
                    {
                        "check": "palette",
                        "status": "FAIL",
                        "detail": f"Hex {hx} not in ruleset palette",
                    }
                )

    if "gradient" in html.lower():
        results.append(
            {
                "check": "no_gradients",
                "status": "FAIL",
                "detail": "Gradient usage is prohibited by brand rules",
            }
        )

    if provenance.startswith("PLACEHOLDER_POC"):
        results.append(
            {
                "check": "placeholder_declared",
                "status": "PASS",
                "detail": "Placeholder copy is declared in shot config",
            }
        )

    if not any(r.get("status") == "FAIL" for r in results):
        results.append({"check": "overlay_lint", "status": "PASS", "detail": "OK"})
    return results


def _missing_approved_strings(html: str, overlay_text: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    # Strip tags so "label<br>text" still matches approved "label text"
    # Unescape entities so "Tilt &amp; tension" matches approved "Tilt & tension"
    hay = html_lib.unescape(html or "")
    hay = re.sub(r"<[^>]+>", " ", hay)
    hay = _fold_approved_text(hay)

    def need(value: str | None) -> None:
        if not value:
            return
        compact = re.sub(r"\s+", " ", str(value)).strip()
        if not compact or len(compact) < 2:
            return
        if _fold_approved_text(compact) in hay:
            return
        missing.append(compact)

    # Prefer resolved_* when present (Power Cleaner-style decisions)
    need(overlay_text.get("resolved_headline") or overlay_text.get("headline"))
    need(overlay_text.get("headline_line_2"))
    need(overlay_text.get("resolved_footnote"))
    need(overlay_text.get("sub_headline") or overlay_text.get("subhead"))
    need(overlay_text.get("body"))
    need(overlay_text.get("disclaimer"))
    for item in overlay_text.get("items") or []:
        if isinstance(item, dict):
            need(item.get("label"))
            need(item.get("count"))
            need(item.get("value"))
    need(overlay_text.get("supporting_line"))
    for callout in overlay_text.get("callouts") or []:
        if isinstance(callout, dict):
            need(callout.get("label"))
            need(callout.get("value"))
        elif isinstance(callout, str):
            need(callout)
    for benefit in overlay_text.get("benefits") or []:
        if isinstance(benefit, dict):
            need(benefit.get("title"))
            need(benefit.get("body"))
    for swatch in overlay_text.get("swatches") or []:
        if isinstance(swatch, str):
            need(swatch)
    for step in overlay_text.get("steps") or []:
        if isinstance(step, dict):
            need(step.get("caption"))
            need(step.get("number"))
    return missing


def _fold_approved_text(text: str) -> str:
    """Normalize for approved-string presence checks across product copy styles."""
    s = html_lib.unescape(text or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[“”\"'`´]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _palette_hexes(ruleset: dict[str, Any]) -> set[str]:
    found: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "hex" in obj and isinstance(obj["hex"], str):
                found.add(obj["hex"].upper())
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for i in obj:
                walk(i)

    walk(ruleset.get("palette", {}))
    walk(ruleset.get("infographic_palette", {}))
    return found

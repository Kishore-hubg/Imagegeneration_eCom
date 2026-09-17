"""Live provider adapters — Higgsfield / Gemini / Claude."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

_HTML_FENCE = re.compile(r"^```(?:html)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


@dataclass
class SceneResult:
    """Which provider actually produced a scene, so the manifest can say so."""

    path: Path
    provider: str
    model: str
    notes: list[str] = field(default_factory=list)
    reference_count: int = 0

    @property
    def is_higgsfield(self) -> bool:
        return self.provider == "higgsfield"


class HiggsfieldError(RuntimeError):
    """A Higgsfield API failure, classified so callers can react correctly.

    kind is one of:
      auth        — bad or missing credentials. Config error, never retry.
      credits     — account has no API credit balance. Fund it, never retry.
      unavailable — model not provisioned/blocked/disabled for this account.
                    Try the next model in the chain, never retry this one.
      validation  — our request body is wrong. Code bug, never retry.
      transient   — rate limit, 5xx or network. Retry with backoff.
      generation  — accepted but finished failed/nsfw/canceled.
    """

    RETRYABLE = {"transient"}
    TRY_NEXT_MODEL = {"unavailable", "generation"}

    def __init__(self, kind: str, message: str, *, status: int | None = None, model: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.model = model

    @property
    def retryable(self) -> bool:
        return self.kind in self.RETRYABLE

    @property
    def try_next_model(self) -> bool:
        return self.kind in self.TRY_NEXT_MODEL


_STATUS_KIND = {
    400: "validation",
    401: "auth",
    403: "credits",
    404: "unavailable",
    422: "validation",
    423: "unavailable",
    429: "transient",
    503: "unavailable",
}


def _classify(status: int, detail: str, model: str | None = None) -> HiggsfieldError:
    kind = _STATUS_KIND.get(status) or ("transient" if status >= 500 else "validation")
    # Higgsfield returns a FastAPI envelope; the machine-readable token is in `detail`.
    if "not_enough_credits" in detail:
        kind = "credits"
    elif "model_not_found" in detail or "model_disabled" in detail or "model_blocked" in detail:
        kind = "unavailable"
    return HiggsfieldError(
        kind, f"HTTP {status} on {model or '?'}: {detail[:300]}", status=status, model=model
    )


def _auth_headers() -> dict[str, str]:
    s = get_settings()
    return {
        "Authorization": f"Key {s.higgsfield_api_key}:{s.higgsfield_api_secret}",
        "Content-Type": "application/json",
    }


# Aspect ratio enums differ per model; sending an unsupported value is a 422.
_ASPECT_SUPPORT = {
    "/nano-banana": {"auto", "1:1", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "16:9", "9:16", "21:9"},
    "/higgsfield-ai/soul/standard": {"1:1", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "16:9", "9:16", "21:9"},
    "/higgsfield-ai/soul/reference": {"1:1", "4:3", "3:4", "3:2", "2:3", "16:9", "9:16"},
    "/higgsfield-ai/soul/character": {"1:1", "4:3", "3:4", "3:2", "2:3", "16:9", "9:16"},
}

_ASPECT_ALIASES = {
    "5:4": ["5:4", "4:3", "1:1"],
    "4:5": ["4:5", "3:4", "1:1"],
    "21:9": ["21:9", "16:9"],
}


def _clamp_aspect(model: str, aspect: str) -> str:
    supported = _ASPECT_SUPPORT.get(model)
    aspect = (aspect or "1:1").strip()
    if not supported:
        return aspect
    for candidate in _ASPECT_ALIASES.get(aspect, [aspect]):
        if candidate in supported:
            return candidate
    return "1:1" if "1:1" in supported else sorted(supported)[0]


def _build_body(model: str, *, prompt: str, aspect_ratio: str, image_urls: list[str]) -> dict[str, Any]:
    """Per-model request body. Each model has a different, non-interchangeable schema."""
    aspect = _clamp_aspect(model, aspect_ratio)

    if model == "/nano-banana":
        body: dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": aspect,
            "output_format": "png",
            "num_images": 1,
        }
        if image_urls:
            # Schema requires objects, not bare URL strings, and forbids extra keys.
            body["input_images"] = [
                {"type": "image_url", "image_url": u}
                for u in image_urls[: get_settings().higgsfield_max_input_images]
            ]
        return body

    if model.endswith("/soul/reference") or model.endswith("/soul/character"):
        if not image_urls:
            raise HiggsfieldError(
                "validation",
                f"{model} requires image_reference_url but no reference uploaded",
                model=model,
            )
        return {
            "prompt": prompt,
            "image_reference_url": image_urls[0],
            "aspect_ratio": aspect,
            "resolution": "1080p",
            "enhance_prompt": False,
            "batch_size": 1,
        }

    if model.endswith("/soul/standard"):
        # The published OpenAPI spec declares resolution as 2K/4K here, but the
        # live API rejects those and only accepts 720p/1080p (verified 2026-09-17
        # via scripts/probe_soul_body.py).
        return {
            "prompt": prompt,
            "aspect_ratio": aspect,
            "resolution": "1080p",
            "num_images": 1,
        }

    return {"prompt": prompt, "aspect_ratio": aspect}


def _image_to_jpeg_bytes(path: Path, max_side: int = 1536) -> tuple[bytes, str]:
    """Load PSD/PNG/JPEG and return JPEG bytes + mime."""
    try:
        img = Image.open(path)
    except Exception:
        raise
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"


def _image_to_png_bytes(path: Path, max_side: int = 1536) -> bytes:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _upload_higgsfield(client: httpx.AsyncClient, path: Path) -> str:
    """Upload local image; return public_url for model input.

    Raises HiggsfieldError on failure. A silently dropped reference produces a
    scene with no product in it, which is worse than a failed shot.
    """
    s = get_settings()
    base = s.higgsfield_api_base_url.rstrip("/")
    data, mime = _image_to_jpeg_bytes(path)
    r = await client.post(
        f"{base}/files/generate-upload-url",
        headers=_auth_headers(),
        json={"content_type": mime},
    )
    if r.status_code >= 400:
        raise _classify(r.status_code, r.text, "/files/generate-upload-url")
    payload = r.json()
    # Presigned storage URL — must carry every returned header, and never our credentials.
    headers = dict(payload.get("upload_headers") or {"Content-Type": mime})
    put = await client.put(payload["upload_url"], content=data, headers=headers)
    if put.status_code >= 400:
        raise HiggsfieldError(
            "transient",
            f"Presigned PUT failed ({put.status_code}) for {path.name}: {put.text[:200]}",
            status=put.status_code,
        )
    return payload["public_url"]


async def _poll_higgsfield(client: httpx.AsyncClient, status_url: str, model: str) -> dict[str, Any]:
    s = get_settings()
    interval = float(getattr(s, "higgsfield_poll_interval_seconds", 3) or 3)
    timeout = float(getattr(s, "higgsfield_poll_timeout_seconds", 300) or 300)
    elapsed = 0.0
    consecutive_errors = 0
    while elapsed < timeout:
        try:
            r = await client.get(status_url, headers=_auth_headers())
        except httpx.HTTPError as exc:
            consecutive_errors += 1
            if consecutive_errors > 5:
                raise HiggsfieldError("transient", f"Status polling kept failing: {exc}", model=model)
            await asyncio.sleep(interval)
            elapsed += interval
            continue

        # Docs: retry GET status on 5xx rather than abandoning a paid job.
        if r.status_code >= 500:
            consecutive_errors += 1
            if consecutive_errors > 5:
                raise HiggsfieldError(
                    "transient", f"Status endpoint 5xx x{consecutive_errors}", status=r.status_code, model=model
                )
            await asyncio.sleep(interval)
            elapsed += interval
            continue
        if r.status_code >= 400:
            raise _classify(r.status_code, r.text, model)

        consecutive_errors = 0
        body = r.json()
        status = str(body.get("status", "")).lower()
        if status in {"completed", "failed", "nsfw", "canceled", "cancelled"}:
            return body
        await asyncio.sleep(interval)
        elapsed += interval
    raise HiggsfieldError(
        "transient", f"Poll timed out after {timeout:.0f}s: {status_url}", model=model
    )


async def _submit_higgsfield(
    client: httpx.AsyncClient,
    *,
    model: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """POST one model, retrying only genuinely transient failures."""
    s = get_settings()
    base = s.higgsfield_api_base_url.rstrip("/")
    attempts = max(1, s.higgsfield_max_retries)
    last: HiggsfieldError | None = None

    for attempt in range(1, attempts + 1):
        try:
            r = await client.post(f"{base}{model}", headers=_auth_headers(), json=body)
        except httpx.HTTPError as exc:
            last = HiggsfieldError("transient", f"Network error on {model}: {exc}", model=model)
        else:
            if r.status_code < 400:
                return r.json()
            last = _classify(r.status_code, r.text, model)
            # Submissions take no idempotency key, so only retry when the server
            # clearly never accepted the job.
            if not last.retryable:
                raise last

        if attempt < attempts:
            backoff = min(2 ** attempt, 20) + random.uniform(0, 1)
            logger.info(
                "Higgsfield %s transient failure (attempt %d/%d), retrying in %.1fs",
                model,
                attempt,
                attempts,
                backoff,
            )
            await asyncio.sleep(backoff)

    raise last or HiggsfieldError("transient", f"{model} exhausted retries", model=model)


async def _run_higgsfield_model(
    client: httpx.AsyncClient,
    *,
    model: str,
    prompt: str,
    aspect_ratio: str,
    image_urls: list[str],
    out_path: Path,
) -> Path:
    s = get_settings()
    base = s.higgsfield_api_base_url.rstrip("/")

    body = _build_body(model, prompt=prompt, aspect_ratio=aspect_ratio, image_urls=image_urls)
    queued = await _submit_higgsfield(client, model=model, body=body)

    status_url = queued.get("status_url")
    if not status_url and queued.get("request_id"):
        status_url = f"{base}/requests/{queued['request_id']}/status"
    if not status_url:
        raise HiggsfieldError(
            "validation", f"Response missing status_url: {json.dumps(queued)[:200]}", model=model
        )

    final = await _poll_higgsfield(client, status_url, model)
    status = str(final.get("status", "")).lower()
    if status != "completed":
        raise HiggsfieldError(
            "generation",
            f"{model} ended as {status}: {final.get('error') or ''}",
            model=model,
        )

    images = final.get("images") or final.get("output") or []
    url = None
    if isinstance(images, list) and images:
        first = images[0]
        url = first.get("url") if isinstance(first, dict) else first
    if not url:
        raise HiggsfieldError(
            "generation", f"{model} completed with no image URL", model=model
        )

    # Output URLs expire after 7 days — land it on disk immediately.
    img_resp = await client.get(url)
    if img_resp.status_code >= 400:
        raise HiggsfieldError(
            "transient", f"Could not download output ({img_resp.status_code})", model=model
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(img_resp.content)
    Image.open(out_path).convert("RGB").save(out_path, "PNG")
    return out_path


async def _generate_higgsfield(
    *,
    prompt: str,
    input_image_paths: list[Path],
    aspect_ratio: str,
    out_path: Path,
) -> SceneResult:
    """Walk the configured model chain; first model to deliver wins."""
    s = get_settings()
    if not s.higgsfield_configured:
        raise HiggsfieldError("auth", "HIGGSFIELD_API_KEY / HIGGSFIELD_API_SECRET not set")

    chain = s.higgsfield_models
    notes: list[str] = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        image_urls: list[str] = []
        wanted = [Path(p) for p in input_image_paths if p and Path(p).exists()]
        for p in wanted[: s.higgsfield_max_input_images]:
            image_urls.append(await _upload_higgsfield(client, p))
        if wanted and not image_urls:
            raise HiggsfieldError("transient", "All product reference uploads failed")

        last: HiggsfieldError | None = None
        for model in chain:
            try:
                path = await _run_higgsfield_model(
                    client,
                    model=model,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_urls=image_urls,
                    out_path=out_path,
                )
            except HiggsfieldError as exc:
                last = exc
                if exc.kind in {"auth", "credits"}:
                    # Account-level; every other model will fail identically.
                    raise
                notes.append(f"{model}: {exc.kind} — {exc}")
                logger.warning("Higgsfield %s unusable (%s); trying next model", model, exc.kind)
                continue

            if model.endswith("/soul/standard") and image_urls:
                notes.append(
                    "Scene generated without product references — soul/standard is "
                    "prompt-only. Product likeness is not grounded."
                )
            logger.info("Scene generated via Higgsfield %s -> %s", model, out_path)
            return SceneResult(
                path=path,
                provider="higgsfield",
                model=model,
                notes=notes,
                reference_count=len(image_urls) if not model.endswith("/soul/standard") else 0,
            )

    raise last or HiggsfieldError("unavailable", f"No usable Higgsfield model in chain: {chain}")


async def probe_higgsfield() -> dict[str, Any]:
    """Preflight the model chain so the operator learns at boot, not mid-demo."""
    s = get_settings()
    if not s.higgsfield_configured:
        return {"available": False, "reason": "credentials not set", "models": {}}

    base = s.higgsfield_api_base_url.rstrip("/")
    models: dict[str, str] = {}
    available: list[str] = []
    reason = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        for model in s.higgsfield_models:
            probe = _build_body(
                model, prompt="probe", aspect_ratio="1:1", image_urls=["https://example.com/p.jpg"]
            ) if model.endswith(("/soul/reference", "/soul/character")) else _build_body(
                model, prompt="probe", aspect_ratio="1:1", image_urls=[]
            )
            try:
                r = await client.post(f"{base}{model}", headers=_auth_headers(), json=probe)
            except httpx.HTTPError as exc:
                models[model] = f"unreachable: {exc}"
                continue
            if r.status_code < 400:
                models[model] = "available"
                available.append(model)
                if r.json().get("cancel_url"):
                    try:
                        await client.post(r.json()["cancel_url"], headers=_auth_headers())
                    except httpx.HTTPError:
                        pass
                continue
            err = _classify(r.status_code, r.text, model)
            models[model] = f"{err.kind} ({r.status_code})"
            if err.kind in {"auth", "credits"}:
                reason = err.kind

    return {
        "available": bool(available),
        "usable_models": available,
        "models": models,
        "reason": reason or (None if available else "no model in chain is provisioned"),
    }


async def _generate_gemini_image(
    *,
    prompt: str,
    input_image_paths: list[Path],
    out_path: Path,
) -> Path:
    """Fallback image generation via Gemini (used when Higgsfield has no credits/model)."""
    s = get_settings()
    if not s.gemini_api_key:
        raise RuntimeError("Gemini fallback unavailable: GEMINI_API_KEY not set")
    model = getattr(s, "gemini_image_model", None) or "nano-banana-pro-preview"
    parts: list[dict[str, Any]] = [{"text": prompt or "Clean e-commerce product photograph, no text overlay."}]
    for p in input_image_paths[:4]:
        if not p or not Path(p).exists():
            continue
        try:
            data, mime = _image_to_jpeg_bytes(Path(p), max_side=1280)
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
        except Exception:
            logger.exception("Could not attach input image %s", p)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(url, params={"key": s.gemini_api_key}, json=payload)
    body = r.json()
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini image gen failed ({r.status_code}): {(body.get('error') or {}).get('message') or r.text[:300]}")

    raw = None
    for part in body.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            raw = base64.b64decode(inline["data"])
            break
    if not raw:
        raise RuntimeError(f"Gemini image gen returned no image: {json.dumps(body)[:400]}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)
    Image.open(out_path).convert("RGB").save(out_path, "PNG")
    logger.info("Scene generated via Gemini fallback model=%s -> %s", model, out_path)
    return out_path


async def generate_scene(
    *,
    prompt: str,
    input_image_paths: list[Path],
    aspect_ratio: str,
    out_path: Path,
) -> SceneResult:
    """Higgsfield first; Gemini only when Higgsfield genuinely cannot serve.

    The old version caught every exception at WARNING and fell through, so a
    permanent misconfiguration looked identical to a transient blip and a whole
    run could silently ship Gemini output. Configuration and account faults are
    now surfaced as errors and, when HIGGSFIELD_REQUIRED is set, they stop the shot.
    """
    s = get_settings()
    try:
        return await _generate_higgsfield(
            prompt=prompt,
            input_image_paths=input_image_paths,
            aspect_ratio=aspect_ratio,
            out_path=out_path,
        )
    except HiggsfieldError as exc:
        if exc.kind == "auth":
            logger.error(
                "Higgsfield credentials rejected (%s). Regenerate the key/secret pair at "
                "https://cloud.higgsfield.ai/ — this is a configuration fault, not a transient error.",
                exc,
            )
        elif exc.kind == "credits":
            logger.error(
                "Higgsfield has no API credit balance (%s). API credits are billed separately "
                "from a Higgsfield web subscription — top up at https://cloud.higgsfield.ai/.",
                exc,
            )
        elif exc.kind == "unavailable":
            logger.error(
                "No model in HIGGSFIELD_MODEL_CHAIN is provisioned for this account (%s). "
                "Ask Higgsfield to enable nano-banana, or set the chain to a model you do have.",
                exc,
            )
        elif exc.kind == "validation":
            logger.error("Higgsfield rejected our request body (%s) — this is a code bug.", exc)
        else:
            logger.warning("Higgsfield transient failure: %s", exc)

        if s.higgsfield_required:
            raise RuntimeError(
                f"Higgsfield required but unavailable ({exc.kind}): {exc}. "
                "Set HIGGSFIELD_REQUIRED=false to allow the Gemini fallback."
            ) from exc

        path = await _generate_gemini_image(
            prompt=prompt,
            input_image_paths=input_image_paths,
            out_path=out_path,
        )
        return SceneResult(
            path=path,
            provider="gemini",
            model=getattr(s, "gemini_image_model", "") or "nano-banana-pro-preview",
            notes=[f"Higgsfield unavailable ({exc.kind}): {exc}"],
            reference_count=len([p for p in input_image_paths if p and Path(p).exists()][:4]),
        )


async def fidelity_gate(
    *,
    photo_path: Path,
    hero_path: Path,
    check_product_identity: bool = True,
) -> dict[str, Any]:
    s = get_settings()
    prompt_path = Path(s.prompt_dir) / "02_gemini_fidelity_gate.md"
    if not prompt_path.is_absolute():
        prompt_path = s.project_root / prompt_path
    system = (
        "You are a quality gate for e-commerce product photography. "
        "Judge only the criteria given. Respond with JSON only."
    )
    if prompt_path.exists():
        text = prompt_path.read_text(encoding="utf-8")
        if "```" in text:
            # Prefer system prompt block if present
            m = re.search(r"## System prompt\s*```(.*?)```", text, re.S)
            if m:
                system = m.group(1).strip()

    identity_note = (
        "Check PRODUCT IDENTITY strictly."
        if check_product_identity
        else "Skip PRODUCT IDENTITY (check_product_identity=false). Mark product_identity as SKIPPED."
    )
    user_text = (
        f"{identity_note}\n"
        "REFERENCE IMAGE is image 1. GENERATED IMAGE is image 2.\n"
        "Respond with JSON only:\n"
        '{"verdict":"PASS|FAIL","product_identity":"PASS|FAIL|SKIPPED",'
        '"setting":"PASS|FAIL","brand_safety":"PASS|FAIL","reserved_space":"PASS|FAIL",'
        '"failure_reason":null}'
    )

    def _part(path: Path) -> dict[str, Any]:
        data, mime = _image_to_jpeg_bytes(path, max_side=1280)
        return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}

    # Prefer PNG fallback if hero is PSD and fails
    hero = Path(hero_path)
    photo = Path(photo_path)
    parts = [{"text": user_text}]
    try:
        parts.append(_part(hero))
    except Exception:
        raise RuntimeError(f"Cannot load hero for fidelity gate: {hero}")
    parts.append(_part(photo))

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, params={"key": s.gemini_api_key}, json=payload)
    body = r.json()
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini fidelity gate failed ({r.status_code}): {(body.get('error') or {}).get('message') or r.text[:300]}")

    raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
    raw_text = _JSON_FENCE.sub("", raw_text).strip()
    try:
        verdict = json.loads(raw_text)
    except json.JSONDecodeError:
        # salvage first {...}
        m = re.search(r"\{.*\}", raw_text, re.S)
        if not m:
            raise RuntimeError(f"Fidelity gate non-JSON: {raw_text[:300]}")
        verdict = json.loads(m.group(0))

    if not check_product_identity:
        verdict["product_identity"] = "SKIPPED"
        checks = [verdict.get("setting"), verdict.get("brand_safety"), verdict.get("reserved_space")]
        verdict["verdict"] = "PASS" if all(c == "PASS" for c in checks) else "FAIL"
    return verdict


async def design_overlay(
    *,
    shot: dict[str, Any],
    photo_path: Path | None,
    brand_ruleset: dict[str, Any],
) -> str:
    s = get_settings()
    prompt_dir = Path(s.prompt_dir)
    if not prompt_dir.is_absolute():
        prompt_dir = s.project_root / prompt_dir

    if photo_path:
        prompt_file = prompt_dir / "03_claude_overlay_designer.md"
        system = (
            "You are a brand designer producing a text overlay layer for an e-commerce "
            "product image. Output a single self-contained HTML document and nothing else. "
            "No markdown fence."
        )
    else:
        prompt_file = prompt_dir / "04_claude_graphic_only.md"
        system = (
            "You design exact graphic-only e-commerce cards as self-contained HTML. "
            "Output HTML only, no markdown fence."
        )

    if prompt_file.exists():
        raw = prompt_file.read_text(encoding="utf-8")
        m = re.search(r"## System prompt\s*```(.*?)```", raw, re.S)
        if m:
            system = m.group(1).strip()

    approved = shot.get("overlay_text") or {}
    required_labels: list[str] = []

    def _req(value: Any) -> None:
        if value is None:
            return
        s_val = str(value).strip()
        if s_val:
            required_labels.append(s_val)

    _req(approved.get("resolved_headline") or approved.get("headline"))
    _req(approved.get("headline_line_2"))
    _req(approved.get("resolved_footnote"))
    _req(approved.get("sub_headline") or approved.get("subhead"))
    _req(approved.get("body"))
    _req(approved.get("disclaimer"))
    for callout in approved.get("callouts") or []:
        if isinstance(callout, dict):
            _req(callout.get("label"))
            _req(callout.get("value"))
        elif isinstance(callout, str):
            _req(callout)
    for item in approved.get("items") or []:
        if isinstance(item, dict):
            _req(item.get("label"))
            _req(item.get("count"))
            _req(item.get("value"))
    _req(approved.get("supporting_line"))
    for benefit in approved.get("benefits") or []:
        if isinstance(benefit, dict):
            _req(benefit.get("title"))
            _req(benefit.get("body"))
    for step in approved.get("steps") or []:
        if isinstance(step, dict):
            _req(step.get("caption"))
            _req(step.get("number"))
    for swatch in approved.get("swatches") or []:
        if isinstance(swatch, str):
            _req(swatch)

    user_bits = [
        "BRAND RULESET\n" + json.dumps(brand_ruleset, indent=2)[:12000],
        f"SHOT id={shot.get('shot_id')} purpose={shot.get('purpose')} type={shot.get('type')}",
        "APPROVED TEXT\n" + json.dumps(approved, indent=2),
        f"LAYOUT DIRECTION\n{shot.get('layout_direction') or ''}",
        "CANVAS: transparent 1500x1500. Use brand hex colors exactly. Sentence case. No gradients.",
        "CRITICAL: Return one COMPLETE HTML document that ends with </html>.",
        "CRITICAL: Every approved label/headline/callout/value string MUST appear as visible text in the HTML — "
        "leader lines or dots alone are not enough. Dense dimension/spec cards must list every callout.",
        "CRITICAL: Do not leave <body> empty. Start writing HTML immediately — no preamble.",
    ]
    if required_labels:
        user_bits.append(
            "REQUIRED VISIBLE STRINGS (must appear verbatim):\n- "
            + "\n- ".join(required_labels)
        )
    content: list[dict[str, Any]] = [{"type": "text", "text": "\n\n".join(user_bits)}]
    if photo_path and Path(photo_path).exists():
        data = _image_to_png_bytes(Path(photo_path), max_side=1500)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.b64encode(data).decode(),
            },
        })

    # Opus 5+ enables adaptive thinking by default. Thinking can consume the
    # entire max_tokens budget and leave an empty <body> (Hyken SKU_1). Overlay
    # HTML is deterministic layout work — disable thinking and keep effort medium.
    effort = (s.anthropic_reasoning_effort or "medium").strip().lower()
    if effort in {"xhigh", "max"}:
        effort = "high"  # thinking cannot be disabled at xhigh/max
    payload: dict[str, Any] = {
        "model": s.anthropic_model,
        "max_tokens": max(s.anthropic_max_tokens, 8000),
        "system": system,
        "messages": [{"role": "user", "content": content}],
        "thinking": {"type": "disabled"},
        "output_config": {"effort": effort},
    }
    # Dense dimension / multi-callout cards need more output headroom
    if len(required_labels) >= 8:
        payload["max_tokens"] = max(int(payload["max_tokens"]), 16000)
    headers = {
        "x-api-key": s.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages", headers=headers, json=payload
        )
        if r.status_code >= 400:
            # Retry without output_config if the account rejects the field shape
            slim = {k: v for k, v in payload.items() if k != "output_config"}
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=slim,
            )
    body = r.json()
    if r.status_code >= 400:
        raise RuntimeError(
            f"Claude overlay failed ({r.status_code}): "
            f"{(body.get('error') or {}).get('message') or r.text[:300]}"
        )

    html = _extract_claude_html(body)
    from app.pipeline.lint import lint_overlay_markup, overlay_html_is_complete

    def _overlay_ready(candidate: str) -> tuple[bool, str]:
        ok_c, reason_c = overlay_html_is_complete(candidate)
        if not ok_c:
            return False, reason_c
        fails = [
            r
            for r in lint_overlay_markup(candidate, shot, brand_ruleset)
            if r.get("status") == "FAIL"
            and r.get("check") in {"html_complete", "approved_text_present"}
        ]
        if fails:
            return False, fails[0].get("detail") or "approved text missing"
        return True, "OK"

    ok, reason = _overlay_ready(html)
    stop_reason = body.get("stop_reason")
    needs_retry = not ok
    if needs_retry:
        logger.warning(
            "Overlay HTML incomplete (stop_reason=%s, reason=%s) — retrying once",
            stop_reason,
            reason,
        )
        retry_payload = {
            **payload,
            "thinking": {"type": "disabled"},
            "max_tokens": max(int(payload["max_tokens"]), 16000),
            "messages": [
                {"role": "user", "content": content},
                {
                    "role": "assistant",
                    "content": (html[:4000] if html and "<body></body>" not in html.replace(" ", "") else ""),
                },
                {
                    "role": "user",
                    "content": (
                        "Your previous HTML was incomplete or missing approved text "
                        f"({reason or stop_reason}). Return a COMPLETE HTML document ending with "
                        "</html>. Every REQUIRED VISIBLE STRING must appear as a text node. "
                        "Do not return an empty body. Do not use only leader lines without labels."
                    ),
                },
            ],
        }
        # Drop empty assistant turn if we have nothing useful to continue from
        if not retry_payload["messages"][1]["content"]:
            retry_payload["messages"] = [
                {"role": "user", "content": content},
                retry_payload["messages"][2],
            ]
        async with httpx.AsyncClient(timeout=180.0) as client:
            r2 = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=retry_payload,
            )
        if r2.status_code < 400:
            body2 = r2.json()
            html2 = _extract_claude_html(body2)
            if "</html>" in html2.lower() and "<body></body>" not in html2.replace(" ", "").lower():
                html = html2
            elif html and html2 and "<body></body>" not in html.replace(" ", "").lower():
                html = html + html2
            else:
                html = html2 or html
            ok2, reason2 = _overlay_ready(html)
            if not ok2:
                raise RuntimeError(
                    f"Claude overlay HTML still incomplete after retry: {reason2}"
                )
        else:
            raise RuntimeError(
                f"Claude overlay retry failed ({r2.status_code}): {r2.text[:300]}"
            )

    ok, reason = _overlay_ready(html)
    if not ok:
        raise RuntimeError(f"Claude overlay HTML incomplete: {reason}")
    return html


def _extract_claude_html(body: dict[str, Any]) -> str:
    texts = []
    for block in body.get("content") or []:
        if block.get("type") == "text":
            texts.append(block.get("text") or "")
    html = "\n".join(texts).strip()
    html = _HTML_FENCE.sub("", html).strip()
    if "<html" not in html.lower():
        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
            "<style>body{width:1500px;height:1500px;margin:0;font-family:Arial,sans-serif}</style>"
            f"</head><body>{html}</body></html>"
        )
    return html

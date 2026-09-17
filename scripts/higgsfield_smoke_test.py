"""
Higgsfield API smoke test — verifies credentials, base URL, endpoint paths and
request body shape independently of the pipeline.

This is the check `_DEV_HANDOFF/07_SETUP_AND_ENABLEMENT.md` section 1 asks for.
Run it before debugging anything else in the generation path.

Usage:
  .\\.venv\\Scripts\\python.exe scripts\\higgsfield_smoke_test.py
  .\\.venv\\Scripts\\python.exe scripts\\higgsfield_smoke_test.py --generate
  .\\.venv\\Scripts\\python.exe scripts\\higgsfield_smoke_test.py --generate --with-image
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings

CANDIDATE_BASES = ["https://api.higgsfield.ai", "https://platform.higgsfield.ai"]
IMAGE_MODEL_PATHS = [
    "/nano-banana",
    "/higgsfield-ai/soul/standard",
    "/higgsfield-ai/soul/reference",
]


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "Authorization": f"Key {s.higgsfield_api_key}:{s.higgsfield_api_secret}",
        "Content-Type": "application/json",
    }


def _explain(status: int) -> str:
    return {
        200: "OK",
        400: "invalid parameters or concurrency reached",
        401: "BAD CREDENTIALS",
        403: "INSUFFICIENT CREDITS",
        404: "model or request not found for this account",
        422: "REQUEST BODY VALIDATION FAILED",
        423: "model temporarily blocked",
        429: "rate limited",
        500: "server error",
        503: "model disabled or not ready",
    }.get(status, "unexpected")


async def check_auth(client: httpx.AsyncClient, base: str) -> dict:
    """A status GET on a random request id separates auth failure from routing."""
    url = f"{base}/requests/{uuid.uuid4()}/status"
    try:
        r = await client.get(url, headers=_headers())
    except Exception as exc:  # noqa: BLE001
        return {"base": base, "reachable": False, "detail": str(exc)[:200]}
    return {
        "base": base,
        "reachable": True,
        "status": r.status_code,
        "auth_ok": r.status_code != 401,
        "meaning": _explain(r.status_code),
        "correlation_id": r.headers.get("X-Correlation-ID"),
    }


async def probe_model(client: httpx.AsyncClient, base: str, path: str, body: dict) -> dict:
    try:
        r = await client.post(f"{base}{path}", headers=_headers(), json=body)
    except Exception as exc:  # noqa: BLE001
        return {"path": path, "reachable": False, "detail": str(exc)[:200]}
    out = {
        "path": path,
        "status": r.status_code,
        "meaning": _explain(r.status_code),
        "correlation_id": r.headers.get("X-Correlation-ID"),
    }
    if r.status_code < 400:
        payload = r.json()
        out["request_id"] = payload.get("request_id")
        out["status_url"] = payload.get("status_url")
        # Don't leave a paid job running just to probe the route.
        if payload.get("cancel_url"):
            try:
                await client.post(payload["cancel_url"], headers=_headers())
                out["canceled"] = True
            except Exception:  # noqa: BLE001
                out["canceled"] = False
    else:
        out["detail"] = r.text[:300]
    return out


async def upload(client: httpx.AsyncClient, base: str, path: Path) -> dict:
    """Presigned upload, exactly as documented: POST url -> PUT bytes -> public_url."""
    from PIL import Image
    import io

    img = Image.open(path).convert("RGB")
    img.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    data = buf.getvalue()

    r = await client.post(
        f"{base}/files/generate-upload-url",
        headers=_headers(),
        json={"content_type": "image/jpeg"},
    )
    if r.status_code >= 400:
        return {"ok": False, "stage": "generate-upload-url", "status": r.status_code, "detail": r.text[:300]}
    payload = r.json()
    put = await client.put(
        payload["upload_url"],
        content=data,
        headers=dict(payload.get("upload_headers") or {"Content-Type": "image/jpeg"}),
    )
    if put.status_code >= 400:
        return {"ok": False, "stage": "PUT", "status": put.status_code, "detail": put.text[:300]}
    return {"ok": True, "public_url": payload["public_url"], "bytes": len(data)}


async def poll(client: httpx.AsyncClient, status_url: str, timeout: int = 300) -> dict:
    elapsed = 0.0
    interval = 3.0
    while elapsed < timeout:
        r = await client.get(status_url, headers=_headers())
        if r.status_code >= 500:
            await asyncio.sleep(interval)
            elapsed += interval
            continue
        r.raise_for_status()
        body = r.json()
        status = str(body.get("status", "")).lower()
        print(f"    ... {status} ({elapsed:.0f}s)")
        if status in {"completed", "failed", "nsfw", "canceled", "cancelled"}:
            return body
        await asyncio.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"poll timed out after {timeout}s")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Run one real billable generation to completion")
    parser.add_argument("--with-image", action="store_true", help="Include a reference image in the generation")
    args = parser.parse_args()

    s = get_settings()
    report: dict = {}

    print("=" * 70)
    print("HIGGSFIELD SMOKE TEST")
    print("=" * 70)
    print(f"key id      : {s.higgsfield_api_key[:8]}...{s.higgsfield_api_key[-4:]}")
    print(f"secret      : {'set (' + str(len(s.higgsfield_api_secret)) + ' chars)' if s.higgsfield_api_secret else 'MISSING'}")
    print(f"configured  : {s.higgsfield_api_base_url}{s.higgsfield_nano_banana_endpoint}")
    print()

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        print("[1] Credentials + base URL reachability")
        report["auth"] = []
        for base in CANDIDATE_BASES:
            res = await check_auth(client, base)
            report["auth"].append(res)
            if res.get("reachable"):
                print(f"    {base:38s} HTTP {res['status']}  {res['meaning']}")
            else:
                print(f"    {base:38s} UNREACHABLE  {res['detail']}")

        working_base = next(
            (r["base"] for r in report["auth"] if r.get("reachable") and r.get("auth_ok")),
            None,
        )
        if not working_base:
            print("\n    FATAL: no base URL accepted these credentials. Stop here and")
            print("    regenerate the key/secret pair at https://cloud.higgsfield.ai/")
            _write(report)
            sys.exit(1)
        print(f"    -> using {working_base}")
        print()

        print("[2] Configured endpoint from .env (reproduces the pipeline call)")
        configured = s.higgsfield_nano_banana_endpoint or "/nano-banana"
        if not configured.startswith("/"):
            configured = "/" + configured
        res = await probe_model(
            client, working_base, configured, {"prompt": "a plain grey studio backdrop", "aspect_ratio": "1:1"}
        )
        report["configured_endpoint"] = res
        print(f"    {configured:38s} HTTP {res.get('status')}  {res.get('meaning')}")
        if res.get("detail"):
            print(f"      detail: {res['detail']}")
        print()

        print("[3] Documented model paths, minimal valid body")
        report["model_paths"] = []
        for path in IMAGE_MODEL_PATHS:
            res = await probe_model(
                client, working_base, path, {"prompt": "a plain grey studio backdrop", "aspect_ratio": "1:1"}
            )
            report["model_paths"].append(res)
            print(f"    {path:38s} HTTP {res.get('status')}  {res.get('meaning')}")
            if res.get("detail"):
                print(f"      detail: {res['detail']}")
        print()

        print("[4] Body shape check on /nano-banana")
        fake = "https://example.com/x.jpg"
        shapes = {
            "input_images as bare strings (current code)": {
                "prompt": "test",
                "input_images": [fake],
                "image_urls": [fake],
                "image_url": fake,
            },
            "input_images as objects (per schema)": {
                "prompt": "test",
                "input_images": [{"type": "image_url", "image_url": fake}],
            },
        }
        report["body_shapes"] = {}
        for label, body in shapes.items():
            res = await probe_model(client, working_base, "/nano-banana", body)
            report["body_shapes"][label] = res
            print(f"    {label:44s} HTTP {res.get('status')}  {res.get('meaning')}")
            if res.get("detail"):
                print(f"      detail: {res['detail'][:200]}")
        print()

        if args.generate:
            print("[5] One real generation, end to end")
            body: dict = {
                "prompt": (
                    "A commercial office lobby floor, polished concrete, morning daylight. "
                    "Clean photographic style, no text."
                ),
                "aspect_ratio": "1:1",
                "output_format": "png",
            }
            if args.with_image:
                hero = next(
                    (p for p in (ROOT / "Staples Assets").rglob("*.png")),
                    None,
                ) or next((p for p in (ROOT / "Staples Assets").rglob("*.jpg")), None)
                if hero:
                    print(f"    uploading reference: {hero.name}")
                    up = await upload(client, working_base, hero)
                    report["upload"] = up
                    if up.get("ok"):
                        print(f"    upload OK ({up['bytes']} bytes)")
                        body["input_images"] = [{"type": "image_url", "image_url": up["public_url"]}]
                    else:
                        print(f"    upload FAILED at {up['stage']}: HTTP {up['status']} {up['detail']}")
                else:
                    print("    no reference image found under 'Staples Assets'")

            r = await client.post(f"{working_base}/nano-banana", headers=_headers(), json=body)
            if r.status_code >= 400:
                report["generation"] = {"status": r.status_code, "detail": r.text[:400]}
                print(f"    POST failed HTTP {r.status_code} ({_explain(r.status_code)}): {r.text[:300]}")
                _write(report)
                sys.exit(1)
            queued = r.json()
            print(f"    queued request_id={queued.get('request_id')}")
            final = await poll(client, queued["status_url"])
            report["generation"] = {"status": final.get("status"), "request_id": final.get("request_id")}
            if str(final.get("status")).lower() == "completed":
                images = final.get("images") or []
                url = images[0].get("url") if images and isinstance(images[0], dict) else None
                out = ROOT / "outputs_live" / "_higgsfield_smoke" / "nano_banana.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                img = await client.get(url)
                out.write_bytes(img.content)
                report["generation"]["saved"] = str(out)
                print(f"    COMPLETED -> {out}")
            else:
                print(f"    ended as {final.get('status')}: {final.get('error')}")
            print()

    _write(report)
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    ok_paths = [p["path"] for p in report.get("model_paths", []) if p.get("status", 999) < 400]
    cfg = report.get("configured_endpoint", {})
    if cfg.get("status", 999) < 400:
        print(f"  .env endpoint works: {configured}")
    else:
        print(f"  .env endpoint BROKEN: {configured} -> HTTP {cfg.get('status')} ({cfg.get('meaning')})")
    print(f"  usable model paths : {ok_paths or 'NONE'}")
    if any(p.get("status") == 403 for p in report.get("model_paths", [])):
        print("  CREDITS: at least one model returned 403 — fund the API account at")
        print("           https://cloud.higgsfield.ai/ (API credits are separate from a web subscription)")


def _write(report: dict) -> None:
    out = ROOT / "outputs_live" / "_higgsfield_smoke"
    out.mkdir(parents=True, exist_ok=True)
    (out / "SMOKE_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {out / 'SMOKE_REPORT.json'}")


if __name__ == "__main__":
    asyncio.run(main())

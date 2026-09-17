# Higgsfield integration notes

**Verified:** 2026-09-17 against the live account (key id `104ccf66…d333`)
**Re-verify with:** `.\.venv\Scripts\python.exe scripts\higgsfield_smoke_test.py`

This is the artifact `07_SETUP_AND_ENABLEMENT.md` section 1 asks for. It was never
written during the original build, which is why the account faults below went
undetected through a full four-SKU live run.

---

## 1. Base URL

`https://api.higgsfield.ai`

`https://platform.higgsfield.ai` also resolves and behaves **identically** — all 50
model endpoints return the same status on both. The docs use the two
interchangeably (quickstart shows `platform`, authentication and file-upload pages
show `api`, the OpenAPI `servers` block declares `api`). There is no behavioural
difference, so this is not a thing to debug.

## 2. Authentication

```http
Authorization: Key {api_key_id}:{api_key_secret}
```

The legacy `hf-api-key` / `hf-secret` header pair still works but is deprecated.
**Our credentials are valid** — no endpoint returns 401. Anything that looks like an
auth problem is really the provisioning or credit problem below.

## 3. Account capability — the actual blocker

| Endpoint | Status | Meaning |
|---|---|---|
| `/nano-banana` | `404 model_not_found` | **Not provisioned for this account** |
| `/higgsfield-ai/soul/standard` | `403 not_enough_credits` | Enabled, zero credit balance |
| `/higgsfield-ai/soul/reference` | `403 not_enough_credits` | Enabled, zero credit balance |
| `/higgsfield-ai/soul/character` | `403 not_enough_credits` | Enabled, zero credit balance |
| `/reve/*` | `423 model_blocked` | Temporarily blocked upstream |

Two independent things must be fixed before Higgsfield can serve a single shot:

1. **Fund API credits** at <https://cloud.higgsfield.ai/>. API credits are billed
   separately from a Higgsfield *web app* subscription — having a paid plan on the
   website does not give the REST API a credit balance. This is the reason the
   original run fell back to Gemini on every shot.
2. **Get nano-banana enabled** on the account if multi-reference product
   compositing is wanted. A 404 here is an account entitlement, not a bad path —
   per Higgsfield's error table it is explicitly do-not-retry, and no amount of
   endpoint-string guessing will change it. Ask Higgsfield support to enable it.

Soul `reference` is the usable substitute once credits exist, but it accepts only a
**single** `image_reference_url`, so shots that declare two or more product
references lose the extra angles.

## 4. Endpoint paths

Only these image paths exist. There is no `/nano-banana_2` and no
`/higgsfield-ai/soul/v2/standard` — both were in our code and both always 404'd.

```
/nano-banana
/higgsfield-ai/soul/standard
/higgsfield-ai/soul/reference
/higgsfield-ai/soul/character
```

## 5. Request bodies — not interchangeable

Each model has a different schema. Sending one model's body to another is a 422.

**`/nano-banana`** — `input_images` must be **objects**, not bare URL strings, and
the item schema is `additionalProperties: false`:

```json
{
  "prompt": "...",
  "aspect_ratio": "1:1",
  "output_format": "png",
  "num_images": 1,
  "input_images": [{ "type": "image_url", "image_url": "https://..." }]
}
```

**`/higgsfield-ai/soul/reference`** — requires `image_reference_url` (singular):

```json
{
  "prompt": "...",
  "image_reference_url": "https://...",
  "aspect_ratio": "1:1",
  "resolution": "1080p",
  "enhance_prompt": false,
  "batch_size": 1
}
```

**`/higgsfield-ai/soul/standard`** — prompt only, cannot ground the product:

```json
{ "prompt": "...", "aspect_ratio": "1:1", "resolution": "1080p", "num_images": 1 }
```

> **The published OpenAPI spec is wrong here.** It declares `resolution` for
> `soul/standard` as `"2K" | "4K"`. The live API rejects both and only accepts
> `"720p" | "1080p"`. Trust the live API over `/docs/openapi.json`.

### Aspect ratio support differs per model

| Model | Supported |
|---|---|
| `/nano-banana` | `auto 1:1 4:3 3:4 3:2 2:3 5:4 4:5 16:9 9:16 21:9` |
| `soul/standard` | same minus `auto` |
| `soul/reference` | `1:1 4:3 3:4 3:2 2:3 16:9 9:16` (no `5:4`, `4:5`, `21:9`) |

`app/adapters/live.py` clamps to the nearest supported ratio rather than 422-ing.

## 6. File uploads

Three steps, exactly as documented:

1. `POST /files/generate-upload-url` with `{"content_type": "image/jpeg"}`
2. `PUT` the bytes to the returned `upload_url`, carrying **every** header in
   `upload_headers` (includes `x-amz-tagging`). Never send our API credentials to
   the presigned storage URL.
3. Pass the returned `public_url` as the model's image input.

The upload URL expires after one hour. Accepted image types: `jpeg`, `jpg`, `png`,
`webp`, `gif`. PSD heroes are converted to JPEG by `_image_to_jpeg_bytes` first.

## 7. Request lifecycle

`POST` returns `{status, request_id, status_url, cancel_url}` immediately. Poll
`status_url` until `status` is one of `completed | failed | nsfw | canceled`.

- Retry the status `GET` on 5xx and network errors — do **not** abandon a paid job
  because of one transient blip.
- Do **not** auto-retry the generation `POST` after an ambiguous timeout;
  submissions take no idempotency key, so a retry can double-bill.
- Output URLs are valid for **at least 7 days**. Download immediately.
- `failed` and `nsfw` are not charged; reserved credits are refunded.

## 8. Error codes and what to do

| Status | Kind in our code | Action |
|---|---|---|
| 400 / 422 | `validation` | Our body is wrong. Code bug. Never retry. |
| 401 | `auth` | Bad credentials. Rotate the key. Never retry. |
| 403 | `credits` | Fund the account. Never retry. |
| 404 / 423 / 503 | `unavailable` | Try the next model in the chain. |
| 429 / 5xx | `transient` | Retry with exponential backoff and jitter. |

Every response carries an `X-Correlation-ID`. Record it with `request_id` when
contacting support.

## 9. Rate limits

Not established — we could never get a successful generation through, so no
concurrency ceiling was observed. `MAX_CONCURRENT_SHOTS` stays at 1 until a
funded account lets us measure it. Note `400` can also mean "concurrency reached",
which our classifier currently treats as `validation`; revisit once limits are known.

## 10. Security

The key and secret are in `.env` (gitignored) but were also echoed as plaintext
into a terminal session on 2026-09-16. Higgsfield's guidance is to rotate any
credential that may have been exposed in logs or screenshots, so **these two values
should be rotated** at <https://cloud.higgsfield.ai/>.

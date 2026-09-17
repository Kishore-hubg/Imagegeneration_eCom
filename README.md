# Staples / Coastwide marketplace image studio

Proof-of-concept pipeline that turns supplier product photos into Staples-compliant marketplace image stacks. Built from `_DEV_HANDOFF` Stage 0–12 contracts, with brand tokens from the Staples and Coastwide Digital Content Style Guides (8.17.26).

## What you get

- Four live product cards: ExpressMop → Power Cleaner → ProGel → Hyken
- Click a card → concurrent shot pipeline → results grid → zip download
- Side-by-side toggle against Staples production references
- **Mock mode by default** — no API keys required

## Quick start (mock mode)

```powershell
cd d:\Praty_Tasks\StaplesImageGeneration
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-local.txt
python -m playwright install chromium
copy .env.example .env   # already MOCK_MODE=true
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`requirements.txt` holds the runtime dependencies and is what the Vercel build
installs. `requirements-local.txt` adds Playwright on top, because the hosted
function cannot run Chromium.

Open http://127.0.0.1:8000

## Brand styling

| Token | Staples | Coastwide |
|---|---|---|
| Primary | `#E42A11` | `#FF8200` |
| Text | `#262020` slate | `#414140` charcoal |
| Surfaces | `#F5F3F0` paper, `#FFFFFF` | white + `#FFE6CC` tint |

Hard rules respected in UI and overlays: **no gradients**, sentence case, product never covered by text in generated layouts.

## Architecture

```
app/
  main.py           FastAPI routes
  loader.py         Config validation at boot
  orchestrator.py   Job + concurrent shots
  adapters/mock.py  Stage 0 mock for nano-banana / Gemini / Claude
  pipeline/         hero, router, compose, lint
  static/           Brand-styled vanilla JS UI
_DEV_HANDOFF/       Authoritative configs + prompts
outputs/{sku}/_MOCK/{job_id}/
```

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/skus` | Four cards, demo order |
| POST | `/api/jobs` | `{ "sku": "24639471" }` |
| GET | `/api/jobs/{id}` | Poll every 1.5s |
| GET | `/api/jobs/{id}/package` | Zip of finished images |
| GET | `/api/health` | Mock flag, active scene provider, Higgsfield capability, shot counts |

## Live providers

Set `MOCK_MODE=false` and fill keys in `.env` after completing `_DEV_HANDOFF/07_SETUP_AND_ENABLEMENT.md`.

| Stage | Provider | Notes |
|---|---|---|
| Scene generation | **Higgsfield** (primary) | Model chain: `/nano-banana` → `soul/reference` → `soul/standard` |
| Scene generation | Gemini (fallback) | Only when Higgsfield genuinely cannot serve |
| Fidelity gate | Gemini | Vision pass/fail on each raw photo |
| Overlay design | Claude | HTML/CSS, rasterized by Playwright Chromium |

Higgsfield is always tried first. Each shot records which model actually produced
it in `manifest.json` (`scene_providers`, and `scene_provider` per shot) and in the
package `README.txt`, so a deliverable can never imply Higgsfield authorship it
doesn't have. Shots served by the fallback are flagged `generated_by_fallback_provider`.

**Before any live run, confirm what your account can reach:**

```powershell
.\.venv\Scripts\python.exe scripts\higgsfield_smoke_test.py
```

It checks credentials, both base URLs, every model in the chain, and the request
body shape, then prints a verdict. `--generate` runs one real billable generation
end to end. Findings for the current account are recorded in
`_DEV_HANDOFF/HIGGSFIELD_NOTES.md`; read that first if generation is falling back.

Set `HIGGSFIELD_REQUIRED=true` to make photo shots **fail** instead of silently
substituting Gemini — use this for any run whose output is presented as Higgsfield work.

## Vercel deployment (catalogue only)

Live at https://imagegeneration-e-com.vercel.app

Deployment is zero-config: Vercel detects FastAPI and builds one function that
serves every route, so there is no `vercel.json`. **Do not add a catch-all
rewrite** — Vercel now passes the rewritten path to the app, so `/(.*)` →
`/api/index` makes every route 404. `.vercelignore` keeps `Staples Assets/` and
the PDFs out of the bundle, which is what holds the upload to ~900 KB.

The deployed site serves the UI, the SKU catalogue, brand rules and channel
targets — **image generation is disabled there**, and each card says so. Card
thumbnails come from `app/static/thumbnails/`, a 590 KB pre-rendered copy that
ships with the build; locally the same route prefers the freshly generated ones.

Three hard limits make the pipeline itself impossible on a serverless function:

| Limit | Consequence |
|---|---|
| `Staples Assets/` is 2.3 GB of PSD/PNG | Cannot fit the 250 MB bundle, so heroes and references are absent |
| No Chromium binary, and no room for one | Overlay rasterization is unavailable |
| Ephemeral, per-invocation instances | In-memory job state would not survive polling |

The app is built to survive all three. Startup never raises: a missing asset
degrades its SKU (`can_generate: false`), a failed boot is reported through
`GET /api/health` as `ok: false` with `boot_error`, and everything the app
writes goes under `/tmp` instead of the read-only deployment directory.
`STRICT_ASSETS` controls this and defaults to `false` only on Vercel/Lambda, so
a missing asset is still a hard failure locally.

Settings also treat an empty environment variable as unset. The Vercel project
has every variable defined with a blank value, and `""` cannot parse as an `int`
or `bool` — without that rule, `Settings()` raises and the whole app fails.

To run the full pipeline against a public URL, deploy the container image to a
host with a persistent disk and a real browser rather than a serverless function.

## Assumptions

1. `ASSET_ROOT=.` (this repo root contains `Staples Assets/`).
2. Stage 0 mock returns watermarked acceptance-reference images under `outputs/.../_MOCK/`.
3. Overlay rasterization uses Playwright Chromium (`python -m playwright install chromium`).
4. Best Buy is kept in config but hidden in the UI (`show_in_ui`).
5. Each shot's product references come from its `scene_prompt.input_images`, hero first.

# Imagegeneration_eCom

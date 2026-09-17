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
pip install -r requirements.txt
copy .env.example .env   # already MOCK_MODE=true
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

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
| GET | `/api/health` | Mock flag + shot counts |

## Live providers (later)

Set `MOCK_MODE=false` and fill keys in `.env` after completing `_DEV_HANDOFF/07_SETUP_AND_ENABLEMENT.md` (Higgsfield `/nano-banana`, Gemini fidelity gate, Claude overlay). Live adapters are intentionally not invented — they raise until verified.

## Assumptions

1. `ASSET_ROOT=.` (this repo root contains `Staples Assets/`).
2. Stage 0 mock returns watermarked acceptance-reference images under `outputs/.../_MOCK/`.
3. Overlay rasterization uses Pillow for Stage 0; Playwright Chromium lands with Stage 7 live overlays.
4. Best Buy is kept in config but hidden in the UI (`show_in_ui`).

# Imagegeneration_eCom

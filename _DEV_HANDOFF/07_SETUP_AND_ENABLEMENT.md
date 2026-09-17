# Setup and enablement

Everything you need to get from a fresh machine to a working pipeline, and how to get it yourself. No kickoff call, no sessions to book — Pratyoosh reviews your work daily from what you leave in the folder, so the last section tells you what to leave.

Work top to bottom. **Section 1 is the only part that blocks you, and even that doesn't block Stages 0–3 of the build.**

---

## 0. What you're being given

| | |
|---|---|
| **This folder** — `Staples Image Generation/`, including `_DEV_HANDOFF/` | ✅ you have it |
| **Higgsfield account credentials** (username + password) | 📩 Pratyoosh will send separately |
| **Gemini Pro API key** | ✅ you already have |
| **Anthropic API key** | ✅ you already have |

Everything else on this page you can obtain or install yourself.

---

## 1. Higgsfield — the one thing that takes real work

You're getting **account credentials, not an API key.** You need to pull the API credentials out of the account yourself, and — more importantly — read their live API docs, because I could not verify the endpoint details from outside the account. **Treat their docs as authoritative over anything written in this handoff.**

### 1.1 Get the API credentials

1. Log in with the credentials Pratyoosh sends.
2. Find the API section of the dashboard — usually under *Account*, *Settings*, *Developers* or *API*.
3. Locate or generate an **API key** and an **API secret**. Higgsfield issues both; some endpoints want them as two separate headers rather than one bearer token.
4. Copy them straight into `.env`. Never paste them into a chat, a commit, a screenshot or a Claude Code prompt.

### 1.2 Read their API docs and write down eight things

This is the part that matters. Work through their docs and record each of these — you'll need every one, and guessing any of them costs you an afternoon:

| # | What to find | Goes into |
|---|---|---|
| 1 | API base URL | `HIGGSFIELD_API_BASE_URL` |
| 2 | Exact `/nano-banana` endpoint path | `HIGGSFIELD_NANO_BANANA_ENDPOINT` |
| 3 | Auth header format — one bearer token, or key + secret as two headers? | your HTTP client |
| 4 | Request body field names — confirm `prompt`, `input_images`, `aspect_ratio`, `output_format` are right, and how `input_images` are passed (URL? base64? multipart upload?) | `generate.py` |
| 5 | The async contract — does the POST return a `status_url` to poll, or must you register a webhook? What are the status values? | `generate.py` |
| 6 | Max `input_images` per call (assumed 8) | config validation |
| 7 | Supported `aspect_ratio` values — confirm `1:1` and `3:2` are both accepted | shot configs use both |
| 8 | Output URL expiry (assumed 7 days) | confirms the download-immediately rule |

**Item 4 is the one most likely to differ from the assumption.** If `input_images` needs uploaded assets rather than inline base64, there's an upload step before every generate call that isn't in the current instructions. Find out on day one, not day four.

### 1.3 Check the account's limits

Two numbers you need before you write concurrency code:

- **Rate limit** — requests per minute or per hour. Set `MAX_CONCURRENT_SHOTS` in `.env` from this. It ships at `3` as a conservative guess. A 429 storm mid-demo is an avoidable way to lose the room.
- **Credit balance and cost per call** — a full four-SKU run is **18 generation calls**. Add retries and prompt iteration and you should budget **200–400 calls** before the demo is tuned. If the balance won't cover that, flag it to Pratyoosh immediately rather than discovering it at call 150.

### 1.4 Smoke-test before writing any app code

Do this with `curl` or a ten-line script, outside the project. It takes twenty minutes and it de-risks the entire Higgsfield integration.

1. POST one generate request: a trivial prompt, one input image, `aspect_ratio: "1:1"`, `output_format: "png"`.
2. Poll the `status_url` until it completes.
3. Download the result to disk.
4. Open it and confirm it's a real image.

**Pass condition:** you have a PNG on disk that you generated through the API, and you know exactly which headers, field names and status values got you there.

Until this passes, do not touch `generate.py`. Once it passes, `generate.py` is a half-hour job.

### 1.5 Write it down

Create `_DEV_HANDOFF/HIGGSFIELD_NOTES.md` with all eight findings, the working curl command, and the two limit numbers. It's the single most useful artifact you'll produce in week one, and it's what lets anyone else pick this up.

---

## 2. Verify the two keys you already have

Both take five minutes and both fail in ways that are easy to misdiagnose later.

### 2.1 Gemini — confirm vision is enabled

The fidelity gate sends **images**. A text-only key authenticates fine and then fails only at Stage 5, which looks like a bug in your gate code rather than a key problem.

**Test:** send one request with an image attached and any trivial question about it. If you get a description back, you're good. If you get a 400 about unsupported content, you need a key with vision access.

### 2.2 Anthropic — confirm model and reasoning effort

The architecture specifies `claude-opus-5` at reasoning effort `medium`. Both are locked.

**Test:** one call to `claude-opus-5` with `reasoning_effort: "medium"` and a one-line prompt. Confirm it returns and that the model string is accepted. If your key lacks Opus access, say so before you build around it.

---

## 3. Install the environment

```bash
python3 --version                    # need 3.11+
python3 -m venv .venv && source .venv/bin/activate

pip install fastapi uvicorn pillow playwright httpx python-dotenv jsonschema
playwright install chromium          # ⚠️ SEPARATE STEP — see below
```

### The one command everyone forgets

```bash
playwright install chromium
```

`pip install playwright` installs the Python library. It does **not** install the browser. Without this command every rasterization silently fails, and the error message points at Playwright rather than at the missing browser. Put it in your setup script.

### Fonts — install them at OS level

The licensed brand faces (Staples Norms Pro, Axiforma) aren't available and per Pratyoosh's decision we're not chasing them. We fall back to **Inter** and **Poppins**, both free from Google Fonts.

**Download and install both into the OS font directory.** If headless Chromium can't resolve a font it drops silently to a default serif — the output looks obviously wrong but is easy to miss at thumbnail size, and you'll waste time hunting a layout bug that's actually a font bug.

```bash
# verify Chromium can see them
fc-list | grep -i -E "inter|poppins"     # Linux
# macOS: check Font Book
```

### Disk

**~10 GB free.** The source folder is ~4.5 GB with the PSDs, and each full run writes raw attempts, overlays, composites and platform variants for 29 shots.

---

## 4. Network access

If you're behind a corporate proxy, these three hosts need to be reachable:

| host | for |
|---|---|
| `higgsfield.ai` (and whatever base URL their docs give) | image generation |
| `generativelanguage.googleapis.com` | Gemini |
| `api.anthropic.com` | Claude |

Nothing else needs egress. No marketplace APIs, no cloud storage, no CDN — every asset is local.

---

## 5. Things you do NOT need

Listed so you don't go looking:

- **Photoshop or `psd-tools`.** Two heroes are `.psd`; Pillow reads the flattened composite in one line. `psd-tools` isn't even installable in some environments and you don't need it.
- **A database.** Job state lives in an in-process dict; artifacts live on disk with a `manifest.json`. A restart losing job state is acceptable here.
- **Cloud storage or auth.** Everything is local and single-user.
- **Marketplace seller accounts.** Amazon, Walmart, Target, Best Buy, Staples.com — nothing uploads anywhere. The specs are just output dimensions.
- **Licensed brand fonts.** Decided; fallbacks are fine.
- **A Figma or Streamline licence.** Icons are drawn as inline SVG paths.

---

## 6. Your first three days need no Higgsfield key at all

Worth internalising, because it means Section 1 doesn't gate you.

Set `MOCK_MODE=true` and the three model calls are replaced with stubs that return the real finished Staples image for each shot. **Everything else runs for real** — config loading, the job state machine, concurrency, rasterization, compositing, platform variants, disk writes, the manifest, the API, frontend polling, the zip.

So Stages 0–3 and 7–12 of `01_BUILD_INSTRUCTIONS.md` are all buildable today. Then the keys drop in and only three functions change.

**One safety rule:** mock mode returns genuine Staples production images. Watermark them, or write them under `outputs/{sku}/_MOCK/`, or both. A mock artifact must never be mistakable for a generated one — that's how a real agency image ends up in a client deliverable labelled as AI output.

---

## 7. Stack

Python 3.11 + FastAPI, vanilla-JS frontend, is what `01_BUILD_INSTRUCTIONS.md` assumes throughout. Playwright and Pillow are the reason — the image toolchain is native to Python.

If you'd rather use Node/TypeScript, the contracts, schemas and prompts are all language-neutral and nothing forbids it. **Tell Pratyoosh in your daily note if you switch**, so the instructions stop matching on purpose rather than by accident.

---

## 8. How Pratyoosh reviews your work

He reviews **daily, on his own, from the folder.** No calls, no status meetings. So your job is to leave the folder in a state that answers his questions without you present.

### Keep a daily note

`_DEV_HANDOFF/DAILY_NOTES.md` — append a short entry each day. Four lines is plenty:

```
## 16 Sep
Stage: 0–2 done, config loading + job state machine running in mock mode.
Blocked: nothing. Higgsfield smoke test passes; notes in HIGGSFIELD_NOTES.md.
Next: Stages 3 and 7 — router, rasterize, composite.
Decisions I made: using httpx over requests for async polling.
```

That last line is the one that saves time. If you made a call that differs from the instructions, write it down — it's cheaper than him finding it in the diff.

### Leave the outputs in place

Don't clean `outputs/` between runs once you're generating for real. The folder plus `manifest.json` is how he sees what the pipeline actually did — retries, gate verdicts, lint results, flagged shots, placeholder strings.

### Flag blockers the day they appear

Anything in Section 1 that comes back wrong — no API access in the account, credits too low, a rate limit that makes the demo impractical, `input_images` needing an upload step — goes in the daily note **that day**, not once you've worked around it. Those are the four things only Pratyoosh can fix.

---

## 9. Setup checklist

Copy this into your daily note and tick as you go.

**Higgsfield**

- [ ] Logged in with supplied credentials
- [ ] API key and secret located, copied into `.env`
- [ ] Base URL and nano-banana endpoint path recorded
- [ ] Auth header format confirmed
- [ ] Request body field names confirmed, especially how `input_images` are passed
- [ ] Async contract confirmed — poll vs webhook, status values
- [ ] Max input images, supported aspect ratios (`1:1` and `3:2`), output URL expiry recorded
- [ ] Rate limit recorded, `MAX_CONCURRENT_SHOTS` set from it
- [ ] Credit balance checked against a 200–400 call budget
- [ ] **Smoke test passes** — a PNG on disk, generated through the API
- [ ] `HIGGSFIELD_NOTES.md` written

**Existing keys**

- [ ] Gemini key confirmed to accept images
- [ ] Anthropic key confirmed for `claude-opus-5` at reasoning effort `medium`

**Environment**

- [ ] Python 3.11+, venv active
- [ ] Dependencies installed
- [ ] `playwright install chromium` run
- [ ] Inter and Poppins installed at OS level and visible to Chromium
- [ ] ~10 GB free disk
- [ ] Three API hosts reachable

**Project**

- [ ] `.env` created from `.env.example`, and `.env` is in `.gitignore`
- [ ] `ASSET_ROOT` points at the `Staples Image Generation` folder
- [ ] App boots and logs four SKUs: ExpressMop 8, Power Cleaner 8, ProGel 6, Hyken 7
- [ ] `MOCK_MODE=true` and a full ExpressMop run completes end to end
- [ ] `DAILY_NOTES.md` started

---

## 10. Where to go next

1. `00_START_HERE.md` — the ten-minute orientation. Read it first if you haven't.
2. `06_DECISIONS_LOG.md` — every judgment call the build rests on. Read once.
3. `02_FILE_MANIFEST.md` — which files matter, which are noise, which is the hero for each product.
4. `01_BUILD_INSTRUCTIONS.md` — start at Stage 0 and work down.

Two things in there are load-bearing and easy to skim past, so they're repeated here:

**The reserved-zone sentence in each scene prompt must reach Higgsfield verbatim.** Every photo shot's prompt ends with an `IMPORTANT:` instruction telling the model to leave a specific region of the frame empty. That one sentence is what makes overlay placement reliable. Don't reformat it, don't summarize it, don't append your own style words. When an overlay comes out badly placed, check that sentence survived into the request body before you debug anything else.

**Never fall back to an `acceptance_reference` image when a shot fails.** Those are Staples' own finished production images, sitting in the folder so you can compare your output against the real thing. If one ever lands in an output folder labelled as generated, the credibility of the whole exercise goes with it. A shot flagged `needs_review` with an honest reason is a better outcome — it shows the pipeline knows when it's wrong.

Questions to Pratyoosh directly: **pratyoosh.patel@infovision.com**

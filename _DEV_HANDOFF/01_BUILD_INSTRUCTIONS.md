# Build instructions

This is the implementation spec. It is written to be read by an engineer and to be handed to Claude Code as context.

**How to use it with Claude Code:** start a session in the project root with this file, `02_FILE_MANIFEST.md`, and the whole `config/` directory in context. Work one stage at a time. Do not ask for the whole app in one prompt — the stages below are sized to be one prompt each, and each has a stated exit condition you can check before moving on.

---

## Contents

- [Ground rules](#ground-rules)
- [Stage 0 — Mock mode first](#stage-0--mock-mode-first)
- [Stage 1 — Project skeleton and config loading](#stage-1--project-skeleton-and-config-loading)
- [Stage 2 — Job and state model](#stage-2--job-and-state-model)
- [Stage 3 — The shot-type router](#stage-3--the-shot-type-router)
- [Stage 4 — Photo generation](#stage-4--photo-generation)
- [Stage 5 — The fidelity gate](#stage-5--the-fidelity-gate)
- [Stage 6 — Overlay design](#stage-6--overlay-design)
- [Stage 7 — Rasterize, lint, composite](#stage-7--rasterize-lint-composite)
- [Stage 8 — Platform variants](#stage-8--platform-variants)
- [Stage 9 — Persistence and the manifest](#stage-9--persistence-and-the-manifest)
- [Stage 10 — API contract](#stage-10--api-contract)
- [Stage 11 — Frontend](#stage-11--frontend)
- [Stage 12 — Packaging](#stage-12--packaging)

---

## Ground rules

**Stack.** Python 3.11+ with FastAPI is the expected choice, and everything below assumes it. The image toolchain — Playwright for rasterizing, Pillow for compositing — is native to Python and that is the main reason. If you have a strong reason to use Node/TypeScript instead, the contracts, schemas and prompts are all language-neutral and nothing here forbids it. Tell Pratyoosh if you switch.

**Architecture is settled.** The pipeline shape, the model assignments and the branching shot logic were agreed with the client and are not open for redesign. If something in here looks wrong, raise it rather than silently improving it — there is usually a reason, and `06_DECISIONS_LOG.md` records every judgment call that was made and why.

**Model assignments are locked.**

| job | model | note |
|---|---|---|
| photographic generation | Higgsfield `/nano-banana` | not Soul, not Dop, not any video endpoint |
| vision fidelity gate | Gemini Pro | raw photo only, never the composite |
| overlay design and layout code | Claude `claude-opus-5`, reasoning effort `medium` | vision on for photo shots, off for graphic-only, not called at all for `photo_only` |

**Never hit a deadline by weakening a check.** Particularly the claim lint. A stack that ships with one shot flagged `needs_review` is a good outcome. A stack that ships with a silently invented claim on a regulated chemical is not.

**Placeholder copy is allowed, but only when declared.** This is an internal POC and the client has authorized placeholder text where it unblocks a shot. Every shot carries a `text_provenance` field — `APPROVED`, `PUBLISHED_ART`, `PLACEHOLDER_POC` or `NONE`. Placeholder strings bypass source validation but are **counted, recorded and surfaced** in the run summary, `manifest.json` and the package README. The hard limit: a placeholder may never state a quantified promise or a regulated instruction — no dilution ratio, application distance, contact time, kill claim, certification, refund period or warranty term. Generic reassurance is fine; a specific number is not.

---

## Stage 0 — Mock mode first

**Do this before anything else and before you have any API keys.**

Set `MOCK_MODE=true`. In mock mode, the three external calls are replaced:

| real call | mock behavior |
|---|---|
| nano-banana generate | sleep 2–4s, return the shot's `acceptance_reference` image |
| Gemini gate | sleep 1s, return `{"verdict": "PASS", ...}` |
| Claude overlay | sleep 2s, return a canned HTML overlay from a fixture file |

Everything else runs for real: config loading, the job state machine, concurrency, rasterization, compositing, platform variants, disk writes, the manifest, the API, the frontend polling, the zip.

**Why this ordering is not optional.** It removes the API keys from your critical path entirely, so you are not blocked on Pratyoosh. And when the keys arrive you are debugging three model calls against a skeleton you already trust, instead of debugging five unknowns at once.

Build `MOCK_MODE` as a flag on a single adapter layer — one module with three functions, each of which branches at the top. Do not sprinkle `if mock:` through the pipeline.

**One safety requirement:** mock mode returns real Staples production images. Watermark them, or write them to `outputs/{sku}/_MOCK/`, or both. A mock artifact must never be mistakable for a generated one. Refuse to start in mock mode if `--demo` is passed.

**Exit condition:** clicking a card on the landing page runs all eight ExpressMop shots to completion, writes a full output tree, and serves a downloadable zip — with no API key anywhere in the environment.

Note that two ExpressMop shots (`SKU_6` guarantee, `SKU_7` school corridor) have `acceptance_reference: null`, because we added them and Staples has no equivalent. Mock mode needs a fallback for those — a plain placeholder card with the shot id on it is fine.

---

## Stage 1 — Project skeleton and config loading

```
project/
├── app/
│   ├── main.py              FastAPI app, routes
│   ├── config.py            env loading, path resolution
│   ├── models.py            pydantic models for every config shape
│   ├── orchestrator.py      job lifecycle, concurrency
│   ├── pipeline/
│   │   ├── router.py        dispatch by shot type
│   │   ├── generate.py      nano-banana adapter
│   │   ├── gate.py          Gemini adapter
│   │   ├── overlay.py       Claude adapter
│   │   ├── raster.py        HTML -> PNG
│   │   ├── composite.py     overlay onto photo
│   │   ├── lint.py          claim lint + brand lint
│   │   └── variants.py      render-target fan-out
│   ├── adapters/
│   │   └── mock.py          Stage 0 mock implementations
│   └── static/              frontend
├── _DEV_HANDOFF/            this folder — configs and prompts live here
├── outputs/
└── .env
```

**Config loading.** Parse every file in `config/` into pydantic models at startup, not lazily. A malformed config should crash the app on boot with a clear message, not fail halfway through a demo.

Validate at load time:

- every `hero_image.path` resolves to a file that exists under `ASSET_ROOT`
- every `acceptance_reference` path resolves, where present
- every `shots[].render_targets` entry names a real `render_targets[].id` in `platform_targets.json`
- every `shots[].brand_ruleset` reference resolves to a loaded ruleset
- enabled shot count per SKU is between 6 and 8
- every shot has a `text_provenance` value, and every `PLACEHOLDER_POC` shot also has a `placeholder_declaration` block
- every hex string in both rulesets matches `^#[0-9A-F]{6}$`

**Path resolution.** Every path inside a SKU config is relative to `ASSET_ROOT`. Resolve once at load, store absolute, and never re-resolve downstream. Note that paths contain spaces — use `pathlib`, never string concatenation.

**All four SKUs are complete.** There are no tabled configs and no disabled cards. Expected counts at boot:

| config | enabled | total |
|---|---|---|
| `sku_24639471_expressmop.json` | 8 | 8 |
| `sku_24321408_powercleaner.json` | 8 | 9 |
| `sku_24636223_progel.json` | 6 | 6 |
| `sku_990119_hyken.json` | 7 | 7 |

**Exit condition:** app boots, logs those four counts, and fails loudly on a deliberately corrupted config.

---

## Stage 2 — Job and state model

One job per **SKU run**. One task per **shot**. Shots within a job run concurrently up to `MAX_CONCURRENT_SHOTS`.

```python
JobStatus  = queued | running | completed | completed_with_flags | failed
ShotStatus = pending | generating_scene | checking | designing_overlay
           | rendering | compositing | scaling | done | needs_review | failed
```

The status names map directly to the labels the frontend shows, so keep them stable:

| `ShotStatus` | frontend label |
|---|---|
| `pending` | Waiting |
| `generating_scene` | Generating scene |
| `checking` | Checking |
| `designing_overlay` | Adding brand layer |
| `rendering` | Drawing layout |
| `compositing` | Compositing |
| `scaling` | Sizing for channels |
| `done` | Done |
| `needs_review` | Needs review |
| `failed` | Failed |

Different types show different sequences, and that is worth surfacing rather than hiding — it makes the branching design visible to whoever is watching the screen:

| type | sequence |
|---|---|
| `hero_passthrough` | `scaling` → `done` |
| `graphic_only` | `designing_overlay` → `rendering` → `scaling` → `done` |
| `graphic_only_with_generated_tiles` | `generating_scene` → `designing_overlay` → `rendering` → `scaling` → `done` |
| `photo_overlay` | `generating_scene` → `checking` → `designing_overlay` → `rendering` → `compositing` → `scaling` → `done` |
| `photo_only` | `generating_scene` → `checking` → `scaling` → `done` |

**Job record:**

```python
{
  "job_id": "uuid",
  "sku": "24639471",
  "status": "running",
  "created_at": "...",
  "completed_at": null,
  "shots": [ ShotRecord, ... ],
  "counts": {"total": 6, "done": 4, "needs_review": 0, "failed": 0}
}
```

**Shot record** carries: `shot_id`, `label`, `type`, `text_provenance`, `status`, `attempts`, `gate_verdicts[]`, `lint_results`, `artifacts{}` (paths to raw photo, overlay PNG, composite, each variant), `flags[]`, `error`.

Add `placeholder_strings[]` to the record for any `PLACEHOLDER_POC` shot, carrying the actual invented text. It is what the run summary and the package README read from.

**Concurrency.** `asyncio` with a semaphore at `MAX_CONCURRENT_SHOTS`. Keep it at 3 or lower until the Higgsfield rate limit is known — a 429 storm mid-demo is an avoidable way to lose the room.

**No database.** Jobs live in an in-process dict, and every artifact is on disk with a `manifest.json` beside it. A restart losing job state is acceptable here; adding Postgres to a POC is not.

**Exit condition:** a job runs six shots concurrently, the status endpoint reflects every transition, and killing a shot mid-flight marks it `failed` without taking down the job.

---

## Stage 3 — The shot-type router

Dispatch on `shot.type`. Six types:

| type | path | count |
|---|---|---|
| `hero_passthrough` | no model calls. Recompose the existing hero onto the target canvas. | 4 |
| `graphic_only` | Claude (no vision) → rasterize → lint. No photo, no gate. | 7 |
| `graphic_only_with_generated_tiles` | one nano-banana call for a grid sheet → slice → Claude (no vision) → rasterize → lint. No gate. | 2 |
| `photo_overlay` | nano-banana → Gemini gate → Claude (with vision) → rasterize → lint → composite. | 14 |
| `photo_only` | nano-banana → Gemini gate. **The passed photo IS the finished shot.** No Claude call, no overlay, no composite. | 2 |
| `asset_passthrough` | rasterize a supplied PDF onto a canvas. No model calls. | 1 (disabled) |

### `photo_only` in detail

Two shots — ExpressMop `SKU_7` and ProGel `SKU_5` — carry no text at all, because their briefs say so (*"No callout needed"*). Generate, gate, save. Nothing layered on top.

Cheap to implement and the purest demonstration of the generation capability: there is no overlay drawing attention away from whether the product and the scene are actually right. Worth getting working early for that reason.

These shots have `overlay_text: null`, `layout_direction: null`, and a `reserved_zone` of `"none"` — nothing needs reserving because nothing is being placed.

### `hero_passthrough` in detail

An addition to the original two-type architecture, approved by Pratyoosh (decisions log, item 8). The reasoning: the marketplace main image must be the real product on pure white with no text. Regenerating it risks violating product accuracy for zero benefit. So:

1. Load `hero_image.path`. **Two of the four heroes are `.psd`** — see below.
2. Flatten any alpha onto pure white.
3. Detect the product bounding box (threshold anything not near-white).
4. Scale so the product's longest side covers ≥ 85% of the target frame.
5. Center on a `RT_MAIN_WHITE` canvas, 2400×2400, background exactly `RGB(255,255,255)`.
6. Assert: every pixel outside the product box is exactly `(255,255,255)`; no text present; ≥ 85% fill achieved.

All four heroes are 3000×3000, so nothing upscales. Still record the scale factor in the manifest — if a hero is ever swapped for a smaller one, that number is how you find out.

### Reading the PSD heroes

Power Cleaner and Hyken point at `.psd` files. Pillow reads a PSD's flattened composite directly:

```python
Image.open(path).convert("RGB")   # -> clean 3000x3000 RGB on white
```

No `psd-tools`, no Photoshop, no layer handling. Verified on all four SKUs. **Do not attempt layer-level access** — the composite is the finished flattened shot and it is all you need.

Each of those two configs also carries a `png_fallback` (1000×1000). Use it only if PSD reading fails, and log loudly when you do, because the main image will then be a 2.4× upscale.

**Exit condition:** router dispatches every type correctly; `hero_passthrough` produces a spec-compliant 2400×2400 main image for all four SKUs, including both PSD sources.

---

## Stage 4 — Photo generation

Full detail in `prompts/01_nano_banana_scene_prompt.md`. The essentials:

- Request body is `prompt` + `input_images` (max 8) + `aspect_ratio` + `output_format`.
- The prompt is the shot's `scene_prompt.template` **verbatim**. It already contains the reserved-zone instruction. Do not reformat it, do not summarize it, do not append your own style words.
- `input_images` symbolic names resolve against the SKU config. Hero first, always.
- The API is asynchronous — POST returns a `status_url`; poll it.
- **Download the result to disk the moment it completes.** Higgsfield URLs expire after 7 days and nothing downstream may hold one.

Save to `outputs/{sku}/{shot_id}/raw_attempt_{n}.png`. Keep failed attempts — they are what you show when explaining why a shot was flagged.

**Exit condition:** a real nano-banana call returns an image, it lands on disk, and the reserved zone in the result is visibly clear.

---

## Stage 5 — The fidelity gate

Full prompt in `prompts/02_gemini_fidelity_gate.md`.

The shape of it: raw photo + hero reference in, one JSON verdict out, four sub-checks (product identity, setting, brand safety, reserved space). All four must pass.

Three things that are easy to get wrong:

1. **It runs on the raw photo only.** Never on the composite. There is no second vision pass at the end — that is a deliberate POC simplification, not an oversight.
2. **It does not run on graphic-only shots at all.** Nothing photographic to judge.
3. **Some shots skip the product-identity check.** Power Cleaner `SKU_5` shows a wall dispenser; the bottle is inside it and never visible. Implement as an explicit per-shot flag, `fidelity_gate.check_product_identity: false`, defaulting to strict.

**Retry policy, fixed:** one retry with the same prompt. Fail twice → `needs_review`, record both attempts and both verdicts, move on. Never loop further. Never fall back to the `acceptance_reference`.

**Exit condition:** a deliberately bad generation (wrong colors) is caught and fails; a good one passes; a double failure flags the shot and the job continues.

---

## Stage 6 — Overlay design

Full prompts in `prompts/03_claude_overlay_designer.md` (photo shots, vision on) and `prompts/04_claude_graphic_only.md` (graphic shots, vision off).

The key move: **pass the actual passed photograph as an image attachment.** Claude designs against what it can see — where the reserved zone landed, how bright it is, what is behind it. Summarizing the photo in text and skipping the attachment throws away the entire reason this step is ordered after the gate rather than before it.

Both prompts share an output contract:

- one self-contained HTML document
- a single root element sized exactly 1500 × 1500
- all CSS inline; no external stylesheets, no web font requests, no remote images, no JavaScript
- icons as inline `<svg>` paths, 1.5px stroke, rounded caps and joins
- every hex must exist in the ruleset palette
- overlay shots: transparent background, text and graphics only, do not draw the photo

**Why 1500 × 1500.** Both style guides specify it as the design canvas and every type size in them is given for it. Design at 1500, render at whatever the target needs — the layer is vector, so that is free.

**Fonts.** Staples Norms Pro and Axiforma are not in the shared folder. Use the fallback stacks in the rulesets and **install the fallback locally** so the headless browser can resolve it — otherwise it silently drops to a default serif, which is easy to miss and looks obviously wrong. Wire `@font-face` from `assets/fonts/` so the real files drop in with no other change. This is open item 3.

**Exit condition:** Claude returns valid standalone HTML for one shot of each type; it renders correctly in a browser; every color traces to the ruleset.

---

## Stage 7 — Rasterize, lint, composite

### Rasterize

**Playwright with headless Chromium.** Chosen deliberately: Claude is writing real HTML and CSS, and Chromium is the only renderer that will interpret it the way Claude expects. `resvg` and `CairoSVG` are faster but only handle SVG, which would force Claude into a much more constrained output format and lose flexbox, web fonts and CSS text layout.

```python
page.set_viewport_size({"width": 1500, "height": 1500})
page.set_content(html, wait_until="networkidle")
page.wait_for_timeout(200)                     # let fonts settle
page.screenshot(path=out, omit_background=True)  # transparent PNG
```

`omit_background=True` is what gives transparency; without it you get an opaque white rectangle and the composite is ruined in a way that is not obvious at thumbnail size.

Launch the browser **once** at app startup and reuse the context. Launching per shot adds seconds per image and is the most common cause of a sluggish-feeling demo.

Install with `playwright install chromium` — add it to the setup script, it is the step people forget.

### Lint

Run all checks in `prompts/05_claim_lint_rules.md` on the markup, before compositing. The claim lint is the one that matters; the brand checks (palette, no gradients, sentence case, min/max type size, container contrast) run alongside it and are all cheap.

Extract text from the **markup**, not by OCR of the PNG. You have the source; it is exact and free.

On failure: mark `needs_review`, record the offending string verbatim, do not composite, **do not retry**. A model that invented a claim once will do it again, possibly more subtly.

### Composite

Pillow, straightforward:

```python
base = Image.open(photo).convert("RGBA")
over = Image.open(overlay_png).convert("RGBA")
if over.size != base.size:
    over = over.resize(base.size, Image.LANCZOS)
base.alpha_composite(over)
base.convert("RGB").save(out, "PNG")
```

Better still: re-rasterize the overlay at the base image's native size rather than resizing the PNG. It is vector, so a fresh render at 2000px is sharper than an upscaled 1500px raster and costs one more screenshot.

For `graphic_only` shots there is nothing to composite — the rasterized card *is* the output. Flatten onto the ruleset's default white background.

**Exit condition:** an overlay rasterizes with real transparency, composites cleanly, and a deliberately planted fake claim is caught by the lint and blocks the composite.

---

## Stage 8 — Platform variants

**This is not a separate pass.** It is the tail of Stage 3, and it is mostly free.

The research in `config/platform_targets.json` found that all five channels — Amazon, Walmart, Target, Best Buy, Staples.com — use a 1:1 square main image with a pure white background and no text, and all five accept a 1:1 secondary image with text allowed. They therefore collapse into **two render targets**:

| target | canvas | background | text |
|---|---|---|---|
| `RT_MAIN_WHITE` | 2400 × 2400 | pure white, machine-checked | not allowed |
| `RT_SECONDARY_SQUARE` | 2000 × 2000 (designed at 1500) | any | allowed |

So for each finished shot: look up its `render_targets`, and for each one either emit the already-correct file, or re-render. **Re-render, never regenerate.** No shot needs a second nano-banana call to satisfy a second target — the overlay is vector and the photo is already at the right aspect ratio.

Run the target's `machine_checks` on every emitted variant and record the results in the manifest. The white-background check on `RT_MAIN_WHITE` is the one Amazon actually enforces on upload, so it is worth being able to say it passed.

**Caveat worth carrying into the client conversation:** Best Buy's spec could not be verified (login-gated partner portal) and Staples.com's internal spec is not in the folder. Both are *assumed* to be satisfied because the two targets represent the strictest superset of the three channels that could be verified. Do not present them as confirmed. Open items 5 and 6.

**Exit condition:** every enabled shot emits a file per render target, all machine checks pass, and no shot triggered a second generation call.

---

## Stage 9 — Persistence and the manifest

Write every artifact to disk the moment it exists. Nothing stays in memory, nothing depends on a remote URL.

```
outputs/{sku}/
├── manifest.json
├── {shot_id}/
│   ├── raw_attempt_1.png
│   ├── raw_attempt_2.png        (only if there was a retry)
│   ├── overlay.html
│   ├── overlay.png
│   ├── composite.png
│   ├── RT_MAIN_WHITE.png        (only for targets this shot satisfies)
│   └── RT_SECONDARY_SQUARE.png
└── package.zip
```

`manifest.json` is the audit trail and is what you show when someone asks what the pipeline actually did. Per shot, record: type, final status, attempt count, every gate verdict with its failure reason, every lint result, any spelling correction applied, the upscale factor if one was used, every artifact path, model versions, and wall-clock duration.

Record `needs_review` shots with their reason **in full**. Those entries are the honest part of the demo and they are more persuasive than a clean run — they show the pipeline knows when it is wrong.

**Exit condition:** a completed run leaves a directory that a person can navigate without the app, and `manifest.json` explains every decision the pipeline made.

---

## Stage 10 — API contract

```
GET  /api/skus
     -> [{sku, display_name, card_label, hero_thumbnail_url, shot_count, demo_order}]
     All four are live. demo_order: ExpressMop 1, Power Cleaner 2, ProGel 3, Hyken 4.

POST /api/jobs                {"sku": "24639471"}
     -> 201 {"job_id": "..."}
     -> 404 {"error": "Unknown SKU"}

GET  /api/jobs/{job_id}
     -> {job_id, sku, status, counts, placeholder_count,
         shots: [{shot_id, label, type, text_provenance, status, thumbnail_url, flags}]}

GET  /api/jobs/{job_id}/package
     -> 200 application/zip
     -> 409 if the job is not finished

GET  /api/assets/{sku}/{shot_id}/{filename}
     -> the image, for thumbnails and the results grid
```

Polling, not websockets. `GET /api/jobs/{job_id}` every 1500ms is entirely adequate for six concurrent shots, and it is one less thing to debug on a projector.

Keep the status payload small and stable — it is polled dozens of times per run.

**Exit condition:** the full flow is drivable from `curl` alone, with no frontend.

---

## Stage 11 — Frontend

One static page, vanilla JS. No build step. The demo is the pipeline, not the UI — but it should not look unfinished, because it is going in front of a client's client.

**Landing.** Four cards, one per SKU, each showing its real untouched hero photo, the product name and the shot count. Clicking a card is the entire input. All four are live — nothing is disabled.

**Card order matters.** Show them in this order, which is the agreed demo sequence: **ExpressMop, Power Cleaner, ProGel, Hyken.** ExpressMop leads because it has the best reference coverage; Power Cleaner follows as the compliance story.

Hero thumbnails for Power Cleaner and Hyken come from PSDs — rasterize them to PNG once at startup and cache, rather than reading a 3000px PSD on every page load.

**Run.** One row per shot: label, status text, a small spinner, and a thumbnail that appears when the shot finishes. Poll every 1500ms. Use the exact status labels from the Stage 2 table.

Two details worth the effort because they make the architecture legible to whoever is watching:

- Graphic-only rows show a visibly shorter sequence (*Drawing layout → Done*). It makes the two-branch design obvious without anyone explaining it.
- A `needs_review` row shows amber with the reason on hover. Do not hide flagged shots.
- A `PLACEHOLDER_POC` row carries a small neutral marker — a dot or a short "placeholder copy" label. Not a warning, just visible. Two shots have it.

**Channel labels.** Do not display **Best Buy** anywhere in the frontend. It inherits Amazon's spec by decision rather than by verification, so naming it would put an unverified compliance claim in front of the client. Filter channels on the `show_in_ui` flag in `platform_targets.json` rather than deleting the channel — it stays in the config so the coverage logic remains complete.

**Results.** Grid of finished images. Beside each, where an `acceptance_reference` exists, offer a toggle to show Staples' own production version of the same shot. **This side-by-side is the most persuasive thing in the entire build** — it turns "here is what the AI made" into "here is what the AI made, next to what the agency charges $1,000–2,000 for." Build it.

Then: one **Download package** button.

**Exit condition:** click a card, watch the checklist fill, see the grid, toggle a comparison, download the zip.

---

## Stage 12 — Packaging

Zip the SKU's output folder as each job completes, so the download button is instant rather than starting a zip.

Ship the generated images plus a short `README.txt` naming the SKU, run timestamp, shot count, any flagged shots with reasons, and the model versions used. Exclude intermediate artifacts unless `?include_intermediates=true` — a client-facing package should contain finished images, not `raw_attempt_2.png`.

**The README must carry a placeholder list.** Every `PLACEHOLDER_POC` string in the run, quoted verbatim, under a heading that says plainly that this text was written for the POC and is not Staples-approved copy. Two shots have it today. This is the one thing in the packaging step that is not cosmetic: if these images ever travel beyond InfoVision, that list is what stops invented brand copy being mistaken for the real thing.

**Exit condition:** the downloaded zip opens on a Mac with no warnings and contains only finished, correctly named images.

---

## Suggested order and rough sizing

| stages | what you get | rough |
|---|---|---|
| 0, 1, 2 | mock mode, configs loading, job state machine | day 1 |
| 3, 7, 9 | router, rasterize/composite, disk layout — still all mocked | day 2 |
| 10, 11, 12 | API, frontend, zip — full demo running on mocks | day 3 |
| 4, 5, 6 | swap in the three real model calls, one at a time | day 4 |
| 8, tuning | variants, prompt tuning against the reference images | day 5 |

Everything up to and including day 3 needs **no API keys at all**. If the keys are slow to arrive, you are not blocked — say so rather than waiting.

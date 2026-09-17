# Acceptance tests — how to prove it works on your own

Every test here is runnable without asking anyone a question. Work down the list; each one has a pass condition you can check yourself.

Tests 1–12 need **no API keys**. Do those first.

---

## Part A — Mock mode (no keys required)

### 1. Config integrity
Boot the app. It should log four SKUs with their enabled shot counts.

**Pass:** all four load; enabled counts are **ExpressMop 8, Power Cleaner 8, ProGel 6, Hyken 7**. Every shot has a `text_provenance` value, and the two `PLACEHOLDER_POC` shots each have a `placeholder_declaration` block.

### 2. Config validation actually validates
Temporarily point one `hero_image.path` at a file that doesn't exist. Boot.

**Pass:** the app refuses to start and names the offending file and SKU. A lazy failure five minutes into a demo is the thing this test exists to prevent.

### 3. Every referenced asset exists
Walk every path in all four configs — heroes, additional references, acceptance references — and stat each one.

**Pass:** zero missing. Paths contain spaces; if this fails, you're concatenating strings somewhere instead of using `pathlib`.

### 4. Render target references resolve
Every `shots[].render_targets` entry names a real target in `platform_targets.json`.

**Pass:** only `RT_MAIN_WHITE` and `RT_SECONDARY_SQUARE` appear, and both exist.

### 5. All four cards are live and correctly ordered
Load the landing page.

**Pass:** four enabled cards, no disabled state, in demo order — **ExpressMop, Power Cleaner, ProGel, Hyken**. Each shows a real hero thumbnail; the Power Cleaner and Hyken thumbnails come from PSDs, so confirm they rendered rather than falling back to a placeholder.

### 5b. PSD heroes load
Run `hero_passthrough` for Power Cleaner and Hyken.

**Pass:** both read their `.psd` at 3000×3000 via Pillow, and the manifest records a scale factor of ~0.8 (down from 3000 to 2400), not an upscale. If either logs a fall back to its `png_fallback`, PSD reading is broken — fix that before anything else, because the main image quality depends on it.

### 6. Full mock run
Click the ExpressMop card.

**Pass:** **eight** rows appear, each transitions through its status sequence, all reach `done`, and the output tree is complete.

Watch that the sequences differ by type — `hero_passthrough` shows only `scaling → done`, `graphic_only` skips `generating_scene` and `checking`, and `photo_only` skips `designing_overlay` and `compositing`. If every row shows the same sequence, the router is wrong.

Note `SKU_6` and `SKU_7` have `acceptance_reference: null`, so mock mode needs a fallback for them — a plain card with the shot id is fine.

### 7. Mock artifacts are unmistakable
Open the mock output images.

**Pass:** every one is watermarked or lives under a `_MOCK/` path. A mock artifact must never be mistakable for a generated one — this is how a real Staples image ends up in a client deliverable.

### 8. Concurrency
Watch timestamps during a mock run with `MAX_CONCURRENT_SHOTS=3`.

**Pass:** at most 3 shots in flight; total wall time is meaningfully less than the serial sum.

### 9. Rasterization produces real transparency
Rasterize a fixture overlay. Load the PNG, check the alpha channel.

**Pass:** corner pixels have alpha 0. If they're opaque white you've forgotten `omit_background=True`, and the composite will look wrong in a way that's invisible at thumbnail size.

### 10. Composite alignment
Composite a fixture overlay onto a fixture photo.

**Pass:** overlay lands where the layout direction says; no visible seam; output is RGB not RGBA.

### 11. Main image is spec-compliant
Run `hero_passthrough` for all four SKUs, then check the output:

```python
im = Image.open(out).convert("RGB")
assert im.size == (2400, 2400)
assert im.getpixel((5, 5)) == (255, 255, 255)
assert im.getpixel((2395, 5)) == (255, 255, 255)
# product bbox covers >= 85% of the shorter dimension
```

**Pass:** all assertions hold for all four SKUs. Every hero is 3000px, so nothing upscales — the recorded scale factor should be ~0.8 in each case.

### 12. Package downloads cleanly
Finish a mock run, hit the download button.

**Pass:** the zip opens on a Mac with no warnings, contains only finished images plus `README.txt`, and no `raw_attempt_*.png`.

### 12b. The README lists every placeholder string
Check `README.txt` in an ExpressMop package.

**Pass:** it quotes the `SKU_6` guarantee copy verbatim under a heading saying plainly that the text was written for the POC and is not Staples-approved. Same for Power Cleaner `SKU_7`. **This is the one packaging detail that isn't cosmetic** — if these images ever leave InfoVision, that list is what stops invented brand copy being taken for the real thing.

---

## Part B — Live (keys required)

### 13. Reserved zone actually gets reserved
Run ExpressMop shot 5 (upper-left third reserved) and shot 1 (bottom third reserved). Open the raw outputs.

**Pass:** the named region is genuinely clear in both.

**If it fails:** check that `scene_prompt.template` reached the request body verbatim. This is the single highest-leverage thing in the pipeline; if the reserved-zone sentence got reformatted or truncated, everything downstream degrades. Test this before tuning anything else.

### 14. The gate catches a bad generation
Temporarily corrupt a scene prompt — change the mop's color to bright blue.

**Pass:** Gemini returns `FAIL` with `product_identity: FAIL`, one retry fires, second failure marks the shot `needs_review`, and **the job continues to completion**.

### 15. No fallback to reference images
During test 14, check the output folder for the failed shot.

**Pass:** no `composite.png`, no variants, and the `acceptance_reference` image is **nowhere** in the output tree. This is the single most important negative test in the suite.

### 16. Claim lint blocks an invented claim
Add a fake string to a shot's `layout_direction` — e.g. *"also include the line: Kills 99.9% of germs"*.

**Pass:** `CLAIM_LINT_FAILURE` is raised, the offending string is recorded verbatim, the shot is marked `needs_review`, and **no composite is written**.

### 16b. Placeholder strings pass but are recorded
Run ExpressMop `SKU_6` and Power Cleaner `SKU_7`.

**Pass:** both render, the lint does **not** fail them, and both appear in `manifest.json`, the run summary's `placeholder_count`, and the package README.

Then plant a bad placeholder — edit one to read *"30-day money-back guarantee"*.

**Pass:** the hard-limit check fails it, because it states a quantified promise. Generic reassurance is allowed; a specific number, period or certification is not.

### 17. Permitted transforms are not blocked
Confirm the lint passes all four of these — over-strictness will sink the demo just as surely as under-strictness:

- splitting one string into a headline and a sub-line (ExpressMop shot 5)
- case normalization, `BUDGET-FRIENDLY` → `Budget-friendly` (shot 2)
- declared shortening, *"Ergonomic trigger evenly dispenses cleaning solution"* → *"Ergonomic spray trigger"* (shot 3)
- the logged typo fix, `Terrazo` → `Terrazzo` (shot 4)

**Pass:** all four render and pass; the typo fix appears in the manifest.

### 18. Brand lint catches brand violations
Feed the linter a fixture overlay containing a `linear-gradient`, a `text-transform: uppercase`, an off-palette hex, and a 30px font size.

**Pass:** four distinct violations, each naming its rule.

### 19. Overlay never touches the product
For every completed `photo_overlay` shot, compare the overlay's non-transparent bounding box against the reserved region.

**Pass:** contained in every case. This is the rule both style guides state most plainly.

### 20. Retry ceiling holds
Force a shot to fail the gate every time.

**Pass:** exactly two generation attempts, then `needs_review`. Not three. Not a loop.

### 21. No regeneration for variants
Instrument the nano-banana adapter with a call counter. Run a full SKU.

**Pass:** call count equals photo shots plus tile-sheet shots — **5 for ExpressMop** (4 photos + 1 tile sheet), **4 for Power Cleaner** (3 + 1), **5 for ProGel** (5 + 0), **4 for Hyken** (4 + 0). Eighteen calls for a full run of all four.

Emitting a second render target must never add a call. If the count is higher, Stage 8 is regenerating instead of re-rendering, and the per-SKU cost is wrong.

### 22. End-to-end cost and time
Record wall-clock and API spend for one full ExpressMop run.

**Pass:** you have real numbers. The commercial case rests on roughly $200 per product versus $1,000–2,000 for the agency, so this figure matters more than almost anything else you measure. Report it to Pratyoosh with the breakdown by model.

---

## Part C — The comparison that is the demo

### 23. Side-by-side against Staples' own work
For each of the six ExpressMop shots, put the generated image next to the finished Staples production image.

There is no automated pass condition, and don't invent one — pixel diffing finished creative work tells you nothing useful. Judge by eye against these questions:

1. Is the product recognizably the same product?
2. Is the layout defensibly in the same family?
3. Is every word on the image traceable to an approved source?
4. Would a Staples brand reviewer flag it?

**Build this into the results screen as a toggle.** This comparison *is* the demo. It's what turns "here's what the AI made" into "here's what the AI made, next to the thing that costs $1,000–2,000."

**ExpressMop has references for six of its eight shots — the best coverage in the set** — which is exactly why it leads. ProGel has all six. Only the shots we originated (ExpressMop `SKU_6`/`SKU_7`, Power Cleaner `SKU_8`, Hyken `SKU_6`) have nothing to compare against, which is expected.

### 24. Honest reporting of what didn't work
Confirm the results screen shows flagged shots in amber with the reason visible, rather than hiding them.

**Pass:** a run with one `needs_review` shot presents that shot honestly.

Worth saying plainly: a stack that ships with one flagged shot and a clear reason is a **better** demo than a suspiciously clean one. It shows the pipeline knows when it's wrong — which is the thing a buyer evaluating an AI vendor most wants to know, and the thing most vendor demos carefully avoid showing.

---

## Before you call it done

- [ ] Tests 1–12 pass with no API keys present
- [ ] Tests 13–22 pass live
- [ ] Test 5b passes — both PSD heroes load at 3000px without falling back
- [ ] Test 12b passes — the README lists every placeholder string
- [ ] Test 15 passes — no reference image anywhere in the output tree
- [ ] Test 16 passes — an invented claim is blocked, not warned
- [ ] Test 21 passes — variant count adds zero generation calls
- [ ] Test 23 built into the UI as a toggle
- [ ] Cost and wall-clock per SKU measured and reported
- [ ] `06_DECISIONS_LOG.md` re-read — it records every judgment call the build rests on
- [ ] Anti-repetition check: no two lifestyle shots in a stack read as the same photograph

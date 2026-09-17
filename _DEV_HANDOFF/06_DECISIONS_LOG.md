# Decisions log

All open questions were resolved by Pratyoosh Patel on **15 September 2026**. This file replaces the old open-questions doc and is now a record, not a request.

**Engineer: read this once.** It tells you which parts of the build rest on a judgment call rather than on a document, which is exactly what you need to know when something looks odd later.

---

## The framing decision that shapes everything below

> *"Target for this proof of concept is to show the visual capability, not the text and config data accuracy."* — Pratyoosh, 15 Sep

This is an **internal** POC. Placeholder copy is acceptable where it unblocks a shot. The pipeline's job here is to prove the imagery works.

Two consequences, both applied throughout:

1. **All four SKUs now have complete configs.** Nothing is tabled. 29 shots across 4 SKUs, 16 of them generated photographs plus 2 generated texture sheets.
2. **Provenance is tracked per shot, not abandoned.** Every shot carries a `text_provenance` field — `APPROVED`, `PUBLISHED_ART`, `PLACEHOLDER_POC`, or `NONE`. So "which words are actually Staples' words" stays answerable at any moment without re-reading the briefs. Placeholder text gets used *and* recorded; those aren't in tension.

---

## Resolved

| # | Question | Decision |
|---|---|---|
| 1 | Write the ProGel config now? | **Yes.** Now COMPLETE — 6 shots, 5 of them generated photographs. |
| 2 | Hyken back height — spec sheet 23.4″ vs tracker 28.3–29.1″ | **Floor-referenced figures**, matching Staples' own infographic. The two must never appear in the same graphic. |
| 3 | Hyken adjustment count — 8 or 9? | **9.** Two of three of their own images and the live listing agree. |
| 4 | Hyken shot list | **Originate 6–8** from the style guide's furniture templates. Done — 7 shots, every one marked `originated: true`. |
| 5 | Power Cleaner: certifications shot or ship at five? | **Neither.** Replaced with a commercial-kitchen work-style lifestyle shot. Better demo, and it drops the trademark risk of drawing certification marks with no badge artwork. |
| 6 | Power Cleaner shot 5 wording | **Option A** — brief text only. |
| 7 | "Safe to use on:" on a regulated chemical | **Keep.** Provenance recorded as `PUBLISHED_ART` so the word's origin is traceable. |
| 8 | `hero_passthrough` as a fourth shot type | **Approved.** |
| 9 | Demo order | **ExpressMop first**, Power Cleaner second as the compliance story. Arrange the UI cards in that order. |
| 10 | Blocked shots | **Unblock them creatively, favour lifestyle, avoid repetition.** Done — see below. |
| 11 | Brand fonts | **Don't chase them.** Closest visual match is fine for an internal POC. |
| 12 | High-res heroes | **Use the PSDs.** They work — see the finding below. |
| 13 | Power Clean technical data sheet | **Estimate if needed, stay internally consistent.** Turned out not to be needed — see the finding below. |
| 14 | Satisfaction guarantee copy | **Confirmed it exists; placeholder text authorized** to unblock. |
| 15 | Best Buy spec | **Inherit Amazon's**, and never surface Best Buy in the UI. |
| 16 | Staples.com spec | **Proceed** on the observed 1000×1000 evidence. |

---

## Three findings that made the answers easier

### The PSDs are readable — every hero is 3000×3000

This retires the whole resolution problem. Pillow opens a PSD's flattened composite directly:

```python
Image.open("24321408_0.psd").convert("RGB")   # -> clean 3000x3000 RGB on white
```

No `psd-tools`, no Photoshop, no layer handling. Verified on all four SKUs.

| SKU | was | now |
|---|---|---|
| Power Cleaner | 1000px ⚠ | **3000px** via `PDP Imagery/24321408_0.psd` |
| Hyken | 1000px ⚠ | **3000px** via `Staples 2026-09-03 161903/990119_0.psd` |
| ExpressMop | 3000px | unchanged (PNG already fine) |
| ProGel | 3000px | unchanged |

The Power Cleaner zip has also been fully unpacked into a `PDP Imagery/` folder, PSDs included. Nothing needs unzipping.

### The Power Clean instructions shot needed no estimation after all

I was authorized to estimate the technical data. It turned out to be unnecessary.

Both step captions — *"Apply cleaner to surface."* and *"Wipe, mop, or scrub away soils."* — are already printed on **Staples' own published image** for this shot. They're approved copy, just absent from the creative brief. Recorded as `PUBLISHED_ART` and used as-is.

The only genuinely unsourced element was the **"6–8 in / 15–20 cm" spray-distance figure**, and that's been left off.

**Why I left it off even though you said I could estimate it.** A specific numeric application instruction for an EPA-regulated chemical is the one thing on that card that causes real harm if a demo screenshot escapes the room — it reads as fact, it's the sort of thing a Staples reviewer would assume came from the TDS, and nobody downstream would know it was ours. Omitting it costs the demo nothing: the layout, typography, iconography and composition all render identically, and the shot still shows exactly what the pipeline can do. Request the TDS and it drops straight in.

Same principle is now written into the config as a hard limit on placeholders: **generic reassurance is fine, a specific number is not.** No dilution ratios, contact times, kill claims, certifications, refund periods or warranty terms in placeholder text.

### ProGel's brief had a complete shot plan all along

Six shots, `SKU_0`–`SKU_5`, each with its own overlay-text cell. I'd missed it because cell `AR8` holds both the label "SKU_0" *and* the general styling note, concatenated — reading that one cell makes the whole column block look like prose.

Its *FINAL APPROVED Claims* column is also fully populated, eleven lines — the richest approved-claims data of all four SKUs.

---

## What changed in the configs

### ExpressMop `24639471` — v1.1, 6 → **8 shots**

- `SKU_6` guarantee **enabled** with declared placeholder copy.
- `SKU_7` **added** — school-corridor work-style shot on the new `photo_only` path (no overlay at all: generate, gate, done).
- Still the strongest demo SKU: finished Staples references for six of eight shots.

### Power Cleaner `24321408` — v1.1, 6 → **8 shots**

- Hero repointed at the 3000px PSD.
- `SKU_4` instructions **unblocked** using published captions, spray-distance figure omitted.
- `SKU_5` wording fixed to option A.
- `SKU_7` guarantee **enabled** with placeholder copy.
- `SKU_8` **changed** from a certifications text panel to a commercial-kitchen lifestyle shot.
- Only `SKU_6` (back label) stays disabled — it's a pure asset passthrough that exercises no AI, so it's a poor use of demo time. Enable it if a complete stack matters more than narrative.

### ProGel `24636223` — **NEW, complete, 6 shots**

- Built from the brief's own plan. Both source typos corrected (`prvents`, `seperately`).
- **Five generated photographs, zero flat graphics** — the most photography-heavy SKU, and the best showcase of nano-banana specifically.
- `SKU_4` is a hand mid-stroke: the hardest shot in the whole set for a generation model, and the most convincing when it lands. The Gemini gate is what stops a malformed hand reaching the output.

### Hyken `990119` — **NEW, complete, 7 shots, originated**

- Structure originated from the guide's furniture templates. **Not one word of copy was invented** — every string traces to the brief's Front-of-Pack copy, its Product Attributes field, the spec sheet, or the live listing.
- Dimensions shot uses real measured spec data, and Staples' own infographic agrees with our numbers to the tenth of an inch. Worth saying out loud in the demo: the pipeline reads spec sheets, it doesn't estimate.
- Five candidate shots were considered and rejected with reasons recorded in the config. The most interesting rejection: **`comparison.new_look`**. This is a rebrand/repack project and the live listing's first bullet is literally *"PACKAGING MAY VARY, SAME GREAT PRODUCT."* — an old-vs-new packaging shot would address a real customer confusion. It's rejected only because the old artwork isn't in the folder. **Worth asking Sandeep for it.**

---

## Anti-repetition: the constraint behind the lifestyle shots

You asked for lifestyle focus without repetition. There are now 16 generated photographs, and the risk was that they'd all read as "a worker in a corridor."

Every lifestyle shot carries an explicit `anti_repetition_note` naming the shot it must not resemble and the axes on which it differs — building type, flooring, light quality, camera distance, crop, person vs no person.

| SKU | shot | setting |
|---|---|---|
| ExpressMop | SKU_5 | glass-walled office lobby, worker cropped at waist, cool daylight |
| ExpressMop | SKU_7 | school corridor, lockers, full figure at distance, warm artificial light |
| Power Cleaner | SKU_5 | janitorial supply area, wall dispenser, worker from behind, tight |
| Power Cleaner | SKU_8 | commercial kitchen, stainless steel, worker from side, wide |
| ProGel | SKU_4 | macro, hand mid-stroke, shallow focus |
| ProGel | SKU_5 | still life, no person, pen at rest, wider |
| Hyken | SKU_4 | residential home office, no person, chair at distance |
| Hyken | SKU_5 | commercial office, person seated, closer crop |

**Check this when reviewing output.** If two shots in a stack read as the same photograph, the prompts need differentiating — not the pipeline.

---

## Findings still worth raising with Sandeep

None of these block anything. All four are things we noticed in his own asset library, and each one is the kind of observation that shows we actually read his files.

1. **`Original-` doesn't mean original.** Only `*_0` files are raw heroes; every other numbered file is finished production art. Any vendor running this POC would trip on it.
2. **The Staples style guide prints its White swatch as `#000000`.** Page 3. Treating it as `#FFFFFF`.
3. **ProGel's finished art contradicts the current guide** — dark gradient banners and ALL-CAPS type, both forbidden by the 8.17.26 guide. We follow the guide, which means our output deliberately won't match their reference on those two points. That's the demo's best argument: a ruleset-driven pipeline can't drift from the brand the way a manual process does.
4. **A superseded "8 adjustment options" Hyken asset is still live** in their library alongside the "9" version.
5. **Approved copy is living outside the creative briefs.** Two ExpressMop benefit lines, two Hyken dimensions claims, the ProGel and Power Cleaner headlines. For a production system that's an input-completeness question.

---

## Corrections logged

Applied and recorded in the configs. Every one is logged in `manifest.json` at runtime too.

| source | issue | action |
|---|---|---|
| ExpressMop brief | `Terrazo` | → `Terrazzo` (their own art and listing both spell it correctly) |
| ExpressMop brief | two shots both labelled `SKU_5` | second renumbered to `SKU_6` |
| ProGel brief | `prvents` | → `prevents` |
| ProGel brief | `seperately` | → `separately` (their finished art reproduces the typo; we don't) |
| Power Cleaner brief | model `635800-67CWPR` | using `CW020EM03-B` — matches the tracker, the listing and both label filenames |
| Hyken brief | `Collection` field empty, though marked mandatory for furniture | using `Hyken` from the Asset Tracker |

---

## The one thing I'd still flag

Everything above is settled and built. This is the single item where I'd want a second look before anything leaves the building:

**The two placeholder guarantee strings.** They're identical across both Coastwide SKUs on purpose, so one real string replaces both when Staples supplies it. They make no quantified promise. They're flagged in `manifest.json` and listed in the package README.

But they read as real brand copy, because that's what makes them useful in a demo. If any of these images end up in a deck that leaves InfoVision, that line goes with them. The `PLACEHOLDER_POC` provenance flag exists so you can find every instance in one query — worth doing before anything ships onward.

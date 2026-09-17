# File manifest — what to point at, what to ignore

Everything here is relative to the shared folder **`Staples Image Generation/`**, which is `ASSET_ROOT` in `.env`.

---

## The naming rule that will trip you up

Across all four product folders, **only the `*_0` file is a raw hero image. Every other numbered file is a *finished* production image**, already carrying headlines, callouts and layout.

The `Original-` filename prefix does **not** mean raw. `Original-24636223_3.png` is a fully finished marketplace panel with a headline and a leader line on it.

This was verified by opening all 25 PNGs across the four SKU folders. Earlier project notes stated that the ProGel pen had no finished reference images at all — that is incorrect, it has five.

| prefix | what it actually is |
|---|---|
| `Original-*_0.png` | raw hero, white background, no text |
| `Bynder default-*_0.png` | raw hero, white background, no text |
| `Original-*_1..5.png` | **finished** production panel |
| `Bynder default-*_1..8.png` | **finished** production panel |
| `*.psd` | layered studio master — **IN SCOPE, and it's where the best heroes live.** See below. |
| `*.ai`, `*.eps` | vector packaging artwork — out of scope except the one label passthrough |

Finished panels are not inputs. They are your **test oracle** — generate, then compare side by side. They may also be passed to nano-banana as *secondary* product references, since they show the product from angles the hero does not.

---

## Root

| file | use it? |
|---|---|
| `Staples Digital Content Style Guide 8.17.26.pdf` | **Already distilled** into `config/staples_ruleset.json`. Read it only to check something. |
| `Coastwide Digital Content Style Guide 8.17.26.pdf` | **Already distilled** into `config/coastwide_ruleset.json`. Same. |
| `POC Scope Discussion.docx` | Background transcript. Useful context, no build data. |
| `Opus_Handoff_Prompt.md` | Prior planning notes. **Superseded by this folder** — where it disagrees with a config file, the config wins. |

---

## `Staples Assets/`

| file | use it? |
|---|---|
| `Asset Tracker.xlsx` | **Yes.** One sheet, four SKUs. Live marketplace copy (headliner, descriptions, up to 14 bullets) and the full spec attribute block per SKU. Already extracted into each config's `approved_source_strings`. Row 4 = Hyken, 6 = ExpressMop, 8 = ProGel, 10 = Power Cleaner. Note: each SKU's spec *names* sit in the row **above** its data row. |
| `Staples & Coastwide Brand Voice.docx` | **Already distilled** into both rulesets under `brand_voice`. |

---

## SKU 1 — Coastwide ExpressMop `24639471`  ★ build against this one first

`Staples Assets/Coastwide ExpressMop sku 24639471/`

**Config:** `config/sku_24639471_expressmop.json` — COMPLETE, **8 enabled shots**.

### ★ HERO
```
PDP Imagery/Original-24639471_0.png          3000×3000, pure white
```
The authoritative product reference. Passed to every nano-banana call.

### Finished references — one per shot, a complete set
| file | shot |
|---|---|
| `PDP Imagery/Original-24639471_1.png` | SKU_1 starter-kit contents |
| `PDP Imagery/Bynder default-24639471_2.png` | SKU_2 benefits card |
| `PDP Imagery/Original-24639471_3.png` | SKU_3 feature bubbles |
| `PDP Imagery/Bynder default-24639471_4.png` | SKU_4 surfaces grid |
| `PDP Imagery/Original-24639471_5.png` | SKU_5 in-use lifestyle |

SKU_6 (guarantee) and SKU_7 (school corridor) have no reference — both were added by us.

**This SKU has a finished reference for six of its eight shots — the best coverage in the set.** That makes it the acceptance oracle for the whole project and the SKU to lead the demo with.

### Supporting
| file | use it? |
|---|---|
| `Coastwide - Express Mop_brief (2).xlsx` | **Yes** — sheet `BRIEF`, row 8. The filled shot plan. Already extracted. |
| `SBGProdSpec_V6_Class_5793 - Wet Mops V2.xlsx` | Reference only. |
| `Packaging Artwork/I&ISaferChoice_BLACK.PNG` | EPA Safer Choice badge. Not used by any configured shot. |
| `Packaging Artwork/*.ai`, `*.eps` | Out of scope. |
| `PDP Imagery/*.psd` | Not needed here — the PNG hero is already 3000px. |
| `PDP Imagery/24639471_4.png` | Near-duplicate of the Bynder `_4` at 1254px. Ignore; use the Bynder one. |

---

## SKU 2 — Coastwide Power Cleaner `24321408`

`Staples Assets/Coastwide Power Cleaner/`

**Config:** `config/sku_24321408_powercleaner.json` — COMPLETE, **8 enabled, 1 disabled**.

> **Already unzipped for you.** `Staples 2026-09-03 160437.zip` has been extracted into a new `PDP Imagery/` subfolder alongside it. No unzip step is needed. The zip is left in place untouched.

### ★ HERO
```
PDP Imagery/24321408_0.psd    3000×3000, pure white   ← read via Pillow
```
PNG fallback at `PDP Imagery/Bynder default-24321408_0.png` (1000×1000) if PSD reading ever fails. The earlier resolution warning is **resolved** — the PSD clears `RT_MAIN_WHITE` with room to spare.

### Finished references
| file | shot |
|---|---|
| `PDP Imagery/Bynder default-24321408_1.png` | SKU_1 size and yield |
| `PDP Imagery/Bynder default-24321408_2.png` | SKU_2 features card |
| `PDP Imagery/Bynder default-24321408_3.png` | SKU_3 surfaces grid |
| `PDP Imagery/Bynder default-24321408_4.png` | SKU_4 instructions — **now enabled**; the two step captions come from this image |
| `PDP Imagery/Bynder default-24321408_4-1.png` | SKU_5 dispenser lifestyle |
| `PDP Imagery/Bynder default-24321408_6.png` | SKU_6 back label — **shot stays disabled** (pure asset passthrough, no AI), reference only |

### Supporting
| file | use it? |
|---|---|
| `Coastwide Midlab Phase 1_Creative Brief.xlsx` | **Yes** — sheet `BRIEF`, row 6. Rows 5–26 are ~20 sibling cleaner SKUs on the identical 8-shot pattern; useful for seeing the house style, not needed to build. |
| `...Bottle Label.pdf` / `.ai` | The regulatory label. Needed **only** if SKU_6 (back-label passthrough) is enabled. |
| `...BOX Label.pdf` / `.ai` | Carton label. Not used. |
| `Product Launch Order w Pricing 2.4.26.xlsx` | Pricing. Irrelevant to imagery. |
| `PDP Imagery/24321408_0.psd` | **THE HERO.** 3000×3000, read via Pillow. |
| `PDP Imagery/*.psd` (others), `*.jpg` | Not needed — duplicates of the PNGs at other stages. |

> **Regulated chemical.** `claim_policy: APPROVED_ONLY_STRICT`. Every visible word traces to an approved string, to Staples' own published art, or to a declared placeholder — the shot's `text_provenance` says which. Nothing may be drawn on or over the bottle label. The spray-distance figure on the instructions card is deliberately omitted: it's a numeric application instruction for a regulated chemical and it appears in no document we hold.

---

## SKU 3 — Staples Hyken chair `990119`

`Staples Assets/Staples Hyken/`

**Config:** `config/sku_990119_hyken.json` — COMPLETE, **7 enabled shots**, structure originated by InfoVision.

### ★ HERO
```
Staples 2026-09-03 161903/990119_0.psd    3000×3000, pure white, front ¾   ← read via Pillow
```
PNG fallback at `Bynder default-990119-NAD-X_1.png` (1000×1000). Of the five white-background PSDs, `990119_0` is the only full-chair front three-quarter — `_1` is rear ¾, `NAD-X_1` clips the base, `NAD-X_6` shows two chairs, `NAD-X_7` is an exploded view.

### Finished references
**23 of them**, all in `Staples 2026-09-03 161903/` (already unzipped — use the folder, not the `.zip`). Full catalogue with a description of each is in the config file under `asset_inventory.catalogue`. Richest reference set of the four SKUs.

Worth knowing: `Bynder default-990119_Dims.png` is a dimensions infographic whose numbers match the spec sheet exactly — proof that dimension charts are spec-sheet-driven, not estimated.

### Supporting
| file | use it? |
|---|---|
| `Staples - Chair ReBrand RePack_Brief - 10192024.xlsx` | **Yes** — sheet `BRIEF`, **row 25** of 45 chair SKUs. Front-of-Pack copy and Product Attributes are filled; the shot columns (AU–BL) are empty, which is why the structure was originated. |
| `ST63137 Hyken Black SBGProdSpec_V6...xlsx` | **Yes** — `Chair Dimension` tab, row 15 (`Claimed (in)`), averaged across 10 factory samples. Drives the dimensions shot. |
| `ST63907 SBGProdSpec_V6...New Package...xlsx` | Repack variant spec. |
| `*.glb`, `*.stp` | CAD. Not needed for 2D. Also, the Asset Tracker flags the CAD paddles as facing the wrong way — don't use it as an angle reference. |
| `*.ai`, `*.pdf` | Packaging artwork. Out of scope. |
| `*.psd` | Out of scope. |

---

## SKU 4 — Staples ProGel pen `24636223`

`Staples Assets/Staples ProGel Metal Body sku 24636223/`

**Config:** `config/sku_24636223_progel.json` — COMPLETE, **6 enabled shots**, five of them generated photographs.

### ★ HERO
```
Assets/PDP Imagery/Original-24636223_0.png   3000×3000, pure white
```
Pen on its blister card plus the bare pen. Best hero resolution of the four — comfortably exceeds `RT_MAIN_WHITE`.

### Finished references
`_1` through `_5` in the same folder. Five finished panels. Catalogued in the config.

⚠️ **These five contradict the current style guide** — they use a dark gradient banner and ALL-CAPS type, both of which the 8.17.26 guide forbids. The art predates or ignores the guide. **Follow the guide, not the art**, and flag the conflict — it is a useful finding for the client about their own back catalogue. Also, `_2` misspells "separately"; don't reproduce it.

### Supporting
| file | use it? |
|---|---|
| `Staples_ProGel Metal Body_NPD_Creative Brief.xlsx` | **Yes** — sheet `BRIEF`, row 8. Contains a **complete six-shot plan** (`SKU_0`–`SKU_5`, cells AR8/AT8/AV8/AX8/AZ8/BB8 with overlay text in AS8/AU8/AW8/AY8/BA8/BC8) plus a fully populated FINAL APPROVED claims column (M8, eleven lines). Note cell `AR8` holds both the "SKU_0" label and a general styling note, concatenated — which is why the plan is easy to miss. |
| `SBGProdSpec_V6_Class_724 - Metal Progel...xlsx` | Reference. |
| `Assets/Techpack/...Tech Pack-R0.pdf` | Reference. Filename contains mojibake from a mangled (TM) character — glob `*Tech Pack-R0.pdf` rather than hardcoding it. |
| `Assets/Packaging Artwork/*` | Out of scope. |
| `Assets/CAD/*.stp` | Out of scope. |
| `Assets/PDP Imagery/*.psd` | Not needed — the PNG hero is already 3000px. |

---

## PSDs are in scope — read the composite with Pillow

Two of the four heroes only exist at 1000px as PNG, but **all four exist at 3000×3000 as PSD**. Pillow reads a PSD's flattened composite directly:

```python
Image.open("24321408_0.psd").convert("RGB")   # -> clean 3000x3000 RGB on white
```

No `psd-tools`, no Photoshop, no layer handling. Verified on all four SKUs. Don't attempt layer-level access — the composite is all you need, and it's already the finished flattened shot.

| SKU | hero | px |
|---|---|---|
| ExpressMop | `PDP Imagery/Original-24639471_0.png` | 3000 (PNG fine) |
| Power Cleaner | `PDP Imagery/24321408_0.psd` | **3000 (PSD)** |
| ProGel | `Assets/PDP Imagery/Original-24636223_0.png` | 3000 (PNG fine) |
| Hyken | `Staples 2026-09-03 161903/990119_0.psd` | **3000 (PSD)** |

Each config carries a `png_fallback` for the two PSD heroes in case PSD reading ever fails.

## Still never open these

`.ai`, `.eps`, `.stp`, `.glb`. They need software you don't have and nothing in the pipeline reads them. The single exception is the Power Cleaner bottle label **PDF**, and only if the back-label passthrough shot is enabled.

---

## Quick reference

| SKU | brand | shots | generated photos | hero | px |
|---|---|---|---|---|---|
| `24639471` ExpressMop ★ | Coastwide | 8 | 4 | `Original-24639471_0.png` | 3000 |
| `24321408` Power Cleaner | Coastwide | 8 (+1 off) | 3 | `24321408_0.psd` | 3000 |
| `24636223` ProGel | Staples | 6 | 5 | `Original-24636223_0.png` | 3000 |
| `990119` Hyken | Staples | 7 | 4 | `990119_0.psd` | 3000 |

**29 shots, 16 generated photographs, every hero at 3000px.** All four configs are complete; no card is disabled.

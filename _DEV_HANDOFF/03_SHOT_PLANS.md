# Shot plans — the human-readable version

The machine-readable versions in `config/sku_*.json` are the source of truth. This document is for reading, reviewing and showing to the client.

**All four SKUs are complete.** 29 shots, 16 generated photographs, 2 generated texture sheets.

| SKU | brand | shots | generated photos | references available |
|---|---|---|---|---|
| ExpressMop `24639471` ★ | Coastwide | 8 | 4 | **6 of 8** |
| Power Cleaner `24321408` | Coastwide | 8 (+1 off) | 3 | 6 of 9 |
| ProGel `24636223` | Staples | 6 | **5** | 6 of 6 |
| Hyken `990119` | Staples | 7 | 4 | 6 of 7 |

---

## How to read a shot

Each one names five things: **purpose**, **stack template** (which entry in the style guide's §8 catalogue), **type** (which pipeline path), **approved text** with its source cell, and — for photo shots — the **scene prompt** including the reserved-space instruction.

### The six types

| type | what happens |
|---|---|
| **hero passthrough** | No AI. The real hero photo recomposed onto a pure-white 2400×2400 canvas. |
| **graphic only** | No photography. Claude writes HTML/SVG from the brand rules and approved text; rasterized. |
| **graphic only + tiles** | One nano-banana call returns a grid of textures; Claude masks them into a card. |
| **photo + overlay** | nano-banana → Gemini check → Claude designs the overlay *while looking at the photo* → composite. |
| **photo only** | nano-banana → Gemini check. The passed photo **is** the finished shot. No text. |
| **asset passthrough** | A supplied PDF placed on a canvas. One shot, currently off. |

### The copy rule, and how provenance is tracked

You may **split** an approved string into a headline and sub-line, **shorten** a label by dropping words, and **normalize capitalization** to sentence case. You may not add a word, number, percentage, certification or comparative of your own.

Every shot declares where its words came from:

| provenance | meaning | count |
|---|---|---|
| `APPROVED` | Verbatim from the brief or the live listing | 18 |
| `PUBLISHED_ART` | Verbatim from Staples' own finished image for that shot | 3 |
| `PLACEHOLDER_POC` | Written by us. Internal POC only. | **2** |
| `NONE` | No text on the shot | 7 |

The two placeholders are the satisfaction-guarantee lines. They make no quantified promise — no time window, no refund percentage, no warranty term — and both are listed in `manifest.json` and the package README.

---

# ★ SKU 24639471 — Coastwide ExpressMop Starter Kit

**Coastwide Professional · CW63248 · 8 shots · 4 generated photos**

Shots 0–5 come straight from the client's own filled shot plan. **Every one of those six has a finished Staples production image to compare against** — the best reference coverage in the set. Lead the demo here.

| # | shot | template | type | text |
|---|---|---|---|---|
| 0 | Main image | Main · product without package | hero passthrough | none |
| 1 | What's in the kit | Education · contents | photo + overlay | **Starter kit includes:** 1 Mop · 1 Microfiber wet mop pad · 12 Floor cleaner cartridges |
| 2 | Benefits card | Education · features & benefits | graphic only | ✓ Budget-friendly · ✓ **Easy to use** — User-friendly design with premeasured, concentrated refills · ✓ Saves time |
| 3 | Feature callouts | Education · detail zoom-in | photo + overlay | Ergonomic spray trigger · Easy fill tank · 7k sq. ft. per refill · Pre-measured refill cartridges |
| 4 | Surfaces | Education · features & benefits | graphic only + tiles | **Safe to use on most hard floors including:** Sealed wood · Rubber flooring · Linoleum · Terrazzo · Marble · Vinyl |
| 5 | In use ★ | Lifestyle · in use, focal | photo + overlay | **Great for quick and convenient maintenance** of high-traffic and customer-facing spaces |
| 6 | Guarantee | Trust · brand story | graphic only | ⚠ **placeholder** |
| 7 | School corridor | Lifestyle · use cases | photo only | none |

### Worth knowing

**Shot 2 will look sparser than Staples' version.** Their finished card carries supporting lines under *Budget-friendly* and *Saves time* that appear nowhere in the brief — approved copy from a source outside this folder. We render title-only rather than invent replacements. That's a missing-input finding, not a defect.

**Shot 3's labels are declared shortenings.** *"Ergonomic spray trigger"* comes from *"Ergonomic trigger evenly dispenses cleaning solution"*. Each pair is whitelisted in the config so the linter accepts it.

**Shot 4 fixes a typo.** The brief spells it *"Terrazo"*; Staples' own image and the Asset Tracker both spell it *"Terrazzo"*. Corrected and logged. Its headline also comes from their published art rather than the brief, which says only *"For Use on Hard Floors"*.

**Shot 5 is the flagship.** Facilities worker mopping a glossy tile floor in a bright glass-walled office lobby, headline in the reserved upper-left third. The one shot that exercises generate → check → see-the-photo-and-design end to end. Budget extra prompt-tuning time.

**Shot 7 is new and carries no text at all** — a school corridor with lockers, full-figure worker at a distance, warm artificial light. Deliberately unlike shot 5 (glass lobby, cropped at the waist, cool daylight). It's the cleanest demonstration of raw generation quality, with nothing layered on top to distract.

---

# SKU 24321408 — Coastwide Power Clean Degreaser

**Coastwide Professional · CW020EM03-B · 8 shots · 3 generated photos**

> ⚠️ **EPA-regulated chemical.** Strictest claim policy. Nothing drawn on or over the bottle label.

| # | shot | template | type | text |
|---|---|---|---|---|
| 0 | Main image | Main · product without package | hero passthrough | none |
| 1 | Size and yield | Education · specifications | photo + overlay | **Yields 28 ready-to-use** gallons per bottle · **3.25L** Bottles · **2 Bottles** per Carton |
| 2 | Features card | Education · features & benefits | graphic only | ✓ **Heavy duty alkaline cleaner and degreaser** — Removes tough greases, oils and other stubborn spills · ✓ **Concentrated formula** — Lowers end-use cost · ✓ **Low foaming** — Prevents recovery tank clogging |
| 3 | Surfaces | Education · features & benefits | graphic only + tiles | **Safe to use on:** Concrete floors · Shower rooms · Walls · Equipment and machinery |
| 4 | Instructions | Education · instructions for use | graphic only | **Easy to use** · 1 Apply cleaner to surface. · 2 Wipe, mop, or scrub away soils. |
| 5 | Dispenser ★ | Cross-sell · bundle & accessories | photo + overlay | **Use with the Coastwide Professional ExpressMix wall-mount dispenser** · \*Sold separately |
| 6 | Back label | Education · packaging | asset passthrough | **OFF** — pure asset passthrough, no AI |
| 7 | Guarantee | Trust · brand story | graphic only | ⚠ **placeholder** |
| 8 | Commercial kitchen ★ | Lifestyle · in use, focal | photo + overlay | **Industrial-strength cleaner/degreaser** |

### Worth knowing

**Shot 4 needed no estimation after all.** Both step captions are already printed on Staples' own published image for this shot — approved copy, just absent from the brief. The **"6–8 in / 15–20 cm" spray-distance figure is deliberately omitted**: it's the only genuinely unsourced element, and a specific numeric application instruction for a regulated chemical is the wrong thing to invent even for an internal demo. Request the TDS and it drops straight in. The card's layout, typography and composition render identically without it.

**Shot 3's headline says "Safe to use on:"** — verbatim from their published art, kept on your instruction. Provenance is recorded as `PUBLISHED_ART` so the origin of the word *safe* stays traceable.

**Shot 5 uses brief text only.** Their published version reads *"Easy to dilute and dispense…"*, which is demonstrably approved but appears in nothing we hold. The bottle is also inside the dispenser and never visible, so the product-identity check is switched off for this shot — only setting, brand safety and reserved space are checked.

**Shot 8 replaces the certifications panel.** A commercial kitchen: stainless steel, warm task lighting, worker from the side, wide framing — deliberately unlike shot 5's tight janitorial supply area with its muted blue-grey wall. A lifestyle shot demonstrates the capability being sold; a text panel listing EPA/NSF/Green Seal didn't, and carried trademark risk with no badge artwork available.

**Shot 6 stays off.** It's the regulatory label, which can't lawfully be redrawn — the only legitimate route is placing the supplied PDF, which exercises no AI. Enable it if a complete stack matters more than demo narrative.

---

# SKU 24636223 — Staples ProGel Elite Pen

**Staples · ST63291-CC · 6 shots · 5 generated photos · zero flat graphics**

From the brief's own six-shot plan. The most photography-heavy SKU, and the only Staples-brand stack that's photography end to end — which makes it the best showcase of nano-banana specifically, and proof the pipeline isn't just a Coastwide-orange trick.

| # | shot | template | type | text |
|---|---|---|---|---|
| 0 | Main image | Main · **product with package** | hero passthrough | none |
| 1 | Barrel features | Education · features & benefits | photo + overlay | **Premium metal barrel** · Ergonomic molded grip · Carbon steel clip · Fine tip 0.7mm |
| 2 | Ink on paper | Education · detail zoom-in | photo + overlay | **Ultra-smooth and quick drying ink** · prevents skipping and smudging |
| 3 | Refillable | Education · contents | photo + overlay | **Refillable to save money and reduce waste** · \*Ink sold separately |
| 4 | Hand writing ★ | Lifestyle · in use, focal | photo + overlay | **Perfect for all day use** · No smudge · No smear · No bleed |
| 5 | Desk still life | Lifestyle · natural setting, focal | photo only | none |

### Worth knowing

**The palette direction is the client's own.** Cell `AR8`: *"this carousel should be representative similarly like the packaging. Dark gray and red."* That maps to Slate `#262020` dominant with Staples Red `#E42A11` as accent — as a **flat fill**, because the guide forbids gradients.

**Two source typos corrected:** `prvents` → `prevents`, `seperately` → `separately`. Staples' own finished art reproduces the second one; we don't.

**Shot 0 is "product with package" on purpose.** The guide names *"pen thickness"* as an explicit case for showing the packaging, and the raw hero already is exactly that shot.

**Shot 3 has a truthfulness constraint.** This is a black-ink 2-pack; blue refills are separate SKUs. Staples' reference shows one blue and one black refill. Safest is two black — showing blue risks implying this pack contains blue ink.

**Shot 4 is the flagship and the riskiest shot in the whole project.** A hand mid-stroke is the hardest thing in the set for a generation model to get right, which makes it the most convincing when it lands. The Gemini gate is what stops a malformed hand reaching the output — this is the shot that justifies having a gate at all.

**Shot 5 is the style guide's own worked example**, almost word for word: *"a pen sitting on a desk conveys / highlights the pen without concern over the size of the pen relative to a conference room."* No text, per the brief. Deliberately unlike shot 4 — wider, no person, pen at rest.

> ⚠️ **All five reference panels contradict the current style guide** — dark gradient banners and ALL-CAPS type, both forbidden by the 8.17.26 guide. The art predates or ignores it. **We follow the guide**, so our output deliberately won't match theirs on those two points. That's the demo's best argument: a ruleset-driven pipeline can't drift from the brand the way a manual process does.

---

# SKU 990119 — Staples Hyken Task Chair

**Staples · ST63137 · 7 shots · 4 generated photos · structure originated**

The brief's shot columns are empty — verified empty for all 45 chair SKUs in that file. So the **structure** was originated from the style guide's furniture templates. **Not one word of copy was invented**: every string traces to the brief's Front-of-Pack copy, its Product Attributes field, the spec sheet, or the live listing.

| # | shot | template | type | text |
|---|---|---|---|---|
| 0 | Main image | Main · product without package | hero passthrough | none |
| 1 | Dimensions | Education · **dimensions** | graphic only | 10 measured callouts + 275 lb capacity |
| 2 | 9 adjustments | Education · product parts | photo + overlay | **9 adjustment options** for all day support · 5 circular callouts |
| 3 | Breathable mesh | Education · detail zoom-in | photo + overlay | **Breathable mesh back** ensures airflow for prolonged comfort |
| 4 | Home office ★ | Lifestyle · natural setting, scene | photo + overlay | **Adjustable armrests and seat height** for personalized support |
| 5 | Seated in use | Lifestyle · human context & scale | photo + overlay | **Ergonomic design with adjustable lumbar support** for stability and relief |
| 6 | Trust panel | Trust · certifications | graphic only | **275 lb** weight capacity · **5-year** manufacturer warranty · **BIFMA** compliant |

### Worth knowing

**Shot 1 is the most defensible shot in the entire project.** The guide names furniture explicitly as the case for a dimensions shot, and the numbers come from the spec sheet's `Chair Dimension` tab — claimed inches averaged across ten factory test samples. **Staples' own dimensions infographic agrees with our figures to the tenth of an inch.** Say that out loud in the demo: the pipeline reads spec sheets, it doesn't estimate.

Two decisions inside it. **Back height** uses the floor-referenced figures (28.3–29.1″), not the spec sheet's panel height (23.4″) — different measurements, both correct, and mixing them would produce a self-contradicting chart. And the **"5′6″–5′10″ suggested height"** and **desk-clearance** claims on their infographic are *not* reproduced, because neither appears in any document we hold.

Shot 1 also needs no generation call: the front and side elevations are cropped from `Bynder default-990119-NAD-X_6.png`, which already contains both views cleanly. Dimension lines must land on real geometry.

**Shot 2 says 9, not 8.** Their own library has both an "8 adjustment options" and a "9 adjustment options" asset; the live listing says 9. A superseded asset is still live in their library — worth mentioning to Sandeep.

**Shot 3 leads on the brief's own Anchor Bar Differentiator: *"Breathable Mesh"*** — the single thing Staples chose to lead with on this SKU.

**Shots 4 and 5 are deliberately different.** Shot 4: residential home office, wide, no person, chair at a distance, daylight from a window. Shot 5: commercial office, closer crop, person seated and working, seen from three-quarter rear so the mesh back and armrest are visibly supporting her. Different building type, different distance, person vs no person.

**Shot 6 renders BIFMA as text, never as a mark.** No badge artwork exists in this folder and a drawn lookalike is a fabricated certification mark.

### Five shots considered and rejected

Reasons are recorded in the config. The most interesting:

**`comparison.new_look`** — this is a *rebrand/repack* project and the live listing's first bullet is literally *"PACKAGING MAY VARY, SAME GREAT PRODUCT."* An old-vs-new packaging shot would address a real customer confusion, and the guide has a template for exactly this. Rejected only because the old artwork isn't in the folder. **Worth asking Sandeep for it** — it would be a genuinely good seventh or eighth shot.

**`comparison.vs_self`** — the guide's own example is *"different models of office chairs"*, and Staples has a finished HYKEN FAMILY image comparing Hyken / Pro / XL. Strong fit, but it needs accurate heroes for the Pro and XL, which are different SKUs not in this folder. Generating a plausible-looking Pro would be inventing a product.

**`instructions_assembly`** — the listing says *"Assembly required"*, but the guide says to use this template only when *ease of assembly is part of the value proposition*. Nothing frames assembly as a benefit here; it's disclosed, not sold. Using it would invert the client's own positioning.

Also rejected: `before_after` (a chair replacing a chair isn't a visible environmental change) and `contents_whats_in_the_box` (pack inclusion is "1 chair").

---

## Anti-repetition — check this when reviewing output

There are 16 generated photographs, and the obvious failure mode is that they all read as "a worker in a corridor." Every lifestyle shot carries an `anti_repetition_note` in the config naming the shot it must not resemble and the axes on which it differs.

| SKU | shot | setting | distance | person |
|---|---|---|---|---|
| ExpressMop | 5 | glass-walled office lobby, cool daylight | cropped at waist | yes |
| ExpressMop | 7 | school corridor, lockers, warm artificial | full figure, distant | yes |
| Power Cleaner | 5 | janitorial supply area, muted blue-grey | tight | from behind |
| Power Cleaner | 8 | commercial kitchen, stainless, warm task light | wide | from side |
| ProGel | 4 | macro, hand mid-stroke | very close | hand only |
| ProGel | 5 | desk still life, warm daylight | medium | none |
| Hyken | 4 | residential home office, window light | wide | none |
| Hyken | 5 | commercial office | closer | seated |

**If two shots in a stack read as the same photograph, differentiate the prompts — not the pipeline.**

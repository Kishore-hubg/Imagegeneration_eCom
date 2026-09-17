# Platform targets — the research, in plain English

Machine-readable version: `config/platform_targets.json`. That file is the source of truth; this one is for reading and for the client conversation.

---

## The finding

Five sales channels were in scope: Amazon, Walmart, Target, Best Buy and Staples.com. The task was to deduplicate them by **actual requirement** — aspect ratio, background rule, text-allowed — rather than treat them as five independent outputs.

**They collapse into two.**

Every one of the five uses a **1:1 square main image on a pure white background with no text**, and every one accepts a **1:1 secondary image with text allowed**. Not one channel in scope requires a non-square aspect ratio.

| target | canvas | background | text | satisfies |
|---|---|---|---|---|
| `RT_MAIN_WHITE` | 2400 × 2400 | pure white, RGB(255,255,255) | ❌ | all five |
| `RT_SECONDARY_SQUARE` | 2000 × 2000 (designed at 1500) | any | ✅ | all five |

**Why this matters commercially.** One generated image per shot satisfies all five channels. Channel count doesn't multiply generation cost — it multiplies a resize, which is free. That is a genuinely good line for the client, and it's worth making explicitly: *"adding a sixth marketplace costs nothing."*

---

## How the sizes were chosen

Both numbers are the **strictest value across every channel**, so one file clears them all.

**2400 × 2400** for the main image comes from Target, which asks for 2400px on the longest side — the highest figure found anywhere. It comfortably clears Amazon's 1600px zoom recommendation and every reported Walmart minimum.

**2000 × 2000** for secondary images, designed at 1500 × 1500. The 1500 figure isn't arbitrary: both style guides name it as the design canvas and every type size in them is specified for it. So design at 1500 in vector, render at 2000 for delivery. Because it's vector, that's lossless and free.

Worth noting: **Staples' own finished production images are 1000 × 1000.** Our secondary target is double their current output.

---

## Confidence, honestly

This is the part to be careful about in front of the client.

| channel | confidence | what that means |
|---|---|---|
| **Amazon** | ✅ Confirmed | Pure white RGB(255,255,255), machine-checked on upload. No text/logo/watermark on main. Product ≥85% of frame. ≥1600px recommended, 1000px hard minimum. The most consistently documented of the five. |
| **Walmart** | ⚠️ Secondary sources, conflicting | Background rule, 1:1 ratio and no-text rule are consistent everywhere. The **minimum size is not** — reported variously as 500×500, 640×480, 1000×1000 and 2000×2000. Our 2400px target clears all of them, so the conflict doesn't block the build. Confirm against Seller Center before making a production claim. |
| **Target** | ⚠️ Secondary sources | Pure white, square, ≥85% fill, no text/graphics/insets, 2400px primary minimum. Drawn from partner-facing summaries and integration-platform docs, not Target's own portal (login-gated). **The 2400px figure is load-bearing** — it's what sets our main canvas size — so it's the one most worth confirming. |
| **Best Buy** | 🔵 Inherited by decision | Specs sit behind the login-gated partner portal; no authoritative public figures found. **Decision (15 Sep): apply Amazon's spec, and never name Best Buy in the UI.** Amazon's is the strictest of the three verifiable channels, so anything clearing it almost certainly clears Best Buy. |
| **Staples.com** | 🔵 Accepted by decision | Internal spec isn't in the shared folder. **Decision (15 Sep): proceed** on the observed evidence that every finished asset is 1000 × 1000 — their current delivery size, well below our 2000px secondary target. |

---

## Best Buy is suppressed in the UI — on purpose

Best Buy inherits Amazon's spec by decision, not by verification. So it is served by the same two render targets as everything else, but **its name must not appear anywhere in the frontend** — not the landing page, not the status rows, not the results grid, not the package README.

Implement it as the `show_in_ui: false` flag on that channel and have the frontend filter on it. Don't solve it by deleting the channel: it stays in the config so the coverage logic remains complete, and so it can be switched on the moment a real spec arrives.

The reasoning is narrow but worth stating. Naming a channel in the UI reads as a compliance claim. We can't make that claim for Best Buy, and the output doesn't change either way — so the honest move is to serve it silently rather than assert something unchecked.

**Still the easy win:** Staples is already a Best Buy marketplace seller, so Sandeep can almost certainly produce the real spec on request. One answer turns this from inherited to verified.

---

## What the pipeline actually checks

Each target carries machine checks that run on every emitted variant and get recorded in the manifest.

**`RT_MAIN_WHITE`** — every pixel outside the product silhouette is exactly RGB(255,255,255); no text glyphs anywhere; product bounding box ≥85% of the shorter dimension; exactly 2400×2400; ≤5 MB.

The white-background check is the one Amazon genuinely enforces on upload, so being able to say it passed is worth the few lines of code.

**`RT_SECONDARY_SQUARE`** — exactly 2000×2000; no overlay element intersects the product bounding box; every hex in the overlay exists in the brand ruleset palette; every visible string matches an approved source; smallest text ≥45px at the 1500 design canvas; ≤5 MB.

---

## If a new channel is added later

The architecture already handles it. A channel with a different aspect ratio becomes `RT_3`, and the shots that need it change their `scene_prompt.aspect_ratio` so nano-banana generates at the right shape from the start — rather than cropping a square afterwards and losing the composition.

Only shots whose aspect ratio actually changes need regenerating. Everything else is a re-render.

---

## Sources

Amazon's figures were carried forward as confirmed from the prior planning work. The rest:

- [IsoPeel — marketplace requirements comparison chart](https://isopeel.com/guides/marketplace-image-requirements-comparison/) *(Amazon, Walmart)*
- [PixelBatch — Walmart image requirements guide](https://pixelbatch.io/blog/walmart-image-requirements-guide) *(Walmart)*
- [IsoPeel — Walmart marketplace image requirements](https://isopeel.com/guides/walmart-marketplace-image-requirements/) *(Walmart)*
- [Zentail — requirements for selling on Target+](https://help.zentail.com/en/articles/8615160-requirements-for-selling-on-target) *(Target)*
- [Feedonomics — selling on Target Plus](https://feedonomics.com/blog/selling-on-target/) *(Target)*
- [Best Buy Partner Portal — vendor supplied files and images](https://partners.bestbuy.com/-/vendor-supplied-files-and-images) *(login-gated, not retrievable)*

All of the above except the last are third-party aggregators rather than the marketplaces' own documentation. That's precisely why Walmart, Target and Best Buy are marked as they are.

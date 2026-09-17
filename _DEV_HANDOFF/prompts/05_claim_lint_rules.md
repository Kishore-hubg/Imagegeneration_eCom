# Claim lint — the rule that keeps this project out of trouble

**Runs at:** Stage 7, on every rendered overlay, before compositing.
**Applies to:** every shot that renders text — 23 of the 30 configured shots. Non-negotiable on the two Coastwide chemical SKUs.

---

## Why this exists

Two of the four SKUs in scope are EPA-regulated cleaning chemicals. The Coastwide style guide states plainly that packaging stickers must not be applied to or used to modify chemical product labels without brand and compliance approval, and that regulatory labelling requirements apply.

An AI pipeline that writes marketing copy onto a regulated chemical product image is a compliance incident waiting to happen. The mitigation is not "prompt the model to be careful." It is a deterministic check that runs after generation and fails loudly.

If a claim lint failure ever gets waved through to hit a demo deadline, the demo is not worth it. Ship the shot flagged instead.

---

## What the lint does

For each rendered overlay, extract every visible text string, then verify each one against the shot's approved sources.

### Extracting the strings

Parse the HTML Claude returned and collect all text nodes, plus any `<svg><text>` content, plus `alt` and `aria-label` attributes. Do not OCR the rasterized PNG — you have the markup, use it. It is exact and free.

### First, read the shot's provenance

Every shot declares `text_provenance`. It decides how the string is validated:

| provenance | how the lint treats it | count |
|---|---|---|
| `APPROVED` | Validate against `approved_source_strings` and the shot's own `overlay_text`, per the rules below. | 18 |
| `PUBLISHED_ART` | Same validation, but the source is the shot's `overlay_text.source` field describing Staples' published image rather than a brief cell. Record the provenance in the manifest so the origin stays traceable. | 3 |
| `PLACEHOLDER_POC` | **Bypass source validation** — there is no source, by design. But run every other check, record the strings verbatim in `manifest.json` and the package README, and count them in the run summary. | 2 |
| `NONE` | Nothing to check; the shot renders no text. | 7 |

`PLACEHOLDER_POC` bypasses validation; it does not bypass *visibility*. An invented string that nobody can find later is the actual failure mode here, not an invented string as such.

**The hard limit on placeholders.** A placeholder may never state a quantified promise or a regulated instruction — no dilution ratio, application distance, contact time, kill claim, certification, refund period or warranty term. Add a positive check for this: if a `PLACEHOLDER_POC` string contains a digit, a percentage sign, or any of `day / week / month / year / hour / minute / refund / warranty / guarantee period / certified / approved by`, fail it. The two current placeholders pass — they are deliberately generic.

### Verifying each string

For `APPROVED` and `PUBLISHED_ART` shots, a string **passes** if it satisfies any one of:

1. **Exact match** (after normalizing whitespace and case) to a value anywhere in `shot.overlay_text` or `sku_config.approved_source_strings`.
2. **Subsequence match** — every word in the rendered string appears in a single approved source string, in the same order, with no word added. This is what permits the shortening rule: *"Ergonomic trigger evenly dispenses cleaning solution"* → *"Ergonomic spray trigger"* fails this test and must be declared explicitly (see below), whereas *"Ergonomic trigger"* passes.
3. **Declared shortening** — the shot config explicitly lists the rendered label alongside its `source` string, as ExpressMop `SKU_3` does. Then the pair is whitelisted and the lint checks the rendered label matches the declared one exactly.
4. **Structural text** — a small closed list of non-claim strings: units already present in a source (`3.25L`, `12`, `18"`), punctuation, and the asterisk footnote marker.

Anything else **fails**.

Note that `graphic_only_with_generated_tiles` shots need the same treatment as `graphic_only` — the generated tiles carry no text, so only the card's own strings are checked.

### On failure

```
CLAIM_LINT_FAILURE
  sku:        24321408
  shot:       SKU_2
  rendered:   "Kills 99.9% of germs"
  nearest approved source: (none above 0.4 similarity)
  action:     shot marked needs_review, overlay NOT composited
```

Mark the shot `needs_review` in `manifest.json` with the offending string recorded verbatim. Do not composite. Do not retry with a nudged prompt — a model that invented a claim once will do it again, and each retry is another chance for a subtler invention to slip through.

---

## The other Stage 7 checks

Run these alongside the claim lint. All are cheap and deterministic.

| check | rule | source |
|---|---|---|
| **palette** | every hex in the markup exists in the ruleset `palette` or `infographic_palette` | both guides |
| **no gradients** | no `linear-gradient`, `radial-gradient`, `conic-gradient` anywhere in the CSS | both guides: "Don't use gradients" |
| **no opacity on brand color** | no `opacity` or `rgba()` alpha applied to an element filled with the primary brand color | both guides: "Do not change the opacity of the brand color" |
| **sentence case** | no `text-transform: uppercase`; no rendered string that is entirely uppercase and longer than 4 characters (allows `EPA`, `NSF`, `3.25L`) | both guides |
| **min type size** | smallest computed `font-size` ≥ 45px at the 1500 canvas | both guides, §4.5 |
| **max type size** | largest ≤ 130px, or ≤ 180px if the headline is 1–2 words | both guides, §4.5 |
| **no overlay on product** | overlay's non-transparent bounding box does not intersect the product bounding box | both guides, §6.1 |
| **contrast on containers** | text on a red/slate (Staples) or orange/charcoal (Coastwide) container is white | both guides, §1.2 |

---

## Finding the product bounding box

For `photo_overlay` shots, you need the product's extent to check the no-overlay rule. Cheapest workable approach for a POC:

1. The reserved zone is known from the shot config, and the gate has already confirmed it is clear.
2. Compute the overlay's own non-transparent bounding box from the rasterized PNG's alpha channel.
3. Assert that box falls inside the reserved region, expressed as a fraction of the canvas.

That is a proxy for "not on the product", and it is sufficient here. Full product segmentation is not warranted for a POC — and if the reserved zone held, the proxy is exact.

---

## What is explicitly allowed

Be clear with the team about this, because over-strictness will also sink the demo. These are permitted and must not be flagged:

- **Splitting** one approved string into a headline and a sub-line at a clause boundary. Staples' own production art does this on almost every card.
- **Case normalization** — `BUDGET-FRIENDLY` → `Budget-friendly`. The brief supplies caps; the style guide mandates sentence case. Presentation, not wording.
- **Correcting an obvious typo** where two other client sources agree on the correct spelling — `Terrazo` → `Terrazzo` is the documented example. Log every instance.
- **Dropping words** to shorten a label, when no word is added and the claim is not broadened.

What is never allowed: adding a word, a number, a percentage, a certification, a surface, a safety statement or a comparative that is not in the source.

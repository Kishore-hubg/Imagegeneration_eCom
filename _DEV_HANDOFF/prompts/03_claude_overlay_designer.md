# Prompt template — Claude overlay designer (photo shots, with vision)

**Used by:** every `photo_overlay` shot — 14 of the 29.
**Not used by** `photo_only` shots: those carry no text, so there is no overlay step and Claude is never called.
**Called at:** Stage 6, only after the photo has passed the Gemini gate.
**Model:** `claude-opus-5`, reasoning effort `medium`. Locked by the architecture.

---

## Why Claude gets to see the photo

This is the point of the whole sequence. Claude is given vision access to **the specific photograph that just passed the gate** — not a description of it, not a similar image. It can see where the reserved zone actually landed, how bright it is, what is behind it, and where the product's edges are. So it places and colors the overlay against the real image instead of guessing blind.

Pass the actual passed photo as an image attachment. Do not summarize it in text and skip the attachment.

---

## System prompt

```
You are a brand designer producing a text overlay layer for an e-commerce
product image. You write HTML and CSS/SVG that will be rasterized to a
transparent PNG and composited over a photograph you can see.

You work strictly within a brand ruleset. You are not here to improve the
brand, reinterpret it, or make a more interesting design than the rules allow.
Where the ruleset states a rule, the rule wins over your taste.

Two constraints override everything else:

1. You may not place any element over the product. The product must remain
   fully visible and in front. Use the reserved empty region you can see in
   the photograph.

2. You may not write, reword, embellish or add to the product copy. You render
   the exact approved strings you are given. You may split a string at a
   natural clause boundary into a headline and a sub-line, drop words to
   shorten a label, and normalize capitalization to the brand's sentence-case
   rule. You may not add a word that is not in the source string, and you may
   not make a claim stronger, broader or more specific than the source.

3. TEXT COMPLETENESS (applies to every product category — mop, cleaner, pen,
   chair, or any future SKU): every approved headline, label, callout, count,
   value, footnote and disclaimer you were given MUST appear as visible text
   nodes in the HTML. Leader lines, dots, icons or empty bubbles alone are a
   failure. The document MUST be one complete HTML file that ends with
   </html>. Never stop mid-tag. Start writing the HTML immediately — do not
   spend the response on planning or commentary.

Output a single self-contained HTML document and nothing else. No explanation,
no markdown fence, no commentary.
```

---

## User prompt

```
BRAND RULESET
{full contents of staples_ruleset.json or coastwide_ruleset.json}

THE PHOTOGRAPH
[attach the passed nano-banana output image]

This photograph is {width} x {height}. It was generated with an instruction to
leave this region clean and empty: {shot.scene_prompt.reserved_zone}
{if shot.scene_prompt.reserved_zone_note: pass the note too - for four shots the
 enum token says "left" or "bottom" while the prompt actually reserved the
 upper-right or top. The prompt wording is authoritative.}
Look at the image and find where that clear region actually is. Place your
overlay there. If the region is not where it was supposed to be, use whatever
genuinely clear area you can see instead — but never over the product.

SHOT
  id:       {shot.shot_id}
  purpose:  {shot.purpose}
  template: {shot.stack_template}

APPROVED TEXT — render exactly these strings, subject to the splitting and
shortening rules in your instructions:
{shot.overlay_text, serialized}

LAYOUT DIRECTION
{shot.layout_direction}

CANVAS
Produce the overlay on a transparent canvas of exactly 1500 x 1500 CSS pixels.
All type sizes in the ruleset are specified for this canvas, so use them as
literally given. The layer will be re-rendered at other sizes later; because it
is vector, that is free — so do not hardcode anything that only works at one
size.

OUTPUT CONTRACT
- One complete HTML document, <html> through </html>. Truncated markup is a
  hard failure — finish every tag and include every approved string as text.
- If the shot has callouts, items, benefits, steps or footnotes, EACH one must
  have its approved label/value rendered as readable text (not only a line or
  icon pointing at the product).
- <body> must have `background: transparent` and zero margin.
- A single root element sized exactly 1500x1500.
- All CSS inline in a <style> block. No external stylesheets, no web font
  requests, no remote images, no JavaScript.
- Use inline <svg> for icons, drawn as paths. Do not reference an icon library.
- Every color you use must be a hex value that appears in the ruleset palette.
- Do not draw the photograph. The overlay is text and graphics only, on
  transparency.
```

---

## What the model must not be allowed to do

Enforce these in the Stage 7 lint, not by hoping:

- **Invent copy.** Every visible string must trace to `overlay_text`. See `05_claim_lint_rules.md`.
- **Use an off-palette color.** Extract every hex from the returned markup and check it against the ruleset palette.
- **Go under minimum type size.** 45px at the 1500 canvas. Below that it is unreadable on mobile, and the guide says so explicitly.
- **Use a gradient.** Both guides forbid gradients outright. Reject any `linear-gradient` / `radial-gradient` in the returned CSS.
- **Use Title Case or ALL CAPS.** Both guides mandate sentence case. Reject `text-transform: uppercase`.
- **Overlap the product.** Compute the overlay's non-transparent bounding box and check it does not intersect the product's bounding box.

---

## Fonts

The licensed brand typefaces — **Staples Norms Pro** and **Axiforma** — are not in the shared folder. Until they are supplied:

```css
font-family: 'Staples Norms Pro', 'Norms Pro', Inter, 'Helvetica Neue', Arial, sans-serif;
font-family: 'Axiforma', 'Poppins', Inter, 'Helvetica Neue', Arial, sans-serif;
```

Install the fallback locally so the headless browser can actually resolve it — otherwise it silently falls through to a default serif and the output looks wrong in a way that is easy to miss. Put the real font files in `assets/fonts/` and `@font-face` them the moment they arrive; nothing else needs to change.

**Decided 15 Sep:** don't chase the licensed files for this internal POC — get as close a visual match as you can. Inter and Poppins are the current fallbacks. This remains the single most visible gap between the POC output and Staples' production art, so say so once in the demo rather than hoping nobody notices; naming it reads as rigour, being caught by it doesn't.

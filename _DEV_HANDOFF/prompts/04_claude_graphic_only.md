# Prompt template — Claude graphic-only card designer (no vision)

**Used by:** every `graphic_only` and `graphic_only_with_generated_tiles` shot — 9 of the 29.
**Called at:** Stage 3b — this branch skips photo generation and the vision gate entirely.
**Model:** `claude-opus-5`, reasoning effort `medium`.

---

## Why there is no vision model in this branch

A benefits card, a spec table, a surfaces grid — these are precise typography and data, not photographic scenes. The output is **exact by construction**. There is nothing for a vision model to judge. There is only linting: do the hex values match the ruleset, does the visible text match the approved string, is the smallest type above the minimum.

So: no nano-banana call, no Gemini call. Claude writes the markup, it gets rasterized, done. This is the cheapest and most reliable branch in the pipeline, and it accounts for half the shots in both completed SKUs.

---

## System prompt

```
You are a brand designer producing a complete e-commerce infographic card as a
single self-contained HTML document that will be rasterized to a PNG.

You work strictly within a brand ruleset. You are not here to improve the
brand, reinterpret it, or make a more interesting design than the rules allow.
Where the ruleset states a rule, the rule wins over your taste.

One constraint overrides everything else: you may not write, reword, embellish
or add to the product copy. You render the exact approved strings you are
given. You may split a string at a natural clause boundary into a title and a
supporting line, drop words to shorten a label, and normalize capitalization to
the brand's sentence-case rule. You may not add a word that is not in the
source string, and you may not make a claim stronger, broader or more specific
than the source.

TEXT COMPLETENESS (every product category — furniture dimensions, cleaner
specs, pen features, mop contents, certifications-as-text): every approved
title, body line, label, value, step caption, swatch name, supporting line
and disclaimer MUST appear as visible text in the HTML. Icons / leader lines
alone are not a substitute. Dimension cards must show BOTH each callout
label AND its measurement value. Start writing HTML immediately — do not
spend the response on planning. The document MUST end with </html> — never
truncate mid-tag or return an empty <body>.

Output a single self-contained HTML document and nothing else. No explanation,
no markdown fence, no commentary.
```

---

## User prompt

```
BRAND RULESET
{full contents of staples_ruleset.json or coastwide_ruleset.json}

SHOT
  id:       {shot.shot_id}
  purpose:  {shot.purpose}
  template: {shot.stack_template}
  (consult the matching entry under ruleset.stack_templates for what this
   template is for and when it is used)

APPROVED TEXT — render exactly these strings, subject to the splitting and
shortening rules in your instructions:
{shot.overlay_text, serialized}

LAYOUT DIRECTION
{shot.layout_direction}

{IF the shot is graphic_only_with_generated_tiles:}
GENERATED IMAGE TILES
A set of {n} image tiles has been produced separately and saved to:
  {list of local tile paths}
Reference them from your markup as <img src="..."> at those exact paths, and
mask each into the shape the layout direction calls for. Do not attempt to
draw the imagery yourself.

CANVAS
Produce the card at exactly 1500 x 1500 CSS pixels on the ruleset's default
stack background. All type sizes in the ruleset are specified for this canvas,
so use them as literally given.

OUTPUT CONTRACT
- One complete HTML document, <html> through </html>. Truncated markup is a
  hard failure.
- Every approved string in APPROVED TEXT must appear as visible text — not only
  as icons, numbers without labels, or empty layout cells.
- A single root element sized exactly 1500x1500.
- All CSS inline in a <style> block. No external stylesheets, no web font
  requests, no remote images, no JavaScript.
- Use inline <svg> for icons, drawn as paths. Do not reference an icon library.
- Every color you use must be a hex value that appears in the ruleset palette
  or its infographic palette.
```

---

## Icons

The style guides both specify **Streamline 3.0 Regular** — outline icons, rounded corners, 1.5px stroke. Those files are not in the shared folder.

Instruct Claude to draw equivalent icons directly as inline SVG paths honoring that style:

```
stroke-width: 1.5; fill: none; stroke-linecap: round; stroke-linejoin: round;
```

Each shot config that needs icons carries an `icon_concept` string per item (e.g. *"clock face with a small checkmark"*). Pass it through.

Container rules differ by brand and are in the ruleset under `iconography.containers_allowed` and `iconography.prohibited` — Staples in particular forbids using Staples Red for an icon's circle container, and forbids nesting a shape inside a shape. These are easy to violate accidentally; the lint should catch them but the prompt should state them too.

---

## Trust / guarantee panels are out of scope for demo stacks

ExpressMop / Power Cleaner / Hyken previously had satisfaction-guarantee or
certifications graphic cards. Those slots are now `photo_only` lifestyle scenes
per the Shot Mix Policy. Do not reintroduce trust-icon cards in graphic_only
prompts. Keep graphic_only for education that truly needs exact text
(dimensions, contents, yield, feature callouts).

---

## The `graphic_only_with_generated_tiles` sub-case

Two shots need imagery that does not exist in the folder: the ExpressMop surfaces grid (six flooring textures) and the Power Cleaner surfaces grid (four facility settings).

Resolve each with **one** nano-banana call that returns a single grid sheet, then slice it locally:

1. Call nano-banana with the shot's `scene_prompt.template` (it describes the grid explicitly, cell by cell).
2. Slice the returned image into equal cells per `scene_prompt.post_processing`.
3. Save each cell as a local PNG.
4. Pass the paths to Claude, which masks them into circles inside the SVG.

One call rather than six is cheaper, faster, and — more importantly — produces tiles with consistent lighting and color, which six independent calls will not.

There is no Gemini gate on a texture sheet. There is no product in it to check.

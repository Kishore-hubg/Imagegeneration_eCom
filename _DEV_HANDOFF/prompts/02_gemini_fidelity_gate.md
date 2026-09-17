# Prompt template — Gemini Pro fidelity gate

**Used by:** every `photo_overlay` and `photo_only` shot, once per generation attempt.
**Called at:** Stage 5, immediately after the raw photo comes back from nano-banana.

---

## Where this runs, and where it does not

It runs on the **raw generated photo only** — after generation, before any Claude call, before any overlay, before any compositing.

It does **not** run on the final composited image. That is a deliberate simplification for the POC, not an oversight. Do not add a second vision pass at the end.

It does **not** run on `graphic_only` shots at all. Those have no photograph to judge; their output is exact by construction and is checked by the lint rules in Stage 7 instead.

It **does** run on `photo_only` shots — and it is the *only* check those shots get. ExpressMop `SKU_7` and ProGel `SKU_5` carry no text, so there is no overlay step and no lint pass afterwards. Whatever the gate passes is what ships. Treat the gate as load-bearing on those two.

---

## System prompt

```
You are a quality gate for e-commerce product photography. You are shown a
reference photograph of a real product, and a newly generated photograph that
is supposed to contain that same product.

Your job is a single pass/fail judgment. You are not a designer, not a critic,
and not an editor. Do not suggest improvements. Do not describe the image at
length. Judge only the criteria given, and answer only in the required format.

Be strict on product identity and lenient on artistic taste. A plain, slightly
dull but accurate photograph passes. A beautiful photograph of a product that
is the wrong color, wrong shape or wrong brand fails.
```

---

## User prompt

```
REFERENCE IMAGE (the real product):  [attach sku_config.hero_image]
GENERATED IMAGE (under test):        [attach the raw nano-banana output]

Shot purpose: {shot.purpose}
Expected setting: {one line derived from scene_prompt — e.g. "a commercial office lobby, product in use"}

Check all four criteria:

1. PRODUCT IDENTITY
   Is the product in the generated image clearly the same product as the
   reference? Same color, same overall shape, same proportions, same visible
   branding. Not distorted, not melted, not duplicated, not missing parts, not
   given parts it does not have.

2. SETTING APPROPRIATENESS
   Is the scene a plausible, appropriate real-world setting for this product,
   matching the expected setting above?

3. BRAND SAFETY
   Are there any visible logos, wordmarks, signage or brand names in the scene
   OTHER than the branding already on the product itself? Any readable text at
   all? Any competitor product?

4. RESERVED SPACE
   The prompt asked for this region to be left clean and empty:
   {shot.scene_prompt.reserved_zone}
   (If the shot carries a `reserved_zone_note`, the PROMPT TEXT is authoritative
   over the enum value - four shots reserve the upper-right or top third but
   use a left/bottom enum token. Pass the region as described in the prompt.)
   Skip this check entirely for a photo_only shot - nothing will be placed.
   Is that region actually clear — free of objects, free of busy texture, and
   evenly lit enough that text placed there would be legible?

Respond with JSON only, no prose before or after:

{
  "verdict": "PASS" | "FAIL",
  "product_identity": "PASS" | "FAIL",
  "setting": "PASS" | "FAIL",
  "brand_safety": "PASS" | "FAIL",
  "reserved_space": "PASS" | "FAIL",
  "failure_reason": "<one sentence, only if verdict is FAIL, else null>"
}

The overall verdict is PASS only if all four sub-checks are PASS.
```

---

## Per-shot override

Some shots do not show the product at all. **Two shots carry the override:**

- **Power Cleaner `SKU_5`** — the concentrate bottle sits inside the wall dispenser and is never visible in frame.
- **Power Cleaner `SKU_8`** — a commercial-kitchen work-context shot with no product in frame at all.

For those, **skip criterion 1** and require only 2, 3 and 4. It's an explicit flag on the shot, not a special case in code:

```json
"fidelity_gate": { "check_product_identity": false }
```

Absent the flag, all four criteria apply. Defaulting to strict is the right failure mode.

---

## Handling the verdict

| verdict | action |
|---|---|
| PASS | Proceed to Stage 6 (Claude designs the overlay) — or, for a `photo_only` shot, straight to Stage 8. |
| FAIL, attempt 1 | Regenerate once. Log the failure reason. |
| FAIL, attempt 2 | Mark the shot `needs_review` in `manifest.json`. Record both attempts, both verdicts, both reasons. Move on to the next shot. |

The pipeline never blocks on a failed shot and never loops more than twice. A partial stack with one honest `needs_review` flag is a better demo than a stack that took twenty minutes because one shot kept retrying.

**Never** fall back to the `acceptance_reference` image when a shot fails. That would put a real Staples-produced image into an output folder labelled as generated. If Sandeep spots it, the whole POC's credibility goes with it.

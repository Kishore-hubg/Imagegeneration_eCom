# Prompt template — Higgsfield `/nano-banana` scene generation

**Used by:** every `photo_overlay` shot, every `photo_only` shot, and every `graphic_only_with_generated_tiles` shot. 18 calls across the four SKUs — 16 photographs and 2 texture sheets.
**Called at:** Stage 4 of the pipeline.

---

## The one technique that makes this work

Do not generate a finished scene and then hunt for empty space to put text in. That fails often and unpredictably.

**Instead: tell nano-banana upfront to leave a specific region of the frame clean and empty.** The SKU config's `scene_prompt.reserved_zone` field names that region for every shot. The instruction is already written into each shot's `scene_prompt.template` — it is the sentence beginning `IMPORTANT: leave the entire...`.

Keep that sentence. It is the most load-bearing line in the whole prompt. When an overlay comes out badly placed, check first whether the reserved-zone instruction survived into the request body.

---

## Request shape

```
POST {HIGGSFIELD_API_BASE_URL}{HIGGSFIELD_NANO_BANANA_ENDPOINT}

{
  "prompt":        "<the shot's scene_prompt.template, verbatim>",
  "input_images":  [ <resolved file references, max 8> ],
  "aspect_ratio":  "<the shot's scene_prompt.aspect_ratio>",
  "output_format": "png"
}
```

`input_images` comes from `scene_prompt.input_images`, which holds symbolic names that resolve against the SKU config:

| symbolic name | resolves to |
|---|---|
| `hero_image` | `sku_config.hero_image.path` |
| `additional_product_references.<key>` | the matching path under that object |

Always pass the hero first. It is the authoritative product reference.

Higgsfield is **asynchronous**: the POST returns a `status_url`. Poll it every `HIGGSFIELD_POLL_INTERVAL_SECONDS` until it reports completion or you hit `HIGGSFIELD_POLL_TIMEOUT_SECONDS`.

**Download the resulting image to local disk immediately.** Higgsfield's output URLs expire after 7 days.

---

## Anatomy of a scene prompt

Every template in the SKU configs follows this order. If you ever need to write a new one, follow the same order:

1. **Scene type and setting** — `A photorealistic commercial interior scene:` / `A clean product photograph on a pure white seamless background`
2. **Subject and action** — who or what is in frame and what is happening
3. **Product fidelity clause** — always some form of *"must match the reference image exactly in color, material, proportion and branding"*
4. **Lighting and grading** — `even, soft, shadowless studio lighting` for product shots; `warm, inviting color grading` for lifestyle
5. **Brand-safety negatives** — no competitor logos, no readable text, no signage, no other cleaning products
6. **The reserved-zone instruction** — last, prefixed `IMPORTANT:`, describing the empty region in plain physical language

---

## Negative instructions that must appear in every lifestyle prompt

These come straight from the brand hard rules and are not optional:

- `No visible brand logos anywhere in the scene other than those already on the product itself.`
- `No competitor branding.`
- `No readable text of any kind.`
- `Walls white or light gray.` *(style guide: lifestyle wall colors)*
- `Warm color grading.` *(style guide: warmer colors for environment elements)*

For Staples-brand SKUs, add: secondary props in frame should be Staples products, or left plain and neutral.
For Coastwide SKUs, add: secondary props should be Coastwide products, or left plain and neutral.

---

## Reserved-zone vocabulary

Use the physical description, not a coordinate. Models respond to the former.

| `reserved_zone` value | phrasing that works |
|---|---|
| `upper_left_third` | "leave the entire upper-left third of the frame as clean, uncluttered, evenly-lit empty wall and open space with no objects, no strong texture and no busy detail" |
| `bottom_third` | "leave the entire bottom third of the frame as clean, empty, pure white space with nothing in it" |
| `top_quarter_and_bottom_quarter` | "leave the top quarter and the bottom quarter of the frame as clean, completely empty pure white space — no part of the product or its shadow may enter them" |
| `left_quarter_and_right_quarter` | "keep a generous margin of clean, empty, pure white space down the full left edge and the full right edge — roughly the outer quarter on each side must be completely empty" |
| `none` | omit the IMPORTANT sentence entirely — texture sheets, and `photo_only` shots where nothing will be placed |

⚠️ **The enum is incomplete and the prompt is authoritative.** Four shots reserve the **upper-right** third or the **top** third, but the schema's closed list has no token for either, so they use the nearest available one and carry a `reserved_zone_note` saying so. **Always send the prompt's own wording** — never reconstruct the instruction from the enum value. Affected: Power Cleaner `SKU_8`, ProGel `SKU_3`, ProGel `SKU_4`, Hyken `SKU_5`. Extending the enum with `upper_right_third` and `top_third` and correcting those four is the clean fix and is worth doing early.

Always close the sentence with *"...this area is reserved for text that will be added afterwards."* Stating the purpose measurably improves compliance.

**`photo_only` shots reserve nothing.** ExpressMop `SKU_7` and ProGel `SKU_5` carry no text, so their prompts have no IMPORTANT sentence at all. Their whole frame is the composition.

---

## Retry policy

One retry, then stop. This is fixed by the architecture.

- Attempt 1 fails the Gemini gate → regenerate once, with the **same** prompt.
- Attempt 2 fails → mark the shot `needs_review` in the manifest, record both attempts and both gate verdicts, and **move on**. Do not loop further. Do not silently substitute a reference image.

Optionally, on the retry you may append one sentence derived from the gate's failure reason (e.g. `The product must be gray and silver, not blue.`). Log that you did so. Never alter the reserved-zone instruction on retry.

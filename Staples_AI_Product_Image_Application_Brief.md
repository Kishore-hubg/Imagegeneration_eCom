# Staples AI Product Image Application Brief

## Instruction to Claude Code

Build a working proof of concept application by following this document. Start with one product only. Do not generate assets for all four products until the first product has been reviewed and approved.

Use the supplied Developer Handoff document as the primary technical source. Read supporting product assets and brand guidelines only when required. Do not scan or load the complete asset collection into the model context.

## Project Objective

Create an AI-assisted application that transforms basic supplier product photographs into professional, Staples-compliant e-commerce marketing images.

**This brief applies to any product category** — cleaning supplies, writing instruments, seating/furniture, office accessories, and future SKUs. The pipeline, shot-mix rules, text policy and QA gates below are product-agnostic; only the per-SKU config (hero, approved copy, scene prompts) changes.

The application must:

1. Let a user select one of four supplied products.
2. Load the selected product's images, specifications and relevant brand rules.
3. Assemble a product-specific image brief and prompts.
4. Use Higgsfield and Gemini Nano Banana for image generation and controlled image editing.
5. Preserve the product's identity, shape, colour, proportions, logo and important physical details.
6. Prefer real-world **product-in-use / work-life / lifestyle** images over text-heavy graphic cards whenever the shot does not strictly require typography.
7. Reserve suitable blank areas for marketing copy **only when** an approved education overlay is required; otherwise ship a clean photo with no text.
8. Add accurate text through an HTML or canvas overlay (Playwright-rasterized) instead of relying on an image model to render important words or numbers.
9. Run automated visual quality checks using Gemini.
10. Retry a failed result for a maximum of two correction passes.
11. Export approved master images and marketplace-specific versions.

## Immediate Scope

The final interface should show four product options:

- Mop 1
- Mop 2
- Pen
- Chair

Only one selected product must be connected to the complete pipeline during the first proof of concept. The remaining buttons may display `Coming soon` or remain disabled with a clear status.

The first product workflow must be demonstrated and approved before processing the other three products. This protects image-generation credits and allows prompts to be corrected early.

## Shot Mix Policy (All Products)

This policy is mandatory for every SKU in the POC and for any future product added to the app. It is category-neutral: a mop, a pen, a chair, or any later Staples/Coastwide item follows the same rules.

### Prefer work-life / lifestyle imagery

For each product stack (typically 6–8 marketplace images), **bias strongly toward photorealistic scenes that show the product being used in a real workplace or real-life setting** — the same quality bar as a strong “product in use” lifestyle frame (worker using the item in a believable facility, office, classroom, kitchen, retail floor, etc.).

Examples of preferred frames (adapt setting to the product):

| Product type | Example work-life / lifestyle contexts |
|---|---|
| Floor care / mop | Office lobby, school corridor, hotel lobby, retail aisle, healthcare clinic |
| Cleaner / degreaser | Commercial kitchen, warehouse dock, restroom, workshop, cafeteria |
| Writing instrument | Desk in use, meeting room, classroom note-taking |
| Seating / chair | Open office workstation, conference room, home-office desk setup |

Each lifestyle scene in one SKU must be **visually distinct** (different room type, lighting, crop, and action) so the stack does not look repetitive.

### Deprioritize or replace weak text-based cards

Do **not** default to flat text/icon graphic cards when a lifestyle photo will sell the product better.

| Shot pattern | Default decision |
|---|---|
| Trust / satisfaction-guarantee panel (shield icon + placeholder copy) | **Do not generate.** Replace with a `photo_only` work-life scene. |
| Generic benefits list or icon row that is not required by marketplace education | Prefer a `photo_only` in-use lifestyle scene instead. |
| Surfaces / materials swatch grids that fail quality or lint | Prefer a lifestyle scene that *implies* the use context instead of a text-labeled swatch card. |
| Instructions / how-to text panels that are weak or incomplete | Prefer a work-life in-use photo unless approved step copy is mandatory and available. |
| Kit contents / feature callouts / true education overlays with approved copy | Keep as `photo_overlay` or `graphic_only` only when the marketplace benefit of exact text outweighs a clean photo. |

### No trust-guarantee icon cards

Satisfaction-guarantee / trust-social-proof graphics with a shield (or similar) icon and invented or placeholder promise copy are **out of scope for the demo**. For every product:

- Do not author or render trust-guarantee placeholder copy.
- Do not ship a dedicated “Satisfaction guaranteed” graphic card.
- Use that stack slot for an additional product-in-use lifestyle image instead.

### When generation quality is poor

If a text-heavy or graphic-only shot is not generating or rasterizing well (broken typography, empty cards, lint failures, unreadable overlays):

1. Prefer converting that shot to `photo_only` lifestyle / work-life generation rather than iterating endlessly on the graphic.
2. Keep overlays only for shots where approved, regulated, or marketplace-required wording must appear exactly.
3. Record the conversion in the SKU config changelog (`replaced_from`) so the decision is auditable.

### Text overlay rules (when text is still used)

- Never invent product claims; use approved source strings or declared placeholders only where the handoff explicitly allows them.
- Never place text on top of the product.
- Rasterize overlays with a real HTML renderer (Playwright / Chromium), not a string-scrape / Pillow stub that paints raw HTML tags into the image.
- Lifestyle `photo_only` shots carry **no text** — the photograph is the finished deliverable after the fidelity gate.
- **Text completeness (all products):** when a shot *does* require text, every approved headline, label, callout, count, value, step caption, footnote and disclaimer must appear as visible text in the rasterized overlay. Leader lines / icons alone are a failure. Incomplete or truncated HTML (`</html>` missing, mid-tag cutoff) must be rejected and retried — never composited.

### Config expectation per SKU

A healthy demo mix for any product should look approximately like:

- 1 hero / main image (passthrough of the real product on white when a clean hero exists)
- 1–2 education shots with exact text only if needed (contents, dimensions, feature callouts)
- **Majority of remaining slots:** `photo_only` work-life / lifestyle in-use scenes
- **Zero** trust-guarantee graphic cards

## AI Provider Responsibilities

### Higgsfield

Use Higgsfield as the primary creative generation provider when supported by the available account and API. It should produce polished lifestyle scenes, product compositions or campaign-style visuals based on the original product references and prompt.

Requirements:

- Use reference-image or image-to-image capability where available.
- Keep creative strength configurable.
- Preserve the original product accurately.
- Do not invent unsupported accessories, features, claims or specifications.
- Request composition with intentional negative space when marketing text is needed.
- Implement the integration as a provider adapter, not directly inside UI code.
- Confirm the currently available Higgsfield API endpoint, authentication method, model identifier, supported parameters and commercial usage terms from the supplied documentation or account before finalizing the call.
- If the account does not expose an official usable API, do not automate the website or invent an endpoint. Return a clear configuration error and allow Gemini Nano Banana to act as the configured generation fallback.

### Gemini Nano Banana

Use the Gemini image model available in the configured Google account for product-aware image generation or editing. Keep the exact model name configurable because Google may expose different Nano Banana model identifiers by account or API version.

Use it for:

- Reference-based generation or controlled editing.
- Product placement and background refinement.
- Creating alternate compositions.
- Correcting an image after visual-QA feedback.
- Acting as the generation fallback when Higgsfield is unavailable.

Do not hard-code a model identifier without checking that it is enabled for the supplied API key and region.

### Gemini Visual Review

Use a Gemini multimodal model to review the completed image after the text overlay is applied. Return structured JSON and validate it against a schema.

Review the following:

- Product identity and visual fidelity
- Shape, colour and proportions
- Logo and packaging accuracy
- Unsupported or invented features
- Background quality and realism
- Text spelling and number accuracy
- Text contrast, alignment and safe margins
- Staples brand compliance
- Marketplace image requirements
- Visible distortions, artifacts or cropping

## Required End to End Workflow

1. The user opens the application.
2. The user selects a product.
3. The application reads only that product's asset manifest and necessary files.
4. The application retrieves only the relevant Staples brand rules.
5. The prompt builder combines product facts, visual direction, channel rules and negative constraints, following the **Shot Mix Policy** (lifestyle-first for any product category).
6. The user previews the prompt and chooses Higgsfield or Gemini Nano Banana.
7. The selected provider generates the base marketing image.
8. If the shot is `photo_only` lifestyle / work-life: run fidelity gate, then treat the photo as the finished image (no text overlay).
9. If the design requires text, the model leaves an intentional blank area.
10. The application verifies that the intended text area is usable.
11. The application renders exact marketing text using HTML and CSS (Playwright rasterization) or a deterministic canvas library.
12. The text layer is composed over the generated image and exported.
13. Confirm that the text overlay is present, accurate and successfully composited when text is required. This is a mandatory gate before visual QA on overlay shots.
14. Gemini reviews the complete image (composite when text exists; gated photo when `photo_only`) and returns a structured score and issue list.
15. If the result fails, determine whether the issue belongs to the generated visual or the text overlay. Correct the appropriate layer, rebuild the final composite and submit that completed image to Gemini again. If a graphic/text card repeatedly fails, convert the slot to a lifestyle `photo_only` scene per Shot Mix Policy.
16. Stop after two correction passes and show the remaining issues for manual review.
17. If the result passes, export the approved master image and requested marketplace versions.

## Functional Requirements

### Product Selection

- Display a visual card or button for each of the four products.
- Clearly show which product is enabled for the proof of concept.
- Show asset readiness, generation status, QA status and export status.

### Asset Handling

- Preserve all source files as read-only.
- Use a manifest to locate product images and metadata.
- Validate file type, dimensions and file size.
- Never send unrelated products or the full 2.1 GB asset directory to an AI provider.
- Copy generated files into an output directory rather than modifying source assets.

### Prompt Assembly

Create prompts from structured inputs:

- Product name and category
- Verified specifications
- Source-image references
- Required scene or background (prefer real-world in-use / work-life settings for lifestyle slots)
- Staples brand rules
- Intended marketplace
- Required output dimensions
- Text and negative-space requirements (only when the shot type is `photo_overlay` or graphic education)
- Prohibited changes
- Previous QA feedback, when retrying
- Anti-repetition notes so multiple lifestyle scenes for one SKU do not look alike

Show the final assembled prompt in the UI for debugging, but do not expose secrets.

Lifestyle / work-life prompts must:

- Show the product being used in a believable real setting appropriate to that product category.
- Preserve product identity from the hero reference.
- Forbid readable invented signage, competitor branding, and unsupported accessories.
- Omit reserved empty zones when the shot is `photo_only` (no overlay will be added).

### Text Overlay

- Follow the **Shot Mix Policy** above: most lifestyle frames should have **no overlay**.
- The text overlay is part of the final marketing visual **only for shots that require approved education copy**, and must be completed before Gemini visual QA on those shots.
- Do not treat the overlay as a later optional enhancement or post-QA step when text is required.
- Do not create trust-guarantee / shield-icon graphic cards for any product.
- Store copy as structured fields, not as text embedded in the generation prompt.
- Render text deterministically using approved fonts, sizes and colours via HTML/CSS rasterized with Playwright (or equivalent Chromium screenshot), not a naive text extractor.
- **Never ship an overlay that is missing approved text.** Lint must fail if HTML is truncated or if any approved headline/label/callout/value/item value/supporting line/footnote is absent from the markup. Retry the designer once with thinking disabled; if still incomplete, mark `needs_review` — do not composite lines without labels.
- Overlay generation must use Claude with **thinking disabled** (Opus 5+ defaults to adaptive thinking, which can burn the entire token budget and return an empty body). Keep reasoning effort at `medium` or lower for overlays.
- Support heading, short description, specifications, callouts, steps, item values and disclaimer fields when needed — across every product category (furniture dimensions, cleaner specs, pen features, mop contents, etc.).
- Calculate wrapping and safe margins.
- Never allow text to cover the product.
- Export the composition at the required resolution.
- Preserve both the raw generated image and the final composited image, but send the final composited image to visual QA when an overlay exists; for `photo_only`, the gated photo is the final.

### Visual QA

Visual QA begins only after the correct text has been overlaid on the generated visual. The QA input must be the final composite containing the product visual and its text overlay. The QA response must use a structure similar to:

```json
{
  "status": "PASS",
  "overall_score": 92,
  "product_fidelity_score": 95,
  "brand_compliance_score": 90,
  "text_accuracy_score": 100,
  "marketplace_compliance_score": 88,
  "issues": [],
  "correction_instructions": []
}
```

Fail the image when:

- The product has materially changed.
- A logo, feature, measurement or number is wrong.
- Text is misspelled or unreadable.
- A brand rule is violated.
- Required marketplace specifications are not satisfied.
- The overall score or any mandatory category falls below the configured threshold.

Default overall pass threshold: `90/100`. Product fidelity and text accuracy are mandatory pass categories.

### Marketplace Export

Create configuration files for Amazon, Walmart, Target and Best Buy. Do not guess their current specifications. Put verified requirements in configuration and record the source and verification date.

Support configurable:

- Width and height
- Aspect ratio
- File format
- Maximum file size
- Background rules
- Text restrictions
- Safe margins
- Naming convention

## Recommended Technical Architecture

Use a simple, maintainable stack unless the Developer Handoff requires another one:

- Front end: React with TypeScript
- Back end: FastAPI with Python
- Image composition: Pillow or Sharp plus HTML and CSS rendering when needed
- Validation: Pydantic models
- Job state for the POC: SQLite or local JSON metadata
- Generated asset storage for the POC: local output folders
- Production-ready storage interface: object-storage adapter
- AI integrations: separate Higgsfield, Gemini image and Gemini QA adapters

Do not place API keys in source code, browser code, logs or generated files.

## Suggested Project Structure

```text
staples-product-image-poc/
|-- README.md
|-- .env.example
|-- docker-compose.yml
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- services/
|   |   `-- types/
|   `-- package.json
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- models/
|   |   |-- services/
|   |   |   |-- asset_service.py
|   |   |   |-- prompt_service.py
|   |   |   |-- overlay_service.py
|   |   |   |-- qa_service.py
|   |   |   `-- export_service.py
|   |   |-- providers/
|   |   |   |-- base.py
|   |   |   |-- higgsfield_provider.py
|   |   |   |-- gemini_image_provider.py
|   |   |   `-- gemini_qa_provider.py
|   |   `-- main.py
|   |-- tests/
|   `-- requirements.txt
|-- config/
|   |-- products.yaml
|   |-- brand_rules.yaml
|   |-- marketplaces.yaml
|   `-- qa_rules.yaml
|-- source_assets/
|   |-- product_01/
|   |-- product_02/
|   |-- product_03/
|   `-- product_04/
|-- generated_outputs/
|-- docs/
|   |-- developer_handoff/
|   `-- brand_guidelines/
`-- scripts/
```

Adapt this structure when the Developer Handoff specifies an existing technology or directory convention.

## Environment Configuration

Create `.env.example` with placeholders only:

```env
HIGGSFIELD_API_KEY=
HIGGSFIELD_BASE_URL=
HIGGSFIELD_MODEL=
GEMINI_API_KEY=
GEMINI_IMAGE_MODEL=
GEMINI_QA_MODEL=
GENERATION_PROVIDER=higgsfield
GENERATION_FALLBACK_PROVIDER=gemini
QA_PASS_THRESHOLD=90
MAX_QA_RETRIES=2
SOURCE_ASSET_ROOT=./source_assets
OUTPUT_ROOT=./generated_outputs
```

## Minimum API Endpoints

- `GET /api/products`
- `GET /api/products/{product_id}`
- `POST /api/generations`
- `GET /api/generations/{job_id}`
- `POST /api/generations/{job_id}/overlay`
- `POST /api/generations/{job_id}/qa`
- `POST /api/generations/{job_id}/retry`
- `POST /api/generations/{job_id}/export`
- `GET /api/providers/health`

Long-running generation must use a job-based workflow. The UI should poll job status or use server-sent events. Do not hold a browser request open indefinitely.

## Error Handling and Controls

- Validate provider credentials during startup or through a health endpoint.
- Use timeouts, limited retries and exponential backoff for temporary API errors.
- Do not retry authentication, validation or insufficient-credit errors automatically.
- Display estimated or returned credit usage when available.
- Prevent duplicate generation when the user clicks twice.
- Store the prompt, provider, model, timestamp, source-asset identifiers and QA result for each output.
- Do not log API keys or raw authorization headers.
- Reject unsupported file types and untrusted paths.

## Proof of Concept Deliverables

Claude Code must produce:

1. A runnable front-end and back-end application.
2. Four product-selection cards, with one product fully enabled.
3. Higgsfield and Gemini Nano Banana provider adapters.
4. A working one-product generation pipeline.
5. Deterministic text-overlay functionality.
6. Gemini visual QA with a maximum of two correction passes.
7. Configurable marketplace export profiles.
8. Unit tests for prompt assembly, QA parsing, overlays and provider error handling.
9. A `.env.example` file without secrets.
10. A README containing setup, configuration, execution and troubleshooting instructions.
11. Sample output metadata and QA reports.
12. A clear list of assumptions and any unavailable provider capabilities.

## Acceptance Criteria

The proof of concept is complete when:

- The application starts using documented commands.
- The interface displays all four products.
- One product successfully runs through asset selection, prompt creation, generation, text overlay (when required), Gemini QA and export.
- The shot mix for that product follows the **Shot Mix Policy**: majority work-life / lifestyle in-use images; no trust-guarantee icon card; weak text/graphic cards replaced with lifestyle when they do not generate well.
- The application blocks final Gemini QA until the text overlay has been created and composited successfully **on shots that require text**; `photo_only` lifestyle shots skip overlay and QA the photo itself.
- The generated product remains visually faithful to the supplied reference.
- Important copy and numbers are rendered accurately outside the image model when overlays are used.
- Failed QA generates actionable correction instructions.
- No more than two automatic correction passes occur.
- Source assets remain unchanged.
- Secrets are never committed or exposed in the interface.
- The result, prompt, provider details and QA decision are traceable.
- The generated images and QA report can be downloaded.
- The same shot-mix and lifestyle preference rules are written so they can be applied unchanged to any additional product category.

## Required Implementation Order

1. Inspect the Developer Handoff and determine the existing technical constraints.
2. Map the supplied directories without modifying them.
3. Confirm API access and model names for Higgsfield and Gemini.
4. Scaffold the front end and back end.
5. Implement product and asset discovery.
6. Implement prompt assembly.
7. Implement Gemini Nano Banana generation first as the testable baseline.
8. Implement the Higgsfield adapter using the verified API contract.
9. Implement deterministic text overlays.
10. Implement Gemini visual QA and the two-pass correction loop.
11. Implement marketplace export profiles.
12. Test the entire workflow with one product.
13. Share one-product results for approval.
14. Do not enable bulk generation for the remaining products until approval is received.

## Final Instruction to Claude Code

Begin by producing a short implementation plan based on the Developer Handoff, then build the application. Ask for clarification only when a missing choice materially blocks implementation. Keep all provider-specific logic isolated behind adapters. Never invent API endpoints, product claims, marketplace specifications or brand rules. Where an external capability is unavailable, provide a functional mock mode and clearly mark it as simulated.

**Shot-mix reminder (any product):** Prefer real-world product-in-use / work-life lifestyle images. Do not ship trust-guarantee icon cards. When text-based or graphic cards fail quality, convert those slots to lifestyle `photo_only` scenes rather than forcing broken typography. Keep exact-text overlays only where approved education copy is required, and rasterize them with Playwright.

The first milestone is a complete, reviewable workflow for one product that already demonstrates this lifestyle-first mix.

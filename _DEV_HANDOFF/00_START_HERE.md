# Start here

**Project:** Staples / Coastwide marketplace image generation — proof of concept
**For:** the engineer building this
**From:** Pratyoosh Patel, InfoVision
**Date:** 15 September 2026

---

## What you are building, in one paragraph

Staples sells own-brand products. Each one arrives from the manufacturer with one or two plain photographs and a rough description. Every marketplace that sells it — Amazon, Walmart, Target, Best Buy, Staples.com — wants six finished images per product: a clean hero shot, the product being used in a real workplace, benefit cards, spec callouts. Today a photo-retouching agency does this by hand for $1,000–2,000 per product. You are building a pipeline that does it for roughly $200, and a small web app that demonstrates it.

The goal is a demo good enough for our client to show his own team at Staples. It is not a production system. Be pragmatic.

---

## The six-minute version of how it works

Someone opens a page showing four product cards. They click one. That click is the entire input — there is no upload, no form, no settings.

The backend looks up a config file for that product. The config lists six to eight images to produce, decided in advance. Each one takes one of a few paths — but two of them do the real work:

**Kind one: a graphic card.** A benefits list, a spec table, a grid of surface swatches. No photography involved. Claude is handed the brand rules and the exact approved wording, writes HTML and SVG, and that gets turned into a PNG. Nothing to judge — it's either the right hex code and the right words or it isn't, and a linter checks.

**Kind two: a photo with text on it.** The product in a real setting with a benefit line in the corner. Four steps, in order:

1. Nano Banana generates the scene, given the product's real hero photo as reference. The prompt explicitly tells it to *leave a specific corner of the frame empty*. That one instruction is the trick that makes the rest work.
2. Gemini looks at the raw photo and answers one question: is this still the right product, in a sensible setting, with no stray logos? One retry if not. Fail twice and the shot is flagged and the pipeline moves on.
3. Claude — now actually **looking at** that photo — designs the text overlay. It can see where the empty corner landed and how bright it is, so it places and colors the text against the real image rather than guessing.
4. The overlay is rasterized and composited onto the photo.

Two shots skip the overlay entirely — the generated photo *is* the finished image. And the main image skips generation entirely: the real hero photo is simply recomposed onto a pure-white square, because regenerating a product you already have a clean photo of risks accuracy for no gain.

Because the overlay is vector, resizing it for different marketplaces is free. And because all five channels want a square image, everything collapses into just two output sizes.

The screen shows a checklist ticking over as each image finishes. At the end: a download button with a zipped folder.

---

## The three rules that matter more than the code

**1. Never invent product copy — and where copy *is* invented, declare it.** Two of the four products are EPA-regulated cleaning chemicals. Every word on a generated image must trace to an approved string, to Staples' own published art, or to an explicitly declared placeholder. Each shot says which via `text_provenance`. You may split a sentence in two, shorten a label, or fix capitalization. You may not add a word, a number, a percentage or a certification of your own.

The hard limit on placeholders: **generic reassurance is fine, a specific number is not.** No dilution ratios, contact times, kill claims, certifications, refund periods or warranty terms. Those are what cause real harm if a demo screenshot escapes the room.

**2. Never put anything on top of the product.** Both style guides state it outright. It's why the reserved-empty-corner trick exists.

**3. Never substitute a real Staples image for a generated one.** Every product folder contains Staples' own finished production images. They're there so you can compare your output against the real thing. If one ever ends up in an output folder labelled as generated, the credibility of the whole exercise goes with it.

---

## What's in this folder

| | |
|---|---|
| `00_START_HERE.md` | this page |
| `01_BUILD_INSTRUCTIONS.md` | the real one — stage by stage, written to be fed to Claude Code |
| `02_FILE_MANIFEST.md` | which files matter, which are noise, which is the hero image for each product |
| `03_SHOT_PLANS.md` | the image-by-image plan in plain English, for a human to read |
| `04_PLATFORM_TARGETS.md` | what the five marketplaces require, what's confirmed and what isn't |
| `05_ACCEPTANCE_TESTS.md` | how you prove it works without asking anyone |
| `06_DECISIONS_LOG.md` | every judgment call that shaped the build — read this, it affects what you build |
| `07_SETUP_AND_ENABLEMENT.md` | **start here practically** — keys, installs, the Higgsfield smoke test, the setup checklist |
| `config/` | the pre-built JSON: two brand rulesets, the platform targets, four product configs |
| `prompts/` | the exact prompt templates for all three models, plus the lint rules |
| `.env.example` | copy to `.env`, fill in the keys — see `07` for how to get the Higgsfield ones |

---

## Day one, in order

1. Read this page and `06_DECISIONS_LOG.md`. Twenty minutes.
2. Work through `07_SETUP_AND_ENABLEMENT.md` — installs, key checks, and the Higgsfield smoke test. That doc has a checklist; tick it as you go.
3. Skim `02_FILE_MANIFEST.md` so you know what you're pointing at.
4. Open `01_BUILD_INSTRUCTIONS.md` and start at Stage 0.

**Stage 0 is mock mode, and it matters.** You do not need a single API key to build the orchestrator, the job state machine, the frontend, the polling, the compositing or the zip packaging. In mock mode every shot returns the real finished Staples image from the product folder instead of calling an API. Build the entire skeleton that way and get it running end to end. Then drop the keys in and only the three model calls change.

That ordering means you're not blocked waiting on the Higgsfield account, and it means when the keys do land you're debugging one thing at a time instead of five.

---

## Three things you should know going in

**All four products have complete shot plans.** 29 shots in total, 16 of them generated photographs. No SKU is tabled, no card is disabled.

**The finished reference images are your test oracle.** The ExpressMop is the best example: Staples' own finished versions of six of its eight images are sitting in its folder. Generate, put yours beside theirs, and the gap is immediately visible to anyone in the room. That comparison *is* the demo.

**A few strings are deliberate placeholders.** Two satisfaction-guarantee lines were written by us because Staples' real wording isn't in the folder. They're marked `text_provenance: "PLACEHOLDER_POC"`, they carry a `placeholder_declaration` block explaining exactly what's invented, and they must appear in `manifest.json` and the package README. Don't quietly drop that plumbing — it's how anyone can find every made-up string in one query before these images travel anywhere.

---

## How this gets reviewed

No calls or status meetings. Pratyoosh reviews daily from what's in the folder, so keep `_DEV_HANDOFF/DAILY_NOTES.md` up to date — stage reached, anything blocked, anything you decided differently from these instructions. `07_SETUP_AND_ENABLEMENT.md` §8 has the format.

Flag blockers the day they appear, especially anything about the Higgsfield account. Those are the only things you can't solve yourself.

Questions go to Pratyoosh directly — pratyoosh.patel@infovision.com. Everything in `06_DECISIONS_LOG.md` is already settled; you don't need to chase any of it.

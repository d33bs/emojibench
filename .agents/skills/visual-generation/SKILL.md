---
name: visual-generation
description: |
  Create coherent image-generation prompts, pick output styles, and record
  asset licensing and provenance metadata. Use when generating or reviewing
  emojibench assets, writing provider prompts, or deciding whether an image
  is safe to publish.
license: MIT
---

# Visual Generation: prompts, styles, and provenance

Use this skill when you generate, review, or approve emojibench assets.

## Principles

1. Fun mashups come first. Ship a working combination before a perfect one.
2. Every published image needs provenance: who made it, how, and under what
   license. An image without provenance cannot be approved.
3. Never copy Google's Emoji Kitchen artwork or any unlicensed emoji art.
   Draw original art, or use assets with an explicit compatible license.
4. A mock provider's output is a placeholder, not a model result. Label it
   as a mock in metadata and in the interface. Never present mock output
   as generative-model output.
5. Human approval happens before publication. Automated checks and vision
   model scores are suggestions, not approval.

## Prompt writing

Write prompts as a short creative brief with these parts:

- Subjects: the two concepts, named plainly ("a macrophage" + "a superhero").
- Style: one named style, e.g. "flat cartoon", "children's science book",
  "simple line art". Keep it consistent within a story.
- Constraints: background, palette, no-text rules, aspect ratio.
- Scientific intent (when applicable): what the image should convey about
  the subject, phrased as interpretation, not observation.

Bad prompt: "cool science emoji, high quality, 4k".
Good prompt: "A friendly macrophage drawn as a superhero, flat cartoon style,
single character, solid pastel background, no text, square canvas. The intent
is playful analogy: the macrophage 'rescues' by engulfing pathogens."

## Style guide

- Default demo style: flat, friendly, single-subject, solid background,
  no text in the image.
- Keep the palette to 5 colors or fewer per asset.
- Prefer SVG for catalog assets. Generate PNG only when a provider requires
  raster output.
- Keep the two source concepts recognizable in a mashup. If a reviewer cannot
  tell what the inputs were, the combination failed the brief.

## Provenance metadata

Every generated asset record must carry `generation_metadata` with at least:

- provider name and model identifier (or "mock")
- prompt or creative brief, when shareable
- settings (size, style seed if any)
- generation timestamp
- output checksum
- rights status and license
- review state (draft, approved, rejected)

Never commit API credentials or secrets into metadata or prompt files.

## Cost and safety limits

- Paid providers must be explicitly enabled by environment variables.
  An unconfigured installation never makes network calls.
- Set per-job cost or call limits before running a paid provider.
- A generation job must have a timeout and bounded retries.
- Failures surface as user-facing errors with the cause, not silent skips.

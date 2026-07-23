# Controlled Veo renderer

NotebookLM's **Cinematic Video Overview** endpoint does not expose Veo's public
API controls. The `notebooklm.veo_cli` module provides an experimental hybrid
workflow:

1. Use NotebookLM to read the selected sources and produce a grounded shot
   prompt or storyboard.
2. Render each shot through the official Gemini API Veo endpoint.
3. Assemble the downloaded clips in your editor or an FFmpeg workflow.

This does **not** disable Google's server-side safety, privacy, copyright, bias,
or policy enforcement. It exposes only documented generation controls.

## Requirements

The base package already includes `click` and `httpx`, so no additional Python
dependency is needed. Set a Gemini API key in the environment:

### PowerShell

```powershell
$env:GEMINI_API_KEY = "your-key"
```

### Bash

```bash
export GEMINI_API_KEY="your-key"
```

## Inspect a request without generating

```powershell
python -m notebooklm.veo_cli `
  --prompt-file ".\V5_FACE_VISIBLE_SAFE.md" `
  --person-generation allow_all `
  --composition "eye-level medium close-up, both eyes visible" `
  --camera "slow dolly-in, subject remains facing camera" `
  --lens "50mm lens, shallow depth of field focused on the face" `
  --ambiance "soft frontal key and fill lighting" `
  --duration 8 `
  --resolution 1080p `
  --dry-run
```

`--composition`, `--camera`, `--lens`, and `--ambiance` are intentionally added
to the text prompt. Veo documents those as prompt concepts rather than separate
REST parameters.

## Generate a text-to-video clip

```powershell
python -m notebooklm.veo_cli `
  --prompt-file ".\scene-01.md" `
  --person-generation allow_all `
  --composition "medium close-up portrait, full face unobstructed" `
  --camera "eye-level slow lateral track while preserving a three-quarter face" `
  --lens "50mm lens, face in sharp focus" `
  --ambiance "natural daylight with soft frontal fill" `
  --negative-prompt "rear-only view, silhouette, face covered by props" `
  --duration 8 `
  --resolution 1080p `
  --output ".\scene-01.mp4" `
  --save-operation ".\scene-01-operation.json"
```

## Use person or character references

Veo 3.1 accepts up to three asset reference images. Reference-image and other
image-guided modes use adult-person generation. They also require an eight-second
clip.

```powershell
python -m notebooklm.veo_cli `
  --prompt-file ".\scene-02.md" `
  --reference-image ".\character-front.png" `
  --reference-image ".\character-three-quarter.png" `
  --person-generation allow_adult `
  --duration 8 `
  --resolution 1080p `
  --output ".\scene-02.mp4"
```

## Lock the beginning and ending composition

```powershell
python -m notebooklm.veo_cli `
  "The presenter turns toward the camera and explains the central finding." `
  --first-frame ".\scene-start.png" `
  --last-frame ".\scene-end.png" `
  --person-generation allow_adult `
  --duration 8 `
  --output ".\scene-03.mp4"
```

## Practical overview workflow

Ask NotebookLM for a sequence of short, source-grounded scenes. Each scene should
contain:

- narration or dialogue;
- subject and action;
- composition;
- camera positioning and movement;
- lens/focus treatment;
- lighting and ambiance;
- any reusable reference-image filenames.

Render one four-, six-, or eight-second clip per scene. Reference images, 1080p,
and 4K generation require eight seconds. For longer output, render multiple
shots and assemble them afterward. A direct Veo call is a shot renderer, not a
replacement for NotebookLM's automatic long-form editing and narration pipeline.

## Important limitation

Changing `src/notebooklm/_artifact/payloads.py` cannot add these controls to
NotebookLM Cinematic. That RPC sends source IDs, language, instructions, and the
Cinematic format code; Google chooses the internal storyboard and Veo settings.
The controlled renderer is separate on purpose so unsupported fields are not
silently ignored or mistaken for safety overrides.

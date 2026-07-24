# Reference-conditioned NotebookLM Cinematic Video Overview

This workflow adapts the useful portions of the internal design report
**NotebookLM Veo Integration Workflow** into the existing hybrid pipeline.
NotebookLM remains responsible for source grounding and the native Cinematic
Video Overview narration. Direct Gemini API Veo 3.1 calls render replacement
visual scenes with explicit subject references and shot controls.

## What was incorporated

- Source-grounded JSON scene planning before paid video generation.
- Per-scene visual prompts, narration anchors, dialogue cues, ambient-audio cues,
  composition, camera, lens, lighting, and negative prompts.
- Up to three asset reference images for one recurring adult subject, character,
  or product.
- Explicit mutually exclusive generation modes: `text`, `reference`,
  `interpolation`, and `extension`.
- Automatic Veo constraints:
  - reference and interpolation modes use 8-second clips and `allow_adult`;
  - extension mode uses 8 seconds, 720p, and `allow_all`;
  - reference images cannot be combined with first/last frames or extension.
- Immediate download of every completed scene and persistent operation JSON.
- Optional continuation shots through Veo extension. The extension result is a
  combined video, so only its new seven-second tail is used as the scene clip.
- Final FFmpeg assembly using narration extracted from the native NotebookLM
  Cinematic Video Overview.

## Corrections to the design report

The report contains useful architectural ideas, but some claims are speculative,
provider-specific, or time-sensitive. The implementation therefore does not:

- claim knowledge of NotebookLM's private internal model routing;
- guarantee deterministic facial identity;
- hard-code pricing, latency, quotas, or regional availability;
- assume that Vertex AI stable model IDs have the same reference-image features
  as the Gemini API preview models;
- use unsupported SDK workarounds when the documented Gemini REST `inlineData`
  shape is sufficient;
- attempt to weaken Google's safety, privacy, copyright, or identity controls.

Current Gemini API documentation describes Veo 3.1 reference images, first/last
frames, video extension, 4/6/8-second generation, 720p/1080p/4K output, and
server-side two-day retention. Always re-check official documentation before a
production rollout because preview capabilities can change.

## Storyboard schema

```json
{
  "schema_version": 2,
  "title": "Controlled Cinematic Overview",
  "summary": "Source-grounded summary",
  "subjects": [
    {
      "id": "presenter",
      "description": "fictional or authorized adult presenter",
      "reference_images": [
        "references/presenter-front.png",
        "references/presenter-three-quarter.png"
      ]
    }
  ],
  "scenes": [
    {
      "id": "scene-001",
      "title": "Opening",
      "narration": "Explain the source-supported central question.",
      "visual_prompt": "A realistic adult presenter introduces the topic in a modern office.",
      "dialogue": "",
      "ambient_audio": "quiet room tone",
      "subject_ids": ["presenter"],
      "generation_mode": "reference",
      "composition": "eye-level medium close-up, complete unobstructed face",
      "camera": "restrained dolly-in preserving a natural three-quarter angle",
      "lens": "50mm natural perspective, face in sharp focus",
      "ambiance": "soft balanced frontal light with natural skin tones",
      "negative_prompt": "rear-only view, silhouette, hidden or distorted face",
      "duration_seconds": 8,
      "first_frame": null,
      "last_frame": null,
      "extend_from_scene": null
    }
  ]
}
```

## Consent and identity boundary

Reference-image runs require `--confirm-authorized-adult`. Use reference images
only for fictional adults or adults whose likeness you are authorized to use.
The flag records operator intent; it does not bypass provider review or guarantee
that the generated subject will match the images exactly.

## Plan without spending Veo credits

```powershell
uv run python scripts/controlled_cinematic_reference_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "Create a source-grounded documentary with one recurring presenter" `
  --scene-count 10 `
  --plan-only `
  --workspace ".\controlled-reference-work"
```

Review:

```text
controlled-reference-work/storyboard.json
controlled-reference-work/reference-plan.json
```

## Full reference-conditioned run

```powershell
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

uv run python scripts/controlled_cinematic_reference_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "Create a source-grounded documentary with an authorized adult presenter" `
  --storyboard-file ".\storyboard.json" `
  --subject-reference "presenter=.\references\presenter-front.png" `
  --subject-reference "presenter=.\references\presenter-three-quarter.png" `
  --confirm-authorized-adult `
  --model veo-3.1-fast-generate-preview `
  --aspect-ratio 16:9 `
  --resolution 1080p `
  --workspace ".\controlled-reference-work" `
  --output ".\controlled-reference-overview.mp4"
```

## Optional Veo dialogue and ambience

By default, the final video discards Veo scene audio and uses the NotebookLM
Video Overview narration. Add `--include-veo-audio-cues` only when previewing
lip movement or scene sound. Those cues are included in Veo prompts, but the
final assembly still uses the extracted NotebookLM narration track.

## Extension scenes

An extension scene must appear after its base scene:

```json
{
  "id": "scene-002",
  "generation_mode": "extension",
  "extend_from_scene": "scene-001",
  "visual_prompt": "The same continuous shot follows the presenter toward the display.",
  "duration_seconds": 8
}
```

Extension requires 720p and produces a combined video. The pipeline preserves
that full combined asset under `extensions/` for another extension, while the
new seven-second tail is extracted into `clips/` for final assembly.

## Output

```text
controlled-reference-work/
├── storyboard.json
├── reference-plan.json
├── notebooklm-video-overview.mp4
├── notebooklm-video-narration.m4a
├── requests/
├── operations/
├── extensions/
├── clips/
├── normalized/
└── manifest.json
```

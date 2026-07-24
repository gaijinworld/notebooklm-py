# Controlled Cinematic Overview pipeline

This workflow adds the long-form orchestration layer that the single-shot
`notebooklm.veo_cli` renderer does not provide.

```text
NotebookLM sources
        |
        +--> NotebookLM chat: grounded JSON scene storyboard
        |
        +--> NotebookLM Audio Overview: final narration track
                         |
                         v
               controlled Veo 3.1 renderer
                         |
                 scene-001.mp4 ... scene-N.mp4
                         |
                         v
              FFmpeg normalize + concatenate
                         |
                         v
          final MP4 with NotebookLM narration audio
```

The pipeline is separate from NotebookLM's native Cinematic Video Overview RPC.
That RPC remains available but does not accept Veo's public `personGeneration`,
reference-image, resolution, duration, or frame-control fields. The pipeline uses
NotebookLM for grounded planning and narration, then calls the existing direct
Veo 3.1 renderer for each scene.

Google's server-side safety, privacy, copyright, regional, and policy enforcement
remains active. This workflow gives the user supported shot controls; it is not a
safety bypass.

## Requirements

1. Install this checkout and authenticate NotebookLM:

   ```powershell
   uv sync --frozen --extra browser
   uv run notebooklm login
   ```

2. Install FFmpeg so both `ffmpeg` and `ffprobe` are available on `PATH`.

3. Set a paid-tier Gemini API key that can access Veo 3.1:

   ```powershell
   $env:GEMINI_API_KEY = "your-key"
   ```

## Generate a full overview

From the repository root:

```powershell
uv run python scripts/controlled_cinematic_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "Explain the selected sources as a cinematic documentary" `
  --profile "default" `
  --scene-count 12 `
  --person-generation allow_all `
  --aspect-ratio 16:9 `
  --duration 8 `
  --resolution 1080p `
  --audio-format brief `
  --audio-length long `
  --workspace ".\controlled-cinematic-work" `
  --output ".\controlled-cinematic-overview.mp4"
```

By default, all notebook sources are used. Repeat `--source` with full source IDs
to ground the storyboard and narration in a selected subset.

## Use character reference images

Reference images improve visual identity continuity across independently rendered
scenes. Veo 3.1 accepts up to three references. Image-guided generation uses
adult-person mode and eight-second scenes.

```powershell
uv run python scripts/controlled_cinematic_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "A source-grounded documentary with a consistent fictional presenter" `
  --reference-image ".\references\presenter-front.png" `
  --reference-image ".\references\presenter-three-quarter.png" `
  --scene-count 16 `
  --resolution 1080p `
  --output ".\overview-with-presenter.mp4"
```

When references are present, the pipeline automatically uses
`personGeneration=allow_adult`. Without image guidance, text-to-video uses
`allow_all`.

## Review the storyboard before paying for Veo

Use `--plan-only` to ask NotebookLM for the source-grounded storyboard, validate
its JSON shape, and stop before generating audio or video:

```powershell
uv run python scripts/controlled_cinematic_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "Explain GPON and XGS-PON verification" `
  --scene-count 10 `
  --plan-only
```

The plan is written to:

```text
controlled-cinematic-work/storyboard.json
```

Edit that JSON when exact shot-by-shot control is needed, then rerun with:

```powershell
--storyboard-file ".\controlled-cinematic-work\storyboard.json"
```

## Resume an interrupted generation

`--resume` is enabled by default. Existing files are reused:

- `storyboard.json`
- `narration.mp3`
- `clips/scene-###.mp4`
- `normalized/scene-###.mp4`

The final manifest is saved as `manifest.json`. Use `--no-resume` to regenerate
all stages.

## Supply an existing storyboard or narration

NotebookLM remains the recommended source-grounding engine, but individual stages
can be supplied manually:

```powershell
uv run python scripts/controlled_cinematic_pipeline.py `
  --topic "Custom production" `
  --storyboard-file ".\approved-storyboard.json" `
  --narration-audio ".\approved-narration.mp3" `
  --output ".\final.mp4"
```

When both files are supplied, `--notebook` is not required.

## Storyboard format

```json
{
  "title": "Overview title",
  "summary": "Editorial summary",
  "scenes": [
    {
      "title": "Scene 1",
      "narration": "Narration idea grounded in the notebook sources.",
      "visual_prompt": "A fictional adult presenter explains the finding in a modern office.",
      "composition": "Eye-level medium close-up, full face unobstructed",
      "camera": "Slow dolly-in while maintaining a three-quarter face",
      "lens": "50mm lens, face in sharp focus",
      "ambiance": "Soft frontal daylight with natural skin tones",
      "negative_prompt": "Rear-only view, silhouette, hidden face",
      "duration_seconds": 8
    }
  ]
}
```

## Audio and synchronization behavior

NotebookLM Audio Overview is the authoritative final audio. Veo's native audio is
removed while clips are normalized. Because Audio Overview does not expose
frame-accurate scene timestamps, the pipeline keeps thematic scene order and
repeats the complete visual sequence when the narration is longer than one pass.
The final mux uses the narration duration as the endpoint.

For frame-accurate editorial synchronization, review `storyboard.json`, render
more scenes, or edit the normalized clips in an NLE before the final mux.

## Output structure

```text
controlled-cinematic-work/
├── storyboard.json
├── storyboard-raw.txt
├── narration.mp3
├── clips/
│   ├── scene-001.mp4
│   └── ...
├── operations/
│   ├── scene-001.json
│   └── ...
├── normalized/
│   ├── scene-001.mp4
│   └── ...
├── concat.txt
├── assembled-silent.mp4
└── manifest.json
```

## Cost and quota warning

Each scene is a separate Veo generation. Start with `--plan-only`, a small scene
count, the Fast model, and 720p while validating prompts. Increase scene count or
resolution only after the storyboard and reference strategy are approved.

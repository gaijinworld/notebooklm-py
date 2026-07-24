# Controlled Cinematic Video Overview pipeline

This workflow uses NotebookLM's native **Cinematic Video Overview** as the
source-grounded narration source, while direct Veo 3.1 renders the controlled
visual scenes.

```text
Selected NotebookLM sources
        |
        v
NotebookLM Chat
source-grounded JSON storyboard
        |
        v
NotebookLM Cinematic Video Overview
source-grounded narration embedded in the native MP4
        |
        v
FFmpeg audio extraction
NotebookLM narration-only M4A
        |
        v
Direct Veo 3.1 renderer
scene-001.mp4 ... scene-N.mp4
        |
        v
FFmpeg normalize + concatenate
        |
        v
Final MP4 with extracted NotebookLM Video Overview narration
```

The pipeline does not alter NotebookLM's undocumented Cinematic RPC. NotebookLM
is used for source-grounded planning and native Video Overview narration. The
direct Veo endpoint is used for controlled visual rendering because the native
NotebookLM payload does not accept the public Veo people, reference-image,
resolution, duration, or frame controls.

The native NotebookLM Video Overview's **visual track is not reused** in the
final output. FFmpeg extracts only its narration audio, then the final assembly
uses the separately rendered Veo clips.

Google's server-side safety, privacy, copyright, regional, and policy
enforcement remains active. This workflow exposes supported controls; it is not
a safety bypass.

## Requirements

Authenticate NotebookLM:

```powershell
uv sync --frozen --extra browser
uv run notebooklm login
```

Install FFmpeg so `ffmpeg` and `ffprobe` are available on `PATH`.

Set a Gemini API key with Veo 3.1 access:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

## Generate a complete customized overview

Run from the repository root:

```powershell
uv run python scripts/controlled_cinematic_video_overview_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "Explain the selected sources as a cinematic documentary" `
  --profile "default" `
  --scene-count 12 `
  --person-generation allow_all `
  --aspect-ratio 16:9 `
  --duration 8 `
  --resolution 1080p `
  --workspace ".\controlled-video-overview-work" `
  --output ".\controlled-video-overview.mp4"
```

The command performs these stages:

1. NotebookLM Chat creates `storyboard.json`.
2. NotebookLM generates a native Cinematic Video Overview.
3. The completed native MP4 is downloaded.
4. FFmpeg extracts its narration to `notebooklm-video-narration.m4a`.
5. Direct Veo 3.1 renders every storyboard scene.
6. FFmpeg normalizes and concatenates the Veo clips.
7. The extracted NotebookLM narration is muxed into the final MP4.

By default, all notebook sources are used. Repeat `--source` with complete source
IDs to ground both the storyboard and native Video Overview in a selected
subset.

## Review the storyboard before video generation

```powershell
uv run python scripts/controlled_cinematic_video_overview_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "Explain GPON and XGS-PON verification" `
  --scene-count 10 `
  --plan-only
```

This stops before NotebookLM Video Overview generation and before Veo rendering.
The storyboard is saved at:

```text
controlled-video-overview-work/storyboard.json
```

Edit it and rerun with:

```powershell
--storyboard-file ".\controlled-video-overview-work\storyboard.json"
```

## Add Video Overview instructions

Create a text file:

```text
Use one polished documentary narrator.
Follow the supplied scene order.
Explain the selected sources clearly.
Do not mention production tools.
```

Pass it with:

```powershell
--video-overview-instructions-file ".\video-overview-instructions.txt"
```

These instructions affect the native NotebookLM Cinematic Video Overview whose
audio becomes the final narration.

## Reuse an existing NotebookLM Video Overview

```powershell
uv run python scripts/controlled_cinematic_video_overview_pipeline.py `
  --topic "Custom production" `
  --storyboard-file ".\approved-storyboard.json" `
  --video-overview-file ".\approved-notebooklm-video.mp4" `
  --output ".\final.mp4"
```

When both files are supplied, `--notebook` is not required.

## Use character reference images

```powershell
uv run python scripts/controlled_cinematic_video_overview_pipeline.py `
  --notebook "YOUR_NOTEBOOK_ID" `
  --topic "A source-grounded documentary with a consistent fictional presenter" `
  --reference-image ".\references\presenter-front.png" `
  --reference-image ".\references\presenter-three-quarter.png" `
  --scene-count 16 `
  --resolution 1080p `
  --output ".\overview-with-presenter.mp4"
```

Up to three reference images are accepted. Reference-guided rendering uses
`personGeneration=allow_adult`. Text-to-video rendering can use `allow_all`.

## Output structure

```text
controlled-video-overview-work/
├── storyboard.json
├── storyboard-raw.txt
├── notebooklm-video-overview.mp4
├── notebooklm-video-narration.m4a
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

The manifest identifies the narration source:

```json
{
  "narration_source": "notebooklm_cinematic_video_overview",
  "notebooklm_video_overview": "controlled-video-overview-work/notebooklm-video-overview.mp4",
  "narration_audio": "controlled-video-overview-work/notebooklm-video-narration.m4a"
}
```

## Resume behavior

`--resume` is enabled by default. Existing storyboards, native Video Overview,
extracted narration, Veo clips, and normalized clips are reused. Use
`--no-resume` to regenerate all stages.

## Synchronization limitation

NotebookLM Video Overview does not expose frame-accurate narration timestamps
through this workflow. The current assembler preserves thematic storyboard
order and ends the final MP4 at the narration endpoint. A future transcription
and alignment phase is needed for frame-accurate scene timing.

## Cost and quota warning

Each storyboard scene is a separate Veo generation. Start with `--plan-only`, a
small scene count, the Fast Veo model, and 720p. Increase scene count and
resolution only after approving the storyboard, native Video Overview narration,
and reference-image strategy.

# Paste this into “New Gem from Labs”

Build an English-language AI mini-app named **NotebookLM Cinematic Planner**.
It is a planning and approval tool for a source-grounded cinematic production
workflow. It must minimize video-generation credits and must never generate a
full video automatically.

## Primary goal

Turn uploaded source documents or pasted source notes into a reviewable JSON
storyboard and a render handoff package for this external local pipeline:

Selected sources → source-grounded storyboard → NotebookLM Cinematic Video
Overview narration → direct Veo 3.1 scene clips → FFmpeg final MP4.

The mini-app itself is the planning and control surface. The external local
`notebooklm-py` repository performs NotebookLM authentication, native Video
Overview generation, Veo API calls, FFmpeg audio extraction, clip normalization,
and final assembly.

## User interface

Create a polished responsive app with four tabs:

1. **Project**
   - Project title
   - Topic and editorial goal
   - Language
   - Source upload or pasted source notes
   - Estimated narration length in minutes
   - Scene count
   - Aspect ratio: 16:9 or 9:16
   - Resolution: 720p, 1080p, or 4K
   - Veo model: Standard or Fast
   - Clip duration: 4, 6, or 8 seconds
   - Person generation: allow_all or allow_adult
   - Reference image count: 0–3

2. **Storyboard**
   - Editable scene table/cards
   - Each scene includes title, narration anchor, visual prompt, composition,
     camera, lens, ambiance, negative prompt, and duration_seconds
   - Buttons: add scene, duplicate scene, delete scene, import JSON, export JSON

3. **Cost guard**
   - Modes: Plan only, One-clip test, Budget render, Full render
   - Show estimated clip count, rendered seconds, reference-guided clips, and
     a low/medium/high spend-risk label
   - User-configurable maximum clip count
   - Require explicit approval before Full render handoff
   - Never put currency prices in the app because provider pricing can change

4. **Handoff**
   - Preview and download `storyboard.json`
   - Preview and download `render-manifest.json`
   - Preview and download `video-overview-instructions.md`
   - Preview and download `run-controlled-cinematic.ps1`

## Model workflow

Use text models only by default.

### Step 1: Source analyzer

Extract only source-supported facts, themes, claims, entities, locations, and
chronology. Clearly mark uncertainty. Do not invent facts.

### Step 2: Storyboard builder

Generate valid JSON with this structure:

```json
{
  "schema_version": 1,
  "title": "Controlled Cinematic Overview",
  "summary": "Source-grounded summary",
  "scenes": [
    {
      "title": "Scene 1",
      "narration": "Source-grounded narration anchor",
      "visual_prompt": "Standalone visual prompt",
      "composition": "eye-level medium close-up or two-shot",
      "camera": "slow cinematic movement preserving facial visibility",
      "lens": "50mm natural perspective, primary faces in sharp focus",
      "ambiance": "soft balanced frontal lighting with natural skin tones",
      "negative_prompt": "rear-only view, silhouette, hidden face, distorted face, text covering face",
      "duration_seconds": 8
    }
  ]
}
```

For human-centered shots, use fictional, non-famous adults. Favor front or
natural three-quarter facial angles, visible eyes, balanced frontal lighting,
and unobstructed faces. Do not include sexualized body requirements, requests
to bypass safety systems, or words such as uncensored, unfiltered, or override.

### Step 3: Constraint validator

Apply these rules:

- Duration must be 4, 6, or 8 seconds.
- 1080p, 4K, or any reference image requires 8 seconds.
- Reference images require `allow_adult`.
- No more than three reference images.
- Every scene must include `visual_prompt`.
- Full render cannot proceed until the approval checkbox is true.

Show validation problems before showing the handoff package.

### Step 4: Cost estimator

Calculate:

- narration_seconds = narration_minutes × 60
- full_clip_count = ceiling(narration_seconds ÷ clip_duration)
- rendered_seconds = selected_clip_count × clip_duration

Mode behavior:

- Plan only: selected_clip_count = 0
- One-clip test: selected_clip_count = 1
- Budget render: selected_clip_count = minimum(full_clip_count, maximum_clips)
- Full render: selected_clip_count = full_clip_count, but only after explicit approval

### Step 5: Handoff generator

Generate a PowerShell command for:

```text
uv run python scripts/controlled_cinematic_video_overview_pipeline.py
```

Include the storyboard path, notebook placeholder, topic, scene count,
person-generation mode, aspect ratio, duration, resolution, workspace, and
output path.

## Credit-safety requirements

- Never call a video model on initial load.
- Never call a video model after storyboard generation.
- Never call a video model merely to preview the UI.
- A one-clip test must require a separate explicit action and confirmation.
- Full render must be a handoff only, not an in-app generation action.
- Do not request or store API keys.
- Do not attempt to run Python, NotebookLM private APIs, or FFmpeg inside the mini-app.

## Output behavior

The app should be useful even when all generation controls are disabled. It
should produce editable, downloadable planning artifacts and a clear next-step
command for the local repository.

# Google Flow Tool companion for the NotebookLM Cinematic Video Overview pipeline

This companion uses Google Flow as the **selective scene renderer** and
`notebooklm-py` as the source-grounding, narration extraction, validation, and
final FFmpeg assembly layer.

It is designed to reduce wasted generations by separating planning from media
creation, requiring confirmation before every credit-bearing action, rendering
only selected scenes, and reusing approved project assets.

## Supported production flow

```text
Selected NotebookLM sources
        ↓
notebooklm-py / NotebookLM Chat
source-grounded storyboard.json
        ↓
NotebookLM Cinematic Video Overview
source-grounded narration embedded in MP4
        ↓
Google Flow Tool
plan, estimate, and render selected Veo scenes
        ↓
Download approved scene-001.mp4 … scene-N.mp4
        ↓
notebooklm-py / FFmpeg
extract narration, normalize clips, assemble final MP4
```

## Important boundary

Google Flow Tools are created and saved inside an authenticated Google Flow
project. The repository cannot programmatically create or modify a Tool in a
user's private Flow project. Use the complete builder prompt below in the Flow
**Create Tool** page, review the generated interface, and select **Save**.

The Tool must not request a Gemini API key, NotebookLM cookies, Google account
credentials, or GitHub tokens. It operates only on files and assets the user
selects in the current Flow project.

## Complete Google Flow Create Tool prompt

Paste everything in the following block into the Google Flow Create Tool prompt:

```text
Build a reusable desktop web Tool named:

NotebookLM Cinematic Scene Planner

PURPOSE
Create a credit-conscious scene planning and selective Veo rendering mini-app
for a hybrid NotebookLM + Google Flow + FFmpeg workflow.

The user uploads an approved NotebookLM storyboard JSON. The Tool converts each
storyboard scene into a controlled Google Flow video-generation job, lets the
user review and edit it, estimates generation credits, and renders only scenes
the user explicitly selects. Generated media must be saved to the current Flow
project.

NON-NEGOTIABLE COST-SAVING BEHAVIOR
1. Open in Plan Only mode. Plan Only must use no media-generation credits.
2. Never generate media while parsing a storyboard, editing prompts, changing
   controls, estimating cost, importing existing clips, or exporting metadata.
3. Never automatically render all scenes.
4. The primary render button must say "Generate selected scene" and operate on
   exactly one scene by default.
5. Before every credit-bearing action, display a confirmation dialog showing:
   scene number and title, selected model, duration, number of outputs,
   estimated credits, and whether references or a Character are used.
6. Default number of outputs to 1.
7. Default model to Veo 3.1 Lite for draft rendering.
8. Default duration to 4 seconds for text-only drafts.
9. Automatically require 8 seconds when ingredients, references, or Character
   mode require the model's reference-video constraints.
10. Do not upscale while drafting. Keep 1080p and 4K finalization separate and
    disabled by default.
11. Preserve approved clips. Never rerender an approved scene unless the user
    clicks "Create new version" and confirms the cost.
12. Require two confirmations for any optional batch generation.
13. Detect identical prompt fingerprints and offer to reuse an existing clip.
14. Show running estimated credits used and remaining.
15. Credit prices must be editable. Initialize these editable estimates:
    - Veo 3.1 Lite: 10 non-Ultra, 5 Ultra
    - Veo 3.1 Fast: 20 non-Ultra, 10 Ultra
    - Veo 3.1 Quality: 100
    - Gemini Omni Flash: 4s=15, 6s=20, 8s=25, 10s=30
    - 1080p upscale: 0 for eligible subscribers
    - 4K upscale: 50 for eligible Ultra users
16. Include subscription selector: Free/Other, Plus, Pro, Ultra.
17. Always remind the user to verify the latest price displayed by Flow.

INPUTS
A. Required storyboard JSON upload or paste field.
B. Optional native NotebookLM Cinematic Video Overview MP4 upload, used only for
   project reference and filename tracking. Do not edit or regenerate it.
C. Optional project instructions.
D. Optional reusable Flow Character.
E. Optional one to three image ingredients or references.
F. Optional existing generated clips from the current Flow project.

STORYBOARD JSON FORMAT
Accept this structure:
{
  "schema_version": 1,
  "title": "Overview title",
  "summary": "Editorial summary",
  "scenes": [
    {
      "index": 1,
      "title": "Scene title",
      "narration": "Source-grounded narration idea",
      "visual_prompt": "Standalone visual prompt",
      "composition": "Eye-level medium close-up",
      "camera": "Slow dolly-in",
      "lens": "50mm natural perspective",
      "ambiance": "Soft frontal daylight",
      "negative_prompt": "Rear-only view, silhouette, hidden face",
      "duration_seconds": 8
    }
  ]
}

VALIDATION
1. Reject invalid JSON with a clear field error.
2. Require a non-empty scenes array.
3. Assign missing scene indexes sequentially.
4. Allow only 4, 6, or 8 seconds for Veo 3.1 scenes.
5. If references are active, change duration to 8 seconds and explain why.
6. Warn when a scene prompt lacks subject, action, environment, lighting, or
   style.
7. Warn when a face-required scene uses rear view, silhouette, mask, extreme
   crop, heavy shadow, or foreground obstruction.
8. Never claim that provider safety systems or identity checks can be disabled.

INTERFACE
Create a three-column desktop interface.

LEFT COLUMN: Project and cost controls
- Storyboard upload/paste
- Native NotebookLM Video Overview upload
- Flow Character picker
- Reference picker, maximum 3
- Model selector: Veo 3.1 Lite, Fast, Quality, Gemini Omni Flash
- Subscription selector
- Aspect ratio: 16:9 or 9:16
- Output count, default 1
- Editable cost table
- Estimate card: planned, rendered, approved, remaining, estimated used credits,
  estimated remaining credits

CENTER COLUMN: Scene queue
Show one card per storyboard scene with:
- scene number, title, narration anchor
- status: Planned, Ready, Rendering, Rendered, Approved, Rejected, Reused
- model, duration, estimated credit badges
- thumbnail when available
- duplicate-prompt warning
- buttons: Edit, Preview prompt, Import existing clip, Generate selected scene,
  Approve, Reject, Create new version

RIGHT COLUMN: Selected scene editor
Editable fields:
- visual prompt
- composition
- camera position and motion
- lens and focus
- lighting and ambiance
- negative prompt
- face visibility: Not required, Preferred, Front or three-quarter
- model, duration, aspect ratio, Character, references, output count

Show a final prompt preview combining fields in this order:
1. visual prompt
2. Composition: ...
3. Camera positioning and motion: ...
4. Focus and lens effects: ...
5. Lighting and ambiance: ...
6. Continuity requirements
7. Avoid: negative prompt

PROMPT PRESETS
Add zero-credit buttons that only edit the selected scene:
- Presenter close-up
- Presenter three-quarter
- Contextual B-roll
- Product/object detail
- Establishing shot
- Motion graphic explainer

For presenter presets append:
Use an eye-level medium close-up. Keep the primary adult subject facing camera or
at a natural three-quarter angle. Keep both eyes and the complete face
unobstructed and naturally lit. Avoid rear-only view, silhouette, mask, extreme
crop, heavy shadow, and foreground objects covering the face.

REUSE AND VERSIONING
1. Let the user import an existing clip and associate it with a scene.
2. Mark imported clips Reused with 0 estimated generation credits.
3. Keep every version in scene history.
4. Approval locks the selected version.
5. Prompt changes after approval mark the scene Needs review but do not generate.
6. Generate a stable fingerprint from normalized prompt, model, duration, aspect
   ratio, Character, and references.

EXPORT
Provide a zero-credit Export panel that creates:
1. Downloadable scene manifest JSON.
2. Downloadable CSV shot list.
3. Filename checklist requiring approved clips to be named:
   scene-001.mp4, scene-002.mp4, scene-003.mp4, and so on.
4. This copyable PowerShell command:

uv run python scripts/flow_cinematic_video_overview_assembler.py `
  --storyboard-file ".\\storyboard.json" `
  --video-overview-file ".\\notebooklm-video-overview.mp4" `
  --clips-directory ".\\flow-clips" `
  --aspect-ratio 16:9 `
  --resolution 1080p `
  --workspace ".\\flow-cinematic-work" `
  --output ".\\final-notebooklm-flow-overview.mp4"

The manifest must include scene index, title, approval status, filename, model,
duration, prompt fingerprint, and estimated credits.

FINAL UX RULES
- Make Plan Only visually prominent.
- Approved and Reused are green; Ready and Needs review are amber; Rejected and
  Missing clip are red.
- Disable final export until every scene is Approved or Reused.
- Do not put Generate All in the primary interface.
- Explain that final audio extraction and MP4 muxing happen locally through
  notebooklm-py and FFmpeg, not inside the Tool.
- Keep generated media in the current Google Flow project.
```

## Recommended Flow settings

1. Use **one output**.
2. Use **Veo 3.1 Lite** for draft scenes.
3. Set Agent confirmation before generation to **Always**.
4. Use one reusable Flow Character for recurring presenters.
5. Delay 1080p/4K upscaling until clips are approved.

## Export convention

Download approved Flow clips with exact names:

```text
flow-clips/
├── scene-001.mp4
├── scene-002.mp4
├── scene-003.mp4
└── ...
```

## Assemble without another Veo generation

```powershell
uv run python scripts/flow_cinematic_video_overview_assembler.py `
  --storyboard-file ".\storyboard.json" `
  --video-overview-file ".\notebooklm-video-overview.mp4" `
  --clips-directory ".\flow-clips" `
  --aspect-ratio 16:9 `
  --resolution 1080p `
  --workspace ".\flow-cinematic-work" `
  --output ".\final-notebooklm-flow-overview.mp4"
```

This path makes no direct Veo API request and requires no `GEMINI_API_KEY`. It
extracts the NotebookLM Video Overview narration, validates and normalizes the
approved Flow clips, concatenates them, and muxes the final MP4.

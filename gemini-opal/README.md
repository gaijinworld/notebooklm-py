# NotebookLM Cinematic Planner for Gemini Gems from Google Labs

This folder contains a cost-controlled planning app for the controlled cinematic
pipeline in PR #14.

The app is intentionally **planning-first**:

1. Collect source notes and production preferences.
2. Generate or edit a source-grounded storyboard.
3. Validate Veo constraints before any video generation.
4. Estimate clip count and rendered seconds.
5. Require an explicit approval gate.
6. Export a PR #14-compatible storyboard, render manifest, Video Overview
   instructions, and PowerShell command.

It does **not** call NotebookLM, Veo, or FFmpeg from the browser prototype.
The actual generation and assembly remain in:

```text
scripts/controlled_cinematic_video_overview_pipeline.py
```

## Why this saves credits

- The default mode is `Plan only`, which schedules zero video clips.
- `One-clip test` limits validation to one Veo clip.
- `Budget render` enforces a user-defined maximum clip count.
- `Full render` requires an explicit approval checkbox.
- The planner exports reusable JSON so prompts can be reviewed before any
  NotebookLM Video Overview or Veo request is started.

## Recommended Gemini surface

Use **New Gem from Labs** in the Gemini Gem manager. Gems from Labs are powered
by Opal and support multi-step mini-app workflows. The classic Gem creation page
is useful for instructions and knowledge files, but it is not the recommended
surface for this interactive workflow.

## Build the Opal mini-app

1. Open Gemini on desktop with a personal Google account.
2. Open `Gems`.
3. Under `My Gems from Labs`, choose `New Gem`.
4. Paste the complete content of `OPAL_BUILD_PROMPT.md`.
5. Submit and review the generated workflow.
6. Open the advanced editor and apply the node configuration in
   `ADVANCED_EDITOR_WORKFLOW.md`.
7. Keep every video-generation node disabled by default.

## Use the Canvas prototype

Open:

```text
gemini-opal/canvas/index.html
```

The prototype is a standalone local web app. It can also be supplied to Gemini
Canvas as a reference implementation.

## Exported files

The planner produces:

```text
storyboard.json
render-manifest.json
video-overview-instructions.md
run-controlled-cinematic.ps1
```

`storyboard.json` matches the schema accepted by PR #14.

## Important boundary

The planner improves review, cost control, composition prompts, and handoff. It
does not disable or weaken Google safety or policy enforcement. It also does not
attempt to run the local Python package or FFmpeg inside a Gem.

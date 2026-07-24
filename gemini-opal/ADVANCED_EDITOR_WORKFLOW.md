# Opal advanced-editor workflow

Use this as the node-by-node reference after the initial mini-app is generated.

## Inputs

### `project_input`

Collect:

- title
- topic
- language
- source files or source notes
- narration minutes
- scene count
- aspect ratio
- resolution
- Veo model
- clip duration
- person generation
- reference count
- mode
- maximum clips
- full-render approval

## Generate nodes

### `analyze_sources`

Model type: text/agent

Instruction:

> Analyze only the supplied sources. Return a compact factual brief with themes,
> chronology, entities, locations, claims, and uncertainty. Do not generate any
> images, audio, or video.

### `build_storyboard`

Model type: text

Input: `analyze_sources` + project settings

Instruction:

> Produce only valid JSON compatible with schema version 1 in
> `schemas/storyboard.schema.json`. Keep every narration anchor grounded in the
> source brief. Use positive face-visible composition instructions for fictional
> non-famous adults. Do not request safety bypasses or sexualized styling.

### `validate_storyboard`

Model type: text/logic

Input: storyboard JSON + project settings

Instruction:

> Validate required fields and Veo combinations. Return a JSON object with
> `valid`, `errors`, `warnings`, and `normalized_settings`. Do not generate media.

### `estimate_render`

Model type: logic

Input: normalized settings

Output:

```json
{
  "narration_seconds": 600,
  "full_clip_count": 75,
  "selected_clip_count": 0,
  "rendered_seconds": 0,
  "risk": "low"
}
```

### `approval_gate`

Routing:

- `plan_only` → handoff outputs
- `one_clip_test` with confirmation → optional one-video node
- `budget_render` → handoff outputs only
- `full_render` without approval → return to Cost guard
- `full_render` with approval → handoff outputs only

### `optional_test_clip`

Model type: video

Default state: disabled

Requirements:

- Only runs from One-clip test mode.
- Exactly one clip.
- Fast model.
- 720p when available.
- 8 seconds when references are present.
- Never fan out to multiple clips.

### `build_handoff`

Model type: text

Generate four outputs:

1. storyboard JSON
2. render manifest JSON
3. Video Overview instructions markdown
4. PowerShell command

## Output nodes

Expose downloads for all four handoff files. Show a banner:

> No NotebookLM Video Overview or Veo full-render request has been started.
> Run the exported command locally when the storyboard is approved.

## Forbidden routes

Do not connect storyboard generation directly to a video node. Do not add loops
that generate every scene. Do not request API keys. Do not run full render inside
Opal.

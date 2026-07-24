#!/usr/bin/env python3
"""NotebookLM Video Overview narration + reference-conditioned Veo 3.1 scenes.

The workflow keeps the native NotebookLM Cinematic Video Overview as the
source-grounded narration source, but renders replacement visuals through the
direct Gemini API Veo endpoint. Reference images must depict fictional adults or
adults whose likeness the operator is authorized to use.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import click
import controlled_cinematic_pipeline as base
import controlled_cinematic_video_overview_pipeline as video_pipeline

from notebooklm import NotebookLMClient
from notebooklm._cinematic_reference import (
    ReferenceSceneError,
    build_scene_payload,
    build_subject_reference_map,
    normalize_reference_storyboard,
    scene_reference_paths,
)
from notebooklm.veo_cli import _DEFAULT_MODEL, _SUPPORTED_MODELS, _generate

_REFERENCE_STORYBOARD_SHAPE = {
    "title": "string",
    "summary": "string",
    "subjects": [
        {
            "id": "presenter",
            "description": "fictional or authorized adult presenter",
            "reference_images": ["references/presenter-front.png"],
        }
    ],
    "scenes": [
        {
            "id": "scene-001",
            "title": "string",
            "narration": "source-grounded narration anchor",
            "visual_prompt": "standalone Veo visual prompt",
            "dialogue": "optional exact dialogue cue for Veo preview audio",
            "ambient_audio": "optional ambience or sound-effect cue",
            "subject_ids": ["presenter"],
            "generation_mode": "reference",
            "composition": "eye-level medium close-up",
            "camera": "restrained dolly-in",
            "lens": "50mm natural perspective",
            "ambiance": "soft frontal lighting",
            "negative_prompt": "rear-only view, hidden or distorted face",
            "duration_seconds": 8,
            "first_frame": None,
            "last_frame": None,
            "extend_from_scene": None,
        }
    ],
}


def _storyboard_question(
    *,
    topic: str,
    scene_count: int,
    language: str,
    extra_instructions: str | None,
) -> str:
    extra = (
        f"\nAdditional production instructions:\n{extra_instructions}\n"
        if extra_instructions
        else ""
    )
    return f"""
Create a source-grounded cinematic production plan about: {topic}

Return ONLY valid JSON. Use exactly {scene_count} scenes. Output language: {language}.

Requirements:
- Ground every narration anchor in the selected NotebookLM sources.
- Separate source-grounded narration from the visual prompt.
- Use fictional, non-famous adults or adults whose likeness is explicitly authorized.
- Use generation_mode `reference` for recurring presenters or products.
- Use generation_mode `text` for B-roll with no continuity requirement.
- Use generation_mode `interpolation` only when both first_frame and last_frame are supplied.
- Use generation_mode `extension` only for a continuous shot that follows an earlier scene.
- Never combine reference images, interpolation frames, and extension in one scene.
- Reference-guided and interpolation scenes are 8 seconds.
- Favor front or natural three-quarter faces, visible eyes, unobstructed faces, and balanced light.
- Avoid sexualized descriptions, minors, real-person impersonation, and safety-bypass wording.
- Include optional dialogue and ambient_audio only when they improve a one-scene preview.
{extra}
Use this exact JSON shape:
{json.dumps(_REFERENCE_STORYBOARD_SHAPE, indent=2)}
""".strip()


async def _create_storyboard(
    client: NotebookLMClient,
    *,
    notebook_id: str,
    source_ids: list[str] | None,
    topic: str,
    scene_count: int,
    language: str,
    extra_instructions: str | None,
) -> tuple[dict[str, Any], str]:
    question = _storyboard_question(
        topic=topic,
        scene_count=scene_count,
        language=language,
        extra_instructions=extra_instructions,
    )
    click.echo("Asking NotebookLM for a reference-aware storyboard...", err=True)
    result = await client.chat.ask(notebook_id, question, source_ids=source_ids)
    payload = base._extract_json_object(result.answer)
    storyboard = normalize_reference_storyboard(
        payload, default_duration=8, maximum_scenes=scene_count
    )
    return storyboard, result.answer


def _resolve_asset(path_value: str | None, *, asset_root: Path) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = asset_root / path
    return path.resolve()


def _trim_extension_tail(
    *,
    source: Path,
    destination: Path,
    ffmpeg: str,
    ffprobe: str,
) -> None:
    duration = base._probe_duration(ffprobe, source)
    start = max(0.0, duration - 7.0)
    destination.parent.mkdir(parents=True, exist_ok=True)
    base._run_process(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(destination),
        ],
        label=f"extract extension tail for {destination.name}",
    )


async def _render_scenes(
    *,
    storyboard: dict[str, Any],
    api_key: str,
    model: str,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    subject_references: dict[str, tuple[Path, ...]],
    asset_root: Path,
    include_audio_cues: bool,
    enhance_prompt: bool,
    seed: int | None,
    clips_dir: Path,
    operations_dir: Path,
    requests_dir: Path,
    extensions_dir: Path,
    ffmpeg: str,
    ffprobe: str,
    timeout: float,
    poll_interval: float,
    resume: bool,
) -> tuple[list[Path], list[dict[str, Any]]]:
    for directory in (clips_dir, operations_dir, requests_dir, extensions_dir):
        directory.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []
    plans: list[dict[str, Any]] = []
    full_video_by_scene: dict[str, Path] = {}

    for scene in storyboard["scenes"]:
        index = int(scene["index"])
        scene_id = str(scene["id"])
        clip_path = clips_dir / f"scene-{index:03d}.mp4"
        mode = str(scene["generation_mode"])
        raw_output = (
            extensions_dir / f"scene-{index:03d}-full.mp4"
            if mode == "extension"
            else clip_path
        )

        references = scene_reference_paths(scene, subject_references)
        first_frame = _resolve_asset(scene.get("first_frame"), asset_root=asset_root)
        last_frame = _resolve_asset(scene.get("last_frame"), asset_root=asset_root)
        extension_video = None
        if mode == "extension":
            parent_id = str(scene.get("extend_from_scene") or "").strip()
            if not parent_id:
                raise base.PipelineError(
                    f"Scene {scene_id} is extension mode but has no extend_from_scene."
                )
            extension_video = full_video_by_scene.get(parent_id)
            if extension_video is None:
                raise base.PipelineError(
                    f"Scene {scene_id} extends {parent_id}, which has not been rendered earlier."
                )

        if resume and clip_path.is_file() and clip_path.stat().st_size > 0:
            if mode != "extension" or raw_output.is_file():
                click.echo(f"Reusing scene {scene_id}: {clip_path}", err=True)
                clips.append(clip_path)
                full_video_by_scene[scene_id] = raw_output
                continue

        payload, request_summary = build_scene_payload(
            scene,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            person_generation=person_generation,
            references=references,
            first_frame=first_frame,
            last_frame=last_frame,
            extension_video=extension_video,
            enhance_prompt=enhance_prompt,
            seed=None if seed is None else seed + index,
            include_audio_cues=include_audio_cues,
        )
        base._write_json(requests_dir / f"scene-{index:03d}.json", request_summary)
        plans.append(request_summary)

        click.echo(
            f"Rendering {scene_id} ({mode}) {index}/{len(storyboard['scenes'])}: "
            f"{scene['title']}",
            err=True,
        )
        await asyncio.to_thread(
            _generate,
            api_key=api_key,
            model=model,
            payload=payload,
            output=raw_output,
            timeout=timeout,
            poll_interval=poll_interval,
            save_operation=operations_dir / f"scene-{index:03d}.json",
        )
        if mode == "extension":
            await asyncio.to_thread(
                _trim_extension_tail,
                source=raw_output,
                destination=clip_path,
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
            )
        clips.append(clip_path)
        full_video_by_scene[scene_id] = raw_output

    return clips, plans


async def _run(
    *,
    notebook_id: str | None,
    profile: str | None,
    source_ids: list[str] | None,
    topic: str,
    language: str,
    scene_count: int,
    model: str,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    subject_reference_values: tuple[str, ...],
    confirm_authorized_adult: bool,
    storyboard_file: Path | None,
    storyboard_instructions: str | None,
    video_overview_file: Path | None,
    video_overview_instructions: str | None,
    asset_root: Path | None,
    include_audio_cues: bool,
    enhance_prompt: bool,
    seed: int | None,
    workspace: Path,
    output_path: Path,
    ffmpeg_value: str,
    ffprobe_value: str,
    notebook_timeout: float,
    veo_timeout: float,
    poll_interval: float,
    resume: bool,
    plan_only: bool,
) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    storyboard_path = workspace / "storyboard.json"
    raw_storyboard_path = workspace / "storyboard-raw.txt"
    native_video_path = workspace / "notebooklm-video-overview.mp4"
    narration_path = workspace / "notebooklm-video-narration.m4a"

    root = (asset_root or (storyboard_file.parent if storyboard_file else Path.cwd())).resolve()
    storyboard: dict[str, Any] | None = None
    if storyboard_file is not None:
        storyboard = normalize_reference_storyboard(
            json.loads(storyboard_file.read_text(encoding="utf-8")),
            default_duration=8,
            maximum_scenes=scene_count,
        )
    elif resume and storyboard_path.is_file():
        storyboard = normalize_reference_storyboard(
            json.loads(storyboard_path.read_text(encoding="utf-8")),
            default_duration=8,
            maximum_scenes=scene_count,
        )

    need_storyboard = storyboard is None
    need_video = video_overview_file is None and not (
        resume and native_video_path.is_file()
    )
    if (need_storyboard or need_video) and not notebook_id:
        raise base.PipelineError(
            "--notebook is required unless both --storyboard-file and "
            "--video-overview-file are supplied."
        )

    if need_storyboard or need_video:
        async with NotebookLMClient.from_storage(profile=profile) as client:
            if storyboard is None:
                assert notebook_id is not None
                storyboard, raw = await _create_storyboard(
                    client,
                    notebook_id=notebook_id,
                    source_ids=source_ids,
                    topic=topic,
                    scene_count=scene_count,
                    language=language,
                    extra_instructions=storyboard_instructions,
                )
                raw_storyboard_path.write_text(raw, encoding="utf-8")
                base._write_json(storyboard_path, storyboard)

            if plan_only:
                references = build_subject_reference_map(
                    storyboard, subject_reference_values, asset_root=root
                )
                plan = {
                    "status": "planned",
                    "storyboard": str(storyboard_path),
                    "subjects": {
                        key: [str(path) for path in value]
                        for key, value in references.items()
                    },
                    "scenes": [
                        {
                            "id": scene["id"],
                            "mode": scene["generation_mode"],
                            "subject_ids": scene["subject_ids"],
                        }
                        for scene in storyboard["scenes"]
                    ],
                }
                base._write_json(workspace / "reference-plan.json", plan)
                return plan

            if video_overview_file is None:
                if resume and native_video_path.is_file():
                    video_overview_file = native_video_path
                else:
                    assert notebook_id is not None
                    video_overview_file = await video_pipeline._create_native_video_overview(
                        client,
                        notebook_id=notebook_id,
                        source_ids=source_ids,
                        language=language,
                        topic=topic,
                        storyboard=storyboard,
                        extra_instructions=video_overview_instructions,
                        output_path=native_video_path,
                        timeout=notebook_timeout,
                    )
    else:
        assert storyboard is not None
        if plan_only:
            base._write_json(storyboard_path, storyboard)
            return {
                "status": "planned",
                "storyboard": str(storyboard_path),
                "scene_count": len(storyboard["scenes"]),
            }

    assert storyboard is not None
    base._write_json(storyboard_path, storyboard)
    if video_overview_file is None:
        video_overview_file = native_video_path

    subject_references = build_subject_reference_map(
        storyboard, subject_reference_values, asset_root=root
    )
    uses_references = any(subject_references.values())
    if uses_references and not confirm_authorized_adult:
        raise base.PipelineError(
            "Reference images require --confirm-authorized-adult to confirm the depicted "
            "adult is fictional or you are authorized to use their likeness."
        )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise base.PipelineError("GEMINI_API_KEY is required for Veo rendering.")
    ffmpeg = base._require_binary(ffmpeg_value, "FFmpeg")
    ffprobe = base._require_binary(ffprobe_value, "FFprobe")

    narration_audio = await asyncio.to_thread(
        video_pipeline._extract_narration,
        ffmpeg=ffmpeg,
        video_path=video_overview_file,
        output_path=narration_path,
        resume=resume,
    )
    clips, request_plan = await _render_scenes(
        storyboard=storyboard,
        api_key=api_key,
        model=model,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        person_generation=person_generation,
        subject_references=subject_references,
        asset_root=root,
        include_audio_cues=include_audio_cues,
        enhance_prompt=enhance_prompt,
        seed=seed,
        clips_dir=workspace / "clips",
        operations_dir=workspace / "operations",
        requests_dir=workspace / "requests",
        extensions_dir=workspace / "extensions",
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        timeout=veo_timeout,
        poll_interval=poll_interval,
        resume=resume,
    )
    assembly = await asyncio.to_thread(
        base._assemble_final_video,
        clips=clips,
        narration_audio=narration_audio,
        output_path=output_path,
        workspace=workspace,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        resume=resume,
    )
    manifest = {
        "schema_version": 2,
        "status": "completed",
        "narration_source": "notebooklm_cinematic_video_overview",
        "storyboard": str(storyboard_path),
        "notebooklm_video_overview": str(video_overview_file),
        "narration_audio": str(narration_audio),
        "model": model,
        "aspect_ratio": aspect_ratio,
        "requested_resolution": resolution,
        "subject_references": {
            key: [str(path) for path in value]
            for key, value in subject_references.items()
        },
        "scene_requests": request_plan,
        "rendered_clips": [str(path) for path in clips],
        **assembly,
    }
    base._write_json(workspace / "manifest.json", manifest)
    return manifest


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--notebook", "notebook_id")
@click.option("--profile")
@click.option("--source", "source_ids", multiple=True)
@click.option("--topic", required=True)
@click.option("--language", default="en", show_default=True)
@click.option("--scene-count", type=click.IntRange(1, 60), default=12, show_default=True)
@click.option("--model", type=click.Choice(_SUPPORTED_MODELS), default=_DEFAULT_MODEL)
@click.option("--aspect-ratio", type=click.Choice(["16:9", "9:16"]), default="16:9")
@click.option("--resolution", type=click.Choice(["720p", "1080p", "4k"]), default="720p")
@click.option(
    "--person-generation",
    type=click.Choice(["auto", "allow_all", "allow_adult"]),
    default="auto",
)
@click.option(
    "--subject-reference",
    "subject_reference_values",
    multiple=True,
    help="Map a subject ID to an image: presenter=references/front.png. Repeat up to 3 times.",
)
@click.option(
    "--confirm-authorized-adult",
    is_flag=True,
    help="Confirm reference images depict fictional adults or adults whose likeness is authorized.",
)
@click.option("--storyboard-file", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option(
    "--storyboard-instructions-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option("--video-overview-file", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option(
    "--video-overview-instructions-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option("--asset-root", type=click.Path(path_type=Path, exists=True, file_okay=False))
@click.option("--include-veo-audio-cues/--no-veo-audio-cues", default=False)
@click.option("--enhance-prompt/--no-enhance-prompt", default=True)
@click.option("--seed", type=int)
@click.option(
    "--workspace",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("controlled-reference-work"),
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("controlled-reference-overview.mp4"),
)
@click.option("--ffmpeg", "ffmpeg_value", default="ffmpeg")
@click.option("--ffprobe", "ffprobe_value", default="ffprobe")
@click.option("--notebook-timeout", type=click.FloatRange(min=1), default=3600.0)
@click.option("--veo-timeout", type=click.FloatRange(min=1), default=1800.0)
@click.option("--poll-interval", type=click.FloatRange(min=1), default=10.0)
@click.option("--resume/--no-resume", default=True)
@click.option("--plan-only", is_flag=True)
@click.option("--json-output", is_flag=True)
def main(
    notebook_id: str | None,
    profile: str | None,
    source_ids: tuple[str, ...],
    topic: str,
    language: str,
    scene_count: int,
    model: str,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    subject_reference_values: tuple[str, ...],
    confirm_authorized_adult: bool,
    storyboard_file: Path | None,
    storyboard_instructions_file: Path | None,
    video_overview_file: Path | None,
    video_overview_instructions_file: Path | None,
    asset_root: Path | None,
    include_veo_audio_cues: bool,
    enhance_prompt: bool,
    seed: int | None,
    workspace: Path,
    output_path: Path,
    ffmpeg_value: str,
    ffprobe_value: str,
    notebook_timeout: float,
    veo_timeout: float,
    poll_interval: float,
    resume: bool,
    plan_only: bool,
    json_output: bool,
) -> None:
    """Generate controlled Veo scenes with authorized adult face references."""
    try:
        result = asyncio.run(
            _run(
                notebook_id=notebook_id,
                profile=profile,
                source_ids=list(source_ids) or None,
                topic=topic,
                language=language,
                scene_count=scene_count,
                model=model,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                person_generation=person_generation,
                subject_reference_values=subject_reference_values,
                confirm_authorized_adult=confirm_authorized_adult,
                storyboard_file=storyboard_file,
                storyboard_instructions=base._read_optional_text(
                    storyboard_instructions_file
                ),
                video_overview_file=video_overview_file,
                video_overview_instructions=base._read_optional_text(
                    video_overview_instructions_file
                ),
                asset_root=asset_root,
                include_audio_cues=include_veo_audio_cues,
                enhance_prompt=enhance_prompt,
                seed=seed,
                workspace=workspace,
                output_path=output_path,
                ffmpeg_value=ffmpeg_value,
                ffprobe_value=ffprobe_value,
                notebook_timeout=notebook_timeout,
                veo_timeout=veo_timeout,
                poll_interval=poll_interval,
                resume=resume,
                plan_only=plan_only,
            )
        )
    except (base.PipelineError, ReferenceSceneError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    elif result.get("status") == "planned":
        click.echo(f"Reference-aware storyboard ready: {result['storyboard']}")
    else:
        click.echo(f"Final video ready: {result['final_output']}")
        click.echo(f"Manifest: {workspace / 'manifest.json'}")


if __name__ == "__main__":
    main()

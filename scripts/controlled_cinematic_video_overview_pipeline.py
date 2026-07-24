#!/usr/bin/env python3
"""NotebookLM Video Overview narration -> controlled Veo scenes -> FFmpeg output.

This entry point is intentionally separate from the Audio Overview experiment in
``controlled_cinematic_pipeline.py``. It uses NotebookLM's native Cinematic
Video Overview as the source-grounded narration source, extracts that video's
audio track, renders controlled visual scenes with direct Veo 3.1, and muxes the
NotebookLM narration into the assembled final MP4.

Google's server-side safety and policy enforcement remains active.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import click

import controlled_cinematic_pipeline as base
from notebooklm import NotebookLMClient


def _video_overview_instructions(
    *,
    topic: str,
    storyboard: dict[str, Any],
    extra_instructions: str | None,
) -> str:
    outline = "\n".join(
        f"{scene['index']}. {scene['title']}: {scene['narration']}"
        for scene in storyboard["scenes"]
    )
    extra = (
        f"\nAdditional Video Overview instructions:\n{extra_instructions}\n"
        if extra_instructions
        else ""
    )
    return f"""
Create a source-grounded Cinematic Video Overview about: {topic}

Use a polished documentary narration. Follow this scene order so the narration
and the separately rendered Veo scenes remain thematically aligned. Cover the
important claims in the selected sources. Do not mention the storyboard, audio
extraction, rendering process, or production tools.

Scene outline:
{outline}
{extra}
""".strip()


async def _create_native_video_overview(
    client: NotebookLMClient,
    *,
    notebook_id: str,
    source_ids: list[str] | None,
    language: str,
    topic: str,
    storyboard: dict[str, Any],
    extra_instructions: str | None,
    output_path: Path,
    timeout: float,
) -> Path:
    instructions = _video_overview_instructions(
        topic=topic,
        storyboard=storyboard,
        extra_instructions=extra_instructions,
    )
    click.echo(
        "Generating NotebookLM Cinematic Video Overview for narration...",
        err=True,
    )
    status = await client.artifacts.generate_cinematic_video(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
    )
    final_status = await client.artifacts.wait_for_completion(
        notebook_id,
        status.task_id,
        timeout=timeout,
    )
    if str(final_status.status) != "completed":
        raise base.PipelineError(
            "NotebookLM Cinematic Video Overview generation ended with "
            f"status {final_status.status}."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    downloaded = await client.artifacts.download_video(
        notebook_id,
        str(output_path),
        artifact_id=status.task_id,
    )
    return Path(downloaded)


def _extract_narration(
    *,
    ffmpeg: str,
    video_path: Path,
    output_path: Path,
    resume: bool,
) -> Path:
    if resume and output_path.is_file() and output_path.stat().st_size > 0:
        return output_path
    if not video_path.is_file():
        raise base.PipelineError(f"NotebookLM Video Overview was not found: {video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-map",
            "0:a:0",
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr[-3000:] or completed.stdout[-3000:]
        raise base.PipelineError(
            "Extract NotebookLM Video Overview narration failed with "
            f"exit code {completed.returncode}:\n{detail}"
        )
    return output_path


async def _run(
    *,
    notebook_id: str | None,
    profile: str | None,
    source_ids: list[str] | None,
    topic: str,
    language: str,
    scene_count: int,
    duration: int,
    model: str,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    references: tuple[Path, ...],
    enhance_prompt: bool,
    seed: int | None,
    storyboard_file: Path | None,
    storyboard_instructions: str | None,
    video_overview_file: Path | None,
    video_overview_instructions: str | None,
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

    storyboard: dict[str, Any] | None = None
    if storyboard_file is not None:
        storyboard = base._normalize_storyboard(
            json.loads(storyboard_file.read_text(encoding="utf-8")),
            default_duration=duration,
            maximum_scenes=scene_count,
        )
    elif resume and storyboard_path.is_file():
        storyboard = base._normalize_storyboard(
            json.loads(storyboard_path.read_text(encoding="utf-8")),
            default_duration=duration,
            maximum_scenes=scene_count,
        )

    if video_overview_file is None and resume and native_video_path.is_file():
        video_overview_file = native_video_path

    need_storyboard = storyboard is None
    need_video = video_overview_file is None
    if (need_storyboard or need_video) and not notebook_id:
        raise base.PipelineError(
            "--notebook is required unless both --storyboard-file and "
            "--video-overview-file are supplied."
        )

    if need_storyboard or need_video:
        async with NotebookLMClient.from_storage(profile=profile) as client:
            if storyboard is None:
                assert notebook_id is not None
                storyboard, raw = await base._create_storyboard(
                    client,
                    notebook_id=notebook_id,
                    source_ids=source_ids,
                    topic=topic,
                    scene_count=scene_count,
                    duration=duration,
                    language=language,
                    extra_instructions=storyboard_instructions,
                )
                base._write_json(storyboard_path, storyboard)
                raw_storyboard_path.write_text(raw, encoding="utf-8")

            if plan_only:
                return {
                    "status": "planned",
                    "storyboard": str(storyboard_path),
                    "scene_count": len(storyboard["scenes"]),
                }

            if video_overview_file is None:
                assert notebook_id is not None
                video_overview_file = await _create_native_video_overview(
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
    elif plan_only:
        assert storyboard is not None
        base._write_json(storyboard_path, storyboard)
        return {
            "status": "planned",
            "storyboard": str(storyboard_path),
            "scene_count": len(storyboard["scenes"]),
        }

    assert storyboard is not None
    assert video_overview_file is not None
    base._write_json(storyboard_path, storyboard)

    ffmpeg = base._require_binary(ffmpeg_value, "FFmpeg")
    ffprobe = base._require_binary(ffprobe_value, "FFprobe")
    narration_audio = await asyncio.to_thread(
        _extract_narration,
        ffmpeg=ffmpeg,
        video_path=video_overview_file,
        output_path=narration_path,
        resume=resume,
    )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise base.PipelineError("GEMINI_API_KEY is required for Veo rendering.")

    clips = await base._render_scenes(
        storyboard=storyboard,
        api_key=api_key,
        model=model,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        person_generation=person_generation,
        references=references,
        enhance_prompt=enhance_prompt,
        seed=seed,
        clips_dir=workspace / "clips",
        operations_dir=workspace / "operations",
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
        "topic": topic,
        "notebook_id": notebook_id,
        "source_ids": source_ids or [],
        "model": model,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "person_generation": "allow_adult" if references else person_generation,
        "reference_images": [str(path) for path in references],
        "storyboard": str(storyboard_path),
        "notebooklm_video_overview": str(video_overview_file),
        "narration_source": "notebooklm_cinematic_video_overview",
        "narration_audio": str(narration_audio),
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
@click.option("--duration", type=click.Choice(["4", "6", "8"]), default="8", show_default=True)
@click.option(
    "--model",
    type=click.Choice(base._SUPPORTED_MODELS),
    default=base._DEFAULT_MODEL,
    show_default=True,
)
@click.option(
    "--aspect-ratio",
    type=click.Choice(["16:9", "9:16"]),
    default="16:9",
    show_default=True,
)
@click.option(
    "--resolution",
    type=click.Choice(["720p", "1080p", "4k"]),
    default="1080p",
    show_default=True,
)
@click.option(
    "--person-generation",
    type=click.Choice(["allow_all", "allow_adult"]),
    default="allow_all",
    show_default=True,
)
@click.option(
    "--reference-image",
    "references",
    multiple=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option("--enhance-prompt/--no-enhance-prompt", default=True, show_default=True)
@click.option("--seed", type=int)
@click.option(
    "--storyboard-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--storyboard-instructions-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--video-overview-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--video-overview-instructions-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--workspace",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("controlled-video-overview-work"),
    show_default=True,
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("controlled-video-overview.mp4"),
    show_default=True,
)
@click.option("--ffmpeg", "ffmpeg_value", default="ffmpeg", show_default=True)
@click.option("--ffprobe", "ffprobe_value", default="ffprobe", show_default=True)
@click.option("--notebook-timeout", type=click.FloatRange(min=1), default=3600.0)
@click.option("--veo-timeout", type=click.FloatRange(min=1), default=1800.0)
@click.option("--poll-interval", type=click.FloatRange(min=1), default=10.0)
@click.option("--resume/--no-resume", default=True, show_default=True)
@click.option("--plan-only", is_flag=True)
@click.option("--json-output", is_flag=True)
def main(
    notebook_id: str | None,
    profile: str | None,
    source_ids: tuple[str, ...],
    topic: str,
    language: str,
    scene_count: int,
    duration: str,
    model: str,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    references: tuple[Path, ...],
    enhance_prompt: bool,
    seed: int | None,
    storyboard_file: Path | None,
    storyboard_instructions_file: Path | None,
    video_overview_file: Path | None,
    video_overview_instructions_file: Path | None,
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
    """Build a NotebookLM Video Overview narration + controlled Veo production."""
    if len(references) > 3:
        raise click.ClickException("At most three reference images are supported.")
    if references:
        person_generation = "allow_adult"
    if (references or resolution in {"1080p", "4k"}) and duration != "8":
        duration = "8"
        click.echo(
            "Using 8-second scenes because references and 1080p/4k require it.",
            err=True,
        )

    try:
        result = asyncio.run(
            _run(
                notebook_id=notebook_id,
                profile=profile,
                source_ids=list(source_ids) or None,
                topic=topic,
                language=language,
                scene_count=scene_count,
                duration=int(duration),
                model=model,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                person_generation=person_generation,
                references=references,
                enhance_prompt=enhance_prompt,
                seed=seed,
                storyboard_file=storyboard_file,
                storyboard_instructions=base._read_optional_text(
                    storyboard_instructions_file
                ),
                video_overview_file=video_overview_file,
                video_overview_instructions=base._read_optional_text(
                    video_overview_instructions_file
                ),
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
    except (base.PipelineError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    elif result.get("status") == "planned":
        click.echo(f"Storyboard ready: {result['storyboard']}")
    else:
        click.echo(f"Final video ready: {result['final_output']}")
        click.echo(f"Manifest: {workspace / 'manifest.json'}")


if __name__ == "__main__":
    main()

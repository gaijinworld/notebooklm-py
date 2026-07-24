#!/usr/bin/env python3
"""Assemble Google Flow-rendered clips with NotebookLM Video Overview narration.

Google Flow is used only as the controlled scene renderer. This script performs
no Veo generation and therefore requires no Gemini API key. It validates the
Flow clip set against an approved NotebookLM storyboard, extracts narration from
the native NotebookLM Cinematic Video Overview, normalizes the clips, and muxes
the final MP4 with FFmpeg.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click
import controlled_cinematic_pipeline as base
import controlled_cinematic_video_overview_pipeline as video_pipeline


def _collect_flow_clips(
    *,
    clips_directory: Path,
    storyboard: dict[str, Any],
) -> list[Path]:
    if not clips_directory.is_dir():
        raise base.PipelineError(f"Flow clips directory was not found: {clips_directory}")

    clips: list[Path] = []
    missing: list[str] = []
    for scene in storyboard["scenes"]:
        index = int(scene["index"])
        filename = f"scene-{index:03d}.mp4"
        clip = clips_directory / filename
        if not clip.is_file() or clip.stat().st_size == 0:
            missing.append(filename)
            continue
        clips.append(clip)

    if missing:
        rendered = ", ".join(missing)
        raise base.PipelineError(
            "Google Flow clips are missing or empty: "
            f"{rendered}. Export one approved MP4 per storyboard scene."
        )
    return clips


def _write_flow_render_manifest(
    *,
    workspace: Path,
    storyboard: dict[str, Any],
    clips: list[Path],
) -> Path:
    payload = {
        "schema_version": 1,
        "renderer": "google_flow",
        "scene_count": len(storyboard["scenes"]),
        "clips": [
            {
                "scene_index": int(scene["index"]),
                "scene_title": scene["title"],
                "clip": str(clip),
            }
            for scene, clip in zip(storyboard["scenes"], clips, strict=True)
        ],
    }
    output = workspace / "flow-render-manifest.json"
    base._write_json(output, payload)
    return output


async def _run(
    *,
    storyboard_file: Path,
    video_overview_file: Path,
    clips_directory: Path,
    workspace: Path,
    output_path: Path,
    aspect_ratio: str,
    resolution: str,
    ffmpeg_value: str,
    ffprobe_value: str,
    resume: bool,
) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    storyboard = base._normalize_storyboard(
        json.loads(storyboard_file.read_text(encoding="utf-8")),
        default_duration=8,
        maximum_scenes=60,
    )
    storyboard_path = workspace / "storyboard.json"
    base._write_json(storyboard_path, storyboard)

    clips = _collect_flow_clips(
        clips_directory=clips_directory,
        storyboard=storyboard,
    )
    flow_manifest = _write_flow_render_manifest(
        workspace=workspace,
        storyboard=storyboard,
        clips=clips,
    )

    ffmpeg = base._require_binary(ffmpeg_value, "FFmpeg")
    ffprobe = base._require_binary(ffprobe_value, "FFprobe")
    narration_path = workspace / "notebooklm-video-narration.m4a"
    narration_audio = await asyncio.to_thread(
        video_pipeline._extract_narration,
        ffmpeg=ffmpeg,
        video_path=video_overview_file,
        output_path=narration_path,
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
        "schema_version": 1,
        "status": "completed",
        "renderer": "google_flow",
        "storyboard": str(storyboard_path),
        "notebooklm_video_overview": str(video_overview_file),
        "narration_source": "notebooklm_cinematic_video_overview",
        "narration_audio": str(narration_audio),
        "flow_render_manifest": str(flow_manifest),
        "rendered_clips": [str(path) for path in clips],
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        **assembly,
    }
    base._write_json(workspace / "manifest.json", manifest)
    return manifest


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--storyboard-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Approved NotebookLM storyboard JSON used to validate Flow clip names.",
)
@click.option(
    "--video-overview-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Native NotebookLM Cinematic Video Overview MP4 containing narration.",
)
@click.option(
    "--clips-directory",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Directory containing scene-001.mp4 through scene-NNN.mp4 from Flow.",
)
@click.option(
    "--workspace",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("flow-cinematic-work"),
    show_default=True,
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("flow-controlled-video-overview.mp4"),
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
@click.option("--ffmpeg", "ffmpeg_value", default="ffmpeg", show_default=True)
@click.option("--ffprobe", "ffprobe_value", default="ffprobe", show_default=True)
@click.option("--resume/--no-resume", default=True, show_default=True)
@click.option("--json-output", is_flag=True)
def main(
    storyboard_file: Path,
    video_overview_file: Path,
    clips_directory: Path,
    workspace: Path,
    output_path: Path,
    aspect_ratio: str,
    resolution: str,
    ffmpeg_value: str,
    ffprobe_value: str,
    resume: bool,
    json_output: bool,
) -> None:
    """Assemble approved Google Flow clips with NotebookLM video narration."""
    try:
        result = asyncio.run(
            _run(
                storyboard_file=storyboard_file,
                video_overview_file=video_overview_file,
                clips_directory=clips_directory,
                workspace=workspace,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                ffmpeg_value=ffmpeg_value,
                ffprobe_value=ffprobe_value,
                resume=resume,
            )
        )
    except (base.PipelineError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Final video ready: {result['final_output']}")
        click.echo(f"Manifest: {workspace / 'manifest.json'}")


if __name__ == "__main__":
    main()

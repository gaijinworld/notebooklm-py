#!/usr/bin/env python3
"""Source-grounded NotebookLM -> controlled Veo 3.1 -> FFmpeg pipeline.

This script intentionally keeps Google's server-side safety and policy controls
active. It does not alter NotebookLM's undocumented Cinematic RPC. Instead it:

1. asks NotebookLM chat for a source-grounded JSON scene storyboard;
2. generates or downloads a NotebookLM Audio Overview for narration;
3. renders each storyboard scene through the existing controlled Veo 3.1 client;
4. normalizes and stitches scene MP4 files with FFmpeg; and
5. muxes NotebookLM narration as the authoritative final audio track.

Run from a notebooklm-py checkout after installing the package in editable mode.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click

from notebooklm import AudioFormat, AudioLength, NotebookLMClient
from notebooklm.veo_cli import (
    _DEFAULT_MODEL,
    _SUPPORTED_MODELS,
    _build_payload,
    _compose_prompt,
    _generate,
    _validate_controls,
)

_STORYBOARD_SCHEMA = {
    "title": "string",
    "summary": "string",
    "scenes": [
        {
            "title": "string",
            "narration": "string",
            "visual_prompt": "string",
            "composition": "string",
            "camera": "string",
            "lens": "string",
            "ambiance": "string",
            "negative_prompt": "string",
            "duration_seconds": 8,
        }
    ],
}

_DEFAULT_NEGATIVE = (
    "rear-only view, silhouette, face hidden by hair or props, mask, facial distortion, "
    "blank facial features, text covering the face, defocused primary subject"
)

_AUDIO_FORMATS: dict[str, AudioFormat] = {
    "deep-dive": AudioFormat.DEEP_DIVE,
    "brief": AudioFormat.BRIEF,
    "critique": AudioFormat.CRITIQUE,
    "debate": AudioFormat.DEBATE,
}
_AUDIO_LENGTHS: dict[str, AudioLength] = {
    "short": AudioLength.SHORT,
    "default": AudioLength.DEFAULT,
    "long": AudioLength.LONG,
}


class PipelineError(RuntimeError):
    """Raised when a controlled-cinematic pipeline stage cannot continue."""


def _read_optional_text(path: Path | None) -> str | None:
    if path is None:
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline >= 0:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _extract_json_object(value: str) -> dict[str, Any]:
    text = _strip_code_fence(value)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise PipelineError("NotebookLM did not return a JSON storyboard.") from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PipelineError(f"NotebookLM storyboard JSON is invalid: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PipelineError("NotebookLM storyboard must be one JSON object.")
    return parsed


def _normalize_scene(raw: Any, index: int, default_duration: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PipelineError(f"Storyboard scene {index} must be a JSON object.")

    visual_prompt = str(raw.get("visual_prompt") or raw.get("prompt") or "").strip()
    if not visual_prompt:
        raise PipelineError(f"Storyboard scene {index} has no visual_prompt.")

    duration_raw = raw.get("duration_seconds", default_duration)
    try:
        duration = int(duration_raw)
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"Storyboard scene {index} has an invalid duration.") from exc
    if duration not in {4, 6, 8}:
        duration = default_duration

    narration = str(raw.get("narration") or "").strip()
    return {
        "index": index,
        "title": str(raw.get("title") or f"Scene {index}").strip(),
        "narration": narration,
        "visual_prompt": visual_prompt,
        "composition": str(
            raw.get("composition")
            or "eye-level medium close-up or two-shot, unobstructed faces, both eyes visible"
        ).strip(),
        "camera": str(
            raw.get("camera")
            or "slow cinematic movement while preserving front or three-quarter facial visibility"
        ).strip(),
        "lens": str(
            raw.get("lens") or "50mm natural perspective, primary faces in sharp focus"
        ).strip(),
        "ambiance": str(
            raw.get("ambiance") or "soft balanced frontal lighting with natural skin tones"
        ).strip(),
        "negative_prompt": str(raw.get("negative_prompt") or _DEFAULT_NEGATIVE).strip(),
        "duration_seconds": duration,
    }


def _normalize_storyboard(
    payload: dict[str, Any], *, default_duration: int, maximum_scenes: int
) -> dict[str, Any]:
    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise PipelineError("NotebookLM storyboard JSON contains no scenes.")
    if len(raw_scenes) > maximum_scenes:
        raw_scenes = raw_scenes[:maximum_scenes]

    scenes = [
        _normalize_scene(scene, index, default_duration)
        for index, scene in enumerate(raw_scenes, start=1)
    ]
    return {
        "schema_version": 1,
        "title": str(payload.get("title") or "Controlled Cinematic Overview").strip(),
        "summary": str(payload.get("summary") or "").strip(),
        "scenes": scenes,
    }


def _storyboard_question(
    *,
    topic: str,
    scene_count: int,
    duration: int,
    language: str,
    extra_instructions: str | None,
) -> str:
    extra = f"\nAdditional project instructions:\n{extra_instructions}\n" if extra_instructions else ""
    return f"""
Create a source-grounded cinematic scene plan about: {topic}

Return ONLY valid JSON. Do not use Markdown fences and do not add commentary.
Use exactly {scene_count} scenes. The output language is {language}.
Every scene will be rendered as a separate {duration}-second Veo 3.1 clip.

Requirements:
- Ground every factual claim and narration idea in the selected notebook sources.
- Use fictional, non-famous adults where people improve understanding.
- Favor eye-level close-ups, medium close-ups, and two-shots with clearly visible faces.
- Keep faces unobstructed, naturally lit, and front-facing or at a natural three-quarter angle.
- Use realistic environments relevant to the sources.
- Give every scene a concise narration idea and a standalone visual prompt.
- Keep composition, camera, lens, ambiance, and negative-prompt instructions separate.
- Avoid sexualized descriptions and any request to bypass safety systems.
{extra}
Use this exact JSON shape:
{json.dumps(_STORYBOARD_SCHEMA, indent=2)}
""".strip()


def _narration_instructions(
    *,
    topic: str,
    storyboard: dict[str, Any],
    extra_instructions: str | None,
) -> str:
    outline = "\n".join(
        f"{scene['index']}. {scene['title']}: {scene['narration']}"
        for scene in storyboard["scenes"]
    )
    extra = f"\nAdditional narration instructions:\n{extra_instructions}\n" if extra_instructions else ""
    return f"""
Create a source-grounded Audio Overview about: {topic}

Use a polished documentary tone. Follow this scene order so the narration and visuals remain
thematically aligned. Do not mention the storyboard, rendering process, or production tools.

Scene outline:
{outline}
{extra}
""".strip()


async def _create_storyboard(
    client: NotebookLMClient,
    *,
    notebook_id: str,
    source_ids: list[str] | None,
    topic: str,
    scene_count: int,
    duration: int,
    language: str,
    extra_instructions: str | None,
) -> tuple[dict[str, Any], str]:
    question = _storyboard_question(
        topic=topic,
        scene_count=scene_count,
        duration=duration,
        language=language,
        extra_instructions=extra_instructions,
    )
    click.echo("Asking NotebookLM for a source-grounded scene storyboard...", err=True)
    result = await client.chat.ask(notebook_id, question, source_ids=source_ids)
    payload = _extract_json_object(result.answer)
    storyboard = _normalize_storyboard(
        payload,
        default_duration=duration,
        maximum_scenes=scene_count,
    )
    return storyboard, result.answer


async def _create_narration(
    client: NotebookLMClient,
    *,
    notebook_id: str,
    source_ids: list[str] | None,
    language: str,
    topic: str,
    storyboard: dict[str, Any],
    audio_format: AudioFormat,
    audio_length: AudioLength,
    extra_instructions: str | None,
    output_path: Path,
    timeout: float,
) -> Path:
    instructions = _narration_instructions(
        topic=topic,
        storyboard=storyboard,
        extra_instructions=extra_instructions,
    )
    click.echo("Generating NotebookLM Audio Overview narration...", err=True)
    status = await client.artifacts.generate_audio(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
        audio_format=audio_format,
        audio_length=audio_length,
    )
    final_status = await client.artifacts.wait_for_completion(
        notebook_id,
        status.task_id,
        timeout=timeout,
    )
    if str(final_status.status) != "completed":
        raise PipelineError(f"NotebookLM audio generation ended with status {final_status.status}.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    downloaded = await client.artifacts.download_audio(
        notebook_id,
        str(output_path),
        artifact_id=status.task_id,
    )
    return Path(downloaded)


def _require_binary(value: str, display_name: str) -> str:
    candidate = Path(value).expanduser()
    if candidate.parent != Path(".") or candidate.is_absolute():
        if not candidate.is_file():
            raise PipelineError(f"{display_name} executable not found: {candidate}")
        return str(candidate)
    resolved = shutil.which(value)
    if resolved is None:
        raise PipelineError(
            f"{display_name} was not found on PATH. Install FFmpeg or pass the executable path."
        )
    return resolved


def _run_process(command: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr[-3000:] or completed.stdout[-3000:]
        raise PipelineError(f"{label} failed with exit code {completed.returncode}:\n{detail}")
    return completed


def _probe_duration(ffprobe: str, media_path: Path) -> float:
    completed = _run_process(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(media_path),
        ],
        label=f"ffprobe {media_path.name}",
    )
    try:
        duration = float(json.loads(completed.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Could not read media duration for {media_path}.") from exc
    if duration <= 0:
        raise PipelineError(f"Media duration is not positive for {media_path}.")
    return duration


def _target_size(aspect_ratio: str, resolution: str) -> tuple[int, int]:
    landscape = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "4k": (3840, 2160),
    }[resolution]
    if aspect_ratio == "16:9":
        return landscape
    return landscape[1], landscape[0]


def _normalize_clips(
    *,
    clips: list[Path],
    output_dir: Path,
    ffmpeg: str,
    aspect_ratio: str,
    resolution: str,
    resume: bool,
) -> list[Path]:
    width, height = _target_size(aspect_ratio, resolution)
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24"
    )
    for index, clip in enumerate(clips, start=1):
        destination = output_dir / f"scene-{index:03d}.mp4"
        if resume and destination.is_file() and destination.stat().st_size > 0:
            normalized.append(destination)
            continue
        _run_process(
            [
                ffmpeg,
                "-y",
                "-i",
                str(clip),
                "-map",
                "0:v:0",
                "-vf",
                video_filter,
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
            label=f"normalize scene {index}",
        )
        normalized.append(destination)
    return normalized


def _concat_file_line(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
    return f"file '{escaped}'"


def _assemble_final_video(
    *,
    clips: list[Path],
    narration_audio: Path,
    output_path: Path,
    workspace: Path,
    ffmpeg: str,
    ffprobe: str,
    aspect_ratio: str,
    resolution: str,
    resume: bool,
) -> dict[str, Any]:
    if not clips:
        raise PipelineError("No rendered scene clips are available for assembly.")
    if not narration_audio.is_file():
        raise PipelineError(f"Narration audio was not found: {narration_audio}")

    normalized = _normalize_clips(
        clips=clips,
        output_dir=workspace / "normalized",
        ffmpeg=ffmpeg,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        resume=resume,
    )
    audio_duration = _probe_duration(ffprobe, narration_audio)
    sequence_duration = sum(_probe_duration(ffprobe, clip) for clip in normalized)
    repeat_count = max(1, math.ceil(audio_duration / sequence_duration))

    concat_path = workspace / "concat.txt"
    concat_lines = [
        _concat_file_line(clip)
        for _ in range(repeat_count)
        for clip in normalized
    ]
    concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    silent_video = workspace / "assembled-silent.mp4"
    _run_process(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(silent_video),
        ],
        label="concatenate normalized scenes",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run_process(
        [
            ffmpeg,
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(narration_audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        label="mux NotebookLM narration with assembled video",
    )
    return {
        "audio_duration_seconds": round(audio_duration, 3),
        "single_scene_sequence_seconds": round(sequence_duration, 3),
        "visual_sequence_repetitions": repeat_count,
        "normalized_clips": [str(path) for path in normalized],
        "final_output": str(output_path),
    }


async def _render_scenes(
    *,
    storyboard: dict[str, Any],
    api_key: str,
    model: str,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    references: tuple[Path, ...],
    enhance_prompt: bool,
    seed: int | None,
    clips_dir: Path,
    operations_dir: Path,
    timeout: float,
    poll_interval: float,
    resume: bool,
) -> list[Path]:
    clips_dir.mkdir(parents=True, exist_ok=True)
    operations_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []

    image_guided = bool(references)
    effective_person_generation = "allow_adult" if image_guided else person_generation

    for scene in storyboard["scenes"]:
        index = int(scene["index"])
        destination = clips_dir / f"scene-{index:03d}.mp4"
        if resume and destination.is_file() and destination.stat().st_size > 0:
            click.echo(f"Reusing rendered scene {index}: {destination}", err=True)
            rendered.append(destination)
            continue

        duration = int(scene["duration_seconds"])
        if references or resolution in {"1080p", "4k"}:
            duration = 8
        _validate_controls(
            duration=duration,
            resolution=resolution,
            references=references,
            first_frame=None,
            last_frame=None,
            person_generation=effective_person_generation,
        )
        prompt = _compose_prompt(
            scene["visual_prompt"],
            composition=scene["composition"],
            camera=scene["camera"],
            lens=scene["lens"],
            ambiance=scene["ambiance"],
        )
        payload = _build_payload(
            prompt,
            aspect_ratio=aspect_ratio,
            duration=duration,
            resolution=resolution,
            person_generation=effective_person_generation,
            negative_prompt=scene["negative_prompt"],
            seed=None if seed is None else seed + index,
            enhance_prompt=enhance_prompt,
            references=references,
            first_frame=None,
            last_frame=None,
        )
        click.echo(
            f"Rendering scene {index}/{len(storyboard['scenes'])}: {scene['title']}",
            err=True,
        )
        await asyncio.to_thread(
            _generate,
            api_key=api_key,
            model=model,
            payload=payload,
            output=destination,
            timeout=timeout,
            poll_interval=poll_interval,
            save_operation=operations_dir / f"scene-{index:03d}.json",
        )
        rendered.append(destination)
    return rendered


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


async def _run_pipeline(
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
    narration_audio: Path | None,
    narration_instructions: str | None,
    audio_format: AudioFormat,
    audio_length: AudioLength,
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
    narration_path = workspace / "narration.mp3"

    storyboard: dict[str, Any] | None = None
    raw_storyboard: str | None = None

    if storyboard_file is not None:
        storyboard = _normalize_storyboard(
            json.loads(storyboard_file.read_text(encoding="utf-8")),
            default_duration=duration,
            maximum_scenes=scene_count,
        )
    elif resume and storyboard_path.is_file():
        storyboard = _normalize_storyboard(
            json.loads(storyboard_path.read_text(encoding="utf-8")),
            default_duration=duration,
            maximum_scenes=scene_count,
        )

    need_notebook_storyboard = storyboard is None
    need_notebook_audio = narration_audio is None and not (resume and narration_path.is_file())
    if (need_notebook_storyboard or need_notebook_audio) and not notebook_id:
        raise PipelineError(
            "--notebook is required unless both --storyboard-file and --narration-audio are supplied."
        )

    if need_notebook_storyboard or need_notebook_audio:
        async with NotebookLMClient.from_storage(profile=profile) as client:
            if storyboard is None:
                assert notebook_id is not None
                storyboard, raw_storyboard = await _create_storyboard(
                    client,
                    notebook_id=notebook_id,
                    source_ids=source_ids,
                    topic=topic,
                    scene_count=scene_count,
                    duration=duration,
                    language=language,
                    extra_instructions=storyboard_instructions,
                )
                _write_json(storyboard_path, storyboard)
                raw_storyboard_path.write_text(raw_storyboard, encoding="utf-8")

            if plan_only:
                return {
                    "status": "planned",
                    "storyboard": str(storyboard_path),
                    "scene_count": len(storyboard["scenes"]),
                }

            if narration_audio is None:
                if resume and narration_path.is_file():
                    narration_audio = narration_path
                else:
                    assert notebook_id is not None
                    narration_audio = await _create_narration(
                        client,
                        notebook_id=notebook_id,
                        source_ids=source_ids,
                        language=language,
                        topic=topic,
                        storyboard=storyboard,
                        audio_format=audio_format,
                        audio_length=audio_length,
                        extra_instructions=narration_instructions,
                        output_path=narration_path,
                        timeout=notebook_timeout,
                    )
    else:
        assert storyboard is not None
        if plan_only:
            _write_json(storyboard_path, storyboard)
            return {
                "status": "planned",
                "storyboard": str(storyboard_path),
                "scene_count": len(storyboard["scenes"]),
            }

    assert storyboard is not None
    _write_json(storyboard_path, storyboard)
    if narration_audio is None:
        narration_audio = narration_path

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise PipelineError("GEMINI_API_KEY is required for Veo rendering.")
    ffmpeg = _require_binary(ffmpeg_value, "FFmpeg")
    ffprobe = _require_binary(ffprobe_value, "FFprobe")

    clips = await _render_scenes(
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
        _assemble_final_video,
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
        "topic": topic,
        "notebook_id": notebook_id,
        "source_ids": source_ids or [],
        "model": model,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "person_generation": "allow_adult" if references else person_generation,
        "reference_images": [str(path) for path in references],
        "storyboard": str(storyboard_path),
        "narration_audio": str(narration_audio),
        "rendered_clips": [str(path) for path in clips],
        **assembly,
    }
    _write_json(workspace / "manifest.json", manifest)
    return manifest


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--notebook", "notebook_id", help="Notebook ID used for storyboard and narration.")
@click.option("--profile", help="NotebookLM authentication profile name.")
@click.option(
    "--source",
    "source_ids",
    multiple=True,
    help="Full NotebookLM source ID; repeat to limit grounding. Omit for all sources.",
)
@click.option("--topic", required=True, help="Topic and editorial goal for the final overview.")
@click.option("--language", default="en", show_default=True)
@click.option("--scene-count", type=click.IntRange(1, 60), default=12, show_default=True)
@click.option("--duration", type=click.Choice(["4", "6", "8"]), default="8", show_default=True)
@click.option("--model", type=click.Choice(_SUPPORTED_MODELS), default=_DEFAULT_MODEL, show_default=True)
@click.option("--aspect-ratio", type=click.Choice(["16:9", "9:16"]), default="16:9", show_default=True)
@click.option("--resolution", type=click.Choice(["720p", "1080p", "4k"]), default="1080p", show_default=True)
@click.option(
    "--person-generation",
    type=click.Choice(["allow_all", "allow_adult"]),
    default="allow_all",
    show_default=True,
    help="Veo people-generation mode. Reference images automatically use allow_adult.",
)
@click.option(
    "--reference-image",
    "references",
    multiple=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Veo asset reference image; repeat up to three times.",
)
@click.option("--enhance-prompt/--no-enhance-prompt", default=True, show_default=True)
@click.option("--seed", type=int, help="Optional base seed; scene index is added to it.")
@click.option(
    "--storyboard-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Use an existing storyboard JSON instead of asking NotebookLM chat.",
)
@click.option(
    "--storyboard-instructions-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--narration-audio",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Use existing narration audio instead of generating a NotebookLM Audio Overview.",
)
@click.option(
    "--narration-instructions-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--audio-format",
    type=click.Choice(sorted(_AUDIO_FORMATS)),
    default="brief",
    show_default=True,
)
@click.option(
    "--audio-length",
    type=click.Choice(sorted(_AUDIO_LENGTHS)),
    default="long",
    show_default=True,
)
@click.option(
    "--workspace",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("controlled-cinematic-work"),
    show_default=True,
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("controlled-cinematic-overview.mp4"),
    show_default=True,
)
@click.option("--ffmpeg", "ffmpeg_value", default="ffmpeg", show_default=True)
@click.option("--ffprobe", "ffprobe_value", default="ffprobe", show_default=True)
@click.option("--notebook-timeout", type=click.FloatRange(min=1), default=3600.0, show_default=True)
@click.option("--veo-timeout", type=click.FloatRange(min=1), default=1800.0, show_default=True)
@click.option("--poll-interval", type=click.FloatRange(min=1), default=10.0, show_default=True)
@click.option("--resume/--no-resume", default=True, show_default=True)
@click.option("--plan-only", is_flag=True, help="Generate/validate the storyboard, then stop.")
@click.option("--json-output", is_flag=True, help="Print the final manifest as JSON.")
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
    narration_audio: Path | None,
    narration_instructions_file: Path | None,
    audio_format: str,
    audio_length: str,
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
    """Build a complete source-grounded NotebookLM + Veo + FFmpeg overview."""
    if len(references) > 3:
        raise click.ClickException("At most three --reference-image values are supported.")
    if references and person_generation == "allow_all":
        person_generation = "allow_adult"
    if (references or resolution in {"1080p", "4k"}) and duration != "8":
        duration = "8"
        click.echo(
            "Using 8-second scenes because references and 1080p/4k require that duration.",
            err=True,
        )

    try:
        result = asyncio.run(
            _run_pipeline(
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
                storyboard_instructions=_read_optional_text(storyboard_instructions_file),
                narration_audio=narration_audio,
                narration_instructions=_read_optional_text(narration_instructions_file),
                audio_format=_AUDIO_FORMATS[audio_format],
                audio_length=_AUDIO_LENGTHS[audio_length],
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
    except (PipelineError, json.JSONDecodeError) as exc:
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

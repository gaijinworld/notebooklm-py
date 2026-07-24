"""Reference-conditioned Veo scene planning for NotebookLM cinematic workflows.

This module contains transport-neutral validation and payload construction for
controlled Veo 3.1 shots. It keeps Google's server-side safety and identity
protections active. Reference images should depict fictional adults or adults
whose likeness the operator is authorized to use.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Mapping, Sequence

SUPPORTED_MODES = ("text", "reference", "interpolation", "extension")
SUPPORTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_VIDEO_MIME_TYPES = {"video/mp4"}
DEFAULT_NEGATIVE_PROMPT = (
    "rear-only view, silhouette, face hidden by hair or props, mask, facial distortion, "
    "blank facial features, extreme crop, text covering the face, defocused primary subject"
)


class ReferenceSceneError(ValueError):
    """Raised when a scene cannot be represented by a supported Veo mode."""


def _text(value: Any, default: str = "") -> str:
    resolved = str(value or default).strip()
    return resolved


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ReferenceSceneError("Expected a JSON array of strings.")
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_reference_storyboard(
    payload: Mapping[str, Any],
    *,
    default_duration: int = 8,
    maximum_scenes: int = 60,
) -> dict[str, Any]:
    """Normalize schema-v1/v2 storyboards without discarding reference metadata."""
    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ReferenceSceneError("Storyboard JSON must contain at least one scene.")
    if len(raw_scenes) > maximum_scenes:
        raise ReferenceSceneError(
            f"Storyboard has {len(raw_scenes)} scenes; maximum is {maximum_scenes}."
        )

    raw_subjects = payload.get("subjects") or payload.get("source_documents") or []
    subjects: list[dict[str, Any]] = []
    if raw_subjects:
        if not isinstance(raw_subjects, list):
            raise ReferenceSceneError("subjects must be a JSON array.")
        for index, subject in enumerate(raw_subjects, start=1):
            if not isinstance(subject, Mapping):
                raise ReferenceSceneError(f"Subject {index} must be a JSON object.")
            subject_id = _text(subject.get("id"), f"subject-{index:03d}")
            subjects.append(
                {
                    "id": subject_id,
                    "description": _text(subject.get("description") or subject.get("notes")),
                    "reference_images": _string_list(subject.get("reference_images")),
                }
            )

    scenes: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_scenes, start=1):
        if not isinstance(raw, Mapping):
            raise ReferenceSceneError(f"Scene {index} must be a JSON object.")
        visual_prompt = _text(raw.get("visual_prompt") or raw.get("prompt"))
        if not visual_prompt:
            raise ReferenceSceneError(f"Scene {index} requires visual_prompt.")

        try:
            duration = int(raw.get("duration_seconds", default_duration))
        except (TypeError, ValueError) as exc:
            raise ReferenceSceneError(f"Scene {index} has an invalid duration.") from exc
        if duration not in {4, 6, 8}:
            raise ReferenceSceneError(f"Scene {index} duration must be 4, 6, or 8 seconds.")

        subject_ids = _string_list(raw.get("subject_ids"))
        first_frame = _text(raw.get("first_frame")) or None
        last_frame = _text(raw.get("last_frame")) or None
        extend_from_scene = _text(raw.get("extend_from_scene")) or None
        mode = _text(raw.get("generation_mode"))
        if not mode:
            if extend_from_scene:
                mode = "extension"
            elif first_frame or last_frame:
                mode = "interpolation"
            elif subject_ids:
                mode = "reference"
            else:
                mode = "text"
        if mode not in SUPPORTED_MODES:
            raise ReferenceSceneError(
                f"Scene {index} generation_mode must be one of: {', '.join(SUPPORTED_MODES)}."
            )

        scenes.append(
            {
                "index": index,
                "id": _text(raw.get("id"), f"scene-{index:03d}"),
                "title": _text(raw.get("title"), f"Scene {index}"),
                "narration": _text(raw.get("narration")),
                "visual_prompt": visual_prompt,
                "dialogue": _text(raw.get("dialogue")),
                "ambient_audio": _text(raw.get("ambient_audio")),
                "subject_ids": subject_ids,
                "generation_mode": mode,
                "composition": _text(
                    raw.get("composition"),
                    "eye-level medium close-up or two-shot, complete unobstructed adult faces",
                ),
                "camera": _text(
                    raw.get("camera"),
                    "restrained cinematic movement preserving front or natural three-quarter faces",
                ),
                "lens": _text(
                    raw.get("lens"),
                    "50mm natural perspective, primary faces in sharp focus",
                ),
                "ambiance": _text(
                    raw.get("ambiance"),
                    "soft balanced frontal lighting with natural skin tones",
                ),
                "negative_prompt": _text(
                    raw.get("negative_prompt"), DEFAULT_NEGATIVE_PROMPT
                ),
                "duration_seconds": duration,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "extend_from_scene": extend_from_scene,
            }
        )

    return {
        "schema_version": 2,
        "title": _text(payload.get("title"), "Controlled Cinematic Overview"),
        "summary": _text(payload.get("summary")),
        "subjects": subjects,
        "scenes": scenes,
    }


def parse_subject_reference(value: str) -> tuple[str, Path]:
    """Parse SUBJECT_ID=PATH command-line mappings."""
    subject_id, separator, raw_path = value.partition("=")
    if not separator or not subject_id.strip() or not raw_path.strip():
        raise ReferenceSceneError(
            "Subject reference must use SUBJECT_ID=PATH, for example presenter=front.png."
        )
    return subject_id.strip(), Path(raw_path.strip()).expanduser()


def build_subject_reference_map(
    storyboard: Mapping[str, Any],
    overrides: Sequence[str],
    *,
    asset_root: Path,
) -> dict[str, tuple[Path, ...]]:
    """Resolve storyboard and CLI reference images into a subject-to-path map."""
    resolved: dict[str, list[Path]] = {}
    for subject in storyboard.get("subjects", []):
        subject_id = str(subject["id"])
        paths = []
        for raw_path in subject.get("reference_images", []):
            path = Path(raw_path).expanduser()
            if not path.is_absolute():
                path = asset_root / path
            paths.append(path)
        resolved[subject_id] = paths

    for override in overrides:
        subject_id, path = parse_subject_reference(override)
        if not path.is_absolute():
            path = asset_root / path
        resolved.setdefault(subject_id, []).append(path)

    result: dict[str, tuple[Path, ...]] = {}
    for subject_id, paths in resolved.items():
        deduplicated: list[Path] = []
        for path in paths:
            normalized = path.resolve()
            if normalized not in deduplicated:
                deduplicated.append(normalized)
        if len(deduplicated) > 3:
            raise ReferenceSceneError(
                f"Subject {subject_id!r} has {len(deduplicated)} references; "
                "Veo supports at most 3."
            )
        result[subject_id] = tuple(deduplicated)
    return result


def scene_reference_paths(
    scene: Mapping[str, Any], subject_references: Mapping[str, tuple[Path, ...]]
) -> tuple[Path, ...]:
    paths: list[Path] = []
    for subject_id in scene.get("subject_ids", []):
        for path in subject_references.get(str(subject_id), ()):
            if path not in paths:
                paths.append(path)
    if len(paths) > 3:
        raise ReferenceSceneError(
            f"Scene {scene.get('id')} resolves to {len(paths)} reference images; maximum is 3."
        )
    return tuple(paths)


def build_scene_prompt(scene: Mapping[str, Any], *, include_audio_cues: bool) -> str:
    """Compose an auditable Veo prompt from a normalized scene."""
    parts = [str(scene["visual_prompt"]).strip()]
    if include_audio_cues and scene.get("dialogue"):
        dialogue = str(scene["dialogue"]).replace('"', "'").strip()
        parts.append(f'Dialogue: "{dialogue}"')
    if include_audio_cues and scene.get("ambient_audio"):
        parts.append(f"Ambient audio and sound effects: {str(scene['ambient_audio']).strip()}")
    parts.extend(
        [
            f"Composition: {scene['composition']}",
            f"Camera positioning and motion: {scene['camera']}",
            f"Focus and lens effects: {scene['lens']}",
            f"Lighting and ambiance: {scene['ambiance']}",
        ]
    )
    return "\n\n".join(part for part in parts if part.strip())


def _inline_media(path: Path, supported_mime_types: set[str]) -> dict[str, Any]:
    if not path.is_file():
        raise ReferenceSceneError(f"Media file not found: {path}")
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type not in supported_mime_types:
        expected = ", ".join(sorted(supported_mime_types))
        raise ReferenceSceneError(f"Unsupported media type for {path}; expected {expected}.")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime_type, "data": encoded}}


def validate_scene_mode(
    *,
    mode: str,
    duration: int,
    resolution: str,
    person_generation: str,
    references: Sequence[Path],
    first_frame: Path | None,
    last_frame: Path | None,
    extension_video: Path | None,
) -> tuple[int, str, str]:
    """Validate mutually exclusive Veo modes and return normalized controls."""
    if mode not in SUPPORTED_MODES:
        raise ReferenceSceneError(f"Unsupported generation mode: {mode}")
    if duration not in {4, 6, 8}:
        raise ReferenceSceneError("Veo duration must be 4, 6, or 8 seconds.")
    if len(references) > 3:
        raise ReferenceSceneError("Veo supports at most three reference images.")
    if last_frame and not first_frame:
        raise ReferenceSceneError("A last frame requires a first frame.")

    if mode == "text":
        if references or first_frame or last_frame or extension_video:
            raise ReferenceSceneError("Text mode cannot include images or an extension video.")
        if resolution in {"1080p", "4k"}:
            duration = 8
        return duration, resolution, "allow_all"

    if mode == "reference":
        if not references:
            raise ReferenceSceneError("Reference mode requires one to three subject images.")
        if first_frame or last_frame or extension_video:
            raise ReferenceSceneError(
                "Reference images cannot be combined with interpolation frames or extension."
            )
        return 8, resolution, "allow_adult"

    if mode == "interpolation":
        if references or extension_video:
            raise ReferenceSceneError(
                "Interpolation cannot be combined with reference images or extension."
            )
        if not first_frame or not last_frame:
            raise ReferenceSceneError("Interpolation requires both first_frame and last_frame.")
        return 8, resolution, "allow_adult"

    if references or first_frame or last_frame:
        raise ReferenceSceneError(
            "Extension cannot be combined with reference images or interpolation frames."
        )
    if extension_video is None:
        raise ReferenceSceneError("Extension mode requires a previous Veo-generated video.")
    return 8, "720p", "allow_all"


def build_scene_payload(
    scene: Mapping[str, Any],
    *,
    aspect_ratio: str,
    resolution: str,
    person_generation: str,
    references: Sequence[Path] = (),
    first_frame: Path | None = None,
    last_frame: Path | None = None,
    extension_video: Path | None = None,
    enhance_prompt: bool = True,
    seed: int | None = None,
    include_audio_cues: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one Gemini REST payload and a compact non-secret request summary."""
    mode = str(scene["generation_mode"])
    duration, effective_resolution, effective_person = validate_scene_mode(
        mode=mode,
        duration=int(scene["duration_seconds"]),
        resolution=resolution,
        person_generation=person_generation,
        references=references,
        first_frame=first_frame,
        last_frame=last_frame,
        extension_video=extension_video,
    )

    instance: dict[str, Any] = {
        "prompt": build_scene_prompt(scene, include_audio_cues=include_audio_cues)
    }
    if mode == "reference":
        instance["referenceImages"] = [
            {"image": _inline_media(path, SUPPORTED_IMAGE_MIME_TYPES), "referenceType": "asset"}
            for path in references
        ]
    elif mode == "interpolation":
        assert first_frame is not None and last_frame is not None
        instance["image"] = _inline_media(first_frame, SUPPORTED_IMAGE_MIME_TYPES)
        instance["lastFrame"] = _inline_media(last_frame, SUPPORTED_IMAGE_MIME_TYPES)
    elif mode == "extension":
        assert extension_video is not None
        instance["video"] = _inline_media(extension_video, SUPPORTED_VIDEO_MIME_TYPES)

    parameters: dict[str, Any] = {
        "aspectRatio": aspect_ratio,
        "durationSeconds": duration,
        "resolution": effective_resolution,
        "enhancePrompt": enhance_prompt,
        "numberOfVideos": 1,
        "personGeneration": effective_person,
    }
    negative_prompt = str(scene.get("negative_prompt") or "").strip()
    if negative_prompt:
        parameters["negativePrompt"] = negative_prompt
    if seed is not None and mode != "extension":
        parameters["seed"] = seed

    summary = {
        "scene_id": scene["id"],
        "generation_mode": mode,
        "duration_seconds": duration,
        "resolution": effective_resolution,
        "person_generation": effective_person,
        "reference_images": [str(path) for path in references],
        "first_frame": str(first_frame) if first_frame else None,
        "last_frame": str(last_frame) if last_frame else None,
        "extension_video": str(extension_video) if extension_video else None,
        "audio_cues_in_prompt": include_audio_cues,
    }
    return {"instances": [instance], "parameters": parameters}, summary

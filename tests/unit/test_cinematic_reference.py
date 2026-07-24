from pathlib import Path

import pytest

from notebooklm._cinematic_reference import (
    ReferenceSceneError,
    build_scene_payload,
    normalize_reference_storyboard,
    validate_scene_mode,
)


def _scene(**overrides: object) -> dict[str, object]:
    scene: dict[str, object] = {
        "id": "scene-001",
        "title": "Presenter",
        "narration": "Explain the finding.",
        "visual_prompt": "An adult presenter explains the finding.",
        "dialogue": "This is the result.",
        "ambient_audio": "quiet office room tone",
        "subject_ids": ["presenter"],
        "generation_mode": "reference",
        "composition": "medium close-up",
        "camera": "slow dolly-in",
        "lens": "50mm",
        "ambiance": "soft frontal light",
        "negative_prompt": "rear-only view",
        "duration_seconds": 8,
        "first_frame": None,
        "last_frame": None,
        "extend_from_scene": None,
    }
    scene.update(overrides)
    return scene


def test_normalize_storyboard_preserves_reference_metadata() -> None:
    payload = {
        "title": "Overview",
        "subjects": [
            {
                "id": "presenter",
                "description": "authorized adult presenter",
                "reference_images": ["front.png", "three-quarter.png"],
            }
        ],
        "scenes": [_scene()],
    }

    result = normalize_reference_storyboard(payload)

    assert result["schema_version"] == 2
    assert result["subjects"][0]["reference_images"] == [
        "front.png",
        "three-quarter.png",
    ]
    assert result["scenes"][0]["dialogue"] == "This is the result."
    assert result["scenes"][0]["generation_mode"] == "reference"


def test_reference_mode_normalizes_to_adult_and_eight_seconds(tmp_path: Path) -> None:
    reference = tmp_path / "face.png"
    reference.write_bytes(b"not-a-real-png")

    duration, resolution, person = validate_scene_mode(
        mode="reference",
        duration=4,
        resolution="1080p",
        person_generation="allow_all",
        references=(reference,),
        first_frame=None,
        last_frame=None,
        extension_video=None,
    )

    assert duration == 8
    assert resolution == "1080p"
    assert person == "allow_adult"


def test_reference_and_interpolation_are_mutually_exclusive(tmp_path: Path) -> None:
    reference = tmp_path / "face.png"
    frame = tmp_path / "frame.png"
    reference.write_bytes(b"x")
    frame.write_bytes(b"x")

    with pytest.raises(ReferenceSceneError, match="cannot be combined"):
        validate_scene_mode(
            mode="reference",
            duration=8,
            resolution="720p",
            person_generation="allow_adult",
            references=(reference,),
            first_frame=frame,
            last_frame=frame,
            extension_video=None,
        )


def test_extension_forces_720p_allow_all(tmp_path: Path) -> None:
    video = tmp_path / "previous.mp4"
    video.write_bytes(b"video")

    duration, resolution, person = validate_scene_mode(
        mode="extension",
        duration=4,
        resolution="4k",
        person_generation="allow_adult",
        references=(),
        first_frame=None,
        last_frame=None,
        extension_video=video,
    )

    assert duration == 8
    assert resolution == "720p"
    assert person == "allow_all"


def test_payload_includes_reference_images_and_optional_audio_cues(tmp_path: Path) -> None:
    reference = tmp_path / "face.png"
    reference.write_bytes(b"image")

    payload, summary = build_scene_payload(
        _scene(),
        aspect_ratio="16:9",
        resolution="720p",
        person_generation="auto",
        references=(reference,),
        include_audio_cues=True,
    )

    instance = payload["instances"][0]
    assert instance["referenceImages"][0]["referenceType"] == "asset"
    assert "Dialogue:" in instance["prompt"]
    assert "Ambient audio and sound effects:" in instance["prompt"]
    assert payload["parameters"]["personGeneration"] == "allow_adult"
    assert summary["reference_images"] == [str(reference)]

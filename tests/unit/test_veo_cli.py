from pathlib import Path

import click
import pytest

from notebooklm.veo_cli import (
    _build_payload,
    _compose_prompt,
    _extract_video_uri,
    _validate_controls,
)


def test_compose_prompt_adds_explicit_shot_controls() -> None:
    result = _compose_prompt(
        "A presenter explains the finding.",
        composition="medium close-up",
        camera="eye-level slow dolly-in",
        lens="50mm shallow focus",
        ambiance="soft frontal fill",
    )

    assert "Composition: medium close-up" in result
    assert "Camera positioning and motion: eye-level slow dolly-in" in result
    assert "Focus and lens effects: 50mm shallow focus" in result
    assert "Lighting and ambiance: soft frontal fill" in result


def test_validate_rejects_non_eight_second_reference_generation() -> None:
    with pytest.raises(click.ClickException, match="require --duration 8"):
        _validate_controls(
            duration=6,
            resolution="720p",
            references=(Path("face.png"),),
            first_frame=None,
            last_frame=None,
            person_generation="allow_adult",
        )


def test_validate_rejects_allow_all_for_image_guided_generation() -> None:
    with pytest.raises(click.ClickException, match="adult people only"):
        _validate_controls(
            duration=8,
            resolution="720p",
            references=(),
            first_frame=Path("start.png"),
            last_frame=None,
            person_generation="allow_all",
        )


def test_build_text_payload_exposes_supported_parameters() -> None:
    payload = _build_payload(
        "A cinematic presenter shot.",
        aspect_ratio="16:9",
        duration=8,
        resolution="1080p",
        person_generation="allow_all",
        negative_prompt="rear-only view",
        seed=42,
        enhance_prompt=True,
        references=(),
        first_frame=None,
        last_frame=None,
    )

    assert payload["instances"] == [{"prompt": "A cinematic presenter shot."}]
    assert payload["parameters"] == {
        "aspectRatio": "16:9",
        "durationSeconds": 8,
        "resolution": "1080p",
        "enhancePrompt": True,
        "numberOfVideos": 1,
        "personGeneration": "allow_all",
        "negativePrompt": "rear-only view",
        "seed": 42,
    }


def test_extract_video_uri_supports_rest_operation_shape() -> None:
    operation = {
        "done": True,
        "response": {
            "generateVideoResponse": {
                "generatedSamples": [
                    {"video": {"uri": "https://example.test/generated.mp4"}}
                ]
            }
        },
    }

    assert _extract_video_uri(operation) == "https://example.test/generated.mp4"


def test_extract_video_uri_surfaces_api_error() -> None:
    with pytest.raises(click.ClickException, match="blocked by policy"):
        _extract_video_uri(
            {"done": True, "error": {"message": "blocked by policy"}}
        )

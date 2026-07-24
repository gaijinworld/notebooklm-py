from pathlib import Path

import pytest

from notebooklm._cinematic_reference import (
    ReferenceSceneError,
    build_scene_payload,
    build_scene_prompt,
    build_subject_reference_map,
    normalize_reference_storyboard,
    parse_subject_reference,
    scene_reference_paths,
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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"visual_prompt": "B-roll"}, "text"),
        ({"visual_prompt": "Presenter", "subject_ids": ["presenter"]}, "reference"),
        ({"visual_prompt": "Frames", "first_frame": "a.png"}, "interpolation"),
        ({"visual_prompt": "Continue", "extend_from_scene": "scene-001"}, "extension"),
    ],
)
def test_normalize_storyboard_infers_generation_mode(
    raw: dict[str, object], expected: str
) -> None:
    result = normalize_reference_storyboard({"scenes": [raw]})
    assert result["scenes"][0]["generation_mode"] == expected


@pytest.mark.parametrize(
    "payload, message",
    [
        ({}, "at least one scene"),
        ({"scenes": "bad"}, "at least one scene"),
        ({"subjects": {}, "scenes": [{"visual_prompt": "x"}]}, "subjects"),
        ({"scenes": ["bad"]}, "must be a JSON object"),
        ({"scenes": [{}]}, "requires visual_prompt"),
        ({"scenes": [{"visual_prompt": "x", "duration_seconds": "bad"}]}, "invalid duration"),
        ({"scenes": [{"visual_prompt": "x", "duration_seconds": 5}]}, "must be 4, 6, or 8"),
        ({"scenes": [{"visual_prompt": "x", "generation_mode": "bad"}]}, "must be one of"),
        ({"scenes": [{"visual_prompt": "x", "subject_ids": "bad"}]}, "array of strings"),
    ],
)
def test_normalize_storyboard_rejects_invalid_input(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ReferenceSceneError, match=message):
        normalize_reference_storyboard(payload)


def test_normalize_storyboard_rejects_too_many_scenes() -> None:
    scenes = [{"visual_prompt": "x"}, {"visual_prompt": "y"}]
    with pytest.raises(ReferenceSceneError, match="maximum is 1"):
        normalize_reference_storyboard({"scenes": scenes}, maximum_scenes=1)


def test_parse_subject_reference() -> None:
    subject_id, path = parse_subject_reference(" presenter = refs/front.png ")
    assert subject_id == "presenter"
    assert path == Path("refs/front.png")


@pytest.mark.parametrize("value", ["bad", "=path.png", "presenter="])
def test_parse_subject_reference_rejects_invalid_value(value: str) -> None:
    with pytest.raises(ReferenceSceneError, match="SUBJECT_ID=PATH"):
        parse_subject_reference(value)


def test_build_subject_reference_map_resolves_and_deduplicates(tmp_path: Path) -> None:
    storyboard = {
        "subjects": [
            {
                "id": "presenter",
                "reference_images": ["front.png", "front.png"],
            }
        ]
    }
    result = build_subject_reference_map(
        storyboard,
        ("presenter=three-quarter.png",),
        asset_root=tmp_path,
    )
    assert result["presenter"] == (
        (tmp_path / "front.png").resolve(),
        (tmp_path / "three-quarter.png").resolve(),
    )


def test_build_subject_reference_map_rejects_more_than_three(tmp_path: Path) -> None:
    storyboard = {
        "subjects": [
            {
                "id": "presenter",
                "reference_images": ["1.png", "2.png", "3.png", "4.png"],
            }
        ]
    }
    with pytest.raises(ReferenceSceneError, match="at most 3"):
        build_subject_reference_map(storyboard, (), asset_root=tmp_path)


def test_scene_reference_paths_deduplicates() -> None:
    first = Path("front.png")
    second = Path("side.png")
    result = scene_reference_paths(
        {"id": "scene-001", "subject_ids": ["a", "b"]},
        {"a": (first, second), "b": (second,)},
    )
    assert result == (first, second)


def test_scene_reference_paths_rejects_more_than_three() -> None:
    paths = tuple(Path(f"{index}.png") for index in range(4))
    with pytest.raises(ReferenceSceneError, match="maximum is 3"):
        scene_reference_paths(
            {"id": "scene-001", "subject_ids": ["presenter"]},
            {"presenter": paths},
        )


def test_build_scene_prompt_audio_cues_are_optional() -> None:
    without_audio = build_scene_prompt(_scene(), include_audio_cues=False)
    with_audio = build_scene_prompt(_scene(dialogue='Say "hello"'), include_audio_cues=True)
    assert "Dialogue:" not in without_audio
    assert "Ambient audio" not in without_audio
    assert 'Dialogue: "Say \'hello\'"' in with_audio
    assert "Ambient audio and sound effects" in with_audio
    assert "Composition: medium close-up" in with_audio


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"mode": "bad"}, "Unsupported generation mode"),
        ({"duration": 5}, "must be 4, 6, or 8"),
        ({"references": tuple(Path(f"{i}.png") for i in range(4))}, "at most three"),
        ({"last_frame": Path("last.png")}, "requires a first frame"),
        ({"mode": "text", "references": (Path("face.png"),)}, "Text mode"),
        ({"mode": "reference", "references": ()}, "requires one to three"),
        (
            {
                "mode": "reference",
                "references": (Path("face.png"),),
                "first_frame": Path("first.png"),
            },
            "cannot be combined",
        ),
        ({"mode": "interpolation"}, "requires both"),
        (
            {
                "mode": "interpolation",
                "references": (Path("face.png"),),
                "first_frame": Path("first.png"),
                "last_frame": Path("last.png"),
            },
            "cannot be combined",
        ),
        ({"mode": "extension"}, "operation video URI"),
        (
            {"mode": "extension", "references": (Path("face.png"),)},
            "cannot be combined",
        ),
    ],
)
def test_validate_scene_mode_rejects_invalid_combinations(
    kwargs: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "mode": "text",
        "duration": 8,
        "resolution": "720p",
        "references": (),
        "first_frame": None,
        "last_frame": None,
        "extension_video_uri": None,
    }
    values.update(kwargs)
    with pytest.raises(ReferenceSceneError, match=message):
        validate_scene_mode(**values)  # type: ignore[arg-type]


def test_validate_scene_modes_normalize_documented_controls() -> None:
    assert validate_scene_mode(
        mode="text",
        duration=4,
        resolution="1080p",
        references=(),
        first_frame=None,
        last_frame=None,
        extension_video_uri=None,
    ) == (8, "1080p", "allow_all")
    assert validate_scene_mode(
        mode="reference",
        duration=4,
        resolution="1080p",
        references=(Path("face.png"),),
        first_frame=None,
        last_frame=None,
        extension_video_uri=None,
    ) == (8, "1080p", "allow_adult")
    assert validate_scene_mode(
        mode="interpolation",
        duration=4,
        resolution="720p",
        references=(),
        first_frame=Path("first.png"),
        last_frame=Path("last.png"),
        extension_video_uri=None,
    ) == (8, "720p", "allow_adult")
    assert validate_scene_mode(
        mode="extension",
        duration=4,
        resolution="4k",
        references=(),
        first_frame=None,
        last_frame=None,
        extension_video_uri="https://example.test/video.mp4",
    ) == (8, "720p", "allow_all")


def test_build_reference_payload_and_optional_audio_cues(tmp_path: Path) -> None:
    reference = tmp_path / "face.png"
    reference.write_bytes(b"image")

    payload, summary = build_scene_payload(
        _scene(),
        aspect_ratio="16:9",
        resolution="720p",
        references=(reference,),
        include_audio_cues=True,
        seed=42,
    )

    instance = payload["instances"][0]
    assert instance["referenceImages"][0]["referenceType"] == "asset"
    assert "Dialogue:" in instance["prompt"]
    assert payload["parameters"]["personGeneration"] == "allow_adult"
    assert payload["parameters"]["seed"] == 42
    assert summary["reference_images"] == [str(reference)]


def test_build_interpolation_payload(tmp_path: Path) -> None:
    first = tmp_path / "first.jpg"
    last = tmp_path / "last.webp"
    first.write_bytes(b"first")
    last.write_bytes(b"last")
    payload, summary = build_scene_payload(
        _scene(generation_mode="interpolation", subject_ids=[]),
        aspect_ratio="9:16",
        resolution="720p",
        first_frame=first,
        last_frame=last,
    )
    assert payload["instances"][0]["image"]["inlineData"]["mimeType"] == "image/jpeg"
    assert payload["instances"][0]["lastFrame"]["inlineData"]["mimeType"] == "image/webp"
    assert summary["person_generation"] == "allow_adult"


def test_build_extension_payload_uses_transient_uri_without_seed() -> None:
    payload, summary = build_scene_payload(
        _scene(generation_mode="extension", subject_ids=[], extend_from_scene="scene-000"),
        aspect_ratio="16:9",
        resolution="4k",
        extension_video_uri="https://example.test/transient.mp4",
        seed=42,
    )
    assert payload["instances"][0]["video"] == {
        "uri": "https://example.test/transient.mp4"
    }
    assert "seed" not in payload["parameters"]
    assert payload["parameters"]["resolution"] == "720p"
    assert summary["extends_previous_veo_video"] is True


@pytest.mark.parametrize("name", ["missing.png", "bad.gif"])
def test_build_reference_payload_rejects_bad_image(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    if name == "bad.gif":
        path.write_bytes(b"gif")
    with pytest.raises(ReferenceSceneError, match="Image file not found|Unsupported image"):
        build_scene_payload(
            _scene(),
            aspect_ratio="16:9",
            resolution="720p",
            references=(path,),
        )

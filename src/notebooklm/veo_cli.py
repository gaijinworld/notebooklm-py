"""Experimental direct Veo renderer with explicit supported controls.

This module deliberately does not modify NotebookLM's undocumented cinematic
artifact payload. NotebookLM does not expose Veo generation controls there.
Instead, this CLI calls the official Gemini API Veo endpoint directly so users
can render source-grounded prompts or storyboards produced by NotebookLM.

Run with::

    python -m notebooklm.veo_cli "A documentary shot ..." --dry-run

Google's server-side safety filters and policy enforcement always remain active.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import click
import httpx

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_DEFAULT_MODEL = "veo-3.1-generate-preview"
_SUPPORTED_MODELS = (
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
)


def _read_prompt(prompt: str | None, prompt_file: Path | None) -> str:
    if prompt and prompt_file:
        raise click.ClickException("Pass either PROMPT or --prompt-file, not both.")
    if prompt_file is not None:
        prompt = prompt_file.read_text(encoding="utf-8")
    resolved = (prompt or "").strip()
    if not resolved:
        raise click.ClickException("A non-empty PROMPT or --prompt-file is required.")
    return resolved


def _inline_image(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise click.ClickException(f"Image file not found: {path}")
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise click.ClickException(f"Unsupported image type for {path}. Use PNG, JPEG, or WebP.")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime_type, "data": encoded}}


def _compose_prompt(
    base: str,
    *,
    composition: str | None,
    camera: str | None,
    lens: str | None,
    ambiance: str | None,
) -> str:
    """Add shot controls to the natural-language prompt.

    Veo exposes composition and camera direction through prompting rather than
    dedicated REST fields, so these values are kept explicit and auditable.
    """
    additions: list[str] = []
    if composition:
        additions.append(f"Composition: {composition.strip()}")
    if camera:
        additions.append(f"Camera positioning and motion: {camera.strip()}")
    if lens:
        additions.append(f"Focus and lens effects: {lens.strip()}")
    if ambiance:
        additions.append(f"Lighting and ambiance: {ambiance.strip()}")
    if not additions:
        return base
    return f"{base.rstrip()}\n\n" + "\n".join(additions)


def _validate_controls(
    *,
    duration: int,
    resolution: str,
    references: tuple[Path, ...],
    first_frame: Path | None,
    last_frame: Path | None,
    person_generation: str,
) -> None:
    if duration not in {4, 6, 8}:
        raise click.ClickException("--duration must be 4, 6, or 8 seconds.")
    if len(references) > 3:
        raise click.ClickException("Veo 3.1 supports at most three reference images.")
    if references and (first_frame or last_frame):
        raise click.ClickException(
            "--reference-image cannot be combined with --first-frame/--last-frame."
        )
    if last_frame and not first_frame:
        raise click.ClickException("--last-frame requires --first-frame.")
    if (references or resolution in {"1080p", "4k"}) and duration != 8:
        raise click.ClickException("Reference images and 1080p/4k generation require --duration 8.")
    image_guided = bool(references or first_frame or last_frame)
    if image_guided and person_generation == "allow_all":
        raise click.ClickException(
            "Image-guided Veo 3.1 generation supports adult people only; "
            "use --person-generation allow_adult or auto."
        )


def _build_payload(
    prompt: str,
    *,
    aspect_ratio: str,
    duration: int,
    resolution: str,
    person_generation: str,
    negative_prompt: str | None,
    seed: int | None,
    enhance_prompt: bool,
    references: tuple[Path, ...],
    first_frame: Path | None,
    last_frame: Path | None,
) -> dict[str, Any]:
    instance: dict[str, Any] = {"prompt": prompt}
    if references:
        instance["referenceImages"] = [
            {"image": _inline_image(path), "referenceType": "asset"} for path in references
        ]
    if first_frame:
        instance["image"] = _inline_image(first_frame)
    if last_frame:
        instance["lastFrame"] = _inline_image(last_frame)

    parameters: dict[str, Any] = {
        "aspectRatio": aspect_ratio,
        "durationSeconds": duration,
        "resolution": resolution,
        "enhancePrompt": enhance_prompt,
        "numberOfVideos": 1,
    }
    if person_generation != "auto":
        parameters["personGeneration"] = person_generation
    if negative_prompt:
        parameters["negativePrompt"] = negative_prompt.strip()
    if seed is not None:
        parameters["seed"] = seed

    return {"instances": [instance], "parameters": parameters}


def _extract_video_uri(operation: dict[str, Any]) -> str:
    if operation.get("error"):
        error = operation["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise click.ClickException(f"Veo generation failed: {message}")

    response = operation.get("response") or {}
    generate_response = response.get("generateVideoResponse") or {}
    samples = generate_response.get("generatedSamples") or []
    if samples:
        uri = ((samples[0] or {}).get("video") or {}).get("uri")
        if uri:
            return str(uri)

    # Compatibility with newer SDK-shaped operation responses.
    generated = response.get("generatedVideos") or []
    if generated:
        uri = ((generated[0] or {}).get("video") or {}).get("uri")
        if uri:
            return str(uri)

    raise click.ClickException(
        "Veo completed without a downloadable video URI. "
        "Inspect the operation JSON with --save-operation."
    )


def _request_json(response: httpx.Response, *, action: str) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text[:1000]
        raise click.ClickException(
            f"Gemini API {action} failed with HTTP {response.status_code}: {detail}"
        ) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise click.ClickException(f"Gemini API {action} returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise click.ClickException(f"Gemini API {action} returned an unexpected response.")
    return payload


def _generate(
    *,
    api_key: str,
    model: str,
    payload: dict[str, Any],
    output: Path,
    timeout: float,
    poll_interval: float,
    save_operation: Path | None,
) -> None:
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    endpoint = f"{_BASE_URL}/models/{model}:predictLongRunning"
    deadline = time.monotonic() + timeout

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        kickoff = _request_json(
            client.post(endpoint, headers=headers, json=payload), action="request"
        )
        operation_name = kickoff.get("name")
        if not operation_name:
            raise click.ClickException("Gemini API did not return a long-running operation name.")

        click.echo(f"Started Veo operation: {operation_name}")
        operation: dict[str, Any] = kickoff
        while not operation.get("done"):
            if time.monotonic() >= deadline:
                raise click.ClickException(
                    f"Timed out after {timeout:g}s while waiting for Veo. "
                    f"Operation: {operation_name}"
                )
            time.sleep(poll_interval)
            operation = _request_json(
                client.get(f"{_BASE_URL}/{operation_name}", headers=headers),
                action="poll",
            )
            click.echo("Veo is still generating...", err=True)

        if save_operation is not None:
            save_operation.parent.mkdir(parents=True, exist_ok=True)
            save_operation.write_text(
                json.dumps(operation, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        video_uri = _extract_video_uri(operation)
        download = client.get(video_uri, headers={"x-goog-api-key": api_key})
        try:
            download.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise click.ClickException(
                f"Video download failed with HTTP {download.status_code}."
            ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(download.content)
    click.echo(f"Saved video: {output}")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("prompt", required=False)
@click.option(
    "--prompt-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Read the complete Veo prompt from a UTF-8 text file.",
)
@click.option(
    "--model", type=click.Choice(_SUPPORTED_MODELS), default=_DEFAULT_MODEL, show_default=True
)
@click.option(
    "--aspect-ratio", type=click.Choice(["16:9", "9:16"]), default="16:9", show_default=True
)
@click.option(
    "--duration", type=int, default=8, show_default=True, help="Clip duration: 4, 6, or 8 seconds."
)
@click.option(
    "--resolution", type=click.Choice(["720p", "1080p", "4k"]), default="720p", show_default=True
)
@click.option(
    "--person-generation",
    type=click.Choice(["auto", "allow_all", "allow_adult"]),
    default="auto",
    show_default=True,
    help="Official Veo people-generation setting; regional restrictions still apply.",
)
@click.option("--composition", help="Shot framing, such as close-up, two-shot, or wide shot.")
@click.option("--camera", help="Camera position and motion, such as eye-level slow dolly-in.")
@click.option("--lens", help="Focus or lens direction, such as shallow focus or 50mm lens.")
@click.option("--ambiance", help="Lighting and color direction.")
@click.option("--negative-prompt", help="Elements Veo should avoid, subject to API support.")
@click.option(
    "--seed", type=int, help="Optional Veo seed; improves similarity but is not deterministic."
)
@click.option("--enhance-prompt/--no-enhance-prompt", default=True, show_default=True)
@click.option(
    "--reference-image",
    "references",
    multiple=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Asset reference image; repeat up to three times.",
)
@click.option(
    "--first-frame",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Image used as the first frame.",
)
@click.option(
    "--last-frame",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Image used as the last frame; requires --first-frame.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("veo-output.mp4"),
    show_default=True,
)
@click.option("--timeout", type=click.FloatRange(min=1.0), default=900.0, show_default=True)
@click.option("--poll-interval", type=click.FloatRange(min=1.0), default=10.0, show_default=True)
@click.option(
    "--save-operation",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Save the final operation JSON for debugging.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the exact Gemini API request without calling Veo.",
)
def main(
    prompt: str | None,
    prompt_file: Path | None,
    model: str,
    aspect_ratio: str,
    duration: int,
    resolution: str,
    person_generation: str,
    composition: str | None,
    camera: str | None,
    lens: str | None,
    ambiance: str | None,
    negative_prompt: str | None,
    seed: int | None,
    enhance_prompt: bool,
    references: tuple[Path, ...],
    first_frame: Path | None,
    last_frame: Path | None,
    output: Path,
    timeout: float,
    poll_interval: float,
    save_operation: Path | None,
    dry_run: bool,
) -> None:
    """Render a controlled Veo clip from a NotebookLM-authored PROMPT.

    This command exposes official Gemini API controls. It does not disable or
    weaken Google's server-side safety, privacy, copyright, or policy filters.
    """
    resolved_prompt = _read_prompt(prompt, prompt_file)
    resolved_prompt = _compose_prompt(
        resolved_prompt,
        composition=composition,
        camera=camera,
        lens=lens,
        ambiance=ambiance,
    )
    _validate_controls(
        duration=duration,
        resolution=resolution,
        references=references,
        first_frame=first_frame,
        last_frame=last_frame,
        person_generation=person_generation,
    )
    payload = _build_payload(
        resolved_prompt,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        person_generation=person_generation,
        negative_prompt=negative_prompt,
        seed=seed,
        enhance_prompt=enhance_prompt,
        references=references,
        first_frame=first_frame,
        last_frame=last_frame,
    )

    if dry_run:
        # Avoid dumping large base64 image bodies into the terminal.
        redacted = json.loads(json.dumps(payload))
        instance = redacted["instances"][0]
        for key in ("image", "lastFrame"):
            if key in instance:
                instance[key]["inlineData"]["data"] = "<base64 omitted>"
        for reference in instance.get("referenceImages", []):
            reference["image"]["inlineData"]["data"] = "<base64 omitted>"
        click.echo(json.dumps(redacted, indent=2, ensure_ascii=False))
        return

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise click.ClickException(
            "GEMINI_API_KEY is required. Set it in the environment before rendering."
        )
    _generate(
        api_key=api_key,
        model=model,
        payload=payload,
        output=output,
        timeout=timeout,
        poll_interval=poll_interval,
        save_operation=save_operation,
    )


if __name__ == "__main__":
    main()

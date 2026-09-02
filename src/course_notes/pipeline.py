from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from course_notes.download import download_video
from course_notes.media import capture_screenshots, extract_audio, probe_media
from course_notes.transcribe import transcribe_audio, write_transcript


@dataclass(frozen=True, slots=True)
class PrepareOptions:
    language: str = "auto"
    device: Literal["auto", "cuda", "cpu"] = "auto"
    screenshot_interval: int = 30


_DEFAULT_PREPARE_OPTIONS = PrepareOptions()


def prepare(
    url: str,
    output: Path,
    options: PrepareOptions = _DEFAULT_PREPARE_OPTIONS,
) -> dict[str, object]:
    output = output.expanduser().resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise ValueError(f"output must be a missing or empty directory: {output}")
    else:
        output.mkdir(parents=True)

    video = download_video(url, output)
    media = probe_media(video)
    audio = extract_audio(video, output / "audio.wav")
    transcript = transcribe_audio(audio, language=options.language, device=options.device)
    transcript_json, transcript_markdown = write_transcript(transcript, output)
    screenshots_json, images = capture_screenshots(
        video, media.duration_ms, output, options.screenshot_interval
    )

    return {
        "output": str(output),
        "video": str(video.resolve()),
        "audio": str(audio.resolve()),
        "transcript_json": str(transcript_json.resolve()),
        "transcript_markdown": str(transcript_markdown.resolve()),
        "screenshots_json": str(screenshots_json.resolve()),
        "screenshots": [str(image.resolve()) for image in images],
        "language": transcript.language,
        "transcript_segment_count": len(transcript.segments),
        "screenshot_count": len(images),
    }

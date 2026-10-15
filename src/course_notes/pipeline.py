from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
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

    with (output / "prepare.log").open("w", encoding="utf-8") as log_file:

        def log_event(message: str) -> None:
            clean = " ".join(message.splitlines()).strip()
            clean = re.sub(r"https?://\S+", "[URL]", clean)
            log_file.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {clean}\n")
            log_file.flush()

        log_event("prepare started")
        phase = "download"
        try:
            log_event("download started")
            video = download_video(url, output, log=log_event)
            log_event("download completed")
            phase = "probe"
            log_event("probe started")
            media = probe_media(video)
            log_event("probe completed")
            phase = "audio"
            log_event("audio started")
            audio = extract_audio(video, output / "audio.wav")
            log_event("audio completed")
            phase = "asr"
            log_event("asr started")
            transcript = transcribe_audio(audio, language=options.language, device=options.device)
            log_event("asr completed")
            phase = "transcript"
            log_event("transcript started")
            transcript_json, transcript_markdown = write_transcript(transcript, output)
            log_event("transcript completed")
            phase = "screenshots"
            log_event("screenshots started")
            screenshots_json, images = capture_screenshots(
                video, media.duration_ms, output, options.screenshot_interval
            )
            log_event("screenshots completed")
        except Exception as error:
            log_event(f"{phase} failed: {type(error).__name__}: {error}")
            raise

        log_event("prepare completed")
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

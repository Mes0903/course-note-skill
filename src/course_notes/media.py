from __future__ import annotations

import json
import math
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass(frozen=True, slots=True)
class MediaInfo:
    duration_ms: int


def probe_media(video: Path, *, run=subprocess.run) -> MediaInfo:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-of",
            "json",
            "-show_entries",
            "stream=codec_type:format=duration",
            str(video),
        ],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    streams = payload["streams"]
    if not isinstance(streams, list) or not any(
        isinstance(stream, dict) and stream.get("codec_type") == "video" for stream in streams
    ):
        raise ValueError("media has no video stream")
    if not any(
        isinstance(stream, dict) and stream.get("codec_type") == "audio" for stream in streams
    ):
        raise ValueError("media has no audio stream")

    duration = payload["format"]["duration"]
    if isinstance(duration, bool):
        raise ValueError("media duration must be finite and positive")
    seconds = float(duration)
    duration_ms = round(seconds * 1_000)
    if not math.isfinite(seconds) or duration_ms <= 0:
        raise ValueError("media duration must be finite and positive")
    return MediaInfo(duration_ms)


def extract_audio(video: Path, target: Path, *, run=subprocess.run) -> Path:
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        with wave.open(str(target), "rb") as audio:
            profile = (
                audio.getcomptype(),
                audio.getnchannels(),
                audio.getframerate(),
                audio.getsampwidth(),
            )
    except (EOFError, wave.Error) as error:
        raise ValueError("ffmpeg did not produce a valid WAV file") from error
    if profile != ("NONE", 1, 16_000, 2):
        raise ValueError("ffmpeg did not produce the required WAV profile")
    return target


def extract_jpeg(video: Path, time_ms: int, target: Path, *, run=subprocess.run) -> Path:
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{time_ms / 1000:.3f}",
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(target),
        ],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    if not target.is_file() or target.stat().st_size == 0 or cv2.imread(str(target)) is None:
        raise ValueError("ffmpeg did not produce a readable JPEG")
    return target


def screenshot_times(duration_ms: int, interval_seconds: int = 30) -> tuple[int, ...]:
    if duration_ms <= 0 or interval_seconds <= 0:
        raise ValueError("duration and interval must be positive")
    first = min(500, duration_ms - 1)
    interval_ms = interval_seconds * 1_000
    return tuple(sorted({first, *range(interval_ms, duration_ms, interval_ms)}))


def capture_screenshots(
    video: Path, duration_ms: int, output: Path, interval_seconds: int = 30
) -> tuple[Path, tuple[Path, ...]]:
    screenshots = output / "screenshots"
    screenshots.mkdir()
    records: list[dict[str, int | str]] = []
    images: list[Path] = []
    for index, time_ms in enumerate(screenshot_times(duration_ms, interval_seconds), start=1):
        name = f"{index:04d}-{time_ms:09d}.jpg"
        image = extract_jpeg(video, time_ms, screenshots / name)
        images.append(image)
        records.append({"path": f"screenshots/{name}", "time_ms": time_ms})
    index = output / "screenshots.json"
    index.write_text(json.dumps(records), encoding="utf-8")
    return index, tuple(images)

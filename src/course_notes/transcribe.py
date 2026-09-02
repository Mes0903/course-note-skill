from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from faster_whisper import WhisperModel


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptResult:
    language: str
    language_probability: float
    segments: tuple[TranscriptSegment, ...]


def transcribe_audio(
    audio: Path,
    *,
    language: str = "auto",
    device: Literal["auto", "cuda", "cpu"] = "auto",
    model_cache: Path = Path(".cache/course-notes/models"),
) -> TranscriptResult:
    compute_type = {"cpu": "int8", "cuda": "float16"}.get(device, "default")
    model_cache.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        "Systran/faster-whisper-large-v3",
        device=device,
        compute_type=compute_type,
        download_root=str(model_cache),
    )
    generated, info = model.transcribe(
        str(audio),
        language=None if language == "auto" else language,
        beam_size=5,
        vad_filter=False,
        word_timestamps=False,
        condition_on_previous_text=False,
    )
    segments: list[TranscriptSegment] = []
    for segment in generated:
        raw_text = segment.text
        if raw_text.strip():
            segments.append(
                TranscriptSegment(
                    start_ms=int(segment.start * 1_000),
                    end_ms=int(segment.end * 1_000),
                    text=raw_text,
                )
            )
    return TranscriptResult(
        language=info.language,
        language_probability=info.language_probability,
        segments=tuple(segments),
    )


def write_transcript(result: TranscriptResult, output: Path) -> tuple[Path, Path]:
    json_path = output / "transcript.raw.json"
    markdown_path = output / "transcript.raw.md"
    json_path.write_text(
        json.dumps(
            {
                "language": result.language,
                "language_probability": result.language_probability,
                "segments": [
                    {
                        "start_ms": segment.start_ms,
                        "end_ms": segment.end_ms,
                        "text": segment.text,
                    }
                    for segment in result.segments
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines: list[str] = []
    for segment in result.segments:
        start_hours, start_remainder = divmod(segment.start_ms, 3_600_000)
        start_minutes, start_remainder = divmod(start_remainder, 60_000)
        start_seconds, start_milliseconds = divmod(start_remainder, 1_000)
        end_hours, end_remainder = divmod(segment.end_ms, 3_600_000)
        end_minutes, end_remainder = divmod(end_remainder, 60_000)
        end_seconds, end_milliseconds = divmod(end_remainder, 1_000)
        lines.append(
            f"[{start_hours:02}:{start_minutes:02}:{start_seconds:02}.{start_milliseconds:03} "
            f"\N{EN DASH} {end_hours:02}:{end_minutes:02}:{end_seconds:02}.{end_milliseconds:03}] "
            f"{segment.text}"
        )
    markdown_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return json_path, markdown_path

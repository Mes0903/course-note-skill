from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from course_notes.media import extract_jpeg

_FULLWIDTH_COLON = "\N{FULLWIDTH COLON}"
_EN_DASH = "\N{EN DASH}"


@dataclass(frozen=True, slots=True)
class ArticleSegment:
    segment_id: str
    start_ms: int
    end_ms: int
    frame_ms: int | None
    frame_path: str
    source_text: str
    translation_text: str


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _list_field(value: dict[str, Any], field: str, label: str) -> list[Any]:
    result = value.get(field)
    if not isinstance(result, list):
        raise ValueError(f"{label}.{field} must be a list")
    return result


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _integer(value: dict[str, Any], field: str, label: str) -> int:
    result = value.get(field)
    if type(result) is not int:
        raise ValueError(f"{label}.{field} must be an integer")
    return result


def _text(value: dict[str, Any], field: str, label: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{label}.{field} must be nonblank text")
    return result


def _article_text(value: dict[str, Any], field: str, label: str) -> str:
    result = _text(value, field, label)
    if "![" in result or "<!--" in result:
        raise ValueError(f"{label}.{field} may not add article structure")
    if "\n" in result or "\r" in result:
        raise ValueError(
            f"{label}.{field} must be one physical-line prose paragraph"
        )
    if re.match(
        r"(?:#{1,6}(?:[ \t]|$)|>|[-*+](?:[ \t]|$)|\d+[.)](?:[ \t]|$)|"
        r"```|~~~|</?[A-Za-z][^>]*>|(?:[*_-][ \t]*){3,}$)",
        result.lstrip(),
    ):
        raise ValueError(f"{label}.{field} may not add Markdown block structure")
    return result.strip()


def _timestamp(time_ms: int) -> str:
    hours, remainder = divmod(time_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


def _render(segments: list[ArticleSegment], field: str) -> str:
    blocks = []
    for segment in segments:
        parts = [f"<!-- segment:{segment.segment_id} -->"]
        if segment.frame_ms is not None:
            parts.append(f"![畫面]({segment.frame_path})")
        parts.extend(
            [
                f"時間{_FULLWIDTH_COLON}{_timestamp(segment.start_ms)}"
                f"{_EN_DASH}{_timestamp(segment.end_ms)}",
                getattr(segment, field),
            ]
        )
        blocks.append("\n\n".join(parts))
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _validate_raw(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    raw_values = _list_field(transcript, "segments", "transcript")
    if not raw_values:
        raise ValueError("transcript.segments must not be empty")
    raw_segments = []
    for index, value in enumerate(raw_values):
        label = f"transcript.segments[{index}]"
        raw = _object(value, label)
        start_ms = _integer(raw, "start_ms", label)
        end_ms = _integer(raw, "end_ms", label)
        if start_ms < 0 or end_ms <= start_ms:
            raise ValueError(f"{label} must have a positive time range")
        _text(raw, "text", label)
        raw_segments.append(raw)
    return raw_segments


def _video(output: Path) -> Path:
    videos = [
        path
        for path in output.glob("video.*")
        if path.is_file() and path.stat().st_size > 0 and not path.name.endswith(".part")
    ]
    if len(videos) != 1:
        raise ValueError(f"output must contain exactly one complete video.* file: {output}")
    return videos[0]


def _validated_segments(
    raw_segments: list[dict[str, Any]],
    article_decision: dict[str, Any],
    translation_decision: dict[str, Any],
) -> list[ArticleSegment]:
    if type(article_decision.get("schema_version")) is not int or (
        article_decision["schema_version"] != 1
    ):
        raise ValueError("article.schema_version must be 1")
    if type(translation_decision.get("schema_version")) is not int or (
        translation_decision["schema_version"] != 1
    ):
        raise ValueError("translation.schema_version must be 1")
    decisions = _list_field(article_decision, "segments", "article")
    translation_items = _list_field(translation_decision, "items", "translation")
    if not decisions:
        raise ValueError("article.segments must not be empty")

    partial: list[dict[str, Any]] = []
    visual_count = 0
    cursor = 0
    for index, value in enumerate(decisions, start=1):
        label = f"article.segments[{index - 1}]"
        decision = _object(value, label)
        transcript_start = _integer(decision, "transcript_start", label)
        transcript_end = _integer(decision, "transcript_end", label)
        if transcript_start != cursor:
            raise ValueError(f"{label} must start at raw transcript index {cursor}")
        if transcript_end <= transcript_start or transcript_end > len(raw_segments):
            raise ValueError(f"{label} has an invalid transcript range")
        start_ms = _integer(raw_segments[transcript_start], "start_ms", "raw segment")
        end_ms = _integer(raw_segments[transcript_end - 1], "end_ms", "raw segment")
        if "frame_ms" not in decision:
            raise ValueError(f"{label}.frame_ms is required")
        frame_ms = decision["frame_ms"]
        if frame_ms is None:
            if not partial:
                raise ValueError("article.segments[0].frame_ms must start a visual group")
            frame_path = partial[-1]["frame_path"]
        else:
            if type(frame_ms) is not int:
                raise ValueError(f"{label}.frame_ms must be an integer or null")
            if not start_ms <= frame_ms < end_ms:
                raise ValueError(f"{label}.frame_ms must lie inside the article time range")
            visual_count += 1
            frame_path = f"frames/{visual_count:04d}.jpg"
        partial.append(
            {
                "segment_id": f"segment-{index:04d}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "frame_ms": frame_ms,
                "frame_path": frame_path,
                "source_text": _article_text(decision, "source_text", label),
            }
        )
        cursor = transcript_end
    if cursor != len(raw_segments):
        raise ValueError("article ranges must cover the complete raw transcript")

    expected_ids = [segment["segment_id"] for segment in partial]
    actual_ids = []
    translations = []
    for index, value in enumerate(translation_items):
        label = f"translation.items[{index}]"
        item = _object(value, label)
        segment_id = item.get("segment_id")
        if not isinstance(segment_id, str):
            raise ValueError(f"{label}.segment_id must be text")
        actual_ids.append(segment_id)
        translations.append(_article_text(item, "text", label))
    if actual_ids != expected_ids:
        raise ValueError("translation segment IDs must exactly match article order")

    return [
        ArticleSegment(**segment, translation_text=translation)
        for segment, translation in zip(partial, translations, strict=True)
    ]


def compose_articles(
    output: Path, article_path: Path, translation_path: Path
) -> dict[str, object]:
    output = output.expanduser().resolve()
    if not output.is_dir():
        raise ValueError(f"output must be a prepared directory: {output}")
    source = output / "source.md"
    translation = output / "zh-TW.md"
    frames_dir = output / "frames"
    if source.exists() or translation.exists() or frames_dir.exists():
        raise ValueError("final article output already exists")

    article_decision = _load_json(article_path.expanduser().resolve())
    translation_decision = _load_json(translation_path.expanduser().resolve())
    transcript = _load_json(output / "transcript.raw.json")
    video = _video(output)
    raw_segments = _validate_raw(transcript)
    segments = _validated_segments(raw_segments, article_decision, translation_decision)

    frames_dir.mkdir()
    frames: list[Path] = []
    for segment in segments:
        if segment.frame_ms is not None:
            target = output / segment.frame_path
            frames.append(extract_jpeg(video, segment.frame_ms, target))

    source.write_text(_render(segments, "source_text"), encoding="utf-8")
    translation.write_text(_render(segments, "translation_text"), encoding="utf-8")
    return {
        "output": str(output),
        "source": str(source.resolve()),
        "translation": str(translation.resolve()),
        "frames": [str(frame.resolve()) for frame in frames],
        "segment_count": len(segments),
    }

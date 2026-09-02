---
name: course-notes
description: Use when a user supplies a video or lecture URL, or asks for complete source-language and Taiwanese Traditional Chinese transcript articles with corresponding video frames.
---

# Course Notes

Turn one video URL into two complete, aligned transcript articles:

- `source.md` keeps the spoken content in its source language, with readable punctuation and paragraphs.
- `zh-TW.md` faithfully renders the same content in natural Taiwanese Traditional Chinese.
- Every prose paragraph is one article segment. An integer `frame_ms` starts a meaningful visual group; `null` continues the preceding group. Both files share segment IDs, time ranges, visual boundaries, image paths, and order.

This is a transcript, not lecture notes. Preserve introductions, asides, repetition, uncertainty, and other spoken content. Do not summarize or remove material merely because it is off topic.

## Prepare

Starting at this `SKILL.md`, walk upward until one directory contains both `pyproject.toml` and an executable `scripts/course-notes`. Treat it as `REPO`. Stop clearly if either marker is absent.

Choose a fresh absolute output directory. Run the wrapper by absolute path:

```bash
"$REPO/scripts/course-notes" prepare "$URL" --output "$OUTPUT" \
  --language "$LANGUAGE" --device "$DEVICE" \
  --screenshot-interval "$INTERVAL"
```

Use `auto`, `auto`, and `30` for language, device, and interval unless the user requests other supported values.

Only when the wrapper prints exactly `course-notes: run scripts/install.sh first`, run `"$REPO/scripts/install.sh" --device "$DEVICE"` once, then retry the identical prepare command once. Do not install for another failure or retry installation again.

## Author the aligned decisions

Read the complete `transcript.raw.json`, `transcript.raw.md`, and `screenshots.json`. Inspect every JPEG listed in the screenshot index, and inspect the video directly when the fixed candidates do not show enough context. Preserve all preparation artifacts.

Treat raw ASR as evidence, not ground truth. Spot-check the beginning, ending, and any implausible or context-breaking span against the audio; when a span is suspicious, re-transcribe only that short span with an alternate appropriate setting (for example VAD) and keep the speech supported by the evidence.

Write `$OUTPUT/article.json` with this shape:

```json
{
  "schema_version": 1,
  "segments": [
    {
      "transcript_start": 0,
      "transcript_end": 12,
      "frame_ms": 500,
      "source_text": "Readable source-language transcript text."
    }
  ]
}
```

Build article ranges under these rules:

- `transcript_start` is inclusive and `transcript_end` is exclusive. Start at raw segment `0`, use only adjacent contiguous ranges, and end at the total raw segment count.
- Group utterances into readable semantic segments without omission or reordering.
- Each `source_text` is exactly one physical-line prose paragraph. It may not contain a line break or start Markdown block structure. When the discourse needs a new paragraph, start the next adjacent segment.
- `source_text` may repair punctuation, obvious ASR boundaries, consistent terminology, and LaTeX supported by the transcript or frames; it must remain a complete source-language transcript.
- Every segment includes `frame_ms`. An integer starts a meaningful visual group and must lie inside that segment's time span. `null` continues the preceding visual group; the first segment must use an integer.
- Start a new visual group for a slide change or a meaningful bullet, formula, or diagram reveal. Do not start one for cursor or presenter movement, compression noise, or cosmetic animation.
- If an important visual change happens inside a long prose paragraph, split the transcript at the nearest reasonable semantic and raw-transcript boundary without losing, reordering, or changing its content. Give the new segment its own `frame_ms` only when that visual change merits a new group.

Invoke and follow `zhtw-translocalizer`. Resolve the directory containing its loaded `SKILL.md`, then set the shell variable `ZHTW_SKILL_ROOT` to that absolute directory before either lint gate below. Write `$OUTPUT/translation.json` with one item for every derived ID in exact order:

```json
{
  "schema_version": 1,
  "items": [
    {"segment_id": "segment-0001", "text": "忠實且自然的臺灣繁體中文逐字稿。"}
  ]
}
```

Preserve every utterance and its source order. Do not summarize, omit, reorder, strengthen, or add claims. Keep formulas as supported LaTeX. Match the article's one-paragraph segment and visual boundaries exactly. Follow the translocalizer's paragraph rhythm: split dense prose at semantic boundaries, normally before it grows beyond roughly 150 CJK characters, while retaining flexibility for meaning and formulas. Each decision text field is one physical line and may not start Markdown block structure or add Markdown images or `<!-- segment:... -->` markers; `compose` owns that structure.

Before final review, project the translation item texts in order into a temporary Markdown file outside `$OUTPUT`, separated by blank lines and without JSON syntax or article metadata. Run the translocalizer linter on that candidate and inspect every warning. Resolve every true `L020` by splitting both decisions at the same semantic boundary and assigning each resulting segment an integer or `null` according to its visual group. An `L020` may remain only when the paragraph is a deliberate semantic or formula exception that the fresh reviewer confirms.

How to divide drafting work among subagents is a local judgment. Before publication, always give the complete raw transcript, article decision, translation decision, screenshot index, and relevant frames to a fresh subagent for a final review.

Require findings tied to segment IDs for coverage, transcript fidelity, one-paragraph segment boundaries, paragraph density, meaningful visual reveals, redundant visual starts, terminology, LaTeX, punctuation, and Taiwanese Traditional Chinese. The reviewer must confirm that meaningful reveals remain visible and that redundant visuals do not start new groups. Confirm each finding against the evidence before editing. If a candidate changes materially, use another fresh reviewer; do not reuse a previous reviewer.

## Compose and verify

Only after review is clean, run:

```bash
"$REPO/scripts/course-notes" compose --output "$OUTPUT" \
  --article "$OUTPUT/article.json" \
  --translation "$OUTPUT/translation.json"
```

Verify the final artifacts:

- Both Markdown files contain the same ordered segment markers, times, image paths, and visual boundaries.
- A group-start block is marker, image, timestamp, then paragraph. A continuation block is marker, timestamp, then paragraph. The effective frame for a continuation is the most recent preceding group-start image.
- Each segment block contains exactly one prose paragraph, and no prose paragraph appears outside a segment block.
- Paragraph count equals segment count, image count equals visual-group count, and `frames/` contains exactly one decodable JPEG per visual group.
- Every image link resolves. `compose` validates and renders the explicit decisions; it never infers visual similarity.

Run the `zhtw-translocalizer` Lua linter on the final translation and inspect every warning:

```bash
lua5.4 "$ZHTW_SKILL_ROOT/scripts/lint.lua" --format markdown "$OUTPUT/zh-TW.md"
```

Use `lua` only when `lua5.4` is unavailable, as directed by that skill. The timestamp line and internal segment marker are required article structure. Classify warnings about those exact generated fields against that context rather than editing their alignment. The final output must not introduce an unresolved `L020` that was absent from the reviewed candidate; if it does, the request is not complete.

The request is complete only after returning direct links to both `source.md` and `zh-TW.md`. Also report the segment/frame count and the linter result. Diagnose unusual source handling with ordinary tools for that run.

---
name: course-notes
description: Use when a user supplies a video or lecture URL, or asks for complete source-language and Taiwanese Traditional Chinese transcript articles with corresponding video frames.
---

# Course Notes

Turn one video URL into two complete, aligned transcript articles:

- `source.md` keeps every utterance in its source language; readability means punctuation and paragraph breaks.
- `zh-TW.md` faithfully translates every utterance into Taiwanese Traditional Chinese, with only the local grammar adjustments translation needs.
- Every prose paragraph is one article segment. An integer `frame_ms` starts a meaningful visual group; `null` continues the preceding group. Both files share segment IDs, time ranges, visual boundaries, image paths, and order.

Use each raw utterance as the fidelity check unit. Preserve spoken fillers, repetitions, restarts, negation, self-corrections, hesitation, introductions, endings, asides, and examples in order. Readability is not permission to condense speech into lecture notes.

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

After `prepare` starts, inspect `$OUTPUT/prepare.log` when progress stalls or the command fails. It records the current phase and download retry/error messages. Wait for `prepare` to succeed before authoring; after a failure, diagnose the log and use a fresh empty output directory for another full run rather than assembling partial artifacts.

## Author the aligned decisions

Read the complete `transcript.raw.json`, `transcript.raw.md`, and `screenshots.json`. Inspect every JPEG listed in the screenshot index, and inspect the video directly when the fixed candidates do not show enough context. Preserve all preparation artifacts.

Treat raw ASR as evidence, not ground truth, and never modify raw artifacts. Listen directly to the beginning, ending, suspected ASR errors, and any proposed deletion. Re-transcribe only a suspicious short span when useful.

If direct listening is unavailable in the current environment, disclose that verification gap and preserve unresolved words; re-ASR is not proof that you heard the audio. Do not make deletions or audio-dependent repairs without the required evidence.

Remove an ASR hallucination only when direct listening proves the words were not spoken. VAD, low amplitude, or implausible meaning alone is insufficient. Frames may support term spelling, but cannot supply unspoken content.

Preserve the speaker's actual factual, numeric, or wording mistakes. Keep unresolved doubts conservatively and flag them in the handoff, marking genuinely inaudible words locally as `[聽不清楚]`. Record deletions and nontrivial word repairs with raw index, time, and supporting evidence in the task area, without changing the schema.

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
- Edit `source_text` only for whitespace, punctuation, paragraph breaks, faithful LaTeX typesetting, and evidence-supported local ASR repairs; preserve the source language and code-switching. Repair only the misrecognized term, retaining surrounding speech: an audio-supported repair to `Terraced House` still keeps `或這個這叫什麼……吧`.
- Every segment includes `frame_ms`. An integer starts a meaningful visual group and must lie inside that segment's time span. `null` continues the preceding visual group; the first segment must use an integer.
- Start a new visual group for a slide change or a meaningful bullet, formula, or diagram reveal. Do not start one for cursor or presenter movement, compression noise, or cosmetic animation.
- If an important visual change happens inside a long prose paragraph, split the transcript at the nearest reasonable semantic and raw-transcript boundary without losing, reordering, or changing its content. Give the new segment its own `frame_ms` only when that visual change merits a new group.

Invoke `zhtw-translocalizer` within this complete-transcript contract. This contract takes precedence over generic prose advice to omit repeated subjects, replace negation and self-correction with a conclusion, or delete asides. Still review Traditional/Simplified characters, terminology, punctuation, and `L020`; spoken style is not a blanket lint exemption.

Resolve the directory containing its loaded `SKILL.md`, then set the shell variable `ZHTW_SKILL_ROOT` to that absolute directory before either lint gate below. Write `$OUTPUT/translation.json` with one item for every derived ID in exact order:

```json
{
  "schema_version": 1,
  "items": [
    {"segment_id": "segment-0001", "text": "忠實且自然的臺灣繁體中文逐字稿。"}
  ]
}
```

Translate every occurrence of spoken content in order, retaining repetition, negation, corrections, hesitation, and tone. Do not summarize, omit, reorder, strengthen, add claims, or insert translator notes into the transcript. Keep formulas as supported LaTeX and match the article's one-paragraph segment and visual boundaries exactly.

Split dense prose at adjacent raw-utterance boundaries, normally before roughly 150 CJK characters. Reduce density by splitting, never by deleting words. Do not invent a raw boundary within an indivisible utterance or formula.

Each decision text field is one physical line and may not start Markdown block structure or add Markdown images or `<!-- segment:... -->` markers; `compose` owns that structure.

Before final review, project the translation item texts in order into a temporary Markdown file outside `$OUTPUT`, separated by blank lines and without JSON syntax or article metadata. Run the translocalizer linter on that candidate and inspect every warning.

Resolve every true `L020` by splitting both decisions at the same adjacent raw boundary and assigning each resulting segment an integer or `null` according to its visual group. An `L020` may remain only for an indivisible utterance or formula that the fresh reviewer confirms. Document the specific reason for any warning retained to preserve actual speech.

How to divide drafting work among subagents is a local judgment. Before publication, give the complete raw transcript, article decision, translation decision, screenshot index, relevant frames, and repair evidence to a fresh subagent with no history fork for each final review round.

Require a complete, sentence-by-sentence raw → source → zh comparison of every raw utterance, not sampling. Raw index coverage, word-count ratios, lint success, and valid images are structural or auxiliary checks, not proof that speech is complete. Each finding must include raw index, segment ID, a short quotation, and evidence.

Review omissions, additions, rewrites, repair evidence, one-paragraph boundaries, density, meaningful visual reveals, redundant visual starts, terminology, LaTeX, punctuation, and Taiwanese Traditional Chinese. Confirm that meaningful reveals remain visible and redundant visuals do not start new groups.

The coordinator must verify each finding before editing. After any material change, use another fresh reviewer with no history fork; do not reuse a previous reviewer.

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

Run the `zhtw-translocalizer` Python linter on the final translation and inspect every warning:

```bash
python3 "$ZHTW_SKILL_ROOT/linter/lint.py" --profile final --format markdown "$OUTPUT/zh-TW.md"
```

Use Python 3.10 or newer and the linter shipped with the loaded skill. If that entrypoint is unavailable, report the missing dependency instead of claiming lint passed. The timestamp line and internal segment marker are required article structure. Classify warnings about those exact generated fields against that context rather than editing their alignment. The final output must not introduce an unresolved `L020` that was absent from the reviewed candidate; if it does, the request is not complete.

The request is complete only after returning direct links to both `source.md` and `zh-TW.md`. Also report the segment/frame count and the linter result. Diagnose unusual source handling with ordinary tools for that run.

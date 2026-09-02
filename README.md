# Course Notes

Course Notes is a small local agent workflow that turns one video URL into aligned transcript articles. The finished output includes a readable source-language transcript and a Taiwanese Traditional Chinese version. One segment is one prose paragraph. Both versions use the same segments, times, visual boundaries, and images; several adjacent paragraphs may share one meaningful visual group.

## Requirements and install

Python 3.12, FFmpeg, and FFprobe are required. From the repository root, run:

```bash
scripts/install.sh --device auto
```

The installer creates `.venv`, installs pinned Deno for yt-dlp, and selects CPU or CUDA dependencies. Whisper models are cached under `.cache/course-notes/models` when first used.

## Use with the agent

Give the URL to the `course-notes` skill. The agent runs preparation, reads the complete raw transcript and visual evidence, writes the two article decisions, obtains a fresh content review, and publishes both Markdown files. A run is complete only when `source.md` and `zh-TW.md` exist.

## Mechanical commands

`prepare` downloads and inspects the media, runs ASR once over the complete audio, and captures fixed-interval candidate screenshots. Choose a missing or empty output directory:

```bash
scripts/course-notes prepare VIDEO_URL --output /absolute/path/to/output \
  --language auto --device auto --screenshot-interval 30
```

`--language` accepts `auto` or a language code. `--device` accepts `auto`, `cuda`, or `cpu`. Successful stdout is one JSON object containing absolute artifact paths, detected language, transcript segment count, and screenshot count.

After the agent has written `article.json` and `translation.json`, `compose` validates and renders the final aligned articles:

```bash
scripts/course-notes compose --output /absolute/path/to/output \
  --article /absolute/path/to/output/article.json \
  --translation /absolute/path/to/output/translation.json
```

`prepare` owns only reproducible media work. The agent owns semantic grouping, readable transcript text, explicit visual-group decisions, translation, and review. `compose` owns only contract validation, frame extraction, and rendering: it never decides whether adjacent visuals are similar.

## Output

```text
output/
  video.<actual-extension>
  audio.wav
  transcript.raw.json
  transcript.raw.md
  screenshots.json
  screenshots/
    0001-000000500.jpg
    ...
  article.json
  translation.json
  source.md
  zh-TW.md
  frames/
    0001.jpg
    ...
```

The article decision covers every raw ASR segment exactly once and in order with contiguous half-open transcript-index ranges. Each article segment contains one physical-line prose paragraph without Markdown block structure and includes `frame_ms`. An integer starts a meaningful visual group and must fall within that segment's time range. `frame_ms: null` continues the preceding visual group, so the first segment must use an integer.

Start a new group for slide changes and meaningful bullet, formula, or diagram reveals, not for cursor or presenter movement, compression noise, or cosmetic animation. If a meaningful change falls inside a long paragraph, split it at a nearby semantic and raw-transcript boundary without changing transcript content.

Older decisions that use an integer `frame_ms` for every segment remain valid: each paragraph simply starts its own visual group. The translation decision has the same derived segment IDs, and both rendered language files must have matching visual boundaries. A group-start block renders marker, image, timestamp, then paragraph; a continuation renders marker, timestamp, then paragraph. A continuation's effective frame is the most recent preceding group-start image.

Final review checks both directions: meaningful reveals must remain visible, and redundant visual starts must not create unnecessary images. Final counts must satisfy paragraph count = segment count and image count = visual-group count.

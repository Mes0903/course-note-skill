# Course Notes

Course Notes is a small local agent workflow that turns one video URL into aligned transcript articles. The finished output includes a readable source-language transcript and a Taiwanese Traditional Chinese version. One segment is one prose paragraph. Both versions use the same segments, times, visual boundaries, and images; several adjacent paragraphs may share one meaningful visual group.

For the complete data flow, program flow, project structure, responsibility boundaries, and artifact contracts, see [Architecture](docs/architecture.md).

## Requirements and install

The installer supports GNU/Linux x86-64, including WSL2. Python 3.12, Bash, curl, sha256sum, tar, unzip, FFmpeg, FFprobe, and GNU core utilities are required. On a new machine:

```bash
git clone https://github.com/Mes0903/course-note-skill.git
cd course-note-skill
scripts/install.sh --device auto
```

The installer creates `.venv`, installs pinned Deno for yt-dlp, and selects CPU or CUDA dependencies. Whisper models are cached under `.cache/course-notes/models` when first used.

The complete agent workflow also requires the external [zhtw-translocalizer skill](https://github.com/hanaya-dev/zhTW-translocalizer-skills), including its Python linter. Install that skill separately according to its instructions; `scripts/install.sh` installs only this project's tools. Its linter requires Python 3.10 or newer.

## Use with the agent

Open the cloned repository as the agent's workspace. The project-local skill is [`.agents/skills/course-notes/SKILL.md`](.agents/skills/course-notes/SKILL.md); keep it inside the checkout because it locates the CLI by walking up to the repository root. Give the URL to that skill. The agent runs preparation, reads the complete raw transcript and visual evidence, writes the two article decisions, obtains a fresh content review, and publishes both Markdown files. A run is complete only when `source.md` and `zh-TW.md` exist.

## Mechanical commands

`prepare` downloads and inspects the media, runs ASR once over the complete audio, and captures fixed-interval candidate screenshots. Choose a missing or empty output directory:

```bash
scripts/course-notes prepare VIDEO_URL --output /absolute/path/to/output \
  --language auto --device auto --screenshot-interval 30
```

`--language` accepts `auto` or a language code. `--device` accepts `auto`, `cuda`, or `cpu`. Successful stdout is one JSON object containing absolute artifact paths, detected language, transcript segment count, and screenshot count.

`$OUTPUT/prepare.log` is written and flushed as the run proceeds. It records the current phase, download progress, retry notices, and the final error if a phase fails. During a long run, inspect it with `tail -f "$OUTPUT/prepare.log"`. The tool retries interrupted downloads within the same run; after an exhausted failure, keep the log and choose a new empty output directory for another run.

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
  prepare.log
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

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from course_notes import __version__
from course_notes.article import compose_articles
from course_notes.pipeline import PrepareOptions, prepare


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="course-notes",
        description="Prepare video evidence and compose aligned transcript articles.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("prepare")
    prepare_command.add_argument("url")
    prepare_command.add_argument("--output", required=True, type=Path)
    prepare_command.add_argument("--language", default="auto")
    prepare_command.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    prepare_command.add_argument("--screenshot-interval", type=int, default=30)
    compose_command = commands.add_parser("compose")
    compose_command.add_argument("--output", required=True, type=Path)
    compose_command.add_argument("--article", required=True, type=Path)
    compose_command.add_argument("--translation", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "compose":
        result = compose_articles(args.output, args.article, args.translation)
    else:
        result = prepare(
            args.url,
            args.output,
            PrepareOptions(
                language=args.language,
                device=args.device,
                screenshot_interval=args.screenshot_interval,
            ),
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

from __future__ import annotations

import re
import stat
from collections.abc import Callable
from pathlib import Path
from time import monotonic

import yt_dlp


class _DownloadLogger:
    def __init__(self, log: Callable[[str], None]) -> None:
        self.log = log

    def _emit(self, message: str) -> None:
        self.log(re.sub(r"https?://\S+", "[URL]", " ".join(message.splitlines())))

    def debug(self, message: str) -> None:
        if "Retrying" in message or "Got error" in message:
            self._emit(message)

    def warning(self, message: str) -> None:
        self._emit(f"yt-dlp warning: {message}")

    def error(self, message: str) -> None:
        self._emit(f"yt-dlp error: {message}")


def download_video(url: str, output: Path, *, log: Callable[[str], None] | None = None) -> Path:
    output = Path(output)
    options = {
        "noplaylist": True,
        "ignoreconfig": True,
        "cachedir": False,
        "format": "bv*+ba/b",
        "merge_output_format": "mkv",
        "outtmpl": str(output / "video.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "retries": 10,
        "fragment_retries": 10,
    }
    if log is not None:
        last_progress: dict[str, float] = {}

        def progress_hook(event: dict[str, object]) -> None:
            name = Path(str(event.get("filename") or "media")).name
            if event.get("status") == "finished":
                log(f"download {name}: finished")
                return
            if event.get("status") != "downloading":
                return
            now = monotonic()
            if now - last_progress.get(name, float("-inf")) < 15:
                return
            last_progress[name] = now
            downloaded = event.get("downloaded_bytes")
            total = event.get("total_bytes") or event.get("total_bytes_estimate")
            if (
                isinstance(downloaded, (int, float))
                and isinstance(total, (int, float))
                and total > 0
            ):
                log(f"download {name}: {downloaded / total:.0%}")
            elif isinstance(downloaded, (int, float)):
                log(f"download {name}: {int(downloaded)} bytes")

        options["logger"] = _DownloadLogger(log)
        options["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.extract_info(url, download=True)

    videos = [
        path
        for path in output.glob("video.*")
        if path.suffix != ".part" and stat.S_ISREG(path.lstat().st_mode) and path.stat().st_size > 0
    ]
    if len(videos) != 1:
        raise ValueError("yt-dlp did not produce one complete video file")
    return videos[0]

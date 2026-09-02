from __future__ import annotations

import stat
from pathlib import Path

import yt_dlp


def download_video(url: str, output: Path) -> Path:
    output = Path(output)
    options = {
        "noplaylist": True,
        "ignoreconfig": True,
        "cachedir": False,
        "format": "bv*+ba/b",
        "merge_output_format": "mkv",
        "outtmpl": str(output / "video.%(ext)s"),
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.extract_info(url, download=True)

    videos = [
        path
        for path in output.glob("video.*")
        if path.suffix != ".part"
        and stat.S_ISREG(path.lstat().st_mode)
        and path.stat().st_size > 0
    ]
    if len(videos) != 1:
        raise ValueError("yt-dlp did not produce one complete video file")
    return videos[0]

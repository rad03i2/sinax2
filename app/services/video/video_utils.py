# -*- coding: utf-8 -*-
"""
SINAX Video Utilities
Helper functions for timestamp parsing, bitrate estimation, path management, and file scanning.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv",
    ".wmv", ".m4v", ".ts", ".mts", ".m2ts", ".vob",
    ".3gp", ".ogv", ".mpg", ".mpeg"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus", ".m4a", ".wma"
}


def parse_timestamp(val: str) -> float:
    """
    Parses various timestamp representations into total seconds (float).
    Examples:
        '10' -> 10.0
        '01:30' -> 90.0
        '01:15:30.5' -> 4530.5
        '00:02:15' -> 135.0
    """
    if not val:
        return 0.0
    s = str(val).strip()
    # If pure float/int
    try:
        return float(s)
    except ValueError:
        pass

    # Match HH:MM:SS[.xxx] or MM:SS[.xxx]
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            sec = float(parts[2])
            return h * 3600.0 + m * 60.0 + sec
        elif len(parts) == 2:
            m = float(parts[0])
            sec = float(parts[1])
            return m * 60.0 + sec
    except Exception:
        pass

    return 0.0


def format_seconds(seconds: float, include_ms: bool = False) -> str:
    """
    Formats seconds into standard HH:MM:SS or HH:MM:SS.mmm string.
    """
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    rem = seconds % 3600
    mins = int(rem // 60)
    secs = rem % 60
    if include_ms:
        return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"
    return f"{hrs:02d}:{mins:02d}:{int(secs):02d}"


def calculate_target_bitrate(target_mb: float, duration_sec: float, audio_kbit: int = 128) -> Tuple[int, int]:
    """
    Calculates the required video bitrate (in kbps) to ensure the total file
    size meets or is slightly below target_mb, accounting for container muxing overhead (~5%).
    Returns (video_kbps, audio_kbps).
    """
    if duration_sec <= 0:
        return (1000, audio_kbit)

    # Convert target_mb to total bits with 5% safety margin
    total_bits = (target_mb * 8 * 1024 * 1024) * 0.95
    total_bitrate_bps = total_bits / duration_sec
    total_kbps = int(total_bitrate_bps / 1000)

    # Audio allocation
    if total_kbps < 200:
        audio_kbps = min(64, audio_kbit)
    else:
        audio_kbps = audio_kbit

    video_kbps = max(50, total_kbps - audio_kbps)
    return (video_kbps, audio_kbps)


def is_video_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def is_audio_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in AUDIO_EXTENSIONS


def scan_video_files(paths: List[str], recursive: bool = True) -> List[str]:
    """
    Scans a list of files or folders and collects all video files.
    """
    collected = []
    seen = set()

    for p_str in paths:
        p = Path(p_str)
        if not p.exists():
            continue
        if p.is_file():
            if p.suffix.lower() in VIDEO_EXTENSIONS:
                resolved = str(p.resolve())
                if resolved not in seen:
                    seen.add(resolved)
                    collected.append(resolved)
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for item in p.glob(pattern):
                if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
                    resolved = str(item.resolve())
                    if resolved not in seen:
                        seen.add(resolved)
                        collected.append(resolved)

    return collected


def generate_output_path(
    input_path: str,
    output_dir: Optional[str] = None,
    prefix: str = "",
    suffix: str = "",
    new_ext: Optional[str] = None,
    preserve_dir_structure: bool = False,
    root_dir: Optional[str] = None,
) -> str:
    """
    Generates a conflict-free or structured destination path for an output video.
    """
    in_p = Path(input_path)
    stem = in_p.stem
    ext = (new_ext if new_ext else in_p.suffix).lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    new_filename = f"{prefix}{stem}{suffix}{ext}"

    if output_dir:
        out_base = Path(output_dir)
        if preserve_dir_structure and root_dir:
            try:
                rel = in_p.parent.relative_to(Path(root_dir))
                target_folder = out_base / rel
            except Exception:
                target_folder = out_base
        else:
            target_folder = out_base
    else:
        target_folder = in_p.parent

    target_folder.mkdir(parents=True, exist_ok=True)
    out_file = target_folder / new_filename

    # If the output file is identical to the input file, add a suffix to avoid overwriting source
    if str(out_file.resolve()) == str(in_p.resolve()):
        out_file = target_folder / f"{prefix}{stem}{suffix or '_out'}{ext}"

    return str(out_file)


def format_bytes(size_bytes: int) -> str:
    """Formats bytes into human readable MB/GB string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

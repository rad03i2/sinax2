# -*- coding: utf-8 -*-
"""
Audio Utilities for SINAX Audio Center.
Time formatting, format definitions, file scanners, bitrate calculations.
"""

import os
import re
from typing import List, Dict, Optional, Tuple, Set


AUDIO_FORMATS = [
    "mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "wma", "aiff", "alac", "ac3", "amr"
]

AUDIO_EXTENSIONS: Set[str] = {
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".oga",
    ".opus", ".wma", ".aiff", ".aif", ".ac3", ".amr", ".mka"
}


def is_audio_file(filepath: str) -> bool:
    """Check if file extension matches known audio formats."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in AUDIO_EXTENSIONS


def scan_audio_files(directory: str, recursive: bool = True) -> List[str]:
    """Scan directory for supported audio files."""
    results = []
    if not os.path.exists(directory):
        return results

    if recursive:
        for root, _, files in os.walk(directory):
            for f in sorted(files):
                if is_audio_file(f):
                    results.append(os.path.join(root, f))
    else:
        for f in sorted(os.listdir(directory)):
            full = os.path.join(directory, f)
            if os.path.isfile(full) and is_audio_file(f):
                results.append(full)
    return results


def format_duration(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS string."""
    if seconds is None or seconds < 0:
        return "00:00"
    total_sec = int(round(seconds))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_time_str(time_str: str) -> float:
    """
    Parse timestamp string into seconds.
    Supports formats:
      - "ss" or "ss.s"
      - "mm:ss" or "mm:ss.s"
      - "hh:mm:ss" or "hh:mm:ss.s"
    """
    if not time_str:
        return 0.0
    time_str = str(time_str).strip()
    try:
        if ":" not in time_str:
            return max(0.0, float(time_str))
        parts = time_str.split(":")
        if len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return max(0.0, m * 60.0 + s)
        elif len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return max(0.0, h * 3600.0 + m * 60.0 + s)
    except (ValueError, IndexError):
        pass
    return 0.0


def format_file_size(num_bytes: int) -> str:
    """Format bytes into readable string (B, KB, MB, GB)."""
    if num_bytes is None or num_bytes < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}" if unit != 'B' else f"{int(num_bytes)} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def calc_target_audio_bitrate(target_mb: float, duration_seconds: float) -> int:
    """
    Calculate target audio bitrate in kbps for a specific target file size in MB.
    Formula: target_bytes = target_mb * 1024 * 1024 * 0.95 (5% safety container overhead)
             bitrate_bps = (target_bytes * 8) / duration_seconds
             bitrate_kbps = bitrate_bps / 1000
    Clamped between 32 kbps and 320 kbps.
    """
    if duration_seconds <= 0 or target_mb <= 0:
        return 128
    target_bytes = target_mb * 1024 * 1024 * 0.95
    bitrate_bps = (target_bytes * 8) / duration_seconds
    bitrate_kbps = int(bitrate_bps / 1000)
    # Clamp to practical audio boundaries
    return max(32, min(320, bitrate_kbps))


# Standard Loudness Normalization Profiles
LOUDNORM_PRESETS = {
    "youtube_spotify": {"i": -14.0, "tp": -1.0, "lra": 11.0, "label": "YouTube / Spotify (-14 LUFS)"},
    "podcast_apple": {"i": -16.0, "tp": -1.0, "lra": 10.0, "label": "Podcast / Apple Podcasts (-16 LUFS)"},
    "broadcast_ebu": {"i": -23.0, "tp": -1.0, "lra": 7.0, "label": "EBU R128 European Broadcast (-23 LUFS)"},
    "general_quiet": {"i": -18.0, "tp": -1.5, "lra": 12.0, "label": "Standard Web Audio (-18 LUFS)"},
}

# Compression Presets
COMPRESS_PRESETS = {
    "light": {"bitrate": "256k", "quality": "2", "label": "ضغط خفيف (أعلى جودة - 256 kbps)"},
    "balanced": {"bitrate": "192k", "quality": "4", "label": "متوازن (موصى به - 192 kbps)"},
    "strong": {"bitrate": "128k", "quality": "5", "label": "ضغط قوي (توفير مساحة - 128 kbps)"},
    "max": {"bitrate": "64k", "quality": "8", "label": "أقصى ضغط (صوتيات ومحاضرات - 64 kbps)"},
    "lossless_flac": {"codec": "flac", "compression_level": "8", "label": "ضغط بدون فقدان (FLAC Level 8)"},
}

# Graphic EQ Presets
EQ_PRESETS = {
    "flat": {"bass": 0, "mid": 0, "treble": 0, "label": "افتراضي (Flat)"},
    "bass_boost": {"bass": 6, "mid": 0, "treble": -1, "label": "تعزيز البيز (Bass Boost)"},
    "vocal_speech": {"bass": -3, "mid": 4, "treble": 2, "label": "وضوح الكلام البشري (Speech Clarity)"},
    "podcast_warmth": {"bass": 2, "mid": 3, "treble": 3, "label": "صوت إذاعي دافئ (Broadcast Warmth)"},
    "treble_boost": {"bass": -2, "mid": 0, "treble": 6, "label": "بريق التريبل (Treble Boost)"},
    "acoustic": {"bass": 3, "mid": 1, "treble": 4, "label": "صوت طبيعي حيوي (Acoustic)"},
}

# -*- coding: utf-8 -*-
"""
SINAX File Quick Tools
File inspector, path copy formatters, timestamp editor with undo logging,
attribute changer, double extension and magic bytes inspector, and checksum sidecars.
"""

import ctypes
from datetime import datetime
import mimetypes
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple


MAGIC_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "PNG Image", ".png"),
    (b"\xff\xd8\xff", "JPEG Image", ".jpg"),
    (b"GIF87a", "GIF Image", ".gif"),
    (b"GIF89a", "GIF Image", ".gif"),
    (b"%PDF", "PDF Document", ".pdf"),
    (b"PK\x03\x04", "ZIP Archive / Office OpenXML", ".zip"),
    (b"Rar!\x1a\x07\x00", "RAR Archive", ".rar"),
    (b"Rar!\x1a\x07\x01\x00", "RAR5 Archive", ".rar"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip Archive", ".7z"),
    (b"MZ", "Windows Executable / DLL (PE)", ".exe"),
    (b"\x1f\x8b\x08", "GZIP Compressed", ".gz"),
    (b"OggS", "OGG Container", ".ogg"),
    (b"RIFF", "WAV / AVI / WEBP Container", ".riff"),
    (b"\x00\x00\x01\x00", "Windows Icon", ".ico"),
]


class FileTools:
    """Operations on individual files and file system metadata."""

    # History stack for timestamp undos: list of (file_path, old_atime, old_mtime)
    _timestamp_undo_history: List[Tuple[str, float, float]] = []

    @staticmethod
    def inspect_file(file_path: str) -> Dict[str, Any]:
        """Gathers comprehensive metadata and file system properties."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = p.stat()
        size_bytes = stat.st_size
        mime_type, _ = mimetypes.guess_type(file_path)

        # Windows attributes
        attrs = []
        is_readonly = False
        is_hidden = False
        try:
            raw_attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
            if raw_attrs != -1:
                if raw_attrs & 0x01:
                    attrs.append("Read-Only")
                    is_readonly = True
                if raw_attrs & 0x02:
                    attrs.append("Hidden")
                    is_hidden = True
                if raw_attrs & 0x04:
                    attrs.append("System")
                if raw_attrs & 0x20:
                    attrs.append("Archive")
        except Exception:
            pass

        created_dt = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        modified_dt = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        accessed_dt = datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S")

        # Double extension check (e.g. document.pdf.exe)
        parts = p.name.split(".")
        is_double_ext = len(parts) > 2 and parts[-1].lower() in ("exe", "bat", "cmd", "vbs", "ps1", "scr", "com")

        return {
            "name": p.name,
            "stem": p.stem,
            "suffix": p.suffix,
            "parent": str(p.parent),
            "full_path": str(p.resolve()),
            "size_bytes": size_bytes,
            "size_human": FileTools.format_size(size_bytes),
            "created": created_dt,
            "modified": modified_dt,
            "accessed": accessed_dt,
            "attributes": attrs,
            "is_readonly": is_readonly,
            "is_hidden": is_hidden,
            "mime_type": mime_type or "unknown/binary",
            "is_double_ext": is_double_ext,
        }

    @staticmethod
    def get_path_copy_variants(file_path: str) -> Dict[str, str]:
        """Generates various formatted representations of a file path for easy copying."""
        p = Path(file_path).resolve()
        raw_win = str(p)
        quoted = f'"{raw_win}"'
        pwsh = f"& '{raw_win}'"
        python_raw = f'r"{raw_win}"'
        uri = p.as_uri()

        return {
            "win_path": raw_win,
            "quoted": quoted,
            "powershell": pwsh,
            "python_raw": python_raw,
            "uri": uri,
            "parent_dir": str(p.parent),
            "filename": p.name,
            "stem": p.stem,
        }

    @staticmethod
    def format_size(bytes_val: int) -> str:
        """Converts raw byte count to human readable decimal string."""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024**2:
            return f"{bytes_val / 1024:.2f} KB"
        elif bytes_val < 1024**3:
            return f"{bytes_val / (1024**2):.2f} MB"
        elif bytes_val < 1024**4:
            return f"{bytes_val / (1024**3):.2f} GB"
        return f"{bytes_val / (1024**4):.2f} TB"

    @staticmethod
    def convert_size_units(bytes_val: int) -> Dict[str, str]:
        """Computes both Decimal (SI) and Binary (IEC) byte metrics."""
        b = float(bytes_val)
        return {
            "Bytes": f"{bytes_val:,} B",
            "KB (SI)": f"{b / 1000.0:,.2f} KB",
            "KiB (IEC)": f"{b / 1024.0:,.2f} KiB",
            "MB (SI)": f"{b / (1000**2):,.2f} MB",
            "MiB (IEC)": f"{b / (1024**2):,.2f} MiB",
            "GB (SI)": f"{b / (1000**3):,.2f} GB",
            "GiB (IEC)": f"{b / (1024**3):,.2f} GiB",
            "TB (SI)": f"{b / (1000**4):,.2f} TB",
            "TiB (IEC)": f"{b / (1024**4):,.2f} TiB",
        }

    @staticmethod
    def change_timestamps(
        file_path: str,
        new_modified_dt: Optional[datetime] = None,
        new_accessed_dt: Optional[datetime] = None
    ) -> bool:
        """Updates modified and accessed file timestamps while logging previous values for undo."""
        p = Path(file_path)
        if not p.exists():
            return False

        stat = p.stat()
        old_atime = stat.st_atime
        old_mtime = stat.st_mtime

        # Save for undo
        FileTools._timestamp_undo_history.append((str(p), old_atime, old_mtime))

        m_epoch = new_modified_dt.timestamp() if new_modified_dt else time.time()
        a_epoch = new_accessed_dt.timestamp() if new_accessed_dt else m_epoch

        os.utime(str(p), (a_epoch, m_epoch))
        return True

    @staticmethod
    def undo_last_timestamp_change() -> Optional[str]:
        """Reverts the last timestamp modification recorded in session history."""
        if not FileTools._timestamp_undo_history:
            return None

        path, old_atime, old_mtime = FileTools._timestamp_undo_history.pop()
        if os.path.exists(path):
            os.utime(path, (old_atime, old_mtime))
            return path
        return None

    @staticmethod
    def inspect_magic_signature(file_path: str) -> Dict[str, Any]:
        """Reads file header bytes and detects genuine content type vs nominal extension."""
        p = Path(file_path)
        if not p.is_file():
            return {"status": "error", "message": "File not found"}

        with open(file_path, "rb") as f:
            header = f.read(32)

        detected_type = "غير معروف (Raw Binary / Unknown)"
        expected_ext = p.suffix
        mismatch = False

        for sig_bytes, type_label, standard_ext in MAGIC_SIGNATURES:
            if header.startswith(sig_bytes):
                detected_type = type_label
                expected_ext = standard_ext
                if p.suffix.lower() != standard_ext.lower() and not (standard_ext == ".zip" and p.suffix.lower() in (".docx", ".xlsx", ".pptx", ".jar")):
                    mismatch = True
                break

        return {
            "filename": p.name,
            "nominal_extension": p.suffix,
            "detected_type": detected_type,
            "expected_extension": expected_ext,
            "has_mismatch": mismatch,
            "header_hex": " ".join(f"{b:02X}" for b in header[:16]),
        }

    @staticmethod
    def create_checksum_sidecar(file_path: str, algorithm: str = "SHA-256") -> str:
        """Computes checksum and saves alongside file as <name>.<ext>.sha256."""
        from app.services.quick_tools.tools.hash_tools import HashTools
        digest = HashTools.compute_file_hash(file_path, algorithm=algorithm)
        p = Path(file_path)
        sidecar_path = p.with_name(f"{p.name}.sha256")
        with open(sidecar_path, "w", encoding="utf-8") as f:
            f.write(f"{digest} *{p.name}\n")
        return str(sidecar_path)

    @staticmethod
    def touch_file(file_path: str) -> bool:
        """Touches a file, creating it if non-existent, or updating modified time to now."""
        p = Path(file_path)
        p.touch(exist_ok=True)
        return True

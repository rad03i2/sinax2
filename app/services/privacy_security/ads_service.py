# -*- coding: utf-8 -*-
"""
Alternate Data Streams (ADS) Inspector for SINAX Privacy & Security.
Discovers hidden NTFS streams using native Windows FindFirstStreamW API.
Parses Mark of the Web (Zone.Identifier) and allows safe, confirmed unblocking.
"""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class WIN32_FIND_STREAM_DATA(ctypes.Structure):
    _fields_ = [
        ("StreamSize", ctypes.c_longlong),
        ("cStreamName", wintypes.WCHAR * 296)
    ]


class AlternateDataStreamsService:
    """NTFS stream discovery and Mark of the Web (MOTW) management."""

    @classmethod
    def list_streams(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Enumerates all NTFS alternate streams for a file using Win32 API.
        Returns a list of dicts with 'name', 'size_bytes', and 'stream_type'.
        """
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return []

        kernel32 = ctypes.windll.kernel32
        FindFirstStreamW = kernel32.FindFirstStreamW
        FindFirstStreamW.restype = ctypes.c_void_p
        FindFirstStreamW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]

        FindNextStreamW = kernel32.FindNextStreamW
        FindNextStreamW.restype = wintypes.BOOL
        FindNextStreamW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        FindClose = kernel32.FindClose
        FindClose.restype = wintypes.BOOL
        FindClose.argtypes = [ctypes.c_void_p]

        data = WIN32_FIND_STREAM_DATA()
        handle = FindFirstStreamW(str(p), 0, ctypes.byref(data), 0)
        invalid_handle = ctypes.c_void_p(-1).value

        streams = []
        if handle and handle != invalid_handle:
            try:
                while True:
                    s_name = data.cStreamName
                    s_size = data.StreamSize

                    # Classify stream
                    if s_name == "::$DATA":
                        s_type = "التدفق الأساسي (Main Data Stream)"
                    elif "Zone.Identifier" in s_name:
                        s_type = "وسام الإنترنت (Mark of the Web / MOTW)"
                    else:
                        s_type = "تدفق بيانات بديل إضافي (Named Stream)"

                    streams.append({
                        "name": s_name,
                        "size_bytes": s_size,
                        "type": s_type,
                        "is_motw": "Zone.Identifier" in s_name
                    })

                    if not FindNextStreamW(handle, ctypes.byref(data)):
                        break
            finally:
                FindClose(handle)

        return streams

    @classmethod
    def read_motw(cls, file_path: str) -> Optional[str]:
        """Reads Zone.Identifier stream text if present."""
        zone_stream = f"{file_path}:Zone.Identifier"
        try:
            if os.path.exists(zone_stream):
                with open(zone_stream, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
        except Exception:
            pass
        return None

    @classmethod
    def remove_motw(cls, file_path: str) -> Tuple[bool, str]:
        """
        Safely removes Zone.Identifier stream (unblocking the file).
        Must only be called with explicit user confirmation.
        """
        zone_stream = f"{file_path}:Zone.Identifier"
        try:
            if os.path.exists(zone_stream):
                os.remove(zone_stream)
                return True, "تمت إزالة وسام الإنترنت (Zone.Identifier) وفك حظر الملف بنجاح."
            return False, "الملف لا يحمل وسام إنترنت بالأصل."
        except Exception as e:
            return False, f"فشلت إزالة وسام الإنترنت: {str(e)}"

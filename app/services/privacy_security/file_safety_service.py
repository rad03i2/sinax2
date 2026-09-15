# -*- coding: utf-8 -*-
"""
File Safety Inspector Service for SINAX Privacy & Security.
Executes non-executable static analysis:
- Magic bytes vs extension mismatch detector
- Double extension detector (.pdf.exe, .jpg.scr)
- Authenticode signature inspection
- Alternate Data Streams / Mark of the Web (Zone.Identifier)
- Cryptographic digests (SHA-256, SHA-512)
- Zero execution of suspicious payloads.
"""

import mimetypes
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.privacy_security.models import FileSafetyReport, SafetyLevel, SignatureStatus
from app.services.privacy_security.providers.signature_provider import WindowsAuthenticodeProvider
from app.services.quick_tools.tools.hash_tools import HashTools

MAGIC_SIGNATURES = [
    (b"MZ", "تطبيق تنفيذي Windows (PE/Executable)", "application/x-dosexec", [".exe", ".dll", ".sys", ".scr", ".cpl"]),
    (b"%PDF", "وثيقة PDF", "application/pdf", [".pdf"]),
    (b"\xFF\xD8\xFF", "صورة JPEG", "image/jpeg", [".jpg", ".jpeg"]),
    (b"\x89PNG\r\n\x1a\n", "صورة PNG", "image/png", [".png"]),
    (b"GIF87a", "صورة GIF", "image/gif", [".gif"]),
    (b"GIF89a", "صورة GIF", "image/gif", [".gif"]),
    (b"PK\x03\x04", "أرشيف مضغوط ZIP / حزمة أوفيس", "application/zip", [".zip", ".docx", ".xlsx", ".pptx", ".jar", ".apk"]),
    (b"Rar!\x1a\x07", "أرشيف RAR", "application/x-rar", [".rar"]),
    (b"7z\xbc\xaf\x27\x1c", "أرشيف 7-Zip", "application/x-7z-compressed", [".7z"]),
    (b"\x1f\x8b", "أرشيف GZIP", "application/gzip", [".gz"]),
    (b"RIFF", "وسائط متعددة (WAV / AVI / WEBP)", "audio/video", [".wav", ".avi", ".webp"]),
]

EXECUTABLE_EXTENSIONS = {".exe", ".scr", ".bat", ".cmd", ".vbs", ".js", ".ps1", ".jar", ".com", ".pif"}
DECEPTIVE_DOC_EXTENSIONS = {".jpg", ".png", ".jpeg", ".pdf", ".docx", ".xlsx", ".txt", ".mp4", ".mp3", ".zip"}


class FileSafetyService:
    """Non-executable static safety analysis engine."""

    @classmethod
    def inspect_file(cls, file_path: str) -> FileSafetyReport:
        """Performs non-executable comprehensive static file analysis."""
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return FileSafetyReport(
                path=str(p),
                filename=p.name,
                size_bytes=0,
                extension="",
                detected_mime="unknown",
                detected_type_name="ملف غير موجود",
                safety_level=SafetyLevel.CRITICAL,
                recommendations=["الملف غير موجود على القرص."]
            )

        stat = p.stat()
        size = stat.st_size
        ext = p.suffix.lower()

        # 1. Inspect Magic Bytes
        detected_type_name, detected_mime, is_mismatch, real_exec_type = cls._detect_magic_type(p, ext)

        # 2. Check for Double Extension deception (e.g. invoice.pdf.exe)
        is_double_ext, double_ext_warning = cls._detect_double_extension(p.name)

        # 3. Calculate SHA-256 and SHA-512
        sha256 = HashTools.compute_file_hash(str(p), algorithm="SHA-256")
        sha512 = HashTools.compute_file_hash(str(p), algorithm="SHA-512")

        # 4. Check Authenticode Signature
        sig_status, publisher, _ = WindowsAuthenticodeProvider.verify_file(str(p))

        # 5. Check Mark of the Web (Zone.Identifier) & Streams
        is_downloaded, zone_id, streams = cls._inspect_streams(p)

        # 6. Evaluate Recommendations & Safety Level
        recommendations = []
        safety_level = SafetyLevel.SAFE

        if is_double_ext:
            safety_level = SafetyLevel.WARNING
            recommendations.append(f"تنبيه امتداد مخادع: {double_ext_warning}")

        if is_mismatch:
            safety_level = SafetyLevel.WARNING
            recommendations.append(f"تنبيه تطابق المحتوى: الامتداد الظاهر ({ext}) لا يتطابق مع نوع البيانات الحقيقي ({detected_type_name}).")

        if ext in EXECUTABLE_EXTENSIONS:
            if sig_status == SignatureStatus.VALID:
                recommendations.append(f"برنامج تنفيذي موثق وموقع رقمياً بواسطة: {publisher}.")
            elif sig_status == SignatureStatus.UNSIGNED:
                if safety_level == SafetyLevel.SAFE:
                    safety_level = SafetyLevel.REVIEW_NEEDED
                recommendations.append("الملف تنفيذي غير موقع رقمياً (Unsigned). تحقق من مصدره قبل التشغيل.")
            elif sig_status in (SignatureStatus.INVALID, SignatureStatus.HASH_MISMATCH):
                safety_level = SafetyLevel.WARNING
                recommendations.append("توقيع الملف تالف أو لا يتطابق مع محتوى البرنامج الحالي.")

        if is_downloaded:
            recommendations.append("الملف يحمل وسام الإنترنت (Mark of the Web) وتم تحميله من شبكة خارجية.")

        created_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime))
        modified_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

        return FileSafetyReport(
            path=str(p),
            filename=p.name,
            size_bytes=size,
            extension=ext,
            detected_mime=detected_mime,
            detected_type_name=detected_type_name,
            is_extension_mismatch=is_mismatch,
            is_double_extension=is_double_ext,
            real_executable_type=real_exec_type,
            sha256=sha256,
            sha512=sha512,
            creation_time=created_str,
            modified_time=modified_str,
            signature_status=sig_status,
            publisher=publisher,
            is_downloaded_from_internet=is_downloaded,
            zone_id=zone_id,
            alternate_data_streams=streams,
            defender_scan_status="جاهز للفحص",
            recommendations=recommendations,
            safety_level=safety_level
        )

    @staticmethod
    def _detect_magic_type(path: Path, ext: str) -> Tuple[str, str, bool, Optional[str]]:
        header = b""
        try:
            with open(path, "rb") as f:
                header = f.read(32)
        except Exception:
            return "ملف غير قابل للقراءة", "application/octet-stream", False, None

        for sig, type_name, mime, valid_exts in MAGIC_SIGNATURES:
            if header.startswith(sig):
                if ext not in valid_exts:
                    real_exec = type_name if "PE" in type_name or "Executable" in type_name else None
                    return type_name, mime, True, real_exec
                return type_name, mime, False, None

        # Fallback to standard mimetypes
        guessed_mime, _ = mimetypes.guess_type(str(path))
        return "ملف قياسي", (guessed_mime or "application/octet-stream"), False, None

    @staticmethod
    def _detect_double_extension(filename: str) -> Tuple[bool, str]:
        parts = filename.lower().split(".")
        if len(parts) >= 3:
            first_ext = "." + parts[-2]
            last_ext = "." + parts[-1]
            if first_ext in DECEPTIVE_DOC_EXTENSIONS and last_ext in EXECUTABLE_EXTENSIONS:
                return True, f"الملف يتظاهر بأنه مستند ({first_ext}) ولكنه في الحقيقة تطبيق تنفيذي ({last_ext})."
        return False, ""

    @staticmethod
    def _inspect_streams(path: Path) -> Tuple[bool, Optional[int], List[Dict[str, Any]]]:
        is_downloaded = False
        zone_id = None
        streams = []

        # Check Zone.Identifier stream directly
        zone_stream = f"{str(path)}:Zone.Identifier"
        try:
            if os.path.exists(zone_stream):
                with open(zone_stream, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    streams.append({"name": ":Zone.Identifier:$DATA", "size": len(content), "type": "Mark of the Web"})
                    for line in content.splitlines():
                        if line.startswith("ZoneId="):
                            try:
                                zone_id = int(line.split("=")[1])
                                if zone_id in (3, 4):  # Internet or Restricted
                                    is_downloaded = True
                            except ValueError:
                                pass
        except Exception:
            pass

        return is_downloaded, zone_id, streams

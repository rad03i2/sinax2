# -*- coding: utf-8 -*-
"""
Digital Signature Center Service for SINAX Privacy & Security.
Orchestrates single-file verification, certificate details inspection,
batch directory classification, and unsigned executable discovery.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.models import CertificateDetails, SignatureStatus
from app.services.privacy_security.providers.signature_provider import WindowsAuthenticodeProvider

TARGET_BINARY_EXTENSIONS = {".exe", ".dll", ".sys", ".scr", ".cpl", ".msi", ".ps1", ".cat"}


@dataclass
class BatchSignatureResult:
    valid_count: int = 0
    unsigned_count: int = 0
    invalid_count: int = 0
    unknown_count: int = 0
    total_scanned: int = 0
    files_details: List[Dict[str, Any]] = None


class SignatureService:
    """Authenticode verification coordinator."""

    @classmethod
    def inspect_file(cls, file_path: str) -> Tuple[SignatureStatus, str, Optional[CertificateDetails]]:
        """Verifies signature of a single binary or script file."""
        return WindowsAuthenticodeProvider.verify_file(file_path)

    @classmethod
    def scan_directory(
        cls,
        folder_path: str,
        recursive: bool = False,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> BatchSignatureResult:
        """
        Scans all executables and libraries in a directory and classifies signatures.
        """
        p_dir = Path(folder_path).resolve()
        result = BatchSignatureResult(files_details=[])

        if not p_dir.exists() or not p_dir.is_dir():
            return result

        # Collect relevant binary files
        pattern = "**/*" if recursive else "*"
        candidates = [
            f for f in p_dir.glob(pattern)
            if f.is_file() and f.suffix.lower() in TARGET_BINARY_EXTENSIONS
        ]

        total = len(candidates)
        result.total_scanned = total

        for idx, file_path in enumerate(candidates):
            if cancel_check and cancel_check():
                break

            status, pub, cert = WindowsAuthenticodeProvider.verify_file(str(file_path))

            if status == SignatureStatus.VALID:
                result.valid_count += 1
            elif status == SignatureStatus.UNSIGNED:
                result.unsigned_count += 1
            elif status in (SignatureStatus.INVALID, SignatureStatus.HASH_MISMATCH, SignatureStatus.EXPIRED, SignatureStatus.UNTRUSTED):
                result.invalid_count += 1
            else:
                result.unknown_count += 1

            result.files_details.append({
                "path": str(file_path),
                "filename": file_path.name,
                "status": status.value,
                "publisher": pub,
                "has_cert": bool(cert),
                "issuer": cert.issuer if cert else "",
            })

            if progress_cb and total > 0:
                progress_cb((idx + 1) / total, f"فحص التوقيع: {idx + 1} من {total} ({file_path.name})")

        return result

    @classmethod
    def find_unsigned_executables(cls, folder_path: str) -> List[Dict[str, Any]]:
        """Finds unsigned executables only in a user-selected folder."""
        batch = cls.scan_directory(folder_path, recursive=False)
        return [f for f in (batch.files_details or []) if f["status"] == SignatureStatus.UNSIGNED.value]

# -*- coding: utf-8 -*-
"""
Microsoft Defender Service for SINAX Privacy & Security Center.
Provides clean service-level abstraction over native Windows Defender:
- Live protection telemetry and signature intelligence inspection
- On-demand custom file, directory, and batch scans
- Signature definition update coordination
- Official Windows Security settings integration
Zero custom fake antivirus engines; strictly delegates to Windows native defender.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.providers.antivirus_provider import MicrosoftDefenderProvider


class DefenderService:
    """Consolidated Microsoft Defender service layer."""

    def __init__(self):
        self._provider = MicrosoftDefenderProvider()

    def get_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Queries live Defender status, real-time protection, and signatures."""
        return self._provider.get_defender_status(force_refresh=force_refresh)

    def scan_path(self, target_path: str, timeout_seconds: int = 120) -> Tuple[bool, str]:
        """
        Executes on-demand scan of a single file or directory.
        Returns: (no_threat: bool, message: str)
        """
        return self._provider.scan_path(target_path, timeout_seconds=timeout_seconds)

    def scan_batch(
        self,
        paths: List[str],
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Sequentially scans a batch of file paths.
        """
        results = {
            "total": len(paths),
            "scanned": 0,
            "clean_count": 0,
            "threat_or_error_count": 0,
            "details": [],
        }

        total = len(paths)
        for idx, p in enumerate(paths):
            if cancel_check and cancel_check():
                break

            pct = (idx / total) if total > 0 else 0.0
            if progress_cb:
                progress_cb(pct, f"فحص: {Path(p).name}")

            ok, msg = self.scan_path(p)
            results["scanned"] += 1
            if ok:
                results["clean_count"] += 1
            else:
                results["threat_or_error_count"] += 1

            results["details"].append({"path": p, "clean": ok, "message": msg})

        if progress_cb:
            progress_cb(1.0, "اكتمل فحص Defender.")

        return results

    def update_signatures(self) -> Tuple[bool, str]:
        """Updates Microsoft Defender security intelligence definitions."""
        return self._provider.update_signatures()

    def open_windows_security(self):
        """Opens official Windows Security App."""
        self._provider.open_windows_security()

    def open_ransomware_settings(self):
        """Opens official Controlled Folder Access (Ransomware) settings."""
        self._provider.open_ransomware_settings()

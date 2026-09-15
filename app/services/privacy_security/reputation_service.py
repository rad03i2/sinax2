# -*- coding: utf-8 -*-
"""
Reputation Service for SINAX Privacy & Security Center.
Provides clean service coordination for online and offline reputation providers:
- Local hash-first querying (queries SHA-256 only, never uploads raw files automatically)
- Windows DPAPI key storage integration
- Resilient offline fallback and error handling
"""

from typing import Any, Dict, Optional, Tuple
from app.services.privacy_security.providers.reputation_provider import (
    FileReputationProvider,
    VirusTotalProvider,
)
from app.services.quick_tools.tools.hash_tools import HashTools


class ReputationService:
    """Consolidated file reputation and hash lookup service."""

    def __init__(self):
        self._vt_provider = VirusTotalProvider()

    def check_file_reputation_by_hash(
        self,
        file_path: str,
        provider_name: str = "virustotal",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Computes SHA-256 locally, then checks reputation if provider is configured.
        Guarantees that no raw file leaves the machine.
        """
        try:
            sha256 = HashTools.compute_file_hash(file_path, algorithm="SHA-256")
        except Exception as e:
            return False, f"فشل حساب بصمة الهاش محلياً: {str(e)}", {}

        if provider_name == "virustotal":
            return self._vt_provider.check_hash(sha256)

        return False, f"مزود السمعة غير مدعوم: {provider_name}", {}

    def check_hash_reputation(
        self,
        sha256_hash: str,
        provider_name: str = "virustotal",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Checks reputation of an existing SHA-256 hash string."""
        if provider_name == "virustotal":
            return self._vt_provider.check_hash(sha256_hash)
        return False, f"مزود السمعة غير مدعوم: {provider_name}", {}

    def save_api_key(self, provider_name: str, api_key: str):
        """Securely stores provider API key using Windows DPAPI."""
        if provider_name == "virustotal":
            self._vt_provider.save_api_key(api_key)

    def has_api_key(self, provider_name: str = "virustotal") -> bool:
        """Checks if a provider API key is stored."""
        if provider_name == "virustotal":
            return bool(self._vt_provider.get_api_key())
        return False

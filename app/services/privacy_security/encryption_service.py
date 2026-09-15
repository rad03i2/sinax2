# -*- coding: utf-8 -*-
"""
Encryption Service for SINAX Privacy & Security Center.
Provides clean service interfaces for:
- AES-256-GCM authenticated encryption/decryption
- scrypt / Argon2 key derivation functions
- Windows DPAPI account-bound secret storage
- Integrity verification and tamper detection
Zero custom crypto; strictly standard NIST-compliant cryptographic primitives.
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from app.services.privacy_security.providers.encryption_provider import (
    PortableVaultProvider,
    WindowsDpapiProvider,
)


class EncryptionService:
    """Consolidated cryptographic and vault encryption service."""

    @staticmethod
    def encrypt_file(
        source_path: str,
        dest_vault_path: str,
        password: str,
        is_directory_archive: bool = False,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str]:
        """Encrypts a file into an authenticated .sinaxvault container."""
        return PortableVaultProvider.encrypt_file(
            source_path=source_path,
            dest_vault_path=dest_vault_path,
            password=password,
            is_directory_archive=is_directory_archive,
            progress_cb=progress_cb,
            cancel_check=cancel_check,
        )

    @staticmethod
    def decrypt_file(
        vault_path: str,
        dest_path: str,
        password: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str, bool]:
        """Decrypts a .sinaxvault container with authentication verification."""
        return PortableVaultProvider.decrypt_file(
            vault_path=vault_path,
            dest_path=dest_path,
            password=password,
            progress_cb=progress_cb,
            cancel_check=cancel_check,
        )

    @staticmethod
    def protect_secret_dpapi(data: bytes, description: str = "SINAX Protected Secret") -> bytes:
        """Encrypts secret data bound to current Windows user account using DPAPI."""
        return WindowsDpapiProvider.protect(data, description=description)

    @staticmethod
    def unprotect_secret_dpapi(cipher_data: bytes) -> bytes:
        """Decrypts Windows DPAPI protected secret data."""
        return WindowsDpapiProvider.unprotect(cipher_data)

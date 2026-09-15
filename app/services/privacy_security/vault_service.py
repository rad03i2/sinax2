# -*- coding: utf-8 -*-
"""
Vault Service for SINAX Privacy & Security.
High-level manager for creating, opening, and extracting .sinaxvault containers.
Handles single files and entire directories with structure preservation.
Integrates Portable AES-256-GCM and Windows DPAPI modes.
"""

import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.privacy_db import PrivacyDatabase
from app.services.privacy_security.providers.encryption_provider import (
    PortableVaultProvider,
    WindowsDpapiProvider,
)


class VaultService:
    """High-level encryption vault management engine."""

    def __init__(self):
        self._db = PrivacyDatabase()

    def create_vault(
        self,
        source_path: str,
        dest_vault_path: str,
        password: str,
        mode: str = "portable",  # "portable" (AES-GCM+scrypt) or "windows_dpapi"
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str]:
        """
        Creates a .sinaxvault container for a file or an entire directory.
        """
        src = Path(source_path).resolve()
        dest = Path(dest_vault_path).resolve()

        if not src.exists():
            return False, "المسار المصدري غير موجود."

        is_dir = src.is_dir()
        temp_tar = None

        try:
            # If directory, package into a streaming tarball first
            if is_dir:
                if progress_cb:
                    progress_cb(0.05, "جاري تحزيم شجرة المجلدات داخل الحاوية...")
                temp_tar = dest.parent / f"pack_{os.urandom(8).hex()}.tar"
                with tarfile.open(temp_tar, "w") as tar:
                    tar.add(src, arcname=src.name)
                input_file_to_encrypt = temp_tar
                total_files = len(list(src.rglob("*")))
            else:
                input_file_to_encrypt = src
                total_files = 1

            if mode == "portable":
                ok, msg = PortableVaultProvider.encrypt_file(
                    str(input_file_to_encrypt),
                    str(dest),
                    password=password,
                    is_directory_archive=is_dir,
                    progress_cb=progress_cb,
                    cancel_check=cancel_check,
                )
            elif mode == "windows_dpapi":
                # Account bound DPAPI encryption
                with open(input_file_to_encrypt, "rb") as fin:
                    raw_data = fin.read()
                cipher = WindowsDpapiProvider.protect(raw_data, description="SINAX Protected Vault")
                with open(dest, "wb") as fout:
                    fout.write(b"SINAXDPA\x01\x00")  # DPAPI magic header
                    fout.write(cipher)
                ok, msg = True, "تم تشفير الخزنة وربطها بحساب Windows الحالي بنجاح."
            else:
                return False, f"نمط التشفير غير مدعوم: {mode}"

            if ok:
                self._db.register_vault(str(dest), mode=mode, cipher="AES-256-GCM", total_files=total_files)
                self._db.log_event("VAULT_CREATED", str(dest), "SUCCESS", {"mode": mode, "is_directory": is_dir})

            return ok, msg

        except Exception as e:
            return False, f"خطأ أثناء إنشاء الخزنة: {str(e)}"
        finally:
            if temp_tar and temp_tar.exists():
                try:
                    temp_tar.unlink()
                except Exception:
                    pass

    def open_vault(
        self,
        vault_path: str,
        dest_extract_dir: str,
        password: str = "",
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str]:
        """
        Decrypts and extracts the contents of a .sinaxvault file.
        """
        vault = Path(vault_path).resolve()
        dest_dir = Path(dest_extract_dir).resolve()

        if not vault.exists():
            return False, "ملف الخزنة غير موجود."

        dest_dir.mkdir(parents=True, exist_ok=True)
        temp_dec = dest_dir / f"dec_{os.urandom(8).hex()}.tmp"

        try:
            # Check if DPAPI format
            with open(vault, "rb") as f:
                magic = f.read(8)

            if magic == b"SINAXDPA":
                with open(vault, "rb") as f:
                    f.seek(10)
                    cipher = f.read()
                plaintext = WindowsDpapiProvider.unprotect(cipher)
                with open(temp_dec, "wb") as f:
                    f.write(plaintext)
                is_dir = False
                ok, msg = True, "تم فك التشفير عبر حساب Windows بنجاح."
            else:
                ok, msg, is_dir = PortableVaultProvider.decrypt_file(
                    str(vault),
                    str(temp_dec),
                    password=password,
                    progress_cb=progress_cb,
                    cancel_check=cancel_check,
                )

            if not ok:
                return False, msg

            # If it was a directory vault, unpack the tar archive
            if is_dir:
                if progress_cb:
                    progress_cb(0.9, "جاري استخراج الملفات واستعادة بنية المجلد...")
                with tarfile.open(temp_dec, "r") as tar:
                    tar.extractall(path=dest_dir)
                final_output = str(dest_dir)
            else:
                # Rename decrypted file to target
                final_target = dest_dir / vault.stem
                if final_target.exists():
                    final_target.unlink()
                temp_dec.rename(final_target)
                final_output = str(final_target)

            self._db.log_event("VAULT_DECRYPTED", str(vault), "SUCCESS", {"output": final_output})
            return True, f"تم استخراج وفك تشفير محتويات الخزنة بنجاح إلى: {final_output}"

        except Exception as e:
            return False, f"فشل فتح الخزنة: {str(e)}"
        finally:
            if temp_dec.exists():
                try:
                    temp_dec.unlink()
                except Exception:
                    pass

    def get_known_vaults(self) -> List[Dict[str, Any]]:
        """Returns list of registered vaults from the database."""
        return self._db.get_registered_vaults()

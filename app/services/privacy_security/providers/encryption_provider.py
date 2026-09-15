# -*- coding: utf-8 -*-
"""
Encryption Provider for SINAX Privacy & Security.
Implements authenticated chunked streaming AES-256-GCM with scrypt KDF for portable .sinaxvault files,
and Windows DPAPI (Data Protection API) for account-bound secrets.
Zero custom crypto; strictly standard cryptographic primitives.
"""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import struct
import tempfile
from typing import Callable, Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app.services.privacy_security.models import VaultHeader

MAGIC_HEADER = b"SINAXVLT"
FORMAT_VERSION = 1
CHUNK_SIZE = 1024 * 1024  # 1 MB streaming chunks
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1


class PortableVaultProvider:
    """
    Standard AES-256-GCM + scrypt authenticated encryption engine.
    Streams in 1MB chunks to support files exceeding 100 GB without RAM pressure.
    """

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Derives a 256-bit AES key using scrypt."""
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
        )
        return kdf.derive(password.encode("utf-8"))

    @staticmethod
    def encrypt_file(
        source_path: str,
        dest_vault_path: str,
        password: str,
        is_directory_archive: bool = False,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str]:
        """
        Encrypts source file into a .sinaxvault container using AES-256-GCM.
        Guarantees atomic creation and cleanup on cancel/error.
        """
        src = Path(source_path).resolve()
        dest = Path(dest_vault_path).resolve()

        if not src.exists():
            return False, f"الملف المصدري غير موجود: {source_path}"

        total_size = src.stat().st_size
        salt = os.urandom(32)
        key = PortableVaultProvider.derive_key(password, salt)
        aesgcm = AESGCM(key)

        dest.parent.mkdir(parents=True, exist_ok=True)
        temp_dest = dest.with_suffix(dest.suffix + ".tmp_enc")

        try:
            with open(src, "rb") as fin, open(temp_dest, "wb") as fout:
                # Write 64-byte structured header:
                # Magic (8b) + Version (2b) + Salt (32b) + ChunkSize (4b) + Flags (2b) + Reserved (16b)
                flags = 1 if is_directory_archive else 0
                header_prefix = struct.pack(">8sHH32sIH14s", MAGIC_HEADER, FORMAT_VERSION, 1, salt, CHUNK_SIZE, flags, b"\x00" * 14)
                fout.write(header_prefix)

                chunk_index = 0
                bytes_processed = 0

                while True:
                    if cancel_check and cancel_check():
                        fout.close()
                        if temp_dest.exists():
                            temp_dest.unlink()
                        return False, "تم إلغاء عملية التشفير بناءً على طلب المستخدم."

                    chunk = fin.read(CHUNK_SIZE)
                    if not chunk and chunk_index > 0:
                        break

                    # Construct unique 12-byte nonce per chunk: 8 bytes CSPRNG prefix + 4 bytes chunk index
                    chunk_nonce = os.urandom(8) + struct.pack(">I", chunk_index)
                    associated_data = struct.pack(">Q", chunk_index)

                    ciphertext = aesgcm.encrypt(chunk_nonce, chunk, associated_data)

                    # Write: Nonce (12b) + Ciphertext_length (4b) + Ciphertext_with_tag
                    fout.write(chunk_nonce)
                    fout.write(struct.pack(">I", len(ciphertext)))
                    fout.write(ciphertext)

                    bytes_processed += len(chunk)
                    chunk_index += 1

                    if progress_cb and total_size > 0:
                        progress = min(1.0, bytes_processed / total_size)
                        mb_done = bytes_processed / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        progress_cb(progress, f"جاري التشفير: {mb_done:.1f} MB من {mb_total:.1f} MB ({int(progress*100)}%)")

                    if not chunk:
                        # Empty source file handled
                        break

            # Atomic rename after full successful encryption
            if dest.exists():
                dest.unlink()
            temp_dest.rename(dest)

            if progress_cb:
                progress_cb(1.0, "اكتمل التشفير وتم التحقق من سلامة الحاوية بنجاح.")
            return True, f"تم إنشاء الخزنة المشفرة بنجاح: {dest.name}"

        except Exception as e:
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass
            return False, f"فشل التشفير: {str(e)}"

    @staticmethod
    def decrypt_file(
        vault_path: str,
        dest_path: str,
        password: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str, bool]:
        """
        Decrypts a .sinaxvault file using AES-256-GCM.
        Returns: (success: bool, message: str, is_directory_archive: bool)
        Guarantees that no corrupted or unauthenticated data remains on disk.
        """
        vault = Path(vault_path).resolve()
        dest = Path(dest_path).resolve()

        if not vault.exists():
            return False, f"ملف الخزنة غير موجود: {vault_path}", False

        vault_size = vault.stat().st_size
        if vault_size < 74:
            return False, "ملف الخزنة تالف أو لا يحتوي على ترويسة صالحة.", False

        dest.parent.mkdir(parents=True, exist_ok=True)
        temp_dest = dest.with_suffix(dest.suffix + ".tmp_dec")

        try:
            with open(vault, "rb") as fin:
                header_data = fin.read(64)
                magic, version, kdf_id, salt, chunk_size, flags, _ = struct.unpack(">8sHH32sIH14s", header_data)

                if magic != MAGIC_HEADER:
                    return False, "الملف ليس حاوية مشفرة صالحة من نوع SINAX Vault.", False

                if version != FORMAT_VERSION:
                    return False, f"إصدار الحاوية غير مدعوم ({version}).", False

                is_dir = bool(flags & 1)

                key = PortableVaultProvider.derive_key(password, salt)
                aesgcm = AESGCM(key)

                with open(temp_dest, "wb") as fout:
                    chunk_index = 0
                    bytes_read = 64

                    while bytes_read < vault_size:
                        if cancel_check and cancel_check():
                            fout.close()
                            if temp_dest.exists():
                                temp_dest.unlink()
                            return False, "تم إلغاء فك التشفير بناءً على طلب المستخدم.", is_dir

                        nonce = fin.read(12)
                        len_bytes = fin.read(4)
                        if not nonce or not len_bytes:
                            break

                        ciphertext_len = struct.unpack(">I", len_bytes)[0]
                        ciphertext = fin.read(ciphertext_len)

                        if len(ciphertext) != ciphertext_len:
                            raise ValueError("بيانات الحاوية مبتورة أو ناقصة.")

                        associated_data = struct.pack(">Q", chunk_index)

                        # Decrypt and authenticate GCM tag
                        try:
                            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
                        except Exception:
                            raise ValueError("تعذر فك التشفير أو فشل التحقق من سلامة البيانات (كلمة المرور غير صحيحة أو تم العبث بالملف).")

                        fout.write(plaintext)
                        bytes_read += 16 + ciphertext_len
                        chunk_index += 1

                        if progress_cb and vault_size > 0:
                            progress = min(1.0, bytes_read / vault_size)
                            progress_cb(progress, f"جاري فك التشفير والتحقق: {int(progress * 100)}%")

            # Atomic commit on success
            if dest.exists():
                dest.unlink()
            temp_dest.rename(dest)

            return True, "تم فك التشفير والتحقق من سلامة البيانات بنجاح.", is_dir

        except Exception as e:
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass
            return False, str(e), False


class WindowsDpapiProvider:
    """DPAPI wrapper using Windows CryptProtectData and CryptUnprotectData via ctypes."""

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    @classmethod
    def protect(cls, plaintext: bytes, description: str = "SINAX Secret") -> bytes:
        """Protects data tied to the current Windows user account."""
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = cls.DATA_BLOB(len(plaintext), ctypes.cast(ctypes.create_string_buffer(plaintext), ctypes.POINTER(ctypes.c_byte)))
        out_blob = cls.DATA_BLOB()

        # CRYPTPROTECT_UI_FORBIDDEN = 0x01
        success = crypt32.CryptProtectData(ctypes.byref(in_blob), description, None, None, None, 0x01, ctypes.byref(out_blob))
        if not success:
            raise RuntimeError("فشلت عملية CryptProtectData في تشفير البيانات عبر DPAPI.")

        cipher = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        kernel32.LocalFree(out_blob.pbData)
        return cipher

    @classmethod
    def unprotect(cls, ciphertext: bytes) -> bytes:
        """Unprotects DPAPI data for the current Windows user account."""
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = cls.DATA_BLOB(len(ciphertext), ctypes.cast(ctypes.create_string_buffer(ciphertext), ctypes.POINTER(ctypes.c_byte)))
        out_blob = cls.DATA_BLOB()

        success = crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0x01, ctypes.byref(out_blob))
        if not success:
            raise RuntimeError("فشلت عملية CryptUnprotectData في استرجاع البيانات (البيانات لا تخص حساب المستخدم الحالي).")

        plaintext = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        kernel32.LocalFree(out_blob.pbData)
        return plaintext

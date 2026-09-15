# -*- coding: utf-8 -*-
"""
SINAX High-Performance Copy Engine.
Provides low-RAM chunked streaming file copying with atomic partial renames (.sinaxpartial),
locked file resilience, timestamp preservation, and Robocopy provider integration.
"""

import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger

logger = get_logger("copy_engine")


class CopyError(Exception):
    pass


class FileLockedError(CopyError):
    pass


class CopyEngine:
    """Core file copying abstraction with streaming and atomic rename."""

    CHUNK_SIZE = 512 * 1024  # 512 KB chunks for smooth I/O and low RAM

    @classmethod
    def copy_file_streaming(
        cls,
        src_path: str,
        dst_path: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Copies a single file using chunked streaming directly to .sinaxpartial
        then atomically renames to dst_path upon verified completion.
        """
        src = Path(src_path)
        dst = Path(dst_path)

        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source file not found: {src_path}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        partial_dst = dst.parent / f".{dst.name}.sinaxpartial"

        total_bytes = src.stat().st_size
        copied_bytes = 0

        try:
            with open(src, "rb") as f_in, open(partial_dst, "wb") as f_out:
                while True:
                    if cancel_check and cancel_check():
                        # Clean up partial on cancel
                        f_out.close()
                        partial_dst.unlink(missing_ok=True)
                        return False

                    chunk = f_in.read(cls.CHUNK_SIZE)
                    if not chunk:
                        break

                    f_out.write(chunk)
                    copied_bytes += len(chunk)

                    if progress_cb:
                        progress_cb(copied_bytes, total_bytes)

                f_out.flush()
                os.fsync(f_out.fileno())

            # Verify size before atomic rename
            if partial_dst.stat().st_size != total_bytes:
                partial_dst.unlink(missing_ok=True)
                raise CopyError(f"Partial copy size mismatch for {dst.name}")

            # Atomic rename
            os.replace(str(partial_dst), str(dst))

            # Preserve modification and access times
            src_stat = src.stat()
            os.utime(str(dst), (src_stat.st_atime, src_stat.st_mtime))

            return True

        except PermissionError as e:
            partial_dst.unlink(missing_ok=True)
            raise FileLockedError(f"الملف قيد الاستخدام أو مقفول بواسطة تطبيق آخر: {src.name} ({e})")
        except Exception as e:
            partial_dst.unlink(missing_ok=True)
            raise CopyError(f"فشل نسخ الملف: {e}")

    @classmethod
    def copy_file_safe(
        cls,
        src_path: str,
        dst_path: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        """Safe wrapper returning (success, error_message)."""
        try:
            ok = cls.copy_file_streaming(src_path, dst_path, progress_cb, cancel_check)
            return ok, ""
        except FileLockedError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)


class RobocopyProvider:
    """Robocopy integration for robust mass folder copies with Windows attributes."""

    @classmethod
    def execute_robocopy(
        cls,
        source_dir: str,
        dest_dir: str,
        mirror: bool = False,
        dry_run: bool = False,
        exclude_patterns: Optional[List[str]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, int, str]:
        """
        Runs robocopy.exe with safe list arguments (NO shell=True).
        Parses exit codes: codes < 8 indicate success or benign changes!
        """
        cmd = ["robocopy.exe", source_dir, dest_dir]

        if mirror:
            cmd.append("/MIR")
        else:
            cmd.append("/E")

        # Retry policy: 1 retry, 1 second wait
        cmd.extend(["/R:1", "/W:1", "/NP", "/NDL", "/NFL"])

        if dry_run:
            cmd.append("/L")

        if exclude_patterns:
            files_ex = [p for p in exclude_patterns if not p.endswith("/") and not p.endswith("\\")]
            if files_ex:
                cmd.append("/XF")
                cmd.extend(files_ex)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600
            )

            # Robocopy return codes:
            # 0 = No changes, 1 = Files copied, 2 = Extra files, 4 = Mismatches
            # 1+2 = 3, 1+4 = 5, 2+4 = 6, 1+2+4 = 7 (All successful/benign)
            # >= 8 means one or more failures
            if res.returncode < 8:
                return True, res.returncode, "اكتملت عملية النسخ بنجاح عبر Robocopy."
            else:
                return False, res.returncode, f"فشل جزئي أو كلي أثناء نسخ Robocopy (كود الخطأ: {res.returncode})"

        except Exception as e:
            return False, -1, f"تعذر تشغيل Robocopy: {e}"

# -*- coding: utf-8 -*-
"""
Secure Delete Service for SINAX Privacy & Security.
Orchestrates storage-aware deletion, prepares confirmation statistics,
protects critical Windows directories, and records audit logs.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.models import StorageType
from app.services.privacy_security.privacy_db import PrivacyDatabase
from app.services.privacy_security.providers.secure_delete_provider import NativeOverwriteProvider


class SecureDeleteService:
    """High-level sensitive deletion coordinator."""

    def __init__(self):
        self._db = PrivacyDatabase()

    def inspect_target_for_deletion(self, path: str) -> Dict[str, Any]:
        """
        Inspects the item before deletion and returns media type, item count,
        total size, and safety warnings for the confirmation dialog.
        """
        p = Path(path).resolve()
        if not p.exists():
            return {"exists": False, "error": "المسار غير موجود."}

        is_dir = p.is_dir()
        is_protected = NativeOverwriteProvider.is_path_protected(str(p))
        storage_type, media_desc = NativeOverwriteProvider.get_drive_storage_type(str(p))

        if is_protected:
            total_items = 0
            total_bytes = 0
        elif is_dir:
            files = [f for f in p.rglob("*") if f.is_file()]
            total_items = len(files)
            total_bytes = sum(f.stat().st_size for f in files)
        else:
            total_items = 1
            total_bytes = p.stat().st_size

        is_flash = storage_type in (StorageType.SSD, StorageType.NVME)

        if is_flash:
            scientific_note = (
                "تنبيه علمي هام (NIST 800-88):\n"
                "هذا الملف يقع على قرص وميضي (SSD/NVMe). نظراً لوجود طبقة ترجمة الفلاش (FTL) "
                "وخوارزميات توزيع التآكل (Wear-Leveling)، فإن الكتابة فوق الملف لا تضمن محو "
                "كل النسخ الفيزيائية الموزعة في الكتل المحجوزة. للبيانات فائقة السرية، "
                "الحل الموصى به هو التشفير الكامل للقرص أو مسح القرص بالكامل (Device Sanitization)."
            )
        else:
            scientific_note = (
                "القرص من نوع مغناطيسي تقليدي (HDD). "
                "تعتبر الكتابة المتعددة (Overwriting) فعالة جداً في إتلاف البيانات ومنع استرجاعها."
            )

        return {
            "exists": True,
            "path": str(p),
            "is_directory": is_dir,
            "is_protected": is_protected,
            "storage_type": storage_type.value,
            "media_desc": media_desc,
            "is_flash": is_flash,
            "total_items": total_items,
            "total_bytes": total_bytes,
            "scientific_note": scientific_note,
        }

    def execute_secure_delete(
        self,
        path: str,
        passes: int = 1,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str]:
        """Executes the sensitive deletion process and records an audit log."""
        p = Path(path).resolve()
        if not p.exists():
            return False, "المسار المحدد غير موجود."

        info = self.inspect_target_for_deletion(str(p))
        if info.get("is_protected"):
            return False, "محاولة مرفوضة: لا يمكن حذف ملفات أو مجلدات النظام الأساسية."

        if p.is_dir():
            ok, msg, count = NativeOverwriteProvider.secure_delete_folder(
                str(p),
                passes=passes,
                progress_cb=progress_cb,
                cancel_check=cancel_check,
            )
        else:
            ok, msg = NativeOverwriteProvider.secure_delete_file(
                str(p),
                passes=passes,
                progress_cb=progress_cb,
            )

        status_str = "SUCCESS" if ok else "FAILED"
        self._db.log_event(
            "SECURE_DELETE",
            str(p),
            status_str,
            {"passes": passes, "storage_type": info["storage_type"], "is_flash": info["is_flash"]}
        )

        return ok, msg

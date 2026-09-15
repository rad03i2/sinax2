# -*- coding: utf-8 -*-
"""
SINAX Clipboard Laboratory
Inspects active clipboard data types (Text, Image, File lists), offers 1-click
plain text conversion, QR code creation from clipboard, and file exports.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtGui import QClipboard, QGuiApplication, QImage, QPixmap


class ClipboardTools:
    """Operations on the operating system clipboard buffer."""

    @staticmethod
    def inspect_clipboard() -> Dict[str, Any]:
        """Gathers information about the current content residing in the system clipboard."""
        app = QGuiApplication.instance()
        if not app:
            return {"type": "none", "description": "تطبيق الواجهة غير نشط"}

        cb = app.clipboard()
        mime = cb.mimeData()

        if not mime:
            return {"type": "empty", "description": "الحافظة فارغة حالياً"}

        if mime.hasUrls():
            urls = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
            return {
                "type": "files",
                "count": len(urls),
                "preview": ", ".join(Path(u).name for u in urls[:5]),
                "urls": urls,
                "description": f"{len(urls)} ملف/مجلد منسوخ",
            }
        elif mime.hasImage():
            img = cb.image()
            return {
                "type": "image",
                "width": img.width(),
                "height": img.height(),
                "description": f"صورة في الحافظة ({img.width()}×{img.height()} بكسل)",
            }
        elif mime.hasText():
            text = cb.text()
            return {
                "type": "text",
                "char_count": len(text),
                "word_count": len(text.split()),
                "has_html": mime.hasHtml(),
                "preview": text[:120].replace("\n", " "),
                "full_text": text,
                "description": f"نص ({len(text)} حرف)",
            }

        return {"type": "other", "description": "بيانات غير نصية"}

    @staticmethod
    def copy_as_plain_text() -> Optional[str]:
        """Strips all HTML/Rich formatting from clipboard, leaving pure plain text."""
        app = QGuiApplication.instance()
        if not app:
            return None
        cb = app.clipboard()
        text = cb.text()
        if text:
            cb.clear()
            cb.setText(text)
            return text
        return None

    @staticmethod
    def save_clipboard_to_file(dest_path: str) -> bool:
        """Saves current clipboard text or image directly to a disk file."""
        app = QGuiApplication.instance()
        if not app:
            return False
        cb = app.clipboard()
        mime = cb.mimeData()

        if mime.hasImage():
            img = cb.image()
            return img.save(dest_path)
        elif mime.hasText():
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(cb.text())
            return True
        return False

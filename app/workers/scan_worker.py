# -*- coding: utf-8 -*-
"""
SINAX ScanWorker
Asynchronously scans directories in a background QThread, emitting batches of FileItems
and summary metrics to keep the user interface completely fluid.
"""

from pathlib import Path
from typing import Optional, List, Dict
from PySide6.QtCore import Signal

from app.workers.base_worker import BaseWorker
from app.models.file_item import FileItem
from app.core.constants import FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.logger import get_logger

logger = get_logger("scan_worker")

class ScanWorker(BaseWorker):
    scan_started = Signal()
    chunk_loaded = Signal(list)  # List[FileItem]
    summary_ready = Signal(dict, object)  # (category_counts, total_bytes)
    scan_finished = Signal(list)  # All List[FileItem]
    scan_error = Signal(str)

    def __init__(
        self,
        directory: Path,
        recursive: bool = False,
        category_filter: str = "all",
        custom_extension: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.directory = Path(directory)
        self.recursive = recursive
        self.category_filter = category_filter
        self.custom_extension = custom_extension

    def run(self):
        self.scan_started.emit()
        items: List[FileItem] = []
        counts: Dict[str, int] = {k: 0 for k in FILE_CATEGORIES.keys()}
        total_bytes = 0
        chunk: List[FileItem] = []

        if not self.directory.exists() or not self.directory.is_dir():
            self.scan_error.emit("المجلد المحدد غير موجود أو لا يمكن الوصول إليه.")
            return

        try:
            iterator = self.directory.rglob('*') if self.recursive else self.directory.glob('*')
            for path in iterator:
                if self.is_canceled():
                    self.operation_canceled.emit()
                    return

                try:
                    if not path.is_file():
                        continue

                    item = FileItem.from_path(path)
                    counts['all'] += 1
                    counts[item.category_key] = counts.get(item.category_key, 0) + 1
                    total_bytes += item.size_bytes

                    # Filtering
                    if self.category_filter and self.category_filter != "all":
                        if item.category_key != self.category_filter:
                            continue

                    if self.custom_extension:
                        clean = self.custom_extension.lower().strip()
                        if not clean.startswith('.'):
                            clean = '.' + clean
                        if item.extension.lower() != clean:
                            continue

                    items.append(item)
                    chunk.append(item)

                    # Emit in chunks of 50
                    if len(chunk) >= 50:
                        self.chunk_loaded.emit(list(chunk))
                        chunk.clear()

                except (PermissionError, FileNotFoundError):
                    continue

            # Emit remaining items
            if chunk:
                self.chunk_loaded.emit(list(chunk))
                chunk.clear()

            self.summary_ready.emit(counts, total_bytes)
            self.scan_finished.emit(items)
            logger.info(f"Scan complete for {self.directory}: {len(items)} matching files.")

        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.scan_error.emit(f"حدث خطأ أثناء فحص المجلد: {e}")

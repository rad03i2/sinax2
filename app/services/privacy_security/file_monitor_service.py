# -*- coding: utf-8 -*-
"""
File Integrity Monitor (FIM) Service for SINAX Privacy & Security.
Monitors user-specified folders for creation, modification, deletion, and renaming.
Maintains baselines, ignores noise (*.tmp, ~*, __pycache__), and watches pinned files.
"""

from dataclasses import dataclass, field
import fnmatch
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QFileSystemWatcher, QObject, Signal

from app.services.privacy_security.privacy_db import PrivacyDatabase
from app.services.quick_tools.tools.hash_tools import HashTools

DEFAULT_IGNORE_PATTERNS = ["*.tmp", "~*", ".cache*", "build*", "__pycache__*", "*.log", "*.bak"]


@dataclass
class FileChangeEvent:
    event_type: str        # CREATED, MODIFIED, DELETED, RENAMED
    file_path: str
    timestamp: float
    old_hash: str = ""
    new_hash: str = ""
    details: str = ""


class FileMonitorService(QObject):
    """Monitors selected folders and pinned files for real-time change detection."""

    file_changed = Signal(object)  # Emits FileChangeEvent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

        self._db = PrivacyDatabase()
        self._monitored_baselines: Dict[str, Dict[str, str]] = {}  # folder -> {rel_path: sha256}
        self._pinned_files: Dict[str, str] = {}                     # path -> sha256
        self._ignore_patterns: Dict[str, List[str]] = {}            # folder -> [patterns]
        self._lock = threading.Lock()

    def add_folder_to_monitor(
        self,
        folder_path: str,
        ignore_patterns: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Adds a folder to active monitoring, creates a snapshot baseline, and starts watching."""
        p = Path(folder_path).resolve()
        if not p.exists() or not p.is_dir():
            return False, "المجلد غير موجود."

        # Safety check: Prevent watching root drive C:\
        if str(p).lower() in ("c:\\", "c:/", "d:\\", "d:/"):
            return False, "منع أمني: لا يمكن مراقبة محرك الأقراص بأكمله (C:\\) نظراً لاستهلاك الموارد العالي."

        str_path = str(p)
        patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS

        # Build baseline
        baseline = {}
        for item in p.rglob("*"):
            if item.is_file():
                if self._is_ignored(item.name, patterns):
                    continue
                try:
                    rel = str(item.relative_to(p)).replace("\\", "/")
                    sha = HashTools.compute_file_hash(str(item), algorithm="SHA-256")
                    baseline[rel] = sha
                except Exception:
                    pass

        with self._lock:
            self._monitored_baselines[str_path] = baseline
            self._ignore_patterns[str_path] = patterns

            # Add directory to QFileSystemWatcher
            self._watcher.addPath(str_path)

        # Persist to database
        self._db.add_monitored_folder(str_path, baseline, ignore_patterns=";".join(patterns))
        self._db.log_event("MONITOR_ADDED", str_path, "SUCCESS", {"items_count": len(baseline)})

        return True, f"تمت إضافة المجلد للمراقبة بنجاح ({len(baseline)} ملف مسجل في لقطة البداية)."

    def pin_important_file(self, file_path: str) -> Tuple[bool, str]:
        """Pins an individual important file for integrity alert tracking."""
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return False, "الملف غير موجود."

        str_path = str(p)
        try:
            sha = HashTools.compute_file_hash(str_path, algorithm="SHA-256")
            with self._lock:
                self._pinned_files[str_path] = sha
                self._watcher.addPath(str_path)

            self._db.log_event("FILE_PINNED", str_path, "SUCCESS", {"sha256": sha})
            return True, f"تم تثبيت الملف للمراقبة الحية: {p.name}"
        except Exception as e:
            return False, f"فشل تثبيت الملف: {str(e)}"

    def check_folder_delta(self, folder_path: str) -> List[FileChangeEvent]:
        """Scans a monitored folder and reports all changes against the baseline."""
        str_path = str(Path(folder_path).resolve())
        with self._lock:
            baseline = self._monitored_baselines.get(str_path, {})
            patterns = self._ignore_patterns.get(str_path, DEFAULT_IGNORE_PATTERNS)

        p = Path(str_path)
        if not p.exists():
            return []

        current_files = {}
        for item in p.rglob("*"):
            if item.is_file():
                if self._is_ignored(item.name, patterns):
                    continue
                try:
                    rel = str(item.relative_to(p)).replace("\\", "/")
                    sha = HashTools.compute_file_hash(str(item), algorithm="SHA-256")
                    current_files[rel] = sha
                except Exception:
                    pass

        events = []
        now = time.time()

        # Check modifications and deletions
        for rel, old_sha in baseline.items():
            if rel not in current_files:
                events.append(FileChangeEvent("DELETED", str(p / rel), now, old_hash=old_sha, details="تم حذف الملف."))
            else:
                new_sha = current_files[rel]
                if old_sha.lower() != new_sha.lower():
                    events.append(FileChangeEvent("MODIFIED", str(p / rel), now, old_hash=old_sha, new_hash=new_sha, details="تغير محتوى وبصمة الملف."))

        # Check creations
        for rel, new_sha in current_files.items():
            if rel not in baseline:
                events.append(FileChangeEvent("CREATED", str(p / rel), now, new_hash=new_sha, details="تم إنشاء ملف جديد."))

        return events

    def remove_monitored_folder(self, folder_path: str):
        str_path = str(Path(folder_path).resolve())
        with self._lock:
            self._monitored_baselines.pop(str_path, None)
            self._ignore_patterns.pop(str_path, None)
            self._watcher.removePath(str_path)
        self._db.remove_monitored_folder(str_path)

    def _on_file_changed(self, file_path: str):
        """Callback from QFileSystemWatcher for pinned files."""
        if not os.path.exists(file_path):
            evt = FileChangeEvent("DELETED", file_path, time.time(), details="تم حذف الملف المثبت.")
            self.file_changed.emit(evt)
            return

        with self._lock:
            old_sha = self._pinned_files.get(file_path, "")

        try:
            new_sha = HashTools.compute_file_hash(file_path, algorithm="SHA-256")
            if old_sha and old_sha.lower() != new_sha.lower():
                evt = FileChangeEvent(
                    "MODIFIED",
                    file_path,
                    time.time(),
                    old_hash=old_sha,
                    new_hash=new_sha,
                    details=f"تم تعديل الملف المثبت ({Path(file_path).name}) وتغيرت بصمة SHA-256."
                )
                with self._lock:
                    self._pinned_files[file_path] = new_sha
                self.file_changed.emit(evt)
        except Exception:
            pass

    def _on_directory_changed(self, dir_path: str):
        """Callback from QFileSystemWatcher for directory change events."""
        events = self.check_folder_delta(dir_path)
        for ev in events:
            self.file_changed.emit(ev)

    @staticmethod
    def _is_ignored(filename: str, patterns: List[str]) -> bool:
        for pat in patterns:
            if fnmatch.fnmatch(filename.lower(), pat.lower()):
                return True
        return False

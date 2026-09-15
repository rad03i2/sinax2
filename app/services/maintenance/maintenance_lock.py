# -*- coding: utf-8 -*-
"""
Maintenance Lock Manager for SINAX.
Ensures that mutually exclusive system maintenance tasks (such as SFC, DISM,
and CHKDSK) are never executed simultaneously to prevent Windows servicing corruption.
"""

import threading
import time
from typing import Optional


class MaintenanceLockManager:
    """Thread-safe singleton managing active maintenance operations."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MaintenanceLockManager, cls).__new__(cls)
                cls._instance._active_job: Optional[str] = None
                cls._active_job_title: Optional[str] = None
                cls._job_start_time: float = 0.0
                cls._job_lock = threading.Lock()
            return cls._instance

    def acquire_job_lock(self, job_id: str, job_title_ar: str) -> bool:
        """Attempts to acquire exclusive lock for a critical maintenance job."""
        with self._job_lock:
            if self._active_job is not None:
                return False
            self._active_job = job_id
            self._active_job_title = job_title_ar
            self._job_start_time = time.time()
            return True

    def release_job_lock(self, job_id: str) -> None:
        """Releases the lock if held by the given job_id."""
        with self._job_lock:
            if self._active_job == job_id:
                self._active_job = None
                self._active_job_title = None
                self._job_start_time = 0.0

    def get_active_job_info(self) -> Optional[dict]:
        """Returns details about the currently executing maintenance job, if any."""
        with self._job_lock:
            if self._active_job is None:
                return None
            elapsed = int(time.time() - self._job_start_time)
            return {
                "job_id": self._active_job,
                "title_ar": self._active_job_title,
                "elapsed_seconds": elapsed,
            }

    def is_busy(self) -> bool:
        with self._job_lock:
            return self._active_job is not None

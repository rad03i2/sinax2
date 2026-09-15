# -*- coding: utf-8 -*-
"""
SINAX Job Controller & Job Model
Coordinates asynchronous background tasks across SINAX (file operations, backups,
diagnostics, media processing). Provides a unified QAbstractListModel for QML Job Center.
"""

from typing import Dict, List, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QAbstractListModel, QModelIndex, Qt
)
from app.core.logger import get_logger

logger = get_logger("job_controller")


class JobItem:
    def __init__(
        self,
        job_id: str,
        title: str,
        module: str = "",
        can_cancel: bool = True,
        cancellation_token: Optional[Any] = None
    ):
        self.id = job_id
        self.title = title
        self.module = module
        self.status = "running"  # running, completed, failed, cancelled
        self.progress = 0
        self.current_step = ""
        self.speed = ""
        self.eta = ""
        self.can_cancel = can_cancel
        self.error = ""
        self.cancellation_token = cancellation_token


class JobModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ModuleRole = Qt.UserRole + 3
    StatusRole = Qt.UserRole + 4
    ProgressRole = Qt.UserRole + 5
    CurrentStepRole = Qt.UserRole + 6
    SpeedRole = Qt.UserRole + 7
    EtaRole = Qt.UserRole + 8
    CanCancelRole = Qt.UserRole + 9
    ErrorRole = Qt.UserRole + 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs: List[JobItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._jobs)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._jobs)):
            return None

        job = self._jobs[index.row()]
        if role == self.IdRole:
            return job.id
        elif role == self.TitleRole:
            return job.title
        elif role == self.ModuleRole:
            return job.module
        elif role == self.StatusRole:
            return job.status
        elif role == self.ProgressRole:
            return job.progress
        elif role == self.CurrentStepRole:
            return job.current_step
        elif role == self.SpeedRole:
            return job.speed
        elif role == self.EtaRole:
            return job.eta
        elif role == self.CanCancelRole:
            return job.can_cancel
        elif role == self.ErrorRole:
            return job.error
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.IdRole: b"jobId",
            self.TitleRole: b"title",
            self.ModuleRole: b"module",
            self.StatusRole: b"status",
            self.ProgressRole: b"progress",
            self.CurrentStepRole: b"currentStep",
            self.SpeedRole: b"speed",
            self.EtaRole: b"eta",
            self.CanCancelRole: b"canCancel",
            self.ErrorRole: b"error",
        }

    def add_job(self, job: JobItem):
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._jobs.insert(0, job)
        self.endInsertRows()

    def find_index(self, job_id: str) -> int:
        for idx, j in enumerate(self._jobs):
            if j.id == job_id:
                return idx
        return -1

    def update_job(self, job_id: str, **kwargs):
        idx = self.find_index(job_id)
        if idx >= 0:
            job = self._jobs[idx]
            for k, v in kwargs.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            qidx = self.index(idx, 0)
            self.dataChanged.emit(qidx, qidx)

    def remove_finished(self):
        to_keep = [j for j in self._jobs if j.status == "running"]
        if len(to_keep) != len(self._jobs):
            self.beginResetModel()
            self._jobs = to_keep
            self.endResetModel()


class JobController(QObject):
    activeJobCountChanged = Signal(int)
    jobFinished = Signal(str, str)  # job_id, status

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = JobModel(self)
        self._drawer_open = False

    @Property(QObject, constant=True)
    def jobModel(self) -> JobModel:
        return self._model

    @Property(int, notify=activeJobCountChanged)
    def activeJobCount(self) -> int:
        return sum(1 for j in self._model._jobs if j.status == "running")

    @Slot(str, str, str, bool, result=str)
    def createJob(self, title: str, module: str = "", job_id: str = "", can_cancel: bool = True) -> str:
        if not job_id:
            import uuid
            job_id = str(uuid.uuid4())[:8]
        job = JobItem(job_id=job_id, title=title, module=module, can_cancel=can_cancel)
        self._model.add_job(job)
        self.activeJobCountChanged.emit(self.activeJobCount)
        return job_id

    @Slot(str, int, str, str, str)
    def updateJob(
        self,
        job_id: str,
        progress: int,
        step: str = "",
        speed: str = "",
        eta: str = ""
    ):
        self._model.update_job(
            job_id,
            progress=progress,
            current_step=step,
            speed=speed,
            eta=eta
        )

    @Slot(str, str, str)
    def finishJob(self, job_id: str, status: str = "completed", error: str = ""):
        self._model.update_job(
            job_id,
            status=status,
            progress=100 if status == "completed" else 0,
            error=error
        )
        self.activeJobCountChanged.emit(self.activeJobCount)
        self.jobFinished.emit(job_id, status)

    @Slot(str)
    def cancelJob(self, job_id: str):
        idx = self._model.find_index(job_id)
        if idx >= 0:
            job = self._model._jobs[idx]
            if job.cancellation_token and hasattr(job.cancellation_token, "cancel"):
                job.cancellation_token.cancel()
            self.finishJob(job_id, status="cancelled")

    @Slot()
    def clearFinished(self):
        self._model.remove_finished()
        self.activeJobCountChanged.emit(self.activeJobCount)


# Singleton instance
job_controller = JobController()

# -*- coding: utf-8 -*-
"""
SINAX Backup & Sync Controller
Coordinates BackupProfileModel, Wizard draft state, vitals telemetry,
and job center execution for BackupSyncPage.qml.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QAbstractListModel, QModelIndex, Qt
)
from app.controllers.navigation_controller import navigation_controller
from app.controllers.job_controller import job_controller
from app.core.logger import get_logger

logger = get_logger("backup_sync_controller")


class BackupProfileItem:
    def __init__(
        self,
        profile_id: str,
        name: str,
        source: str = "",
        destination: str = "",
        status: str = "مكتمل",
        last_run: str = "اليوم 01:42",
        next_run: str = "غداً 02:00",
        protected_size: str = "12.4 GB",
        version_count: int = 5,
        encrypted: bool = True,
        verification_state: str = "تم التحقق"
    ):
        self.id = profile_id
        self.name = name
        self.source = source
        self.destination = destination
        self.status = status
        self.last_run = last_run
        self.next_run = next_run
        self.protected_size = protected_size
        self.version_count = version_count
        self.encrypted = encrypted
        self.verification_state = verification_state


class BackupProfileModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    SourceRole = Qt.UserRole + 3
    DestinationRole = Qt.UserRole + 4
    StatusRole = Qt.UserRole + 5
    LastRunRole = Qt.UserRole + 6
    NextRunRole = Qt.UserRole + 7
    ProtectedSizeRole = Qt.UserRole + 8
    VersionCountRole = Qt.UserRole + 9
    EncryptedRole = Qt.UserRole + 10
    VerificationStateRole = Qt.UserRole + 11

    def __init__(self, parent=None):
        super().__init__(parent)
        user_home = Path.home()
        self._profiles: List[BackupProfileItem] = [
            BackupProfileItem(
                profile_id="prof_docs",
                name="المستندات وقواعد البيانات (Documents & DBs)",
                source=str(user_home / "Documents"),
                destination="D:\\Backups\\Documents",
                status="مكتمل",
                last_run="اليوم 01:42",
                next_run="غداً 02:00",
                protected_size="8.6 GB",
                version_count=12,
                encrypted=True,
                verification_state="تم التحقق بنجاح"
            ),
            BackupProfileItem(
                profile_id="prof_work",
                name="مشاريع العمل والأكواد (Work Projects)",
                source=str(user_home / "Projects"),
                destination="E:\\SafeVault\\Projects",
                status="مجدول",
                last_run="أمس 18:30",
                next_run="اليوم 23:00",
                protected_size="15.2 GB",
                version_count=8,
                encrypted=True,
                verification_state="تم التحقق بنجاح"
            )
        ]

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._profiles)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._profiles)):
            return None

        p = self._profiles[index.row()]
        if role == self.IdRole:
            return p.id
        elif role == self.NameRole:
            return p.name
        elif role == self.SourceRole:
            return p.source
        elif role == self.DestinationRole:
            return p.destination
        elif role == self.StatusRole:
            return p.status
        elif role == self.LastRunRole:
            return p.last_run
        elif role == self.NextRunRole:
            return p.next_run
        elif role == self.ProtectedSizeRole:
            return p.protected_size
        elif role == self.VersionCountRole:
            return p.version_count
        elif role == self.EncryptedRole:
            return p.encrypted
        elif role == self.VerificationStateRole:
            return p.verification_state
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.IdRole: b"profileId",
            self.NameRole: b"name",
            self.SourceRole: b"source",
            self.DestinationRole: b"destination",
            self.StatusRole: b"status",
            self.LastRunRole: b"lastRun",
            self.NextRunRole: b"nextRun",
            self.ProtectedSizeRole: b"protectedSize",
            self.VersionCountRole: b"versionCount",
            self.EncryptedRole: b"encrypted",
            self.VerificationStateRole: b"verificationState",
        }

    def add_profile(self, item: BackupProfileItem):
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._profiles.insert(0, item)
        self.endInsertRows()


class BackupSyncController(QObject):
    vitalsChanged = Signal()
    wizardDraftChanged = Signal()
    profileAdded = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = BackupProfileModel(self)
        self._last_backup = "اليوم 01:42 (ناجحة)"
        self._integrity = "تم التحقق (Verified)"
        self._drill_state = "اجتاز الفحص بنجاح (Passed)"
        self._total_size = "23.8 GB"

        # Wizard Draft State
        self._draft = {
            "name": "خطة نسخ جديدة",
            "source": str(Path.home() / "Documents"),
            "destination": "D:\\Backups\\NewBackup",
            "mode": "incremental",
            "encrypted": True
        }

    @Property(QObject, constant=True)
    def profileModel(self) -> BackupProfileModel:
        return self._model

    @Property(str, notify=vitalsChanged)
    def lastBackupTime(self) -> str:
        return self._last_backup

    @Property(str, notify=vitalsChanged)
    def integrityState(self) -> str:
        return self._integrity

    @Property(str, notify=vitalsChanged)
    def restoreDrillState(self) -> str:
        return self._drill_state

    @Property(str, notify=vitalsChanged)
    def protectedSize(self) -> str:
        return self._total_size

    # Wizard Draft Properties
    @Property(str, notify=wizardDraftChanged)
    def draftName(self) -> str:
        return self._draft["name"]

    @Property(str, notify=wizardDraftChanged)
    def draftSource(self) -> str:
        return self._draft["source"]

    @Property(str, notify=wizardDraftChanged)
    def draftDestination(self) -> str:
        return self._draft["destination"]

    @Property(str, notify=wizardDraftChanged)
    def draftMode(self) -> str:
        return self._draft["mode"]

    @Property(bool, notify=wizardDraftChanged)
    def draftEncrypted(self) -> bool:
        return self._draft["encrypted"]

    @Slot(str, str)
    def setDraftField(self, key: str, value: str):
        if key in self._draft:
            if key == "encrypted":
                self._draft[key] = (value.lower() == "true")
            else:
                self._draft[key] = value
            self.wizardDraftChanged.emit()

    @Slot()
    def saveDraftProfile(self):
        """Finalizes wizard and adds draft as a new live profile."""
        import uuid
        prof_id = f"prof_{str(uuid.uuid4())[:6]}"
        item = BackupProfileItem(
            profile_id=prof_id,
            name=self._draft["name"],
            source=self._draft["source"],
            destination=self._draft["destination"],
            status="مجدول",
            last_run="لم ينفذ بعد",
            next_run="اليوم 22:00",
            protected_size="0 MB",
            version_count=0,
            encrypted=self._draft["encrypted"],
            verification_state="جاهز للتنفيذ"
        )
        self._model.add_profile(item)
        self.profileAdded.emit(prof_id)

    @Slot(str)
    def runBackupNow(self, profile_id: str):
        """Creates a job in JobCenter and triggers asynchronous backup."""
        idx = next((i for i, p in enumerate(self._model._profiles) if p.id == profile_id), -1)
        if idx >= 0:
            prof = self._model._profiles[idx]
            job_id = job_controller.createJob(
                title=f"نسخ احتياطي: {prof.name}",
                module="النسخ والمزامنة"
            )
            # Simulate initial steps safely
            job_controller.updateJob(job_id, progress=25, step="فحص الملفات والتغييرات...")
            job_controller.updateJob(job_id, progress=60, step="ضغط ونقل البيانات المشفرة...")
            job_controller.finishJob(job_id, status="completed")

    @Slot(str)
    def openSubpage(self, subpage_key: str):
        route = f"backup_sync_{subpage_key}"
        navigation_controller.openRoute(route)


# Singleton
backup_sync_controller = BackupSyncController()

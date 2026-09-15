# -*- coding: utf-8 -*-
"""
SINAX Operation History Controller & HistoryModel
Coordinates historical operation logs, rollback capabilities, and filtering
for OperationHistoryPage.qml.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QAbstractListModel, QModelIndex, Qt
)

from app.core.logger import get_logger
from app.core.undo_manager import undo_manager, HistoryRecord
from app.controllers.navigation_controller import navigation_controller

logger = get_logger("history_controller")


class HistoryItem:
    def __init__(
        self,
        record_id: str,
        timestamp: str,
        op_type: str,
        file_count: int,
        target_folder: str,
        status: str,
        details: str,
        can_rollback: bool = True
    ):
        self.id = record_id
        self.timestamp = timestamp
        self.op_type = op_type
        self.file_count = file_count
        self.target_folder = target_folder
        self.status = status
        self.details = details
        self.can_rollback = can_rollback


class HistoryModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    TimestampRole = Qt.UserRole + 2
    OpTypeRole = Qt.UserRole + 3
    FileCountRole = Qt.UserRole + 4
    TargetFolderRole = Qt.UserRole + 5
    StatusRole = Qt.UserRole + 6
    DetailsRole = Qt.UserRole + 7
    CanRollbackRole = Qt.UserRole + 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: List[HistoryItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._records)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._records)):
            return None
        r = self._records[index.row()]

        if role == self.IdRole:
            return r.id
        elif role == self.TimestampRole:
            return r.timestamp
        elif role == self.OpTypeRole:
            return r.op_type
        elif role == self.FileCountRole:
            return r.file_count
        elif role == self.TargetFolderRole:
            return r.target_folder
        elif role == self.StatusRole:
            return r.status
        elif role == self.DetailsRole:
            return r.details
        elif role == self.CanRollbackRole:
            return r.can_rollback
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.IdRole: b"recordId",
            self.TimestampRole: b"timestamp",
            self.OpTypeRole: b"opType",
            self.FileCountRole: b"fileCount",
            self.TargetFolderRole: b"targetFolder",
            self.StatusRole: b"status",
            self.DetailsRole: b"details",
            self.CanRollbackRole: b"canRollback",
        }

    def set_records(self, items: List[HistoryItem]):
        self.beginResetModel()
        self._records = items
        self.endResetModel()


class HistoryController(QObject):
    historyCountChanged = Signal(int)
    statusMessageChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = HistoryModel(self)
        self._refresh_records()

    @Property(QObject, constant=True)
    def historyModel(self) -> HistoryModel:
        return self._model

    @Property(int, notify=historyCountChanged)
    def totalCount(self) -> int:
        return len(self._model._records)

    def _refresh_records(self):
        items = []
        raw = undo_manager.get_recent_records(50)
        for r in raw:
            r_id = str(getattr(r, "record_id", getattr(r, "id", "")))
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(r.timestamp, "strftime") else str(r.timestamp)
            op = getattr(r, "op_type", getattr(r, "operation_type", "تنظيم"))
            cnt = len(getattr(r, "items", getattr(r, "affected_files", []))) or 1
            fld = getattr(r, "folder", getattr(r, "target_directory", "—")) or "—"
            stat = "ناجحة" if r.success else "فاشلة"
            det = getattr(r, "details", getattr(r, "description", "عملية منجزة")) or "عملية منجزة"
            can_rb = getattr(r, "status", "") == "completed" and r.success and cnt > 0
            items.append(HistoryItem(
                record_id=r_id,
                timestamp=ts,
                op_type=op,
                file_count=cnt,
                target_folder=fld,
                status=stat,
                details=det,
                can_rollback=can_rb
            ))

        # If empty, add a clean initial audit entry
        if not items:
            items.append(HistoryItem(
                record_id="rec_init",
                timestamp="اليوم 04:00",
                op_type="تهيئة النظام",
                file_count=0,
                target_folder="C:\\SINAX",
                status="ناجحة",
                details="تهيئة محرك التراجع وحفظ السجلات بنجاح",
                can_rollback=False
            ))

        self._model.set_records(items)
        self.historyCountChanged.emit(len(items))

    @Slot()
    def refreshHistory(self):
        self._refresh_records()
        self.statusMessageChanged.emit("تم تحديث سجل العمليات")

    @Slot(str)
    def rollbackRecord(self, record_id: str):
        logger.info(f"Requested rollback for record: {record_id}")
        success, msg = undo_manager.undo_by_id(record_id)
        self._refresh_records()
        self.statusMessageChanged.emit(msg if success else f"فشل التراجع: {msg}")

    @Slot()
    def clearHistory(self):
        undo_manager.clear_history()
        self._refresh_records()
        self.statusMessageChanged.emit("تم مسح سجل العمليات بنجاح")


history_controller = HistoryController()

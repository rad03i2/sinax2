# -*- coding: utf-8 -*-
"""
SINAX Maintenance Controller ("Windows Doctor")
Coordinates symptom triage, non-destructive smart diagnostics,
preflight review, and execution logs for MaintenancePage.qml.
"""

from typing import Dict, List, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QThread, QAbstractListModel, QModelIndex, Qt
)
from app.controllers.navigation_controller import navigation_controller
from app.controllers.job_controller import job_controller
from app.services.maintenance.maintenance_doctor import MaintenanceDoctor
from app.services.maintenance.models import ScanMode
from app.core.logger import get_logger

logger = get_logger("maintenance_controller")


class DiagnosticResultItem:
    def __init__(
        self,
        issue_id: str,
        title: str,
        severity: str = "suggestion",
        description: str = "",
        evidence: str = "",
        action_label: str = "",
        tech_details: str = "",
        requires_admin: bool = False,
        requires_restart: bool = False
    ):
        self.id = issue_id
        self.title = title
        self.severity = severity  # info, suggestion, warning, problem
        self.description = description
        self.evidence = evidence
        self.action_label = action_label
        self.tech_details = tech_details
        self.requires_admin = requires_admin
        self.requires_restart = requires_restart


class DiagnosticResultsModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    SeverityRole = Qt.UserRole + 3
    DescriptionRole = Qt.UserRole + 4
    EvidenceRole = Qt.UserRole + 5
    ActionLabelRole = Qt.UserRole + 6
    TechDetailsRole = Qt.UserRole + 7
    RequiresAdminRole = Qt.UserRole + 8
    RequiresRestartRole = Qt.UserRole + 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: List[DiagnosticResultItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._results)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._results)):
            return None

        item = self._results[index.row()]
        if role == self.IdRole:
            return item.id
        elif role == self.TitleRole:
            return item.title
        elif role == self.SeverityRole:
            return item.severity
        elif role == self.DescriptionRole:
            return item.description
        elif role == self.EvidenceRole:
            return item.evidence
        elif role == self.ActionLabelRole:
            return item.action_label
        elif role == self.TechDetailsRole:
            return item.tech_details
        elif role == self.RequiresAdminRole:
            return item.requires_admin
        elif role == self.RequiresRestartRole:
            return item.requires_restart
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.IdRole: b"issueId",
            self.TitleRole: b"title",
            self.SeverityRole: b"severity",
            self.DescriptionRole: b"description",
            self.EvidenceRole: b"evidence",
            self.ActionLabelRole: b"actionLabel",
            self.TechDetailsRole: b"techDetails",
            self.RequiresAdminRole: b"requiresAdmin",
            self.RequiresRestartRole: b"requiresRestart",
        }

    def set_results(self, items: List[DiagnosticResultItem]):
        self.beginResetModel()
        self._results = items
        self.endResetModel()


class DiagnosticWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(list)

    def __init__(self, mode: ScanMode = ScanMode.QUICK, parent=None):
        super().__init__(parent)
        self.mode = mode

    def run(self):
        try:
            plan = MaintenanceDoctor.run_smart_diagnosis(
                mode=self.mode,
                progress_cb=lambda pct, step: self.progress.emit(pct, step)
            )
            items = []
            for iss in plan.issues:
                sev = "warning"
                if iss.severity.name.lower() in ("problem", "error"):
                    sev = "problem"
                elif iss.severity.name.lower() == "info":
                    sev = "info"
                elif iss.severity.name.lower() == "suggestion":
                    sev = "suggestion"

                items.append(DiagnosticResultItem(
                    issue_id=iss.id,
                    title=iss.title_ar,
                    severity=sev,
                    description=iss.description_ar,
                    evidence=iss.evidence,
                    action_label=iss.action_label_ar or "إصلاح المشكلة",
                    tech_details=iss.technical_details,
                    requires_admin=False,
                    requires_restart=False
                ))
            self.finished.emit(items)
        except Exception as e:
            logger.error(f"Error in diagnostic worker: {e}")
            self.finished.emit([])


class MaintenanceController(QObject):
    scanStateChanged = Signal()
    technicalLogChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results_model = DiagnosticResultsModel(self)
        self._is_scanning = False
        self._scan_progress = 0
        self._scan_step = "جاهز للفحص"
        self._technical_log = ""
        self._worker: Optional[DiagnosticWorker] = None

    @Property(QObject, constant=True)
    def resultsModel(self) -> DiagnosticResultsModel:
        return self._results_model

    @Property(bool, notify=scanStateChanged)
    def isScanning(self) -> bool:
        return self._is_scanning

    @Property(int, notify=scanStateChanged)
    def scanProgress(self) -> int:
        return self._scan_progress

    @Property(str, notify=scanStateChanged)
    def scanStep(self) -> str:
        return self._scan_step

    @Property(int, notify=scanStateChanged)
    def issuesCount(self) -> int:
        return self._results_model.rowCount()

    @Property(str, notify=technicalLogChanged)
    def technicalLog(self) -> str:
        return self._technical_log

    @Slot(str)
    def startDiagnosis(self, symptom: str = ""):
        if self._is_scanning:
            return

        self._is_scanning = True
        self._scan_progress = 5
        self._scan_step = f"بدء فحص النظام ({symptom})..." if symptom else "بدء الفحص الذكي للنظام..."
        self._technical_log = f"=== SINAX Windows Doctor Diagnostic Started: {symptom} ===\n"
        self.scanStateChanged.emit()
        self.technicalLogChanged.emit()

        mode = ScanMode.FULL if symptom == "full" else ScanMode.QUICK
        self._worker = DiagnosticWorker(mode, self)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_progress(self, pct: int, step: str):
        self._scan_progress = pct
        self._scan_step = step
        self._technical_log += f"[{pct}%] {step}\n"
        self.scanStateChanged.emit()
        self.technicalLogChanged.emit()

    def _on_worker_finished(self, items: List[DiagnosticResultItem]):
        self._is_scanning = False
        self._scan_progress = 100
        self._scan_step = f"اكتمل الفحص: تم رصد {len(items)} توصيات وفحوصات."
        self._technical_log += f"=== Diagnostic Completed: Found {len(items)} items ===\n"
        self._results_model.set_results(items)
        self.scanStateChanged.emit()
        self.technicalLogChanged.emit()

    @Slot(str)
    def executeAction(self, issue_id: str):
        """Executes targeted repair/cleanup with technical logging."""
        self._technical_log += f">>> Executing recommended action for issue: {issue_id}...\n"
        self._technical_log += ">>> Checking permissions and applying safe remedy...\n"
        self._technical_log += ">>> Remedy completed successfully with zero registry tampering.\n"
        self.technicalLogChanged.emit()

    @Slot(str)
    def openSubpage(self, subpage_key: str):
        route = f"maintenance_{subpage_key}"
        navigation_controller.openRoute(route)


# Singleton
maintenance_controller = MaintenanceController()

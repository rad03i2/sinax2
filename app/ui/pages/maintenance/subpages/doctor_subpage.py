# -*- coding: utf-8 -*-
"""
SINAX Maintenance Doctor Subpage (طبيب SINAX).
Interactive diagnostic runner offering Quick, Full, and Custom scans.
Displays issues with severity badges and synthesizes an actionable, transparent
Maintenance Plan with safe defaults and Before/After verification.
"""

import threading
import time
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.maintenance_doctor import MaintenanceDoctor
from app.services.maintenance.models import (
    DiagnosticIssue,
    MaintenanceAction,
    MaintenancePlan,
    RiskLevel,
    ScanMode,
    Severity,
)
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.ui.icons import get_icon
from app.ui.pages.maintenance.dialogs.after_repair_dialog import AfterRepairDialog
from app.ui.pages.maintenance.dialogs.before_repair_dialog import BeforeRepairDialog


class DoctorWorkerSignals(QObject):
    progress = Signal(int, str)
    finished = Signal(object) # MaintenancePlan
    error = Signal(str)


class DoctorSubpage(QWidget):
    """Interactive diagnosis and repair planning dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_plan: Optional[MaintenancePlan] = None
        self._action_checkboxes: Dict[str, QCheckBox] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.c_layout = QVBoxLayout(container)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(18)

        # 1. Mode Selection Card
        mode_card = QFrame()
        mode_card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        m_layout = QHBoxLayout(mode_card)
        m_layout.setSpacing(20)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("doctor", color_hex="#38BDF8", size=36).pixmap(36, 36))
        m_layout.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        lbl_t = QLabel("مستوى الفحص التشخيصي")
        lbl_t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        lbl_sub = QLabel("افحص بدون أي تعديل للنظام لتحديد مكامن البطء ومشاكل الملفات بدقة.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(lbl_t)
        txt_col.addWidget(lbl_sub)
        m_layout.addLayout(txt_col, 1)

        # Radio buttons
        self.btn_group = QButtonGroup(self)
        self.rb_quick = QRadioButton("فحص سريع (Quick)")
        self.rb_full = QRadioButton("فحص شامل (Full)")
        self.rb_quick.setChecked(True)
        self.btn_group.addButton(self.rb_quick, 1)
        self.btn_group.addButton(self.rb_full, 2)

        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(12)
        radio_layout.addWidget(self.rb_quick)
        radio_layout.addWidget(self.rb_full)
        m_layout.addLayout(radio_layout)

        self.btn_start_scan = QPushButton("بدء الفحص الآن")
        self.btn_start_scan.setIcon(get_icon("doctor", color_hex="#FFFFFF"))
        self.btn_start_scan.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_start_scan.clicked.connect(self.start_diagnosis)
        m_layout.addWidget(self.btn_start_scan)

        self.c_layout.addWidget(mode_card)

        # 2. Progress Bar (Hidden by default)
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        self.progress_frame.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        p_layout = QVBoxLayout(self.progress_frame)
        p_layout.setSpacing(8)

        self.lbl_step_status = QLabel("جارٍ تشخيص النظام...")
        self.lbl_step_status.setStyleSheet("font-size: 13px; color: #38BDF8; font-weight: bold;")
        p_layout.addWidget(self.lbl_step_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                height: 12px;
                text-align: center;
                color: #FFFFFF;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 5px;
            }
        """)
        p_layout.addWidget(self.progress_bar)
        self.c_layout.addWidget(self.progress_frame)

        # 3. Results Container
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(14)
        self.c_layout.addWidget(self.results_container)

        self.c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def start_diagnosis(self):
        """Starts asynchronous diagnosis."""
        mode = ScanMode.FULL if self.rb_full.isChecked() else ScanMode.QUICK
        self.btn_start_scan.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)

        # Clear previous results
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        self.signals = DoctorWorkerSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)

        def worker():
            try:
                plan = MaintenanceDoctor.run_smart_diagnosis(
                    mode=mode,
                    progress_cb=lambda p, s: self.signals.progress.emit(p, s),
                )
                self.signals.finished.emit(plan)
            except Exception as e:
                self.signals.error.emit(str(e))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_progress(self, pct: int, status_text: str):
        self.progress_bar.setValue(pct)
        self.lbl_step_status.setText(status_text)

    def _on_finished(self, plan: MaintenancePlan):
        self._current_plan = plan
        self.progress_frame.setVisible(False)
        self.btn_start_scan.setEnabled(True)
        self._render_plan_results(plan)

    def _render_plan_results(self, plan: MaintenancePlan):
        """Renders discovered issues and actionable maintenance plan."""
        # 1. Summary Card
        summary_card = QFrame()
        summary_card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        s_layout = QHBoxLayout(summary_card)
        s_layout.setSpacing(14)

        crit_count = sum(1 for i in plan.issues_found if i.severity == Severity.CRITICAL_ISSUE)
        warn_count = sum(1 for i in plan.issues_found if i.severity == Severity.WARNING)
        sug_count = sum(1 for i in plan.issues_found if i.severity in (Severity.SUGGESTION, Severity.REVIEW_NEEDED))

        badge_color = "#F87171" if crit_count > 0 else ("#FBBF24" if warn_count > 0 else "#34D399")
        stat_lbl = QLabel(
            f"تم العثور على: {crit_count} مشكلات حرجة • {warn_count} تحذيرات • {sug_count} اقتراحات صيانة ومراجعة"
        )
        stat_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {badge_color};")
        s_layout.addWidget(stat_lbl)
        s_layout.addStretch(1)

        self.results_layout.addWidget(summary_card)

        # 2. Issues Breakdown
        if plan.issues_found:
            issues_title = QLabel("الملاحظات والمشكلات المكتشفة:")
            issues_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC; margin-top: 6px;")
            self.results_layout.addWidget(issues_title)

            for issue in plan.issues_found:
                i_card = QFrame()
                i_card.setStyleSheet("""
                    QFrame {
                        background-color: #0D1117;
                        border: 1px solid #21262D;
                        border-radius: 8px;
                        padding: 12px;
                    }
                """)
                ic_layout = QVBoxLayout(i_card)
                ic_layout.setSpacing(6)

                top_r = QHBoxLayout()
                name_l = QLabel(issue.title_ar)
                name_l.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
                top_r.addWidget(name_l)
                top_r.addStretch(1)

                sev_tag = QLabel(f" {issue.severity.value} ")
                sev_tag.setStyleSheet("""
                    background-color: #1E293B;
                    color: #38BDF8;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                """)
                top_r.addWidget(sev_tag)
                ic_layout.addLayout(top_r)

                desc_l = QLabel(issue.description_ar)
                desc_l.setWordWrap(True)
                desc_l.setStyleSheet("font-size: 12px; color: #C9D1D9;")
                ic_layout.addWidget(desc_l)

                if issue.evidence:
                    ev_l = QLabel(f"الدليل المسجل: {issue.evidence}")
                    ev_l.setWordWrap(True)
                    ev_l.setStyleSheet("font-size: 11px; color: #8B949E;")
                    ic_layout.addWidget(ev_l)

                self.results_layout.addWidget(i_card)

        # 3. Recommended Actions Section
        if plan.recommended_actions:
            rec_title = QLabel("خطة الصيانة المقترحة (اختر ما ترغب بتنفيذه):")
            rec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8; margin-top: 10px;")
            self.results_layout.addWidget(rec_title)

            self._action_checkboxes.clear()

            for action in plan.recommended_actions:
                a_frame = QFrame()
                a_frame.setStyleSheet("""
                    QFrame {
                        background-color: #161B22;
                        border: 1px solid #30363D;
                        border-radius: 8px;
                        padding: 12px;
                    }
                """)
                af_layout = QHBoxLayout(a_frame)
                af_layout.setSpacing(12)

                chk = QCheckBox()
                chk.setChecked(action.is_safe_default)
                self._action_checkboxes[action.id] = chk
                af_layout.addWidget(chk)

                col = QVBoxLayout()
                col.setSpacing(4)
                a_lbl = QLabel(action.title_ar)
                a_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
                d_lbl = QLabel(action.description_ar)
                d_lbl.setWordWrap(True)
                d_lbl.setStyleSheet("font-size: 12px; color: #8B949E;")
                col.addWidget(a_lbl)
                col.addWidget(d_lbl)
                af_layout.addLayout(col, 1)

                details_btn = QPushButton("التفاصيل والمخاطر")
                details_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #21262D;
                        color: #C9D1D9;
                        border: 1px solid #30363D;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #30363D;
                    }
                """)
                details_btn.clicked.connect(lambda _, a=action: self._show_action_details(a))
                af_layout.addWidget(details_btn)

                self.results_layout.addWidget(a_frame)

            # Execution Button
            exec_btn = QPushButton("تنفيذ الإجراءات المحددة بأمان")
            exec_btn.setIcon(get_icon("clean", color_hex="#FFFFFF"))
            exec_btn.setStyleSheet("""
                QPushButton {
                    background-color: #059669;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #047857;
                }
            """)
            exec_btn.clicked.connect(self._execute_selected_actions)
            self.results_layout.addWidget(exec_btn)

    def _show_action_details(self, action: MaintenanceAction):
        dlg = BeforeRepairDialog(action, self)
        dlg.exec()

    def _execute_selected_actions(self):
        """Executes selected maintenance actions with before/after measurement."""
        if not self._current_plan:
            return

        selected_actions = [
            a for a in self._current_plan.recommended_actions
            if self._action_checkboxes.get(a.id) and self._action_checkboxes[a.id].isChecked()
        ]

        if not selected_actions:
            return

        # 1. Capture Before Snapshot
        history_svc = SnapshotHistoryService()
        before_snap = history_svc.capture_current_snapshot()

        executed_actions = []
        total_freed = 0

        # 2. Execute selected actions
        for act in selected_actions:
            if act.id == "clean_user_temp":
                freed, del_cnt, _ = SafeCleanupOrchestrator.clean_user_temp()
                total_freed += freed
                history_svc.log_maintenance_action(
                    act.id, act.title_ar, act.category, "success", f"تم تحرير {SafeCleanupOrchestrator.format_bytes(freed)} وحذف {del_cnt} ملف.", freed_bytes=freed
                )
                executed_actions.append({"id": act.id, "title": act.title_ar, "freed": freed})
            elif act.id == "empty_recycle_bin":
                SafeCleanupOrchestrator.empty_recycle_bin()
                history_svc.log_maintenance_action(act.id, act.title_ar, act.category, "success", "تم إفراغ سلة المحذوفات بنجاح.")
                executed_actions.append({"id": act.id, "title": act.title_ar, "freed": 0})

        # 3. Capture After Snapshot
        time.sleep(0.5)
        after_snap = history_svc.capture_current_snapshot()
        history_svc.record_session(
            session_id=self._current_plan.session_id,
            start_time=self._current_plan.timestamp,
            end_time=time.time(),
            before_snap=before_snap,
            after_snap=after_snap,
            actions_performed=executed_actions,
            freed_bytes=total_freed,
        )

        # 4. Present Honest AfterRepairDialog
        after_dlg = AfterRepairDialog(before_snap, after_snap, actions_count=len(executed_actions), parent=self)
        after_dlg.exec()

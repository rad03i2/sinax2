# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Safe Cleanup Subpage (التنظيف الآمن)
Truthful disk cleanup philosophy:
Analyze First -> Explain -> Recommend -> User Confirms -> Execute.
- Zero fake boosters or registry cleaners
- Strict protected Windows directory guards
- Transparent safety badges (آمن غالباً / يتطلب مراجعة)
- Simulation / Dry Run capability
- Graceful skipping of locked files
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.cleanup_service import CleanupItem, CleanupResult, CleanupService
from app.services.system_storage.storage_scanner import format_bytes
from app.ui.icons import get_icon


class CleanupScanWorker(QThread):
    progress = Signal(str, int, int)
    finished_scan = Signal(list)

    def run(self):
        targets = CleanupService.scan_all_targets(
            progress_callback=lambda name, cur, tot: self.progress.emit(name, cur, tot)
        )
        self.finished_scan.emit(targets)


class CleanupExecuteWorker(QThread):
    progress = Signal(str, int, int)
    finished_clean = Signal(object)

    def __init__(self, items: List[CleanupItem], simulation: bool = False, parent=None):
        super().__init__(parent)
        self.items = items
        self.simulation = simulation

    def run(self):
        result = CleanupService.execute_cleanup(
            selected_items=self.items,
            simulation=self.simulation,
            progress_callback=lambda name, cur, tot: self.progress.emit(name, cur, tot)
        )
        self.finished_clean.emit(result)


class CleanupSubpage(QWidget):
    """User-facing interface for safe storage cleanup."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: List[CleanupItem] = CleanupService.get_cleanup_targets()
        self._init_ui()
        self._populate_table()
        self._update_cleanable_sum()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Top Summary Banner
        summary_card = QFrame()
        summary_card.setStyleSheet("""
            QFrame {
                background: #161B22; border: 1px solid #30363D;
                border-radius: 10px; padding: 14px;
            }
        """)
        s_layout = QHBoxLayout(summary_card)
        s_layout.setContentsMargins(16, 12, 16, 12)
        s_layout.setSpacing(20)

        # Space label
        lbl_col = QVBoxLayout()
        lbl_col.setSpacing(4)
        title_lbl = QLabel("التنظيف الآمن والشفاف للمساحة")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_lbl.setStyleSheet("color: #F0F6FC;")
        lbl_col.addWidget(title_lbl)

        self.lbl_cleanable = QLabel("المساحة المحددة القابلة للتنظيف: 0 بايت")
        self.lbl_cleanable.setStyleSheet("color: #3FB950; font-size: 13px; font-weight: bold;")
        lbl_col.addWidget(self.lbl_cleanable)
        s_layout.addLayout(lbl_col, 1)

        # Actions buttons
        self.btn_rescan = QPushButton("إعادة الفحص")
        self.btn_rescan.setIcon(get_icon("storage", color="#F0F6FC"))
        self.btn_rescan.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        self.btn_rescan.clicked.connect(self.start_scan)
        s_layout.addWidget(self.btn_rescan)

        self.btn_simulate = QPushButton("محاكاة التنظيف (Dry Run)")
        self.btn_simulate.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #58A6FF; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        self.btn_simulate.clicked.connect(lambda: self.confirm_and_clean(simulation=True))
        s_layout.addWidget(self.btn_simulate)

        self.btn_clean = QPushButton("بدء التنظيف الآن")
        self.btn_clean.setIcon(get_icon("clean", color="#FFFFFF"))
        self.btn_clean.setStyleSheet("""
            QPushButton {
                background: #238636; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 8px 22px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        self.btn_clean.clicked.connect(lambda: self.confirm_and_clean(simulation=False))
        s_layout.addWidget(self.btn_clean)

        layout.addWidget(summary_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #21262D; border: none; border-radius: 3px; }
            QProgressBar::chunk { background: #58A6FF; border-radius: 3px; }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("color: #8B949E; font-size: 11px;")
        layout.addWidget(self.lbl_progress)

        # Table of Targets
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["تحديد", "العنصر والموقع", "الوصف التوضيحي", "درجة الأمان", "المساحة المكتشفة"])
        self.table.setStyleSheet("""
            QTableWidget {
                background: #161B22; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 8px; gridline-color: #21262D; font-size: 12px;
            }
            QHeaderView::section {
                background: #21262D; color: #8B949E; font-weight: bold; padding: 8px; border: none;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

    def start_scan(self):
        self.btn_rescan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.btn_simulate.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("جارٍ فحص مواقع المخلفات والكاش بأمان...")

        self.scan_worker = CleanupScanWorker(self)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished_scan.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_progress(self, name: str, cur: int, tot: int):
        pct = int((cur / max(1, tot)) * 100)
        self.progress_bar.setValue(pct)
        self.lbl_progress.setText(f"جارٍ فحص: {name} ({cur}/{tot})...")

    def _on_scan_finished(self, targets: List[CleanupItem]):
        self.items = targets
        self.btn_rescan.setEnabled(True)
        self.btn_clean.setEnabled(True)
        self.btn_simulate.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_progress.setText("اكتمل فحص المواقع القابلة للتنظيف.")
        self._populate_table()
        self._update_cleanable_sum()

    def _populate_table(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.items))

        for row, item in enumerate(self.items):
            # Checkbox
            chk = QCheckBox()
            chk.setChecked(item.is_checked)
            chk.stateChanged.connect(lambda state, it=item: self._on_item_toggled(it, state))
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.setContentsMargins(8, 0, 8, 0)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk_lay.addWidget(chk)
            self.table.setCellWidget(row, 0, chk_widget)

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(item.name_ar))

            # Description
            desc_item = QTableWidgetItem(item.description_ar)
            desc_item.setToolTip(item.description_ar)
            self.table.setItem(row, 2, desc_item)

            # Safety badge
            badge_lbl = QLabel(item.safety_label_ar)
            if item.safety_level == "safe":
                badge_lbl.setStyleSheet("""
                    background: rgba(63, 185, 80, 0.15); color: #3FB950;
                    border: 1px solid rgba(63, 185, 80, 0.3); border-radius: 4px;
                    padding: 2px 8px; font-weight: bold; font-size: 10px;
                """)
            else:
                badge_lbl.setStyleSheet("""
                    background: rgba(210, 153, 34, 0.15); color: #D29922;
                    border: 1px solid rgba(210, 153, 34, 0.3); border-radius: 4px;
                    padding: 2px 8px; font-weight: bold; font-size: 10px;
                """)
            badge_widget = QWidget()
            b_lay = QHBoxLayout(badge_widget)
            b_lay.setContentsMargins(4, 0, 4, 0)
            b_lay.setAlignment(Qt.AlignCenter)
            b_lay.addWidget(badge_lbl)
            self.table.setCellWidget(row, 3, badge_widget)

            # Size & count
            sz_str = f"{format_bytes(item.size_bytes)} ({item.files_count:,} ملف)"
            self.table.setItem(row, 4, QTableWidgetItem(sz_str))

    def _on_item_toggled(self, item: CleanupItem, state: int):
        item.is_checked = (state == Qt.Checked.value or state == 2)
        self._update_cleanable_sum()

    def _update_cleanable_sum(self):
        total_selected = sum(it.size_bytes for it in self.items if it.is_checked)
        self.lbl_cleanable.setText(f"المساحة المحددة القابلة للتنظيف: {format_bytes(total_selected)}")

    def confirm_and_clean(self, simulation: bool = False):
        selected = [it for it in self.items if it.is_checked and it.size_bytes > 0]
        if not selected:
            QMessageBox.information(self, "تنبيه", "لم يتم تحديد أي عناصر تحتوي على ملفات للتنظيف.")
            return

        total_bytes = sum(it.size_bytes for it in selected)

        if simulation:
            QMessageBox.information(
                self,
                "محاكاة التنظيف الآمن",
                f"ستقوم هذه العملية بمحاكاة تنظيف {format_bytes(total_bytes)} دون حذف أي ملف من القرص."
            )
        else:
            confirm = QMessageBox.question(
                self,
                "تأكيد التنظيف الآمن",
                f"أنت على وشك تنظيف {format_bytes(total_bytes)} من الملفات المؤقتة والكاش المحددة.\n\n"
                "ملاحظة أمان: سيتم تخطي أي ملف مفتوح أو قيد الاستخدام بواسطة ويندوز أو البرامج تلقائياً وبأمان.\n\n"
                "هل ترغب في المتابعة؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

        # Run execute worker
        self.btn_clean.setEnabled(False)
        self.btn_simulate.setEnabled(False)
        self.btn_rescan.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        mode_str = "محاكاة" if simulation else "تنفيذ"
        self.lbl_progress.setText(f"جارٍ {mode_str} التنظيف...")

        self.clean_worker = CleanupExecuteWorker(self.items, simulation=simulation, parent=self)
        self.clean_worker.progress.connect(self._on_scan_progress)
        self.clean_worker.finished_clean.connect(self._on_clean_finished)
        self.clean_worker.start()

    def _on_clean_finished(self, result: CleanupResult):
        self.btn_clean.setEnabled(True)
        self.btn_simulate.setEnabled(True)
        self.btn_rescan.setEnabled(True)
        self.progress_bar.setVisible(False)

        msg = (
            f"اكتملت العملية بنجاح في {result.duration:.2f} ثانية!\n\n"
            f"- المساحة المحررة: {format_bytes(result.cleaned_bytes)}\n"
            f"- عدد الملفات المحذوفة: {result.cleaned_files:,}\n"
            f"- ملفات قيد الاستخدام تم تخطيها بأمان: {result.skipped_locked_files:,}\n"
        )
        if result.errors:
            msg += f"\nملاحظات: {', '.join(result.errors[:2])}"

        QMessageBox.information(self, "نتيجة التنظيف", msg)
        self.start_scan()

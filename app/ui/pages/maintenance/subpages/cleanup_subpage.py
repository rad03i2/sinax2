# -*- coding: utf-8 -*-
"""
Safe Cleanup & Downloads Review Subpage for SINAX Maintenance & Repair Center.
Implements honest temporary files analysis and cleanup with explicit safety classifications,
and a dedicated Downloads Review section that never auto-deletes files.
"""

import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.ui.icons import get_icon


class CleanupSubpage(QWidget):
    """Subpage for transparent, media-safe temporary cache cleanup and downloads review."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.run_analysis()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        tabs = QTabWidget(self)
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363D;
                background-color: #0D1117;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161B22;
                color: #8B949E;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #21262D;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
        """)

        # Tab 1: Safe Temp Cleanup
        self.tab_temp = QWidget()
        self._init_temp_tab()
        tabs.addTab(self.tab_temp, "التنظيف الآمن للملفات المؤقتة")

        # Tab 2: Downloads Review
        self.tab_downloads = QWidget()
        self._init_downloads_tab()
        tabs.addTab(self.tab_downloads, "مراجعة مجلد التنزيلات (Downloads)")

        main_layout.addWidget(tabs)

    def _init_temp_tab(self):
        layout = QVBoxLayout(self.tab_temp)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        t_lbl = QLabel("تحليل الملفات المؤقتة والكاش القابلة للتنظيف الآمن:")
        t_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        top_bar.addWidget(t_lbl)
        top_bar.addStretch(1)

        btn_analyze = QPushButton("إعادة التحليل")
        btn_analyze.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #21262D;
            }
        """)
        btn_analyze.clicked.connect(self.run_analysis)
        top_bar.addWidget(btn_analyze)

        self.btn_clean_temp = QPushButton("تنظيف الملفات المؤقتة بأمان")
        self.btn_clean_temp.setIcon(get_icon("clean", color_hex="#FFFFFF"))
        self.btn_clean_temp.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_clean_temp.clicked.connect(self._clean_temp_files)
        top_bar.addWidget(self.btn_clean_temp)

        layout.addLayout(top_bar)

        # Table of cleanup targets
        self.temp_table = QTableWidget()
        self.temp_table.setColumnCount(4)
        self.temp_table.setHorizontalHeaderLabels(["النوع / الموقع", "الحجم المستهلك", "درجة الأمان", "المسار"])
        self.temp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.temp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.temp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.temp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.temp_table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
                color: #C9D1D9;
            }
            QHeaderView::section {
                background-color: #0D1117;
                color: #8B949E;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.temp_table, 1)

        # Bottom info card
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        i_layout = QHBoxLayout(info_frame)
        self.lbl_total_clean = QLabel("إجمالي المساحة القابلة للتحرير: 0 B")
        self.lbl_total_clean.setStyleSheet("font-size: 13px; font-weight: bold; color: #38BDF8;")
        i_layout.addWidget(self.lbl_total_clean)
        i_layout.addStretch(1)

        btn_empty_rb = QPushButton("إفراغ سلة المحذوفات")
        btn_empty_rb.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #F87171;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        btn_empty_rb.clicked.connect(self._empty_recycle_bin_prompt)
        i_layout.addWidget(btn_empty_rb)

        layout.addWidget(info_frame)

    def _init_downloads_tab(self):
        layout = QVBoxLayout(self.tab_downloads)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_lbl = QLabel(
            "مراجعة مجلد التنزيلات: لا تقوم SINAX بمسح مجلد التنزيلات تلقائياً إطلاقاً.\n"
            "نعرض لك الملفات الكبيرة ومثبتات البرامج القديمة لتحديد ما ترغب بالاحتفاظ به."
        )
        header_lbl.setWordWrap(True)
        header_lbl.setStyleSheet("font-size: 13px; color: #94A3B8; line-height: 1.4;")
        layout.addWidget(header_lbl)

        self.dl_table = QTableWidget()
        self.dl_table.setColumnCount(4)
        self.dl_table.setHorizontalHeaderLabels(["اسم الملف", "الحجم", "تاريخ التعديل", "العمر بالأيام"])
        self.dl_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.dl_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.dl_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.dl_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.dl_table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
                color: #C9D1D9;
            }
            QHeaderView::section {
                background-color: #0D1117;
                color: #8B949E;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.dl_table, 1)

        bottom_r = QHBoxLayout()
        self.lbl_dl_summary = QLabel("إجمالي حجم التنزيلات: جاري القراءة...")
        self.lbl_dl_summary.setStyleSheet("font-weight: bold; color: #F0F6FC;")
        bottom_r.addWidget(self.lbl_dl_summary)
        bottom_r.addStretch(1)

        open_dl_btn = QPushButton("فتح مجلد التنزيلات في Explorer")
        open_dl_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        open_dl_btn.clicked.connect(self._open_downloads_in_explorer)
        bottom_r.addWidget(open_dl_btn)
        layout.addLayout(bottom_r)

    def run_analysis(self):
        """Calculates cleanup sizes and populates tables."""
        data = SafeCleanupOrchestrator.analyze_cleanup_targets()
        self.temp_table.setRowCount(0)

        rows = [
            ("ملفات المستخدم المؤقتة (User Temp)", data["user_temp"]["bytes"], data["user_temp"]["safety"], data["user_temp"]["path"]),
            ("ملفات النظام المؤقتة (Windows Temp)", data["windows_temp"]["bytes"], data["windows_temp"]["safety"], data["windows_temp"]["path"]),
            ("كاش المعاينات المصغرة (Thumbnails)", data["thumbnail_cache"]["bytes"], data["thumbnail_cache"]["safety"], data["thumbnail_cache"]["path"]),
            ("سلة المحذوفات (Recycle Bin)", data["recycle_bin"]["bytes"], data["recycle_bin"]["safety"], "كافة الأقراص"),
            ("مخلفات الأعطال (Crash Dumps)", data["crash_dumps"]["bytes"], data["crash_dumps"]["safety"], data["crash_dumps"]["path"]),
        ]

        self.temp_table.setRowCount(len(rows))
        for idx, (title, b, safety, path) in enumerate(rows):
            self.temp_table.setItem(idx, 0, QTableWidgetItem(title))
            self.temp_table.setItem(idx, 1, QTableWidgetItem(SafeCleanupOrchestrator.format_bytes(b)))
            self.temp_table.setItem(idx, 2, QTableWidgetItem(safety))
            self.temp_table.setItem(idx, 3, QTableWidgetItem(path))

        self.lbl_total_clean.setText(
            f"إجمالي المساحة القابلة للتحرير: {SafeCleanupOrchestrator.format_bytes(data['total_reclaimable_bytes'])}"
        )

        # Analyze Downloads
        dl_data = SafeCleanupOrchestrator.review_downloads_folder()
        self.lbl_dl_summary.setText(
            f"إجمالي حجم مجلد التنزيلات: {SafeCleanupOrchestrator.format_bytes(dl_data['total_bytes'])} ({dl_data['total_count']} ملف)"
        )
        large_files = dl_data.get("large_files", []) + dl_data.get("installers", [])
        self.dl_table.setRowCount(len(large_files))
        for idx, item in enumerate(large_files):
            self.dl_table.setItem(idx, 0, QTableWidgetItem(item["name"]))
            self.dl_table.setItem(idx, 1, QTableWidgetItem(item["size_str"]))
            self.dl_table.setItem(idx, 2, QTableWidgetItem(item["modified_str"]))
            self.dl_table.setItem(idx, 3, QTableWidgetItem(f"{item['age_days']} يوم"))

    def _clean_temp_files(self):
        freed, cnt, skipped = SafeCleanupOrchestrator.clean_user_temp()
        SnapshotHistoryService().log_maintenance_action(
            "clean_user_temp", "تنظيف ملفات المستخدم المؤقتة", "cleanup", "success", f"تم تحرير {SafeCleanupOrchestrator.format_bytes(freed)}.", freed_bytes=freed
        )
        QMessageBox.information(
            self,
            "اكتمل التنظيف",
            f"تم تنظيف الملفات المؤقتة بنجاح.\nالمساحة المحررة: {SafeCleanupOrchestrator.format_bytes(freed)}\nتم حذف: {cnt} ملف\nتم تخطي: {skipped} ملف قيد الاستخدام حالياً."
        )
        self.run_analysis()

    def _empty_recycle_bin_prompt(self):
        reply = QMessageBox.question(
            self,
            "تأكيد إفراغ سلة المحذوفات",
            "هل أنت متأكد من رغبتك في إفراغ سلة المحذوفات لجميع الأقراص نهائياً؟\nلا يمكن التراجع عن هذا الإجراء.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            SafeCleanupOrchestrator.empty_recycle_bin()
            self.run_analysis()

    def _open_downloads_in_explorer(self):
        import subprocess
        dl_path = str(Path.home() / "Downloads")
        try:
            subprocess.Popen(["explorer.exe", dl_path])
        except Exception:
            pass

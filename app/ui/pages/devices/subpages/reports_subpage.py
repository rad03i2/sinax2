# -*- coding: utf-8 -*-
"""
SINAX Hardware Reports & Snapshots Subpage (صفحة التقارير، الخصوصية ومقارنة العتاد)
Exports comprehensive hardware reports in HTML, JSON, TXT, CSV formats,
toggles privacy masking, creates hardware state snapshots, and compares diffs.
"""

import os
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import HardwareSnapshot
from app.services.devices.hardware_report_service import HardwareReportService
from app.ui.icons import get_icon


class ReportsSubpage(QWidget):
    """Subpage for generating reports, managing hardware snapshots, and viewing change diffs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._snapshots: List[HardwareSnapshot] = []
        self._init_ui()
        self.refresh_snapshots()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("تقارير العتاد ولقطات التغيير (Reports & Snapshots)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 1. Report Exporter Card
        exp_card = QFrame()
        exp_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        e_layout = QVBoxLayout(exp_card)
        e_layout.setSpacing(14)

        e_title = QLabel("تصدير تقرير شامل للعتاد (Export Hardware Report)")
        e_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        e_title.setStyleSheet("color: #38BDF8; background: transparent;")
        e_layout.addWidget(e_title)

        e_desc = QLabel(
            "يمكنك استخراج تقرير توثيقي كامل ومفصل لكافة مواصفات ومكونات حاسوبك بالصيغة المناسبة "
            "سواء للمشاركة مع الدعم الفني، أو لتوثيق ملكية الجهاز ومواصفاته."
        )
        e_desc.setStyleSheet("color: #94A3B8; background: transparent;")
        e_desc.setWordWrap(True)
        e_layout.addWidget(e_desc)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(14)

        lbl_fmt = QLabel("صيغة الملف:")
        lbl_fmt.setStyleSheet("color: #CBD5E1; font-weight: bold; background: transparent;")
        ctrl_row.addWidget(lbl_fmt)

        self.combo_fmt = QComboBox()
        self.combo_fmt.setStyleSheet("""
            QComboBox {
                background: #0F172A; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 6px; padding: 6px 14px; min-width: 140px; font-weight: bold;
            }
        """)
        self.combo_fmt.addItem("تقرير HTML تفاعلي", "html")
        self.combo_fmt.addItem("ملف نصي (TXT)", "txt")
        self.combo_fmt.addItem("بيانات JSON تقنية", "json")
        self.combo_fmt.addItem("جدول CSV", "csv")
        ctrl_row.addWidget(self.combo_fmt)

        self.chk_privacy = QCheckBox("تفعيل وضع الخصوصية (إخفاء السيريال واسم الجهاز)")
        self.chk_privacy.setChecked(True)
        self.chk_privacy.setStyleSheet("color: #F8FAFC; font-weight: bold; background: transparent;")
        ctrl_row.addWidget(self.chk_privacy)

        ctrl_row.addStretch()

        self.btn_export = QPushButton("  تصدير التقرير الآن")
        self.btn_export.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: #0078D4; color: #FFFFFF; border-radius: 6px;
                padding: 0 18px; font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
        """)
        self.btn_export.clicked.connect(self._export_report)
        ctrl_row.addWidget(self.btn_export)

        e_layout.addLayout(ctrl_row)
        layout.addWidget(exp_card)

        # 2. Hardware Snapshots & Diff Comparison Card
        snap_card = QFrame()
        snap_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        s_layout = QVBoxLayout(snap_card)
        s_layout.setSpacing(14)

        s_head = QHBoxLayout()
        s_title = QLabel("سجل لقطات العتاد وتتبع التغييرات (Hardware Snapshots & History)")
        s_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        s_title.setStyleSheet("color: #38BDF8; background: transparent;")
        s_head.addWidget(s_title)
        s_head.addStretch()
        s_layout.addLayout(s_head)

        s_desc = QLabel(
            "تتيح لك اللقطات تسجيل الحالة العتادية الحالية للجهاز في قاعدة بيانات محلية، "
            "لتنبيهك عند استبدال أي قطعة، أو ترقية الذاكرة، أو تغيير كرت الشاشة."
        )
        s_desc.setStyleSheet("color: #94A3B8; background: transparent;")
        s_desc.setWordWrap(True)
        s_layout.addWidget(s_desc)

        # Snapshot input row
        snap_input_row = QHBoxLayout()
        snap_input_row.setSpacing(10)

        self.txt_snap_name = QLineEdit()
        self.txt_snap_name.setPlaceholderText("اكتب اسمًا توضيحيًا للقطة (مثال: قبل ترقية الرامات)...")
        self.txt_snap_name.setFixedHeight(34)
        self.txt_snap_name.setStyleSheet("""
            QLineEdit {
                background: #0F172A; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 6px; padding: 0 12px;
            }
        """)
        snap_input_row.addWidget(self.txt_snap_name, 1)

        self.btn_take_snap = QPushButton("  حفظ لقطة جديدة")
        self.btn_take_snap.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.btn_take_snap.setFixedHeight(34)
        self.btn_take_snap.setStyleSheet("""
            QPushButton {
                background: #10B981; color: #FFFFFF; border-radius: 6px;
                padding: 0 14px; font-weight: bold;
            }
            QPushButton:hover { background: #059669; }
        """)
        self.btn_take_snap.clicked.connect(self._take_snapshot)
        snap_input_row.addWidget(self.btn_take_snap)
        s_layout.addLayout(snap_input_row)

        # Snapshots Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["المعرّف", "اسم اللقطة", "تاريخ التسجيل", "المعالج والذاكرة"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0F172A;
                border: 1px solid #334155;
                gridline-color: #1E293B;
                color: #F8FAFC;
                border-radius: 6px;
            }
            QHeaderView::section {
                background: #1E293B;
                color: #CBD5E1;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)
        self.table.setFixedHeight(160)
        s_layout.addWidget(self.table)

        # Diff Comparison Output
        diff_row = QHBoxLayout()
        self.btn_compare = QPushButton("  مقارنة آخر لقطتين لاكتشاف التغييرات")
        self.btn_compare.setIcon(get_icon("devices", "#FFFFFF", 14))
        self.btn_compare.setFixedHeight(32)
        self.btn_compare.setStyleSheet("""
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 14px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.btn_compare.clicked.connect(self._compare_snapshots)
        diff_row.addWidget(self.btn_compare)
        diff_row.addStretch()
        s_layout.addLayout(diff_row)

        self.txt_diff = QTextEdit()
        self.txt_diff.setReadOnly(True)
        self.txt_diff.setFixedHeight(100)
        self.txt_diff.setStyleSheet("""
            QTextEdit {
                background: #0F172A; color: #CBD5E1; border: 1px solid #334155;
                border-radius: 6px; padding: 8px; font-size: 11px;
            }
        """)
        self.txt_diff.setPlaceholderText("نتائج المقارنة بين لقطات العتاد ستظهر هنا...")
        s_layout.addWidget(self.txt_diff)

        layout.addWidget(snap_card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_snapshots(self):
        try:
            self._snapshots = HardwareReportService.list_snapshots()
            self.table.setRowCount(len(self._snapshots))
            for r, sn in enumerate(self._snapshots):
                self.table.setItem(r, 0, QTableWidgetItem(sn.snapshot_id))
                self.table.setItem(r, 1, QTableWidgetItem(sn.name))
                self.table.setItem(r, 2, QTableWidgetItem(sn.created_at))
                summary_str = f"CPU: {sn.cpu_name[:25]}... | RAM: {sn.ram_total_gb:.1f} GB"
                self.table.setItem(r, 3, QTableWidgetItem(summary_str))
        except Exception:
            pass

    def _export_report(self):
        fmt = self.combo_fmt.currentData()
        mask = self.chk_privacy.isChecked()

        filters = {
            "html": "HTML Files (*.html)",
            "txt": "Text Files (*.txt)",
            "json": "JSON Files (*.json)",
            "csv": "CSV Files (*.csv)",
        }
        default_name = f"SINAX_Hardware_Report.{fmt}"
        save_path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير العتاد", default_name, filters.get(fmt, "All Files (*)"))
        if not save_path:
            return

        success = HardwareReportService.export_report(fmt=fmt, mask_privacy=mask, destination_path=save_path)
        if success and os.path.exists(save_path):
            res = QMessageBox.question(
                self,
                "تم التصدير بنجاح",
                f"تم حفظ تقرير العتاد بنجاح في:\n{save_path}\n\nهل ترغب في فتح الملف الآن؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if res == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))
        else:
            QMessageBox.warning(self, "فشل التصدير", "تعذر تصدير تقرير العتاد.")

    def _take_snapshot(self):
        name = self.txt_snap_name.text().strip() or "لقطة عتاد يدوية"
        snap = HardwareReportService.save_snapshot(name=name)
        if snap:
            self.txt_snap_name.clear()
            self.refresh_snapshots()
            QMessageBox.information(self, "تم الحفظ", f"تم حفظ لقطة العتاد بنجاح بنجاح:\n{snap.name}")
        else:
            QMessageBox.warning(self, "خطأ", "تعذر حفظ لقطة العتاد.")

    def _compare_snapshots(self):
        if len(self._snapshots) < 2:
            self.txt_diff.setText("تحتاج إلى وجود لقطتين على الأقل لإجراء المقارنة.")
            return

        # Compare first two snapshots
        id1 = self._snapshots[0].snapshot_id
        id2 = self._snapshots[1].snapshot_id
        res = HardwareReportService.compare_snapshots(id1, id2)

        if not res.get("changed"):
            self.txt_diff.setText(f"✓ {res.get('message_ar')}\nلم يطرأ أي تغيير على المعالج أو الذاكرة أو وحدات التخزين أو كروت الشاشة بين اللقطتين.")
        else:
            lines = [f"⚠ {res.get('message_ar')}:"]
            for diff in res.get("differences", []):
                lines.append(f"• {diff.get('category')} - {diff.get('item')}: كان [{diff.get('old')}] وأصبح [{diff.get('new')}]")
            self.txt_diff.setText("\n".join(lines))

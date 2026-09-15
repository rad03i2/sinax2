# -*- coding: utf-8 -*-
"""
SINAX Leftover Remnants Scanner Subpage
Scans disk and registry for remnants left behind after software uninstallation
with a strict 3-tier confidence system and automated registry backups.
"""

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.leftover_scanner import LeftoverItem, LeftoverScanner
from app.ui.icons import get_icon


class LeftoversSubpage(QWidget):
    """Subpage scanning for uninstalled software leftovers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_items: List[LeftoverItem] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Search Frame
        top_frame = QFrame()
        top_frame.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        tf_layout = QVBoxLayout(top_frame)
        tf_layout.setSpacing(10)

        lbl_t = QLabel("البحث عن بقايا البرامج المتروكة (Leftovers Scanner)")
        lbl_t.setStyleSheet("color: #A371F7; font-size: 16px; font-weight: bold;")
        tf_layout.addWidget(lbl_t)

        lbl_desc = QLabel("ابحث بحذر عن المجلدات، الملفات، الاختصارات، ومفاتيح السجل التابعة لبرنامج تم حذفه مسبقاً.")
        lbl_desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        tf_layout.addWidget(lbl_desc)

        input_row = QHBoxLayout()
        self.input_app_name = QLineEdit()
        self.input_app_name.setPlaceholderText("اكتب اسم البرنامج المراد البحث عن بقاياه (مثال: VLC, Chrome, Nero)...")
        self.input_app_name.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px 12px; font-size: 13px;")
        self.input_app_name.returnPressed.connect(self._on_scan)
        input_row.addWidget(self.input_app_name, 1)

        self.btn_scan = QPushButton("فحص البقايا")
        self.btn_scan.setIcon(get_icon("clean", color="#F0F6FC"))
        self.btn_scan.setStyleSheet("background: #1F6FEB; color: white; border: none; border-radius: 6px; padding: 8px 18px; font-weight: bold; font-size: 13px;")
        self.btn_scan.clicked.connect(self._on_scan)
        input_row.addWidget(self.btn_scan)

        tf_layout.addLayout(input_row)

        # Warning guard note
        lbl_guard = QLabel("🛡️ نظام الأمان: يتم تلقائياً استبعاد المجلدات المشتركة للشركات الكبرى (Adobe, Microsoft, Autodesk, إلخ) والملفات الشخصية لحمايتها.")
        lbl_guard.setStyleSheet("color: #8B949E; font-size: 11px;")
        tf_layout.addWidget(lbl_guard)

        main_layout.addWidget(top_frame)

        # 2. Controls & Actions Bar
        ctrl_bar = QHBoxLayout()
        self.lbl_results_count = QLabel("لم يتم إجراء فحص بعد.")
        self.lbl_results_count.setStyleSheet("color: #8B949E; font-size: 12px;")
        ctrl_bar.addWidget(self.lbl_results_count)

        ctrl_bar.addStretch(1)

        btn_select_high = QPushButton("تحديد عالي الثقة فقط")
        btn_select_high.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        btn_select_high.clicked.connect(self._select_high_confidence_only)
        ctrl_bar.addWidget(btn_select_high)

        self.btn_clean_selected = QPushButton("تنظيف المحدد بأمان")
        self.btn_clean_selected.setIcon(get_icon("uninstall", color="#F0F6FC"))
        self.btn_clean_selected.setStyleSheet("background: #DA3633; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        self.btn_clean_selected.clicked.connect(self._on_clean_selected)
        ctrl_bar.addWidget(self.btn_clean_selected)

        main_layout.addLayout(ctrl_bar)

        # 3. Results Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "تحديد",
            "النوع",
            "المسار",
            "الحجم",
            "درجة الثقة والتوضيح",
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 45)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0D1117; alternate-background-color: #161B22; color: #C9D1D9;
                border: 1px solid #30363D; border-radius: 10px; font-size: 12px;
            }
            QHeaderView::section {
                background: #161B22; color: #F0F6FC; font-weight: bold;
                border: none; border-bottom: 1px solid #30363D; padding: 8px;
            }
        """)
        main_layout.addWidget(self.table, 1)

    def scan_for_app(self, app: InstalledApp):
        """Pre-populates the search box and triggers an automatic scan."""
        self.input_app_name.setText(app.name)
        self._on_scan()

    def _on_scan(self):
        name = self.input_app_name.text().strip()
        if not name or len(name) < 3:
            QMessageBox.information(self, "فحص البقايا", "يرجى كتابة اسم البرنامج المكون من 3 أحرف على الأقل للبحث بدقة.")
            return

        self._current_items = LeftoverScanner.scan_for_app(name)
        self.table.setRowCount(len(self._current_items))

        type_labels = {
            "folder": "مجلد ملفات",
            "file": "ملف مستقل",
            "shortcut": "اختصار برنامج",
            "registry": "مفتاح في السجل",
        }

        for r, item in enumerate(self._current_items):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if item.selected else Qt.Unchecked)
            self.table.setItem(r, 0, chk)

            self.table.setItem(r, 1, QTableWidgetItem(type_labels.get(item.item_type, item.item_type)))
            self.table.setItem(r, 2, QTableWidgetItem(item.path))
            self.table.setItem(r, 3, QTableWidgetItem(item.display_size))

            # Confidence with color
            conf_item = QTableWidgetItem(f"{item.confidence_label_ar} — {item.reason}")
            if item.confidence == "high":
                conf_item.setForeground(QColor("#3FB950"))  # Green
            else:
                conf_item.setForeground(QColor("#D29922"))  # Yellow
            self.table.setItem(r, 4, conf_item)

        self.lbl_results_count.setText(f"تم العثور على {len(self._current_items)} بقايا محتملة للبرنامج '{name}'.")

    def _select_high_confidence_only(self):
        for r, item in enumerate(self._current_items):
            chk = self.table.item(r, 0)
            if chk:
                chk.setCheckState(Qt.Checked if item.confidence == "high" else Qt.Unchecked)

    def _on_clean_selected(self):
        selected_items = []
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                if r < len(self._current_items):
                    selected_items.append(self._current_items[r])

        if not selected_items:
            QMessageBox.information(self, "تنظيف البقايا", "يرجى تحديد عناصر لتنظيفها عبر مربعات الاختيار [✓].")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد تنظيف البقايا",
            f"سيتم حذف {len(selected_items)} عنصراً من بقايا البرنامج ونقل الملفات إلى سلة المحذوفات مع حفظ نسخة احتياطية من مفاتيح السجل.\n\nهل ترغب في المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            suc, fail, errors = LeftoverScanner.clean_leftovers(selected_items)
            msg = f"اكتملت العملية بنجاح: تم تنظيف {suc} عنصراً."
            if fail > 0:
                msg += f"\nتعذر حذف {fail} عنصراً:\n" + "\n".join(errors[:5])
            QMessageBox.information(self, "نتائج التنظيف", msg)
            self._on_scan()

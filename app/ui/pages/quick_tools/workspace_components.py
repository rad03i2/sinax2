# -*- coding: utf-8 -*-
"""
SINAX Quick Tools Workspace Components
Reusable UI widgets: Split View (Input / Output), Option Selectors, Action Bars,
and Tabular Result Presenters.
"""

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import get_icon


class SplitViewWorkspace(QWidget):
    """Integrated two-pane workspace with Input editor and Output result area."""

    execute_requested = Signal(str, dict)       # (input_text, options)
    copy_requested = Signal(str)               # output_text
    pass_to_pipeline_requested = Signal(str)   # output_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_options: Dict[str, Any] = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Options & Controls Bar (Dynamic)
        self.options_frame = QFrame()
        self.options_frame.setObjectName("OptionsFrame")
        self.options_frame.setStyleSheet("""
            QFrame#OptionsFrame {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        self.options_layout = QHBoxLayout(self.options_frame)
        self.options_layout.setContentsMargins(10, 6, 10, 6)
        self.options_layout.setSpacing(12)

        self.options_title = QLabel("الخيارات والمعايير:")
        self.options_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.options_title.setStyleSheet("color: #E6EDF3;")
        self.options_layout.addWidget(self.options_title)

        # Dynamic controls holder
        self.dynamic_controls_widget = QWidget()
        self.dynamic_controls_layout = QHBoxLayout(self.dynamic_controls_widget)
        self.dynamic_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_controls_layout.setSpacing(8)
        self.options_layout.addWidget(self.dynamic_controls_widget, 1)

        layout.addWidget(self.options_frame)

        # 2. Splitter: Input Pane | Output Pane
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #30363D;
                width: 4px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background: #0078D4;
            }
        """)

        # Input Container
        self.input_container = QFrame()
        self.input_container.setStyleSheet("background: #0D1117; border: 1px solid #21262D; border-radius: 8px;")
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(8)

        in_header = QHBoxLayout()
        in_title = QLabel("المدخلات (Input):")
        in_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        in_title.setStyleSheet("color: #58A6FF;")
        in_header.addWidget(in_title)
        in_header.addStretch()

        self.clear_btn = QPushButton("مسح")
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 5px;
                padding: 0 10px;
                font-size: 11px;
            }
            QPushButton:hover { background: #30363D; color: #F0F6FC; }
        """)
        self.clear_btn.clicked.connect(self._clear_input)
        in_header.addWidget(self.clear_btn)
        input_layout.addLayout(in_header)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setFont(QFont("Consolas", 10))
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                background: #161B22;
                color: #E6EDF3;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px;
            }
            QPlainTextEdit:focus { border: 1px solid #0078D4; }
        """)
        self.input_edit.setPlaceholderText("اكتب هنا أو الصق النص أو اسحب الملفات...")
        input_layout.addWidget(self.input_edit, 1)

        # Output Container
        self.output_container = QFrame()
        self.output_container.setStyleSheet("background: #0D1117; border: 1px solid #21262D; border-radius: 8px;")
        output_layout = QVBoxLayout(self.output_container)
        output_layout.setContentsMargins(10, 10, 10, 10)
        output_layout.setSpacing(8)

        out_header = QHBoxLayout()
        out_title = QLabel("المخرجات والنتيجة (Output):")
        out_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        out_title.setStyleSheet("color: #3FB950;")
        out_header.addWidget(out_title)
        out_header.addStretch()

        self.copy_btn = QPushButton("نسخ النتيجة")
        self.copy_btn.setIcon(get_icon("duplicate", "#FFFFFF", 16))
        self.copy_btn.setFixedHeight(28)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                padding: 0 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        self.copy_btn.clicked.connect(self._on_copy_output)
        out_header.addWidget(self.copy_btn)

        self.pipe_btn = QPushButton("تمرير كمدخل ➔")
        self.pipe_btn.setFixedHeight(28)
        self.pipe_btn.setStyleSheet("""
            QPushButton {
                background: #1F6FEB;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                padding: 0 10px;
                font-size: 11px;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        self.pipe_btn.clicked.connect(self._on_pass_to_pipeline)
        out_header.addWidget(self.pipe_btn)

        output_layout.addLayout(out_header)

        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setFont(QFont("Consolas", 10))
        self.output_edit.setStyleSheet("""
            QPlainTextEdit {
                background: #161B22;
                color: #7EE787;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        output_layout.addWidget(self.output_edit, 1)

        # Image preview label (for QR / Barcode)
        self.qr_preview_label = QLabel()
        self.qr_preview_label.setAlignment(Qt.AlignCenter)
        self.qr_preview_label.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 6px;")
        self.qr_preview_label.setVisible(False)
        output_layout.addWidget(self.qr_preview_label, 1)

        # Table preview widget (for inventories, duplicates, characters)
        self.table_preview = QTableWidget()
        self.table_preview.setStyleSheet("""
            QTableWidget {
                background: #161B22;
                color: #E6EDF3;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
            }
            QHeaderView::section {
                background: #21262D;
                color: #8B949E;
                padding: 4px;
                font-weight: bold;
                border: none;
            }
        """)
        self.table_preview.horizontalHeader().setStretchLastSection(True)
        self.table_preview.setVisible(False)
        output_layout.addWidget(self.table_preview, 1)

        self.splitter.addWidget(self.input_container)
        self.splitter.addWidget(self.output_container)
        self.splitter.setSizes([450, 450])

        layout.addWidget(self.splitter, 1)

        # 3. Bottom Action Bar
        action_bar = QHBoxLayout()
        self.run_btn = QPushButton("تشغيل الأداة (Execute)")
        self.run_btn.setIcon(get_icon("play", "#FFFFFF", 16))
        self.run_btn.setFixedHeight(38)
        self.run_btn.setMinimumWidth(160)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #106EBE; }
            QPushButton:pressed { background: #005A9E; }
        """)
        self.run_btn.clicked.connect(self._on_run_clicked)
        action_bar.addWidget(self.run_btn)

        self.status_lbl = QLabel("")
        self.status_lbl.setFont(QFont("Segoe UI", 10))
        self.status_lbl.setStyleSheet("color: #8B949E;")
        action_bar.addWidget(self.status_lbl)
        action_bar.addStretch()

        self.export_btn = QPushButton("تصدير إلى ملف...")
        self.export_btn.setFixedHeight(34)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #E6EDF3;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 11px;
            }
            QPushButton:hover { background: #30363D; }
        """)
        self.export_btn.clicked.connect(self._on_export_clicked)
        action_bar.addWidget(self.export_btn)

        layout.addLayout(action_bar)

    def set_input_text(self, text: str):
        self.input_edit.setPlainText(text)

    def get_input_text(self) -> str:
        return self.input_edit.toPlainText()

    def set_output_text(self, text: str):
        self.qr_preview_label.setVisible(False)
        self.table_preview.setVisible(False)
        self.output_edit.setVisible(True)
        self.output_edit.setPlainText(text)
        self.status_lbl.setText("تمت المعالجة بنجاح.")

    def set_output_pixmap(self, pixmap: QPixmap):
        self.output_edit.setVisible(False)
        self.table_preview.setVisible(False)
        self.qr_preview_label.setVisible(True)
        self.qr_preview_label.setPixmap(pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.status_lbl.setText("تم توليد الرمز بنجاح.")

    def set_output_table(self, headers: List[str], rows: List[List[str]]):
        self.output_edit.setVisible(False)
        self.qr_preview_label.setVisible(False)
        self.table_preview.setVisible(True)
        self.table_preview.clear()
        self.table_preview.setColumnCount(len(headers))
        self.table_preview.setHorizontalHeaderLabels(headers)
        self.table_preview.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                self.table_preview.setItem(r_idx, c_idx, item)
        self.status_lbl.setText(f"تم استخراج {len(rows)} عنصر.")

    def _clear_input(self):
        self.input_edit.clear()
        self.output_edit.clear()
        self.qr_preview_label.clear()
        self.table_preview.clear()
        self.status_lbl.setText("")

    def _on_copy_output(self):
        txt = self.output_edit.toPlainText()
        if txt:
            from PySide6.QtGui import QGuiApplication
            app = QGuiApplication.instance()
            if app:
                app.clipboard().setText(txt)
                old_txt = self.copy_btn.text()
                self.copy_btn.setText("✓ تم النسخ!")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: self.copy_btn.setText(old_txt))

    def _on_pass_to_pipeline(self):
        out_txt = self.output_edit.toPlainText()
        if out_txt:
            self.pass_to_pipeline_requested.emit(out_txt)

    def _on_run_clicked(self):
        self.execute_requested.emit(self.input_edit.toPlainText(), self._current_options)

    def _on_export_clicked(self):
        txt = self.output_edit.toPlainText()
        if not txt:
            return
        dest, _ = QFileDialog.getSaveFileName(self, "تصدير النتيجة", "", "Text Files (*.txt);;JSON Files (*.json);;All Files (*.*)")
        if dest:
            try:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(txt)
                self.status_lbl.setText(f"تم الحفظ بنجاح في: {dest}")
            except Exception as e:
                self.status_lbl.setText(f"فشل الحفظ: {e}")

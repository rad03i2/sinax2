# -*- coding: utf-8 -*-
"""
SINAX Internal PDF Viewer & Thumbnail Preview Widget
High-speed local PDF viewer using PyMuPDF rendering with zoom, navigation,
and visual thumbnail strip.
"""

from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QSplitter, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QIcon

import fitz  # PyMuPDF
from app.ui.icons import get_icon


class PDFViewerWidget(QWidget):
    page_changed = Signal(int, int)   # (current_page_idx, total_pages)
    pages_reordered = Signal(list)    # [0, 2, 1, 3, ...]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[fitz.Document] = None
        self.current_page_idx: int = 0
        self.total_pages: int = 0
        self.zoom_factor: float = 1.0
        self._page_order: List[int] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #252526; border: 1px solid #333333; border-radius: 6px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(8)

        # Page navigation buttons
        self.btn_first = QPushButton()
        self.btn_first.setIcon(get_icon("page_first", "#CCCCCC", 14))
        self.btn_first.setToolTip("الصفحة الأولى")
        self.btn_first.setFixedSize(28, 28)
        self.btn_first.clicked.connect(lambda: self.go_to_page(0))
        tb_layout.addWidget(self.btn_first)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(get_icon("arrow_up", "#CCCCCC", 14))
        self.btn_prev.setToolTip("الصفحة السابقة")
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.clicked.connect(self._on_prev_page)
        tb_layout.addWidget(self.btn_prev)

        self.page_lbl = QLabel("0 / 0")
        self.page_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold; min-width: 60px;")
        self.page_lbl.setAlignment(Qt.AlignCenter)
        tb_layout.addWidget(self.page_lbl)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(get_icon("arrow_down", "#CCCCCC", 14))
        self.btn_next.setToolTip("الصفحة التالية")
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.clicked.connect(self._on_next_page)
        tb_layout.addWidget(self.btn_next)

        self.btn_last = QPushButton()
        self.btn_last.setIcon(get_icon("page_last", "#CCCCCC", 14))
        self.btn_last.setToolTip("الصفحة الأخيرة")
        self.btn_last.setFixedSize(28, 28)
        self.btn_last.clicked.connect(lambda: self.go_to_page(self.total_pages - 1))
        tb_layout.addWidget(self.btn_last)

        tb_layout.addSpacing(12)

        # Zoom Controls
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setToolTip("تصغير")
        self.btn_zoom_out.setFixedSize(28, 28)
        self.btn_zoom_out.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_zoom_out.clicked.connect(self._on_zoom_out)
        tb_layout.addWidget(self.btn_zoom_out)

        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.setFixedWidth(85)
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
        tb_layout.addWidget(self.zoom_combo)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setToolTip("تكبير")
        self.btn_zoom_in.setFixedSize(28, 28)
        self.btn_zoom_in.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_zoom_in.clicked.connect(self._on_zoom_in)
        tb_layout.addWidget(self.btn_zoom_in)

        tb_layout.addStretch(1)

        # Reorder actions (Move Page)
        self.btn_move_left = QPushButton("← نقل للخلف")
        self.btn_move_left.setToolTip("نقل الصفحة الحالية خطوة إلى الوراء")
        self.btn_move_left.clicked.connect(self._on_move_page_back)
        tb_layout.addWidget(self.btn_move_left)

        self.btn_move_right = QPushButton("نقل للأمام →")
        self.btn_move_right.setToolTip("نقل الصفحة الحالية خطوة للأمام")
        self.btn_move_right.clicked.connect(self._on_move_page_forward)
        tb_layout.addWidget(self.btn_move_right)

        layout.addWidget(toolbar)

        # 2. Main Content Splitter (Thumbnails + Page View)
        splitter = QSplitter(Qt.Horizontal)

        # Thumbnails List (Left side)
        self.thumb_list = QListWidget()
        self.thumb_list.setFixedWidth(120)
        self.thumb_list.setIconSize(QSize(90, 120))
        self.thumb_list.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 4px;
                margin-bottom: 6px;
                color: #CCCCCC;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
                color: #FFFFFF;
            }
        """)
        self.thumb_list.currentRowChanged.connect(self.go_to_page)
        splitter.addWidget(self.thumb_list)

        # Center Page Viewer (Scrollable)
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QFrame.NoFrame)
        self.page_scroll.setStyleSheet("QScrollArea { background-color: #181818; border: 1px solid #333333; border-radius: 6px; }")
        self.page_scroll.verticalScrollBar().setSingleStep(32)

        self.page_display = QLabel()
        self.page_display.setAlignment(Qt.AlignCenter)
        self.page_display.setText("اسحب أو اختر ملف PDF لعرضه هنا")
        self.page_display.setStyleSheet("color: #777777; font-size: 14px;")

        self.page_scroll.setWidget(self.page_display)
        splitter.addWidget(self.page_scroll)

        # Proportions: 120px thumbnails, rest for main view
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def load_document(self, pdf_path: Path):
        """Loads and renders the PDF document."""
        self.close_document()
        try:
            self.doc = fitz.open(str(pdf_path))
            self.total_pages = len(self.doc)
            self._page_order = list(range(self.total_pages))
            self.current_page_idx = 0

            # Populate Thumbnails
            self.thumb_list.clear()
            for i in range(self.total_pages):
                page = self.doc[i]
                # Mini thumbnail matrix
                pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                item = QListWidgetItem(f"صفحة {i+1}")
                item.setIcon(QIcon(QPixmap.fromImage(qimg)))
                item.setTextAlignment(Qt.AlignCenter)
                self.thumb_list.addItem(item)

            if self.total_pages > 0:
                self.thumb_list.setCurrentRow(0)
                self.render_current_page()
        except Exception as e:
            self.page_display.setText(f"فشل فتح المستند:\n{str(e)}")

    def render_current_page(self):
        """Renders the current active page onto the label using the active zoom factor."""
        if not self.doc or self.total_pages == 0:
            return

        real_pno = self._page_order[self.current_page_idx]
        page = self.doc[real_pno]

        zoom = self.zoom_factor * (120.0 / 72.0)  # comfortable default scale
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

        self.page_display.setPixmap(QPixmap.fromImage(qimg))
        self.page_lbl.setText(f"{self.current_page_idx + 1} / {self.total_pages}")
        self.page_changed.emit(self.current_page_idx, self.total_pages)

    def go_to_page(self, page_idx: int):
        if not self.doc or self.total_pages == 0:
            return
        if 0 <= page_idx < self.total_pages:
            self.current_page_idx = page_idx
            if self.thumb_list.currentRow() != page_idx:
                self.thumb_list.setCurrentRow(page_idx)
            self.render_current_page()

    def _on_prev_page(self):
        if self.current_page_idx > 0:
            self.go_to_page(self.current_page_idx - 1)

    def _on_next_page(self):
        if self.current_page_idx < self.total_pages - 1:
            self.go_to_page(self.current_page_idx + 1)

    def _on_zoom_changed(self, text: str):
        try:
            val = float(text.replace("%", "").strip()) / 100.0
            self.zoom_factor = max(0.2, min(3.0, val))
            self.render_current_page()
        except ValueError:
            pass

    def _on_zoom_in(self):
        self.zoom_factor = min(3.0, self.zoom_factor + 0.25)
        self.zoom_combo.setCurrentText(f"{int(self.zoom_factor * 100)}%")

    def _on_zoom_out(self):
        self.zoom_factor = max(0.25, self.zoom_factor - 0.25)
        self.zoom_combo.setCurrentText(f"{int(self.zoom_factor * 100)}%")

    def _on_move_page_back(self):
        if self.current_page_idx > 0:
            idx = self.current_page_idx
            self._page_order[idx - 1], self._page_order[idx] = self._page_order[idx], self._page_order[idx - 1]
            self.current_page_idx -= 1
            self.pages_reordered.emit(self._page_order)
            self._refresh_thumbnails()
            self.go_to_page(self.current_page_idx)

    def _on_move_page_forward(self):
        if self.current_page_idx < self.total_pages - 1:
            idx = self.current_page_idx
            self._page_order[idx + 1], self._page_order[idx] = self._page_order[idx], self._page_order[idx + 1]
            self.current_page_idx += 1
            self.pages_reordered.emit(self._page_order)
            self._refresh_thumbnails()
            self.go_to_page(self.current_page_idx)

    def _refresh_thumbnails(self):
        if not self.doc:
            return
        for i, real_pno in enumerate(self._page_order):
            item = self.thumb_list.item(i)
            if item:
                page = self.doc[real_pno]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                item.setText(f"صفحة {real_pno + 1}")
                item.setIcon(QIcon(QPixmap.fromImage(qimg)))

    def get_page_order(self) -> List[int]:
        return list(self._page_order)

    def close_document(self):
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
        self.total_pages = 0
        self.current_page_idx = 0
        self._page_order = []
        self.thumb_list.clear()
        self.page_display.setText("اسحب أو اختر ملف PDF لعرضه هنا")
        self.page_lbl.setText("0 / 0")

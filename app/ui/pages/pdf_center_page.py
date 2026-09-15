# -*- coding: utf-8 -*-
"""
SINAX PDF Center Main Page
Comprehensive PDF Hub featuring search filtering, category chips, tool cards catalog,
and integrated unified workspace.
"""

from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QScrollArea, QStackedWidget,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.config import config
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.services.pdf.pdf_registry import PDF_TOOLS_REGISTRY, PDF_CATEGORIES, PDFToolDefinition, get_tool_by_id
from app.ui.pages.pdf_components.pdf_card_widget import PDFCardWidget
from app.ui.pages.pdf_components.pdf_workspace import PDFToolWorkspace


class QMLPDFCenterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "pdfController")
        self.quick_widget.setSource(get_qml_url("pages/PdfCenterPage.qml"))
        layout.addWidget(self.quick_widget)


class PDFCenterPage(QWidget):
    back_to_hub_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "all"
        self._search_text = ""
        self._card_widgets: Dict[str, PDFCardWidget] = {}
        self._catalog_widget: Optional[QWidget] = None
        self._favorites: List[str] = config.get("pdf_favorites", ["merge", "compress", "split", "extract_pages", "protect"])
        self._init_ui()

    def _init_ui(self):
        self.stack = QStackedWidget(self)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)

        # Page 0: Modern QML PDF Center
        self.qml_view = QMLPDFCenterPage(self)
        self.stack.addWidget(self.qml_view)

    @property
    def catalog_widget(self) -> QWidget:
        if self._catalog_widget is None:
            self._catalog_widget = self._create_catalog_widget()
        return self._catalog_widget

    def _create_catalog_widget(self) -> QWidget:
        catalog_root = QWidget()
        layout = QVBoxLayout(catalog_root)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 1. Hero Header Banner
        hero_frame = QFrame()
        hero_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B2447, stop:1 #19376D);
                border: 1px solid #1D428A;
                border-radius: 10px;
            }
        """)
        hf_layout = QVBoxLayout(hero_frame)
        hf_layout.setContentsMargins(24, 18, 24, 18)
        hf_layout.setSpacing(6)

        title_lbl = QLabel("مركز PDF الاحترافي الشامل")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        hf_layout.addWidget(title_lbl)

        sub_lbl = QLabel("كل ما تحتاجه لإنشاء وتعديل وتنظيم وتحسين وحماية وتوقيع ملفات PDF محلياً بأعلى سرعة وأمان.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #CCCCCC;")
        hf_layout.addWidget(sub_lbl)
        layout.addWidget(hero_frame)

        # 2. Search Bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ابحث عن أداة PDF... (مثال: دمج، ضغط، تقسيم، تدوير، علامة مائية، حماية، صفحات)")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #262626;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #60CDFF;
                background-color: #2C2C2C;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input)
        layout.addLayout(search_row)

        # 3. Category Chips Bar
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(48)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cat_widget = QWidget()
        cat_layout = QHBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(6)

        self._cat_buttons = {}
        for cat_id, cat_name in PDF_CATEGORIES:
            btn = QPushButton(cat_name)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #222222;
                    color: #CCCCCC;
                    border: 1px solid #383838;
                    border-radius: 16px;
                    padding: 4px 14px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2D2D2D;
                    border-color: #60CDFF;
                    color: #FFFFFF;
                }
                QPushButton:checked {
                    background-color: #0078D4;
                    color: #FFFFFF;
                    font-weight: bold;
                    border-color: #0078D4;
                }
            """)
            btn.clicked.connect(lambda checked, cid=cat_id: self._on_category_clicked(cid))
            cat_layout.addWidget(btn)
            self._cat_buttons[cat_id] = btn

        self._cat_buttons["all"].setChecked(True)
        cat_layout.addStretch(1)
        cat_scroll.setWidget(cat_widget)
        layout.addWidget(cat_scroll)

        # 4. Scrollable Cards Grid
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cards_scroll.verticalScrollBar().setSingleStep(32)

        self.cards_content = QWidget()
        self.grid_layout = QGridLayout(self.cards_content)
        self.grid_layout.setContentsMargins(4, 8, 4, 48)
        self.grid_layout.setSpacing(14)

        self._populate_cards()
        self.cards_scroll.setWidget(self.cards_content)
        layout.addWidget(self.cards_scroll, 1)

        return catalog_root

    def _populate_cards(self):
        # Clear existing
        for w in self._card_widgets.values():
            w.setParent(None)
        self._card_widgets.clear()

        row = 0
        col = 0
        columns = 3  # 3 columns responsive card layout

        query = self._search_text.lower().strip()
        cat = self._active_category

        for tool in PDF_TOOLS_REGISTRY:
            # Filter by Category
            if cat == "most_used" and tool.id not in self._favorites and tool.category != "most_used":
                continue
            elif cat != "all" and cat != "most_used" and tool.category != cat:
                continue

            # Filter by Search Text
            if query:
                in_title_ar = query in tool.title_ar.lower()
                in_title_en = query in tool.title_en.lower()
                in_desc = query in tool.description_ar.lower()
                in_tags = any(query in tag.lower() for tag in tool.tags)
                if not (in_title_ar or in_title_en or in_desc or in_tags):
                    continue

            is_fav = tool.id in self._favorites
            card = PDFCardWidget(tool, is_favorite=is_fav)
            card.clicked.connect(self._on_tool_selected)
            card.favorite_toggled.connect(self._on_favorite_toggled)

            self.grid_layout.addWidget(card, row, col)
            self._card_widgets[tool.id] = card

            col += 1
            if col >= columns:
                col = 0
                row += 1

    def _on_search_changed(self, text: str):
        self._search_text = text
        self._populate_cards()

    def _on_category_clicked(self, category_id: str):
        self._active_category = category_id
        for cid, btn in self._cat_buttons.items():
            btn.setChecked(cid == category_id)
        self._populate_cards()

    def _on_favorite_toggled(self, tool_id: str, is_fav: bool):
        if is_fav and tool_id not in self._favorites:
            self._favorites.append(tool_id)
        elif not is_fav and tool_id in self._favorites:
            self._favorites.remove(tool_id)
        config.set("pdf_favorites", self._favorites, auto_save=True)

    def _on_tool_selected(self, tool_id: str):
        tool = get_tool_by_id(tool_id)
        if not tool:
            return

        # Create Workspace for selected tool
        workspace = PDFToolWorkspace(tool)
        workspace.back_to_catalog_requested.connect(self._on_back_to_catalog)
        workspace.status_changed.connect(self.status_changed.emit)
        workspace.progress_changed.connect(self.progress_changed.emit)

        # Add to stack and switch
        if self.stack.count() > 1:
            old_w = self.stack.widget(1)
            self.stack.removeWidget(old_w)
            old_w.deleteLater()

        self.stack.addWidget(workspace)
        self.stack.setCurrentIndex(1)

    def _on_back_to_catalog(self):
        self.stack.setCurrentIndex(0)
        self.status_changed.emit("جاهز")

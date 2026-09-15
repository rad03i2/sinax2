# -*- coding: utf-8 -*-
"""
SINAX Universal File Converter Page
Full responsive Fluent interface featuring:
- ~54 categorized conversion cards with dual independent directional buttons.
- Real-time search by format name or keyword (e.g. PDF, MP3, JPG).
- From/To format selection with dynamic target combo populating.
- 13 Category filter chips (All, PDF, Documents, Spreadsheets, Presentations, Images, Audio, Video, Data, Ebooks, Archives, Favorites, Most Used).
- Smart Quick Drop zone for instant format discovery.
- Embedded ConversionWorkspace with seamless back-navigation.
- Complete dynamic light and dark theme architecture.
"""

from pathlib import Path
from typing import List, Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QScrollArea, QStackedWidget,
    QGridLayout, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QColor, QCursor

from app.services.conversion.registry import conversion_registry, ConversionCardDefinition, ConversionDefinition
from app.ui.pages.converter_components.conversion_card_widget import ConversionCardWidget
from app.ui.pages.converter_components.converter_workspace import ConverterWorkspace
from app.ui.icons import get_icon
from app.ui.themes.theme_manager import theme_manager
from app.core.logger import get_logger

logger = get_logger("universal_converter_page")

CATEGORIES = [
    ("all", "الكل"),
    ("pdf", "PDF"),
    ("documents", "المستندات"),
    ("spreadsheets", "الجداول"),
    ("presentations", "العروض التقديمية"),
    ("images", "الصور"),
    ("audio", "الصوت"),
    ("video", "الفيديو"),
    ("data", "البيانات"),
    ("ebooks", "الكتب الإلكترونية"),
    ("archives", "الأرشيفات"),
    ("favorites", "المفضلة"),
    ("most_used", "الأكثر استخداماً")
]


class QuickDropBanner(QFrame):
    file_dropped = Signal(object)  # Path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("quickDropBanner")
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()
        self.apply_theme(theme_manager.effective_theme)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self.icon_lbl = QLabel()
        layout.addWidget(self.icon_lbl)

        text_v = QVBoxLayout()
        text_v.setSpacing(2)
        self.t_main = QLabel("اسحب أي ملف إلى هنا وسنعرض لك التحويلات المناسبة له فوراً")
        self.t_sub = QLabel("يدعم المحوّل الشامل أكثر من 50 صيغة مستندات، صور، صوت، فيديو، وجداول...")
        text_v.addWidget(self.t_main)
        text_v.addWidget(self.t_sub)
        layout.addLayout(text_v, 1)

    def apply_theme(self, theme_name: str):
        is_dark = (theme_name == "dark")
        if is_dark:
            self.setStyleSheet("""
                QFrame#quickDropBanner {
                    background-color: #1A2433;
                    border: 1px dashed #0078D4;
                    border-radius: 8px;
                }
                QFrame#quickDropBanner:hover {
                    background-color: #1F2D40;
                    border-color: #60CDFF;
                }
            """)
            self.t_main.setStyleSheet("font-size: 13px; font-weight: bold; color: #60CDFF;")
            self.t_sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
            icon = get_icon("sparkles", "#60CDFF", 22)
        else:
            self.setStyleSheet("""
                QFrame#quickDropBanner {
                    background-color: #EFF6FF;
                    border: 1px dashed #3B82F6;
                    border-radius: 8px;
                }
                QFrame#quickDropBanner:hover {
                    background-color: #DBEAFE;
                    border-color: #1D4ED8;
                }
            """)
            self.t_main.setStyleSheet("font-size: 13px; font-weight: bold; color: #1D4ED8;")
            self.t_sub.setStyleSheet("font-size: 11px; color: #475569;")
            icon = get_icon("sparkles", "#2563EB", 22)

        self.icon_lbl.setPixmap(icon.pixmap(22, 22))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            p = Path(urls[0].toLocalFile())
            self.file_dropped.emit(p)


class UniversalConverterPage(QWidget):
    status_changed = Signal(str, bool, bool)
    progress_changed = Signal(int, int)
    back_to_hub_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UniversalConverterPage")
        self._current_category = "all"
        self._card_widgets: List[ConversionCardWidget] = []
        self._columns_count = 3
        self.current_workspace = None
        self.setAcceptDrops(True)
        self._init_ui()
        theme_manager.theme_changed.connect(self._on_theme_changed)
        self._apply_theme(theme_manager.effective_theme)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Page 0: Cards Catalog
        self.catalog_widget = QWidget()
        self._init_catalog_ui(self.catalog_widget)
        self.stack.addWidget(self.catalog_widget)

        # Page 1: Workspace Container
        self.workspace_container = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_container)
        self.workspace_layout.setContentsMargins(0, 0, 0, 0)
        self.stack.addWidget(self.workspace_container)

        root_layout.addWidget(self.stack)

    def _init_catalog_ui(self, container: QWidget):
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        # 1. Search Bar & From/To Row
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        # Search Input
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 ابحث عن تحويل أو صيغة (مثل: PDF, MP3, JPG, Word)...")
        self.search_edit.setMinimumHeight(38)
        self.search_edit.setStyleSheet("font-size: 13px; padding: 4px 12px;")
        self.search_edit.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self.search_edit, 3)

        # From Combo
        self.lbl_from = QLabel("من:")
        filter_bar.addWidget(self.lbl_from)

        self.combo_from = QComboBox()
        self.combo_from.setMinimumHeight(38)
        self.combo_from.setMinimumWidth(110)
        self.combo_from.addItem("الكل", "")
        for fmt in conversion_registry.get_all_source_formats():
            self.combo_from.addItem(fmt, fmt)
        self.combo_from.currentIndexChanged.connect(self._on_from_changed)
        filter_bar.addWidget(self.combo_from)

        # To Combo
        self.lbl_to = QLabel("إلى:")
        filter_bar.addWidget(self.lbl_to)

        self.combo_to = QComboBox()
        self.combo_to.setMinimumHeight(38)
        self.combo_to.setMinimumWidth(110)
        self.combo_to.addItem("اختر الهدف", "")
        self.combo_to.currentIndexChanged.connect(self._on_to_changed)
        filter_bar.addWidget(self.combo_to)

        # Open Direct Conversion Button
        self.btn_open_pair = QPushButton("فتح التحويل")
        self.btn_open_pair.setProperty("class", "PrimaryButton")
        self.btn_open_pair.setMinimumHeight(38)
        self.btn_open_pair.setCursor(Qt.PointingHandCursor)
        self.btn_open_pair.clicked.connect(self._on_open_pair_clicked)
        filter_bar.addWidget(self.btn_open_pair)

        layout.addLayout(filter_bar)

        # 2. Category Chips Bar
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(46)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cat_widget = QWidget()
        cat_layout = QHBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(6)

        self._cat_buttons = {}
        for cat_id, cat_name in CATEGORIES:
            btn = QPushButton(cat_name)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, cid=cat_id: self._on_category_clicked(cid))
            cat_layout.addWidget(btn)
            self._cat_buttons[cat_id] = btn

        self._cat_buttons["all"].setChecked(True)
        cat_layout.addStretch(1)
        cat_scroll.setWidget(cat_widget)
        layout.addWidget(cat_scroll)

        # 3. Quick Drop Banner
        self.quick_banner = QuickDropBanner()
        self.quick_banner.file_dropped.connect(self._on_file_dropped)
        layout.addWidget(self.quick_banner)

        # 4. Scrollable Cards Grid
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cards_scroll.verticalScrollBar().setSingleStep(36)

        self.cards_content = QWidget()
        self.grid_layout = QGridLayout(self.cards_content)
        self.grid_layout.setContentsMargins(4, 8, 4, 40)
        self.grid_layout.setSpacing(14)

        self.cards_scroll.setWidget(self.cards_content)
        layout.addWidget(self.cards_scroll, 1)

        # Initial population of cards
        self._refresh_cards_grid()

    def _apply_theme(self, theme_name: str):
        is_dark = (theme_name == "dark")

        # Labels
        lbl_color = "#E2E8F0" if is_dark else "#1E293B"
        if hasattr(self, "lbl_from"):
            self.lbl_from.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {lbl_color};")
        if hasattr(self, "lbl_to"):
            self.lbl_to.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {lbl_color};")

        # Category Buttons
        if hasattr(self, "_cat_buttons"):
            for cid, btn in self._cat_buttons.items():
                if is_dark:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #21262D;
                            color: #CCCCCC;
                            border: 1px solid #30363D;
                            border-radius: 16px;
                            padding: 4px 14px;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #2D333B;
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
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #F1F5F9;
                            color: #334155;
                            border: 1px solid #CBD5E1;
                            border-radius: 16px;
                            padding: 4px 14px;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #E2E8F0;
                            border-color: #0078D4;
                            color: #0F172A;
                        }
                        QPushButton:checked {
                            background-color: #0078D4;
                            color: #FFFFFF;
                            font-weight: bold;
                            border-color: #0078D4;
                        }
                    """)

        # Banner
        if hasattr(self, "quick_banner"):
            self.quick_banner.apply_theme(theme_name)

        # Cards
        for card in self._card_widgets:
            card.apply_theme(theme_name)

        # Workspace if open
        if self.current_workspace and hasattr(self.current_workspace, "apply_theme"):
            self.current_workspace.apply_theme(theme_name)

    def _on_theme_changed(self, theme_name: str):
        self._apply_theme(theme_name)

    def _refresh_cards_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._card_widgets.clear()

        q = self.search_edit.text()
        cat = self._current_category
        only_fav = (cat == "favorites")
        only_used = (cat == "most_used")
        target_cat = "all" if (only_fav or only_used) else cat

        cards = conversion_registry.search_cards(
            query=q,
            category=target_cat,
            only_favorites=only_fav,
            only_most_used=only_used
        )

        cols = self._calculate_columns()
        for idx, card_def in enumerate(cards):
            card_w = ConversionCardWidget(card_def)
            card_w.direction_selected.connect(self._open_workspace)
            card_w.favorite_toggled.connect(self._on_fav_toggled)
            r = idx // cols
            c = idx % cols
            self.grid_layout.addWidget(card_w, r, c)
            self._card_widgets.append(card_w)

        if not cards:
            is_dark = (theme_manager.effective_theme == "dark")
            txt_color = "#888888" if is_dark else "#64748B"
            no_card_lbl = QLabel("لا توجد بطاقات تحويل تطابق البحث الحالي.")
            no_card_lbl.setStyleSheet(f"color: {txt_color}; font-size: 14px; padding: 40px;")
            no_card_lbl.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(no_card_lbl, 0, 0, 1, cols)

    def _calculate_columns(self) -> int:
        w = self.width()
        if w < 750:
            return 1
        elif w < 1050:
            return 2
        elif w < 1450:
            return 3
        elif w < 1850:
            return 4
        else:
            return 5

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols = self._calculate_columns()
        if new_cols != self._columns_count:
            self._columns_count = new_cols
            QTimer.singleShot(50, self._reflow_grid)

    def _reflow_grid(self):
        cols = self._columns_count
        cards = list(self._card_widgets)
        for idx, w in enumerate(cards):
            self.grid_layout.removeWidget(w)
            r = idx // cols
            c = idx % cols
            self.grid_layout.addWidget(w, r, c)

    def _on_search_changed(self, text: str):
        self._refresh_cards_grid()

    def _on_category_clicked(self, cat_id: str):
        for cid, btn in self._cat_buttons.items():
            btn.setChecked(cid == cat_id)
        self._current_category = cat_id
        self._refresh_cards_grid()

    def _on_from_changed(self, idx: int):
        val = self.combo_from.currentData()
        self.combo_to.blockSignals(True)
        self.combo_to.clear()
        self.combo_to.addItem("اختر الهدف", "")

        if val:
            targets = conversion_registry.get_targets_for_source(val)
            for t in targets:
                self.combo_to.addItem(t, t)
            self.search_edit.setText(val)
        else:
            self.search_edit.clear()

        self.combo_to.blockSignals(False)

    def _on_to_changed(self, idx: int):
        t_val = self.combo_to.currentData()
        f_val = self.combo_from.currentData()
        if f_val and t_val:
            self.search_edit.setText(f"{f_val} {t_val}")

    def _on_open_pair_clicked(self):
        f_val = self.combo_from.currentData()
        t_val = self.combo_to.currentData()
        if not f_val or not t_val:
            return
        direction = conversion_registry.find_direction(f_val, t_val)
        if direction:
            self._open_workspace(direction, f"{f_val}_{t_val}")

    def _open_workspace(self, direction: ConversionDefinition, card_id: str):
        while self.workspace_layout.count():
            item = self.workspace_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        self.current_workspace = ConverterWorkspace(direction, card_id)
        self.current_workspace.back_requested.connect(self._close_workspace)
        self.current_workspace.status_changed.connect(self.status_changed.emit)
        self.current_workspace.progress_changed.connect(self.progress_changed.emit)
        self.workspace_layout.addWidget(self.current_workspace)

        self.stack.setCurrentIndex(1)
        self.status_changed.emit(f"مساحة التحويل: {direction.title_ar}", False, False)

    def _close_workspace(self):
        self.current_workspace = None
        self.stack.setCurrentIndex(0)
        self.status_changed.emit("المحوّل الشامل للملفات", False, False)
        self.progress_changed.emit(0, 0)
        self._refresh_cards_grid()

    def is_in_workspace(self) -> bool:
        return self.stack.currentIndex() == 1

    def close_workspace(self):
        self._close_workspace()

    def _on_fav_toggled(self, card_id: str, state: bool):
        if self._current_category == "favorites":
            self._refresh_cards_grid()

    def _on_file_dropped(self, path: Path):
        ext = path.suffix.lower().lstrip('.')
        self.search_edit.setText(ext.upper())
        matched = conversion_registry.find_matching_cards_for_file(path)
        if matched:
            self.status_changed.emit(f"عُثر على {len(matched)} بطاقة تحويل متوافقة مع ملفات .{ext.upper()}", False, False)
        else:
            self.status_changed.emit(f"لا يوجد تحويل مباشر لملفات .{ext.upper()}", False, True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            p = Path(urls[0].toLocalFile())
            self._on_file_dropped(p)

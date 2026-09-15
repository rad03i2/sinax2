# -*- coding: utf-8 -*-
"""
SINAX Video Center Main Page
Comprehensive Video Processing Hub featuring search filtering, category chips,
responsive tool cards grid, hardware acceleration status, and integrated unified workspace.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config
from app.services.video.hardware_detector import hardware_detector
from app.services.video.video_registry import (
    VIDEO_CATEGORIES,
    VIDEO_TOOLS,
    VideoToolDefinition,
    get_video_tool_by_id,
)
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.ui.pages.video_components.video_card_widget import VideoCardWidget
from app.ui.pages.video_components.video_workspace import VideoToolWorkspace


class QMLVideoCenterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "videoController")
        self.quick_widget.setSource(get_qml_url("pages/VideoCenterPage.qml"))
        layout.addWidget(self.quick_widget)


class VideoCenterPage(QWidget):
    """Main page for SINAX Video Center."""

    back_to_hub_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "all"
        self._search_text = ""
        self._card_widgets: Dict[str, VideoCardWidget] = {}
        self._catalog_widget: Optional[QWidget] = None
        self._favorites: List[str] = config.get(
            "video_favorites",
            [
                "batch_compress",
                "target_size_compress",
                "batch_convert",
                "fast_remux",
                "resize_scale",
                "trim_cut",
                "extract_audio",
                "create_gif",
                "batch_workflow_builder",
            ],
        )
        self._init_ui()

    def _init_ui(self):
        self.stack = QStackedWidget(self)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)

        # Page 0: Modern QML Video Center
        self.qml_view = QMLVideoCenterPage(self)
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

        # -------------------------------------------------------------
        # 1. Hero Header Banner
        # -------------------------------------------------------------
        hero_frame = QFrame()
        hero_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #141E30, stop:1 #243B55);
                border: 1px solid #2B4764;
                border-radius: 10px;
            }
        """)
        hf_layout = QHBoxLayout(hero_frame)
        hf_layout.setContentsMargins(24, 18, 24, 18)
        hf_layout.setSpacing(16)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(6)

        title_lbl = QLabel("مركز الفيديو الاحترافي الشامل (SINAX Video Center)")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        header_text_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "منظومة متكاملة لمعالجة وتحويل وضغط وتقطيع ودمج وتحسين مقاطع الفيديو محلياً "
            "بالاعتماد على محرك FFmpeg 7.1 وتسريع بطاقات الشاشة (GPU)."
        )
        sub_lbl.setStyleSheet("font-size: 13px; color: #D0D0D0;")
        header_text_layout.addWidget(sub_lbl)
        hf_layout.addLayout(header_text_layout, 1)

        # Hardware acceleration status indicator (Non-blocking Fast Load)
        hw_info = hardware_detector.get_status_summary_fast()
        hw_box = QFrame()
        hw_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 120, 212, 0.2);
                border: 1px solid #0078D4;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        hw_box_layout = QVBoxLayout(hw_box)
        hw_box_layout.setContentsMargins(10, 6, 10, 6)
        hw_box_layout.setSpacing(4)

        self.hw_title = QLabel(hw_info["badge_text"])
        self.hw_title.setStyleSheet("color: #60CDFF; font-weight: bold; font-size: 12px;")
        hw_box_layout.addWidget(self.hw_title)

        self.hw_desc = QLabel("جاهز للعمليات الفائقة" if hw_info.get("is_accelerated") else "جاري التحقق من تسريع العتاد بالخلفية...")
        self.hw_desc.setStyleSheet("color: #AAAAAA; font-size: 10px;")
        hw_box_layout.addWidget(self.hw_desc)
        hf_layout.addWidget(hw_box)

        # Trigger background detection
        hardware_detector.detect_encoders_async(self._on_hw_status_ready)

        layout.addWidget(hero_frame)

        # -------------------------------------------------------------
        # 2. Search Bar
        # -------------------------------------------------------------
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "🔍 ابحث عن أداة للفيديو... (مثال: ضغط، تحويل، قص، دمج، صوت، علامة مائية، Shorts، GIF، تسريع)"
        )
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

        # -------------------------------------------------------------
        # 3. Category Chips Bar
        # -------------------------------------------------------------
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(48)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        chips_container = QWidget()
        chips_container.setStyleSheet("background: transparent;")
        self.chips_layout = QHBoxLayout(chips_container)
        self.chips_layout.setContentsMargins(0, 4, 0, 4)
        self.chips_layout.setSpacing(8)

        self._chip_buttons: Dict[str, QPushButton] = {}
        for cat in VIDEO_CATEGORIES:
            btn = QPushButton(cat["name_ar"])
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=cat["id"]: self._on_category_selected(c))
            self._chip_buttons[cat["id"]] = btn
            self.chips_layout.addWidget(btn)

        self.chips_layout.addStretch(1)
        cat_scroll.setWidget(chips_container)
        layout.addWidget(cat_scroll)
        self._update_chips_styling()

        # -------------------------------------------------------------
        # 4. Scrollable Cards Grid Area
        # -------------------------------------------------------------
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                background-color: #1E1E1E;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #444444;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.cards_container)
        self.grid_layout.setContentsMargins(0, 6, 0, 16)
        self.grid_layout.setSpacing(14)
        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, 1)

        # Populate Cards
        self._populate_cards()
        return catalog_root

    def _populate_cards(self):
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        self._card_widgets.clear()

        for tool in VIDEO_TOOLS:
            is_fav = tool.id in self._favorites
            card = VideoCardWidget(tool, is_favorite=is_fav)
            card.clicked.connect(self.open_tool)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            self._card_widgets[tool.id] = card

        self._filter_and_arrange_cards()

    def _filter_and_arrange_cards(self):
        visible_cards = []
        q = self._search_text.lower().strip()

        for tool in VIDEO_TOOLS:
            card = self._card_widgets.get(tool.id)
            if not card:
                continue

            # Category filter
            cat_match = False
            if self._active_category == "all":
                cat_match = True
            elif self._active_category == "favorites":
                cat_match = tool.id in self._favorites
            elif self._active_category == "popular":
                cat_match = tool.id in (
                    "batch_compress",
                    "target_size_compress",
                    "batch_convert",
                    "fast_remux",
                    "resize_scale",
                    "trim_cut",
                    "batch_workflow_builder",
                )
            elif self._active_category == "batch":
                cat_match = tool.supports_batch
            else:
                cat_match = (tool.category == self._active_category)

            # Search filter
            search_match = True
            if q:
                texts = [
                    tool.title_ar.lower(),
                    tool.title_en.lower(),
                    tool.description_ar.lower(),
                    tool.category.lower(),
                ] + [t.lower() for t in tool.tags]
                search_match = any(q in t for t in texts)

            if cat_match and search_match:
                visible_cards.append(card)
                card.show()
            else:
                card.hide()

        # Responsive column calculation based on width
        container_width = self.width() if self.width() > 400 else 1000
        cols = 3
        if container_width < 700:
            cols = 1
        elif container_width < 1050:
            cols = 2
        elif container_width > 1500:
            cols = 4

        # Arrange in grid
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.removeItem(self.grid_layout.itemAt(i))

        for idx, card in enumerate(visible_cards):
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

    def _on_search_changed(self, text: str):
        self._search_text = text
        self._filter_and_arrange_cards()

    def _on_category_selected(self, cat_id: str):
        self._active_category = cat_id
        self._update_chips_styling()
        self._filter_and_arrange_cards()

    def _update_chips_styling(self):
        active_style = """
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: 1px solid #0078D4;
                border-radius: 14px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: #262626;
                color: #CCCCCC;
                border: 1px solid #383838;
                border-radius: 14px;
                padding: 5px 14px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #60CDFF;
                color: #FFFFFF;
            }
        """
        for cid, btn in self._chip_buttons.items():
            if cid == self._active_category:
                btn.setChecked(True)
                btn.setStyleSheet(active_style)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(inactive_style)

    def _on_favorite_toggled(self, tool_id: str, is_fav: bool):
        if is_fav and tool_id not in self._favorites:
            self._favorites.append(tool_id)
        elif not is_fav and tool_id in self._favorites:
            self._favorites.remove(tool_id)
        config.set("video_favorites", self._favorites)

    def open_tool(self, tool_id: str):
        """Opens the selected video tool in the workspace."""
        tool = get_video_tool_by_id(tool_id)
        if not tool:
            return

        workspace = VideoToolWorkspace(tool, parent=self)
        workspace.back_to_catalog_requested.connect(self._close_workspace)
        workspace.status_changed.connect(self.status_changed.emit)
        workspace.progress_changed.connect(self.progress_changed.emit)

        # Remove previous workspace page if exists
        if self.stack.count() > 1:
            old_w = self.stack.widget(1)
            self.stack.removeWidget(old_w)
            old_w.deleteLater()

        self.stack.addWidget(workspace)
        self.stack.setCurrentIndex(1)
        self.status_changed.emit(f"مركز الفيديو: {tool.title_ar}")

    def _close_workspace(self):
        self.stack.setCurrentIndex(0)
        self.status_changed.emit("مركز الفيديو")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "grid_layout") and self.grid_layout is not None:
            self._filter_and_arrange_cards()

    def _on_hw_status_ready(self, summary: Dict[str, Any]):
        def update_ui():
            try:
                self.hw_title.setText(summary["badge_text"])
                self.hw_desc.setText("جاهز للعمليات الفائقة" if summary["has_gpu"] else "محرك المعالجة الافتراضي جاهز")
            except Exception:
                pass
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, update_ui)

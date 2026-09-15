# -*- coding: utf-8 -*-
"""
SINAX Audio Center Main Page
Comprehensive Audio Processing Hub featuring search filtering, category chips,
responsive tool cards grid, and integrated unified workspace.
"""

from pathlib import Path
from typing import Dict, List, Optional

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
from app.services.audio.audio_registry import (
    AUDIO_CATEGORIES,
    AUDIO_TOOLS_REGISTRY,
    AudioToolDefinition,
    get_audio_tool_by_id,
    search_audio_tools,
)
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.ui.icons import get_icon
from app.ui.pages.audio_components.audio_card_widget import AudioCardWidget
from app.ui.pages.audio_components.audio_workspace import AudioToolWorkspace


class QMLAudioCenterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "audioController")
        self.quick_widget.setSource(get_qml_url("pages/AudioCenterPage.qml"))
        layout.addWidget(self.quick_widget)


class AudioCenterPage(QWidget):
    """Main page for SINAX Audio Center."""

    back_to_hub_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "all"
        self._search_text = ""
        self._card_widgets: Dict[str, AudioCardWidget] = {}
        self._catalog_widget: Optional[QWidget] = None
        self._favorites: List[str] = config.get(
            "audio_favorites",
            [
                "batch_audio_convert",
                "batch_audio_compress",
                "target_size_audio_compress",
                "podcast_voice_enhancer",
                "loudness_normalize_audio",
                "trim_audio",
                "denoise_audio",
                "audio_workflow_builder",
            ],
        )
        self._init_ui()

    def _init_ui(self):
        self.stack = QStackedWidget(self)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)

        # Page 0: Modern QML Audio Center
        self.qml_view = QMLAudioCenterPage(self)
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
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #121F2B, stop:1 #1A364E);
                border: 1px solid #28445E;
                border-radius: 10px;
            }
        """)
        hf_layout = QHBoxLayout(hero_frame)
        hf_layout.setContentsMargins(24, 18, 24, 18)
        hf_layout.setSpacing(16)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(6)

        title_lbl = QLabel("مركز الصوت الاحترافي الشامل (SINAX Audio Center)")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        header_text_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "المحطة الشاملة لمعالجة الملفات الصوتية والموسيقى والتسجيلات والبودكاست دفعة واحدة: "
            "تحويل الصيغ، ضغط ذكي بحجم مستهدف، عزل الضوضاء والوشيش، معايرة LUFS القياسية، دمج، فلاتر ومعادل صوتي محلي 100%."
        )
        sub_lbl.setStyleSheet("font-size: 13px; color: #CCCCCC; line-height: 1.4;")
        sub_lbl.setWordWrap(True)
        header_text_layout.addWidget(sub_lbl)

        hf_layout.addLayout(header_text_layout, 1)

        # Stats Badge
        stats_box = QFrame()
        stats_box.setStyleSheet("""
            background-color: rgba(0, 164, 239, 0.12);
            border: 1px solid #0078D4;
            border-radius: 8px;
            padding: 8px 14px;
        """)
        sb_layout = QVBoxLayout(stats_box)
        sb_layout.setAlignment(Qt.AlignCenter)
        sb_layout.setSpacing(2)

        num_lbl = QLabel(str(len(AUDIO_TOOLS_REGISTRY)))
        num_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A4EF;")
        num_lbl.setAlignment(Qt.AlignCenter)
        sb_layout.addWidget(num_lbl)

        txt_lbl = QLabel("أداة صوتية متخصصة")
        txt_lbl.setStyleSheet("font-size: 11px; color: #DDDDDD;")
        txt_lbl.setAlignment(Qt.AlignCenter)
        sb_layout.addWidget(txt_lbl)

        hf_layout.addWidget(stats_box)
        layout.addWidget(hero_frame)

        # -------------------------------------------------------------
        # 2. Search Bar
        # -------------------------------------------------------------
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #242424;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 2px 10px;
            }
            QFrame:focus-within {
                border: 1px solid #0078D4;
            }
        """)
        sf_layout = QHBoxLayout(search_frame)
        sf_layout.setContentsMargins(8, 6, 8, 6)
        sf_layout.setSpacing(8)

        search_icon = QLabel()
        search_icon.setPixmap(get_icon("search", "#8E8E93").pixmap(18, 18))
        sf_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ابحث عن أداة صوتية بالاسم أو الصيغة أو الوظيفة (مثلاً: MP3, ضغط, تنقية, LUFS, بودكاست)...")
        self.search_input.setStyleSheet("background: transparent; border: none; color: #FFFFFF; font-size: 13px;")
        self.search_input.textChanged.connect(self._on_search_changed)
        sf_layout.addWidget(self.search_input, 1)

        layout.addWidget(search_frame)

        # -------------------------------------------------------------
        # 3. Category Filter Chips (Scrollable Horizontal)
        # -------------------------------------------------------------
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(44)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cat_container = QWidget()
        self.cat_layout = QHBoxLayout(cat_container)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(6)

        self._category_buttons: Dict[str, QPushButton] = {}
        for cat in AUDIO_CATEGORIES:
            btn = QPushButton(cat["name_ar"])
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._chip_style(False))
            btn.clicked.connect(lambda checked, c_id=cat["id"]: self._select_category(c_id))
            self.cat_layout.addWidget(btn)
            self._category_buttons[cat["id"]] = btn

        self.cat_layout.addStretch()
        cat_scroll.setWidget(cat_container)
        layout.addWidget(cat_scroll)

        # Select "all" initially
        if "all" in self._category_buttons:
            self._category_buttons["all"].setChecked(True)
            self._category_buttons["all"].setStyleSheet(self._chip_style(True))

        # -------------------------------------------------------------
        # 4. Tools Grid (Scrollable)
        # -------------------------------------------------------------
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 8, 0, 8)
        self.grid_layout.setSpacing(12)

        self._populate_grid()

        grid_scroll.setWidget(self.grid_container)
        layout.addWidget(grid_scroll, 1)

        return catalog_root

    def _chip_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #0078D4;
                    color: #FFFFFF;
                    border: 1px solid #0078D4;
                    border-radius: 14px;
                    padding: 4px 14px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """
        return """
            QPushButton {
                background-color: #262626;
                color: #CCCCCC;
                border: 1px solid #383838;
                border-radius: 14px;
                padding: 4px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #FFFFFF;
                border-color: #484848;
            }
        """

    def _populate_grid(self):
        # Clear existing items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._card_widgets.clear()

        # Filter tools
        if self._search_text:
            filtered = search_audio_tools(self._search_text)
        elif self._active_category == "favorites":
            filtered = [t for t in AUDIO_TOOLS_REGISTRY if t.id in self._favorites]
        elif self._active_category == "popular":
            popular_ids = {
                "batch_audio_convert", "batch_audio_compress", "target_size_audio_compress",
                "podcast_voice_enhancer", "loudness_normalize_audio", "trim_audio",
                "denoise_audio", "merge_audio", "audio_workflow_builder"
            }
            filtered = [t for t in AUDIO_TOOLS_REGISTRY if t.id in popular_ids]
        elif self._active_category != "all":
            filtered = [t for t in AUDIO_TOOLS_REGISTRY if t.category == self._active_category]
        else:
            filtered = list(AUDIO_TOOLS_REGISTRY)

        columns = 3
        for idx, tool in enumerate(filtered):
            row = idx // columns
            col = idx % columns
            card = AudioCardWidget(tool, is_favorite=(tool.id in self._favorites))
            card.clicked.connect(self.open_tool)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            self.grid_layout.addWidget(card, row, col)
            self._card_widgets[tool.id] = card

    def _select_category(self, cat_id: str):
        self._active_category = cat_id
        for cid, btn in self._category_buttons.items():
            is_cur = (cid == cat_id)
            btn.setChecked(is_cur)
            btn.setStyleSheet(self._chip_style(is_cur))
        self._populate_grid()

    def _on_search_changed(self, text: str):
        self._search_text = text.strip()
        self._populate_grid()

    def _on_favorite_toggled(self, tool_id: str, is_fav: bool):
        if is_fav and tool_id not in self._favorites:
            self._favorites.append(tool_id)
        elif not is_fav and tool_id in self._favorites:
            self._favorites.remove(tool_id)
        config.set("audio_favorites", self._favorites)

    def open_tool(self, tool_id: str):
        """Open the unified workspace for the requested audio tool."""
        tool = get_audio_tool_by_id(tool_id)
        if not tool:
            return

        # Create workspace widget
        workspace = AudioToolWorkspace(tool, parent=self)
        workspace.back_to_catalog_requested.connect(self.close_workspace)
        workspace.status_changed.connect(self.status_changed.emit)
        workspace.progress_changed.connect(self.progress_changed.emit)

        # Remove old workspace if any
        if self.stack.count() > 1:
            w = self.stack.widget(1)
            self.stack.removeWidget(w)
            w.deleteLater()

        self.stack.addWidget(workspace)
        self.stack.setCurrentIndex(1)
        self.status_changed.emit(f"فتح أداة: {tool.title_ar}")

    def is_in_workspace(self) -> bool:
        return self.stack.currentIndex() == 1

    def close_workspace(self):
        if self.stack.currentIndex() == 1:
            w = self.stack.widget(1)
            if hasattr(w, "player_widget"):
                w.player_widget.stop()
            self.stack.setCurrentIndex(0)
            self.status_changed.emit("العودة إلى قائمة أدوات الصوت")

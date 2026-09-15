# -*- coding: utf-8 -*-
"""
SINAX Quick Tools & Utility Lab Master Page
Coordinates the smart search bar, category chips, Smart Drop Zone ("افعل شيئاً سريعاً"),
tool cards grid, and the integrated split-view workspace drawer.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.quick_tools.models import InputType, QuickToolDefinition, SafetyLevel
from app.services.quick_tools.quick_tools_db import QuickToolsDatabase
from app.services.quick_tools.registry import CATEGORIES, QuickToolRegistry
from app.services.quick_tools.resolver import SmartActionResolver
from app.services.quick_tools.tools.calculator_tools import CalculatorTools
from app.services.quick_tools.tools.conversion_tools import ConversionTools
from app.services.quick_tools.tools.developer_tools import DeveloperTools
from app.services.quick_tools.tools.encoding_tools import EncodingTools
from app.services.quick_tools.tools.file_tools import FileTools
from app.services.quick_tools.tools.folder_tools import FolderTools
from app.services.quick_tools.tools.generation_tools import GenerationTools
from app.services.quick_tools.tools.hash_tools import HashTools
from app.services.quick_tools.tools.list_tools import ListTools
from app.services.quick_tools.tools.naming_tools import NamingTools
from app.services.quick_tools.tools.password_tools import PasswordTools
from app.services.quick_tools.tools.qr_barcode_tools import QrBarcodeTools
from app.services.quick_tools.tools.text_tools import TextTools
from app.ui.icons import get_icon
from app.ui.pages.quick_tools.workspace_components import SplitViewWorkspace


class SmartDropZone(QFrame):
    """Interactive drag-and-drop zone with instant type detection and quick action buttons."""

    input_detected = Signal(str) # raw text or dropped path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("SmartDropZone")
        self.setStyleSheet("""
            QFrame#SmartDropZone {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #161B22, stop:1 #0D1117);
                border: 2px dashed #30363D;
                border-radius: 10px;
                padding: 12px;
            }
            QFrame#SmartDropZone:hover {
                border-color: #0078D4;
                background: #161B22;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # Header with icon and instructions
        top_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("tools", "#58A6FF", 24).pixmap(24, 24))
        top_row.addWidget(icon_lbl)

        prompt_lbl = QLabel("افعل شيئاً سريعاً: اسحب ملفاً أو مجلداً، أو الصق نصاً أو رابطاً هنا...")
        prompt_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        prompt_lbl.setStyleSheet("color: #E6EDF3;")
        top_row.addWidget(prompt_lbl)
        top_row.addStretch()

        self.type_badge = QLabel("في انتظار المدخلات")
        self.type_badge.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.type_badge.setStyleSheet("""
            background: #21262D;
            color: #8B949E;
            border-radius: 4px;
            padding: 3px 8px;
        """)
        top_row.addWidget(self.type_badge)
        layout.addLayout(top_row)

        # Inline quick text input box
        input_row = QHBoxLayout()
        self.inline_input = QLineEdit()
        self.inline_input.setPlaceholderText("اكتب أو الصق هنا مباشرة (مثال: https://... أو 50 GB إلى MB أو بصمة ملف)...")
        self.inline_input.setFont(QFont("Segoe UI", 10))
        self.inline_input.setFixedHeight(34)
        self.inline_input.setStyleSheet("""
            QLineEdit {
                background: #0D1117;
                color: #FFFFFF;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 0 10px;
            }
            QLineEdit:focus { border: 1px solid #0078D4; }
        """)
        self.inline_input.textChanged.connect(self._on_text_changed)
        input_row.addWidget(self.inline_input, 1)

        self.paste_btn = QPushButton("لصق من الحافظة")
        self.paste_btn.setIcon(get_icon("clipboard", "#FFFFFF", 14))
        self.paste_btn.setFixedHeight(34)
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #E6EDF3;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }
            QPushButton:hover { background: #30363D; }
        """)
        self.paste_btn.clicked.connect(self._on_paste_clicked)
        input_row.addWidget(self.paste_btn)

        layout.addLayout(input_row)

        # Dynamic Quick Actions Container
        self.actions_container = QWidget()
        self.actions_layout = QHBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 4, 0, 0)
        self.actions_layout.setSpacing(8)
        layout.addWidget(self.actions_container)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime.hasUrls():
            urls = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
            if urls:
                self.inline_input.setText(urls[0])
                self.input_detected.emit(urls[0])
                event.acceptProposedAction()
                return
        if mime.hasText():
            text = mime.text().strip()
            self.inline_input.setText(text)
            self.input_detected.emit(text)
            event.acceptProposedAction()

    def _on_paste_clicked(self):
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if app:
            txt = app.clipboard().text().strip()
            if txt:
                self.inline_input.setText(txt)
                self.input_detected.emit(txt)

    def _on_text_changed(self, text: str):
        if text.strip():
            self.input_detected.emit(text.strip())

    def update_actions(self, type_label: str, tools: List[QuickToolDefinition], on_action_cb):
        """Refreshes action buttons based on detected input."""
        self.type_badge.setText(type_label)
        self.type_badge.setStyleSheet("""
            background: #1F6FEB;
            color: #FFFFFF;
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
        """)

        # Clear existing action buttons
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for t in tools[:6]:
            btn = QPushButton(t.title_ar.split("(")[0].strip())
            btn.setIcon(get_icon(t.icon, "#58A6FF", 14))
            btn.setFixedHeight(28)
            btn.setStyleSheet("""
                QPushButton {
                    background: #21262D;
                    color: #58A6FF;
                    border: 1px solid #388BFD;
                    border-radius: 5px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #1F6FEB; color: #FFFFFF; }
            """)
            btn.clicked.connect(lambda _, tool=t: on_action_cb(tool))
            self.actions_layout.addWidget(btn)

        self.actions_layout.addStretch()


from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url


class QuickToolsPage(QWidget):
    """Master page for SINAX Quick Tools & Utility Lab with QML Modern UI."""

    status_changed = Signal(str, str)
    progress_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = QuickToolsDatabase()
        self.active_category = "all"
        self.active_tool: Optional[QuickToolDefinition] = None

        QuickToolRegistry.initialize()
        self._init_qml_ui()

    def _init_qml_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "quickToolsController")
        self.quick_widget.setSource(get_qml_url("pages/QuickToolsPage.qml"))
        root_layout.addWidget(self.quick_widget)
        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme(theme_manager.effective_theme)

    def apply_theme(self, theme_name: str = "dark"):
        """Ensures both QML quick_widget and legacy fallback widgets render with active theme."""
        is_light = (theme_name == "light")
        if hasattr(self, "cat_button_group"):
            chip_style = f"""
                QPushButton {{
                    background: {'#F1F5F9' if is_light else '#161B22'};
                    color: {'#0F172A' if is_light else '#8B949E'};
                    border: 1px solid {'#CBD5E1' if is_light else '#30363D'};
                    border-radius: 16px;
                    padding: 0 14px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {'#E2E8F0' if is_light else '#21262D'};
                    color: {'#0F172A' if is_light else '#E6EDF3'};
                }}
                QPushButton:checked {{
                    background: #0078D4;
                    color: #FFFFFF;
                    border-color: #0078D4;
                    font-weight: bold;
                }}
            """
            for btn in self.cat_button_group.buttons():
                btn.setStyleSheet(chip_style)


    def _init_legacy_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Section: Large Command & Search Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("ماذا تريد أن تفعل؟ ابحث عن أداة أو اكتب أمرًا (هاش، QR، تنظيف نص، Base64، حجم مجلد)...")
        self.search_edit.setFont(QFont("Segoe UI", 12))
        self.search_edit.setFixedHeight(46)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: #161B22;
                color: #FFFFFF;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 0 16px;
            }
            QLineEdit:focus {
                border: 2px solid #0078D4;
                background: #0D1117;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_edit, 1)

        main_layout.addLayout(top_bar)

        # 2. Smart Drop Zone ("افعل شيئاً سريعاً")
        self.drop_zone = SmartDropZone(self)
        self.drop_zone.input_detected.connect(self._on_input_detected)
        main_layout.addWidget(self.drop_zone)

        # 3. Horizontal Scrollable Category Chips
        category_scroll = QScrollArea()
        category_scroll.setFixedHeight(42)
        category_scroll.setWidgetResizable(True)
        category_scroll.setFrameShape(QFrame.NoFrame)
        category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        category_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        category_scroll.setStyleSheet("background: transparent;")

        cat_widget = QWidget()
        self.cat_layout = QHBoxLayout(cat_widget)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(8)

        self.cat_button_group = QButtonGroup(self)
        self.cat_button_group.setExclusive(True)

        for cat_id, title_ar, icon_name in CATEGORIES:
            btn = QPushButton(title_ar)
            btn.setIcon(get_icon(icon_name, "#8B949E", 14))
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton {
                    background: #161B22;
                    color: #8B949E;
                    border: 1px solid #30363D;
                    border-radius: 16px;
                    padding: 0 14px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #21262D; color: #E6EDF3; }
                QPushButton:checked {
                    background: #0078D4;
                    color: #FFFFFF;
                    border-color: #0078D4;
                    font-weight: bold;
                }
            """)
            if cat_id == "all":
                btn.setChecked(True)
            btn.clicked.connect(lambda _, c=cat_id: self._on_category_selected(c))
            self.cat_button_group.addButton(btn)
            self.cat_layout.addWidget(btn)

        self.cat_layout.addStretch()
        category_scroll.setWidget(cat_widget)
        main_layout.addWidget(category_scroll)

        # 4. Main Dynamic Area: Split between Workspace Drawer and Cards Grid
        self.main_content_splitter = QSplitter(Qt.Vertical)
        self.main_content_splitter.setStyleSheet("""
            QSplitter::handle {
                background: #30363D;
                height: 4px;
            }
        """)

        # Workspace Container (Drawer)
        self.workspace_container = QFrame()
        self.workspace_container.setObjectName("WorkspaceDrawer")
        self.workspace_container.setStyleSheet("""
            QFrame#WorkspaceDrawer {
                background: #0D1117;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        ws_layout = QVBoxLayout(self.workspace_container)
        ws_layout.setContentsMargins(10, 8, 10, 8)
        ws_layout.setSpacing(8)

        ws_header = QHBoxLayout()
        self.ws_title = QLabel("اختر أداة لبدء العمل")
        self.ws_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.ws_title.setStyleSheet("color: #58A6FF;")
        ws_header.addWidget(self.ws_title)

        self.favorite_btn = QPushButton("☆ إضافة للمفضلة")
        self.favorite_btn.setFixedHeight(26)
        self.favorite_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #E6EDF3;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
            }
            QPushButton:hover { background: #30363D; color: #F0F6FC; }
        """)
        self.favorite_btn.clicked.connect(self._toggle_current_favorite)
        ws_header.addWidget(self.favorite_btn)
        ws_header.addStretch()

        self.close_drawer_btn = QPushButton("إغلاق مساحة العمل ✕")
        self.close_drawer_btn.setFixedHeight(26)
        self.close_drawer_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 11px;
            }
            QPushButton:hover { background: #DA3633; color: #FFFFFF; }
        """)
        self.close_drawer_btn.clicked.connect(self._close_workspace)
        ws_header.addWidget(self.close_drawer_btn)
        ws_layout.addLayout(ws_header)

        self.workspace = SplitViewWorkspace(self.workspace_container)
        self.workspace.execute_requested.connect(self._on_execute_tool)
        self.workspace.pass_to_pipeline_requested.connect(self._on_pass_to_pipeline)
        ws_layout.addWidget(self.workspace, 1)

        self.workspace_container.setVisible(False)
        self.main_content_splitter.addWidget(self.workspace_container)

        # Tools Grid Scroll Area
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setStyleSheet("background: transparent;")

        self.cards_widget = QWidget()
        self.cards_grid = QGridLayout(self.cards_widget)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(12)

        self.cards_scroll.setWidget(self.cards_widget)
        self.main_content_splitter.addWidget(self.cards_scroll)

        main_layout.addWidget(self.main_content_splitter, 1)

        # Initial render of cards
        self._refresh_tools_grid()

    def _on_input_detected(self, raw_input: str):
        """Analyzes input via SmartActionResolver and populates quick action buttons."""
        res = SmartActionResolver.resolve_recommended_tools(raw_input)
        tools = res["recommended_tools"]
        type_label = res["type_label"]
        self.drop_zone.update_actions(type_label, tools, self.open_tool)

    def _on_search_changed(self, text: str):
        self._refresh_tools_grid(query=text)

    def _on_category_selected(self, category: str):
        self.active_category = category
        self._refresh_tools_grid(query=self.search_edit.text(), category=category)

    def _refresh_tools_grid(self, query: str = "", category: Optional[str] = None):
        """Renders tool cards according to active search query and category."""
        # Clear grid
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat = category or self.active_category
        if cat == "favorites":
            fav_ids = set(self.db.get_favorites())
            all_tools = QuickToolRegistry.get_all_tools()
            tools = [t for t in all_tools if t.id in fav_ids]
        else:
            tools = QuickToolRegistry.search(query, cat)

        if not tools:
            empty_lbl = QLabel("لم يتم العثور على أدوات تطابق البحث.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setFont(QFont("Segoe UI", 11))
            empty_lbl.setStyleSheet("color: #8B949E; padding: 40px;")
            self.cards_grid.addWidget(empty_lbl, 0, 0, 1, 3)
            return

        cols = 3
        for idx, tool in enumerate(tools):
            card = self._create_tool_card(tool)
            row = idx // cols
            col = idx % cols
            self.cards_grid.addWidget(card, row, col)

    def _create_tool_card(self, tool: QuickToolDefinition) -> QFrame:
        """Constructs a responsive card widget for a single Quick Tool."""
        card = QFrame()
        card.setObjectName("ToolCard")
        card.setStyleSheet("""
            QFrame#ToolCard {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame#ToolCard:hover {
                border-color: #0078D4;
                background: #1F242C;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(tool.icon, "#58A6FF", 20).pixmap(20, 20))
        hdr.addWidget(icon_lbl)

        title = QLabel(tool.title_ar)
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setStyleSheet("color: #E6EDF3;")
        hdr.addWidget(title, 1)

        fav_star = "★" if self.db.is_favorite(tool.id) else "☆"
        star_btn = QPushButton(fav_star)
        star_btn.setFixedSize(24, 24)
        star_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #E3B341;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { color: #F2CC60; }
        """)
        star_btn.clicked.connect(lambda _, tid=tool.id, b=star_btn: self._toggle_favorite_card(tid, b))
        hdr.addWidget(star_btn)
        layout.addLayout(hdr)

        # Description
        desc = QLabel(tool.description_ar)
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #8B949E;")
        desc.setWordWrap(True)
        layout.addWidget(desc, 1)

        # Footer Action Button
        btn = QPushButton("فتح الأداة ➔")
        btn.setFixedHeight(28)
        btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #58A6FF;
                border: 1px solid #30363D;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1F6FEB; color: #FFFFFF; border-color: #1F6FEB; }
        """)
        btn.clicked.connect(lambda _, t=tool: self.open_tool(t))
        layout.addWidget(btn)

        return card

    def open_tool(self, tool: QuickToolDefinition):
        """Activates the workspace drawer for the specified tool."""
        self.active_tool = tool
        self.db.record_tool_usage(tool.id)

        self.ws_title.setText(f"{tool.title_ar}")
        is_fav = self.db.is_favorite(tool.id)
        self.favorite_btn.setText("★ بالمفضلة" if is_fav else "☆ إضافة للمفضلة")

        # If drop zone has text, seed workspace input
        current_input = self.drop_zone.inline_input.text().strip()
        if current_input:
            self.workspace.set_input_text(current_input)

        # Show workspace drawer
        self.workspace_container.setVisible(True)
        self.main_content_splitter.setSizes([350, 400])

        # Execute immediately if appropriate (e.g. text already present)
        if current_input:
            self._on_execute_tool(current_input, {})

    def _toggle_current_favorite(self):
        if self.active_tool:
            is_fav = self.db.toggle_favorite(self.active_tool.id)
            self.favorite_btn.setText("★ بالمفضلة" if is_fav else "☆ إضافة للمفضلة")
            self._refresh_tools_grid(self.search_edit.text())

    def _toggle_favorite_card(self, tool_id: str, btn: QPushButton):
        is_fav = self.db.toggle_favorite(tool_id)
        btn.setText("★" if is_fav else "☆")

    def _close_workspace(self):
        self.workspace_container.setVisible(False)
        self.active_tool = None

    def _on_pass_to_pipeline(self, output_text: str):
        """Passes result output into input zone to enable chaining multiple tools sequentially."""
        self.workspace.set_input_text(output_text)
        self.workspace.status_lbl.setText("تم تمرير المخرجات كمدخل جديد. يمكنك الآن اختيار أداة أخرى لتطبيقها.")

    def _on_execute_tool(self, input_text: str, options: dict):
        """Executes active tool handler and updates output pane."""
        if not self.active_tool:
            return

        tid = self.active_tool.id
        try:
            # 1. Hash Calculator
            if tid == "hash_calculator":
                import os
                if os.path.isfile(input_text.strip("\"'")):
                    res = HashTools.compute_file_hash(input_text.strip("\"'"), algorithm="SHA-256")
                else:
                    res = HashTools.compute_text_hash(input_text, algorithm="SHA-256")
                self.workspace.set_output_text(res)

            # 2. Base64
            elif tid == "base64_tool":
                res = EncodingTools.text_to_base64(input_text)
                self.workspace.set_output_text(res)

            # 3. QR Generator
            elif tid in ("qr_generator", "wifi_qr"):
                pix = QrBarcodeTools.generate_styled_qr(input_text, size=280)
                self.workspace.set_output_pixmap(pix)

            # 4. Barcode Generator
            elif tid == "barcode_generator":
                pix = QrBarcodeTools.generate_barcode(input_text)
                self.workspace.set_output_pixmap(pix)

            # 5. Password Generator
            elif tid == "password_generator":
                passwords = [PasswordTools.generate_password(16) for _ in range(5)]
                self.workspace.set_output_text("\n".join(passwords))

            # 6. Passphrase Generator
            elif tid == "passphrase_generator":
                phrases = [PasswordTools.generate_passphrase(4) for _ in range(5)]
                self.workspace.set_output_text("\n".join(phrases))

            # 7. Password Strength
            elif tid == "password_strength":
                st = PasswordTools.estimate_password_strength(input_text)
                report = (
                    f"التقييم: {st['label_ar']}\n"
                    f"الإنتروبيا: {st['entropy_bits']} بت (Bits)\n"
                    f"الطول: {st['length']} محرف\n"
                    f"التوصيات:\n- " + "\n- ".join(st["recommendations"])
                )
                self.workspace.set_output_text(report)

            # 8. Text Cleaner
            elif tid == "text_cleaner":
                res = TextTools.clean_text(input_text, trim_lines=True, remove_empty_lines=True, normalize_spaces=True)
                self.workspace.set_output_text(res)

            # 9. Duplicate Lines Remover
            elif tid == "duplicate_lines_remover":
                res, dups = TextTools.remove_duplicate_lines(input_text)
                self.workspace.set_output_text(f"# تم حذف {dups} سطر مكرر:\n" + res)

            # 10. Sort Lines
            elif tid == "sort_lines":
                res = TextTools.sort_lines(input_text, order="NATURAL")
                self.workspace.set_output_text(res)

            # 11. Change Case
            elif tid == "change_case":
                res = TextTools.change_case(input_text, mode="UPPERCASE")
                self.workspace.set_output_text(res)

            # 12. Word Counter
            elif tid == "word_counter":
                m = TextTools.calculate_text_metrics(input_text)
                report = (
                    f"عدد الكلمات: {m['words']:,}\n"
                    f"عدد الأحرف (مع المسافات): {m['chars']:,}\n"
                    f"عدد الأحرف (بدون مسافات): {m['chars_no_spaces']:,}\n"
                    f"عدد الأسطر: {m['lines']:,}\n"
                    f"عدد الفقرات: {m['paragraphs']:,}\n"
                    f"حجم النص في الذاكرة: {m['utf8_bytes']:,} بايت (UTF-8)\n"
                    f"وقت القراءة التقديري: ≈ {m['reading_time_min']} دقيقة"
                )
                self.workspace.set_output_text(report)

            # 13. Arabic Cleaner
            elif tid == "arabic_cleaner":
                res = TextTools.clean_arabic_text(input_text)
                self.workspace.set_output_text(res)

            # 14. Invisible Characters
            elif tid == "invisible_chars":
                res = TextTools.remove_invisible_characters(input_text)
                self.workspace.set_output_text(res)

            # 15. Line Endings
            elif tid == "line_endings":
                res = TextTools.convert_line_endings(input_text, "CRLF")
                self.workspace.set_output_text(res)

            # 16. Entity Extractor
            elif tid == "entity_extractor":
                emails = TextTools.extract_entities(input_text, "emails")
                urls = TextTools.extract_entities(input_text, "urls")
                res = []
                if emails:
                    res.append("# عناوين البريد الإلكتروني المستخرجة:")
                    res.extend(emails)
                if urls:
                    res.append("\n# روابط الويب المستخرجة:")
                    res.extend(urls)
                self.workspace.set_output_text("\n".join(res) if res else "لم يتم العثور على إيميلات أو روابط.")

            # 17. Scientific Calculator
            elif tid == "scientific_calculator":
                eval_res = CalculatorTools.evaluate_expression(input_text)
                if eval_res["is_valid"]:
                    self.workspace.set_output_text(f"= {eval_res['result']}")
                else:
                    self.workspace.set_output_text(f"خطأ: {eval_res['error']}")

            # 18. JSON Formatter
            elif tid == "json_formatter":
                jf = DeveloperTools.format_json(input_text, indent=2)
                if jf["is_valid"]:
                    self.workspace.set_output_text(jf["result"])
                else:
                    self.workspace.set_output_text(f"{jf['error']}\n\nالنص الأصلي:\n{jf['result']}")

            # 19. File Inspector
            elif tid == "file_inspector":
                clean_p = input_text.strip("\"'")
                import os
                if os.path.isfile(clean_p):
                    info = FileTools.inspect_file(clean_p)
                    report = (
                        f"اسم الملف: {info['name']}\n"
                        f"المسار الكامل: {info['full_path']}\n"
                        f"الحجم: {info['size_human']} ({info['size_bytes']:,} بايت)\n"
                        f"تاريخ التعديل: {info['modified']}\n"
                        f"تاريخ الإنشاء: {info['created']}\n"
                        f"السمات: {', '.join(info['attributes']) or 'عادي'}\n"
                        f"نوع المحتوى: {info['mime_type']}\n"
                        f"امتداد مزدوج مشبوه: {'نعم ⚠️' if info['is_double_ext'] else 'لا (سليم)'}"
                    )
                    self.workspace.set_output_text(report)
                else:
                    self.workspace.set_output_text("يرجى إدخال مسار ملف صالح.")

            # 20. Copy Path Variants
            elif tid == "copy_path_variants":
                clean_p = input_text.strip("\"'")
                import os
                if os.path.exists(clean_p):
                    vars_map = FileTools.get_path_copy_variants(clean_p)
                    report = (
                        f"Windows Path:\n{vars_map['win_path']}\n\n"
                        f"Quoted:\n{vars_map['quoted']}\n\n"
                        f"PowerShell:\n{vars_map['powershell']}\n\n"
                        f"Python raw string:\n{vars_map['python_raw']}\n\n"
                        f"Web URI:\n{vars_map['uri']}"
                    )
                    self.workspace.set_output_text(report)
                else:
                    self.workspace.set_output_text("المسار غير موجود على القرص.")

            # 21. Folder Size
            elif tid == "folder_size_stats":
                clean_p = input_text.strip("\"'")
                import os
                if os.path.isdir(clean_p):
                    stats = FolderTools.calculate_folder_stats(clean_p)
                    report = (
                        f"المجلد: {stats['folder_name']}\n"
                        f"الحجم الإجمالي: {stats['size_human']} ({stats['total_bytes']:,} بايت)\n"
                        f"عدد الملفات: {stats['total_files']:,}\n"
                        f"عدد المجلدات الفرعية: {stats['total_folders']:,}\n"
                        f"أكبر ملف: {stats['largest_file']} ({stats['largest_file_size']})\n"
                        f"أحدث تعديل: {stats['newest_file']} ({stats['newest_date']})\n\n"
                        f"أكثر الامتدادات تكراراً:\n" +
                        "\n".join(f"- {ext}: {cnt} ملف" for ext, cnt in stats['top_extensions'])
                    )
                    self.workspace.set_output_text(report)
                else:
                    self.workspace.set_output_text("يرجى إدخال مسار مجلد صالح.")

            # Default fallback for other tools
            else:
                if self.active_tool.handler:
                    res = self.active_tool.handler(input_text)
                    self.workspace.set_output_text(str(res))
                else:
                    self.workspace.set_output_text("تم استلام الأمر.")

        except Exception as e:
            self.workspace.set_output_text(f"حدث خطأ أثناء التنفيذ: {e}")

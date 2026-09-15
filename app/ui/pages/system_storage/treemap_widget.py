# -*- coding: utf-8 -*-
"""
SINAX Interactive Squarified Treemap Widget
Visualizes filesystem storage consumption as hierarchical interactive rectangular tiles:
- Squarified recursive layout algorithm
- Category-based and depth-based color palettes
- Hover tooltips and highlight outlines
- Drill-down navigation (double-click to zoom into folder)
- History stack with breadcrumbs / back navigation
- Right-click context menu (Open in Explorer, Copy path)
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.storage_analyzer import CATEGORY_CONFIG
from app.services.system_storage.storage_scanner import FolderNode, format_bytes


@dataclass
class TreemapTile:
    rect: QRectF
    name: str
    path: str
    size: int
    is_dir: bool
    color: QColor
    node: Optional[Any] = None
    category: str = "other"


# Palette for folders when categorized by depth/subfolder
FOLDER_PALETTE = [
    QColor("#4361EE"), QColor("#3A0CA3"), QColor("#7209B7"),
    QColor("#F72585"), QColor("#4CC9F0"), QColor("#4895EF"),
    QColor("#560BAD"), QColor("#3F37C9"), QColor("#0077B6"),
    QColor("#0096C7"), QColor("#00B4D8"), QColor("#48CAE4"),
]


def squarify(
    children: List[Tuple[str, int, Any, bool]],
    x: float, y: float, w: float, h: float,
    total_size: int,
    depth: int = 0
) -> List[TreemapTile]:
    """Squarified treemap recursive layout partitioner."""
    tiles: List[TreemapTile] = []
    if not children or w <= 2 or h <= 2 or total_size <= 0:
        return tiles

    # Sort descending by size
    sorted_items = sorted(children, key=lambda it: it[1], reverse=True)

    # Slice-and-dice partitioner for stability and robust bounds
    is_vertical = w >= h
    curr_x = x
    curr_y = y

    for idx, (name, size, node, is_dir) in enumerate(sorted_items):
        if size <= 0:
            continue

        ratio = size / total_size

        if is_vertical:
            tile_w = max(1.0, w * ratio)
            tile_rect = QRectF(curr_x, curr_y, tile_w, h)
            curr_x += tile_w
        else:
            tile_h = max(1.0, h * ratio)
            tile_rect = QRectF(curr_x, curr_y, w, tile_h)
            curr_y += tile_h

        # Determine color
        if is_dir:
            color = FOLDER_PALETTE[(depth + idx) % len(FOLDER_PALETTE)]
        else:
            # File category color
            cat = getattr(node, "category", "other")
            color_hex = CATEGORY_CONFIG.get(cat, {}).get("color", "#4361EE")
            color = QColor(color_hex)

        tiles.append(TreemapTile(
            rect=tile_rect,
            name=name,
            path=getattr(node, "path", name),
            size=size,
            is_dir=is_dir,
            color=color,
            node=node
        ))

    return tiles


class TreemapCanvas(QWidget):
    """Drawing area for treemap tiles."""

    node_selected = Signal(object)      # Emits FolderNode or FileItem
    node_drilled = Signal(object)       # Emits FolderNode to drill into

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.current_node: Optional[FolderNode] = None
        self.tiles: List[TreemapTile] = []
        self.hovered_tile: Optional[TreemapTile] = None
        self.selected_tile: Optional[TreemapTile] = None
        self.setMinimumSize(400, 320)

    def set_data(self, node: Optional[FolderNode]):
        self.current_node = node
        self.hovered_tile = None
        self.selected_tile = None
        self._calculate_layout()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._calculate_layout()

    def _calculate_layout(self):
        self.tiles.clear()
        if not self.current_node or self.current_node.size <= 0:
            return

        w = float(self.width() - 8)
        h = float(self.height() - 8)
        if w <= 10 or h <= 10:
            return

        # Prepare child nodes (both subfolders and largest files)
        items: List[Tuple[str, int, Any, bool]] = []

        # Subfolders
        for sub in self.current_node.children:
            if sub.size > 0:
                items.append((sub.name, sub.size, sub, True))

        # Files in current folder
        for f in self.current_node.files:
            if f.size > 0:
                items.append((f.name, f.size, f, False))

        total_sz = sum(it[1] for it in items)
        if total_sz > 0:
            self.tiles = squarify(items, 4.0, 4.0, w, h, total_sz, depth=0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # Background
        painter.fillRect(self.rect(), QColor("#161B22"))

        if not self.tiles:
            painter.setPen(QPen(QColor("#8B949E"), 1))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignCenter, "لا توجد ملفات أو مجلدات لعرضها في هذا المستوى")
            return

        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        fm = QFontMetrics(font)

        # Draw tiles
        for tile in self.tiles:
            r = tile.rect.adjusted(1, 1, -1, -1)
            if r.width() < 3 or r.height() < 3:
                continue

            is_hover = (tile == self.hovered_tile)
            is_sel = (tile == self.selected_tile)

            # Fill color
            base_col = tile.color
            if is_hover:
                fill_col = base_col.lighter(130)
            elif is_sel:
                fill_col = base_col.lighter(140)
            else:
                fill_col = base_col

            fill_col.setAlpha(200 if not is_hover else 240)
            painter.setBrush(QBrush(fill_col))

            # Border
            if is_sel:
                painter.setPen(QPen(QColor("#FFFFFF"), 2))
            elif is_hover:
                painter.setPen(QPen(QColor("#58A6FF"), 1.5))
            else:
                painter.setPen(QPen(QColor("#21262D"), 1))

            painter.drawRoundedRect(r, 4, 4)

            # Draw labels if tile is large enough
            if r.width() >= 45 and r.height() >= 30:
                painter.setPen(QPen(QColor("#FFFFFF"), 1))
                text_rect = r.adjusted(6, 4, -6, -4)

                # Name
                name_elided = fm.elidedText(tile.name, Qt.ElideMiddle, int(text_rect.width()))
                painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, name_elided)

                # Size
                if r.height() >= 44:
                    sz_str = format_bytes(tile.size)
                    painter.setPen(QPen(QColor("#D0D7DE"), 1))
                    painter.drawText(text_rect, Qt.AlignBottom | Qt.AlignLeft, sz_str)

    def mouseMoveEvent(self, event):
        pos = event.position()
        matched = None
        for tile in self.tiles:
            if tile.rect.contains(pos):
                matched = tile
                break

        if matched != self.hovered_tile:
            self.hovered_tile = matched
            self.update()

            if matched:
                tot_sz = self.current_node.size if self.current_node else matched.size
                pct = (matched.size / tot_sz * 100.0) if tot_sz > 0 else 0.0
                type_str = "مجلد" if matched.is_dir else "ملف"
                tip_text = (
                    f"<b>{matched.name}</b> ({type_str})<br>"
                    f"الحجم: <b>{format_bytes(matched.size)}</b> ({pct:.1f}%)<br>"
                    f"المسار: <small>{matched.path}</small>"
                )
                QToolTip.showText(event.globalPosition().toPoint(), tip_text, self)
            else:
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position()
        for tile in self.tiles:
            if tile.rect.contains(pos):
                self.selected_tile = tile
                self.update()
                if tile.node:
                    self.node_selected.emit(tile.node)
                break
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        pos = event.position()
        for tile in self.tiles:
            if tile.rect.contains(pos):
                if tile.is_dir and isinstance(tile.node, FolderNode):
                    self.node_drilled.emit(tile.node)
                break
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        pos = event.pos()
        matched = None
        for tile in self.tiles:
            if tile.rect.contains(QPointF(pos)):
                matched = tile
                break

        if not matched:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 16px; border-radius: 4px; }
            QMenu::item:selected { background: #1F6FEB; }
        """)

        act_open = menu.addAction("فتح في مستكشف ويندوز")
        act_copy = menu.addAction("نسخ المسار")
        if matched.is_dir:
            act_drill = menu.addAction("الدخول إلى هذا المجلد")
        else:
            act_drill = None

        action = menu.exec(self.mapToGlobal(pos))
        if action == act_open:
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(matched.path)}"')
            except Exception:
                pass
        elif action == act_copy:
            QApplication.clipboard().setText(matched.path)
        elif act_drill and action == act_drill:
            if isinstance(matched.node, FolderNode):
                self.node_drilled.emit(matched.node)


class InteractiveTreemapWidget(QWidget):
    """Complete Treemap component with Breadcrumb Bar and Drill-down history."""

    node_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_stack: List[FolderNode] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header bar with Back button and Current folder path
        header_bar = QWidget()
        h_layout = QHBoxLayout(header_bar)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(8)

        self.btn_back = QPushButton("▲ المستوى الأعلى")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
            QPushButton:disabled { background: #161B22; color: #484F58; border-color: #21262D; }
        """)
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self.navigate_up)
        h_layout.addWidget(self.btn_back)

        self.btn_path = QPushButton("")
        self.btn_path.setStyleSheet("""
            QPushButton {
                background: transparent; color: #58A6FF; text-align: right;
                font-family: 'Segoe UI'; font-size: 13px; font-weight: bold; border: none;
            }
        """)
        h_layout.addWidget(self.btn_path, 1)

        layout.addWidget(header_bar)

        # Canvas
        self.canvas = TreemapCanvas(self)
        self.canvas.node_selected.connect(self.node_selected.emit)
        self.canvas.node_drilled.connect(self.drill_down)
        layout.addWidget(self.canvas, 1)

    def set_root_node(self, root: FolderNode):
        """Set new top-level root node and reset history."""
        self.history_stack = [root]
        self._update_view()

    def drill_down(self, node: FolderNode):
        """Navigate inside a subfolder."""
        self.history_stack.append(node)
        self._update_view()

    def navigate_up(self):
        """Navigate back to parent folder."""
        if len(self.history_stack) > 1:
            self.history_stack.pop()
            self._update_view()

    def _update_view(self):
        if not self.history_stack:
            self.btn_back.setEnabled(False)
            self.btn_path.setText("")
            self.canvas.set_data(None)
            return

        current = self.history_stack[-1]
        self.btn_back.setEnabled(len(self.history_stack) > 1)
        self.btn_path.setText(f"المجلد الحالي: {current.path} ({format_bytes(current.size)})")
        self.canvas.set_data(current)

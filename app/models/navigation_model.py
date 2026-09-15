# -*- coding: utf-8 -*-
"""
SINAX QML Navigation Model
Implements a reactive QAbstractListModel driving the QML Sidebar and navigation views.
Supports exclusive accordion folding, instant Arabic search filtering, and state tracking.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, Signal, Slot
from app.core.navigation_constants import NAVIGATION_SECTIONS


class NavigationItem:
    def __init__(
        self,
        item_id: str,
        title: str,
        icon: str,
        is_section: bool = False,
        is_sub: bool = False,
        parent_id: str = "",
        route: str = "",
        badge: str = "",
        is_visible: bool = True,
        is_open: bool = False
    ):
        self.item_id = item_id
        self.title = title
        self.icon = icon
        self.is_section = is_section
        self.is_sub = is_sub
        self.parent_id = parent_id
        self.route = route or item_id
        self.badge = badge
        self.is_visible = is_visible
        self.is_open = is_open


class NavigationModel(QAbstractListModel):
    """QAbstractListModel powering the QML modern sidebar."""

    IdRole = Qt.UserRole + 1
    ItemIdRole = IdRole
    TitleRole = Qt.UserRole + 2
    IconRole = Qt.UserRole + 3
    IsSectionRole = Qt.UserRole + 4
    IsSubRole = Qt.UserRole + 5
    ParentIdRole = Qt.UserRole + 6
    RouteRole = Qt.UserRole + 7
    BadgeRole = Qt.UserRole + 8
    VisibleRole = Qt.UserRole + 9
    IsOpenRole = Qt.UserRole + 10

    openSectionChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[NavigationItem] = []
        self._current_open_section: Optional[str] = "file_manager"
        self._search_query: str = ""
        self._build_model()

    def _build_model(self):
        self.beginResetModel()
        self._items.clear()

        for sec in NAVIGATION_SECTIONS:
            sec_id = sec["id"]
            sec_type = sec.get("type", "item")
            is_sec = (sec_type == "section" and "children" in sec)

            # Add Parent Section / Single Item
            parent_item = NavigationItem(
                item_id=sec_id,
                title=sec["title"],
                icon=sec.get("icon", sec_id),
                is_section=is_sec,
                is_sub=False,
                parent_id="",
                route=sec_id,
                badge="",
                is_visible=True,
                is_open=(sec_id == self._current_open_section)
            )
            self._items.append(parent_item)

            # Add Children
            if is_sec:
                for ch in sec["children"]:
                    ch_id = ch["id"]
                    is_ch_vis = (sec_id == self._current_open_section)
                    child_item = NavigationItem(
                        item_id=ch_id,
                        title=ch["title"],
                        icon=ch.get("icon", "file"),
                        is_section=False,
                        is_sub=True,
                        parent_id=sec_id,
                        route=ch_id,
                        badge="قريباً" if ch.get("upcoming") else "",
                        is_visible=is_ch_vis,
                        is_open=False
                    )
                    self._items.append(child_item)

        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None

        item = self._items[index.row()]
        if role == self.IdRole:
            return item.item_id
        elif role == self.TitleRole:
            return item.title
        elif role == self.IconRole:
            return item.icon
        elif role == self.IsSectionRole:
            return item.is_section
        elif role == self.IsSubRole:
            return item.is_sub
        elif role == self.ParentIdRole:
            return item.parent_id
        elif role == self.RouteRole:
            return item.route
        elif role == self.BadgeRole:
            return item.badge
        elif role == self.VisibleRole:
            return item.is_visible
        elif role == self.IsOpenRole:
            return item.is_open
        return None

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            self.IdRole: QByteArray(b"itemId"),
            self.TitleRole: QByteArray(b"itemTitle"),
            self.IconRole: QByteArray(b"itemIcon"),
            self.IsSectionRole: QByteArray(b"isSection"),
            self.IsSubRole: QByteArray(b"isSub"),
            self.ParentIdRole: QByteArray(b"parentId"),
            self.RouteRole: QByteArray(b"route"),
            self.BadgeRole: QByteArray(b"badge"),
            self.VisibleRole: QByteArray(b"itemVisible"),
            self.IsOpenRole: QByteArray(b"isOpen")
        }

    @property
    def current_open_section(self) -> Optional[str]:
        return self._current_open_section

    @Slot(str)
    def toggle_section(self, sec_id: str):
        """Exclusive Accordion: toggles clicked section and closes other sections."""
        new_open = None if self._current_open_section == sec_id else sec_id
        self._current_open_section = new_open

        for item in self._items:
            if item.is_section:
                item.is_open = (item.item_id == new_open)
            elif item.is_sub:
                item.is_visible = (item.parent_id == new_open)

        first_idx = self.index(0, 0)
        last_idx = self.index(len(self._items) - 1, 0)
        self.dataChanged.emit(first_idx, last_idx, [self.VisibleRole, self.IsOpenRole])
        self.openSectionChanged.emit(new_open or "")

    @Slot()
    def close_section(self):
        """Closes any open section."""
        if self._current_open_section is not None:
            self._current_open_section = None
            for item in self._items:
                if item.is_section:
                    item.is_open = False
                elif item.is_sub:
                    item.is_visible = False

            first_idx = self.index(0, 0)
            last_idx = self.index(len(self._items) - 1, 0)
            self.dataChanged.emit(first_idx, last_idx, [self.VisibleRole, self.IsOpenRole])
            self.openSectionChanged.emit("")

    @Slot(str)
    def expand_for_route(self, route_id: str):
        """Auto-expands the parent section of a route if it is a child sub-item."""
        target_parent = None
        for item in self._items:
            if item.item_id == route_id:
                target_parent = item.parent_id or (item.item_id if item.is_section else None)
                break

        if target_parent and target_parent != self._current_open_section:
            self._current_open_section = target_parent
            for item in self._items:
                if item.is_section:
                    item.is_open = (item.item_id == target_parent)
                elif item.is_sub:
                    item.is_visible = (item.parent_id == target_parent)

            first_idx = self.index(0, 0)
            last_idx = self.index(len(self._items) - 1, 0)
            self.dataChanged.emit(first_idx, last_idx, [self.VisibleRole, self.IsOpenRole])
            self.openSectionChanged.emit(target_parent or "")

    @Slot(str)
    def filter_by_search(self, query: str):
        """Instant Arabic search filtering."""
        q = query.strip().lower()
        self._search_query = q

        if not q:
            # Restore normal accordion state
            for item in self._items:
                if item.is_sub:
                    item.is_visible = (item.parent_id == self._current_open_section)
                else:
                    item.is_visible = True
                    if item.is_section:
                        item.is_open = (item.item_id == self._current_open_section)
        else:
            # Find matching items
            matched_parents = set()
            for item in self._items:
                if q in item.title.lower() or q in item.item_id.lower():
                    if item.is_sub:
                        matched_parents.add(item.parent_id)

            for item in self._items:
                if item.is_section:
                    is_match = (q in item.title.lower()) or (item.item_id in matched_parents)
                    item.is_visible = is_match
                    item.is_open = True
                elif item.is_sub:
                    item.is_visible = (q in item.title.lower() or item.parent_id in matched_parents)
                else:
                    item.is_visible = (q in item.title.lower() or q in item.item_id.lower())

        first_idx = self.index(0, 0)
        last_idx = self.index(len(self._items) - 1, 0)
        self.dataChanged.emit(first_idx, last_idx, [self.VisibleRole, self.IsOpenRole])

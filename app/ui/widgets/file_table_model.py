# -*- coding: utf-8 -*-
"""
SINAX File Table Model
High-performance virtualized QAbstractTableModel for displaying tens of thousands of files
with zero interface stutter.
"""

from typing import List, Optional, Any
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush, QFont

from app.models.file_item import FileItem

HEADERS = [
    "☑",
    "#",
    "اسم الملف الحالي",
    "الاسم الجديد (المعاينة)",
    "النوع",
    "الامتداد",
    "الحجم",
    "تاريخ آخر تعديل",
    "المسار الكامل"
]

class FileTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: List[FileItem] = []
        self._filtered_items: List[FileItem] = []
        self._filter_text: str = ""

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filtered_items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return HEADERS[section]
            elif role == Qt.TextAlignmentRole:
                return int(Qt.AlignCenter)
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._filtered_items):
            return None

        item = self._filtered_items[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return ""  # Rendered via CheckState
            elif col == 1:
                return str(index.row() + 1)
            elif col == 2:
                return item.original_name
            elif col == 3:
                return item.new_name or item.original_name
            elif col == 4:
                return item.category_label
            elif col == 5:
                return item.extension
            elif col == 6:
                return item.formatted_size
            elif col == 7:
                return item.modified_time.strftime("%Y-%m-%d %H:%M") if item.modified_time else "-"
            elif col == 8:
                return str(item.path.parent)

        elif role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if item.is_selected else Qt.Unchecked

        elif role == Qt.TextAlignmentRole:
            if col in (0, 1, 4, 5, 6, 7):
                return int(Qt.AlignCenter)
            return int(Qt.AlignRight | Qt.AlignVCenter)

        elif role == Qt.ForegroundRole:
            if col == 3:
                if item.has_conflict:
                    return QBrush(QColor("#FF4D4F"))  # Red for conflict
                elif item.is_changed:
                    return QBrush(QColor("#52C41A"))  # Green for changed
            elif col == 0 and item.has_conflict:
                return QBrush(QColor("#FF4D4F"))

        elif role == Qt.ToolTipRole:
            if item.has_conflict:
                return f"تنبيه: {item.conflict_reason}"
            if col == 3 and item.is_changed:
                return f"الاسم الجديد: {item.new_name}"
            return str(item.path)

        elif role == Qt.FontRole:
            if col == 3 and (item.is_changed or item.has_conflict):
                font = QFont()
                font.setBold(True)
                return font

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or index.row() >= len(self._filtered_items):
            return False

        item = self._filtered_items[index.row()]
        if index.column() == 0 and role == Qt.CheckStateRole:
            item.is_selected = (value == Qt.Checked.value or value == Qt.Checked)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            flags |= Qt.ItemIsUserCheckable

        return flags

    def set_items(self, items: List[FileItem]) -> None:
        """Sets new list of items and updates view."""
        self.beginResetModel()
        self._all_items = list(items)
        self._apply_filter()
        self.endResetModel()

    def add_items(self, items: List[FileItem]) -> None:
        """Appends chunk of items incrementally."""
        if not items:
            return
        
        start_row = len(self._filtered_items)
        self._all_items.extend(items)
        
        # Check filter
        matching = []
        for i in items:
            if not self._filter_text or self._filter_text in i.original_name.lower() or self._filter_text in i.new_name.lower():
                matching.append(i)

        if matching:
            self.beginInsertRows(QModelIndex(), start_row, start_row + len(matching) - 1)
            self._filtered_items.extend(matching)
            self.endInsertRows()

    def set_filter(self, text: str) -> None:
        """Filters displayed rows by search query."""
        self._filter_text = text.lower().strip()
        self.beginResetModel()
        self._apply_filter()
        self.endResetModel()

    def _apply_filter(self) -> None:
        if not self._filter_text:
            self._filtered_items = list(self._all_items)
        else:
            self._filtered_items = [
                i for i in self._all_items
                if self._filter_text in i.original_name.lower() or self._filter_text in i.new_name.lower()
            ]

    def select_all(self, select: bool = True) -> None:
        """Selects or deselects all filtered items."""
        for item in self._filtered_items:
            item.is_selected = select
        if self._filtered_items:
            first_idx = self.index(0, 0)
            last_idx = self.index(len(self._filtered_items) - 1, 0)
            self.dataChanged.emit(first_idx, last_idx, [Qt.CheckStateRole])

    def invert_selection(self) -> None:
        """Inverts check state of current filtered items."""
        for item in self._filtered_items:
            item.is_selected = not item.is_selected
        if self._filtered_items:
            first_idx = self.index(0, 0)
            last_idx = self.index(len(self._filtered_items) - 1, 0)
            self.dataChanged.emit(first_idx, last_idx, [Qt.CheckStateRole])

    def get_selected_items(self) -> List[FileItem]:
        """Returns all checked items in the model."""
        return [i for i in self._all_items if i.is_selected]

    def get_all_items(self) -> List[FileItem]:
        return list(self._all_items)

    def refresh_previews(self) -> None:
        """Notifies the table view that preview columns have changed."""
        if self._filtered_items:
            first_idx = self.index(0, 2)
            last_idx = self.index(len(self._filtered_items) - 1, 3)
            self.dataChanged.emit(first_idx, last_idx, [Qt.DisplayRole, Qt.ForegroundRole, Qt.FontRole])

    def remove_item_at(self, row: int) -> Optional[FileItem]:
        """Removes a row from the list."""
        if 0 <= row < len(self._filtered_items):
            item = self._filtered_items[row]
            self.beginRemoveRows(QModelIndex(), row, row)
            self._filtered_items.remove(item)
            if item in self._all_items:
                self._all_items.remove(item)
            self.endRemoveRows()
            return item
        return None

    def item_at(self, row: int) -> Optional[FileItem]:
        if 0 <= row < len(self._filtered_items):
            return self._filtered_items[row]
        return None

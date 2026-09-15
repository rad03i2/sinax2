# -*- coding: utf-8 -*-
"""
File Change Monitor Subpage (مراقبة التغييرات الحية - FIM) for SINAX Privacy & Security Center.
Features:
1. Real-time folder & file watcher with baseline tracking.
2. Dynamic ignore filter rules for noisy temp files (*.tmp, ~*, __pycache__).
3. Live event streaming feed (CREATED, MODIFIED, DELETED, RENAMED) with cryptographic hash tracking.
4. Objective alerts with zero false-positive malware labelling.
"""

from datetime import datetime
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.privacy_security.file_monitor_service import FileChangeEvent, FileMonitorService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class FileMonitorSubpage(QWidget):
    """Real-Time File Integrity & Change Monitor (FIM) Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._monitor_service = FileMonitorService(self)
        self._monitor_service.file_changed.connect(self._on_file_changed)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # 1. Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.btn_back = QPushButton(" العودة للرئيسية")
        self.btn_back.setIcon(get_icon("arrow_back", color="#8B949E"))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #161B22; color: #8B949E; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #21262D; color: #F0F6FC; }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        t_lbl = QLabel("مراقبة التغييرات الحية (Change Monitoring & FIM)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("مراقبة فورية للمجلدات والملفات الحساسة وكشف أي إنشاء أو تعديل أو حذف تلقائياً مع تصفية الضوضاء.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        main_layout.addLayout(header_row)

        # 2. Main Content Splitter (Left: Monitored Folders / Right: Live Events)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Right Panel: Monitored items manager
        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0, 0, 8, 0)
        lp_layout.setSpacing(10)

        # Add Folder Row
        add_box = QFrame()
        add_box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        ab_vbox = QVBoxLayout(add_box)
        ab_vbox.setSpacing(8)

        lbl_add = QLabel("إضافة مجلد للمراقبة:")
        lbl_add.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 12px;")
        ab_vbox.addWidget(lbl_add)

        ab_row = QHBoxLayout()
        btn_add_folder = QPushButton(" إضافة مجلد...")
        btn_add_folder.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_add_folder.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        btn_add_folder.clicked.connect(self._on_add_folder)
        ab_row.addWidget(btn_add_folder)

        btn_pin_file = QPushButton(" تثبيت ملف مهم...")
        btn_pin_file.setIcon(get_icon("pin", color="#38BDF8"))
        btn_pin_file.setStyleSheet("""
            QPushButton {
                background-color: #1E293B; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #38BDF8; color: #0D1117; }
        """)
        btn_pin_file.clicked.connect(self._on_pin_file)
        ab_row.addWidget(btn_pin_file)
        ab_vbox.addLayout(ab_row)

        lp_layout.addWidget(add_box)

        # Monitored List
        lbl_list = QLabel("المجلدات والملفات المراقبة حالياً:")
        lbl_list.setStyleSheet("color: #8B949E; font-size: 12px; font-weight: bold;")
        lp_layout.addWidget(lbl_list)

        self.list_monitored = QListWidget()
        self.list_monitored.setStyleSheet("""
            QListWidget {
                background-color: #0D1117; border: 1px solid #30363D; border-radius: 6px;
                color: #F0F6FC; padding: 4px;
            }
            QListWidget::item {
                padding: 6px; border-bottom: 1px solid #161B22; border-radius: 4px;
            }
            QListWidget::item:hover { background-color: #161B22; }
            QListWidget::item:selected { background-color: #1F6FEB; color: #FFFFFF; }
        """)
        lp_layout.addWidget(self.list_monitored, 1)

        btn_remove = QPushButton(" إزالة المسار المحدد من المراقبة")
        btn_remove.setIcon(get_icon("delete", color="#F87171"))
        btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #161B22; color: #F87171; border: 1px solid #F87171;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2D1418; }
        """)
        btn_remove.clicked.connect(self._on_remove_selected)
        lp_layout.addWidget(btn_remove)

        # Noise Filter info
        filter_box = QFrame()
        filter_box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px;")
        fb_vbox = QVBoxLayout(filter_box)
        fb_vbox.setSpacing(4)
        lbl_fb_t = QLabel("تصفية الضوضاء التلقائية:")
        lbl_fb_t.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        fb_vbox.addWidget(lbl_fb_t)

        lbl_fb_desc = QLabel("يتم تلقائياً استبعاد الملفات المؤقتة: *.tmp, ~*, __pycache__, .cache*, *.log")
        lbl_fb_desc.setWordWrap(True)
        lbl_fb_desc.setStyleSheet("color: #6E7681; font-size: 10px;")
        fb_vbox.addWidget(lbl_fb_desc)
        lp_layout.addWidget(filter_box)

        splitter.addWidget(left_panel)

        # Left Panel: Live Events Table
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(8, 0, 0, 0)
        rp_layout.setSpacing(10)

        # Bar: Title + Status + Clear
        bar_row = QHBoxLayout()
        lbl_stream = QLabel("سجل التغييرات الحية (Live Event Feed):")
        lbl_stream.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        bar_row.addWidget(lbl_stream)

        self.lbl_status_badge = QLabel("المراقبة خاملة (أضف مجلداً للبدء)")
        self.lbl_status_badge.setStyleSheet("color: #8B949E; font-size: 11px; font-weight: bold; background: #161B22; padding: 3px 8px; border-radius: 4px;")
        bar_row.addWidget(self.lbl_status_badge)

        bar_row.addStretch(1)

        btn_clear = QPushButton(" مسح السجل")
        btn_clear.setIcon(get_icon("trash", color="#8B949E"))
        btn_clear.setStyleSheet("""
            QPushButton {
                background: #161B22; color: #8B949E; border: 1px solid #30363D;
                border-radius: 4px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background: #21262D; color: #F0F6FC; }
        """)
        btn_clear.clicked.connect(self._clear_events)
        bar_row.addWidget(btn_clear)
        rp_layout.addLayout(bar_row)

        # Live Events Table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(5)
        self.events_table.setHorizontalHeaderLabels(["الوقت", "نوع الحدث", "اسم الملف", "المسار الكامل", "التفاصيل / بصمة الهاش"])
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.events_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 6px;
            }
        """)
        rp_layout.addWidget(self.events_table, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([320, 680])
        main_layout.addWidget(splitter, 1)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلداً لمراقبته فورياً")
        if folder:
            ok, msg = self._monitor_service.add_folder_to_monitor(folder)
            if ok:
                item = QListWidgetItem(f"📁 {Path(folder).name}  ({folder})")
                item.setData(Qt.UserRole, ("folder", folder))
                self.list_monitored.addItem(item)
                self._update_status_badge()
            else:
                QMessageBox.warning(self, "تنبيه", msg)

    def _on_pin_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً حساساً لتثبيته ومراقبته", "", "كافة الملفات (*.*)")
        if file_path:
            ok, msg = self._monitor_service.pin_file_to_monitor(file_path)
            if ok:
                item = QListWidgetItem(f"📌 {Path(file_path).name}  ({file_path})")
                item.setData(Qt.UserRole, ("file", file_path))
                self.list_monitored.addItem(item)
                self._update_status_badge()
            else:
                QMessageBox.warning(self, "تنبيه", msg)

    def _on_remove_selected(self):
        row = self.list_monitored.currentRow()
        if row < 0:
            return

        item = self.list_monitored.item(row)
        data = item.data(Qt.UserRole)
        if data:
            item_type, path = data
            if item_type == "folder":
                self._monitor_service.remove_folder_from_monitor(path)
            elif item_type == "file":
                self._monitor_service.unpin_file(path)

        self.list_monitored.takeItem(row)
        self._update_status_badge()

    def _update_status_badge(self):
        count = self.list_monitored.count()
        if count > 0:
            self.lbl_status_badge.setText(f"المراقبة الحية نشطة ({count} مسارات مراقبة)")
            self.lbl_status_badge.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; background: #132E22; padding: 3px 8px; border-radius: 4px;")
        else:
            self.lbl_status_badge.setText("المراقبة خاملة (أضف مجلداً للبدء)")
            self.lbl_status_badge.setStyleSheet("color: #8B949E; font-size: 11px; font-weight: bold; background: #161B22; padding: 3px 8px; border-radius: 4px;")

    def _on_file_changed(self, event: FileChangeEvent):
        row = self.events_table.rowCount()
        self.events_table.insertRow(row)

        time_str = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
        it_time = QTableWidgetItem(time_str)
        self.events_table.setItem(row, 0, it_time)

        # Event type
        it_type = QTableWidgetItem(event.event_type)
        if event.event_type == "CREATED":
            it_type.setForeground(QColor("#38BDF8"))
        elif event.event_type == "MODIFIED":
            it_type.setForeground(QColor("#FBBF24"))
        elif event.event_type == "DELETED":
            it_type.setForeground(QColor("#F87171"))
        elif event.event_type == "RENAMED":
            it_type.setForeground(QColor("#A78BFA"))
        self.events_table.setItem(row, 1, it_type)

        p = Path(event.file_path)
        self.events_table.setItem(row, 2, QTableWidgetItem(p.name))
        it_p = QTableWidgetItem(str(p))
        it_p.setToolTip(str(p))
        self.events_table.setItem(row, 3, it_p)

        detail = event.details
        if event.new_hash:
            detail += f" [SHA: {event.new_hash[:10]}...]"
        self.events_table.setItem(row, 4, QTableWidgetItem(detail))

        self.events_table.scrollToBottom()

    def _clear_events(self):
        self.events_table.setRowCount(0)

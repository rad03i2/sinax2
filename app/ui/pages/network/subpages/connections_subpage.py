# -*- coding: utf-8 -*-
"""
SINAX Connections & Open Ports Subpage (صفحة الاتصالات الحية والمنافذ المفتوحة)
Shows live TCP/UDP sockets linked to application PIDs and names, and provides a local port availability checker.
"""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.network.connection_service import ConnectionRecord, ConnectionService
from app.ui.icons import get_icon


class ConnectionsSubpage(QWidget):
    """Subpage for viewing network sockets and inspecting port usage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._all_connections: List[ConnectionRecord] = []
        self._init_ui()
        self.refresh_connections()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # 1. Header Toolbar
        top_bar = QHBoxLayout()
        title = QLabel("الاتصالات الحية والمنافذ المفتوحة (Active Connections & Ports)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = QPushButton("  تحديث الاتصالات")
        self.refresh_btn.setIcon(get_icon("sync", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_connections)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 2. Port Inspector Bar ("من يستخدم المنفذ؟")
        port_card = QFrame()
        port_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 12px;")
        port_l = QHBoxLayout(port_card)
        port_l.setSpacing(10)

        lbl = QLabel("فحص منفذ محلي (Port):")
        lbl.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        port_l.addWidget(lbl)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("أدخل رقم المنفذ مثلاً: 8080 أو 3000")
        self.port_input.setFixedHeight(36)
        self.port_input.setStyleSheet("""
            QLineEdit {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0 10px;
                color: #FFFFFF;
            }
            QLineEdit:focus { border-color: #0078D4; }
        """)
        port_l.addWidget(self.port_input, 1)

        check_btn = QPushButton("فحص التوفر واستعلام البرنامج")
        check_btn.setFixedHeight(36)
        check_btn.setStyleSheet("background: #334155; color: white; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        check_btn.clicked.connect(self._inspect_port)
        port_l.addWidget(check_btn)

        layout.addWidget(port_card)

        # Filter row
        filter_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("بحث باسم البرنامج أو العنوان أو المنفذ...")
        self.search_box.setFixedHeight(34)
        self.search_box.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 6px; padding: 0 10px; color: white;")
        self.search_box.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search_box, 1)

        self.established_chk = QCheckBox("الاتصالات النشطة فقط (ESTABLISHED)")
        self.established_chk.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.established_chk.stateChanged.connect(self._apply_filter)
        filter_row.addWidget(self.established_chk)
        layout.addLayout(filter_row)

        # 3. Connections Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "اسم البرنامج (Process)", "PID", "البروتوكول", "العنوان المحلي", "المنفذ المحلي", "العنوان البعيد", "الحالة"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(380)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #FFFFFF;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background: #0F172A;
                color: #94A3B8;
                border: none;
                padding: 6px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_connections(self):
        self._all_connections = ConnectionService.get_active_connections()
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_box.text().strip().lower()
        est_only = self.established_chk.isChecked()

        filtered = []
        for c in self._all_connections:
            if est_only and c.state != "ESTABLISHED":
                continue
            if query:
                match = (
                    query in c.process_name.lower() or
                    query in str(c.pid) or
                    query in str(c.local_port) or
                    query in c.local_address or
                    query in c.remote_address
                )
                if not match:
                    continue
            filtered.append(c)

        self.table.setRowCount(len(filtered))
        for row, c in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(c.process_name))
            self.table.setItem(row, 1, QTableWidgetItem(str(c.pid or "—")))
            self.table.setItem(row, 2, QTableWidgetItem(c.protocol))
            self.table.setItem(row, 3, QTableWidgetItem(c.local_address))
            self.table.setItem(row, 4, QTableWidgetItem(str(c.local_port)))
            rem_str = f"{c.remote_address}:{c.remote_port}" if c.remote_port else c.remote_address
            self.table.setItem(row, 5, QTableWidgetItem(rem_str))
            self.table.setItem(row, 6, QTableWidgetItem(c.state))

    def _inspect_port(self):
        txt = self.port_input.text().strip()
        try:
            p = int(txt)
            if not (1 <= p <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال رقم منفذ صحيح بين 1 و 65535.")
            return

        is_free, msg = ConnectionService.test_local_port_availability(p)
        if is_free:
            QMessageBox.information(self, f"نتيجة فحص المنفذ {p}", msg)
        else:
            QMessageBox.warning(self, f"نتيجة فحص المنفذ {p}", msg)

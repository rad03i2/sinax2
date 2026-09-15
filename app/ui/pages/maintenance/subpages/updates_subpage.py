# -*- coding: utf-8 -*-
"""
Windows Update & Pending Restart Subpage for SINAX.
Displays official Windows Update status, pending reboot causes,
and direct shortcuts to official Microsoft troubleshooters.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.reboot_state_service import RebootStateService
from app.services.maintenance.update_service import WindowsUpdateService
from app.ui.icons import get_icon


class UpdatesSubpage(QWidget):
    """Subpage for Windows Update intelligence and pending reboot detection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Pending Reboot Card
        self.reboot_card = QFrame()
        self.reboot_card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        rb_lay = QHBoxLayout(self.reboot_card)
        rb_lay.setSpacing(14)

        self.rb_icon = QLabel()
        self.rb_icon.setPixmap(get_icon("history", color_hex="#38BDF8", size=36).pixmap(36, 36))
        rb_lay.addWidget(self.rb_icon)

        rb_col = QVBoxLayout()
        rb_col.setSpacing(3)
        self.lbl_rb_title = QLabel("حالة إعادة تشغيل Windows")
        self.lbl_rb_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        self.lbl_rb_desc = QLabel("جاري التحقق من إشارات النظام...")
        self.lbl_rb_desc.setStyleSheet("font-size: 12px; color: #8B949E;")
        rb_col.addWidget(self.lbl_rb_title)
        rb_col.addWidget(self.lbl_rb_desc)
        rb_lay.addLayout(rb_col, 1)

        self.btn_restart_now = QPushButton("إعادة التشغيل الآن")
        self.btn_restart_now.setStyleSheet("""
            QPushButton {
                background-color: #B91C1C;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #991B1B;
            }
        """)
        self.btn_restart_now.clicked.connect(self._prompt_restart)
        rb_lay.addWidget(self.btn_restart_now)

        layout.addWidget(self.reboot_card)

        # 2. Windows Update Section
        upd_header = QHBoxLayout()
        u_title = QLabel("تحديثات Windows الرسمية:")
        u_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        upd_header.addWidget(u_title)
        upd_header.addStretch(1)

        btn_check_upd = QPushButton("تحديث الحالة")
        btn_check_upd.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_check_upd.clicked.connect(self.refresh_data)
        upd_header.addWidget(btn_check_upd)

        btn_open_settings = QPushButton("فتح إعدادات Windows Update")
        btn_open_settings.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        btn_open_settings.clicked.connect(WindowsUpdateService.open_windows_update)
        upd_header.addWidget(btn_open_settings)

        btn_troubleshoot = QPushButton("مصحح أخطاء التحديثات")
        btn_troubleshoot.clicked.connect(WindowsUpdateService.open_update_troubleshooter)
        upd_header.addWidget(btn_troubleshoot)

        layout.addLayout(upd_header)

        # Table of updates
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["عنوان التحديث", "رقم المقالة (KB)", "إعادة التشغيل مطلوبة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
                color: #C9D1D9;
            }
            QHeaderView::section {
                background-color: #0D1117;
                color: #8B949E;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table, 1)

    def refresh_data(self):
        # 1. Fast pending reboot check (instant via registry)
        is_pending, reasons = RebootStateService.check_pending_reboot()
        if is_pending:
            self.lbl_rb_title.setText("تنبيه: Windows ينتظر إعادة تشغيل لإكمال الصيانة")
            self.lbl_rb_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F87171;")
            self.lbl_rb_desc.setText(" • ".join(reasons))
            self.btn_restart_now.setVisible(True)
        else:
            self.lbl_rb_title.setText("حالة الإقلاع: لا توجد عمليات إعادة تشغيل معلقة")
            self.lbl_rb_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #34D399;")
            self.lbl_rb_desc.setText("كافة التحديثات وحزم الصيانة تم تطبيقها بنجاح والنظام مستقر.")
            self.btn_restart_now.setVisible(False)

        # 2. Windows Updates in background thread to prevent UI freezing
        import threading
        def worker():
            try:
                upd = WindowsUpdateService.get_update_status()
                updates_list = upd.get("updates_list", [])
                QTimer.singleShot(0, lambda: self._apply_updates_list(updates_list))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True, name="WinUpdateWorkerThread").start()

    def _apply_updates_list(self, updates_list):
        self.table.setRowCount(len(updates_list))
        for idx, u in enumerate(updates_list):
            self.table.setItem(idx, 0, QTableWidgetItem(u.get("Title", "تحديث Windows")))
            self.table.setItem(idx, 1, QTableWidgetItem(u.get("KB", "غير محدد")))
            self.table.setItem(idx, 2, QTableWidgetItem("نعم" if u.get("RebootRequired") else "لا"))

    def _prompt_restart(self):
        reply = QMessageBox.question(
            self,
            "تأكيد إعادة تشغيل الجهاز",
            "هل ترغب بإعادة تشغيل Windows الآن لإكمال تثبيت التحديثات وعمليات الصيانة؟\n"
            "يرجى حفظ أي أعمال مفتوحة قبل المتابعة.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            RebootStateService.request_restart(delay_seconds=10)
            QMessageBox.information(self, "إعادة التشغيل", "تمت جدولة إعادة التشغيل خلال 10 ثوانٍ.")

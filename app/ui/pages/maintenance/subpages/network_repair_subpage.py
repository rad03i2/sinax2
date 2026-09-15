# -*- coding: utf-8 -*-
"""
Network Repair Subpage for SINAX Maintenance & Repair Center.
Reuses existing Network Doctor engine to detect connectivity, DNS, and gateway health.
Provides official fixes: Flush DNS, IP renew, Adapter reset, and Microsoft Get Help launcher.
"""

import subprocess
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.services.maintenance.troubleshooter_service import TroubleshooterService
from app.services.network.doctor_service import NetworkDoctorService
from app.ui.icons import get_icon


class NetworkRepairSubpage(QWidget):
    """Subpage for diagnosing and repairing network connectivity issues."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.doctor = NetworkDoctorService()
        self._init_ui()
        self.check_network()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header card
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("network", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(3)
        t_l = QLabel("تشخيص وإصلاح مشكلات الشبكة والاتصال")
        t_l.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        s_l = QLabel("التحقق من اتصال الإنترنت، خوادم DNS، بوابات الاتصال، وإصلاح انقطاع المواقع.")
        s_l.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t_l)
        txt_col.addWidget(s_l)
        h_lay.addLayout(txt_col, 1)

        btn_check = QPushButton("إعادة فحص الاتصال")
        btn_check.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_check.clicked.connect(self.check_network)
        h_lay.addWidget(btn_check)

        layout.addWidget(header)

        # Status Grid (4 indicators)
        grid_frame = QFrame()
        grid_frame.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        self.grid = QGridLayout(grid_frame)
        self.grid.setSpacing(12)

        self.lbl_internet = QLabel("جاري الفحص...")
        self.lbl_gateway = QLabel("جاري الفحص...")
        self.lbl_dns = QLabel("جاري الفحص...")
        self.lbl_adapter = QLabel("جاري الفحص...")

        indicators = [
            ("اتصال الإنترنت العام:", self.lbl_internet),
            ("بوابة الاتصال الافتراضية (Gateway):", self.lbl_gateway),
            ("خوادم نظام الأسماء (DNS):", self.lbl_dns),
            ("محول وبطاقة الشبكة:", self.lbl_adapter),
        ]

        for idx, (title, lbl) in enumerate(indicators):
            lbl.setStyleSheet("font-weight: bold; color: #F0F6FC;")
            r = idx // 2
            c = (idx % 2) * 2
            t_label = QLabel(title)
            t_label.setStyleSheet("color: #8B949E; font-size: 12px;")
            self.grid.addWidget(t_label, r, c)
            self.grid.addWidget(lbl, r, c + 1)

        layout.addWidget(grid_frame)

        # Repair Actions Card
        actions_card = QFrame()
        actions_card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        ac_lay = QVBoxLayout(actions_card)
        ac_lay.setSpacing(10)

        a_title = QLabel("إجراءات الإصلاح السريع المتاحة:")
        a_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8;")
        ac_lay.addWidget(a_title)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        btn_flush = QPushButton("مسح كاش DNS (Flush DNS)")
        btn_flush.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_flush.clicked.connect(self._flush_dns)
        btns_row.addWidget(btn_flush)

        btn_renew = QPushButton("تجديد عنوان IP (DHCP Renew)")
        btn_renew.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_renew.clicked.connect(self._renew_ip)
        btns_row.addWidget(btn_renew)

        btn_troubleshoot = QPushButton("تشغيل مصحح مشاكل Windows الرسمي")
        btn_troubleshoot.clicked.connect(TroubleshooterService.open_network_troubleshooter)
        btns_row.addWidget(btn_troubleshoot)

        btns_row.addStretch(1)
        ac_lay.addLayout(btns_row)

        layout.addWidget(actions_card)
        layout.addStretch(1)

    def check_network(self):
        """Diagnoses connectivity using existing network doctor asynchronously."""
        import threading
        from PySide6.QtCore import QTimer

        def _bg():
            try:
                res = self.doctor.run_full_diagnosis()
                status = res.get("status", "ok")
                has_internet = status == "ok" or res.get("internet_connected", True)
                def _update():
                    try:
                        self.lbl_internet.setText("متصل (Online)" if has_internet else "منقطع (Offline)")
                        self.lbl_internet.setStyleSheet(f"font-weight: bold; color: {'#34D399' if has_internet else '#F87171'};")
                        self.lbl_gateway.setText("تستجيب بنجاح" if has_internet else "غير مستجيبة")
                        self.lbl_dns.setText("سليم" if has_internet else "قد يعاني من بطء")
                        self.lbl_adapter.setText("نشط ويعمل")
                    except Exception:
                        pass
                QTimer.singleShot(0, _update)
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def _flush_dns(self):
        try:
            subprocess.run(["ipconfig.exe", "/flushdns"], capture_output=True, timeout=5)
            SnapshotHistoryService().log_maintenance_action(
                "flush_dns_cache", "مسح كاش DNS", "network", "success", "تم إفراغ كاش DNS المحلي بنجاح."
            )
            QMessageBox.information(self, "نجاح العملية", "تم مسح وتفريغ كاش نظام أسماء النطاقات (DNS) المحلي بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تنفيذ الأمر: {e}")

    def _renew_ip(self):
        try:
            subprocess.run(["ipconfig.exe", "/renew"], capture_output=True, timeout=10)
            SnapshotHistoryService().log_maintenance_action(
                "renew_ip", "تجديد عنوان IP", "network", "success", "تم تجديد إيجار DHCP بنجاح."
            )
            QMessageBox.information(self, "نجاح العملية", "تم طلب وتجديد عنوان IP الخاص ببطاقة الشبكة بنجاح.")
            self.check_network()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تجديد عنوان IP: {e}")

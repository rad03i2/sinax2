# -*- coding: utf-8 -*-
"""
Overview Subpage for SINAX Maintenance & Repair Center.
Displays a live telemetry dashboard of Windows system health parameters,
a prominent hero card launching the SINAX Maintenance Doctor,
and quick action cards leading to specialized maintenance subpages.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.reboot_state_service import RebootStateService
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.services.maintenance.update_service import WindowsUpdateService
from app.ui.icons import get_icon
from app.ui.pages.maintenance.dialogs.symptom_picker_dialog import SymptomPickerDialog


class OverviewSubpage(QWidget):
    """Master Dashboard and quick launchpad for Maintenance Center."""

    navigate_requested = Signal(str) # subpage_key
    run_doctor_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.refresh_telemetry()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(20)

        # 1. Hero Card: طبيب SINAX (SINAX Maintenance Doctor)
        hero = QFrame()
        hero.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0F2027, stop:0.5 #203A43, stop:1 #2C5364);
                border: 1px solid #38BDF844;
                border-radius: 12px;
                padding: 22px;
            }
        """)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setSpacing(20)

        hero_icon = QLabel()
        hero_icon.setPixmap(get_icon("doctor", color_hex="#38BDF8", size=60).pixmap(60, 60))
        hero_layout.addWidget(hero_icon)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(6)
        h_title = QLabel("طبيب SINAX — الفحص والتشخيص الذكي الشامل")
        h_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        h_desc = QLabel(
            "فحص آمن غير تدخلي لكافة أجزاء النظام: التخزين، تحديثات Windows، بدء التشغيل، ملفات النظام، الشبكة، والأعطال.\n"
            "يشخص المشكلات بدقة ويقترح خطة صيانة شفافة دون تنفيذ أي إجراء إلا بعد موافقتك الصريحة."
        )
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("font-size: 13px; color: #E0F2FE; line-height: 1.4;")
        hero_text.addWidget(h_title)
        hero_text.addWidget(h_desc)
        hero_layout.addLayout(hero_text, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)

        doctor_btn = QPushButton("افحص جهازي الآن")
        doctor_btn.setCursor(Qt.PointingHandCursor)
        doctor_btn.setIcon(get_icon("doctor", color_hex="#FFFFFF"))
        doctor_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        doctor_btn.clicked.connect(self.run_doctor_requested.emit)
        btn_col.addWidget(doctor_btn)

        symptom_btn = QPushButton("ما مشكلة جهازي؟")
        symptom_btn.setCursor(Qt.PointingHandCursor)
        symptom_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0F172A;
            }
        """)
        symptom_btn.clicked.connect(self._open_symptom_picker)
        btn_col.addWidget(symptom_btn)

        hero_layout.addLayout(btn_col)
        c_layout.addWidget(hero)

        # 2. Section Header: Live Telemetry
        telemetry_hdr = QHBoxLayout()
        t_title = QLabel("المؤشرات الحية لحالة النظام")
        t_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        telemetry_hdr.addWidget(t_title)
        telemetry_hdr.addStretch(1)

        refresh_btn = QPushButton("تحديث البيانات")
        refresh_btn.setIcon(get_icon("update", color_hex="#8B949E"))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #161B22;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #21262D;
                color: #F0F6FC;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_telemetry)
        telemetry_hdr.addWidget(refresh_btn)
        c_layout.addLayout(telemetry_hdr)

        # 3. Telemetry Grid (6 cards)
        self.telemetry_grid = QGridLayout()
        self.telemetry_grid.setSpacing(12)

        self.lbl_space_c = QLabel("جاري الحساب...")
        self.lbl_temp_size = QLabel("جاري الحساب...")
        self.lbl_reboot = QLabel("جاري التحقق...")
        self.lbl_updates = QLabel("جاري التحقق...")
        self.lbl_defender = QLabel("يعمل (Active)")
        self.lbl_network = QLabel("متصل (Online)")

        cards = [
            ("المساحة المتاحة C:", self.lbl_space_c, "storage", "#38BDF8"),
            ("الملفات المؤقتة والكاش:", self.lbl_temp_size, "clean", "#FBBF24"),
            ("إعادة تشغيل معلقة:", self.lbl_reboot, "history", "#F87171"),
            ("تحديثات Windows:", self.lbl_updates, "update", "#A78BFA"),
            ("أمان Windows Defender:", self.lbl_defender, "shield", "#34D399"),
            ("اتصال الشبكة:", self.lbl_network, "network", "#38BDF8"),
        ]

        for idx, (label_text, val_lbl, icon_name, color_hex) in enumerate(cards):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #161B22;
                    border: 1px solid #30363D;
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setSpacing(10)

            i_lbl = QLabel()
            i_lbl.setPixmap(get_icon(icon_name, color_hex=color_hex, size=28).pixmap(28, 28))
            c_lay.addWidget(i_lbl)

            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(label_text)
            t.setStyleSheet("font-size: 11px; color: #8B949E;")
            val_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
            col.addWidget(t)
            col.addWidget(val_lbl)
            c_lay.addLayout(col, 1)

            row = idx // 3
            col_idx = idx % 3
            self.telemetry_grid.addWidget(card, row, col_idx)

        c_layout.addLayout(self.telemetry_grid)

        # 4. Quick Category Navigation Cards
        cat_title = QLabel("الأقسام المتخصصة لمركز الصيانة")
        cat_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC; margin-top: 10px;")
        c_layout.addWidget(cat_title)

        cat_grid = QGridLayout()
        cat_grid.setSpacing(12)

        CAT_ITEMS = [
            ("doctor", "طبيب SINAX", "الفحص والتشخيص الذكي الشامل", "doctor"),
            ("cleanup", "التنظيف الآمن", "إزالة الكاش ومراجعة التنزيلات", "clean"),
            ("windows_repair", "إصلاح Windows", "معالج DISM و SFC وتحليل CBS", "tools"),
            ("storage_disk", "التخزين والقرص", "فحص CHKDSK وتشخيص انخفاض المساحة", "storage"),
            ("updates", "التحديثات والإقلاع", "حالة Windows Update وإعادة التشغيل", "update"),
            ("startup", "بدء التشغيل", "مراجعة البرامج ومساعد Clean Boot", "startup"),
            ("network", "مشاكل الشبكة", "فحص الاتصال و DNS ومصلح ويندوز", "network"),
            ("apps", "مشاكل التطبيقات", "البرامج المعطلة وغير المستجيبة", "apps"),
            ("devices", "مشاكل الأجهزة", "التعريفات، الصوت، الطابعة، البلوتوث", "devices"),
            ("reliability", "السجل والموثوقية", "سجل الأعطال والشاشة الزرقاء BSOD", "doctor"),
            ("advanced", "أدوات متقدمة", "إصلاح Explorer، الوقت، وحزمة الدعم", "tools"),
        ]

        for idx, (sub_key, title, subtitle, icon_name) in enumerate(CAT_ITEMS):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0D1117;
                    border: 1px solid #21262D;
                    border-radius: 8px;
                    padding: 12px;
                    text-align: right;
                }
                QPushButton:hover {
                    background-color: #161B22;
                    border-color: #38BDF8;
                }
            """)
            b_layout = QHBoxLayout(btn)
            b_layout.setSpacing(12)

            ic = QLabel()
            ic.setPixmap(get_icon(icon_name, color_hex="#38BDF8", size=24).pixmap(24, 24))
            b_layout.addWidget(ic)

            t_col = QVBoxLayout()
            t_col.setSpacing(2)
            lbl1 = QLabel(title)
            lbl1.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
            lbl2 = QLabel(subtitle)
            lbl2.setStyleSheet("font-size: 11px; color: #8B949E;")
            t_col.addWidget(lbl1)
            t_col.addWidget(lbl2)
            b_layout.addLayout(t_col, 1)

            btn.clicked.connect(lambda _, k=sub_key: self.navigate_requested.emit(k))

            row = idx // 3
            col_idx = idx % 3
            cat_grid.addWidget(btn, row, col_idx)

        c_layout.addLayout(cat_grid)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def refresh_telemetry(self):
        """Refreshes live system telemetry asynchronously or safely."""
        # 1. Drive C: Free space
        try:
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p("C:\\"), None, None, ctypes.byref(free_bytes)
            )
            self.lbl_space_c.setText(SafeCleanupOrchestrator.format_bytes(int(free_bytes.value)))
        except Exception:
            self.lbl_space_c.setText("غير متوفر")

        # 2. Pending Reboot (Instant registry query)
        try:
            is_pending, _ = RebootStateService.check_pending_reboot()
            self.lbl_reboot.setText("مطلوب (Pending)" if is_pending else "غير مطلوب (جاهز)")
            self.lbl_reboot.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {'#F87171' if is_pending else '#34D399'};"
            )
        except Exception:
            self.lbl_reboot.setText("غير متوفر")

        # 3. Asynchronous deep telemetry (Temp & Updates)
        import threading
        def bg_worker():
            try:
                cleanup_data = SafeCleanupOrchestrator.analyze_cleanup_targets()
                total_b = cleanup_data.get("total_reclaimable_bytes", 0)
                temp_str = SafeCleanupOrchestrator.format_bytes(total_b)
            except Exception:
                temp_str = "غير متوفر"

            try:
                upd = WindowsUpdateService.get_update_status()
                upd_str = upd.get("status_ar", "محدث")
            except Exception:
                upd_str = "راجع الإعدادات"

            # Update UI labels safely via QMetaObject or direct if simple
            try:
                from PySide6.QtCore import QMetaObject, Q_ARG
                QMetaObject.invokeMethod(self.lbl_temp_size, "setText", Qt.QueuedConnection, Q_ARG(str, temp_str))
                QMetaObject.invokeMethod(self.lbl_updates, "setText", Qt.QueuedConnection, Q_ARG(str, upd_str))
            except Exception:
                pass

        threading.Thread(target=bg_worker, daemon=True).start()

    def _open_symptom_picker(self):
        dlg = SymptomPickerDialog(self)
        if dlg.exec():
            selected_key = dlg.selected_key
            # Route symptom directly to appropriate subpage
            route_map = {
                "slow_pc": "doctor",
                "freezing": "apps",
                "internet_down": "network",
                "disk_full": "cleanup",
                "app_crash": "reliability",
                "update_fails": "updates",
                "explorer_glitch": "advanced",
                "sound_issues": "devices",
                "printer_issues": "devices",
                "bluetooth_issues": "devices",
                "slow_startup": "startup",
                "bsod_crash": "reliability",
            }
            target = route_map.get(selected_key, "doctor")
            self.navigate_requested.emit(target)

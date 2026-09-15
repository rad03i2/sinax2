# -*- coding: utf-8 -*-
"""
SINAX Backup & Sync Overview Subpage (لوحة القيادة الرئيسية).
Prominently features the three core pillars:
1. آخر نسخة (Last Backup Status)
2. سلامة النسخة (Backup Health & Integrity)
3. آخر اختبار استعادة (Proven Restore Drill Recency)
Includes visual protection coverage, connected external drive card, and quick launch tiles.
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
from app.services.backup_sync.backup_health_doctor import BackupHealthDoctor
from app.services.backup_sync.device_identity_service import DeviceIdentityService
from app.ui.icons import get_icon


class OverviewSubpage(QWidget):
    """Cockpit overview dashboard for SINAX Backup & Sync."""

    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.doctor = BackupHealthDoctor()
        self._init_ui()
        self.refresh_telemetry()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(18)

        # 1. Top Three Essential Pillars
        three_cards_row = QHBoxLayout()
        three_cards_row.setSpacing(14)

        # Card 1: Last Backup
        self.card_last_backup = self._create_metric_card(
            title="آخر نسخة احتياطية",
            value="جاري الفحص...",
            subtitle="الحالة: جاري التحقق",
            icon_name="backup",
            accent_hex="#38BDF8"
        )
        three_cards_row.addWidget(self.card_last_backup)

        # Card 2: Backup Health
        self.card_health = self._create_metric_card(
            title="سلامة النسخة والبيان",
            value="جاهز للتحقق",
            subtitle="البيان (Manifest) والتحقق",
            icon_name="security",
            accent_hex="#34D399"
        )
        three_cards_row.addWidget(self.card_health)

        # Card 3: Restore Drill Test
        self.card_drill = self._create_metric_card(
            title="آخر اختبار استعادة",
            value="جاهز للاختبار",
            subtitle="هل النسخة قابلة للاستعادة فعلاً؟",
            icon_name="doctor",
            accent_hex="#A78BFA"
        )
        three_cards_row.addWidget(self.card_drill)

        lay.addLayout(three_cards_row)

        # 2. Hero Action Card
        hero_card = QFrame()
        hero_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B2A3D, stop:1 #0D1B2A);
                border: 1px solid #1D4ED8;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        hero_lay = QHBoxLayout(hero_card)
        hero_lay.setSpacing(16)

        hero_icon = QLabel()
        hero_icon.setPixmap(get_icon("backup", color_hex="#38BDF8", size=48).pixmap(48, 48))
        hero_lay.addWidget(hero_icon)

        txt_col = QVBoxLayout()
        h_title = QLabel("احمِ ملفاتك المهمة بدون تعقيد")
        h_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        h_desc = QLabel("اكتشاف فوري للمجلدات الأساسية (سطح المكتب، المستندات، الصور) وحفظها بنقرة واحدة على قرص خارجي.")
        h_desc.setStyleSheet("font-size: 12px; color: #93C5FD;")
        txt_col.addWidget(h_title)
        txt_col.addWidget(h_desc)
        hero_lay.addLayout(txt_col)
        hero_lay.addStretch(1)

        btn_hero = QPushButton("احمِ ملفاتي الآن")
        btn_hero.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 22px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        btn_hero.clicked.connect(lambda: self.navigate_requested.emit("backup_sync_quick_backup"))
        hero_lay.addWidget(btn_hero)

        btn_wizard = QPushButton("معالج النسخ المتقدم")
        btn_wizard.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #F0F6FC;
                border: 1px solid #30363D;
                font-size: 12px;
                padding: 10px 18px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        btn_wizard.clicked.connect(lambda: self.navigate_requested.emit("backup_sync_wizard"))
        hero_lay.addWidget(btn_wizard)

        lay.addWidget(hero_card)

        # 3. Protection Coverage & Connected Drives Section
        grid_mid = QGridLayout()
        grid_mid.setSpacing(14)

        # Box A: Protection Coverage Breakdown
        card_coverage = QFrame()
        card_coverage.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        cov_lay = QVBoxLayout(card_coverage)
        cov_title = QLabel("تغطية حماية الملفات المهمة")
        cov_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        cov_lay.addWidget(cov_title)

        self.lbl_cov_desktop = QLabel("سطح المكتب: جاري الفحص")
        self.lbl_cov_docs = QLabel("المستندات: جاري الفحص")
        self.lbl_cov_pics = QLabel("الصور: جاري الفحص")
        for lbl in (self.lbl_cov_desktop, self.lbl_cov_docs, self.lbl_cov_pics):
            lbl.setStyleSheet("font-size: 12px; color: #8B949E; padding: 2px 0;")
            cov_lay.addWidget(lbl)
        cov_lay.addStretch(1)
        grid_mid.addWidget(card_coverage, 0, 0)

        # Box B: External Storage Drive
        card_drive = QFrame()
        card_drive.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        drv_lay = QVBoxLayout(card_drive)
        drv_title = QLabel("حالة وسائط النسخ الاحتياطي (USB / HDD)")
        drv_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        drv_lay.addWidget(drv_title)

        self.lbl_drv_status = QLabel("جاري اكتشاف الأقراص الخارجية المتصلة...")
        self.lbl_drv_status.setStyleSheet("font-size: 12px; color: #8B949E;")
        drv_lay.addWidget(self.lbl_drv_status)

        btn_drv = QPushButton("إدارة الأقراص الموثوقة والنسخ التلقائي")
        btn_drv.setStyleSheet("background-color: #21262D; color: #38BDF8; border: 1px solid #30363D; border-radius: 6px; padding: 6px;")
        btn_drv.clicked.connect(lambda: self.navigate_requested.emit("backup_sync_destinations"))
        drv_lay.addStretch(1)
        drv_lay.addWidget(btn_drv)
        grid_mid.addWidget(card_drive, 0, 1)

        lay.addLayout(grid_mid)

        # 4. Quick Actions Tiles
        actions_title = QLabel("الأقسام السريعة")
        actions_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC; margin-top: 6px;")
        lay.addWidget(actions_title)

        actions_grid = QGridLayout()
        actions_grid.setSpacing(10)

        tiles = [
            ("تجهيز الجهاز قبل الفورمات", "حزم الملفات والبرامج والتعريفات في أرشيف واحد", "system", "backup_sync_before_format"),
            ("مزامنة المجلدات", "مزامنة اتجاهين ومرآة مع سلة تراجع ومعاينة Dry Run", "sync", "backup_sync_sync"),
            ("استعادة الملفات", "البحث في النسخ واستعادة الملفات المحذوفة من الأصل", "restore", "backup_sync_restore"),
            ("اختبار الاستعادة (Drill)", "فحص هل النسخة قابلة للاستعادة فعلياً أم لا", "doctor", "backup_sync_health"),
        ]

        for i, (t_txt, d_txt, ic_name, route) in enumerate(tiles):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #161B22;
                    border: 1px solid #30363D;
                    border-radius: 8px;
                    padding: 12px;
                }
                QFrame:hover {
                    border-color: #38BDF8;
                }
            """)
            c_lay = QHBoxLayout(card)
            c_icon = QLabel()
            c_icon.setPixmap(get_icon(ic_name, color_hex="#38BDF8", size=24).pixmap(24, 24))
            c_lay.addWidget(c_icon)

            col = QVBoxLayout()
            ct = QLabel(t_txt)
            ct.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
            cd = QLabel(d_txt)
            cd.setStyleSheet("font-size: 11px; color: #8B949E;")
            col.addWidget(ct)
            col.addWidget(cd)
            c_lay.addLayout(col)
            c_lay.addStretch(1)

            btn_open = QPushButton("فتح")
            btn_open.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 14px;")
            btn_open.clicked.connect(lambda r=route: self.navigate_requested.emit(r))
            c_lay.addWidget(btn_open)

            actions_grid.addWidget(card, i // 2, i % 2)

        lay.addLayout(actions_grid)
        lay.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_metric_card(self, title: str, value: str, subtitle: str, icon_name: str, accent_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #161B22;
                border: 1px solid #30363D;
                border-top: 3px solid {accent_hex};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setSpacing(6)

        row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #8B949E;")
        i_lbl = QLabel()
        i_lbl.setPixmap(get_icon(icon_name, color_hex=accent_hex, size=20).pixmap(20, 20))
        row.addWidget(t_lbl)
        row.addStretch(1)
        row.addWidget(i_lbl)
        lay.addLayout(row)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("lbl_value")
        val_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        lay.addWidget(val_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("lbl_subtitle")
        sub_lbl.setStyleSheet("font-size: 11px; color: #8B949E;")
        lay.addWidget(sub_lbl)

        return card

    def refresh_telemetry(self):
        """Asynchronously updates dashboard cards."""
        import threading
        from PySide6.QtCore import QTimer

        def _bg():
            try:
                diag = self.doctor.diagnose_overall_health()
                drives = DeviceIdentityService.list_connected_external_drives()

                def _update():
                    try:
                        # Update Card 1
                        val_1 = self.card_last_backup.findChild(QLabel, "lbl_value")
                        sub_1 = self.card_last_backup.findChild(QLabel, "lbl_subtitle")
                        if val_1 and sub_1:
                            val_1.setText(diag.last_backup_time_str)
                            sub_1.setText(f"مستوى الحماية: {diag.protection_level_ar}")

                        # Update Card 2
                        val_2 = self.card_health.findChild(QLabel, "lbl_value")
                        sub_2 = self.card_health.findChild(QLabel, "lbl_subtitle")
                        if val_2 and sub_2:
                            val_2.setText(diag.last_verified_status)
                            sub_2.setText("تم فحص سلامة النسخ والبيان")

                        # Update Card 3
                        val_3 = self.card_drill.findChild(QLabel, "lbl_value")
                        sub_3 = self.card_drill.findChild(QLabel, "lbl_subtitle")
                        if val_3 and sub_3:
                            val_3.setText(diag.last_drill_status)
                            sub_3.setText("فحص الاستعادة العشوائي")

                        # Coverage labels
                        for f in diag.folders:
                            st = "✓ محمي" if f.is_protected else "✗ غير محمي"
                            color = "#34D399" if f.is_protected else "#F87171"
                            if f.folder_key == "desktop":
                                self.lbl_cov_desktop.setText(f"سطح المكتب: {st}")
                                self.lbl_cov_desktop.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")
                            elif f.folder_key == "documents":
                                self.lbl_cov_docs.setText(f"المستندات: {st}")
                                self.lbl_cov_docs.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")
                            elif f.folder_key == "pictures":
                                self.lbl_cov_pics.setText(f"الصور: {st}")
                                self.lbl_cov_pics.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")

                        # Connected Drives
                        if drives:
                            d = drives[0]
                            free_gb = d.free_bytes / (1024**3)
                            self.lbl_drv_status.setText(
                                f"متصل: {d.drive_letter} ({d.filesystem}) • متوفر {free_gb:.1f} GB"
                            )
                            self.lbl_drv_status.setStyleSheet("font-size: 12px; color: #34D399; font-weight: bold;")
                        else:
                            self.lbl_drv_status.setText("لا توجد أقراص خارجية متصلة حالياً.")
                            self.lbl_drv_status.setStyleSheet("font-size: 12px; color: #8B949E;")

                    except Exception:
                        pass

                QTimer.singleShot(0, _update)
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()

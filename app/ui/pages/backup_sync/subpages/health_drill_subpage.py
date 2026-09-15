# -*- coding: utf-8 -*-
"""
SINAX Backup Health & Restore Drill Subpage ("هل نسختي الاحتياطية قابلة للاستعادة؟").
Executes random test restore drills into a sandbox temp folder, verifying cryptographic
hashes and producing an honest, evidence-based health assessment without fake percentages.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.backup_health_doctor import BackupHealthDoctor
from app.services.backup_sync.restore_drill_service import RestoreDrillService
from app.ui.icons import get_icon


class HealthDrillSubpage(QWidget):
    """Cockpit for running automated restore drills and checking backup health."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.drill_service = RestoreDrillService(self.db)
        self.doctor = BackupHealthDoctor(self.db)
        self._init_ui()
        self.load_profiles()

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
        lay.setSpacing(16)

        # Header card
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #064E3B, stop:1 #0F172A);
                border: 1px solid #10B981;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("doctor", color_hex="#34D399", size=40).pixmap(40, 40))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("اختبار استعادة النسخة الاحتياطية (Restore Drill)")
        t.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("وجود نسخة احتياطية لا قيمة له إذا لم تكن قابلة للاستعادة! يقوم SINAX باختبار عينة عشوائية ومطابقة البصمة فورياً.")
        d.setStyleSheet("font-size: 12px; color: #A7F3D0;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        lay.addWidget(header)

        # Profile selection & Run Drill Box
        box_run = QFrame()
        box_run.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        b_lay = QVBoxLayout(box_run)
        b_lay.setSpacing(12)

        row_sel = QHBoxLayout()
        row_sel.addWidget(QLabel("اختر خطة النسخ للاختبار:"))
        self.combo_profile = QComboBox()
        self.combo_profile.setStyleSheet("background-color: #0D1117; color: white; border: 1px solid #30363D; padding: 6px; border-radius: 6px;")
        row_sel.addWidget(self.combo_profile, 1)

        self.btn_run_drill = QPushButton("تشغيل اختبار الاستعادة الآن")
        self.btn_run_drill.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        self.btn_run_drill.clicked.connect(self._run_drill)
        row_sel.addWidget(self.btn_run_drill)
        b_lay.addLayout(row_sel)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(14)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0D1117;
                border: 1px solid #30363D;
                border-radius: 7px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 6px;
            }
        """)
        b_lay.addWidget(self.prog_bar)

        self.lbl_drill_status = QLabel("جاهز لبدء الفحص...")
        self.lbl_drill_status.setStyleSheet("font-size: 12px; color: #8B949E;")
        b_lay.addWidget(self.lbl_drill_status)

        lay.addWidget(box_run)

        # Health assessment card
        self.card_diag = QFrame()
        self.card_diag.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        d_lay = QVBoxLayout(self.card_diag)
        self.lbl_diag_title = QLabel("تشخيص ومؤشرات حماية البيانات:")
        self.lbl_diag_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        d_lay.addWidget(self.lbl_diag_title)

        self.lbl_diag_body = QLabel("جاري التحليل...")
        self.lbl_diag_body.setStyleSheet("font-size: 13px; color: #C9D1D9; line-height: 1.6;")
        d_lay.addWidget(self.lbl_diag_body)
        lay.addWidget(self.card_diag)

        # 3-2-1 Rule card
        card_321 = QFrame()
        card_321.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        l_321 = QVBoxLayout(card_321)
        t_321 = QLabel("قاعدة الحماية الذهبية 3-2-1 (إرشاد هندسي):")
        t_321.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        l_321.addWidget(t_321)

        guidelines = [
            "• 3 نسخ: احتفظ دائماً بثلاث نسخ من ملفاتك الحيوية (النسخة الأصلية + نسختين احتياطيتين).",
            "• 2 وسائط تخزين: استخدم وسيطين مختلفين للتخزين (مثل قرص داخلي SSD + قرص خارجي HDD/USB).",
            "• 1 موقع معزول: احتفظ بنسخة واحدة مفصولة عن الجهاز لمنع فقدان البيانات عند حدوث أعطال فيزيائية."
        ]
        for g in guidelines:
            lbl = QLabel(g)
            lbl.setStyleSheet("font-size: 12px; color: #94A3B8; padding: 2px 0;")
            l_321.addWidget(lbl)

        lay.addWidget(card_321)
        lay.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_profiles(self):
        profiles = self.db.list_profiles()
        self.combo_profile.clear()
        for p in profiles:
            self.combo_profile.addItem(p.name, p.id)
        self._refresh_doctor()

    def _refresh_doctor(self):
        diag = self.doctor.diagnose_overall_health()
        recs = "• " + "\n• ".join(diag.recommendations) if diag.recommendations else "• جميع المؤشرات الحالية سليمة."
        txt = (
            f"<b>مستوى الحماية الحالي:</b> {diag.protection_level_ar}<br>"
            f"<b>المجلدات المحمية:</b> {diag.protected_folders_count} مجلدات مشمولة<br>"
            f"<b>تاريخ آخر نسخة:</b> {diag.last_backup_time_str}<br><br>"
            f"<b>التوصيات والملاحظات:</b><br>{recs}"
        )
        self.lbl_diag_body.setText(txt)

    def _run_drill(self):
        profile_id = self.combo_profile.currentData()
        if not profile_id:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار خطة نسخ احتياطي للاختبار.")
            return

        self.btn_run_drill.setEnabled(False)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(10)
        self.lbl_drill_status.setText("جاري استخراج عينات عشوائية واختبار البصمات...")

        import threading
        from PySide6.QtCore import QTimer

        def _worker():
            def _prog(done, total, msg):
                QTimer.singleShot(0, lambda: self.prog_bar.setValue(int((done / total) * 100)))
                QTimer.singleShot(0, lambda: self.lbl_drill_status.setText(msg))

            res = self.drill_service.run_drill(profile_id, sample_size=20, progress_cb=_prog)

            def _done():
                self.btn_run_drill.setEnabled(True)
                self.prog_bar.setValue(100)
                self.lbl_drill_status.setText(res.summary_ar)
                if res.is_healthy:
                    QMessageBox.information(self, "نتيجة اختبار الاستعادة", res.summary_ar)
                else:
                    QMessageBox.warning(self, "نتيجة اختبار الاستعادة", res.summary_ar)
                self._refresh_doctor()

            QTimer.singleShot(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

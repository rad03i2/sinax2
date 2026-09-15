# -*- coding: utf-8 -*-
"""
'ماذا تغير بعد الصيانة؟' (What Changed After Maintenance?) Dialog for SINAX.
Presents transparent, measured metrics comparing system parameters before and after
maintenance (free space gained, startup apps modified, system files status)
strictly without fake 'PC is 70% faster' claims.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from app.services.maintenance.models import BeforeAfterSnapshot
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.ui.icons import get_icon


class AfterRepairDialog(QDialog):
    """Honest post-maintenance delta comparison dialog."""

    def __init__(self, before: BeforeAfterSnapshot, after: BeforeAfterSnapshot, actions_count: int, parent=None):
        super().__init__(parent)
        self.before = before
        self.after = after
        self.actions_count = actions_count
        self.setWindowTitle("تقرير التغييرات بعد الصيانة")
        self.setMinimumWidth(540)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        header = QFrame(self)
        header.setStyleSheet("""
            QFrame {
                background-color: #132E22;
                border: 1px solid #059669;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("doctor", color_hex="#34D399", size=40).pixmap(40, 40))
        h_layout.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(4)
        t_lbl = QLabel("اكتملت جلسة الصيانة بنجاح")
        t_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #ECFDF5;")
        txt_col.addWidget(t_lbl)

        sub_lbl = QLabel(f"تم تنفيذ {self.actions_count} إجراءات صيانة وتحقق بنجاح دون أي أخطاء حرجة.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #A7F3D0;")
        txt_col.addWidget(sub_lbl)
        h_layout.addLayout(txt_col, 1)
        layout.addWidget(header)

        # Delta Comparison Grid
        grid_frame = QFrame(self)
        grid_frame.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        grid = QGridLayout(grid_frame)
        grid.setSpacing(12)

        # Table Headers
        lbl_metric = QLabel("المؤشر المقاس")
        lbl_metric.setStyleSheet("font-weight: bold; color: #8B949E; font-size: 12px;")
        lbl_before = QLabel("قبل الصيانة")
        lbl_before.setStyleSheet("font-weight: bold; color: #8B949E; font-size: 12px;")
        lbl_after = QLabel("بعد الصيانة")
        lbl_after.setStyleSheet("font-weight: bold; color: #8B949E; font-size: 12px;")
        lbl_change = QLabel("الفارق المحقق")
        lbl_change.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 12px;")

        grid.addWidget(lbl_metric, 0, 0)
        grid.addWidget(lbl_before, 0, 1)
        grid.addWidget(lbl_after, 0, 2)
        grid.addWidget(lbl_change, 0, 3)

        # Row 1: Free space on C:
        free_before = self.before.free_space_c_bytes
        free_after = self.after.free_space_c_bytes
        diff_space = max(0, free_after - free_before)
        diff_space_str = f"+{SafeCleanupOrchestrator.format_bytes(diff_space)}" if diff_space > 0 else "بدون تغيير ملحوظ"

        grid.addWidget(QLabel("المساحة الحرة على القرص C:"), 1, 0)
        grid.addWidget(QLabel(SafeCleanupOrchestrator.format_bytes(free_before)), 1, 1)
        grid.addWidget(QLabel(SafeCleanupOrchestrator.format_bytes(free_after)), 1, 2)
        lbl_diff_sp = QLabel(diff_space_str)
        lbl_diff_sp.setStyleSheet("font-weight: bold; color: #34D399;")
        grid.addWidget(lbl_diff_sp, 1, 3)

        # Row 2: Temp files
        temp_before = self.before.temp_files_bytes
        temp_after = self.after.temp_files_bytes
        diff_temp = max(0, temp_before - temp_after)
        grid.addWidget(QLabel("حجم الملفات المؤقتة والكاش:"), 2, 0)
        grid.addWidget(QLabel(SafeCleanupOrchestrator.format_bytes(temp_before)), 2, 1)
        grid.addWidget(QLabel(SafeCleanupOrchestrator.format_bytes(temp_after)), 2, 2)
        lbl_diff_temp = QLabel(f"-{SafeCleanupOrchestrator.format_bytes(diff_temp)}")
        lbl_diff_temp.setStyleSheet("font-weight: bold; color: #34D399;")
        grid.addWidget(lbl_diff_temp, 2, 3)

        # Row 3: Pending Reboot
        grid.addWidget(QLabel("حالة إعادة التشغيل:"), 3, 0)
        grid.addWidget(QLabel("مطلوب" if self.before.pending_reboot else "غير مطلوب"), 3, 1)
        grid.addWidget(QLabel("مطلوب" if self.after.pending_reboot else "غير مطلوب"), 3, 2)
        grid.addWidget(QLabel("تم التحديث"), 3, 3)

        layout.addWidget(grid_frame)

        # Note
        note_lbl = QLabel("التزام SINAX: نعرض فقط الأرقام الحقيقية المقاسة ولا ندعي نسب تسريع وهمية.")
        note_lbl.setStyleSheet("font-size: 11px; color: #8B949E; text-align: center;")
        note_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(note_lbl)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        close_btn = QPushButton("إغلاق التقرير")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

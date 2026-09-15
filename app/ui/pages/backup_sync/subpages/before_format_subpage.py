# -*- coding: utf-8 -*-
"""
SINAX Before-Format Subpage (تجهيز الجهاز قبل الفورمات).
Prepares a self-contained archive of personal files, software inventories,
WinGet scripts, hardware drivers, and SINAX configuration before formatting Windows.
"""

from pathlib import Path
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.services.backup_sync.before_format_service import BeforeFormatService
from app.services.backup_sync.device_identity_service import DeviceIdentityService
from app.services.backup_sync.known_folders_service import KnownFoldersService
from app.ui.icons import get_icon


class BeforeFormatSubpage(QWidget):
    """Cockpit for orchestrating complete pre-formatting preparation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B4B, stop:1 #0F172A);
                border: 1px solid #6366F1;
                border-radius: 10px;
                padding: 18px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("system", color_hex="#A5B4FC", size=42).pixmap(42, 42))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("تجهيز الجهاز وحفظ البيانات قبل الفورمات")
        t.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("حفظ شامل لملفاتك الشخصية، قائمة البرامج المثبتة وسكريبت استعادتها، تعريفات العتاد، وإعدادات SINAX.")
        d.setStyleSheet("font-size: 12px; color: #C7D2FE;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Components checklist
        comp_card = QFrame()
        comp_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        c_lay = QVBoxLayout(comp_card)
        c_title = QLabel("عناصر حزمة التجهيز قبل الفورمات:")
        c_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        c_lay.addWidget(c_title)

        self.cb_files = QCheckBox("الملفات والمستندات الشخصية (سطح المكتب، المستندات، الصور، الفيديوهات)")
        self.cb_files.setChecked(True)
        self.cb_apps = QCheckBox("قائمة البرامج المثبتة وسكريبت إعادة التثبيت التلقائي (WinGet Restore Script)")
        self.cb_apps.setChecked(True)
        self.cb_drivers = QCheckBox("تصدير وحفظ حزم تعريفات قطع الجهاز (Hardware Drivers via pnputil)")
        self.cb_drivers.setChecked(True)
        self.cb_settings = QCheckBox("حفظ إعدادات وتفضيلات وخيارات برنامج SINAX")
        self.cb_settings.setChecked(True)

        for cb in (self.cb_files, self.cb_apps, self.cb_drivers, self.cb_settings):
            cb.setStyleSheet("font-size: 13px; color: #F0F6FC; padding: 3px 0;")
            c_lay.addWidget(cb)
        layout.addWidget(comp_card)

        # Destination card
        dest_card = QFrame()
        dest_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        d_lay = QVBoxLayout(dest_card)
        d_title = QLabel("مكان حفظ حزمة الفورمات (يفضل قرص خارجي مستقل HDD / USB):")
        d_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        d_lay.addWidget(d_title)

        d_row = QHBoxLayout()
        self.txt_dest = QLineEdit()
        self.txt_dest.setPlaceholderText("اختر مسار القرص الخارجي لحفظ الحزمة...")
        self.txt_dest.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")

        # Try to find external drive
        ext_drives = DeviceIdentityService.list_connected_external_drives()
        if ext_drives:
            self.txt_dest.setText(str(Path(ext_drives[0].drive_letter + "\\") / "SINAX_Before_Format"))

        d_row.addWidget(self.txt_dest, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_browse.clicked.connect(self._browse_dest)
        d_row.addWidget(btn_browse)
        d_lay.addLayout(d_row)
        layout.addWidget(dest_card)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(16)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #6366F1;
                border-radius: 7px;
            }
        """)
        layout.addWidget(self.prog_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #38BDF8;")
        layout.addWidget(self.lbl_status)

        # Launch button
        self.btn_start = QPushButton("بدء تجهيز حزمة ما قبل الفورمات")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 30px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #4338CA;
            }
        """)
        self.btn_start.clicked.connect(self._start_package)
        layout.addWidget(self.btn_start)

        layout.addStretch(1)

    def _browse_dest(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مكان حفظ الحزمة")
        if d:
            self.txt_dest.setText(d)

    def _start_package(self):
        dest = self.txt_dest.text().strip()
        if not dest:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مكان حفظ الحزمة على قرص خارجي.")
            return

        folders = []
        if self.cb_files.isChecked():
            folders = [f.path for f in KnownFoldersService.get_known_folders() if f.exists and f.key in ("desktop", "documents", "pictures", "videos")]

        self.btn_start.setEnabled(False)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(10)
        self.lbl_status.setText("جاري إعداد الحزمة...")

        import threading
        from PySide6.QtCore import QTimer

        def _worker():
            def _prog(msg, pct):
                QTimer.singleShot(0, lambda: self.lbl_status.setText(msg))
                QTimer.singleShot(0, lambda: self.prog_bar.setValue(int(pct * 100)))

            rep = BeforeFormatService.execute_before_format_package(
                destination_folder=dest,
                include_folders=folders,
                export_apps=self.cb_apps.isChecked(),
                export_drivers=self.cb_drivers.isChecked(),
                export_sinax_settings=self.cb_settings.isChecked(),
                progress_cb=_prog
            )

            def _done():
                self.btn_start.setEnabled(True)
                self.prog_bar.setValue(100)
                if rep.is_success:
                    self.lbl_status.setText("اكتمل تجهيز الحزمة بنجاح ✓")
                    QMessageBox.information(
                        self,
                        "نجاح العملية",
                        f"تم إنشاء حزمة ما قبل الفورمات بنجاح:\n"
                        f"• مجلد الحزمة: {rep.destination_package_dir}\n"
                        f"• الملفات المنسوخة: {rep.files_backed_up_count}\n"
                        f"• البرامج المفهرسة: {rep.programs_cataloged_count}\n"
                        f"• تعريفات العتاد: {rep.drivers_exported_count}\n"
                        f"• دليل الاستعادة: RESTORE_INSTRUCTIONS_AR.txt"
                    )
                else:
                    self.lbl_status.setText(f"خطأ: {rep.error_summary}")
                    QMessageBox.critical(self, "خطأ", f"تعذر استكمال الحزمة: {rep.error_summary}")

            QTimer.singleShot(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

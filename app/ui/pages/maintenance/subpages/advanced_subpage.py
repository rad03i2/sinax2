# -*- coding: utf-8 -*-
"""
Advanced Tools & Maintenance History Subpage for SINAX.
Hosts specialized system maintenance utilities:
- Windows Explorer restart & cache rebuild
- System time synchronization via w32tm
- Support Diagnostic Package generator (with Privacy Mode masking)
- Permanent SQLite Maintenance History log viewer.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.diagnostic_package_service import DiagnosticPackageService
from app.services.maintenance.explorer_repair_service import ExplorerRepairService
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.services.maintenance.troubleshooter_service import TroubleshooterService
from app.ui.icons import get_icon


class AdvancedSubpage(QWidget):
    """Subpage for advanced tools, Explorer repair, and historical maintenance logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.load_history()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        tabs = QTabWidget(self)
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363D;
                background-color: #0D1117;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161B22;
                color: #8B949E;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #21262D;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
        """)

        # Tab 1: Advanced Repair Tools
        self.tab_tools = QWidget()
        self._init_tools_tab()
        tabs.addTab(self.tab_tools, "أدوات الصيانة المتقدمة وإصلاح Explorer")

        # Tab 2: Maintenance History Log
        self.tab_history = QWidget()
        self._init_history_tab()
        tabs.addTab(self.tab_history, "سجل عمليات الصيانة السابقة")

        main_layout.addWidget(tabs)

    def _init_tools_tab(self):
        layout = QVBoxLayout(self.tab_tools)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tools Grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        grid = QGridLayout(grid_frame)
        grid.setSpacing(14)

        TOOLS = [
            ("إعادة تشغيل مستكشف Windows", "يحل تجمّد سطح المكتب وشريط المهام. (سيختفي شريط المهام لثانية واحدة ثم يعود)", "إعادة تشغيل Explorer", self._restart_explorer, "tools"),
            ("إعادة بناء كاش المصغرات", "يمسح قواعد بيانات thumbcache التالفة ويعيد إنشاء صور المعاينة تلقائياً.", "إصلاح كاش المصغرات", self._rebuild_thumbs, "image"),
            ("إعادة بناء كاش الأيقونات", "يصلح الأيقونات البيضاء والمكسورة للبرامج على سطح المكتب وقائمة ابدأ.", "إصلاح كاش الأيقونات", self._rebuild_icons, "clean"),
            ("مزامنة ساعة وتوقيت النظام", "يزامن ساعة الجهاز فورياً مع خوادم التوقيت الرسمية (w32tm /resync).", "مزامنة الوقت الآن", self._sync_time, "history"),
        ]

        for idx, (title, desc, btn_text, handler, icon_name) in enumerate(TOOLS):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #0D1117;
                    border: 1px solid #21262D;
                    border-radius: 8px;
                    padding: 14px;
                }
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(8)

            top_h = QHBoxLayout()
            ic = QLabel()
            ic.setPixmap(get_icon(icon_name, color_hex="#38BDF8", size=24).pixmap(24, 24))
            top_h.addWidget(ic)
            tl = QLabel(title)
            tl.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
            top_h.addWidget(tl)
            top_h.addStretch(1)
            c_lay.addLayout(top_h)

            dl = QLabel(desc)
            dl.setWordWrap(True)
            dl.setStyleSheet("font-size: 12px; color: #8B949E; line-height: 1.3;")
            c_lay.addWidget(dl, 1)

            btn = QPushButton(btn_text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #21262D;
                    color: #F0F6FC;
                    border: 1px solid #30363D;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #30363D;
                    border-color: #38BDF8;
                }
            """)
            btn.clicked.connect(handler)
            c_lay.addWidget(btn)

            r = idx // 2
            c = idx % 2
            grid.addWidget(card, r, c)

        layout.addWidget(grid_frame)

        # Support Diagnostic Package Banner
        diag_card = QFrame()
        diag_card.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #0284C7;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        d_lay = QHBoxLayout(diag_card)
        d_lay.setSpacing(14)

        d_icon = QLabel()
        d_icon.setPixmap(get_icon("doctor", color_hex="#38BDF8", size=32).pixmap(32, 32))
        d_lay.addWidget(d_icon)

        d_text = QVBoxLayout()
        d_text.setSpacing(3)
        dt_l = QLabel("حزمة التشخيص الآمنة للدعم الفني (Privacy-First Diagnostic Package)")
        dt_l.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        ds_l = QLabel("تصدير تقرير فني شامل بصيغة JSON مع تفعيل وضع حجب البيانات الشخصية تلقائياً (حجب اسم المستخدم، IP، وMAC).")
        ds_l.setStyleSheet("font-size: 12px; color: #94A3B8;")
        d_text.addWidget(dt_l)
        d_text.addWidget(ds_l)
        d_lay.addLayout(d_text, 1)

        btn_export_diag = QPushButton("تصدير حزمة التشخيص")
        btn_export_diag.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_export_diag.clicked.connect(self._export_diagnostic_package)
        d_lay.addWidget(btn_export_diag)

        layout.addWidget(diag_card)
        layout.addStretch(1)

    def _init_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_r = QHBoxLayout()
        t_l = QLabel("سجل عمليات وإجراءات الصيانة المنفذة عبر SINAX:")
        t_l.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
        top_r.addWidget(t_l)
        top_r.addStretch(1)

        btn_refresh = QPushButton("تحديث السجل")
        btn_refresh.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_refresh.clicked.connect(self.load_history)
        top_r.addWidget(btn_refresh)
        layout.addLayout(top_r)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["التوقيت", "الإجراء المنفذ", "القسم", "الحالة", "النتيجة المقاسة"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.history_table.setStyleSheet("""
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
        layout.addWidget(self.history_table, 1)

    def load_history(self):
        records = SnapshotHistoryService().get_recent_history(limit=50)
        self.history_table.setRowCount(len(records))
        for idx, rec in enumerate(records):
            self.history_table.setItem(idx, 0, QTableWidgetItem(rec.get("date_str", "")))
            self.history_table.setItem(idx, 1, QTableWidgetItem(rec.get("action_title", "")))
            self.history_table.setItem(idx, 2, QTableWidgetItem(rec.get("category", "")))
            self.history_table.setItem(idx, 3, QTableWidgetItem(rec.get("status", "")))
            self.history_table.setItem(idx, 4, QTableWidgetItem(rec.get("result_summary", "")))

    def _restart_explorer(self):
        reply = QMessageBox.question(
            self,
            "تأكيد إعادة تشغيل Explorer",
            "سيختفي شريط المهام وسطح المكتب لثانية أو ثانيتين ثم يعود للعمل تلقائياً.\nهل ترغب بالمتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            success, msg = ExplorerRepairService.restart_explorer()
            SnapshotHistoryService().log_maintenance_action(
                "restart_explorer", "إعادة تشغيل مستكشف Windows", "explorer", "success" if success else "failed", msg
            )
            QMessageBox.information(self, "النتيجة", msg)
            self.load_history()

    def _rebuild_thumbs(self):
        success, msg = ExplorerRepairService.rebuild_thumbnail_cache()
        SnapshotHistoryService().log_maintenance_action(
            "rebuild_thumbnail_cache", "إعادة بناء كاش المصغرات", "explorer", "success" if success else "failed", msg
        )
        QMessageBox.information(self, "النتيجة", msg)
        self.load_history()

    def _rebuild_icons(self):
        success, msg = ExplorerRepairService.rebuild_icon_cache()
        SnapshotHistoryService().log_maintenance_action(
            "rebuild_icon_cache", "إعادة بناء كاش الأيقونات", "explorer", "success" if success else "failed", msg
        )
        QMessageBox.information(self, "النتيجة", msg)
        self.load_history()

    def _sync_time(self):
        success, msg = TroubleshooterService.sync_system_time()
        SnapshotHistoryService().log_maintenance_action(
            "sync_system_time", "مزامنة وقت النظام", "system", "success" if success else "failed", msg
        )
        QMessageBox.information(self, "مزامنة التوقيت", msg)
        self.load_history()

    def _export_diagnostic_package(self):
        try:
            path = DiagnosticPackageService.export_package_to_file()
            QMessageBox.information(
                self,
                "تم التصدير بنجاح",
                f"تم إنشاء حزمة التشخيص الفنية الآمنة وحفظها على سطح المكتب:\n{path}\nتم حجب كافة البيانات الشخصية وعناوين IP وMAC لحماية خصوصيتك."
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تصدير الحزمة: {e}")

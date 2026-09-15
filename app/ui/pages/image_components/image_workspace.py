# -*- coding: utf-8 -*-
"""
SINAX Image Tool Workspace
Unified interactive workspace for configuring, previewing, and executing
any tool from the Image Center across single files or massive batches.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFrame,
    QFileDialog, QProgressBar, QMessageBox, QTabWidget, QCheckBox,
    QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QDragEnterEvent, QDropEvent

from app.ui.icons import get_icon
from app.services.image.image_registry import ImageToolDefinition
from app.services.image.image_utils import scan_images, format_size, get_proxy_thumbnail
from app.workers.image_worker import ImageWorker
from app.ui.pages.image_components.image_options_panel import ImageOptionsPanel
from app.ui.pages.image_components.image_viewer_widget import ImageViewerWidget
from app.core.config import config


class ImageToolWorkspace(QWidget):
    """Unified interactive workspace for single and batch image processing."""

    back_to_catalog_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, tool: ImageToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.files: List[Path] = []
        self.base_folder: Optional[Path] = None
        self.worker: Optional[ImageWorker] = None
        self._is_paused = False
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. TOP HEADER BAR
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #262626; border: 1px solid #383838; border-radius: 8px;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(12)

        self.btn_back = QPushButton("← العودة إلى قائمة أدوات الصور")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_to_catalog_requested.emit)
        tb_layout.addWidget(self.btn_back)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(self.tool.icon, "#60CDFF", 26).pixmap(26, 26))
        tb_layout.addWidget(icon_lbl)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        t_lbl = QLabel(f"{self.tool.title_ar}  ({self.tool.title_en})")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        title_layout.addWidget(t_lbl)

        d_lbl = QLabel(self.tool.description_ar)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet("font-size: 11px; color: #CCCCCC;")
        title_layout.addWidget(d_lbl)
        tb_layout.addLayout(title_layout, 1)

        main_layout.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. MAIN SPLITTER (Left: Files & Destination | Right: Options & Viewer)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: File List & Output Destination
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Buttons row
        action_row = QHBoxLayout()
        self.btn_add_files = QPushButton("➕ إضافة صور...")
        self.btn_add_files.setStyleSheet(self._action_btn_style("#0078D4"))
        self.btn_add_files.clicked.connect(self._choose_files)
        action_row.addWidget(self.btn_add_files)

        self.btn_add_dir = QPushButton("📁 إضافة مجلد كامل...")
        self.btn_add_dir.setStyleSheet(self._action_btn_style("#2E5B82"))
        self.btn_add_dir.clicked.connect(self._choose_directory)
        action_row.addWidget(self.btn_add_dir)

        self.btn_clear = QPushButton("🗑️ مسح الكل")
        self.btn_clear.setStyleSheet(self._action_btn_style("#382424"))
        self.btn_clear.clicked.connect(self._clear_files)
        action_row.addWidget(self.btn_clear)

        left_layout.addLayout(action_row)

        # Recursive scan checkbox
        self.chk_recursive = QCheckBox("مسح المجلدات الفرعية تلقائياً (Recursive Subfolders)")
        self.chk_recursive.setChecked(True)
        left_layout.addWidget(self.chk_recursive)

        # File stats banner
        self.stats_lbl = QLabel("لم يتم إضافة أي صور بعد (اسحب وأفلت الصور أو المجلدات هنا)")
        self.stats_lbl.setStyleSheet("font-size: 11px; color: #888888; padding: 2px 4px;")
        left_layout.addWidget(self.stats_lbl)

        # Table Widget
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["المعاينة", "اسم الصورة", "الحجم", "الحالة"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 100)
        self.table.setIconSize(QSize(40, 40))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 6px;
                gridline-color: #282828;
                color: #E0E0E0;
            }
            QHeaderView::section {
                background-color: #282828;
                border: 1px solid #333333;
                padding: 6px;
                font-weight: bold;
                color: #CCCCCC;
            }
            QTableWidget::item:selected {
                background-color: #0078D4;
                color: #FFFFFF;
            }
        """)
        self.table.itemSelectionChanged.connect(self._on_table_row_selected)
        left_layout.addWidget(self.table, 1)

        # Output Destination Frame
        out_frame = QFrame()
        out_frame.setStyleSheet("background-color: #232323; border: 1px solid #383838; border-radius: 6px;")
        of_layout = QVBoxLayout(out_frame)
        of_layout.setContentsMargins(10, 8, 10, 8)
        of_layout.setSpacing(6)

        of_layout.addWidget(QLabel("مجلد حفظ النتائج:"))
        dest_row = QHBoxLayout()
        self.txt_dest = QLineEdit(str(Path.home() / "Desktop" / "SINAX_Images_Output"))
        self.txt_dest.setStyleSheet("background-color: #1A1A1A; border: 1px solid #444; border-radius: 4px; padding: 5px; color: #FFF;")
        dest_row.addWidget(self.txt_dest, 1)

        btn_browse_dest = QPushButton("تغيير...")
        btn_browse_dest.setStyleSheet(self._action_btn_style("#333333"))
        btn_browse_dest.clicked.connect(self._choose_dest_folder)
        dest_row.addWidget(btn_browse_dest)
        of_layout.addLayout(dest_row)

        self.chk_preserve_tree = QCheckBox("الحفاظ على هيكل وتفرع المجلدات الأصلية")
        self.chk_preserve_tree.setChecked(True)
        of_layout.addWidget(self.chk_preserve_tree)

        self.chk_overwrite = QCheckBox("استبدال الملفات الأصلية مباشرة (حذر: لا يمكن التراجع)")
        self.chk_overwrite.setStyleSheet("color: #FF8888;")
        of_layout.addWidget(self.chk_overwrite)

        left_layout.addWidget(out_frame)
        splitter.addWidget(left_widget)

        # RIGHT PANE: Tabs (Options Panel & Interactive Viewer)
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #383838;
                background-color: #232323;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #2A2A2A;
                color: #CCCCCC;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #232323;
                color: #60CDFF;
                border-bottom: 2px solid #60CDFF;
            }
        """)

        # Tab 1: Options
        self.options_panel = ImageOptionsPanel(self.tool)
        right_tabs.addTab(self.options_panel, "⚙️ خيارات الأداة")

        # Tab 2: Previewer
        self.viewer = ImageViewerWidget()
        right_tabs.addTab(self.viewer, "👁️ المعاينة والمقارنة (قبل / بعد)")

        splitter.addWidget(right_tabs)
        splitter.setSizes([450, 650])
        main_layout.addWidget(splitter, 1)

        # -------------------------------------------------------------
        # 3. BOTTOM EXECUTION & PROGRESS BAR
        # -------------------------------------------------------------
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #262626; border: 1px solid #383838; border-radius: 8px;")
        bf_layout = QVBoxLayout(bottom_frame)
        bf_layout.setContentsMargins(14, 10, 14, 10)
        bf_layout.setSpacing(6)

        # Top row: Progress bar + Status metrics
        prog_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1A1A1A;
                border: 1px solid #383838;
                border-radius: 6px;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078D4, stop:1 #60CDFF);
                border-radius: 5px;
            }
        """)
        prog_row.addWidget(self.progress_bar, 1)

        self.btn_pause = QPushButton("⏸️ إيقاف مؤقت")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet(self._action_btn_style("#444444"))
        self.btn_pause.clicked.connect(self._toggle_pause)
        prog_row.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("⏹️ إلغاء")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(self._action_btn_style("#5A2424"))
        self.btn_cancel.clicked.connect(self._cancel_worker)
        prog_row.addWidget(self.btn_cancel)

        bf_layout.addLayout(prog_row)

        # Metrics text row
        metrics_row = QHBoxLayout()
        self.lbl_speed_eta = QLabel("السرعة: -- ص/ثانية  |  الوقت المتبقي: --")
        self.lbl_speed_eta.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        metrics_row.addWidget(self.lbl_speed_eta)
        metrics_row.addStretch(1)

        self.lbl_saved = QLabel("")
        self.lbl_saved.setStyleSheet("font-size: 11px; font-weight: bold; color: #6CCB5F;")
        metrics_row.addWidget(self.lbl_saved)

        # Start button
        self.btn_start = QPushButton(f"⚡ بدء تنفيذ العملية الجماعية")
        self.btn_start.setMinimumWidth(280)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078D4, stop:1 #106EBE);
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0086F0;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
            }
        """)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_processing)
        metrics_row.addWidget(self.btn_start)

        bf_layout.addLayout(metrics_row)
        main_layout.addWidget(bottom_frame)

        # Enable drag and drop
        self.setAcceptDrops(True)

    def _action_btn_style(self, bg_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: #60CDFF;
            }}
        """

    # -------------------------------------------------------------------------
    # DRAG & DROP
    # -------------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        self._add_paths(paths)

    def _choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "اختر الصور للمعالجة", "",
            "Images (*.jpg *.jpeg *.png *.webp *.avif *.heic *.heif *.bmp *.tiff *.gif *.ico)"
        )
        if files:
            self._add_paths([Path(f) for f in files])

    def _choose_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد الصور")
        if folder:
            self.base_folder = Path(folder)
            found = scan_images([self.base_folder], recursive=self.chk_recursive.isChecked())
            self._add_paths(found)

    def _choose_dest_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد حفظ الصور المعالجة")
        if folder:
            self.txt_dest.setText(folder)

    def _add_paths(self, paths: List[Path]):
        scanned = scan_images(paths, recursive=self.chk_recursive.isChecked())
        existing = set(str(f) for f in self.files)
        for p in scanned:
            if str(p) not in existing:
                self.files.append(p)
                existing.add(str(p))

        self._refresh_table()

    def _clear_files(self):
        self.files.clear()
        self.table.setRowCount(0)
        self.stats_lbl.setText("لم يتم إضافة أي صور بعد.")
        self.btn_start.setText("⚡ بدء تنفيذ العملية الجماعية")

    def _refresh_table(self):
        self.table.setRowCount(len(self.files))
        total_size = 0

        for row, f in enumerate(self.files):
            # Thumbnail proxy
            thumb = get_proxy_thumbnail(f, (40, 40))
            t_item = QTableWidgetItem()
            if thumb:
                t_item.setIcon(QIcon(thumb))
            self.table.setItem(row, 0, t_item)

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(f.name))

            # Size
            size = f.stat().st_size
            total_size += size
            self.table.setItem(row, 2, QTableWidgetItem(format_size(size)))

            # Status
            status_item = QTableWidgetItem("جاهز")
            status_item.setForeground(Qt.gray)
            self.table.setItem(row, 3, status_item)

        self.stats_lbl.setText(
            f"تم العثور على {len(self.files):,} صورة  |  الحجم الإجمالي: {format_size(total_size)}"
        )
        self.btn_start.setText(f"⚡ بدء تنفيذ العملية الجماعية ({len(self.files):,} صورة)")

        if self.files:
            self.viewer.load_image(self.files[0])

    def _on_table_row_selected(self):
        rows = self.table.selectedIndexes()
        if rows:
            idx = rows[0].row()
            if 0 <= idx < len(self.files):
                self.viewer.load_image(self.files[idx])

    # -------------------------------------------------------------------------
    # WORKER CONTROLS & EXECUTION
    # -------------------------------------------------------------------------
    def _start_processing(self):
        if not self.files:
            QMessageBox.warning(self, "تنبيه", "يرجى إضافة صور أولاً للبدء.")
            return

        out_dir = Path(self.txt_dest.text().strip())
        if not out_dir:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مجلد لحفظ النتائج.")
            return

        if self.chk_overwrite.isChecked():
            res = QMessageBox.warning(
                self, "تأكيد استبدال الملفات",
                "⚠️ أنت على وشك استبدال الصور الأصلية مباشرة!\nهل أنت متأكد من المتابعة؟",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if res != QMessageBox.Yes:
                return

        opts = self.options_panel.get_options()
        self.worker = ImageWorker(
            files=self.files,
            tool_id=self.tool.id,
            options=opts,
            output_folder=out_dir,
            base_folder=self.base_folder,
            preserve_folders=self.chk_preserve_tree.isChecked(),
            overwrite_original=self.chk_overwrite.isChecked(),
            parent=self
        )

        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.all_finished.connect(self._on_worker_finished)

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.worker.start()

    def _toggle_pause(self):
        if not self.worker:
            return
        if self._is_paused:
            self.worker.resume()
            self._is_paused = False
            self.btn_pause.setText("⏸️ إيقاف مؤقت")
        else:
            self.worker.pause()
            self._is_paused = True
            self.btn_pause.setText("▶️ استئناف")

    def _cancel_worker(self):
        if self.worker:
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)

    def _on_file_started(self, idx: int, filename: str):
        row = idx - 1
        if 0 <= row < self.table.rowCount():
            item = self.table.item(row, 3)
            if item:
                item.setText("جاري المعالجة...")
                item.setForeground(Qt.cyan)

    def _on_file_finished(self, idx: int, filename: str, success: bool, msg: str, bytes_saved: int):
        row = idx - 1
        if 0 <= row < self.table.rowCount():
            item = self.table.item(row, 3)
            if item:
                if success:
                    item.setText("مكتمل ✓")
                    item.setForeground(Qt.green)
                else:
                    item.setText(f"فشل: {msg[:18]}")
                    item.setForeground(Qt.red)

    def _on_worker_progress(self, curr: int, total: int, pct: float, speed: float, eta: int, bytes_saved: int):
        self.progress_bar.setValue(int(pct))
        eta_str = f"{eta} ثانية" if eta < 60 else f"{eta // 60} دقيقة و {eta % 60} ثانية"
        self.lbl_speed_eta.setText(f"السرعة: {speed} صورة / ثانية  |  الوقت المتبقي: {eta_str}")
        if bytes_saved > 0:
            self.lbl_saved.setText(f"تم توفير: {format_size(bytes_saved)} 📉")

    def _on_worker_finished(self, summary: Dict[str, Any]):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)

        elapsed = summary.get("elapsed_seconds", 0)
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        time_str = f"{mins} دقيقة و {secs} ثانية" if mins > 0 else f"{secs} ثانية"

        saved_str = format_size(summary.get("bytes_saved", 0))

        msg = (
            f"🎉 اكتملت المعالجة الجماعية بنجاح!\n\n"
            f"• إجمالي الصور: {summary.get('total', 0):,}\n"
            f"• نجح: {summary.get('processed', 0):,}\n"
            f"• فشل: {summary.get('failed', 0):,}\n"
            f"• المساحة الموفرة: {saved_str}\n"
            f"• الزمن المستغرق: {time_str}\n\n"
            f"مجلد الحفظ: {summary.get('output_folder')}"
        )
        QMessageBox.information(self, "اكتملت المعالجة", msg)

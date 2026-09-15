# -*- coding: utf-8 -*-
"""
Visual verification capture script for SINAX RTL Sidebar and Optimized Centers.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.themes.theme_manager import theme_manager

ARTIFACT_DIR = r"C:\Users\HP\.gemini\antigravity\brain\675f47c4-670c-49d5-a34e-1224f61ae57a"
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def capture_all():
    app = QApplication.instance() or QApplication(sys.argv)
    theme_manager.apply_theme("dark")

    window = MainWindow()
    window.resize(1366, 800)
    window.show()

    app.processEvents()
    time.sleep(0.8)
    app.processEvents()

    # 1. Expanded Sidebar & Dashboard
    window.navigate_to("dashboard")
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    pix = window.grab()
    pix.save(os.path.join(ARTIFACT_DIR, "sidebar_rtl_expanded.png"))
    print("[CAPTURED] sidebar_rtl_expanded.png")

    # 2. Collapsed Sidebar
    window.sidebar.set_collapsed(True)
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    pix = window.grab()
    pix.save(os.path.join(ARTIFACT_DIR, "sidebar_rtl_collapsed.png"))
    print("[CAPTURED] sidebar_rtl_collapsed.png")

    # 3. Re-expand sidebar and navigate to Video Center
    window.sidebar.set_collapsed(False)
    window.navigate_to("video_center")
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()
    pix = window.grab()
    pix.save(os.path.join(ARTIFACT_DIR, "video_center_fast.png"))
    print("[CAPTURED] video_center_fast.png")

    # 4. Navigate to System & Storage
    window.navigate_to("system_storage_overview")
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()
    pix = window.grab()
    pix.save(os.path.join(ARTIFACT_DIR, "system_storage_clean.png"))
    print("[CAPTURED] system_storage_clean.png")

    window.close()


if __name__ == "__main__":
    capture_all()

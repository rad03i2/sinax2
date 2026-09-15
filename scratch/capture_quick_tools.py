# -*- coding: utf-8 -*-
"""
Off-screen capture script for SINAX Quick Tools & Utility Lab.
Renders high-resolution PNG artifacts for visual layout, alignment, and RTL verification.
"""

import os
import sys
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui.main_window import MainWindow

ARTIFACT_DIR = r"C:\Users\HP\.gemini\antigravity\brain\675f47c4-670c-49d5-a34e-1224f61ae57a"


def capture_quick_tools():
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    window.resize(1280, 820)
    window.show()

    app.processEvents()
    time.sleep(1.0)
    app.processEvents()

    # 1. Navigate to Quick Tools overview
    window.navigate_to("quick_tools")
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    pix_main = window.grab()
    out1 = os.path.join(ARTIFACT_DIR, "quick_tools_overview.png")
    pix_main.save(out1, "PNG")
    print(f"Captured: {out1}")

    # 2. Test Smart Drop Zone with URL
    qt_page = window.quick_tools_page
    qt_page.drop_zone.inline_input.setText("https://github.com/google/antigravity")
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()

    pix_url = window.grab()
    out2 = os.path.join(ARTIFACT_DIR, "quick_tools_smart_resolver.png")
    pix_url.save(out2, "PNG")
    print(f"Captured: {out2}")

    # 3. Open QR Generator tool in Workspace
    qr_tool = qt_page.drop_zone.actions_layout.itemAt(0).widget()
    if qr_tool:
        qr_tool.click()
        app.processEvents()
        time.sleep(0.5)
        app.processEvents()

    pix_workspace = window.grab()
    out3 = os.path.join(ARTIFACT_DIR, "quick_tools_workspace_qr.png")
    pix_workspace.save(out3, "PNG")
    print(f"Captured: {out3}")

    # Select Hash Category button
    for btn in qt_page.cat_button_group.buttons():
        if "Hash" in btn.text():
            btn.click()
            break
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()

    pix_hash = window.grab()
    out4 = os.path.join(ARTIFACT_DIR, "quick_tools_hash_category.png")
    pix_hash.save(out4, "PNG")
    print(f"Captured: {out4}")

    window.close()
    print("ALL QUICK TOOLS SCREENSHOTS CAPTURED SUCCESSFULLY!")


if __name__ == "__main__":
    capture_quick_tools()

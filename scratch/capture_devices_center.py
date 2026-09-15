# -*- coding: utf-8 -*-
"""
Off-screen capture script for SINAX Devices & Hardware Center subpages.
Renders subpages into high-resolution PNG artifacts for visual verification.
"""

import os
import sys
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

ARTIFACT_DIR = r"C:\Users\HP\.gemini\antigravity\brain\675f47c4-670c-49d5-a34e-1224f61ae57a"


def capture_all():
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    window.resize(1280, 820)
    window.show()

    # Allow initial rendering
    app.processEvents()
    time.sleep(1.0)
    app.processEvents()

    subpages = [
        "devices_overview",
        "devices_cpu",
        "devices_gpu",
        "devices_ram",
        "devices_motherboard",
        "devices_storage",
        "devices_battery",
        "devices_displays",
        "devices_usb",
        "devices_drivers",
        "devices_sensors",
        "devices_windows",
        "devices_quick_check",
        "devices_reports",
    ]

    for key in subpages:
        window.navigate_to(key)
        app.processEvents()
        time.sleep(0.4)
        app.processEvents()

        # Capture
        pix = window.grab()
        filename = f"{key}.png"
        out_path = os.path.join(ARTIFACT_DIR, filename)
        pix.save(out_path, "PNG")
        print(f"Captured: {out_path} ({pix.width()}x{pix.height()})")

    window.close()
    print("ALL DEVICES SUBPAGES CAPTURED SUCCESSFULLY!")


if __name__ == "__main__":
    capture_all()

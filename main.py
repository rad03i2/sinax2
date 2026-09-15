# -*- coding: utf-8 -*-
"""
SINAX - Desktop File & Computer Management Suite
Entry Point
"""

import sys
import os
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication, QTimer

from app.core.constants import APP_NAME, APP_NAME_AR, APP_VERSION
from app.core.config import config
from app.core.logger import setup_logging, get_logger
from app.core.startup_profiler import StartupProfiler
from app.core.crash_recovery import crash_recovery_manager
from app.ui.themes.theme_manager import theme_manager
from app.ui.widgets.splash_screen import SinaxSplashScreen
from app.ui.main_window import MainWindow

def unhandled_exception_hook(exc_type, exc_value, exc_traceback):
    """Logs unexpected exceptions to file without frightening tracebacks to end user."""
    logger = get_logger("system")
    logger.critical("Unhandled Exception:", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def main():
    StartupProfiler.record_milestone("Core & Environment")
    setup_logging()
    logger = get_logger("main")
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}...")
    crash_recovery_manager.record_startup_begin()
    sys.excepthook = unhandled_exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SINAX Technologies")

    # Native RTL Arabic layout direction
    app.setLayoutDirection(Qt.RightToLeft)

    # Apply configured theme (System / Light / Dark)
    theme_mode = config.get("theme_mode", "system")
    theme_manager.set_theme_mode(theme_mode)
    StartupProfiler.record_milestone("Theme & Stylesheet")

    # Show Professional Fast Splash Screen
    splash = SinaxSplashScreen()
    splash.show()
    splash.advance_step("تحميل النواة وقاعدة البيانات")
    app.processEvents()

    # Initialize Main Window with Lazy Loading
    splash.advance_step("تجهيز الواجهة وقمرة القيادة")
    window = MainWindow()
    StartupProfiler.record_milestone("MainWindow Assembled")

    def show_main():
        splash.finish(window)
        window.show()
        crash_recovery_manager.record_startup_success()
        StartupProfiler.record_milestone("Application Presented")
        StartupProfiler.print_benchmark_report()

    # Instant, seamless splash transition as soon as event loop starts
    QTimer.singleShot(0, show_main)

    exit_code = app.exec()
    logger.info("Application terminated cleanly.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

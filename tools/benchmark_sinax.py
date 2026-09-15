import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("c:/Users/HP/Desktop/sinax2")
sys.path.insert(0, str(PROJECT_ROOT))

import psutil

process = psutil.Process()
ram_initial = process.memory_info().rss / (1024 * 1024)

t0 = time.perf_counter()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

t_pyside = time.perf_counter()

app = QApplication.instance() or QApplication(sys.argv)
app.setLayoutDirection(Qt.RightToLeft)

t_app = time.perf_counter()

from app.core.config import config
from app.ui.themes.theme_manager import theme_manager
theme_manager.apply_theme(config.get("theme", "dark"))

t_theme = time.perf_counter()

from app.ui.main_window import MainWindow
t_import_window = time.perf_counter()

window = MainWindow()
t_init_window = time.perf_counter()

ram_startup = process.memory_info().rss / (1024 * 1024)

# Test opening all 15 centers and measure first open vs reopen times
centers = [
    ("dashboard", "Home / Dashboard"),
    ("file_manager", "File Management"),
    ("pdf_center", "PDF"),
    ("image_center", "Images"),
    ("video_center", "Video"),
    ("audio_center", "Audio"),
    ("system_storage", "System & Storage"),
    ("devices", "Devices"),
    ("apps_manager", "Apps"),
    ("network", "Network"),
    ("backup_sync", "Backup & Sync"),
    ("privacy_security", "Privacy & Security"),
    ("maintenance", "Maintenance"),
    ("quick_tools", "Quick Tools"),
    ("settings", "Settings"),
]

page_results = {}

for route, label in centers:
    # First Open
    t_start = time.perf_counter()
    window.navigate_to(route, record_history=False)
    app.processEvents()
    t_first = (time.perf_counter() - t_start) * 1000

    # Reopen
    # switch to dashboard first then back
    window.navigate_to("dashboard", record_history=False)
    app.processEvents()
    t_re_start = time.perf_counter()
    window.navigate_to(route, record_history=False)
    app.processEvents()
    t_reopen = (time.perf_counter() - t_re_start) * 1000

    ram_after = process.memory_info().rss / (1024 * 1024)
    page_results[route] = {
        "label": label,
        "first_ms": t_first,
        "reopen_ms": t_reopen,
        "ram_mb": ram_after
    }

ram_final = process.memory_info().rss / (1024 * 1024)
total_interactive = time.perf_counter() - t0

print("=" * 60)
print("  SINAX PERFORMANCE BASELINE MEASUREMENT")
print("=" * 60)
print(f"PySide6 Import Time       : {(t_pyside - t0)*1000:6.1f} ms")
print(f"QApplication Init         : {(t_app - t_pyside)*1000:6.1f} ms")
print(f"Theme Apply               : {(t_theme - t_app)*1000:6.1f} ms")
print(f"MainWindow Import         : {(t_import_window - t_theme)*1000:6.1f} ms")
print(f"MainWindow Init           : {(t_init_window - t_import_window)*1000:6.1f} ms")
print(f"Total Time To First Frame : {(t_init_window - t0)*1000:6.1f} ms")
print(f"Startup RAM               : {ram_startup:6.1f} MB")
print(f"Final RAM (All Centers)   : {ram_final:6.1f} MB")
print(f"RAM Growth                : {(ram_final - ram_startup):6.1f} MB")
print("-" * 60)
print(f"{'Center':<25} | {'First Open':<12} | {'Reopen':<12} | {'RAM (MB)':<10}")
print("-" * 60)
for route, data in page_results.items():
    print(f"{data['label']:<25} | {data['first_ms']:8.1f} ms  | {data['reopen_ms']:8.1f} ms  | {data['ram_mb']:6.1f} MB")
print("=" * 60)

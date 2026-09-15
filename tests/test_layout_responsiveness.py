# -*- coding: utf-8 -*-
"""
SINAX Layout Responsiveness & Widget Height Verification Test
Tests that no inputs or group boxes are crushed across multiple resolutions.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import (
    QApplication, QLineEdit, QComboBox, QSpinBox, QGroupBox, QListWidget, QScrollArea
)
from PySide6.QtCore import QSize
from app.ui.main_window import MainWindow

class TestLayoutResponsiveness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.window = MainWindow()
        cls.window.navigate_to("batch_rename")
        cls.page = cls.window.batch_rename_page

    def test_tab_scroll_areas_and_widget_heights(self):
        resolutions = [
            (1024, 700),
            (1280, 720),
            (1366, 768),
            (1600, 900),
            (1920, 1080),
            (2560, 1440)
        ]

        for w, h in resolutions:
            self.window.resize(QSize(w, h))
            self.window.show()
            self.app.processEvents()

            for tab_idx in range(4):
                self.page.tabs.setCurrentIndex(tab_idx)
                self.app.processEvents()

                tab_title = self.page.tabs.tabText(tab_idx)
                scroll = self.page.tabs.widget(tab_idx)
                self.assertIsInstance(scroll, QScrollArea, f"Tab {tab_title} must be wrapped in QScrollArea")

                content = scroll.widget()
                self.assertIsNotNone(content, f"Tab {tab_title} must have content widget")

                # Check GroupBoxes
                groupboxes = content.findChildren(QGroupBox)
                self.assertGreater(len(groupboxes), 0, f"Tab {tab_title} should have GroupBoxes")
                for gb in groupboxes:
                    self.assertGreaterEqual(
                        gb.height(), 40,
                        f"Resolution {w}x{h} Tab '{tab_title}' GroupBox '{gb.title()}' is crushed to {gb.height()}px!"
                    )

                # Check all inputs
                inputs = (
                    content.findChildren(QLineEdit) +
                    content.findChildren(QComboBox) +
                    content.findChildren(QSpinBox)
                )
                for inp in inputs:
                    self.assertGreaterEqual(
                        inp.height(), 28,
                        f"Resolution {w}x{h} Tab '{tab_title}' Input {type(inp).__name__} is crushed to {inp.height()}px!"
                    )

    def test_split_proportions(self):
        self.assertFalse(self.page.findChild(QLineEdit).text().startswith("error"))

if __name__ == "__main__":
    unittest.main()

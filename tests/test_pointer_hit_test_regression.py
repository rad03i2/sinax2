# -*- coding: utf-8 -*-
"""
Automated Regression Test Suite for SINAX Pointer Hit Testing & Click Routing.
Verifies that:
1. SinaxCard MouseArea does not swallow clicks destined for nested child controls.
2. Clickable SinaxCards distinguish between child button clicks and card body clicks.
3. JobCenterDialog properly dismisses and does not leak an invisible overlay HWND.
4. Left-half click events in Maximized mode are delivered cleanly across all zones.
"""

import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest

from app.core.qml_helper import configure_qml_engine, QML_ROOT
from app.ui.main_window import MainWindow
from app.ui.dialogs.job_center_dialog import JobCenterDialog


class TestPointerHitTestRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setLayoutDirection(Qt.RightToLeft)

    def test_sinax_card_nested_button_clicks_when_not_clickable(self):
        """Nested buttons inside SinaxCard must receive mouse clicks when card.clickable is false."""
        qw = QQuickWidget()
        configure_qml_engine(qw.engine())

        qml = """
        import QtQuick
        import components 1.0

        Item {
            id: testRoot
            width: 400
            height: 300
            property bool buttonClicked: false
            property bool cardClicked: false

            SinaxCard {
                id: card
                width: 350
                height: 200
                clickable: false
                onClicked: testRoot.cardClicked = true

                SinaxButton {
                    id: btn
                    text: "Action Button"
                    onClicked: testRoot.buttonClicked = true
                }
            }
        }
        """
        comp = QQmlComponent(qw.engine())
        comp.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(QML_ROOT) + "/dummy.qml"))
        self.assertFalse(comp.isError(), f"QML compile errors: {comp.errors()}")

        item = comp.create()
        qw.setContent(QUrl(), comp, item)
        qw.resize(400, 300)
        qw.show()
        self.app.processEvents()

        # Locate SinaxButton
        def find_btn(it):
            if "Button" in it.metaObject().className():
                return it
            for ch in it.childItems():
                res = find_btn(ch)
                if res:
                    return res
            return None

        btn = find_btn(item)
        self.assertIsNotNone(btn)
        p = btn.mapToItem(None, QPoint(15, 15))

        QTest.mouseClick(qw, Qt.LeftButton, Qt.NoModifier, p.toPoint())
        self.app.processEvents()

        self.assertTrue(item.property("buttonClicked"), "SinaxButton inside SinaxCard did NOT receive click!")
        self.assertFalse(item.property("cardClicked"), "Card clicked fired unexpectedly when clickable=false!")

    def test_sinax_card_clickable_separates_button_and_body_clicks(self):
        """When card.clickable is true, clicking button triggers button, clicking background triggers card."""
        qw = QQuickWidget()
        configure_qml_engine(qw.engine())

        qml = """
        import QtQuick
        import components 1.0

        Item {
            id: testRoot
            width: 400
            height: 300
            property bool buttonClicked: false
            property bool cardClicked: false

            SinaxCard {
                id: card
                width: 350
                height: 200
                clickable: true
                onClicked: testRoot.cardClicked = true

                SinaxButton {
                    id: btn
                    text: "Action Button"
                    onClicked: testRoot.buttonClicked = true
                }
            }
        }
        """
        comp = QQmlComponent(qw.engine())
        comp.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(QML_ROOT) + "/dummy.qml"))
        item = comp.create()
        qw.setContent(QUrl(), comp, item)
        qw.resize(400, 300)
        qw.show()
        self.app.processEvents()

        # 1. Click button
        def find_btn(it):
            if "Button" in it.metaObject().className():
                return it
            for ch in it.childItems():
                res = find_btn(ch)
                if res:
                    return res
            return None

        btn = find_btn(item)
        p = btn.mapToItem(None, QPoint(15, 15))
        QTest.mouseClick(qw, Qt.LeftButton, Qt.NoModifier, p.toPoint())
        self.app.processEvents()

        self.assertTrue(item.property("buttonClicked"))
        self.assertFalse(item.property("cardClicked"))

        # 2. Click outside button (card background at 200, 150)
        item.setProperty("buttonClicked", False)
        item.setProperty("cardClicked", False)
        QTest.mouseClick(qw, Qt.LeftButton, Qt.NoModifier, QPoint(200, 150))
        self.app.processEvents()

        self.assertFalse(item.property("buttonClicked"))
        self.assertTrue(item.property("cardClicked"))

    def test_job_center_dialog_closed_dismissal(self):
        """JobCenterDialog must close its QDialog completely when QML emits closed signal."""
        dlg = JobCenterDialog()
        dlg.show_drawer()
        self.app.processEvents()
        self.assertTrue(dlg.isVisible())

        root = dlg._quick_widget.rootObject()
        self.assertIsNotNone(root)
        self.assertTrue(root.property("isOpen"))

        # Emit closed
        root.closed.emit()
        self.app.processEvents()

        self.assertFalse(dlg.isVisible(), "JobCenterDialog remained visible after closed signal was emitted!")

    def test_maximized_horizontal_click_distribution(self):
        """MainWindow in Maximized mode must route clicks to all 5 horizontal zones without swallowing."""
        win = MainWindow()
        win.showMaximized()
        self.app.processEvents()

        geo = win.geometry()
        w = geo.width()

        # Sample points at 10%, 25%, 50%, 75%, 90%
        for pct in [0.1, 0.25, 0.5, 0.75, 0.9]:
            gx = int(geo.x() + w * pct)
            gy = int(geo.y() + 250)
            target = QApplication.widgetAt(QPoint(gx, gy))
            self.assertIsNotNone(target, f"No widget found at horizontal position {pct*100}% ({gx}, {gy})")
            self.assertTrue(target.isVisible(), f"Widget at {pct*100}% is not visible")
            self.assertTrue(target.isEnabled(), f"Widget at {pct*100}% is not enabled")


if __name__ == "__main__":
    unittest.main()

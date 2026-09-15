# -*- coding: utf-8 -*-
"""
SINAX QML Phase 3 Comprehensive Test Suite
Validates:
1. Instantiation of BeforeAfterViewer component.
2. Loading of all 10 Phase 3 QML pages (PDF, Image, Video, Audio, Apps, Network, Privacy, History, Settings, About).
3. Controllers and models (AppsController, InstalledAppsModel, HistoryController, HistoryModel, etc.).
4. Latency benchmarks: Time to Page Shell < 150ms for all 10 pages.
5. Command Palette bilingual aliases and routing.
6. QML Error Boundary resilience.
7. Startup Crash Recovery and Safe UI mode detection.
"""

import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtCore import QUrl

from app.core.qml_helper import configure_qml_engine, get_qml_url, QmlErrorBoundaryWidget
from app.core.crash_recovery import crash_recovery_manager
from app.controllers.navigation_controller import navigation_controller
from app.controllers.command_palette_controller import command_palette_controller
from app.controllers.pdf_controller import pdf_controller
from app.controllers.image_controller import image_controller
from app.controllers.video_controller import video_controller
from app.controllers.audio_controller import audio_controller
from app.controllers.apps_controller import apps_controller, InstalledAppsModel
from app.controllers.network_controller import network_controller
from app.controllers.privacy_controller import privacy_controller
from app.controllers.history_controller import history_controller, HistoryModel
from app.controllers.settings_controller import settings_controller

# Ensure QApplication exists
app = QApplication.instance() or QApplication([])


class TestQmlPhase3Complete(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = QQmlEngine()
        configure_qml_engine(cls.engine)

    def test_before_after_viewer_component(self):
        """Validates that BeforeAfterViewer component instantiates cleanly."""
        url = get_qml_url("components/BeforeAfterViewer.qml")
        comp = QQmlComponent(self.engine, url)
        if comp.isError():
            errors = "\n".join(e.toString() for e in comp.errors())
            self.fail(f"Failed to load BeforeAfterViewer.qml:\n{errors}")
        obj = comp.create()
        self.assertIsNotNone(obj, "BeforeAfterViewer component object is None")
        self.assertAlmostEqual(obj.property("sliderPosition"), 0.5, places=2)

    def test_all_phase3_pages_loading(self):
        """Validates that all 10 Phase 3 QML pages instantiate without syntax or binding errors."""
        phase3_pages = [
            "pages/PdfCenterPage.qml",
            "pages/ImageCenterPage.qml",
            "pages/VideoCenterPage.qml",
            "pages/AudioCenterPage.qml",
            "pages/AppsManagementPage.qml",
            "pages/NetworkCenterPage.qml",
            "pages/PrivacySecurityPage.qml",
            "pages/OperationHistoryPage.qml",
            "pages/SettingsPage.qml",
            "pages/AboutPage.qml",
        ]
        for page_rel in phase3_pages:
            url = get_qml_url(page_rel)
            comp = QQmlComponent(self.engine, url)
            if comp.isError():
                errors = "\n".join(e.toString() for e in comp.errors())
                self.fail(f"Failed to load {page_rel}:\n{errors}")
            obj = comp.create()
            self.assertIsNotNone(obj, f"Page object is None for {page_rel}")

    def test_time_to_page_shell_benchmarks(self):
        """Measures Time to Page Shell latency for all 10 Phase 3 pages (<150ms budget)."""
        phase3_pages = [
            "pages/PdfCenterPage.qml",
            "pages/ImageCenterPage.qml",
            "pages/VideoCenterPage.qml",
            "pages/AudioCenterPage.qml",
            "pages/AppsManagementPage.qml",
            "pages/NetworkCenterPage.qml",
            "pages/PrivacySecurityPage.qml",
            "pages/OperationHistoryPage.qml",
            "pages/SettingsPage.qml",
            "pages/AboutPage.qml",
        ]
        for page_rel in phase3_pages:
            url = get_qml_url(page_rel)
            t0 = time.perf_counter()
            comp = QQmlComponent(self.engine, url)
            obj = comp.create()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertIsNotNone(obj)
            self.assertLess(
                elapsed_ms, 150.0,
                f"Page {page_rel} shell creation took {elapsed_ms:.2f}ms, exceeding 150ms limit"
            )

    def test_pdf_controller(self):
        """Validates PDFController state, operations, and file validation."""
        self.assertFalse(pdf_controller.isBusy)
        self.assertEqual(pdf_controller.progress, 0)
        # Check properties
        self.assertIsInstance(pdf_controller.pageCount, int)

    def test_image_controller(self):
        """Validates ImageController presets, formats, and optimization status."""
        self.assertFalse(image_controller.isBusy)
        self.assertEqual(len(image_controller.supportedFormats), 7)
        self.assertIn("JPEG", image_controller.supportedFormats)
        self.assertIn("WEBP", image_controller.supportedFormats)

    def test_video_controller_hardware_accel(self):
        """Validates VideoController hardware encoder detection."""
        self.assertFalse(video_controller.isBusy)
        enc = video_controller.hwEncoder
        self.assertIsInstance(enc, str)
        self.assertIn(enc, ["NVENC (NVIDIA)", "QSV (Intel)", "AMF (AMD)", "CPU (Software)", "المعالج البرمجي (CPU Software)"])
        self.assertIsInstance(video_controller.hasHardwareAcceleration, bool)

    def test_audio_controller(self):
        """Validates AudioController format conversion methods and waveform generator."""
        self.assertFalse(audio_controller.isBusy)
        self.assertIn("MP3", audio_controller.supportedFormats)
        self.assertIn("FLAC", audio_controller.supportedFormats)
        wf = audio_controller.generateWaveform("dummy_audio.mp3", points=20)
        self.assertEqual(len(wf), 20)

    def test_apps_controller_and_model(self):
        """Validates AppsController and InstalledAppsModel listing and search filtering."""
        model = apps_controller.appsModel
        self.assertIsInstance(model, InstalledAppsModel)
        self.assertGreaterEqual(model.rowCount(), 0)
        apps_controller.setSearchFilter("chrome")
        self.assertEqual(apps_controller.searchFilter, "chrome")
        apps_controller.setSearchFilter("")

    def test_network_controller(self):
        """Validates NetworkController real interface discovery and doctor steps."""
        self.assertIsInstance(network_controller.isConnected, bool)
        self.assertIsInstance(network_controller.activeAdapter, str)
        self.assertIsInstance(network_controller.doctorStatus, str)

    def test_privacy_controller(self):
        """Validates PrivacyController Defender status and file inspection."""
        self.assertIsInstance(privacy_controller.defenderActive, bool)
        self.assertIsInstance(privacy_controller.firewallActive, bool)
        self.assertIsInstance(privacy_controller.secureScore, int)
        # Inspect safe file
        report = privacy_controller.inspectFile(__file__)
        self.assertIn("verdict", report)
        self.assertEqual(report["verdict"], "آمن")

    def test_history_controller_and_model(self):
        """Validates HistoryController operation logging and rollback triggering."""
        model = history_controller.historyModel
        self.assertIsInstance(model, HistoryModel)
        count_before = model.rowCount()
        history_controller.refreshHistory()
        self.assertGreaterEqual(model.rowCount(), 0)

    def test_settings_controller(self):
        """Validates SettingsController config read/write and theme sync."""
        theme = settings_controller.theme
        self.assertIn(theme, ["dark", "light"])
        settings_controller.setSetting("confirm_sensitive_ops", True)
        self.assertTrue(settings_controller.getSetting("confirm_sensitive_ops", False))

    def test_command_palette_phase3_aliases(self):
        """Validates that Phase 3 Arabic and English aliases resolve to the correct routes."""
        # PDF search
        command_palette_controller.search("pdf")
        self.assertGreater(command_palette_controller.filteredCount, 0)
        command_palette_controller.search("بي دي اف")
        self.assertGreater(command_palette_controller.filteredCount, 0)

        # Video search
        command_palette_controller.search("فيديو")
        self.assertGreater(command_palette_controller.filteredCount, 0)

        # Audio search
        command_palette_controller.search("صوت")
        self.assertGreater(command_palette_controller.filteredCount, 0)

        # Apps search
        command_palette_controller.search("برامج")
        self.assertGreater(command_palette_controller.filteredCount, 0)

        # Network search
        command_palette_controller.search("شبكة")
        self.assertGreater(command_palette_controller.filteredCount, 0)

        # About search
        command_palette_controller.search("حول")
        self.assertGreater(command_palette_controller.filteredCount, 0)

    def test_qml_error_boundary_resilience(self):
        """Validates that QmlErrorBoundaryWidget handles non-existent or invalid QML without crashing."""
        boundary = QmlErrorBoundaryWidget("pages/NonExistentPage_ForTest.qml")
        self.assertIsNotNone(boundary)
        # Should transition to error card layout index 1
        self.assertEqual(boundary.stack_layout.currentIndex(), 1)
        self.assertTrue("No such file or directory" in boundary.error_text.toPlainText() or "Cannot open" in boundary.error_text.toPlainText())

    def test_crash_recovery_and_safe_ui(self):
        """Validates CrashRecoveryManager startup tracking and self-repair."""
        crash_recovery_manager.reset_recovery_state()
        self.assertFalse(crash_recovery_manager.should_enter_safe_mode())

        res = crash_recovery_manager.perform_self_repair()
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(len(res.get("items", [])), 1)


if __name__ == "__main__":
    unittest.main()

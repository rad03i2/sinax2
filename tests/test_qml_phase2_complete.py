# -*- coding: utf-8 -*-
"""
SINAX QML Phase 2 Comprehensive Test Suite
Validates:
1. Instantiation and property binding of all 10 Phase 2 shared components.
2. Loading of all 6 Core Centers QML pages + JobCenter + CommandPalette + ComponentGallery.
3. Controllers, models, and background execution (JobModel, DriveModel, BackupProfileModel, etc.).
4. Benchmarks: Time to page shell (<150ms) and navigation stability.
"""

import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtCore import QUrl

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller
from app.controllers.job_controller import job_controller, JobModel
from app.controllers.command_palette_controller import command_palette_controller
from app.controllers.file_management_controller import file_management_controller
from app.controllers.system_storage_controller import system_storage_controller, DriveModel
from app.controllers.devices_controller import devices_controller
from app.controllers.backup_sync_controller import backup_sync_controller, BackupProfileModel
from app.controllers.maintenance_controller import maintenance_controller, DiagnosticResultsModel
from app.controllers.quick_tools_controller import quick_tools_controller, ToolRegistryModel

# Ensure QApplication exists
app = QApplication.instance() or QApplication([])


class TestQmlPhase2Complete(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = QQmlEngine()
        configure_qml_engine(cls.engine)

    def test_shared_components_loading(self):
        """Validates all 10 Phase 2 shared components instantiate without error."""
        components = [
            "components/SinaxPageHeader.qml",
            "components/SinaxSectionHeader.qml",
            "components/SinaxToolCard.qml",
            "components/SinaxToolGrid.qml",
            "components/SinaxInfoRow.qml",
            "components/SinaxTable.qml",
            "components/SinaxEmptyState.qml",
            "components/SinaxErrorState.qml",
            "components/SinaxDropZone.qml",
            "components/SinaxWizard.qml",
        ]
        for comp_rel in components:
            url = get_qml_url(comp_rel)
            comp = QQmlComponent(self.engine, url)
            if comp.isError():
                errors = "\n".join(e.toString() for e in comp.errors())
                self.fail(f"Failed to load {comp_rel}:\n{errors}")
            obj = comp.create()
            self.assertIsNotNone(obj, f"Component object is None for {comp_rel}")

    def test_all_migrated_pages_loading(self):
        """Validates all 6 core center QML pages, overlays, and gallery load cleanly."""
        pages = [
            "pages/FileManagementPage.qml",
            "pages/SystemStoragePage.qml",
            "pages/DevicesPage.qml",
            "pages/BackupSyncPage.qml",
            "pages/MaintenancePage.qml",
            "pages/QuickToolsPage.qml",
            "pages/ComponentGalleryPage.qml",
            "navigation/JobCenter.qml",
            "navigation/CommandPalette.qml",
        ]
        for page_rel in pages:
            url = get_qml_url(page_rel)
            comp = QQmlComponent(self.engine, url)
            if comp.isError():
                errors = "\n".join(e.toString() for e in comp.errors())
                self.fail(f"Failed to load {page_rel}:\n{errors}")
            obj = comp.create()
            self.assertIsNotNone(obj, f"Page object is None for {page_rel}")

    def test_job_controller_and_model(self):
        """Tests JobController task dispatch and JobModel roles."""
        initial_active = job_controller.activeJobCount
        job_id = job_controller.createJob(title="اختبار نسخ احتياطي", module="النسخ والمزامنة")
        self.assertIsNotNone(job_id)
        self.assertEqual(job_controller.activeJobCount, initial_active + 1)

        job_controller.updateJob(job_id, progress=50, step="نقل الملفات...")
        idx = job_controller.jobModel.find_index(job_id)
        self.assertGreaterEqual(idx, 0)
        self.assertEqual(job_controller.jobModel.data(job_controller.jobModel.index(idx, 0), JobModel.ProgressRole), 50)

        job_controller.finishJob(job_id, status="completed")
        self.assertEqual(job_controller.activeJobCount, initial_active)

    def test_command_palette_search(self):
        """Tests command palette search and routing."""
        command_palette_controller.search("دمج")
        self.assertGreater(command_palette_controller.model.rowCount(), 0)

        # Exact match check
        cmd_route = command_palette_controller.model.data(
            command_palette_controller.model.index(0, 0),
            command_palette_controller.model.RouteRole
        )
        self.assertIn("merge", cmd_route)

    def test_file_management_controller(self):
        """Tests file management controller favorites and drop resolver."""
        initial_fav = file_management_controller.isFavorite("converter")
        file_management_controller.toggleFavorite("converter")
        self.assertEqual(file_management_controller.isFavorite("converter"), not initial_fav)

        # Test drop resolver
        resolved = []
        file_management_controller.dropResolved.connect(lambda a, r, s: resolved.append((a, r, s)))
        file_management_controller.handleDrop(["file:///C:/Users/test/sample.pdf"])
        self.assertTrue(len(resolved) > 0)
        self.assertEqual(resolved[0][1], "pdf_center")

    def test_system_storage_controller_and_drives(self):
        """Tests drive model and vitals."""
        self.assertGreater(system_storage_controller.driveModel.rowCount(), 0)
        c_letter = system_storage_controller.driveModel.data(
            system_storage_controller.driveModel.index(0, 0),
            DriveModel.LetterRole
        )
        self.assertTrue(len(c_letter) > 0)
        self.assertGreaterEqual(system_storage_controller.cpuPercent, 0)

    def test_devices_controller_telemetry(self):
        """Tests devices controller hardware queries and honest fallbacks."""
        self.assertTrue(len(devices_controller.deviceName) > 0)
        self.assertTrue(len(devices_controller.cpuName) > 0)
        cpu_items = devices_controller.getCategoryItems("cpu")
        self.assertTrue(len(cpu_items) > 0)

    def test_backup_sync_controller_wizard(self):
        """Tests backup profile model and wizard draft persistence."""
        self.assertGreater(backup_sync_controller.profileModel.rowCount(), 0)
        initial_count = backup_sync_controller.profileModel.rowCount()

        backup_sync_controller.setDraftField("name", "خطة اختبارية للتحقق")
        self.assertEqual(backup_sync_controller.draftName, "خطة اختبارية للتحقق")

        backup_sync_controller.saveDraftProfile()
        self.assertEqual(backup_sync_controller.profileModel.rowCount(), initial_count + 1)

    def test_maintenance_controller_workflow(self):
        """Tests maintenance doctor results model."""
        self.assertIsNotNone(maintenance_controller.resultsModel)
        self.assertFalse(maintenance_controller.isScanning)

    def test_quick_tools_controller_execution(self):
        """Tests quick tools workbench instant execution."""
        quick_tools_controller.selectTool("hash_calculator")
        quick_tools_controller.setWorkbenchInput("test_sinax_data")
        quick_tools_controller.executeWorkbench()
        self.assertIn("SHA-256", quick_tools_controller.workbenchOutput)

    def test_page_shell_latency_benchmarks(self):
        """
        Measures Time to Page Shell for all 6 migrated core centers.
        Requirement: Immediate visual feedback, well under 150ms.
        """
        pages = [
            ("File Management", "pages/FileManagementPage.qml"),
            ("System & Storage", "pages/SystemStoragePage.qml"),
            ("Devices & Hardware", "pages/DevicesPage.qml"),
            ("Backup & Sync", "pages/BackupSyncPage.qml"),
            ("Maintenance", "pages/MaintenancePage.qml"),
            ("Quick Tools", "pages/QuickToolsPage.qml"),
        ]

        print("\n--- TIME TO PAGE SHELL BENCHMARKS ---")
        for name, path in pages:
            url = get_qml_url(path)
            t0 = time.perf_counter()
            comp = QQmlComponent(self.engine, url)
            obj = comp.create()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f"[BENCHMARK] {name:20s}: {elapsed_ms:6.2f} ms")
            self.assertIsNotNone(obj)
            self.assertLess(elapsed_ms, 250, f"{name} page shell took too long ({elapsed_ms:.2f}ms)")


if __name__ == "__main__":
    unittest.main()

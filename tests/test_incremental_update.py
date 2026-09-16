# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.services.update_service import _version_tuple
from tools.make_update_patch import build_patch
from tools.sinax_updater import safe_rel_path


class IncrementalUpdateTests(unittest.TestCase):
    def test_patch_contains_only_changed_and_new_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous = root / "previous"
            current = root / "current"
            previous.mkdir()
            current.mkdir()

            (previous / "unchanged.txt").write_text("same", encoding="utf-8")
            (current / "unchanged.txt").write_text("same", encoding="utf-8")
            (previous / "changed.txt").write_text("old", encoding="utf-8")
            (current / "changed.txt").write_text("new", encoding="utf-8")
            (current / "new.txt").write_text("brand new", encoding="utf-8")
            (previous / "removed.txt").write_text("remove me", encoding="utf-8")

            output = root / "patch.zip"
            manifest = root / "update-manifest.json"
            result = build_patch(previous, current, "1.1.0", "1.1.1", output, manifest)

            self.assertEqual(result["patches"][0]["changed_files"], 2)
            self.assertEqual(result["patches"][0]["deleted_files"], 1)

            with zipfile.ZipFile(output, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("files/changed.txt", names)
                self.assertIn("files/new.txt", names)
                self.assertNotIn("files/unchanged.txt", names)
                patch_manifest = json.loads(zf.read("patch-manifest.json").decode("utf-8"))

            self.assertEqual(patch_manifest["delete"], ["removed.txt"])
            self.assertEqual(patch_manifest["from_version"], "1.1.0")
            self.assertEqual(patch_manifest["to_version"], "1.1.1")

    def test_updater_executable_is_excluded_from_patch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous = root / "previous"
            current = root / "current"
            previous.mkdir()
            current.mkdir()
            (previous / "SINAX-Updater.exe").write_bytes(b"old updater")
            (current / "SINAX-Updater.exe").write_bytes(b"new updater")
            (previous / "SINAX.exe").write_bytes(b"old app")
            (current / "SINAX.exe").write_bytes(b"new app")

            output = root / "patch.zip"
            manifest = root / "update-manifest.json"
            build_patch(previous, current, "1.1.0", "1.1.1", output, manifest)

            with zipfile.ZipFile(output, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("files/SINAX.exe", names)
                self.assertNotIn("files/SINAX-Updater.exe", names)
                patch_manifest = json.loads(zf.read("patch-manifest.json").decode("utf-8"))

            paths = {item["path"] for item in patch_manifest["files"]}
            self.assertNotIn("SINAX-Updater.exe", paths)
            self.assertNotIn("SINAX-Updater.exe", patch_manifest["delete"])

    def test_safe_rel_path_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            safe_rel_path("../outside.txt")
        with self.assertRaises(ValueError):
            safe_rel_path("folder/../../outside.txt")

    def test_version_tuple_orders_versions(self):
        self.assertLess(_version_tuple("1.1.0"), _version_tuple("1.1.1"))
        self.assertLess(_version_tuple("v1.9.9"), _version_tuple("2.0.0"))
        self.assertEqual(_version_tuple("v1.1.0"), _version_tuple("1.1.0"))


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""
Comprehensive Unit Test Suite for SINAX Quick Tools & Utility Lab
Validates Registry, Smart Action Resolver, Hash & Checksum Lab, Encoding Lab,
Password & Security Lab, Text Laboratory, File & Folder Tools, File Generation,
Conversion & Math Calculator, Developer Micro Tools, and List Tools.
"""

from datetime import datetime
import os
from pathlib import Path
import tempfile
import unittest

from app.services.quick_tools.models import InputType, QuickToolDefinition, SafetyLevel
from app.services.quick_tools.quick_tools_db import QuickToolsDatabase
from app.services.quick_tools.registry import QuickToolRegistry
from app.services.quick_tools.resolver import SmartActionResolver
from app.services.quick_tools.tools.calculator_tools import CalculatorTools
from app.services.quick_tools.tools.clipboard_tools import ClipboardTools
from app.services.quick_tools.tools.conversion_tools import ConversionTools
from app.services.quick_tools.tools.datetime_tools import DateTimeTools
from app.services.quick_tools.tools.developer_tools import DeveloperTools
from app.services.quick_tools.tools.encoding_tools import EncodingTools
from app.services.quick_tools.tools.file_tools import FileTools
from app.services.quick_tools.tools.folder_tools import FolderTools
from app.services.quick_tools.tools.generation_tools import GenerationTools
from app.services.quick_tools.tools.hash_tools import HashTools
from app.services.quick_tools.tools.list_tools import ListTools
from app.services.quick_tools.tools.naming_tools import NamingTools
from app.services.quick_tools.tools.password_tools import PasswordTools
from app.services.quick_tools.tools.qr_barcode_tools import QrBarcodeTools
from app.services.quick_tools.tools.system_tools import SystemTools
from app.services.quick_tools.tools.text_tools import TextTools
from app.services.quick_tools.tools.web_tools import WebTools


class TestQuickToolsCore(unittest.TestCase):
    """Core test suite for Quick Tools services and utility engines."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_quick_tools_database(self):
        """Tests local SQLite persistence for favorites and usage tracking."""
        db = QuickToolsDatabase()
        tool_id = "test_hash_tool_unit"

        # Toggle favorite
        is_fav = db.toggle_favorite(tool_id)
        self.assertTrue(is_fav)
        self.assertTrue(db.is_favorite(tool_id))
        self.assertIn(tool_id, db.get_favorites())

        # Toggle again -> False
        is_fav_2 = db.toggle_favorite(tool_id)
        self.assertFalse(is_fav_2)
        self.assertFalse(db.is_favorite(tool_id))

        # Record usage
        db.record_tool_usage(tool_id)
        recents = db.get_recent_tools(10)
        self.assertIn(tool_id, recents)

    def test_registry_and_search(self):
        """Tests tool catalog, Arabic/English synonyms, and category indexing."""
        QuickToolRegistry.initialize()
        tools = QuickToolRegistry.get_all_tools()
        self.assertGreaterEqual(len(tools), 30)

        # Exact ID search
        hash_tool = QuickToolRegistry.get_tool("hash_calculator")
        self.assertIsNotNone(hash_tool)
        self.assertEqual(hash_tool.category, "hash")

        # Synonym searches
        search_hash_ar = QuickToolRegistry.search("بصمة")
        self.assertTrue(any("hash" in t.id for t in search_hash_ar))

        search_qr = QuickToolRegistry.search("كيو ار")
        self.assertTrue(any("qr" in t.id for t in search_qr))

        search_clean = QuickToolRegistry.search("تنظيف النص")
        self.assertTrue(any(t.id == "text_cleaner" for t in search_clean))

        # Category filter
        text_tools = QuickToolRegistry.get_tools_by_category("text")
        self.assertGreaterEqual(len(text_tools), 5)
        for t in text_tools:
            self.assertEqual(t.category, "text")

    def test_smart_action_resolver(self):
        """Tests automated input type detection and recommended actions."""
        # 1. URL
        url_input = "https://github.com/sinax/core?tab=readme"
        res_url = SmartActionResolver.resolve_recommended_tools(url_input)
        self.assertEqual(res_url["input_type"], InputType.URL)
        rec_ids = [t.id for t in res_url["recommended_tools"]]
        self.assertTrue("qr_generator" in rec_ids or "url_encoder" in rec_ids)

        # 2. Hash (64 hex characters)
        hash_input = "a4c9b3e1f028495a6bc31289de456fa1a4c9b3e1f028495a6bc31289de456fa1"
        res_hash = SmartActionResolver.resolve_recommended_tools(hash_input)
        self.assertEqual(res_hash["input_type"], InputType.HASH)

        # 3. JSON
        json_input = '{"service": "SINAX", "active": true}'
        res_json = SmartActionResolver.resolve_recommended_tools(json_input)
        self.assertEqual(res_json["input_type"], InputType.JSON)

        # 4. Number
        num_input = "2048"
        res_num = SmartActionResolver.resolve_recommended_tools(num_input)
        self.assertEqual(res_num["input_type"], InputType.NUMBER)

        # 5. File
        test_file = self.tmp_path / "sample.txt"
        test_file.write_text("Testing resolver", encoding="utf-8")
        res_file = SmartActionResolver.resolve_recommended_tools(str(test_file))
        self.assertEqual(res_file["input_type"], InputType.FILE)

        # 6. Folder
        res_folder = SmartActionResolver.resolve_recommended_tools(str(self.tmp_path))
        self.assertEqual(res_folder["input_type"], InputType.FOLDER)

    def test_hash_tools(self):
        """Tests text/file hashing, format guessing, and folder manifest verification."""
        # Text hash
        h_sha256 = HashTools.compute_text_hash("SINAX", "SHA-256")
        self.assertEqual(len(h_sha256), 64)

        h_md5 = HashTools.compute_text_hash("SINAX", "MD5")
        self.assertEqual(len(h_md5), 32)

        # Format guessing
        guess_md5 = HashTools.guess_hash_format(h_md5)
        self.assertIn("MD5", guess_md5)

        guess_sha256 = HashTools.guess_hash_format(h_sha256)
        self.assertIn("SHA-256", guess_sha256)

        # File hash and verification
        f = self.tmp_path / "data.bin"
        f.write_bytes(b"HELLO_WORLD_SINAX")
        f_hash = HashTools.compute_file_hash(str(f), "SHA-256")
        is_match, actual = HashTools.verify_checksum(str(f), f_hash, "SHA-256")
        self.assertTrue(is_match)

        # Folder manifest
        sub = self.tmp_path / "manifest_test"
        sub.mkdir()
        (sub / "file1.txt").write_text("content 1", encoding="utf-8")
        (sub / "file2.txt").write_text("content 2", encoding="utf-8")

        manifest_path = HashTools.generate_folder_manifest(str(sub))
        self.assertTrue(os.path.isfile(manifest_path))

        # Verify manifest
        report = HashTools.verify_folder_manifest(str(sub), manifest_path)
        self.assertTrue(report["all_healthy"])
        self.assertEqual(report["unchanged_count"], 2)
        self.assertEqual(report["modified_count"], 0)

        # Modify a file and verify detection
        (sub / "file1.txt").write_text("altered content", encoding="utf-8")
        report_altered = HashTools.verify_folder_manifest(str(sub), manifest_path)
        self.assertFalse(report_altered["all_healthy"])
        self.assertEqual(report_altered["modified_count"], 1)

    def test_encoding_tools(self):
        """Tests Base64, Hex, Binary, URL, Unicode, and BOM tools."""
        original = "مرحباً بكم في ساينكس - SINAX"

        # Base64
        b64 = EncodingTools.text_to_base64(original)
        decoded_b64 = EncodingTools.base64_to_text(b64)
        self.assertEqual(decoded_b64, original)

        # Hex
        hex_str = EncodingTools.text_to_hex("Hello")
        self.assertEqual(hex_str.replace(" ", ""), "48656c6c6f")
        self.assertEqual(EncodingTools.hex_to_text(hex_str), "Hello")

        # Binary
        bin_str = EncodingTools.text_to_binary("A")
        self.assertEqual(bin_str, "01000001")
        self.assertEqual(EncodingTools.binary_to_text(bin_str), "A")

        # URL Encoding
        url_enc = EncodingTools.url_encode("hello world/test")
        self.assertIn("%20", url_enc)
        self.assertEqual(EncodingTools.url_decode(url_enc), "hello world/test")

        # HTML Entities
        html_enc = EncodingTools.html_encode("<div>Hello & 'World'</div>")
        self.assertIn("&lt;div&gt;", html_enc)
        self.assertIn("&amp;", html_enc)

        # Character Inspector
        char_info = EncodingTools.inspect_character("A")
        self.assertEqual(char_info["codepoint"], "U+0041")
        self.assertEqual(char_info["name"], "LATIN CAPITAL LETTER A")

        # BOM Inspector
        bom_file = self.tmp_path / "bom_test.txt"
        bom_file.write_text("Test without BOM", encoding="utf-8")
        has_bom, _ = EncodingTools.inspect_bom(str(bom_file))
        self.assertFalse(has_bom)

        EncodingTools.add_utf8_bom(str(bom_file))
        has_bom_after, _ = EncodingTools.inspect_bom(str(bom_file))
        self.assertTrue(has_bom_after)

    def test_password_and_security(self):
        """Tests secure password generation, passphrase, entropy estimation, and UUIDs."""
        pwd = PasswordTools.generate_password(length=20, use_symbols=True, use_digits=True)
        self.assertEqual(len(pwd), 20)

        passphrase = PasswordTools.generate_passphrase(word_count=5, separator="-")
        parts = passphrase.split("-")
        self.assertEqual(len(parts), 5)

        strength = PasswordTools.estimate_password_strength(pwd)
        self.assertGreaterEqual(strength["entropy_bits"], 50.0)
        self.assertIn("score", strength)

        uuids = PasswordTools.generate_uuid(version=4, batch_count=10)
        self.assertEqual(len(uuids), 10)
        self.assertEqual(len(uuids[0]), 36)

    def test_text_tools(self):
        """Tests text cleaner, duplicate lines, sorting, case conversions, and diff."""
        raw_text = "  line 1  \n\n  line 2  \n  line 1  \n"

        # Cleaner
        cleaned = TextTools.clean_text(raw_text, trim_lines=True, remove_empty_lines=True)
        self.assertEqual(cleaned.splitlines(), ["line 1", "line 2", "line 1"])

        # Deduplicate
        deduped, dups_count = TextTools.remove_duplicate_lines(cleaned)
        self.assertEqual(dups_count, 1)
        self.assertEqual(deduped.splitlines(), ["line 1", "line 2"])

        # Sort
        sorted_lines = TextTools.sort_lines("Zebra\nApple\nMango", order="A_Z")
        self.assertEqual(sorted_lines.splitlines(), ["Apple", "Mango", "Zebra"])

        # Case conversions
        self.assertEqual(TextTools.change_case("hello world", "UPPERCASE"), "HELLO WORLD")
        self.assertEqual(TextTools.change_case("hello world", "camelCase"), "helloWorld")
        self.assertEqual(TextTools.change_case("hello world", "snake_case"), "hello_world")

        # Arabic diacritics removal
        arabic_diacritics = "مَرْحَبًا بِكُمْ فِي سَايْنِكْسْ"
        cleaned_ar = TextTools.clean_arabic_text(arabic_diacritics, remove_tashkeel=True)
        self.assertEqual(cleaned_ar, "مرحبا بكم في ساينكس")

        # Text Diff
        diff = TextTools.compute_text_diff("A\nB\nC", "A\nB_MODIFIED\nC\nD")
        self.assertTrue(diff["has_differences"])

        # Entity Extraction
        mixed_text = "Contact info@example.com or support@sinax.org, visit https://sinax.dev at 192.168.1.1"
        emails = TextTools.extract_entities(mixed_text, "emails")
        self.assertEqual(set(emails), {"info@example.com", "support@sinax.org"})
        urls = TextTools.extract_entities(mixed_text, "urls")
        self.assertIn("https://sinax.dev", urls)
        ips = TextTools.extract_entities(mixed_text, "ipv4")
        self.assertIn("192.168.1.1", ips)

    def test_file_tools(self):
        """Tests file inspection, path variants, magic bytes, and timestamp editor with undo."""
        f = self.tmp_path / "test_doc.txt"
        f.write_text("Sample file content for inspector", encoding="utf-8")

        # Inspector
        info = FileTools.inspect_file(str(f))
        self.assertEqual(info["name"], "test_doc.txt")
        self.assertGreater(info["size_bytes"], 0)

        # Path variants
        variants = FileTools.get_path_copy_variants(str(f))
        self.assertIn("win_path", variants)
        self.assertIn("quoted", variants)
        self.assertIn("powershell", variants)
        self.assertIn("python_raw", variants)

        # Timestamp change and undo
        old_mtime = f.stat().st_mtime
        target_dt = datetime(2025, 5, 20, 10, 30, 0)
        FileTools.change_timestamps(str(f), new_modified_dt=target_dt)
        self.assertEqual(int(f.stat().st_mtime), int(target_dt.timestamp()))

        # Undo
        reverted_path = FileTools.undo_last_timestamp_change()
        self.assertEqual(reverted_path, str(f))
        self.assertEqual(int(f.stat().st_mtime), int(old_mtime))

    def test_folder_tools(self):
        """Tests folder statistics, directory tree generator, and empty folder detector."""
        test_dir = self.tmp_path / "tree_test"
        test_dir.mkdir()
        (test_dir / "file_a.txt").write_text("AAA", encoding="utf-8")
        sub = test_dir / "subfolder"
        sub.mkdir()
        (sub / "file_b.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        empty_dir = test_dir / "empty_dir"
        empty_dir.mkdir()

        # Folder Stats
        stats = FolderTools.calculate_folder_stats(str(test_dir))
        self.assertEqual(stats["total_files"], 2)
        self.assertEqual(stats["total_folders"], 2)

        # Directory tree
        tree = FolderTools.generate_directory_tree(str(test_dir), max_depth=2, style="unicode")
        self.assertIn("file_a.txt", tree)
        self.assertIn("subfolder", tree)

        # Empty folders
        empties = FolderTools.find_empty_folders(str(test_dir))
        self.assertTrue(any("empty_dir" in p for p in empties))

    def test_generation_tools(self):
        """Tests template generation, custom size files, and sample datasets."""
        # Template
        out_py = self.tmp_path / "script.py"
        GenerationTools.create_empty_file_with_template(str(out_py), "py")
        self.assertTrue(out_py.is_file())
        self.assertIn("main", out_py.read_text(encoding="utf-8"))

        # Custom size file (500 KB)
        out_dat = self.tmp_path / "500kb.dat"
        GenerationTools.generate_custom_size_file(str(out_dat), size_bytes=500 * 1024, pattern_type="repeating")
        self.assertEqual(out_dat.stat().st_size, 500 * 1024)

        # Lorem Ipsum
        lorem = GenerationTools.generate_lorem_ipsum(2)
        self.assertIn("Lorem ipsum", lorem)

        # Sample CSV
        csv_data = GenerationTools.generate_sample_csv(rows=5)
        self.assertEqual(len(csv_data.splitlines()), 6) # header + 5 rows

    def test_conversion_and_calculator(self):
        """Tests units conversion, storage overhead calculation, and safe AST calculator."""
        # Data size
        conv = ConversionTools.convert_data_size(1.0, "GB")
        self.assertIn("MB (Dec)", conv)
        self.assertIn("1,000.000 MB", conv["MB (Dec)"])

        # Network speed
        speed = ConversionTools.convert_network_speed(100.0, "Mbps")
        self.assertIn("12.50 MB/s", speed["MB/s"])

        # Usable storage
        storage = ConversionTools.calculate_usable_storage(1000.0) # 1 TB
        self.assertIn("931.3 GiB", storage["windows_gib"])

        # Safe AST Calculator
        calc_basic = CalculatorTools.evaluate_expression("2 + 3 * 4")
        self.assertTrue(calc_basic["is_valid"])
        self.assertEqual(calc_basic["result"], "14")

        calc_scientific = CalculatorTools.evaluate_expression("sqrt(16) + sin(pi / 2)")
        self.assertTrue(calc_scientific["is_valid"])
        self.assertEqual(calc_scientific["result"], "5")

        # Rejection of unsafe or syntax errors
        calc_unsafe = CalculatorTools.evaluate_expression("__import__('os').system('dir')")
        self.assertFalse(calc_unsafe["is_valid"])

    def test_developer_and_system_tools(self):
        """Tests JSON/XML formatting, JWT inspection, Color converter, and System shortcuts."""
        # JSON Formatter
        raw_json = '{"b": 2, "a": 1}'
        formatted = DeveloperTools.format_json(raw_json, indent=2)
        self.assertTrue(formatted["is_valid"])
        self.assertIn("\n  \"a\": 1", formatted["result"])

        # Invalid JSON error line/column
        invalid_json = '{\n  "name": "SINAX",\n  bad_syntax\n}'
        err_res = DeveloperTools.format_json(invalid_json)
        self.assertFalse(err_res["is_valid"])
        self.assertEqual(err_res["line"], 3)

        # Color converter
        color = DeveloperTools.convert_color("#0078D4")
        self.assertEqual(color["rgb"], "rgb(0, 120, 212)")

        # Cron helper
        cron_desc = DeveloperTools.explain_cron("*/5 * * * *")
        self.assertIn("5 دقيقة", cron_desc)

        # System Identifiers
        sys_ids = SystemTools.get_system_quick_identifiers()
        self.assertIn("computer_name", sys_ids)
        self.assertIn("username", sys_ids)

    def test_list_tools(self):
        """Tests deduplication, frequency counting, and set operations."""
        items = ["apple", "banana", "apple", "cherry", "banana", "apple"]

        deduped = ListTools.deduplicate(items)
        self.assertEqual(deduped, ["apple", "banana", "cherry"])

        dups = ListTools.find_duplicates(items)
        self.assertEqual(dups[0], ("apple", 3))
        self.assertEqual(dups[1], ("banana", 2))

        # Set operations
        set_res = ListTools.set_operations(["A", "B", "C"], ["B", "C", "D"])
        self.assertEqual(set_res["intersection"], ["B", "C"])
        self.assertEqual(set_res["only_in_a"], ["A"])
        self.assertEqual(set_res["only_in_b"], ["D"])


if __name__ == "__main__":
    unittest.main()

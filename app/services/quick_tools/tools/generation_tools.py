# -*- coding: utf-8 -*-
"""
SINAX File Generation Lab
Generates empty template files, custom sized files (zeros/random/patterns),
NTFS sparse files, test file packs, dummy directory trees, and Lorem Ipsum/CSV/JSON sample data.
"""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import random
import string
from typing import Callable, List, Optional


FSCTL_SET_SPARSE = 0x000900C4


TEMPLATES = {
    "txt": "",
    "json": '{\n  "name": "SINAX Project",\n  "version": "1.0.0",\n  "active": true\n}\n',
    "csv": "id,name,email,role,status\n1,User 1,user1@example.com,Admin,Active\n2,User 2,user2@example.com,User,Active\n",
    "xml": '<?xml version="1.0" encoding="UTF-8"?>\n<root>\n  <item id="1">SINAX Sample Data</item>\n</root>\n',
    "html": '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n  <meta charset="UTF-8">\n  <title>SINAX Document</title>\n</head>\n<body>\n  <h1>مستند تجريبي</h1>\n</body>\n</html>\n',
    "css": "/* SINAX Stylesheet */\nbody {\n  font-family: 'Segoe UI', Tahoma, sans-serif;\n  margin: 0;\n  padding: 0;\n}\n",
    "js": '// SINAX JavaScript Template\nconsole.log("SINAX Ready");\n',
    "py": '# -*- coding: utf-8 -*-\n"""SINAX Python Script."""\n\ndef main():\n    print("Hello from SINAX")\n\nif __name__ == "__main__":\n    main()\n',
    "md": "# مستند تجريبي\n\nمرحباً بك في مستند Markdown المنشأ بواسطة **SINAX**.\n",
    "log": "[INFO] 2026-09-10 12:00:00 - SINAX Log initialized.\n",
}

LOREM_IPSUM_PARAGRAPHS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    "Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. Nullam varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis sollicitudin mauris. Integer in mauris eu nibh euismod gravida.",
    "هذا نص تجريبي بديل باللغة العربية يمكن استخدامه لاختبار التنسيقات وتوزيع النصوص في النماذج والمستندات دون الحاجة إلى نصوص نهائية حقيقية، لتوفير انطباع بصري متوازن ودقيق للتخطيط العام.",
]


class GenerationTools:
    """Creation of mock, dummy, test files, and filesystem structures."""

    @staticmethod
    def create_empty_file_with_template(dest_path: str, ext: str = "txt") -> str:
        """Creates a file with starter template content based on extension."""
        p = Path(dest_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        content = TEMPLATES.get(ext.lower().lstrip("."), "")
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(p.resolve())

    @staticmethod
    def generate_custom_size_file(
        dest_path: str,
        size_bytes: int,
        pattern_type: str = "zeros", # 'zeros', 'random', 'repeating'
        progress_callback: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        chunk_size: int = 1024 * 1024 # 1 MB chunks
    ) -> str:
        """
        Creates a file of exact byte size via chunked streaming.
        Supports zeros, random bytes, or repeating pattern.
        """
        p = Path(dest_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        if pattern_type == "zeros":
            chunk_data = b"\x00" * chunk_size
        elif pattern_type == "repeating":
            base = b"SINAX-STORAGE-TEST-DATA-BLOCK-0123456789ABCDEF\n"
            multiplier = (chunk_size // len(base)) + 1
            chunk_data = (base * multiplier)[:chunk_size]
        else: # random
            chunk_data = None # generated per chunk

        bytes_written = 0
        with open(dest_path, "wb") as f:
            while bytes_written < size_bytes:
                if cancel_check and cancel_check():
                    raise InterruptedError("File generation cancelled.")

                remaining = size_bytes - bytes_written
                curr_chunk_sz = min(chunk_size, remaining)

                if pattern_type == "random":
                    data = os.urandom(curr_chunk_sz)
                else:
                    data = chunk_data[:curr_chunk_sz]

                f.write(data)
                bytes_written += len(data)

                if progress_callback:
                    progress_callback(bytes_written, size_bytes)

        return str(p.resolve())

    @staticmethod
    def generate_sparse_file(dest_path: str, logical_size_bytes: int) -> bool:
        """
        Creates an NTFS sparse file where logical size can be gigabytes
        while actual physical disk allocation remains near zero.
        """
        p = Path(dest_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        # 1. Create file and set sparse attribute
        with open(dest_path, "wb") as f:
            f.seek(logical_size_bytes - 1)
            f.write(b"\x00")

        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateFileW(
                str(p),
                0x40000000 | 0x80000000, # GENERIC_READ | GENERIC_WRITE
                0x00000001,              # FILE_SHARE_READ
                None,
                3,                       # OPEN_EXISTING
                0x00000080,              # FILE_ATTRIBUTE_NORMAL
                None
            )
            if handle != -1:
                bytes_returned = wintypes.DWORD()
                kernel32.DeviceIoControl(
                    handle,
                    FSCTL_SET_SPARSE,
                    None, 0,
                    None, 0,
                    ctypes.byref(bytes_returned),
                    None
                )
                kernel32.CloseHandle(handle)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def generate_test_file_pack(
        target_dir: str,
        file_count: int = 50,
        file_size_kb: int = 100,
        prefix: str = "test_file_"
    ) -> List[str]:
        """Creates a pack of test files for storage, sync, or backup benchmarking."""
        out = Path(target_dir)
        out.mkdir(parents=True, exist_ok=True)
        created = []
        dummy_chunk = b"X" * (file_size_kb * 1024)

        for i in range(1, file_count + 1):
            fp = out / f"{prefix}{i:04d}.dat"
            with open(fp, "wb") as f:
                f.write(dummy_chunk)
            created.append(str(fp))

        return created

    @staticmethod
    def generate_dummy_folder_tree(
        root_dir: str,
        num_folders: int = 5,
        files_per_folder: int = 10
    ) -> int:
        """Builds dummy folder hierarchy for file organizer testing."""
        root = Path(root_dir)
        root.mkdir(parents=True, exist_ok=True)
        total_created = 0

        for f_idx in range(1, num_folders + 1):
            sub = root / f"Folder_{f_idx:02d}"
            sub.mkdir(exist_ok=True)
            for file_idx in range(1, files_per_folder + 1):
                p = sub / f"document_{file_idx:03d}.txt"
                p.write_text(f"Dummy file {file_idx} inside {sub.name}\n", encoding="utf-8")
                total_created += 1

        return total_created

    @staticmethod
    def generate_lorem_ipsum(paragraph_count: int = 3) -> str:
        """Generates Lorem Ipsum paragraphs."""
        count = max(1, min(paragraph_count, 20))
        res = []
        for i in range(count):
            res.append(LOREM_IPSUM_PARAGRAPHS[i % len(LOREM_IPSUM_PARAGRAPHS)])
        return "\n\n".join(res)

    @staticmethod
    def generate_sample_csv(rows: int = 10) -> str:
        """Generates clean sample CSV data."""
        lines = ["ID,Full Name,Email,Country,Status,Points"]
        names = ["Ahmad Salem", "Sarah Connor", "Ali Mansoor", "Elena Rostova", "Omar Khaled", "Jessica Jones"]
        countries = ["Egypt", "Saudi Arabia", "UAE", "Germany", "United States", "Jordan"]
        statuses = ["Active", "Pending", "Verified"]

        for i in range(1, rows + 1):
            name = names[(i - 1) % len(names)]
            email = f"user{i}@example.com"
            country = countries[(i - 1) % len(countries)]
            status = statuses[(i - 1) % len(statuses)]
            points = (i * 137) % 500 + 50
            lines.append(f'{i},"{name}",{email},{country},{status},{points}')

        return "\n".join(lines)

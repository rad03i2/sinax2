# -*- coding: utf-8 -*-
"""
SINAX Hash & Checksum Lab
Implements 10 cryptographic hash algorithms, chunked streaming file hashing,
batch hash generation, format guessing, checksum verification, and folder manifests.
"""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


SUPPORTED_HASH_ALGORITHMS = [
    "SHA-256",
    "SHA-512",
    "SHA-1",
    "MD5",
    "SHA-224",
    "SHA-384",
    "SHA3-256",
    "SHA3-512",
    "BLAKE2b",
    "BLAKE2s",
]

HASH_CREATORS = {
    "SHA-256": hashlib.sha256,
    "SHA-512": hashlib.sha512,
    "SHA-1": hashlib.sha1,
    "MD5": hashlib.md5,
    "SHA-224": hashlib.sha224,
    "SHA-384": hashlib.sha384,
    "SHA3-256": hashlib.sha3_256,
    "SHA3-512": hashlib.sha3_512,
    "BLAKE2B": hashlib.blake2b,
    "BLAKE2S": hashlib.blake2s,
}


class HashTools:
    """Core cryptographic hashing and verification engine."""

    @staticmethod
    def compute_text_hash(text: str, algorithm: str = "SHA-256") -> str:
        """Computes hash of raw text string (UTF-8 encoded)."""
        algo_key = algorithm.upper().replace("-", "")
        creator = HASH_CREATORS.get(algorithm) or HASH_CREATORS.get(algo_key, hashlib.sha256)
        h = creator()
        h.update(text.encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def compute_file_hash(
        file_path: str,
        algorithm: str = "SHA-256",
        progress_callback: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        chunk_size: int = 128 * 1024
    ) -> str:
        """
        Computes cryptographic hash of a file using chunked streaming.
        Safe for multi-gigabyte ISOs and archives without loading full file into memory.
        """
        algo_key = algorithm.upper().replace("-", "")
        creator = HASH_CREATORS.get(algorithm) or HASH_CREATORS.get(algo_key, hashlib.sha256)
        h = creator()

        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        total_bytes = p.stat().st_size
        bytes_read = 0

        with open(file_path, "rb") as f:
            while True:
                if cancel_check and cancel_check():
                    raise InterruptedError("Hash computation cancelled by user.")
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
                bytes_read += len(chunk)
                if progress_callback and total_bytes > 0:
                    progress_callback(bytes_read, total_bytes)

        return h.hexdigest()

    @staticmethod
    def guess_hash_format(hash_str: str) -> str:
        """
        Infers likely algorithm from hex digest length.
        Clearly returned as a format estimation, not a certainty.
        """
        clean = hash_str.strip().lower()
        # Verify hex characters only
        if not all(c in "0123456789abcdef" for c in clean):
            return "غير صالح (ليس تنسيق Hex سداسي عشري)"

        length = len(clean)
        guesses = {
            32: "تنسيق MD5 مرجح (128-bit / 32 حرف)",
            40: "تنسيق SHA-1 مرجح (160-bit / 40 حرف)",
            56: "تنسيق SHA-224 أو SHA3-224 مرجح (224-bit / 56 حرف)",
            64: "تنسيق SHA-256 أو BLAKE2s مرجح (256-bit / 64 حرف)",
            96: "تنسيق SHA-384 أو SHA3-384 مرجح (384-bit / 96 حرف)",
            128: "تنسيق SHA-512 أو BLAKE2b مرجح (512-bit / 128 حرف)",
        }
        return guesses.get(length, f"طول غير قياسي ({length} حرف)")

    @staticmethod
    def verify_checksum(file_path: str, expected_hash: str, algorithm: str = "SHA-256") -> Tuple[bool, str]:
        """
        Verifies whether file digest matches expected checksum string.
        Returns (is_match, actual_hash).
        """
        actual = HashTools.compute_file_hash(file_path, algorithm=algorithm)
        is_match = actual.strip().lower() == expected_hash.strip().lower()
        return is_match, actual

    @staticmethod
    def generate_folder_manifest(
        folder_path: str,
        algorithm: str = "SHA-256",
        output_file: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Generates a standard SHA256 manifest for all files in a folder tree.
        Format compatible with standard sha256sum: '<hash>  <relative_path>'
        """
        root = Path(folder_path)
        if not root.is_dir():
            raise NotADirectoryError(f"Directory not found: {folder_path}")

        files = [p for p in root.rglob("*") if p.is_file() and p.name != "SINAX_MANIFEST.sha256"]
        total = len(files)
        lines = []

        for idx, fpath in enumerate(files):
            if cancel_check and cancel_check():
                raise InterruptedError("Manifest creation cancelled.")
            rel_path = fpath.relative_to(root).as_posix()
            digest = HashTools.compute_file_hash(str(fpath), algorithm=algorithm)
            lines.append(f"{digest} *{rel_path}")
            if progress_callback:
                progress_callback(idx + 1, total, rel_path)

        manifest_content = "\n".join(lines)
        target_path = output_file or str(root / "SINAX_MANIFEST.sha256")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(manifest_content)

        return target_path

    @staticmethod
    def verify_folder_manifest(
        folder_path: str,
        manifest_file: Optional[str] = None,
        algorithm: str = "SHA-256",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Verifies folder contents against an existing manifest.
        Returns counts and details of:
        - unchanged
        - modified
        - missing
        - new (not present in manifest)
        """
        root = Path(folder_path)
        manifest_path = Path(manifest_file) if manifest_file else (root / "SINAX_MANIFEST.sha256")
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        expected_map: Dict[str, str] = {}
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    ehash = parts[0].strip()
                    rel_p = parts[1].lstrip("* ").strip()
                    expected_map[rel_p] = ehash

        current_files = {
            p.relative_to(root).as_posix(): p
            for p in root.rglob("*")
            if p.is_file() and p.name != "SINAX_MANIFEST.sha256"
        }

        unchanged: List[str] = []
        modified: List[str] = []
        missing: List[str] = []
        new_files: List[str] = []

        total_checks = len(expected_map)
        for idx, (rel_path, expected_hash) in enumerate(expected_map.items()):
            if cancel_check and cancel_check():
                raise InterruptedError("Verification cancelled.")
            if rel_path not in current_files:
                missing.append(rel_path)
            else:
                actual_hash = HashTools.compute_file_hash(str(current_files[rel_path]), algorithm=algorithm)
                if actual_hash.lower() == expected_hash.lower():
                    unchanged.append(rel_path)
                else:
                    modified.append(rel_path)
            if progress_callback:
                progress_callback(idx + 1, total_checks, rel_path)

        for rel_path in current_files:
            if rel_path not in expected_map:
                new_files.append(rel_path)

        return {
            "unchanged_count": len(unchanged),
            "modified_count": len(modified),
            "missing_count": len(missing),
            "new_count": len(new_files),
            "unchanged": unchanged,
            "modified": modified,
            "missing": missing,
            "new": new_files,
            "all_healthy": len(modified) == 0 and len(missing) == 0,
        }

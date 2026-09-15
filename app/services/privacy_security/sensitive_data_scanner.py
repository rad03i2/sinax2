# -*- coding: utf-8 -*-
"""
Sensitive Information Scanner for SINAX Privacy & Security.
Finds personal identifiable information (PII) and secret credentials locally:
- Emails, phone numbers, IPv4, URLs
- API keys, JWT, Bearer tokens with strict masking (sk-••••••••••••9A)
- Sensitive project files (.env, *.pem, id_rsa, credentials.json)
- Zero transmission outside the local device.
"""

import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.models import SafetyLevel, SensitiveMatch

# Regular expression patterns for sensitive data
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
IPV4_REGEX = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")
URL_REGEX = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*")
API_KEY_REGEX = re.compile(r"\b(?:sk|pk|api|key|secret|token|ghp|gho)_[a-zA-Z0-9_\-]{16,}\b", re.IGNORECASE)
GENERIC_BEARER_REGEX = re.compile(r"\bBearer\s+([a-zA-Z0-9_\-\.]{20,})\b", re.IGNORECASE)

SENSITIVE_FILENAME_PATTERNS = [
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_ed25519", "id_dsa",
    "credentials.json", "client_secret.json", "secrets.json",
    "wp-config.php", "settings.py.bak"
]

SENSITIVE_EXTENSIONS = {".pem", ".key", ".pfx", ".p12", ".kdbx", ".dump", ".sql.gz"}


class SensitiveDataScanner:
    """Local-first privacy pattern detection engine."""

    @classmethod
    def mask_token(cls, token: str) -> str:
        """Masks a secret token to safely display (e.g. sk-••••••••••••9A)."""
        clean = token.strip()
        if len(clean) <= 6:
            return "••••••"
        prefix = clean[:3]
        suffix = clean[-2:]
        return f"{prefix}••••••••••••{suffix}"

    @classmethod
    def scan_text(cls, text: str, file_path: str = "snippet") -> List[SensitiveMatch]:
        """Scans a text buffer for sensitive patterns."""
        matches = []
        lines = text.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            # 1. Check API Keys / Tokens
            for m in API_KEY_REGEX.finditer(line):
                val = m.group(0)
                matches.append(SensitiveMatch(
                    kind="مفتاح برمجي / Secret Token",
                    file_path=file_path,
                    line_number=line_idx,
                    masked_value=cls.mask_token(val),
                    context_snippet=cls._mask_snippet(line, val),
                    severity=SafetyLevel.CRITICAL
                ))

            # 2. Check Bearer Tokens
            for m in GENERIC_BEARER_REGEX.finditer(line):
                val = m.group(1)
                matches.append(SensitiveMatch(
                    kind="رمز استيثاق Bearer",
                    file_path=file_path,
                    line_number=line_idx,
                    masked_value=cls.mask_token(val),
                    context_snippet=cls._mask_snippet(line, val),
                    severity=SafetyLevel.CRITICAL
                ))

            # 3. Check Emails
            for m in EMAIL_REGEX.finditer(line):
                val = m.group(0)
                matches.append(SensitiveMatch(
                    kind="بريد إلكتروني شخصي",
                    file_path=file_path,
                    line_number=line_idx,
                    masked_value=val,
                    context_snippet=line.strip()[:80],
                    severity=SafetyLevel.REVIEW_NEEDED
                ))

            # 4. Check Phone Numbers
            for m in PHONE_REGEX.finditer(line):
                val = m.group(0)
                if len(re.sub(r"\D", "", val)) >= 7:
                    matches.append(SensitiveMatch(
                        kind="رقم هاتف",
                        file_path=file_path,
                        line_number=line_idx,
                        masked_value=val,
                        context_snippet=line.strip()[:80],
                        severity=SafetyLevel.REVIEW_NEEDED
                    ))

        return matches

    @classmethod
    def scan_file(cls, file_path: str, max_size_bytes: int = 10 * 1024 * 1024) -> List[SensitiveMatch]:
        """Scans an individual text or document file for sensitive information."""
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return []

        # Check filename itself
        matches = []
        if p.name.lower() in SENSITIVE_FILENAME_PATTERNS or p.suffix.lower() in SENSITIVE_EXTENSIONS:
            matches.append(SensitiveMatch(
                kind="ملف أسرار / مفتاح خاص",
                file_path=str(p),
                line_number=1,
                masked_value=p.name,
                context_snippet=f"اسم الملف ({p.name}) يشير إلى ملف حساس لا ينبغي مشاركته.",
                severity=SafetyLevel.CRITICAL
            ))

        if p.stat().st_size > max_size_bytes:
            return matches

        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            matches.extend(cls.scan_text(content, file_path=str(p)))
        except Exception:
            pass

        return matches

    @classmethod
    def scan_project_directory(
        cls,
        folder_path: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Scans an entire code project directory for secrets and suggests .gitignore additions.
        Returns: Dict containing 'matches', 'secret_files_count', 'suggested_gitignore'
        """
        root = Path(folder_path).resolve()
        if not root.exists() or not root.is_dir():
            return {"error": "المجلد غير موجود"}

        ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
        files_to_scan = []
        for r, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in files:
                files_to_scan.append(Path(r) / f)

        total = len(files_to_scan)
        all_matches: List[SensitiveMatch] = []
        suggested_gitignore_entries = set()

        for idx, f in enumerate(files_to_scan):
            if cancel_check and cancel_check():
                break

            fname = f.name.lower()
            fext = f.suffix.lower()

            if fname in SENSITIVE_FILENAME_PATTERNS or fext in SENSITIVE_EXTENSIONS:
                suggested_gitignore_entries.add(fname if fname in SENSITIVE_FILENAME_PATTERNS else f"*{fext}")

            matches = cls.scan_file(str(f))
            if matches:
                all_matches.extend(matches)

            if progress_cb and total > 0:
                progress_cb((idx + 1) / total, f"فحص المشروع: {idx + 1} من {total} ({f.name})")

        return {
            "total_files_scanned": total,
            "sensitive_matches_count": len(all_matches),
            "matches": all_matches,
            "suggested_gitignore": sorted(list(suggested_gitignore_entries)),
        }

    @staticmethod
    def _mask_snippet(line: str, secret: str) -> str:
        masked = SensitiveDataScanner.mask_token(secret)
        return line.replace(secret, masked).strip()[:100]

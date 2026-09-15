# -*- coding: utf-8 -*-
"""
Log Analyzer Service for SINAX Maintenance & Repair Center.
Safely extracts and parses entries from Windows CBS.log (for SFC details)
and DISM.log in read-only mode without modifying system files.
"""

import os
import re
from typing import Dict, List, Optional
from app.services.maintenance.models import CBSLogEntry


class LogAnalyzerService:
    """Parses Windows Servicing logs (CBS.log and dism.log)."""

    CBS_LOG_PATH = r"C:\Windows\Logs\CBS\CBS.log"
    DISM_LOG_PATH = r"C:\Windows\Logs\DISM\dism.log"

    @classmethod
    def get_sfc_cbs_entries(cls, max_entries: int = 50) -> List[CBSLogEntry]:
        """
        Parses CBS.log for '[SR]' tags (SFC Resource Protection entries).
        Extracts timestamp, repair status, and file path.
        """
        results: List[CBSLogEntry] = []
        if not os.path.exists(cls.CBS_LOG_PATH):
            return results

        # Read the tail of the log file to avoid loading gigabytes into memory
        try:
            with open(cls.CBS_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                # Seek near the end if file is large (> 10MB)
                f.seek(0, os.SEEK_END)
                size = f.tell()
                read_bytes = min(size, 8 * 1024 * 1024) # read last 8 MB max
                f.seek(size - read_bytes)
                lines = f.readlines()

            re_sr = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\s+Info\s+CSI\s+.*\[SR\]\s+(.*)$")

            for line in reversed(lines):
                match = re_sr.match(line.strip())
                if match:
                    ts = match.group(1)
                    content = match.group(2)

                    status = "معلومة"
                    file_path = ""

                    if "Repairing corrupted file" in content:
                        status = "تم الإصلاح بنجاح"
                        # Extract file path
                        parts = content.split("Repairing corrupted file")
                        if len(parts) > 1:
                            file_path = parts[1].strip()
                    elif "Cannot repair member file" in content:
                        status = "تعذر الإصلاح"
                        parts = content.split("Cannot repair member file")
                        if len(parts) > 1:
                            file_path = parts[1].strip()
                    elif "Corrupt file" in content:
                        status = "ملف تالف مكتشف"
                    elif "Beginning Verify and Repair" in content:
                        status = "بدء فحص SFC"
                    elif "Verification 100% complete" in content:
                        status = "اكتمال الفحص 100%"

                    results.append(CBSLogEntry(
                        timestamp_str=ts,
                        status=status,
                        file_path=file_path,
                        details=content
                    ))

                    if len(results) >= max_entries:
                        break
        except Exception:
            pass

        return results

    @classmethod
    def get_dism_recent_errors(cls, max_entries: int = 25) -> List[Dict[str, str]]:
        """
        Extracts recent warnings and errors from DISM.log.
        """
        errors: List[Dict[str, str]] = []
        if not os.path.exists(cls.DISM_LOG_PATH):
            return errors

        try:
            with open(cls.DISM_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                read_bytes = min(size, 4 * 1024 * 1024) # last 4MB
                f.seek(size - read_bytes)
                lines = f.readlines()

            re_err = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\s+(Warning|Error)\s+DISM\s+(.*)$")

            for line in reversed(lines):
                match = re_err.match(line.strip())
                if match:
                    errors.append({
                        "timestamp": match.group(1),
                        "level": "تحذير" if match.group(2) == "Warning" else "خطأ",
                        "message": match.group(3).strip(),
                    })
                    if len(errors) >= max_entries:
                        break
        except Exception:
            pass

        return errors

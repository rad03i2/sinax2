# -*- coding: utf-8 -*-
"""
SINAX Spreadsheet Converter
Handles Excel (XLSX), CSV, TSV, and ODS.
Supports multi-sheet extraction, delimiters, and encodings.
"""

import csv
import io
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import openpyxl

from app.services.conversion.base_converter import BaseConverter
from app.core.logger import get_logger

logger = get_logger("spreadsheet_converter")


class SpreadsheetConverter(BaseConverter):
    converter_id = "spreadsheet_converter"
    name_ar = "محول الجداول وجداول البيانات"
    category = "spreadsheets"
    required_tools = []

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "sheet_mode": {
                "type": "select",
                "options": ["الورقة الأولى فقط (First Sheet)", "تصدير كل الأوراق كملفات مستقلة (All Sheets)"],
                "default": "الورقة الأولى فقط (First Sheet)",
                "label": "أوراق العمل في Excel"
            },
            "csv_delimiter": {
                "type": "select",
                "options": ["فاصلة Comma (,)", "فاصلة منقوطة Semicolon (;)", "مسافة جدولة Tab (\t)"],
                "default": "فاصلة Comma (,)",
                "label": "نوع فاصل الحقول"
            },
            "encoding": {
                "type": "select",
                "options": ["UTF-8 مع BOM (متوافق مع Excel)", "UTF-8 عادي", "Windows-1256"],
                "default": "UTF-8 مع BOM (متوافق مع Excel)",
                "label": "ترميز النصوص"
            }
        }

    def convert(
        self,
        source: Path,
        destination: Path,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        options = options or {}
        valid, msg = self.validate_input(source)
        if not valid:
            return False, msg

        if cancel_token and cancel_token():
            return False, "تم إلغاء العملية."

        src_ext = source.suffix.lower().lstrip('.')
        dst_ext = destination.suffix.lower().lstrip('.')
        destination.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(10.0, f"معالجة جدول: {source.name}")

        try:
            # Excel -> CSV / TSV
            if src_ext in ["xlsx", "xlsm"] and dst_ext in ["csv", "tsv"]:
                return self._xlsx_to_csv(source, destination, dst_ext, options, progress_callback, cancel_token)

            # CSV / TSV -> Excel
            if src_ext in ["csv", "tsv"] and dst_ext in ["xlsx"]:
                return self._csv_to_xlsx(source, destination, options, progress_callback, cancel_token)

            # Excel / CSV <-> ODS (requires LibreOffice if pure python odf not installed)
            if "ods" in [src_ext, dst_ext]:
                from app.services.conversion.dependency_manager import dependency_manager
                if not dependency_manager.is_tool_available("soffice"):
                    return False, "يتطلب تحويل ODS تثبيت LibreOffice على حاسوبك."
                return self._convert_via_libreoffice(source, destination, progress_callback, cancel_token)

            return False, f"تحويل الجداول غير مدعوم للصيغ: {src_ext} -> {dst_ext}"

        except Exception as e:
            logger.error(f"Spreadsheet conversion failed: {e}")
            return False, f"فشل تحويل الجدول: {str(e)}"

    def _xlsx_to_csv(
        self,
        source: Path,
        destination: Path,
        dst_ext: str,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
        sheet_mode = options.get("sheet_mode", "الورقة الأولى فقط (First Sheet)")
        delim = "\t" if dst_ext == "tsv" else (";" if "منقوطة" in options.get("csv_delimiter", "") else ",")
        encoding = "utf-8-sig" if "BOM" in options.get("encoding", "") else ("cp1256" if "1256" in options.get("encoding", "") else "utf-8")

        if "كل الأوراق" in sheet_mode:
            # Export all sheets as individual files
            exported = []
            for sheet_name in wb.sheetnames:
                if cancel_token and cancel_token():
                    return False, "تم إلغاء العملية."
                ws = wb[sheet_name]
                out_path = destination.parent / f"{destination.stem}_{sheet_name}.{dst_ext}"
                with open(out_path, "w", encoding=encoding, newline="") as f:
                    writer = csv.writer(f, delimiter=delim)
                    for row in ws.iter_rows(values_only=True):
                        writer.writerow(["" if c is None else str(c) for c in row])
                exported.append(out_path.name)
            wb.close()
            return True, f"تم تصدير {len(exported)} أوراق بنجاح: {', '.join(exported)}"
        else:
            # First sheet only
            ws = wb.active
            with open(destination, "w", encoding=encoding, newline="") as f:
                writer = csv.writer(f, delimiter=delim)
                for row in ws.iter_rows(values_only=True):
                    writer.writerow(["" if c is None else str(c) for c in row])
            wb.close()
            return True, f"تم تحويل الورقة الأولى بنجاح إلى: {destination.name}"

    def _csv_to_xlsx(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = source.stem[:30]

        # Auto-detect delimiter
        raw = source.read_text(encoding="utf-8-sig", errors="replace")
        sample = raw[:2048]
        delim = "\t" if source.suffix.lower() == ".tsv" or "\t" in sample else (";" if ";" in sample else ",")

        reader = csv.reader(io.StringIO(raw), delimiter=delim)
        for r_idx, row in enumerate(reader, 1):
            if cancel_token and cancel_token():
                return False, "تم إلغاء العملية."
            for c_idx, val in enumerate(row, 1):
                # Try numeric casting if clean
                if val.isdigit():
                    ws.cell(row=r_idx, column=c_idx, value=int(val))
                else:
                    ws.cell(row=r_idx, column=c_idx, value=val)

        wb.save(destination)
        return True, f"تم تحويل الملف بنجاح إلى جدول Excel: {destination.name}"

    def _convert_via_libreoffice(
        self,
        source: Path,
        destination: Path,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        import subprocess
        from app.services.conversion.dependency_manager import dependency_manager
        soffice_path = dependency_manager.get_tool_path("soffice")
        if not soffice_path:
            return False, "LibreOffice غير متوفر."

        target_ext = destination.suffix.lower().lstrip('.')
        cmd = [
            str(soffice_path),
            "--headless",
            "--convert-to",
            target_ext,
            "--outdir",
            str(destination.parent),
            str(source)
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        expected_out = destination.parent / f"{source.stem}.{target_ext}"
        if expected_out.exists() and expected_out != destination:
            expected_out.replace(destination)
        if destination.exists():
            return True, f"تم التحويل بنجاح عبر LibreOffice: {destination.name}"
        return False, f"فشل تحويل LibreOffice: {proc.stderr}"

# -*- coding: utf-8 -*-
"""
SINAX Data Converter
Fast, robust conversion between structured data formats: CSV, TSV, JSON, XML, YAML.
Provides strict validation and exact line number reporting on syntax errors.
"""

import json
import csv
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import yaml

from app.services.conversion.base_converter import BaseConverter
from app.core.logger import get_logger

logger = get_logger("data_converter")


class DataConverter(BaseConverter):
    converter_id = "data_converter"
    name_ar = "محول البيانات المهيكلة"
    category = "data"
    required_tools = []

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "indent": {
                "type": "select",
                "options": ["مسافتان (2 spaces)", "4 مسافات (4 spaces)", "مضغوط بدون مسافات (Minified)"],
                "default": "مسافتان (2 spaces)",
                "label": "تنسيق المسافات (Indentation)"
            },
            "encoding": {
                "type": "select",
                "options": ["UTF-8", "UTF-8 مع BOM", "Windows-1256 (عربي قديم)"],
                "default": "UTF-8",
                "label": "ترميز النصوص (Encoding)"
            },
            "csv_delimiter": {
                "type": "select",
                "options": ["فاصلة Comma (,)", "فاصلة منقوطة Semicolon (;)", "مسافة جدولة Tab (\t)", "خط عمودي Pipe (|)"],
                "default": "فاصلة Comma (,)",
                "label": "فاصل الحقول في CSV"
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
        encoding = self._resolve_encoding(options.get("encoding", "UTF-8"))

        if progress_callback:
            progress_callback(15.0, f"قراءة ملف البيانات: {source.name}")

        try:
            raw_text = source.read_text(encoding=encoding, errors="replace")
        except Exception:
            raw_text = source.read_text(encoding="utf-8", errors="replace")

        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 1. JSON <-> YAML
            if src_ext == "json" and dst_ext in ["yaml", "yml"]:
                return self._json_to_yaml(raw_text, destination, options, progress_callback)
            if src_ext in ["yaml", "yml"] and dst_ext == "json":
                return self._yaml_to_json(raw_text, destination, options, progress_callback)

            # 2. CSV / TSV <-> JSON
            if src_ext in ["csv", "tsv"] and dst_ext == "json":
                return self._csv_to_json(raw_text, src_ext, destination, options, progress_callback)
            if src_ext == "json" and dst_ext in ["csv", "tsv"]:
                return self._json_to_csv(raw_text, dst_ext, destination, options, progress_callback)

            # 3. CSV / TSV <-> TSV / CSV
            if src_ext in ["csv", "tsv"] and dst_ext in ["csv", "tsv"]:
                return self._csv_to_tsv(raw_text, src_ext, dst_ext, destination, options, progress_callback)

            # 4. CSV <-> XML
            if src_ext in ["csv", "tsv"] and dst_ext == "xml":
                return self._csv_to_xml(raw_text, src_ext, destination, options, progress_callback)
            if src_ext == "xml" and dst_ext in ["csv", "tsv"]:
                return self._xml_to_csv(raw_text, dst_ext, destination, options, progress_callback)

            # 5. JSON <-> XML
            if src_ext == "json" and dst_ext == "xml":
                return self._json_to_xml(raw_text, destination, options, progress_callback)
            if src_ext == "xml" and dst_ext == "json":
                return self._xml_to_json(raw_text, destination, options, progress_callback)

            return False, f"زوج التحويل غير مدعوم: {src_ext} -> {dst_ext}"

        except Exception as e:
            logger.error(f"Data conversion failed: {e}")
            return False, f"فشل التحويل: {str(e)}"

    def _resolve_encoding(self, enc_str: str) -> str:
        if "BOM" in enc_str:
            return "utf-8-sig"
        if "1256" in enc_str:
            return "cp1256"
        return "utf-8"

    def _get_indent(self, opt_val: Any) -> Optional[int]:
        if isinstance(opt_val, int):
            return opt_val
        if not isinstance(opt_val, str):
            return 2
        if "Minified" in opt_val:
            return None
        if "4" in opt_val:
            return 4
        return 2

    # --- Implementations ---
    def _json_to_yaml(self, text: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return False, f"خطأ في بنية JSON عند السطر {e.lineno}، العمود {e.colno}: {e.msg}"
        out = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        dst.write_text(out, encoding="utf-8")
        return True, f"تم تحويل JSON بنجاح إلى YAML: {dst.name}"

    def _yaml_to_json(self, text: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            return False, f"خطأ في قواعد YAML: {str(e)}"
        indent = self._get_indent(opts.get("indent", "مسافتان (2 spaces)"))
        out = json.dumps(data, ensure_ascii=False, indent=indent)
        dst.write_text(out, encoding="utf-8")
        return True, f"تم تحويل YAML بنجاح إلى JSON: {dst.name}"

    def _csv_to_json(self, text: str, src_ext: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        delim = "\t" if src_ext == "tsv" else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delim)
        rows = list(reader)
        indent = self._get_indent(opts.get("indent", "مسافتان (2 spaces)"))
        dst.write_text(json.dumps(rows, ensure_ascii=False, indent=indent), encoding="utf-8")
        return True, f"تم تحويل {len(rows)} صفاً بنجاح إلى JSON: {dst.name}"

    def _json_to_csv(self, text: str, dst_ext: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return False, f"خطأ في JSON عند السطر {e.lineno}: {e.msg}"

        if not isinstance(data, list):
            data = [data]
        if not data:
            dst.write_text("", encoding="utf-8")
            return True, "تم إنشاء ملف فارغ (المصدر لا يحتوي بيانات)."

        # Collect all keys
        keys = []
        for it in data:
            if isinstance(it, dict):
                for k in it.keys():
                    if k not in keys:
                        keys.append(k)

        delim = "\t" if dst_ext == "tsv" else ","
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=keys, delimiter=delim)
        writer.writeheader()
        for row in data:
            if isinstance(row, dict):
                writer.writerow(row)

        dst.write_text(output.getvalue(), encoding="utf-8-sig")
        return True, f"تم إنشاء ملف {dst_ext.upper()} بنجاح: {dst.name}"

    def _csv_to_tsv(self, text: str, src_ext: str, dst_ext: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        src_delim = "\t" if src_ext == "tsv" else ","
        dst_delim = "\t" if dst_ext == "tsv" else ","
        reader = csv.reader(io.StringIO(text), delimiter=src_delim)
        out = io.StringIO()
        writer = csv.writer(out, delimiter=dst_delim)
        count = 0
        for r in reader:
            writer.writerow(r)
            count += 1
        dst.write_text(out.getvalue(), encoding="utf-8-sig")
        return True, f"تم تحويل {count} صف بنجاح: {dst.name}"

    def _csv_to_xml(self, text: str, src_ext: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        delim = "\t" if src_ext == "tsv" else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delim)
        root = ET.Element("root")
        for row in reader:
            item = ET.SubElement(root, "row")
            for k, v in row.items():
                tag_name = "".join(c if c.isalnum() else "_" for c in str(k).strip()) or "field"
                child = ET.SubElement(item, tag_name)
                child.text = str(v)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(destination := dst), encoding="utf-8", xml_declaration=True)
        return True, f"تم تحويل CSV بنجاح إلى XML: {dst.name}"

    def _xml_to_csv(self, text: str, dst_ext: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            return False, f"خطأ في قواعد XML: {e}"

        rows = []
        keys = []
        for child in root:
            row_dict = {}
            for sub in child:
                if sub.tag not in keys:
                    keys.append(sub.tag)
                row_dict[sub.tag] = sub.text or ""
            if row_dict:
                rows.append(row_dict)

        if not rows:
            return False, "هيكل XML غير جدولي أو لا يحتوي على صفوف بيانات."

        delim = "\t" if dst_ext == "tsv" else ","
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=keys, delimiter=delim)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

        dst.write_text(out.getvalue(), encoding="utf-8-sig")
        return True, f"تم استخراج {len(rows)} صفاً إلى {dst.name}"

    def _json_to_xml(self, text: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return False, f"خطأ في JSON عند السطر {e.lineno}: {e.msg}"

        root = ET.Element("root")
        self._dict_to_xml(data, root)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(dst), encoding="utf-8", xml_declaration=True)
        return True, f"تم تحويل JSON بنجاح إلى XML: {dst.name}"

    def _dict_to_xml(self, data: Any, parent: ET.Element):
        if isinstance(data, dict):
            for k, v in data.items():
                tag = "".join(c if c.isalnum() else "_" for c in str(k)) or "item"
                child = ET.SubElement(parent, tag)
                self._dict_to_xml(v, child)
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, "element")
                self._dict_to_xml(item, child)
        else:
            parent.text = str(data)

    def _xml_to_json(self, text: str, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            return False, f"خطأ في XML: {e}"

        def xml_to_dict(elem: ET.Element):
            d = {}
            for child in elem:
                c_data = xml_to_dict(child) if len(child) else (child.text or "")
                if child.tag in d:
                    if not isinstance(d[child.tag], list):
                        d[child.tag] = [d[child.tag]]
                    d[child.tag].append(c_data)
                else:
                    d[child.tag] = c_data
            return d

        data = {root.tag: xml_to_dict(root)}
        indent = self._get_indent(opts.get("indent", "مسافتان (2 spaces)"))
        dst.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
        return True, f"تم تحويل XML بنجاح إلى JSON: {dst.name}"

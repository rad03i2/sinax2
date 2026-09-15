# -*- coding: utf-8 -*-
"""
Privacy Metadata Inspector & Sanitizer Service for SINAX Privacy & Security.
Inspects metadata in Images (EXIF, GPS), PDFs, Media, and Office docs.
Sanitizes metadata by producing verified clean copies (photo_private.jpg, doc_private.pdf).
Reuses existing SINAX ImageService, PdfService, and safe XML parsers.
"""

import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from app.services.image.image_service import ImageService
from app.services.pdf.pdf_service import PDFService


class MetadataPrivacyService:
    """Multi-format metadata inspection and privacy sanitization engine."""

    def __init__(self):
        self._image_service = ImageService()
        self._pdf_service = PDFService()

    def inspect_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts all identifiable metadata tags from the file.
        Returns: Dict containing 'format', 'has_gps', 'gps_info', 'metadata_fields', 'raw_count'
        """
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return {"error": "الملف غير موجود"}

        ext = p.suffix.lower()

        if ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff"):
            return self._inspect_image_metadata(p)
        elif ext == ".pdf":
            return self._inspect_pdf_metadata(p)
        elif ext in (".docx", ".xlsx", ".pptx"):
            return self._inspect_office_metadata(p)
        else:
            return {
                "format": "غير مدعوم مباشرة للميتاداتا",
                "has_gps": False,
                "gps_info": {},
                "metadata_fields": {},
                "raw_count": 0,
            }

    def sanitize_metadata(
        self,
        file_path: str,
        strip_gps_only: bool = False,
        custom_output_path: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Creates a new clean copy with metadata removed and VERIFIES output after generation.
        Returns: (success: bool, clean_path: str, verified_removals: Dict[str, bool])
        """
        p = Path(file_path).resolve()
        if not p.exists():
            return False, "الملف غير موجود", {}

        ext = p.suffix.lower()
        if custom_output_path:
            out_p = Path(custom_output_path).resolve()
        else:
            out_p = p.parent / f"{p.stem}_private{p.suffix}"

        # 1. Pre-inspection
        before_meta = self.inspect_metadata(str(p))

        # 2. Sanitization according to format
        try:
            if ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff"):
                action = "strip_gps" if strip_gps_only else "strip_all"
                res = self._image_service.metadata_image(p, out_p, action=action)
                if not res.get("success"):
                    return False, f"فشل تنظيف الصورة: {res.get('error')}", {}

            elif ext == ".pdf":
                # Clean PDF metadata via PdfService
                res = self._pdf_service.clean_metadata(p, out_p, title="", author="", subject="", keywords="")
                if not res.get("success"):
                    return False, f"فشل تنظيف PDF: {res.get('error')}", {}

            elif ext in (".docx", ".xlsx", ".pptx"):
                self._clean_office_metadata(p, out_p)

            else:
                # Direct copy fallback if format doesn't have metadata engine
                shutil.copy2(p, out_p)

            # 3. VERIFY AFTER SANITIZATION (Critical SINAX requirement)
            after_meta = self.inspect_metadata(str(out_p))

            verifications = {
                "gps_removed": before_meta.get("has_gps", False) and not after_meta.get("has_gps", False),
                "author_removed": "Author" in before_meta.get("metadata_fields", {}) and "Author" not in after_meta.get("metadata_fields", {}),
                "metadata_cleared": len(after_meta.get("metadata_fields", {})) < len(before_meta.get("metadata_fields", {})),
                "output_verified": out_p.exists() and out_p.stat().st_size > 0,
            }

            return True, str(out_p), verifications

        except Exception as e:
            return False, f"خطأ أثناء إنشاء النسخة المنظفة: {str(e)}", {}

    def _inspect_image_metadata(self, path: Path) -> Dict[str, Any]:
        fields = {}
        has_gps = False
        gps_info = {}

        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if exif:
                    for tag_id, val in exif.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        if tag_name == "GPSInfo":
                            has_gps = True
                            # Parse GPS coordinates
                            gps_info = self._parse_gps(val)
                        elif isinstance(val, (str, int, float)):
                            fields[tag_name] = str(val)

                    # Also check IFD for detailed camera info
                    try:
                        from PIL.ExifTags import IFD
                        exif_ifd = exif.get_ifd(IFD.Exif)
                        for k, v in exif_ifd.items():
                            name = TAGS.get(k, str(k))
                            if isinstance(v, (str, int, float)) and name not in fields:
                                fields[name] = str(v)
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "format": "صورة (Image)",
            "has_gps": has_gps,
            "gps_info": gps_info,
            "metadata_fields": fields,
            "raw_count": len(fields),
        }

    @staticmethod
    def _parse_gps(gps_dict: Any) -> Dict[str, Any]:
        result = {}
        if not isinstance(gps_dict, dict):
            return result
        try:
            for k, v in gps_dict.items():
                name = GPSTAGS.get(k, str(k))
                result[name] = str(v)
        except Exception:
            pass
        return result

    def _inspect_pdf_metadata(self, path: Path) -> Dict[str, Any]:
        stats = self._pdf_service.analyze_pdf(path)
        meta = stats.get("metadata", {})
        cleaned_meta = {}
        for k, v in meta.items():
            if v and str(v).strip():
                # Strip leading slash if any
                clean_k = k[1:] if k.startswith("/") else k
                cleaned_meta[clean_k] = str(v)

        return {
            "format": "مستند PDF",
            "has_gps": False,
            "gps_info": {},
            "metadata_fields": cleaned_meta,
            "raw_count": len(cleaned_meta),
        }

    @staticmethod
    def _inspect_office_metadata(path: Path) -> Dict[str, Any]:
        fields = {}
        try:
            with zipfile.ZipFile(path, "r") as z:
                if "docProps/core.xml" in z.namelist():
                    core_xml = z.read("docProps/core.xml")
                    root = ET.fromstring(core_xml)
                    for child in root:
                        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        if child.text and child.text.strip():
                            fields[tag] = child.text.strip()
        except Exception:
            pass

        return {
            "format": "مستند Office",
            "has_gps": False,
            "gps_info": {},
            "metadata_fields": fields,
            "raw_count": len(fields),
        }

    @staticmethod
    def _clean_office_metadata(src: Path, dest: Path):
        """Cleans docProps/core.xml and docProps/app.xml inside Office OpenXML zip files."""
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in ("docProps/core.xml", "docProps/app.xml"):
                    # Replace with sanitized minimal stub
                    stub = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"></cp:coreProperties>'
                    zout.writestr(item.filename, stub)
                else:
                    zout.writestr(item, zin.read(item.filename))

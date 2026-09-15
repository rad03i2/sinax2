# -*- coding: utf-8 -*-
"""
SINAX PDF Converter
Supports PDF <-> TXT, PDF <-> HTML, PDF <-> Word.
Uses native Qt printToPdf for 100% offline generation with full Arabic RTL support.
Extracts text via pypdf with scanned document OCR alert.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import pypdf
import docx

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("pdf_converter")


class PdfConverter(BaseConverter):
    converter_id = "pdf_converter"
    name_ar = "محول ملفات PDF"
    category = "pdf"
    required_tools = []

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "page_range": {
                "type": "text",
                "default": "all",
                "label": "نطاق الصفحات (مثال: all أو 1-5 أو 1,3,7)"
            },
            "font_size": {
                "type": "int",
                "min": 8,
                "max": 32,
                "default": 13,
                "label": "حجم الخط عند توليد PDF"
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
            progress_callback(10.0, f"معالجة ملف PDF: {source.name}")

        try:
            # 1. PDF -> TXT
            if src_ext == "pdf" and dst_ext == "txt":
                return self._pdf_to_txt(source, destination, options, progress_callback, cancel_token)

            # 2. TXT -> PDF
            if src_ext == "txt" and dst_ext == "pdf":
                return self._txt_to_pdf(source, destination, options, progress_callback, cancel_token)

            # 3. PDF -> HTML
            if src_ext == "pdf" and dst_ext == "html":
                return self._pdf_to_html(source, destination, options, progress_callback, cancel_token)

            # 4. HTML -> PDF
            if src_ext == "html" and dst_ext == "pdf":
                return self._html_to_pdf(source, destination, options, progress_callback, cancel_token)

            # 5. PDF -> DOCX
            if src_ext == "pdf" and dst_ext == "docx":
                return self._pdf_to_docx(source, destination, options, progress_callback, cancel_token)

            # 6. DOCX -> PDF
            if src_ext == "docx" and dst_ext == "pdf":
                return self._docx_to_pdf(source, destination, options, progress_callback, cancel_token)

            return False, f"تحويل PDF غير مدعوم للصيغ: {src_ext} -> {dst_ext}"

        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return False, f"فشل تحويل PDF: {str(e)}"

    def _parse_page_range(self, range_str: str, total_pages: int) -> List[int]:
        if not range_str or range_str.strip().lower() == "all":
            return list(range(total_pages))

        pages = set()
        parts = [p.strip() for p in range_str.split(",") if p.strip()]
        for part in parts:
            if "-" in part:
                try:
                    s, e = part.split("-", 1)
                    start = max(1, int(s.strip()))
                    end = min(total_pages, int(e.strip()))
                    for i in range(start, end + 1):
                        pages.add(i - 1)
                except Exception:
                    pass
            elif part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < total_pages:
                    pages.add(idx)

        res = sorted(list(pages))
        return res if res else list(range(total_pages))

    def _pdf_to_txt(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        reader = pypdf.PdfReader(str(source))
        total = len(reader.pages)
        pages_to_extract = self._parse_page_range(options.get("page_range", "all"), total)

        extracted_text = []
        for idx, page_num in enumerate(pages_to_extract):
            if cancel_token and cancel_token():
                return False, "تم إلغاء العملية."
            p = reader.pages[page_num]
            txt = p.extract_text() or ""
            extracted_text.append(f"--- [صفحة {page_num + 1}] ---\n" + txt)

        full_result = "\n\n".join(extracted_text)

        # Scanned PDF check: if very little text is extracted
        raw_chars = "".join(c for c in full_result if c.isalnum())
        warning = ""
        if len(raw_chars) < 20:
            warning = "\n(تنبيه: يبدو أن هذا الملف ممسوح ضوئياً Scanned ولا يحتوي على طبقة نصوص Text Layer)."

        destination.write_text(full_result, encoding="utf-8")
        return True, f"تم استخراج نصوص {len(pages_to_extract)} صفحة بنجاح إلى: {destination.name}{warning}"

    def _txt_to_pdf(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        from PySide6.QtGui import QTextDocument, QFont, QPdfWriter, QPageSize
        text = source.read_text(encoding="utf-8", errors="replace")

        doc = QTextDocument()
        font_size = int(options.get("font_size", 13))
        font = QFont("Segoe UI", font_size)
        doc.setDefaultFont(font)
        doc.setPlainText(text)

        # Native Qt offline vector PDF generation
        writer = QPdfWriter(str(destination))
        writer.setPageSize(QPageSize(QPageSize.A4))
        doc.print_(writer)

        if destination.exists() and destination.stat().st_size > 0:
            return True, f"تم توليد ملف PDF بنجاح: {destination.name}"
        return False, "فشل إنشاء ملف PDF."

    def _pdf_to_html(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        reader = pypdf.PdfReader(str(source))
        total = len(reader.pages)
        pages_to_extract = self._parse_page_range(options.get("page_range", "all"), total)

        html_parts = []
        for page_num in pages_to_extract:
            p = reader.pages[page_num]
            txt = p.extract_text() or ""
            para_html = "".join(f"<p>{line}</p>" for line in txt.split("\n") if line.strip())
            html_parts.append(f'<div class="pdf-page"><h3>صفحة {page_num + 1}</h3>{para_html}</div><hr/>')

        content = "\n".join(html_parts)
        full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>{source.stem}</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; line-height: 1.6; max-width: 860px; margin: 30px auto; padding: 20px; direction: rtl; color: #222; }}
.pdf-page {{ margin-bottom: 30px; background: #fff; padding: 20px; border: 1px solid #eee; border-radius: 6px; }}
h3 {{ color: #0078D4; margin-top: 0; }}
</style>
</head>
<body>
{content}
</body>
</html>"""
        destination.write_text(full_html, encoding="utf-8")
        return True, f"تم تحويل PDF إلى HTML بنجاح: {destination.name}"

    def _html_to_pdf(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        from PySide6.QtGui import QTextDocument
        raw_html = source.read_text(encoding="utf-8", errors="replace")

        doc = QTextDocument()
        doc.setHtml(raw_html)
        doc.printToPdf(str(destination))

        if destination.exists() and destination.stat().st_size > 0:
            return True, f"تم تحويل HTML إلى PDF بنجاح: {destination.name}"
        return False, "فشل إنشاء ملف PDF من HTML."

    def _pdf_to_docx(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        # 1. Try LibreOffice if available
        if dependency_manager.is_tool_available("soffice"):
            import subprocess
            soffice_path = dependency_manager.get_tool_path("soffice")
            cmd = [str(soffice_path), "--headless", "--convert-to", "docx", "--outdir", str(destination.parent), str(source)]
            subprocess.run(cmd, capture_output=True, timeout=60)
            expected = destination.parent / f"{source.stem}.docx"
            if expected.exists():
                if expected != destination:
                    expected.replace(destination)
                return True, f"تم تحويل PDF إلى DOCX بنجاح: {destination.name}"

        # 2. Native pypdf text-to-docx extraction
        reader = pypdf.PdfReader(str(source))
        doc = docx.Document()
        doc.add_heading(source.stem, level=1)

        total = len(reader.pages)
        pages_to_extract = self._parse_page_range(options.get("page_range", "all"), total)
        for page_num in pages_to_extract:
            txt = reader.pages[page_num].extract_text() or ""
            for line in txt.split("\n"):
                if line.strip():
                    doc.add_paragraph(line.strip())

        doc.save(destination)
        return True, f"تم استخراج نصوص PDF إلى مستند Word: {destination.name}"

    def _docx_to_pdf(
        self,
        source: Path,
        destination: Path,
        options: dict,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        # 1. Try LibreOffice for full layout fidelity
        if dependency_manager.is_tool_available("soffice"):
            import subprocess
            soffice_path = dependency_manager.get_tool_path("soffice")
            cmd = [str(soffice_path), "--headless", "--convert-to", "pdf", "--outdir", str(destination.parent), str(source)]
            subprocess.run(cmd, capture_output=True, timeout=60)
            expected = destination.parent / f"{source.stem}.pdf"
            if expected.exists():
                if expected != destination:
                    expected.replace(destination)
                return True, f"تم تحويل Word إلى PDF بنجاح: {destination.name}"

        # 2. Native QTextDocument text rendering fallback
        from PySide6.QtGui import QTextDocument, QFont
        doc = docx.Document(source)
        full_text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

        qdoc = QTextDocument()
        qdoc.setDefaultFont(QFont("Segoe UI", 12))
        qdoc.setPlainText(full_text)
        qdoc.printToPdf(str(destination))

        if destination.exists() and destination.stat().st_size > 0:
            return True, f"تم توليد PDF بنجاح من مستند Word: {destination.name} (قد تختلف بعض التنسيقات المتقدمة)"
        return False, "تعذر تحويل DOCX إلى PDF."

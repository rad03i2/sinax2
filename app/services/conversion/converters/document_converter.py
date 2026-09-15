# -*- coding: utf-8 -*-
"""
SINAX Document Converter
Handles text, word processing, and markup formats:
Markdown (MD), HTML, DOCX, ODT, RTF, TXT.
Uses Python libraries (markdown, python-docx) natively with LibreOffice/Pandoc fallbacks.
"""

import re
import html
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import docx

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("document_converter")


class DocumentConverter(BaseConverter):
    converter_id = "document_converter"
    name_ar = "محول المستندات والنصوص"
    category = "documents"
    required_tools = []

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "encoding": {
                "type": "select",
                "options": ["UTF-8", "UTF-8 مع BOM", "Windows-1256 (عربي)"],
                "default": "UTF-8",
                "label": "ترميز النصوص الناتجة"
            },
            "html_styling": {
                "type": "select",
                "options": ["تنسيق حديث وأنيق (Modern CSS)", "صفحة بسيطة بدون أنماط (Clean Minimal)"],
                "default": "تنسيق حديث وأنيق (Modern CSS)",
                "label": "تنسيق صفحات HTML"
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
            progress_callback(10.0, f"قراءة المستند: {source.name}")

        try:
            # 1. Markdown <-> HTML
            if src_ext in ["md", "markdown"] and dst_ext == "html":
                return self._md_to_html(source, destination, options, progress_callback)
            if src_ext == "html" and dst_ext in ["md", "markdown"]:
                return self._html_to_md(source, destination, options, progress_callback)

            # 2. DOCX <-> TXT
            if src_ext == "docx" and dst_ext == "txt":
                return self._docx_to_txt(source, destination, options, progress_callback)
            if src_ext == "txt" and dst_ext == "docx":
                return self._txt_to_docx(source, destination, options, progress_callback)

            # 3. DOCX <-> HTML
            if src_ext == "docx" and dst_ext == "html":
                return self._docx_to_html(source, destination, options, progress_callback)
            if src_ext == "html" and dst_ext == "docx":
                return self._html_to_docx(source, destination, options, progress_callback)

            # 4. Formats requiring LibreOffice / Pandoc (ODT, RTF, MD <-> DOCX)
            if any(ext in ["odt", "rtf"] for ext in [src_ext, dst_ext]) or (src_ext in ["md", "markdown"] and dst_ext == "docx"):
                return self._convert_via_external(source, destination, progress_callback, cancel_token)

            return False, f"زوج تحويل المستندات غير مدعوم: {src_ext} -> {dst_ext}"

        except Exception as e:
            logger.error(f"Document conversion failed: {e}")
            return False, f"فشل تحويل المستند: {str(e)}"

    def _md_to_html(self, src: Path, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        import markdown
        text = src.read_text(encoding="utf-8", errors="replace")
        html_body = markdown.markdown(text, extensions=['extra', 'tables', 'fenced_code', 'nl2br'])

        style_opt = opts.get("html_styling", "تنسيق حديث وأنيق (Modern CSS)")
        if "حديث" in style_opt:
            css = """
            body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; line-height: 1.6; max-width: 860px; margin: 40px auto; padding: 0 20px; color: #222; direction: rtl; }
            h1, h2, h3 { color: #0078D4; }
            pre, code { background: #f4f4f4; padding: 4px 8px; border-radius: 4px; font-family: Consolas, monospace; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: right; }
            th { background-color: #f8f9fa; }
            blockquote { border-right: 4px solid #0078D4; margin: 0; padding: 0 16px; color: #666; }
            """
        else:
            css = "body { font-family: sans-serif; direction: rtl; padding: 20px; }"

        full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{src.stem}</title>
<style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""
        dst.write_text(full_html, encoding="utf-8")
        return True, f"تم إنشاء صفحة HTML بنجاح: {dst.name}"

    def _html_to_md(self, src: Path, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        raw = src.read_text(encoding="utf-8", errors="replace")
        # Strip scripts and styles
        raw = re.sub(r'<script.*?</script>', '', raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r'<style.*?</style>', '', raw, flags=re.DOTALL | re.IGNORECASE)

        # Convert simple tags
        md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \g<1>\n\n', raw, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \g<1>\n\n', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \g<1>\n\n', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<p[^>]*>(.*?)</p>', r'\g<1>\n\n', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<b[^>]*>(.*?)</b>', r'**\g<1>**', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\g<1>**', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<i[^>]*>(.*?)</i>', r'*\g<1>*', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<em[^>]*>(.*?)</em>', r'*\g<1>*', md, flags=re.DOTALL | re.IGNORECASE)
        md = re.sub(r'<br\s*/?>', '\n', md, flags=re.IGNORECASE)
        md = re.sub(r'<li[^>]*>(.*?)</li>', r'* \g<1>\n', md, flags=re.DOTALL | re.IGNORECASE)
        # Strip all remaining tags
        md = re.sub(r'<[^>]+>', '', md)
        md = html.unescape(md)
        md = re.sub(r'\n{3,}', '\n\n', md).strip()

        dst.write_text(md, encoding="utf-8")
        return True, f"تم تحويل HTML بنجاح إلى Markdown: {dst.name}"

    def _docx_to_txt(self, src: Path, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        doc = docx.Document(src)
        lines = [p.text for p in doc.paragraphs]
        dst.write_text("\n\n".join(lines), encoding="utf-8")
        return True, f"تم استخراج نصوص Word بنجاح إلى: {dst.name}"

    def _txt_to_docx(self, src: Path, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        text = src.read_text(encoding="utf-8", errors="replace")
        doc = docx.Document()
        for block in text.split("\n\n"):
            if block.strip():
                doc.add_paragraph(block.strip())
        doc.save(dst)
        return True, f"تم إنشاء مستند Word بنجاح: {dst.name}"

    def _docx_to_html(self, src: Path, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        doc = docx.Document(src)
        body_parts = []
        for p in doc.paragraphs:
            if not p.text.strip():
                continue
            if p.style.name.startswith("Heading 1"):
                body_parts.append(f"<h1>{html.escape(p.text)}</h1>")
            elif p.style.name.startswith("Heading 2"):
                body_parts.append(f"<h2>{html.escape(p.text)}</h2>")
            elif p.style.name.startswith("Heading 3"):
                body_parts.append(f"<h3>{html.escape(p.text)}</h3>")
            else:
                body_parts.append(f"<p>{html.escape(p.text)}</p>")

        content = "\n".join(body_parts)
        full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>{src.stem}</title>
<style>body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; max-width: 800px; margin: 40px auto; padding: 20px; direction: rtl; }}</style>
</head>
<body>
{content}
</body>
</html>"""
        dst.write_text(full_html, encoding="utf-8")
        return True, f"تم تحويل مستند Word إلى HTML بنجاح: {dst.name}"

    def _html_to_docx(self, src: Path, dst: Path, opts: dict, cb: Optional[Callable]) -> Tuple[bool, str]:
        # Convert HTML to clean text blocks and write docx
        raw = src.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = html.unescape(text)
        doc = docx.Document()
        for p in text.split("\n"):
            clean_p = p.strip()
            if clean_p:
                doc.add_paragraph(clean_p)
        doc.save(dst)
        return True, f"تم تحويل صفحة HTML بنجاح إلى مستند Word: {dst.name}"

    def _convert_via_external(
        self,
        src: Path,
        dst: Path,
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        import subprocess
        # Try LibreOffice first
        if dependency_manager.is_tool_available("soffice"):
            soffice_path = dependency_manager.get_tool_path("soffice")
            target_ext = dst.suffix.lower().lstrip('.')
            cmd = [
                str(soffice_path),
                "--headless",
                "--convert-to",
                target_ext,
                "--outdir",
                str(dst.parent),
                str(src)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            expected_out = dst.parent / f"{src.stem}.{target_ext}"
            if expected_out.exists() and expected_out != dst:
                expected_out.replace(dst)
            if dst.exists():
                return True, f"تم التحويل بنجاح: {dst.name}"

        # Try Pandoc
        if dependency_manager.is_tool_available("pandoc"):
            pandoc_path = dependency_manager.get_tool_path("pandoc")
            cmd = [str(pandoc_path), "-s", str(src), "-o", str(dst)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if dst.exists():
                return True, f"تم التحويل بنجاح عبر Pandoc: {dst.name}"

        return False, "يتطلب هذا التحويل تثبيت LibreOffice أو Pandoc لإجراء التحويل المكتبي بدقة."

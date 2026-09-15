# -*- coding: utf-8 -*-
"""
SINAX Conversion Registry
Central registry managing all 50+ conversion cards, individual directions,
format querying, categorization, and search.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Type, Set
from pathlib import Path

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.services.conversion.conversion_history import ConversionHistoryManager

# Converters
from app.services.conversion.converters.image_converter import ImageConverter
from app.services.conversion.converters.data_converter import DataConverter
from app.services.conversion.converters.spreadsheet_converter import SpreadsheetConverter
from app.services.conversion.converters.document_converter import DocumentConverter
from app.services.conversion.converters.pdf_converter import PdfConverter
from app.services.conversion.converters.presentation_converter import PresentationConverter
from app.services.conversion.converters.audio_video_converter import AudioVideoConverter
from app.services.conversion.converters.ebook_converter import EbookConverter
from app.services.conversion.converters.archive_converter import ArchiveConverter


@dataclass
class ConversionDefinition:
    """Represents a single conversion direction (e.g. PDF -> DOCX)."""
    source_ext: str
    target_ext: str
    category: str
    converter_class: Type[BaseConverter]
    title_ar: str
    description_ar: str
    supports_batch: bool = True
    is_lossy_warning: Optional[str] = None

    def get_converter_instance(self) -> BaseConverter:
        return self.converter_class()

    def is_available(self) -> bool:
        return self.get_converter_instance().is_available()

    def get_missing_tools(self) -> List[str]:
        return self.get_converter_instance().get_missing_tools()


@dataclass
class ConversionCardDefinition:
    """Represents a UI card with one or two independent directions."""
    card_id: str
    title: str
    category: str
    icon_name: str
    color_hex: str
    forward_dir: ConversionDefinition
    backward_dir: Optional[ConversionDefinition] = None

    def is_available(self) -> bool:
        """Card is available if at least one of its directions is available."""
        f_ok = self.forward_dir.is_available()
        b_ok = self.backward_dir.is_available() if self.backward_dir else True
        return f_ok and b_ok

    def has_any_available(self) -> bool:
        f_ok = self.forward_dir.is_available()
        b_ok = self.backward_dir.is_available() if self.backward_dir else False
        return f_ok or b_ok

    def get_missing_tools(self) -> List[str]:
        tools = set(self.forward_dir.get_missing_tools())
        if self.backward_dir:
            tools.update(self.backward_dir.get_missing_tools())
        return list(tools)

    def is_favorite(self) -> bool:
        return ConversionHistoryManager.is_favorite(self.card_id)


class ConversionRegistry:
    """Singleton Registry managing all available conversions."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConversionRegistry, cls).__new__(cls)
            cls._instance._cards: Dict[str, ConversionCardDefinition] = {}
            cls._register_all_cards()
        return cls._instance

    @classmethod
    def _register_all_cards(cls):
        inst = cls._instance

        # ----------------------------------------------------
        # 1. PDF & DOCUMENTS (12 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="pdf_word",
            title="PDF ↔ Word",
            category="pdf",
            icon_name="file",
            color_hex="#E81123",
            f_src="pdf", f_dst="docx", f_conv=PdfConverter, f_title="PDF → DOCX",
            f_desc="تحويل ملفات PDF إلى مستندات Word قابلة للتحرير بالكامل",
            b_src="docx", b_dst="pdf", b_conv=PdfConverter, b_title="DOCX → PDF",
            b_desc="تحويل مستندات Word إلى ملفات PDF ثابتة التنسيق"
        )
        inst._add_card(
            card_id="pdf_txt",
            title="PDF ↔ TXT",
            category="pdf",
            icon_name="file",
            color_hex="#E81123",
            f_src="pdf", f_dst="txt", f_conv=PdfConverter, f_title="PDF → TXT",
            f_desc="استخراج النصوص العربية والإنجليزية من صفحات PDF بدقة Unicode",
            b_src="txt", b_dst="pdf", b_conv=PdfConverter, b_title="TXT → PDF",
            b_desc="توليد مستند PDF منظم من ملف نصي عادي"
        )
        inst._add_card(
            card_id="pdf_html",
            title="PDF ↔ HTML",
            category="pdf",
            icon_name="file",
            color_hex="#E81123",
            f_src="pdf", f_dst="html", f_conv=PdfConverter, f_title="PDF → HTML",
            f_desc="تحويل صفحات PDF إلى صفحات ويب مع الحفاظ على هيكل الفقرات",
            b_src="html", b_dst="pdf", b_conv=PdfConverter, b_title="HTML → PDF",
            b_desc="تصدير كود وصفحات HTML إلى مستند PDF عالي الجودة"
        )
        inst._add_card(
            card_id="docx_odt",
            title="DOCX ↔ ODT",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="docx", f_dst="odt", f_conv=DocumentConverter, f_title="DOCX → ODT",
            f_desc="تحويل مستند Word إلى صيغة OpenDocument Text المفتوحة",
            b_src="odt", b_dst="docx", b_conv=DocumentConverter, b_title="ODT → DOCX",
            b_desc="تحويل مستند ODT المفتوح إلى مستند Word قياسي"
        )
        inst._add_card(
            card_id="docx_rtf",
            title="DOCX ↔ RTF",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="docx", f_dst="rtf", f_conv=DocumentConverter, f_title="DOCX → RTF",
            f_desc="تحويل مستند Word إلى صيغة Rich Text Format العامة",
            b_src="rtf", b_dst="docx", b_conv=DocumentConverter, b_title="RTF → DOCX",
            b_desc="ترقية مستندات RTF القديمة إلى صيغة Word الحديثة"
        )
        inst._add_card(
            card_id="docx_txt",
            title="DOCX ↔ TXT",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="docx", f_dst="txt", f_conv=DocumentConverter, f_title="DOCX → TXT",
            f_desc="استخراج نصوص Word النصية الصافية بدون تنسيقات معقدة",
            b_src="txt", b_dst="docx", b_conv=DocumentConverter, b_title="TXT → DOCX",
            b_desc="تضمين الملفات النصية العادية داخل مستند Word منسق"
        )
        inst._add_card(
            card_id="docx_html",
            title="DOCX ↔ HTML",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="docx", f_dst="html", f_conv=DocumentConverter, f_title="DOCX → HTML",
            f_desc="نشر مستند Word كصفحة ويب منسقة بأسلوب CSS نظيف",
            b_src="html", b_dst="docx", b_conv=DocumentConverter, b_title="HTML → DOCX",
            b_desc="استيراد صفحات HTML إلى مستندات Word قابلة للتحرير"
        )
        inst._add_card(
            card_id="odt_rtf",
            title="ODT ↔ RTF",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="odt", f_dst="rtf", f_conv=DocumentConverter, f_title="ODT → RTF",
            f_desc="تحويل مستندات OpenDocument إلى صيغة النصوص المنسقة RTF",
            b_src="rtf", b_dst="odt", b_conv=DocumentConverter, b_title="RTF → ODT",
            b_desc="تحويل مستند RTF إلى مستند ODF المفتوح"
        )
        inst._add_card(
            card_id="odt_txt",
            title="ODT ↔ TXT",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="odt", f_dst="txt", f_conv=DocumentConverter, f_title="ODT → TXT",
            f_desc="استخراج النصوص الصافية من مستندات ODT",
            b_src="txt", b_dst="odt", b_conv=DocumentConverter, b_title="TXT → ODT",
            b_desc="إنشاء مستند ODT مفتوح من ملف نصي عادي"
        )
        inst._add_card(
            card_id="md_html",
            title="Markdown ↔ HTML",
            category="documents",
            icon_name="code",
            color_hex="#0078D4",
            f_src="md", f_dst="html", f_conv=DocumentConverter, f_title="MD → HTML",
            f_desc="تحويل كود Markdown التوثيقي إلى صفحة ويب عصرية بتنسيق أنيق",
            b_src="html", b_dst="md", b_conv=DocumentConverter, b_title="HTML → MD",
            b_desc="استخراج محتوى صفحات الويب وتحويله إلى كود Markdown نظيف"
        )
        inst._add_card(
            card_id="md_docx",
            title="Markdown ↔ Word",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="md", f_dst="docx", f_conv=DocumentConverter, f_title="MD → DOCX",
            f_desc="تحويل ملفات Markdown البرمجية إلى مستندات Word مكتبية",
            b_src="docx", b_dst="md", b_conv=DocumentConverter, b_title="DOCX → MD",
            b_desc="تحويل مستندات Word إلى كود Markdown نظيف للمطورين"
        )
        inst._add_card(
            card_id="md_rtf",
            title="Markdown ↔ RTF",
            category="documents",
            icon_name="document",
            color_hex="#0078D4",
            f_src="md", f_dst="rtf", f_conv=DocumentConverter, f_title="MD → RTF",
            f_desc="تحويل نصوص Markdown إلى صيغة RTF الغنية",
            b_src="rtf", b_dst="md", b_conv=DocumentConverter, b_title="RTF → MD",
            b_desc="تحويل نصوص RTF إلى كود Markdown خفيف"
        )

        # ----------------------------------------------------
        # 2. SPREADSHEETS & DATA (8 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="excel_csv",
            title="Excel ↔ CSV",
            category="spreadsheets",
            icon_name="spreadsheet",
            color_hex="#107C41",
            f_src="xlsx", f_dst="csv", f_conv=SpreadsheetConverter, f_title="XLSX → CSV",
            f_desc="تصدير أوراق العمل وجداول Excel إلى ملفات CSV المفصولة بفواصل",
            b_src="csv", b_dst="xlsx", b_conv=SpreadsheetConverter, b_title="CSV → XLSX",
            b_desc="تحويل ملفات البيانات المجدولة CSV إلى جداول Excel منسقة"
        )
        inst._add_card(
            card_id="excel_ods",
            title="Excel ↔ ODS",
            category="spreadsheets",
            icon_name="spreadsheet",
            color_hex="#107C41",
            f_src="xlsx", f_dst="ods", f_conv=SpreadsheetConverter, f_title="XLSX → ODS",
            f_desc="تحويل جداول Microsoft Excel إلى صيغة OpenDocument Spreadsheet",
            b_src="ods", b_dst="xlsx", b_conv=SpreadsheetConverter, b_title="ODS → XLSX",
            b_desc="تحويل جداول ODS الحرة إلى ملفات Excel القياسية"
        )
        inst._add_card(
            card_id="excel_tsv",
            title="Excel ↔ TSV",
            category="spreadsheets",
            icon_name="spreadsheet",
            color_hex="#107C41",
            f_src="xlsx", f_dst="tsv", f_conv=SpreadsheetConverter, f_title="XLSX → TSV",
            f_desc="تصدير جداول Excel إلى ملفات مفصولة بمسافات جدولة TSV",
            b_src="tsv", b_dst="xlsx", b_conv=SpreadsheetConverter, b_title="TSV → XLSX",
            b_desc="استيراد ملفات TSV وتحويلها إلى جدول Excel متكامل"
        )
        inst._add_card(
            card_id="csv_tsv",
            title="CSV ↔ TSV",
            category="data",
            icon_name="data",
            color_hex="#52C41A",
            f_src="csv", f_dst="tsv", f_conv=DataConverter, f_title="CSV → TSV",
            f_desc="تحويل فاصل الحقول من فواصل Comma إلى مسافات جدولة Tab",
            b_src="tsv", b_dst="csv", b_conv=DataConverter, b_title="TSV → CSV",
            b_desc="تحويل الفواصل من مسافات جدولة إلى فواصل عادية Comma"
        )
        inst._add_card(
            card_id="csv_json",
            title="CSV ↔ JSON",
            category="data",
            icon_name="data",
            color_hex="#52C41A",
            f_src="csv", f_dst="json", f_conv=DataConverter, f_title="CSV → JSON",
            f_desc="تحويل الصفوف المجدولة إلى مصفوفات وكائنات JSON برمجية",
            b_src="json", b_dst="csv", b_conv=DataConverter, b_title="JSON → CSV",
            b_desc="تحويل مصفوفات وسجلات JSON إلى جدول بيانات CSV منظم"
        )
        inst._add_card(
            card_id="csv_xml",
            title="CSV ↔ XML",
            category="data",
            icon_name="data",
            color_hex="#52C41A",
            f_src="csv", f_dst="xml", f_conv=DataConverter, f_title="CSV → XML",
            f_desc="تحويل سجلات CSV إلى بنية شجرية موسعة XML",
            b_src="xml", b_dst="csv", b_conv=DataConverter, b_title="XML → CSV",
            b_desc="استخراج الجداول المسطحة من ملفات XML المنظمة"
        )
        inst._add_card(
            card_id="json_xml",
            title="JSON ↔ XML",
            category="data",
            icon_name="data",
            color_hex="#52C41A",
            f_src="json", f_dst="xml", f_conv=DataConverter, f_title="JSON → XML",
            f_desc="تحويل بيانات JSON البرمجية إلى هيكل XML مع التحقق الصارم",
            b_src="xml", b_dst="json", b_conv=DataConverter, b_title="XML → JSON",
            b_desc="تحويل ملفات XML الشجرية إلى كائنات JSON العصرية"
        )
        inst._add_card(
            card_id="json_yaml",
            title="JSON ↔ YAML",
            category="data",
            icon_name="data",
            color_hex="#52C41A",
            f_src="json", f_dst="yaml", f_conv=DataConverter, f_title="JSON → YAML",
            f_desc="تحويل ملفات JSON إلى صيغة إعدادات YAML سهلة القراءة",
            b_src="yaml", b_dst="json", b_conv=DataConverter, b_title="YAML → JSON",
            b_desc="تحويل ملفات تكوين YAML إلى كائنات JSON قياسية"
        )

        # ----------------------------------------------------
        # 3. PRESENTATIONS (4 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="pptx_pdf",
            title="PowerPoint ↔ PDF",
            category="presentations",
            icon_name="presentation",
            color_hex="#D24726",
            f_src="pptx", f_dst="pdf", f_conv=PresentationConverter, f_title="PPTX → PDF",
            f_desc="تصدير عروض PowerPoint إلى مستند PDF عالي الوضوح للعرض والطباعة",
            b_src="pdf", b_dst="pptx", b_conv=PresentationConverter, b_title="PDF → PPTX",
            b_desc="تحويل صفحات PDF إلى شرائح عرض PowerPoint عالية الجودة"
        )
        inst._add_card(
            card_id="pptx_odp",
            title="PPTX ↔ ODP",
            category="presentations",
            icon_name="presentation",
            color_hex="#D24726",
            f_src="pptx", f_dst="odp", f_conv=PresentationConverter, f_title="PPTX → ODP",
            f_desc="تحويل عروض PowerPoint إلى صيغة OpenDocument Presentation",
            b_src="odp", b_dst="pptx", b_conv=PresentationConverter, b_title="ODP → PPTX",
            b_desc="تحويل عروض ODP المفتوحة إلى عروض PowerPoint القياسية"
        )
        inst._add_card(
            card_id="pptx_png",
            title="PowerPoint ↔ PNG",
            category="presentations",
            icon_name="presentation",
            color_hex="#D24726",
            f_src="pptx", f_dst="png", f_conv=PresentationConverter, f_title="PPTX → PNG",
            f_desc="استخراج كل شريحة في العرض التقديمي كصورة PNG مستقلة عالية الدقة",
            b_src="png", b_dst="pptx", b_conv=PresentationConverter, b_title="PNG → PPTX",
            b_desc="تجميع صور PNG في شرائح عرض PowerPoint متسلسلة"
        )
        inst._add_card(
            card_id="pptx_jpg",
            title="PowerPoint ↔ JPG",
            category="presentations",
            icon_name="presentation",
            color_hex="#D24726",
            f_src="pptx", f_dst="jpg", f_conv=PresentationConverter, f_title="PPTX → JPG",
            f_desc="تصدير شرائح العرض التقديمي كصور JPG مضغوطة وسريعة المشاركة",
            b_src="jpg", b_dst="pptx", b_conv=PresentationConverter, b_title="JPG → PPTX",
            b_desc="بناء عرض تقديمي جديد من مجموعة صور JPG"
        )

        # ----------------------------------------------------
        # 4. IMAGES (12 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="jpg_png",
            title="JPG ↔ PNG",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="jpg", f_dst="png", f_conv=ImageConverter, f_title="JPG → PNG",
            f_desc="تحويل صور JPG إلى PNG عالي الوضوح بدون ضغط فقود",
            b_src="png", b_dst="jpg", b_conv=ImageConverter, b_title="PNG → JPG",
            b_desc="تحويل PNG إلى JPG مع دعم اختيار لون خلفية الشفافية"
        )
        inst._add_card(
            card_id="jpg_webp",
            title="JPG ↔ WebP",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="jpg", f_dst="webp", f_conv=ImageConverter, f_title="JPG → WebP",
            f_desc="ضغط الصور إلى صيغة WebP العصرية لتوفير حتى 70% من المساحة",
            b_src="webp", b_dst="jpg", b_conv=ImageConverter, b_title="WebP → JPG",
            b_desc="استعادة صيغة JPG التقليدية من صور WebP للتوافق الكامل"
        )
        inst._add_card(
            card_id="jpg_avif",
            title="JPG ↔ AVIF",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="jpg", f_dst="avif", f_conv=ImageConverter, f_title="JPG → AVIF",
            f_desc="التحويل إلى صيغة AVIF فائقة الكفاءة بأحدث خوارزميات الضغط",
            b_src="avif", b_dst="jpg", b_conv=ImageConverter, b_title="AVIF → JPG",
            b_desc="تحويل صور AVIF إلى صيغة JPG الشائعة للتوافق مع البرامج"
        )
        inst._add_card(
            card_id="jpg_bmp",
            title="JPG ↔ BMP",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="jpg", f_dst="bmp", f_conv=ImageConverter, f_title="JPG → BMP",
            f_desc="تحويل صور JPG إلى صور نقطية غير مضغوطة Bitmap",
            b_src="bmp", b_dst="jpg", b_conv=ImageConverter, b_title="BMP → JPG",
            b_desc="ضغط صور BMP الضخمة إلى JPG خفيف الحجم"
        )
        inst._add_card(
            card_id="jpg_tiff",
            title="JPG ↔ TIFF",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="jpg", f_dst="tiff", f_conv=ImageConverter, f_title="JPG → TIFF",
            f_desc="تصدير الصور إلى صيغة TIFF المخصصة للطباعة ودور النشر",
            b_src="tiff", b_dst="jpg", b_conv=ImageConverter, b_title="TIFF → JPG",
            b_desc="تحويل صور TIFF الممسوحة ضوئياً إلى JPG للمعاينة السريعة"
        )
        inst._add_card(
            card_id="png_webp",
            title="PNG ↔ WebP",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="png", f_dst="webp", f_conv=ImageConverter, f_title="PNG → WebP",
            f_desc="ضغط صور PNG الشفافة إلى WebP مع الحفاظ على طبقة الشفافية Alpha",
            b_src="webp", b_dst="png", b_conv=ImageConverter, b_title="WebP → PNG",
            b_desc="استخراج صور PNG شفافة بدون أي فقدان في الجودة"
        )
        inst._add_card(
            card_id="png_avif",
            title="PNG ↔ AVIF",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="png", f_dst="avif", f_conv=ImageConverter, f_title="PNG → AVIF",
            f_desc="تحويل الرسوميات الشفافة إلى صيغة AVIF من الجيل القادم",
            b_src="avif", b_dst="png", b_conv=ImageConverter, b_title="AVIF → PNG",
            b_desc="تحويل صور AVIF إلى PNG عالي الدقة"
        )
        inst._add_card(
            card_id="png_bmp",
            title="PNG ↔ BMP",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="png", f_dst="bmp", f_conv=ImageConverter, f_title="PNG → BMP",
            f_desc="تحويل PNG إلى صورة Bitmap نقطية متوافقة مع الأنظمة القديمة",
            b_src="bmp", b_dst="png", b_conv=ImageConverter, b_title="BMP → PNG",
            b_desc="تحويل ملفات BMP إلى صور PNG مضغوطة وواضحة"
        )
        inst._add_card(
            card_id="png_tiff",
            title="PNG ↔ TIFF",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="png", f_dst="tiff", f_conv=ImageConverter, f_title="PNG → TIFF",
            f_desc="تحويل صور PNG الشفافة إلى TIFF عالي الجودة للطباعة",
            b_src="tiff", b_dst="png", b_conv=ImageConverter, b_title="TIFF → PNG",
            b_desc="استخراج صور PNG شفافة من ملفات TIFF"
        )
        inst._add_card(
            card_id="png_ico",
            title="PNG ↔ ICO",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="png", f_dst="ico", f_conv=ImageConverter, f_title="PNG → ICO",
            f_desc="إنشاء أيقونات Windows متعددة الأحجام (16x16 حتى 256x256) في ملف واحد",
            b_src="ico", b_dst="png", b_conv=ImageConverter, b_title="ICO → PNG",
            b_desc="استخراج أكبر طبقة أيقونة وحفظها كصورة PNG شفافة"
        )
        # Single Direction: SVG -> PNG
        inst._add_card_single(
            card_id="svg_png",
            title="SVG → PNG",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            src="svg", dst="png", conv=ImageConverter, title_ar="SVG → PNG",
            desc_ar="تحويل الرسوميات الشعاعية المتجهة SVG إلى صور PNG نقطية بدقة فائقة"
        )
        inst._add_card(
            card_id="heic_jpg",
            title="HEIC ↔ JPG",
            category="images",
            icon_name="image",
            color_hex="#FFB900",
            f_src="heic", f_dst="jpg", f_conv=ImageConverter, f_title="HEIC → JPG",
            f_desc="تحويل صور أجهزة آبل والآيفون HEIC إلى صيغة JPG الشائعة",
            b_src="jpg", b_dst="heic", b_conv=ImageConverter, b_title="JPG → HEIC",
            b_desc="تحويل صور JPG إلى صيغة HEIC الموفرة للمساحة"
        )

        # ----------------------------------------------------
        # 5. AUDIO (6 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="mp3_wav",
            title="MP3 ↔ WAV",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="mp3", f_dst="wav", f_conv=AudioVideoConverter, f_title="MP3 → WAV",
            f_desc="فك ضغط ملفات MP3 إلى صيغة WAV الصوتية الخام بدون ضغط",
            b_src="wav", b_dst="mp3", b_conv=AudioVideoConverter, b_title="WAV → MP3",
            b_desc="ضغط تسجيلات WAV الضخمة إلى ملفات MP3 خفيفة الوزن بجودة قابلة للضبط"
        )
        inst._add_card(
            card_id="mp3_flac",
            title="MP3 ↔ FLAC",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="mp3", f_dst="flac", f_conv=AudioVideoConverter, f_title="MP3 → FLAC",
            f_desc="التحويل إلى ترميز FLAC الصوتي عالي النقاء",
            b_src="flac", b_dst="mp3", b_conv=AudioVideoConverter, b_title="FLAC → MP3",
            b_desc="تحويل ألبومات FLAC عالية الدقة إلى MP3 للاستماع على جميع الأجهزة"
        )
        inst._add_card(
            card_id="mp3_aac",
            title="MP3 ↔ AAC",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="mp3", f_dst="aac", f_conv=AudioVideoConverter, f_title="MP3 → AAC",
            f_desc="تحويل الصوتيات إلى ترميز AAC الحديث عالي الكفاءة",
            b_src="aac", b_dst="mp3", b_conv=AudioVideoConverter, b_title="AAC → MP3",
            b_desc="تحويل صوتيات AAC إلى MP3 القياسي لتشغيلها في كل مكان"
        )
        inst._add_card(
            card_id="mp3_m4a",
            title="MP3 ↔ M4A",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="mp3", f_dst="m4a", f_conv=AudioVideoConverter, f_title="MP3 → M4A",
            f_desc="تحويل ملفات MP3 إلى صيغة M4A المفضلة في أجهزة Apple وiTunes",
            b_src="m4a", b_dst="mp3", b_conv=AudioVideoConverter, b_title="M4A → MP3",
            b_desc="تحويل تسجيلات وصوتيات M4A إلى صيغة MP3 المتوافقة عالمياً"
        )
        inst._add_card(
            card_id="mp3_ogg",
            title="MP3 ↔ OGG",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="mp3", f_dst="ogg", f_conv=AudioVideoConverter, f_title="MP3 → OGG",
            f_desc="التحويل إلى ترميز OGG Vorbis المفتوح المفضل في الألعاب والويب",
            b_src="ogg", b_dst="mp3", b_conv=AudioVideoConverter, b_title="OGG → MP3",
            b_desc="تحويل ملفات OGG الصوتية إلى MP3 سهلة المشاركة"
        )
        inst._add_card(
            card_id="mp3_opus",
            title="MP3 ↔ OPUS",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="mp3", f_dst="opus", f_conv=AudioVideoConverter, f_title="MP3 → OPUS",
            f_desc="التحويل إلى ترميز OPUS العالمي الأفضل في نقل الصوت والبودكاست",
            b_src="opus", b_dst="mp3", b_conv=AudioVideoConverter, b_title="OPUS → MP3",
            b_desc="تحويل التسجيلات الصوتية OPUS إلى MP3"
        )
        inst._add_card(
            card_id="wav_flac",
            title="WAV ↔ FLAC",
            category="audio",
            icon_name="audio",
            color_hex="#8950FC",
            f_src="wav", f_dst="flac", f_conv=AudioVideoConverter, f_title="WAV → FLAC",
            f_desc="ضغط تسجيلات WAV الخام إلى FLAC دون فقدان أي ذرة من جودة الصوت",
            b_src="flac", b_dst="wav", b_conv=AudioVideoConverter, b_title="FLAC → WAV",
            b_desc="فك ضغط ملفات FLAC إلى موجات WAV نقية للاستوديوهات"
        )

        # ----------------------------------------------------
        # 6. VIDEO & ANIMATION (8 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="mp4_mkv",
            title="MP4 ↔ MKV",
            category="video",
            icon_name="video",
            color_hex="#00B4D8",
            f_src="mp4", f_dst="mkv", f_conv=AudioVideoConverter, f_title="MP4 → MKV",
            f_desc="تضمين الفيديو في حاوية Matroska MKV القوية مع دعم مسارات الترجمة",
            b_src="mkv", b_dst="mp4", b_conv=AudioVideoConverter, b_title="MKV → MP4",
            b_desc="تحويل فيديوهات MKV إلى MP4 المتوافق مع كافة الشاشات والهواتف"
        )
        inst._add_card(
            card_id="mp4_mov",
            title="MP4 ↔ MOV",
            category="video",
            icon_name="video",
            color_hex="#00B4D8",
            f_src="mp4", f_dst="mov", f_conv=AudioVideoConverter, f_title="MP4 → MOV",
            f_desc="التحويل إلى صيغة QuickTime MOV المتوافقة مع برامج مونتاج Mac",
            b_src="mov", b_dst="mp4", b_conv=AudioVideoConverter, b_title="MOV → MP4",
            b_desc="تحويل فيديوهات كاميرات آبل والآيفون MOV إلى MP4 القياسي"
        )
        inst._add_card(
            card_id="mp4_avi",
            title="MP4 ↔ AVI",
            category="video",
            icon_name="video",
            color_hex="#00B4D8",
            f_src="mp4", f_dst="avi", f_conv=AudioVideoConverter, f_title="MP4 → AVI",
            f_desc="التحويل إلى صيغة AVI المتوافقة مع الشاشات ومشغلات السيارات القديمة",
            b_src="avi", b_dst="mp4", b_conv=AudioVideoConverter, b_title="AVI → MP4",
            b_desc="تحديث الفيديوهات القديمة AVI إلى MP4 الحديث عالي الضغط"
        )
        inst._add_card(
            card_id="mp4_webm",
            title="MP4 ↔ WebM",
            category="video",
            icon_name="video",
            color_hex="#00B4D8",
            f_src="mp4", f_dst="webm", f_conv=AudioVideoConverter, f_title="MP4 → WebM",
            f_desc="تحويل الفيديو إلى صيغة WebM بكوديك VP9 المخصصة لمتصفحات الويب",
            b_src="webm", b_dst="mp4", b_conv=AudioVideoConverter, b_title="WebM → MP4",
            b_desc="تحويل فيديوهات الويب WebM إلى MP4 لتشغيلها دون متصفح"
        )
        inst._add_card(
            card_id="mov_mkv",
            title="MOV ↔ MKV",
            category="video",
            icon_name="video",
            color_hex="#00B4D8",
            f_src="mov", f_dst="mkv", f_conv=AudioVideoConverter, f_title="MOV → MKV",
            f_desc="تغليف فيديوهات QuickTime داخل حاوية MKV المفتوحة",
            b_src="mkv", b_dst="mov", b_conv=AudioVideoConverter, b_title="MKV → MOV",
            b_desc="تحويل ملفات MKV إلى صيغة MOV المتوافقة مع برامج التحرير"
        )
        inst._add_card(
            card_id="gif_mp4",
            title="GIF ↔ MP4",
            category="video",
            icon_name="video",
            color_hex="#00B4D8",
            f_src="gif", f_dst="mp4", f_conv=AudioVideoConverter, f_title="GIF → MP4",
            f_desc="تحويل الصور المتحركة GIF الضخمة إلى فيديو MP4 سلس وصغير الحجم",
            b_src="mp4", b_dst="gif", b_conv=AudioVideoConverter, b_title="MP4 → GIF",
            b_desc="صناعة صور متحركة GIF عالية الجودة من مقاطع الفيديو مع تحكم كامل بالـ FPS"
        )
        # Audio Extraction from Video
        inst._add_card_single(
            card_id="mp4_mp3",
            title="MP4 → MP3",
            category="video",
            icon_name="audio",
            color_hex="#00B4D8",
            src="mp4", dst="mp3", conv=AudioVideoConverter, title_ar="MP4 → MP3",
            desc_ar="استخراج الصوت النقي من مقاطع الفيديو MP4 وحفظه كملف صوتي MP3"
        )
        inst._add_card_single(
            card_id="mkv_mp3",
            title="MKV → MP3",
            category="video",
            icon_name="audio",
            color_hex="#00B4D8",
            src="mkv", dst="mp3", conv=AudioVideoConverter, title_ar="MKV → MP3",
            desc_ar="استخراج المسار الصوتي من أفلام ومقاطع MKV وحفظه بصيغة MP3"
        )

        # ----------------------------------------------------
        # 7. EBOOKS & ARCHIVES (3 Cards)
        # ----------------------------------------------------
        inst._add_card(
            card_id="epub_pdf",
            title="EPUB ↔ PDF",
            category="ebooks",
            icon_name="book",
            color_hex="#9254DE",
            f_src="epub", f_dst="pdf", f_conv=EbookConverter, f_title="EPUB → PDF",
            f_desc="تحويل الكتب الإلكترونية EPUB إلى ملفات PDF جاهزة للقراءة والطباعة",
            b_src="pdf", b_dst="epub", b_conv=EbookConverter, b_title="PDF → EPUB",
            b_desc="تحويل وثائق PDF إلى كتب إلكترونية EPUB قابلة لإعادة التنسيق للقارئات"
        )
        inst._add_card(
            card_id="zip_7z",
            title="ZIP ↔ 7Z (إعادة تغليف الأرشيف)",
            category="archives",
            icon_name="archive",
            color_hex="#FA8C16",
            f_src="zip", f_dst="7z", f_conv=ArchiveConverter, f_title="ZIP → 7Z",
            f_desc="إعادة تغليف الأرشيف المضغوط إلى صيغة 7Z لتحقيق نسبة ضغط فائقة",
            b_src="7z", b_dst="zip", b_conv=ArchiveConverter, b_title="7Z → ZIP",
            b_desc="إعادة حزم أرشيفات 7Z كملفات ZIP للتوافق مع كافة أنظمة التشغيل"
        )
        inst._add_card(
            card_id="xml_yaml",
            title="XML ↔ YAML",
            category="data",
            icon_name="data",
            color_hex="#52C41A",
            f_src="xml", f_dst="yaml", f_conv=DataConverter, f_title="XML → YAML",
            f_desc="تحويل وثائق وتكوينات XML إلى صيغة YAML النظيفة",
            b_src="yaml", b_dst="xml", b_conv=DataConverter, b_title="YAML → XML",
            b_desc="تحويل ملفات تكوين YAML إلى هيكل XML القياسي"
        )

    @classmethod
    def _add_card(
        cls, card_id: str, title: str, category: str, icon_name: str, color_hex: str,
        f_src: str, f_dst: str, f_conv: Type[BaseConverter], f_title: str, f_desc: str,
        b_src: str, b_dst: str, b_conv: Type[BaseConverter], b_title: str, b_desc: str
    ):
        f_dir = ConversionDefinition(
            source_ext=f_src.lower(),
            target_ext=f_dst.lower(),
            category=category,
            converter_class=f_conv,
            title_ar=f_title,
            description_ar=f_desc
        )
        b_dir = ConversionDefinition(
            source_ext=b_src.lower(),
            target_ext=b_dst.lower(),
            category=category,
            converter_class=b_conv,
            title_ar=b_title,
            description_ar=b_desc
        )
        card = ConversionCardDefinition(
            card_id=card_id,
            title=title,
            category=category,
            icon_name=icon_name,
            color_hex=color_hex,
            forward_dir=f_dir,
            backward_dir=b_dir
        )
        cls._instance._cards[card_id] = card

    @classmethod
    def _add_card_single(
        cls, card_id: str, title: str, category: str, icon_name: str, color_hex: str,
        src: str, dst: str, conv: Type[BaseConverter], title_ar: str, desc_ar: str
    ):
        f_dir = ConversionDefinition(
            source_ext=src.lower(),
            target_ext=dst.lower(),
            category=category,
            converter_class=conv,
            title_ar=title_ar,
            description_ar=desc_ar
        )
        card = ConversionCardDefinition(
            card_id=card_id,
            title=title,
            category=category,
            icon_name=icon_name,
            color_hex=color_hex,
            forward_dir=f_dir,
            backward_dir=None
        )
        cls._instance._cards[card_id] = card

    @classmethod
    def get_all_cards(cls) -> List[ConversionCardDefinition]:
        return list(cls()._cards.values())

    @classmethod
    def get_card(cls, card_id: str) -> Optional[ConversionCardDefinition]:
        return cls()._cards.get(card_id)

    @classmethod
    def search_cards(
        cls,
        query: str = "",
        category: str = "all",
        only_favorites: bool = False,
        only_most_used: bool = False
    ) -> List[ConversionCardDefinition]:
        """Performs multi-criteria filtering across all registered cards."""
        all_cards = cls.get_all_cards()
        favs = set(ConversionHistoryManager.get_favorites())
        most_used = set(ConversionHistoryManager.get_most_used_card_ids(limit=12))

        filtered = []
        q = query.strip().lower()

        for card in all_cards:
            # 1. Favorites filter
            if only_favorites and card.card_id not in favs:
                continue

            # 2. Most used filter
            if only_most_used and card.card_id not in most_used:
                continue

            # 3. Category filter
            if category != "all":
                # Special cases
                if category == "pdf" and card.category != "pdf":
                    continue
                elif category != "pdf" and card.category != category:
                    continue

            # 4. Search text query
            if q:
                # Check formats, titles, extensions
                f_exts = f"{card.forward_dir.source_ext} {card.forward_dir.target_ext}"
                b_exts = f"{card.backward_dir.source_ext} {card.backward_dir.target_ext}" if card.backward_dir else ""
                card_text = f"{card.title} {card.forward_dir.title_ar} {card.forward_dir.description_ar} {f_exts} {b_exts}".lower()
                if q not in card_text:
                    continue

            filtered.append(card)

        return filtered

    @classmethod
    def get_all_source_formats(cls) -> List[str]:
        """Returns sorted unique list of all source extensions."""
        exts = set()
        for card in cls.get_all_cards():
            exts.add(card.forward_dir.source_ext.upper())
            if card.backward_dir:
                exts.add(card.backward_dir.source_ext.upper())
        return sorted(list(exts))

    @classmethod
    def get_targets_for_source(cls, source_ext: str) -> List[str]:
        """Returns valid target extensions for a given source extension."""
        s = source_ext.lower().lstrip('.')
        targets = set()
        for card in cls.get_all_cards():
            if card.forward_dir.source_ext == s:
                targets.add(card.forward_dir.target_ext.upper())
            if card.backward_dir and card.backward_dir.source_ext == s:
                targets.add(card.backward_dir.target_ext.upper())
        return sorted(list(targets))

    @classmethod
    def find_direction(cls, source_ext: str, target_ext: str) -> Optional[ConversionDefinition]:
        """Finds the specific conversion direction definition."""
        s = source_ext.lower().lstrip('.')
        t = target_ext.lower().lstrip('.')
        for card in cls.get_all_cards():
            if card.forward_dir.source_ext == s and card.forward_dir.target_ext == t:
                return card.forward_dir
            if card.backward_dir and card.backward_dir.source_ext == s and card.backward_dir.target_ext == t:
                return card.backward_dir
        return None

    @classmethod
    def find_matching_cards_for_file(cls, file_path: Path) -> List[ConversionCardDefinition]:
        """Smart Drop helper: returns all cards accepting this file's extension."""
        ext = file_path.suffix.lower().lstrip('.')
        matched = []
        for card in cls.get_all_cards():
            if card.forward_dir.source_ext == ext:
                matched.append(card)
            elif card.backward_dir and card.backward_dir.source_ext == ext:
                matched.append(card)
        return matched


conversion_registry = ConversionRegistry()

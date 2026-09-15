# -*- coding: utf-8 -*-
"""
SINAX PDF Tool Registry
Central data-driven registry defining all PDF tools, categories, metadata, and capability schemas.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PDFToolDefinition:
    id: str
    title_ar: str
    title_en: str
    category: str
    icon: str
    description_ar: str
    description_en: str
    status: str = "ready"               # "ready" (جاهز), "needs_dep" (يحتاج مكون), "upcoming" (قريباً)
    supports_batch: bool = True
    requires_preview: bool = True
    options_type: str = "generic"       # identifies which options panel to render
    required_engine: str = "internal"   # "internal", "tesseract", "qpdf", "ghostscript"
    tags: List[str] = field(default_factory=list)

# PDF Categories
PDF_CATEGORIES = [
    ("all", "الكل"),
    ("most_used", "الأكثر استخداماً"),
    ("pages", "تنظيم الصفحات"),
    ("compress_optimize", "الضغط والتحسين"),
    ("security_privacy", "الأمان والخصوصية"),
    ("edit_annotate", "التحرير والتنقيح"),
    ("extract", "الاستخراج"),
    ("inspect_repair", "المقارنة والفحص"),
    ("print_batch", "الطباعة والعمليات"),
]

# All Tools Catalog
PDF_TOOLS_REGISTRY: List[PDFToolDefinition] = [
    # --- 1. الأكثر استخداماً / الأدوات الأساسية ---
    PDFToolDefinition(
        id="merge",
        title_ar="دمج ملفات PDF",
        title_en="Merge PDF",
        category="most_used",
        icon="merge",
        description_ar="دمج عشرات أو مئات الملفات بترتيب مخصص ونطاقات صفحات محددة لكل ملف.",
        description_en="Combine multiple PDF files into one with custom page ranges and ordering.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="merge",
        tags=["دمج", "تجميع", "جمع", "merge", "combine"]
    ),
    PDFToolDefinition(
        id="split",
        title_ar="تقسيم PDF",
        title_en="Split PDF",
        category="most_used",
        icon="split",
        description_ar="فصل كل صفحة في ملف، أو كل X صفحات، أو تقسيم حسب نطاقات صفحات مخصصة.",
        description_en="Split PDF into individual pages, chunks, or custom ranges.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="split",
        tags=["تقسيم", "فصل", "تجزئة", "split", "divide", "صفحات"]
    ),
    PDFToolDefinition(
        id="compress",
        title_ar="ضغط وتحسين PDF",
        title_en="Compress PDF",
        category="most_used",
        icon="compress",
        description_ar="تقليل حجم الملف عبر 4 مستويات متقدمة، أو تحديد حجم مستهدف بالميجابايت.",
        description_en="Reduce PDF file size using 4 optimization presets or a target MB size.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="compress",
        tags=["ضغط", "تصغير", "حجم", "compress", "reduce", "optimize"]
    ),
    PDFToolDefinition(
        id="extract_pages",
        title_ar="استخراج صفحات محددة",
        title_en="Extract Pages",
        category="most_used",
        icon="extract",
        description_ar="استخراج صفحات معينة وحفظها في مستند PDF جديد ومستقل بنقرة واحدة.",
        description_en="Extract specific pages into a new clean PDF file.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="extract_pages",
        tags=["استخراج", "صفحات", "extract", "pages"]
    ),
    PDFToolDefinition(
        id="delete_pages",
        title_ar="حذف صفحات من PDF",
        title_en="Delete Pages",
        category="most_used",
        icon="trash",
        description_ar="حذف صفحات فردية أو زوجية أو نطاق محدد ومعاينة المستند قبل التطبيق.",
        description_en="Delete selected, odd, even, or range pages from PDF.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="delete_pages",
        tags=["حذف", "إزالة", "delete", "remove", "صفحات"]
    ),
    PDFToolDefinition(
        id="pdf_to_images",
        title_ar="تحويل PDF إلى صور",
        title_en="PDF to Images",
        category="most_used",
        icon="image",
        description_ar="تصدير كل صفحة أو صفحات محددة إلى صور عالية الدقة (PNG, JPG, WebP, TIFF).",
        description_en="Export PDF pages to high-resolution PNG, JPG, WebP, or TIFF images.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="pdf_to_images",
        tags=["صور", "تحويل", "jpg", "png", "images", "export"]
    ),
    PDFToolDefinition(
        id="images_to_pdf",
        title_ar="تجميع الصور في PDF",
        title_en="Images to PDF",
        category="most_used",
        icon="pdf",
        description_ar="دمج مئات الصور بترتيب مخصص وهوامش وأحجام ورق متعددة (A4, Letter) في PDF.",
        description_en="Convert and combine multiple images into a single professional PDF.",
        status="ready",
        supports_batch=True,
        requires_preview=False,
        options_type="images_to_pdf",
        tags=["صور", "تجميع", "pdf", "photos", "album"]
    ),
    PDFToolDefinition(
        id="page_numbers",
        title_ar="ترقيم الصفحات و Bates",
        title_en="Page Numbers & Bates",
        category="most_used",
        icon="number",
        description_ar="إضافة أرقام الصفحات بـ 6 مواضع وأنماط مخصصة (صفحة X من Y) وبادئات Bates.",
        description_en="Add flexible page numbers and legal Bates numbering to pages.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="page_numbers",
        tags=["ترقيم", "أرقام", "bates", "صفحات", "numbers"]
    ),
    PDFToolDefinition(
        id="watermark",
        title_ar="إضافة علامة مائية",
        title_en="Add Watermark",
        category="most_used",
        icon="watermark",
        description_ar="وضع علامة مائية نصية مخصصة بالزاوية والشفافية أو وضع شعار صورة PNG.",
        description_en="Stamp text or image watermark with custom angle, opacity and position.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="watermark",
        tags=["علامة مائية", "شعار", "ختم", "watermark", "stamp"]
    ),
    PDFToolDefinition(
        id="protect",
        title_ar="حماية وتشفير PDF",
        title_en="Protect & Encrypt",
        category="most_used",
        icon="lock",
        description_ar="تشفير الملف بكلمة مرور حديثة (AES-256) وقفل صلاحيات النسخ والطباعة.",
        description_en="Encrypt PDF with modern password protection and permission limits.",
        status="ready",
        supports_batch=True,
        requires_preview=False,
        options_type="protect",
        tags=["حماية", "تشفير", "كلمة مرور", "قفل", "protect", "encrypt", "password"]
    ),
    PDFToolDefinition(
        id="unlock",
        title_ar="فك حماية PDF بكلمة مرور",
        title_en="Unlock PDF",
        category="most_used",
        icon="unlock",
        description_ar="إزالة التشفير وحفظ نسخة مفتوحة عند تقديم كلمة المرور الصحيحة للمستند.",
        description_en="Remove PDF password and restrictions using the valid password.",
        status="ready",
        supports_batch=True,
        requires_preview=False,
        options_type="unlock",
        tags=["فك قفل", "إزالة كلمة المرور", "unlock", "decrypt"]
    ),

    # --- 2. تنظيم الصفحات والقص ---
    PDFToolDefinition(
        id="reorder",
        title_ar="إعادة ترتيب الصفحات",
        title_en="Reorder Pages",
        category="pages",
        icon="reorder",
        description_ar="تنظيم الصفحات بالسحب والإفلات وتغيير تسلسل الصفحات بدقة وسهولة.",
        description_en="Organize and reorder pages visually with thumbnail preview.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="reorder",
        tags=["ترتيب", "تنظيم", "reorder", "organize", "صفحات"]
    ),
    PDFToolDefinition(
        id="rotate",
        title_ar="تدوير الصفحات",
        title_en="Rotate Pages",
        category="pages",
        icon="rotate",
        description_ar="تدوير الصفحات 90° يميناً أو يساراً أو 180° لصفحات محددة أو كافة المستند.",
        description_en="Rotate pages 90 or 180 degrees permanently.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="rotate",
        tags=["تدوير", "قلب", "rotate", "orientation", "صفحات"]
    ),
    PDFToolDefinition(
        id="crop",
        title_ar="قص صفحات PDF",
        title_en="Crop Pages",
        category="pages",
        icon="crop",
        description_ar="اقتصاص الهوامش الزائدة أو تحديد مستطيل مخصص للمحتوى المرئي.",
        description_en="Crop margins or custom visible area from PDF pages.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="crop",
        tags=["قص", "اقتصاص", "crop", "margins", "صفحات"]
    ),
    PDFToolDefinition(
        id="halve_pages",
        title_ar="شق الصفحات إلى نصفين",
        title_en="Halve Pages (Split 2-in-1)",
        category="pages",
        icon="split",
        description_ar="مفيد للكتب والوثائق الممسوحة ضوئياً (صفحتين في ورقة واحدة) لفصلها عمودياً.",
        description_en="Split dual-page scanned documents into individual clean pages.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="halve_pages",
        tags=["شق", "نصفين", "كتاب", "halve", "dual"]
    ),
    PDFToolDefinition(
        id="add_margins",
        title_ar="إضافة وتعديل الهوامش",
        title_en="Add Margins",
        category="pages",
        icon="margin",
        description_ar="إضافة مساحات بيضاء علوية أو سفلية أو جانبية لتسهيل الطباعة والتجليد.",
        description_en="Add extra binding margins to top, bottom, left or right.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="margins",
        tags=["هوامش", "تجليد", "margins", "padding"]
    ),

    # --- 3. الضغط والتحسين المتقدم ---
    PDFToolDefinition(
        id="compress_target",
        title_ar="ضغط لحجم مستهدف محدد",
        title_en="Compress to Target Size",
        category="compress_optimize",
        icon="compress",
        description_ar="خوارزمية ذكية تكرارية لتحقيق حجم مستهدف (مثل أقل من 2 MB) بأعلى جودة.",
        description_en="Iterative compression to reach an exact maximum target file size.",
        status="ready",
        supports_batch=True,
        requires_preview=False,
        options_type="compress_target",
        tags=["حجم مستهدف", "ميجا", "target size", "mb", "ضغط"]
    ),
    PDFToolDefinition(
        id="grayscale",
        title_ar="تحويل إلى أبيض وأسود / رمادي",
        title_en="Convert to Grayscale",
        category="compress_optimize",
        icon="convert",
        description_ar="إزالة الألوان وتحويل المستند إلى درجات الرمادي لتقليل الحجم وتسريع الطباعة.",
        description_en="Convert color documents to monochrome or grayscale for size reduction.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="grayscale",
        tags=["رمادي", "أبيض وأسود", "grayscale", "monochrome"]
    ),
    PDFToolDefinition(
        id="flatten",
        title_ar="تسطيح PDF (Flatten)",
        title_en="Flatten PDF",
        category="compress_optimize",
        icon="flatten",
        description_ar="تثبيت النماذج القابلة للتحرير والتعليقات في محتوى ثابت لا يمكن تعديله.",
        description_en="Flatten interactive form fields and annotations into static graphics.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="flatten",
        tags=["تسطيح", "تثبيت", "flatten", "forms"]
    ),

    # --- 4. الأمان والخصوصية والتنقيح ---
    PDFToolDefinition(
        id="redact",
        title_ar="تنقيح حقيقي للبيانات الحساسة",
        title_en="True Redaction",
        category="security_privacy",
        icon="redact",
        description_ar="حذف حقيقي ودائم للنصوص الحساسة وأرقام الهواتف والبيانات السرية من الكود.",
        description_en="Permanently erase sensitive texts and pixels from the document.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="redact",
        tags=["تنقيح", "حجب", "سري", "redact", "erase", "privacy"]
    ),
    PDFToolDefinition(
        id="metadata",
        title_ar="فحص وتعديل وحذف Metadata",
        title_en="Edit & Clean Metadata",
        category="security_privacy",
        icon="info",
        description_ar="استعراض وتعديل العنوان والمؤلف أو حذف كافة البيانات الوصفية لحماية الخصوصية.",
        description_en="View, modify, or strip hidden metadata and author traces.",
        status="ready",
        supports_batch=True,
        requires_preview=False,
        options_type="metadata",
        tags=["ميتاداتا", "بيانات وصفية", "مؤلف", "metadata", "author"]
    ),

    # --- 5. الاستخراج والمحتوى ---
    PDFToolDefinition(
        id="extract_text",
        title_ar="استخراج النصوص كاملة",
        title_en="Extract Text to TXT",
        category="extract",
        icon="text",
        description_ar="استخراج النصوص العربية والإنجليزية من الصفحات وحفظها في ملف نصي UTF-8.",
        description_en="Extract all raw text content from PDF pages into a text file.",
        status="ready",
        supports_batch=True,
        requires_preview=True,
        options_type="extract_text",
        tags=["نصوص", "استخراج", "text", "txt"]
    ),
    PDFToolDefinition(
        id="extract_images",
        title_ar="استخراج جميع الصور الأصلية",
        title_en="Extract Embedded Images",
        category="extract",
        icon="image",
        description_ar="استخراج كافة الصور المخزنة داخل الـ PDF وحفظها بجودتها الأصلية بدون ضغط.",
        description_en="Extract all embedded original images into a separate folder.",
        status="ready",
        supports_batch=True,
        requires_preview=False,
        options_type="extract_images",
        tags=["صور", "استخراج", "images", "extract", "embedded"]
    ),

    # --- 6. المقارنة والفحص والإصلاح ---
    PDFToolDefinition(
        id="pdf_doctor",
        title_ar="طبيب وفاحص ملفات PDF",
        title_en="PDF Quick Doctor & Stats",
        category="inspect_repair",
        icon="check",
        description_ar="فحص شامل لسلامة الهيكل، عدد الصفحات، الخطوط، الصور، التشفير، وإصلاح الأخطاء.",
        description_en="Inspect structural integrity, fonts, encryption, and repair broken XREFs.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="doctor",
        tags=["فحص", "إصلاح", "طبيب", "doctor", "inspect", "repair", "health"]
    ),
    PDFToolDefinition(
        id="compare_pdfs",
        title_ar="مقارنة ملفين جنباً إلى جنب",
        title_en="Compare Two PDFs",
        category="inspect_repair",
        icon="compare",
        description_ar="مقارنة مستندين صفحة بصفحة واكتشاف التعديلات والفروقات البصرية والنصية.",
        description_en="Compare two documents side-by-side to highlight page and text differences.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="compare",
        tags=["مقارنة", "فرق", "اختلاف", "compare", "diff"]
    ),

    # --- 7. الطباعة والعمليات ---
    PDFToolDefinition(
        id="print_pdf",
        title_ar="طباعة PDF ومعاينة الطباعة",
        title_en="Print PDF & Preview",
        category="print_batch",
        icon="print",
        description_ar="نافذة طباعة ويندوز مدمجة مع معاينة الصفحات الفردية/الزوجية والنطاقات والاتجاه.",
        description_en="Integrated print preview with page selection, orientation, and copies.",
        status="ready",
        supports_batch=False,
        requires_preview=True,
        options_type="print",
        tags=["طباعة", "طابعة", "معاينة", "print", "preview"]
    ),
    PDFToolDefinition(
        id="ocr_searchable",
        title_ar="التعرف الضوئي OCR (نص قابل للبحث)",
        title_en="OCR to Searchable PDF",
        category="most_used",
        icon="ocr",
        description_ar="تحويل المستندات الممسوحة ضوئياً إلى نصوص قابلة للبحث والنسخ (يتطلب Tesseract).",
        description_en="Convert scanned PDFs into searchable text documents via OCR.",
        status="needs_dep",
        supports_batch=True,
        requires_preview=True,
        options_type="ocr",
        required_engine="tesseract",
        tags=["ocr", "مسح", "تعرف", "بحث", "tesseract"]
    ),
]

def get_tool_by_id(tool_id: str) -> Optional[PDFToolDefinition]:
    """Returns the tool definition by ID, or None if not found."""
    for tool in PDF_TOOLS_REGISTRY:
        if tool.id == tool_id:
            return tool
    return None

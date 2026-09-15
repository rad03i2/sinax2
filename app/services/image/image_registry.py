# -*- coding: utf-8 -*-
"""
SINAX Image Center Registry
Data-driven registry defining all image processing tools, categories,
supported options schemas, and operational badges.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


IMAGE_CATEGORIES = [
    {"id": "all", "name_ar": "الكل", "icon": "image"},
    {"id": "popular", "name_ar": "الأكثر استخداماً", "icon": "popular"},
    {"id": "batch", "name_ar": "المعالجة الجماعية", "icon": "batch"},
    {"id": "compress", "name_ar": "الضغط", "icon": "compress"},
    {"id": "resize", "name_ar": "تغيير الحجم", "icon": "resize"},
    {"id": "convert", "name_ar": "التحويل", "icon": "convert"},
    {"id": "edit", "name_ar": "القص والتدوير", "icon": "crop"},
    {"id": "enhance", "name_ar": "التحسين والفلاتر", "icon": "wand"},
    {"id": "privacy", "name_ar": "الخصوصية والميتاداتا", "icon": "lock"},
    {"id": "advanced", "name_ar": "أدوات متقدمة", "icon": "settings"},
    {"id": "workflow", "name_ar": "سير العمل (Workflows)", "icon": "workflow"},
    {"id": "favorites", "name_ar": "المفضلة", "icon": "star"},
]


@dataclass
class ImageToolDefinition:
    id: str
    title_ar: str
    title_en: str
    description_ar: str
    category: str
    icon: str
    supports_batch: bool = True
    badge: str = "جاهز للاستخدام"
    options_type: str = "compress"
    tags: List[str] = field(default_factory=list)


IMAGE_TOOLS_REGISTRY: List[ImageToolDefinition] = [
    # 1. Compression
    ImageToolDefinition(
        id="batch_compress",
        title_ar="ضغط الصور الجماعي",
        title_en="Batch Compress",
        description_ar="ضغط مئات أو آلاف الصور بذكاء مع تقليل الحجم والحفاظ على دقة الألوان وتفاصيل الصورة.",
        category="compress",
        icon="compress",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="compress",
        tags=["ضغط", "حجم", "توفير", "مساحة", "تخفيض", "batch", "compress", "reduce"]
    ),
    ImageToolDefinition(
        id="target_size_compress",
        title_ar="الضغط إلى حجم مستهدف",
        title_en="Target Size Optimizer",
        description_ar="تحديد سقف حجم أقصى (مثل أقل من 500 KB أو 1 MB) وتحسين جودة كل صورة للوصول لأفضل نتيجة تحته.",
        category="compress",
        icon="compress",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="target_size",
        tags=["حجم مستهدف", "كيلوبايت", "ميجابايت", "target size", "kb", "mb", "limit"]
    ),

    # 2. Resize
    ImageToolDefinition(
        id="batch_resize",
        title_ar="تغيير الأبعاد الجماعي",
        title_en="Batch Resize",
        description_ar="تغيير أبعاد آلاف الصور بالبكسل، النسبة المئوية، أطول ضلع، أو وفق أوضاع Fit وFill وStretch مع عدم التكبير.",
        category="resize",
        icon="resize",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="resize",
        tags=["أبعاد", "حجم", "بكسل", "نسبة", "resize", "scale", "dimensions", "fit", "fill"]
    ),
    ImageToolDefinition(
        id="social_resize",
        title_ar="تجهيز الصور للسوشيال ميديا",
        title_en="Social Media Presets",
        description_ar="قوالب جاهزة بأبعاد دقيقة لـ Instagram (مربع، طولي)، وفيسبوك، ويوتيوب، وتويتر، وستوري.",
        category="resize",
        icon="resize",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="social_presets",
        tags=["سوشيال", "انستغرام", "فيسبوك", "يوتيوب", "ستوري", "social", "instagram", "story"]
    ),

    # 3. Format Conversion
    ImageToolDefinition(
        id="batch_convert",
        title_ar="تحويل صيغ الصور الشامل",
        title_en="Format Converter",
        description_ar="تحويل جماعي بين JPG, PNG, WebP, AVIF, BMP, TIFF, GIF, ICO و HEIC الصادرة من الآيفون.",
        category="convert",
        icon="convert",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="convert",
        tags=["تحويل", "صيغة", "webp", "heic", "avif", "png", "jpg", "convert", "format"]
    ),
    ImageToolDefinition(
        id="heic_to_jpg",
        title_ar="تحويل صور آيفون HEIC إلى JPG",
        title_en="HEIC to JPG/PNG",
        description_ar="تحويل فوري فائق السرعة لصور iPhone و iPad الحديثة إلى صيغة JPG المتوافقة عالمياً.",
        category="convert",
        icon="convert",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="heic_quick",
        tags=["ايفون", "heic", "heif", "apple", "iphone", "jpg", "photos"]
    ),

    # 4. Crop & Orientation
    ImageToolDefinition(
        id="batch_crop",
        title_ar="القص الجماعي والنسب الثابتة",
        title_en="Batch Crop",
        description_ar="قص الصور بنسب أبعاد ثابتة (1:1، 16:9، 4:3، إلخ) مع تحديد الموضع من المركز أو الأطراف ومحرر قص يدوي.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="crop",
        tags=["قص", "اقتصاص", "نسبة", "crop", "aspect ratio", "cut"]
    ),
    ImageToolDefinition(
        id="rotate_orient",
        title_ar="التدوير وتصحيح الاتجاه التلقائي",
        title_en="Rotate & Auto-Orient",
        description_ar="تدوير 90° و 180°، انعكاس أفقي وعمودي، والتصحيح التلقائي للصور المقلوبة اعتماداً على حساس EXIF.",
        category="edit",
        icon="rotate",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="rotate",
        tags=["تدوير", "قلب", "انعكاس", "تصحيح", "rotate", "flip", "orientation", "exif"]
    ),

    # 5. Background & Transparency
    ImageToolDefinition(
        id="smart_transparency",
        title_ar="إزالة الخلفية والشفافية",
        title_en="Smart Transparency",
        description_ar="تفريغ الخلفية البيضاء أو لون محدد بدقة مع التحكم بمقدار التسامح Tolerance وحفظ النتيجة كـ PNG شفاف.",
        category="enhance",
        icon="wand",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="transparency",
        tags=["شفافية", "خلفية", "تفريغ", "ابيض", "transparent", "background", "alpha"]
    ),
    ImageToolDefinition(
        id="replace_bg_color",
        title_ar="تغيير لون خلفية الشفافية",
        title_en="Background Color Fill",
        description_ar="ملء المساحات الشفافة بلون أبيض، أسود، أو لون مخصص قبل التحويل إلى صيغ غير شفافة مثل JPG.",
        category="enhance",
        icon="palette",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="bg_fill",
        tags=["ملء", "خلفية", "تعبئة", "لون", "fill", "background color"]
    ),

    # 6. Watermark & Branding
    ImageToolDefinition(
        id="watermark",
        title_ar="إضافة علامة مائية أو شعار",
        title_en="Watermark & Logo Stamp",
        description_ar="ختم نص مخصص بزاوية وشفافية في 9 مواضع، أو إضافة شعار PNG مفرغ على دفعة الصور لحماية الحقوق.",
        category="enhance",
        icon="watermark",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="watermark",
        tags=["علامة مائية", "شعار", "حقوق", "لوجو", "watermark", "logo", "copyright", "stamp"]
    ),
    ImageToolDefinition(
        id="borders_canvas",
        title_ar="إضافة إطار وتوسيع الكانفاس",
        title_en="Frames & Canvas Expansion",
        description_ar="إضافة حواف وإطارات ملونة أو زوايا دائرية، أو توسيع مساحة العمل حول الصورة دون تكبير محتواها.",
        category="enhance",
        icon="palette",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="border",
        tags=["اطار", "حواف", "كانفاس", "border", "canvas", "padding", "frame"]
    ),

    # 7. Enhancement & Filters
    ImageToolDefinition(
        id="auto_enhance",
        title_ar="التحسين التلقائي للألوان والتباين",
        title_en="Auto Enhance & CLAHE",
        description_ar="تحسين فوري تلقائي للإضاءة وتوزيع الألوان والحدة والتباين باستخدام خوارزميات الرؤية الحاسوبية.",
        category="enhance",
        icon="wand",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="auto_enhance",
        tags=["تحسين", "اضاءة", "تباين", "حدة", "enhance", "contrast", "brightness", "clahe"]
    ),
    ImageToolDefinition(
        id="color_adjustments",
        title_ar="تعديل الإضاءة والألوان المتقدم",
        title_en="Color & Light Adjustments",
        description_ar="التحكم بالسطوع، التباين، التشبع، الحدة، إزالة التشويش (Denoise)، وتحويل لـ Grayscale أو Sepia أو B&W.",
        category="enhance",
        icon="palette",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="adjustments",
        tags=["سطوع", "الوان", "تشبع", "ابيض واسود", "sepia", "grayscale", "adjust", "denoise"]
    ),

    # 8. Privacy & Metadata
    ImageToolDefinition(
        id="strip_metadata_safe",
        title_ar="إنشاء نسخة آمنة وحذف الميتاداتا",
        title_en="Safe Share & Metadata Stripper",
        description_ar="حذف جميع بيانات EXIF و IPTC و XMP وتفاصيل الكاميرا لضمان الخصوصية التامة عند مشاركة الصور.",
        category="privacy",
        icon="lock",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="metadata_strip",
        tags=["خصوصية", "ميتاداتا", "exif", "امان", "privacy", "strip", "metadata", "clean"]
    ),
    ImageToolDefinition(
        id="strip_gps_only",
        title_ar="إزالة موقع GPS الجغرافي فقط",
        title_en="Strip GPS Location Only",
        description_ar="مسح إحداثيات المكان الجغرافي حصراً من صور الكاميرا مع الحفاظ على تاريخ الالتقاط وبقية البيانات.",
        category="privacy",
        icon="lock",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="gps_only",
        tags=["موقع", "gps", "خريطة", "احداثيات", "location", "geotag", "privacy"]
    ),
    ImageToolDefinition(
        id="shift_date",
        title_ar="تعديل وإزاحة تاريخ الصور",
        title_en="EXIF Date Shifter",
        description_ar="إزاحة وتعديل تاريخ ووقت التقاط الصور بالساعات أو الأيام لتصحيح أخطاء ساعة الكاميرا أو فارق التوقيت.",
        category="privacy",
        icon="settings",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="date_shift",
        tags=["تاريخ", "وقت", "ساعة", "ازاحة", "date", "time", "shift", "timestamp"]
    ),

    # 9. Advanced & Creation
    ImageToolDefinition(
        id="favicon_ico_generator",
        title_ar="توليد أيقونات Favicon و ICO",
        title_en="Favicon / ICO Generator",
        description_ar="توليد ملف أيقونة .ico احترافي مدمج يحتوي على كافة المقاسات (16, 24, 32, 48, 64, 128, 256).",
        category="advanced",
        icon="settings",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="ico_gen",
        tags=["ايقونة", "favicon", "ico", "icon", "website", "windows"]
    ),
    ImageToolDefinition(
        id="contact_sheet",
        title_ar="ورقة الملصقات Contact Sheet",
        title_en="Contact Sheet & Collage",
        description_ar="تجميع عشرات أو مئات الصور في شبكة موحدة Grid مع أسماء الملفات وخلفية متناسقة كملخص بصري.",
        category="advanced",
        icon="image",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="contact_sheet",
        tags=["ملصقات", "شبكة", "تجميع", "contact sheet", "grid", "collage", "montage"]
    ),
    ImageToolDefinition(
        id="gif_maker_extractor",
        title_ar="صانع ومستخرج صور GIF المتحركة",
        title_en="GIF Maker & Extractor",
        description_ar="إنشاء ملف GIF متحرك من سلسلة صور مع التحكم بالسرعة، أو استخراج كل إطار من ملف GIF إلى صور مستقلة.",
        category="advanced",
        icon="image",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="gif_tools",
        tags=["متحركة", "gif", "انيميشن", "اطارات", "animated", "frames", "extract"]
    ),
    ImageToolDefinition(
        id="similar_images_detection",
        title_ar="كشف الصور المتشابهة بصرياً",
        title_en="Perceptual Similarity Detector",
        description_ar="كشف الصور المتشابهة واللقطات المتقاربة بالبصمة الإدراكية (Perceptual Hash) مع نسبة التشابه.",
        category="advanced",
        icon="search",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="similarity",
        tags=["تشابه", "مكررة", "لقطات", "similar", "hash", "duplicates", "phash"]
    ),
    ImageToolDefinition(
        id="color_palette_extractor",
        title_ar="استخراج لوحة الألوان السائدة",
        title_en="Color Palette Extractor",
        description_ar="استخراج الألوان الأساسية المهيمنة على الصورة مع أكواد HEX و RGB وإمكانية نسخها بضغطة واحدة.",
        category="advanced",
        icon="palette",
        supports_batch=False,
        badge="جاهز للاستخدام",
        options_type="palette",
        tags=["الوان", "باليتة", "كود", "hex", "rgb", "palette", "dominant colors"]
    ),
    ImageToolDefinition(
        id="blur_quality_inspector",
        title_ar="فاحص حدة وجودة الصور",
        title_en="Blur & Quality Inspector",
        description_ar="تحليل مستوى الضبابية والاهتزاز وحساب دقة الميجابكسل ومعدل DPI وكثافة الألوان والبيانات التقنية.",
        category="advanced",
        icon="search",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="inspector",
        tags=["ضبابية", "اهتزاز", "حدة", "معلومات", "blur", "quality", "inspector", "laplacian"]
    ),

    # 10. Star Feature: Workflow Builder
    ImageToolDefinition(
        id="batch_workflow_builder",
        title_ar="سير المعالجة الجماعي المؤتمت",
        title_en="Batch Workflow Builder",
        description_ar="الميزة الأقوى: بناء سلسلة متتالية من العمليات (مثلاً: تدوير تلقائي -> تصغير -> إزالة GPS -> علامة مائية -> تحويل إلى WebP) وتطبيقها على آلاف الصور مرة واحدة.",
        category="workflow",
        icon="workflow",
        supports_batch=True,
        badge="نجم القسم",
        options_type="workflow",
        tags=["سلسلة", "سير عمل", "مؤتمت", "workflow", "pipeline", "batch", "chain", "preset"]
    ),
]


def get_tool_by_id(tool_id: str) -> Optional[ImageToolDefinition]:
    """Retrieves an image tool definition by its identifier."""
    for tool in IMAGE_TOOLS_REGISTRY:
        if tool.id == tool_id:
            return tool
    return None

# -*- coding: utf-8 -*-
"""
SINAX Video Center Registry
Data-driven registry defining all video processing tools, categories,
supported options schemas, and operational badges.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


VIDEO_CATEGORIES = [
    {"id": "all", "name_ar": "الكل", "icon": "video"},
    {"id": "popular", "name_ar": "الأكثر استخداماً", "icon": "popular"},
    {"id": "compress", "name_ar": "الضغط", "icon": "compress"},
    {"id": "convert", "name_ar": "التحويل", "icon": "convert"},
    {"id": "edit", "name_ar": "القص والدمج", "icon": "crop"},
    {"id": "audio", "name_ar": "الصوت", "icon": "audio"},
    {"id": "subtitles", "name_ar": "الترجمة", "icon": "file"},
    {"id": "resolution", "name_ar": "الحجم والدقة", "icon": "resize"},
    {"id": "speed", "name_ar": "السرعة", "icon": "play"},
    {"id": "frames", "name_ar": "الصور وFrames", "icon": "image"},
    {"id": "privacy", "name_ar": "الخصوصية وMetadata", "icon": "lock"},
    {"id": "advanced", "name_ar": "أدوات متقدمة", "icon": "settings"},
    {"id": "workflow", "name_ar": "سير العمل (Workflows)", "icon": "workflow"},
    {"id": "favorites", "name_ar": "المفضلة", "icon": "star"},
]


@dataclass
class VideoToolDefinition:
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


VIDEO_TOOLS_REGISTRY: List[VideoToolDefinition] = [
    # 1. Compression
    VideoToolDefinition(
        id="batch_video_compress",
        title_ar="ضغط الفيديو الجماعي",
        title_en="Batch Video Compress",
        description_ar="ضغط مئات أو آلاف الفيديوهات بذكاء مع تقليل الحجم والحفاظ على أعلى نقاء بصري وألوان متوازنة.",
        category="compress",
        icon="compress",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="compress",
        tags=["ضغط", "حجم", "توفير", "مساحة", "تخفيض", "batch", "compress", "reduce", "crf"]
    ),
    VideoToolDefinition(
        id="target_size_video_compress",
        title_ar="الضغط إلى حجم مستهدف",
        title_en="Target Size Optimizer",
        description_ar="تحديد سقف حجم أقصى (مثل ≤ 25 MB للواتساب أو الإيميل، 100 MB، 500 MB) مع حساب تلقائي للـ Bitrate.",
        category="compress",
        icon="compress",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="target_size",
        tags=["حجم مستهدف", "ميجابايت", "target size", "mb", "email", "whatsapp", "limit"]
    ),

    # 2. Format Conversion
    VideoToolDefinition(
        id="batch_video_convert",
        title_ar="تحويل صيغ الفيديو الشامل",
        title_en="Format Converter",
        description_ar="تحويل جماعي بين MP4, MKV, MOV, AVI, WebM, FLV, WMV, MPEG, TS, 3GP مع خيارات ترميز متطورة.",
        category="convert",
        icon="convert",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="convert",
        tags=["تحويل", "صيغة", "mp4", "mkv", "mov", "avi", "webm", "convert", "format"]
    ),
    VideoToolDefinition(
        id="fast_remux",
        title_ar="التحويل السريع بدون ترميز (Fast Remux)",
        title_en="Fast Lossless Remux",
        description_ar="تغيير حاوية الفيديو (مثل MKV إلى MP4) في ثوانٍ معدودة بنسخ المسارات مباشرة دون استهلاك المعالج أو فقدان الجودة.",
        category="convert",
        icon="convert",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="remux",
        tags=["remux", "نسخ", "فوري", "بدون اعادة ترميز", "fast", "stream copy"]
    ),

    # 3. Resolution & Social Media
    VideoToolDefinition(
        id="batch_video_resize",
        title_ar="تغيير دقة وأبعاد الفيديو",
        title_en="Batch Resize & Resolution",
        description_ar="تحويل دقة الفيديوهات جماعياً إلى 4K, 1440p, 1080p, 720p, 480p مع الحفاظ على التناسب أو إضافة Padding.",
        category="resolution",
        icon="resize",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="resize",
        tags=["دقة", "ابعاد", "1080p", "720p", "4k", "resize", "resolution", "scale"]
    ),
    VideoToolDefinition(
        id="social_video_presets",
        title_ar="تجهيز الفيديو للسوشيال ميديا",
        title_en="Social Media Presets",
        description_ar="قوالب جاهزة لـ Reels و Shorts و TikTok (9:16) و Instagram Square (1:1) مع خلفية ضبابية مشتقة من الفيديو.",
        category="resolution",
        icon="resize",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="social_presets",
        tags=["سوشيال", "ريلز", "شورتس", "تيك توك", "انستغرام", "reels", "shorts", "tiktok", "9:16"]
    ),
    VideoToolDefinition(
        id="crop_video",
        title_ar="اقتصاص أبعاد الفيديو (Crop)",
        title_en="Video Crop",
        description_ar="قص مساحة مخصصة من شاشة الفيديو أو اقتصاص بنسب ثابتة (16:9, 9:16, 1:1, 4:5).",
        category="resolution",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="crop",
        tags=["قص", "اقتصاص", "نسبة", "crop", "aspect ratio"]
    ),
    VideoToolDefinition(
        id="auto_crop_black_bars",
        title_ar="إزالة الحواف السوداء تلقائياً",
        title_en="Auto Crop Black Bars",
        description_ar="اكتشاف الحواف السوداء العلوية والجانبية (Letterbox / Pillarbox) وقصها آلياً لتعبئة الشاشة.",
        category="resolution",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="black_bars",
        tags=["حواف سوداء", "ازالة", "قص تلقائي", "letterbox", "black bars", "cropdetect"]
    ),

    # 4. Trim & Split & Merge
    VideoToolDefinition(
        id="video_trim",
        title_ar="قص بداية ونهاية الفيديو (Trim)",
        title_en="Trim & Cut",
        description_ar="تحديد وقت البدء والانتهاء (HH:MM:SS) وقص الجزء المرغوب بنمط النسخ السريع أو إعادة الترميز الدقيق.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="trim",
        tags=["قص", "تقطيع", "بداية", "نهاية", "trim", "cut", "duration"]
    ),
    VideoToolDefinition(
        id="video_split",
        title_ar="تقسيم الفيديو إلى أجزاء",
        title_en="Video Splitter",
        description_ar="تقسيم الفيديو حسب الوقت (كل 5 دقائق)، أو عدد محدد من الأجزاء، أو حسب حجم تقريبي (مثل كل 500 MB).",
        category="edit",
        icon="split",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="split",
        tags=["تقسيم", "اجزاء", "قطع", "split", "segments", "chunks"]
    ),
    VideoToolDefinition(
        id="video_merge",
        title_ar="دمج وتجميع الفيديوهات",
        title_en="Video Merger & Joiner",
        description_ar="دمج عدة مقاطع فيديو بالترتيب مع دعم الدمج الفوري بدون ترميز عند توافق الصيغ، أو الدمج الموحد.",
        category="edit",
        icon="merge",
        supports_batch=False,
        badge="جاهز للاستخدام",
        options_type="merge",
        tags=["دمج", "تجميع", "وصل", "merge", "join", "concat"]
    ),
    VideoToolDefinition(
        id="remove_video_segment",
        title_ar="حذف مقطع من منتصف الفيديو",
        title_en="Remove Middle Segment",
        description_ar="اقتطاع وحذف فترة زمنية محددة من داخل الفيديو ودمج المقطعين المتبقيين بسلاسة.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="remove_segment",
        tags=["حذف مقطع", "منتصف", "قص داخلي", "cut segment", "delete part"]
    ),

    # 5. Audio Tools
    VideoToolDefinition(
        id="mute_video",
        title_ar="إزالة الصوت بالكامل (Mute)",
        title_en="Mute Video",
        description_ar="حذف مسار الصوت نهائياً من الفيديو لإنتاج مقطع صامت عالي الجودة وصغير الحجم.",
        category="audio",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="mute",
        tags=["كتم", "صامت", "ازالة الصوت", "mute", "no audio", "strip audio"]
    ),
    VideoToolDefinition(
        id="extract_video_audio",
        title_ar="استخراج الصوت من الفيديو",
        title_en="Extract Audio",
        description_ar="استخراج مسار الصوت إلى MP3, WAV, AAC, M4A, FLAC, OGG, OPUS جماعياً مع خيار النسخ المباشر السريع.",
        category="audio",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="extract_audio",
        tags=["استخراج صوت", "mp3", "wav", "aac", "صوتيات", "extract audio", "rip"]
    ),
    VideoToolDefinition(
        id="replace_add_audio",
        title_ar="استبدال أو إضافة صوت وموسيقى",
        title_en="Replace / Add Audio",
        description_ar="دمج موسيقى خلفية جديدة مع الفيديو أو استبدال الصوت الأصلي بالكامل مع التحكم بالمستوى والتكرار.",
        category="audio",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="replace_audio",
        tags=["استبدال صوت", "موسيقى", "اضافة صوت", "add audio", "music", "background music"]
    ),
    VideoToolDefinition(
        id="audio_volume_loudnorm",
        title_ar="التحكم بالصوت والموازنة التلقائية",
        title_en="Volume & Audio Normalization",
        description_ar="رفع أو خفض مستوى الصوت، وتطبيق موازنة الصوت الذكية (EBU R128 Loudnorm) لمنع تفاوت الصوت.",
        category="audio",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="volume",
        tags=["رفع الصوت", "موازنة", "تعديل الصوت", "volume", "normalize", "loudnorm"]
    ),

    # 6. Speed & Direction
    VideoToolDefinition(
        id="video_speed_control",
        title_ar="تغيير سرعة الفيديو",
        title_en="Video Speed Control",
        description_ar="تسريع أو إبطاء الفيديو من 0.25x حتى 4x مع الحفاظ على نبرة الصوت وسلاسة الحركة.",
        category="speed",
        icon="play",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="speed",
        tags=["سرعة", "تسريع", "تبطيء", "speed", "slow motion", "fast forward", "tempo"]
    ),
    VideoToolDefinition(
        id="reverse_video",
        title_ar="عكس الفيديو والتشغيل للخلف",
        title_en="Reverse Video",
        description_ar="عكس تشغيل لقطات الفيديو بالكامل من النهاية إلى البداية مع خيار عكس الصوت.",
        category="speed",
        icon="play",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="reverse",
        tags=["عكس", "رجوع", "تشغيل للخلف", "reverse", "rewind"]
    ),
    VideoToolDefinition(
        id="rotate_flip_video",
        title_ar="تدوير وقلب الفيديو",
        title_en="Rotate & Flip Video",
        description_ar="تدوير الفيديو 90° يمين/يسار، 180° دوران كامل، وقلب أفقي (Mirror) أو عمودي.",
        category="advanced",
        icon="rotate",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="rotate",
        tags=["تدوير", "قلب", "انعكاس", "rotate", "flip", "transpose"]
    ),

    # 7. Watermark & Subtitles
    VideoToolDefinition(
        id="video_watermark",
        title_ar="إضافة علامة مائية أو شعار",
        title_en="Watermark & Logo Stamp",
        description_ar="ختم نص مخصص في 9 مواضع بشفافية وزاوية محددة، أو إضافة شعار PNG مفرغ مع تحديد وقت الظهور.",
        category="advanced",
        icon="watermark",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="watermark",
        tags=["علامة مائية", "شعار", "لوجو", "حقوق", "watermark", "logo", "copyright"]
    ),
    VideoToolDefinition(
        id="video_subtitles",
        title_ar="إدارة وحرق ملفات الترجمة",
        title_en="Subtitles Manager & Hardsub",
        description_ar="إضافة مسار ترجمة (SRT/VTT)، استخراج الترجمة من الفيديو، أو حرقها دائماً داخل الصورة بخط مخصص.",
        category="subtitles",
        icon="file",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="subtitles",
        tags=["ترجمة", "حرق ترجمة", "srt", "vtt", "subtitles", "hardsub"]
    ),

    # 8. Frames, GIF & Storyboard
    VideoToolDefinition(
        id="extract_video_frames",
        title_ar="استخراج الإطارات والصور من الفيديو",
        title_en="Extract Frames",
        description_ar="استخراج لقطة كل ثانية، كل 5 ثوان، أو التقاط إطار عند لحظة زمنية محددة بدقة وحفظها كـ JPG أو PNG.",
        category="frames",
        icon="image",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="frames",
        tags=["استخراج صور", "اطارات", "لقطة", "frames", "extract", "snapshot"]
    ),
    VideoToolDefinition(
        id="video_thumbnail_generator",
        title_ar="توليد صورة مصغرة للفيديو (Thumbnail)",
        title_en="Thumbnail Generator",
        description_ar="توليد صورة غلاف عالية الدقة (1080p أو 720p) من أي لحظة زمنية بالفيديو.",
        category="frames",
        icon="image",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="thumbnail",
        tags=["غلاف", "مصغرة", "thumbnail", "cover", "poster"]
    ),
    VideoToolDefinition(
        id="video_to_gif",
        title_ar="تحويل الفيديو إلى GIF متحرك",
        title_en="Video to GIF",
        description_ar="تحويل جزء من الفيديو إلى صورة متحركة عالية الجودة بنظام 2-Pass Palette Optimization وتحديد السرعة والأبعاد.",
        category="frames",
        icon="image",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="gif",
        tags=["متحرك", "gif", "انيميشن", "video to gif", "animated"]
    ),
    VideoToolDefinition(
        id="contact_sheet_storyboard",
        title_ar="لوحة المعاينة Contact Sheet",
        title_en="Video Contact Sheet & Storyboard",
        description_ar="توليد شبكة ملصقات Grid من 12 أو 24 لقطة موزعة زمنياً مع التوقيت كملخص بصري للمقطع.",
        category="frames",
        icon="image",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="contact_sheet",
        tags=["لوحة معاينة", "ملخص", "contact sheet", "storyboard", "preview"]
    ),
    VideoToolDefinition(
        id="slideshow_creator",
        title_ar="إنشاء فيديو من الصور (Slideshow)",
        title_en="Images to Video Slideshow",
        description_ar="تحويل سلسلة صور إلى فيديو عالي الدقة مع تحديد مدة كل صورة ومسار موسيقى خلفية اختياري.",
        category="frames",
        icon="video",
        supports_batch=False,
        badge="جاهز للاستخدام",
        options_type="slideshow",
        tags=["سلايد شو", "صور الى فيديو", "عرض شرائح", "slideshow", "images to video"]
    ),

    # 9. Filters & Enhancements
    VideoToolDefinition(
        id="video_color_filters",
        title_ar="فلاتر الفيديو وتحسين الألوان",
        title_en="Color Filters & Enhancement",
        description_ar="تعديل السطوع، التباين، التشبع، إزالة التشويش (Denoise)، زيادة الحدة (Sharpen)، وتحويل لـ Grayscale أو Sepia.",
        category="advanced",
        icon="wand",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="filters",
        tags=["فلاتر", "سطوع", "تباين", "تشويش", "حدة", "filters", "brightness", "contrast", "denoise"]
    ),

    # 10. Inspector, Metadata & GPU
    VideoToolDefinition(
        id="media_inspector_metadata",
        title_ar="فاحص الفيديو ومحرر الميتاداتا",
        title_en="Media Inspector & Metadata",
        description_ar="عرض تفاصيل الحاوية ومسارات الفيديو والصوت والـ Bitrate، وتعديل الميتاداتا أو مسحها بالكامل للمشاركة الآمنة.",
        category="privacy",
        icon="lock",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="inspector",
        tags=["ميتاداتا", "فاحص", "خصوصية", "معلومات", "metadata", "inspector", "ffprobe"]
    ),
    VideoToolDefinition(
        id="hardware_acceleration_setup",
        title_ar="كشف والتسريع العتادي (GPU)",
        title_en="Hardware Acceleration",
        description_ar="اكتشاف كروت الشاشة (NVIDIA NVENC, Intel QSV, AMD AMF) وتسخير قدراتها لتسريع عمليات الترميز.",
        category="advanced",
        icon="settings",
        supports_batch=False,
        badge="جاهز للاستخدام",
        options_type="hardware",
        tags=["كرت شاشة", "تسريع عتادي", "nvenc", "qsv", "amf", "gpu", "hardware acceleration"]
    ),

    # 11. Star Feature: Video Workflow Builder
    VideoToolDefinition(
        id="batch_video_workflow_builder",
        title_ar="سير المعالجة الجماعي المؤتمت",
        title_en="Batch Video Workflow Builder",
        description_ar="الميزة الأقوى: بناء سلسلة متتالية من العمليات (مثل: تحويل لـ MP4 -> تحجيم لـ 1080p -> H.265 -> علامة مائية -> موازنة صوت -> مسح ميتاداتا) وتطبيقها على مئات المقاطع دفعة واحدة.",
        category="workflow",
        icon="workflow",
        supports_batch=True,
        badge="نجم القسم",
        options_type="workflow",
        tags=["سلسلة", "سير عمل", "مؤتمت", "workflow", "pipeline", "batch", "chain", "preset"]
    ),
]


VIDEO_TOOLS = VIDEO_TOOLS_REGISTRY

# Aliases mapping shorthand IDs to registry IDs
TOOL_ALIASES = {
    "batch_compress": "batch_video_compress",
    "target_size_compress": "target_size_video_compress",
    "batch_convert": "batch_video_convert",
    "resize_scale": "batch_video_resize",
    "trim_cut": "video_trim",
    "cut_middle": "video_cut_middle",
    "split_video": "video_split",
    "merge_videos": "video_merge",
    "mute_audio": "mute_video",
    "volume_normalize": "audio_loudnorm",
    "speed_reverse": "video_speed",
    "rotate_flip": "video_rotate_flip",
    "thumbnail": "video_thumbnail",
    "create_gif": "video_gif",
    "contact_sheet": "video_contact_sheet",
    "filters_enhance": "video_filters",
    "strip_metadata": "media_inspector_metadata",
    "batch_workflow_builder": "batch_video_workflow_builder",
}


def get_all_video_tools() -> List[VideoToolDefinition]:
    """Returns all registered video tool definitions."""
    return list(VIDEO_TOOLS_REGISTRY)


def get_tools_by_category(category_id: str) -> List[VideoToolDefinition]:
    """Returns video tools belonging to the specified category."""
    cat_aliases = {
        "compression": "compress",
        "conversion": "convert",
        "editing": "edit",
    }
    resolved_cat = cat_aliases.get(category_id, category_id)
    if resolved_cat in ("all", ""):
        return list(VIDEO_TOOLS_REGISTRY)
    return [t for t in VIDEO_TOOLS_REGISTRY if t.category == resolved_cat]


def get_video_tool_by_id(tool_id: str) -> Optional[VideoToolDefinition]:
    """Retrieves a video tool definition by its identifier or alias."""
    resolved_id = TOOL_ALIASES.get(tool_id, tool_id)
    for tool in VIDEO_TOOLS_REGISTRY:
        if tool.id == resolved_id or tool.id == tool_id:
            return tool
    return None


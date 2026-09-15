# -*- coding: utf-8 -*-
"""
SINAX Audio Center Registry
Data-driven registry defining all audio processing tools, categories,
supported options schemas, and operational badges.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


AUDIO_CATEGORIES = [
    {"id": "all", "name_ar": "الكل", "icon": "audio"},
    {"id": "popular", "name_ar": "الأكثر استخداماً", "icon": "popular"},
    {"id": "convert", "name_ar": "التحويل والصيغ", "icon": "convert"},
    {"id": "compress", "name_ar": "الضغط والحجم", "icon": "compress"},
    {"id": "edit", "name_ar": "القص والدمج والتقسيم", "icon": "crop"},
    {"id": "volume", "name_ar": "الصوت والمستوى والديناميكا", "icon": "audio"},
    {"id": "clean", "name_ar": "التنقية وإزالة الضوضاء", "icon": "wand"},
    {"id": "eq", "name_ar": "المعادل والفلاتر (EQ)", "icon": "settings"},
    {"id": "speed", "name_ar": "السرعة والطبقة (Pitch)", "icon": "play"},
    {"id": "channels", "name_ar": "القنوات والستيريو", "icon": "duplicate"},
    {"id": "metadata", "name_ar": "البيانات والغلاف (Tags)", "icon": "file"},
    {"id": "analysis", "name_ar": "التحليل والمخطط الصوتي", "icon": "search"},
    {"id": "workflow", "name_ar": "سير العمل الصوتي (Workflows)", "icon": "workflow"},
    {"id": "favorites", "name_ar": "المفضلة", "icon": "star"},
]


@dataclass
class AudioToolDefinition:
    id: str
    title_ar: str
    title_en: str
    description_ar: str
    category: str
    icon: str
    supports_batch: bool = True
    badge: str = "جاهز للاستخدام"
    options_type: str = "convert"
    tags: List[str] = field(default_factory=list)


AUDIO_TOOLS_REGISTRY: List[AudioToolDefinition] = [
    # 1. Conversion & Formats
    AudioToolDefinition(
        id="batch_audio_convert",
        title_ar="التحويل الجماعي للصوت",
        title_en="Batch Audio Convert",
        description_ar="تحويل مئات أو آلاف الملفات الصوتية بسرعة فائقة بين صيغ MP3, WAV, FLAC, AAC, M4A, OGG, OPUS, WMA, AIFF, ALAC, AC3, AMR مع التحكم بالـ Bitrate والـ Sample Rate.",
        category="convert",
        icon="convert",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="convert",
        tags=["تحويل", "صيغ", "mp3", "wav", "flac", "aac", "m4a", "opus", "ogg", "wma", "convert", "bitrate", "batch"]
    ),

    # 2. Compression & Size
    AudioToolDefinition(
        id="batch_audio_compress",
        title_ar="ضغط الصوت الذكي",
        title_en="Smart Audio Compress",
        description_ar="تقليل أحجام المقاطع والتسجيلات بدقة عالية دون التضحية بنقاء الصوت، مع إعدادات مسبقة مريحة (خفيف، متوازن، قوي، أقصى).",
        category="compress",
        icon="compress",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="compress",
        tags=["ضغط", "حجم", "توفير", "مساحة", "تخفيض", "compress", "shrink", "mp3"]
    ),
    AudioToolDefinition(
        id="target_size_audio_compress",
        title_ar="الضغط إلى حجم مستهدف",
        title_en="Target Size Audio Optimizer",
        description_ar="تحديد سقف حجم أقصى بالـ MB (مثل أقل من 5MB، 10MB، أو مخصص للواتساب والإيميل) وحساب الـ Bitrate الرياضي تلقائياً للوصول للهدف بدقة.",
        category="compress",
        icon="compress",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="target_size",
        tags=["حجم مستهدف", "تحديد الحجم", "واتساب", "target", "size", "limit", "calculator"]
    ),

    # 3. Trimming, Splitting, Merging & Fades
    AudioToolDefinition(
        id="trim_audio",
        title_ar="قص وتقليم الصوت",
        title_en="Trim & Cut Audio",
        description_ar="قص بداية أو نهاية الملف بدقة أجزاء الثانية، أو استخراج مقطع زمني محدد من مئات الملفات دفعة واحدة.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="trim",
        tags=["قص", "تقليم", "اجتزاء", "trim", "cut", "duration", "start", "end"]
    ),
    AudioToolDefinition(
        id="split_audio",
        title_ar="تقسيم الصوت",
        title_en="Audio Splitter",
        description_ar="تقسيم الملفات الطويلة والكتب الصوتية والبودكاست إلى أجزاء متساوية بالدقائق أو إلى عدد أجزاء محدد.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="split",
        tags=["تقسيم", "تجزئة", "كتب صوتية", "بودكاست", "split", "chunk", "parts"]
    ),
    AudioToolDefinition(
        id="silence_split_audio",
        title_ar="التقسيم التلقائي حسب فترات الصمت",
        title_en="Split by Silence Detection",
        description_ar="اكتشاف فترات السكون والصمت داخل التسجيل الطويل وتقسيمه تلقائياً إلى مقاطع وتراكات منفصلة.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="silence_split",
        tags=["صمت", "سكون", "تلقائي", "تقسيم بالصمت", "silence", "detect", "split"]
    ),
    AudioToolDefinition(
        id="merge_audio",
        title_ar="دمج المقاطع الصوتية",
        title_en="Merge Audio Tracks",
        description_ar="دمج عدة ملفات صوتية في مسار صوتي واحد وبترتيب مخصص بالسحب والإفلات وتوحيد معدلات الترميز.",
        category="edit",
        icon="merge",
        supports_batch=False,
        badge="جاهز للاستخدام",
        options_type="merge",
        tags=["دمج", "تجميع", "ميكس", "merge", "combine", "concat", "join"]
    ),
    AudioToolDefinition(
        id="crossfade_audio",
        title_ar="الدمج المتداخل (Crossfade)",
        title_en="Crossfade Audio Joiner",
        description_ar="دمج التراكات مع تأثير الانتقال الناعم المتداخل (تلاشي صوت التراك السابق بالتزامن مع دخول التراك التالي).",
        category="edit",
        icon="merge",
        supports_batch=False,
        badge="جاهز للاستخدام",
        options_type="crossfade",
        tags=["تداخل", "تلاشي", "كروس فيد", "crossfade", "acrossfade", "transition", "smooth"]
    ),
    AudioToolDefinition(
        id="fade_audio",
        title_ar="تلاشي الصوت (Fade In / Out)",
        title_en="Fade In & Fade Out",
        description_ar="إضافة تأثير بدء هادئ تدريجي (Fade In) أو ختام هادئ تدريجي (Fade Out) في بداية ونهاية المقاطع.",
        category="edit",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="fade",
        tags=["تلاشي", "دخول تدريجي", "خروج تدريجي", "fade", "afade", "in", "out"]
    ),

    # 4. Volume, Normalization & Dynamics
    AudioToolDefinition(
        id="loudness_normalize_audio",
        title_ar="المعايرة القياسية EBU R128 (LUFS)",
        title_en="Loudness Normalization (EBU R128)",
        description_ar="توحيد علو الصوت وفق المعايير العالمية لمنصات البث والبودكاست (-14 LUFS لليوتيوب وسبوتيفاي، -16 LUFS للبودكاست، -23 LUFS للبث).",
        category="volume",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="loudness",
        tags=["معايرة", "lufs", "ebu r128", "loudness", "spotify", "youtube", "podcast", "broadcast"]
    ),
    AudioToolDefinition(
        id="peak_normalize_audio",
        title_ar="المعايرة الذروية (Peak Normalize)",
        title_en="Peak Normalization",
        description_ar="رفع علو المقاطع الصوتية إلى أقصى حد مسموح دون تشويه (0 dBFS أو -1 dBFS) لتوحيد مستوى مجموعة ملفات.",
        category="volume",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="peak_norm",
        tags=["ذروة", "معايرة ذروية", "peak", "normalize", "gain", "0db"]
    ),
    AudioToolDefinition(
        id="volume_adjust_audio",
        title_ar="تعديل وتضخيم الصوت (Gain)",
        title_en="Volume & Gain Adjust",
        description_ar="رفع أو خفض الصوت بمقدار محدد بالديسيبل (+dB / -dB) أو بنسبة مئوية مع الحماية من التقطيع والتشويه.",
        category="volume",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="volume",
        tags=["رفع الصوت", "تضخيم", "خفض", "ديسيبل", "volume", "gain", "amplify", "boost"]
    ),
    AudioToolDefinition(
        id="compressor_audio",
        title_ar="ضاغط الديناميكا (Compressor)",
        title_en="Dynamic Range Compressor",
        description_ar="موازنة الفروق بين الأصوات العالية والمنخفضة (acompressor) لجعل الصوت متماسكاً واحترافياً للتسجيلات الصوتية.",
        category="volume",
        icon="settings",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="compressor",
        tags=["ضاغط", "ديناميكا", "كومبريسور", "compressor", "dynamics", "threshold", "ratio"]
    ),
    AudioToolDefinition(
        id="limiter_audio",
        title_ar="محدد الذروة (Audio Limiter)",
        title_en="Peak Limiter (alimiter)",
        description_ar="منع الـ Clipping والتشويه الرقمي وحماية السماعات من المفاجآت الصوتية الحادة عبر سقف أقصى صارم.",
        category="volume",
        icon="lock",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="limiter",
        tags=["ليمتير", "محدد", "حماية", "limiter", "ceiling", "clip"]
    ),
    AudioToolDefinition(
        id="noise_gate_audio",
        title_ar="بوابة الضوضاء (Noise Gate)",
        title_en="Noise Gate (agate)",
        description_ar="كتم وإسكات الإشارة تماماً عندما ينخفض مستوى الصوت دون عتبة معينة لإزالة ضجيج الخلفية بين الكلمات.",
        category="volume",
        icon="audio",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="noise_gate",
        tags=["بوابة", "نويز جيت", "gate", "agate", "silence", "threshold"]
    ),

    # 5. Cleaning & Noise Reduction
    AudioToolDefinition(
        id="denoise_audio",
        title_ar="إزالة الضوضاء والوشيش (Denoise)",
        title_en="FFT Noise Reduction",
        description_ar="إزالة الوشيش المستمر وضوضاء المكيف والمروحة وخلفية الميكروفون باستخدام فلتر FFT الرقمي الذكي.",
        category="clean",
        icon="wand",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="denoise",
        tags=["ضوضاء", "وشيش", "تنقية", "مكيف", "مروحة", "denoise", "afftdn", "noise", "clean"]
    ),
    AudioToolDefinition(
        id="hum_removal_audio",
        title_ar="إزالة طنين الكهرباء (Hum 50/60 Hz)",
        title_en="Hum & Ground Buzz Removal",
        description_ar="عزل وإزالة طنين الكهرباء الأرضية وترددات 50Hz و 60Hz ومضاعفاتها التوافقية بفلاتر شق فائقة الدقة.",
        category="clean",
        icon="wand",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="hum_removal",
        tags=["طنين", "كهرباء", "50hz", "60hz", "hum", "buzz", "ground", "notch"]
    ),
    AudioToolDefinition(
        id="declick_declip_audio",
        title_ar="معالجة الطقطقة والتشويه الرقمي",
        title_en="De-Click & De-Clip Restorer",
        description_ar="إصلاح النقر والطقطقة الصوتية الناتجة عن الميكروفونات أو الأسطوانات وترميم القمم المشوهة المبتورة.",
        category="clean",
        icon="wand",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="declick",
        tags=["طقطقة", "نقر", "ترميم", "تشويه", "declick", "declip", "restore"]
    ),
    AudioToolDefinition(
        id="silence_remove_audio",
        title_ar="إزالة وحذف فترات الصمت (Silence Stripper)",
        title_en="Truncate Silence",
        description_ar="اكتشاف وحذف لحظات الصمت الطويلة من البداية والنهاية أو بين الجمل والفقرات لتسريع البودكاست والمحاضرات.",
        category="clean",
        icon="crop",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="silence_remove",
        tags=["حذف الصمت", "اقتصاص السكون", "سكون", "silence", "remove", "truncate", "silenceremove"]
    ),
    AudioToolDefinition(
        id="podcast_voice_enhancer",
        title_ar="معزز البودكاست والكلام بنقرة واحدة",
        title_en="1-Click Podcast Voice Enhancer",
        description_ar="سلسلة معالجة صوتية متكاملة بضغطة زر: تنقية الضوضاء + فلتر الترددات المنخفضة + تجميل نبرة الصوت + ضغط ديناميكي + معايرة -16 LUFS.",
        category="clean",
        icon="wand",
        supports_batch=True,
        badge="شائع وموصى به",
        options_type="podcast_enhancer",
        tags=["بودكاست", "صوت بشري", "تحسين", "تعزيز", "ميكروفون", "podcast", "voice", "enhancer", "magic"]
    ),

    # 6. Equalizers & Filters (EQ)
    AudioToolDefinition(
        id="graphic_eq_audio",
        title_ar="المعادل الصوتي (Graphic EQ)",
        title_en="Multi-Band Graphic Equalizer",
        description_ar="التحكم الكامل في طبقات الترددات (البيز، الأصوات المتوسطة، التريبل) مع إعدادات جاهزة (كلام، موسيقى، بيز معزز، نقي).",
        category="eq",
        icon="settings",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="eq",
        tags=["معادل", "اكوالايزر", "بيز", "تربل", "eq", "equalizer", "bass", "treble", "bands"]
    ),
    AudioToolDefinition(
        id="filters_audio",
        title_ar="الفلاتر الصوتية (High-Pass / Low-Pass)",
        title_en="Acoustic Filters (HPF / LPF)",
        description_ar="عزل الترددات غير المرغوبة: فلتر تمرير الترددات العالية لحذف هواء الميكروفون، وفلتر تمرير المنخفضة لحذف الصرير الحاد.",
        category="eq",
        icon="settings",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="filters",
        tags=["فلتر", "هاي باس", "لو باس", "hpf", "lpf", "highpass", "lowpass", "filter"]
    ),
    AudioToolDefinition(
        id="bass_treble_boost",
        title_ar="تعزيز البيز والتريبل السريع",
        title_en="Quick Bass & Treble Booster",
        description_ar="رفع عمق وتضخيم ترددات البيز (Bass Boost) أو زيادة وضوح وبريق الترددات الحادة (Treble Boost) بمزلاجين فقط.",
        category="eq",
        icon="settings",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="bass_treble",
        tags=["بيز", "تريبل", "تضخيم", "bass", "treble", "boost"]
    ),

    # 7. Speed & Pitch
    AudioToolDefinition(
        id="speed_tempo_audio",
        title_ar="تغيير سرعة الصوت (Tempo)",
        title_en="Change Audio Speed / Tempo",
        description_ar="تسريع أو إبطاء التسجيل الصوتي (0.5x إلى 2.0x) مع الحفاظ التام على طبقة ونبرة الصوت الطبيعية دون تغيير نبرة المتحدث.",
        category="speed",
        icon="play",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="speed",
        tags=["سرعة", "تسريع", "إبطاء", "تمبو", "speed", "tempo", "atempo", "duration"]
    ),
    AudioToolDefinition(
        id="pitch_shift_audio",
        title_ar="تغيير طبقة الصوت (Pitch Shift)",
        title_en="Audio Pitch Shift",
        description_ar="تعديل نغمة وطبقة الصوت بالأنصاف النغمية (Semitones) للأعلى أو للأسفل لصنع مؤثرات صوتية ونغمات مميزة.",
        category="speed",
        icon="play",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="pitch",
        tags=["طبقة", "نبرة", "بيتش", "pitch", "semitones", "tune", "shift"]
    ),
    AudioToolDefinition(
        id="reverse_audio",
        title_ar="عكس الصوت للخلف (Reverse)",
        title_en="Reverse Audio Playback",
        description_ar="عكس المسار الصوتي ليعمل من النهاية إلى البداية لإنشاء مؤثرات صوتية تشويقية أو فنية.",
        category="speed",
        icon="play",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="reverse",
        tags=["عكس", "مقلوب", "خلف", "reverse", "areverse", "backwards"]
    ),

    # 8. Channels & Stereo Routing
    AudioToolDefinition(
        id="channel_routing_audio",
        title_ar="توجيه القنوات (Mono / Stereo)",
        title_en="Audio Channel Routing",
        description_ar="التحويل من ستيريو لمونو (Mono Downmix)، أو من مونو لستيريو مزدوج، أو عكس السماعتين اليمنى واليسرى، أو موازنة الـ Pan.",
        category="channels",
        icon="duplicate",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="channels",
        tags=["قنوات", "مونو", "ستيريو", "يمين", "يسار", "بان", "mono", "stereo", "pan", "swap"]
    ),
    AudioToolDefinition(
        id="extract_channels_audio",
        title_ar="فصل واستخراج القنوات",
        title_en="Split Channels to Separate Tracks",
        description_ar="فصل القناة اليسرى والقناة اليمنى من المقاطع الستيريو واستخراج كل قناة في ملف صوتي مستقل تماماً.",
        category="channels",
        icon="duplicate",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="extract_channels",
        tags=["فصل", "استخراج", "قناة يمنى", "قناة يسرى", "extract", "channels", "split"]
    ),

    # 9. Metadata & Tags
    AudioToolDefinition(
        id="metadata_editor_audio",
        title_ar="محرر البيانات الوصفية وغلاف الألبوم",
        title_en="Audio Tag & Metadata Editor",
        description_ar="تحرير وسوم ID3 والبيانات الوصفية دفعة واحدة (العنوان، الفنان، الألبوم، السنة، النوع الموسيقي) وإضافة أو استخراج صورة الغلاف (Cover Art).",
        category="metadata",
        icon="file",
        supports_batch=True,
        badge="جاهز للاستخدام",
        options_type="metadata",
        tags=["بيانات", "ميتاداتا", "وسوم", "غلاف", "فنان", "ألبوم", "id3", "tags", "metadata", "cover"]
    ),

    # 10. Technical Analysis & Visualization
    AudioToolDefinition(
        id="audio_analysis_inspector",
        title_ar="فاحص ومحلل الصوت الشامل (Waveform & LUFS)",
        title_en="Audio Inspector & Waveform Analyzer",
        description_ar="فحص هندسي للملف الصوتي: استخراج المخطط الموجي (Waveform)، المخطط الطيفي (Spectrogram)، قياسات LUFS الحقيقية والـ True Peak ومعدل الترميز.",
        category="analysis",
        icon="search",
        supports_batch=False,
        badge="متقدم",
        options_type="analysis",
        tags=["فحص", "تحليل", "موجة", "طيف", "مخطط", "spectrogram", "waveform", "lufs", "analyzer"]
    ),

    # 11. Workflow Builder
    AudioToolDefinition(
        id="audio_workflow_builder",
        title_ar="منشئ سلاسل المعالجة الصوتية (Workflow Builder)",
        title_en="Custom Audio Workflow Builder",
        description_ar="بناء سلاسل معالجة مخصصة تجمع عدة خطوات (مثل: حذف الصمت ثم تنقية الوشيش ثم المعادل ثم ضبط LUFS ثم التحويل لـ MP3) وتطبيقها دفعة واحدة.",
        category="workflow",
        icon="workflow",
        supports_batch=True,
        badge="الميزة النجمية",
        options_type="workflow",
        tags=["سلسلة", "سير عمل", "تدفق", "مخصص", "أتمتة", "workflow", "pipeline", "chain", "batch"]
    ),
]


def get_audio_tool_by_id(tool_id: str) -> Optional[AudioToolDefinition]:
    """Retrieve an audio tool definition by its unique ID."""
    for tool in AUDIO_TOOLS_REGISTRY:
        if tool.id == tool_id:
            return tool
    return None


def get_audio_tools_by_category(category_id: str) -> List[AudioToolDefinition]:
    """Filter audio tools by category identifier."""
    if category_id == "all":
        return list(AUDIO_TOOLS_REGISTRY)
    elif category_id == "popular":
        popular_ids = {
            "batch_audio_convert",
            "batch_audio_compress",
            "podcast_voice_enhancer",
            "loudness_normalize_audio",
            "trim_audio",
            "denoise_audio",
            "merge_audio",
            "audio_workflow_builder"
        }
        return [t for t in AUDIO_TOOLS_REGISTRY if t.id in popular_ids]
    return [t for t in AUDIO_TOOLS_REGISTRY if t.category == category_id]


def search_audio_tools(query: str) -> List[AudioToolDefinition]:
    """Perform fuzzy search on audio tools across title, description, and tags."""
    if not query:
        return list(AUDIO_TOOLS_REGISTRY)
    q = query.strip().lower()
    results = []
    for tool in AUDIO_TOOLS_REGISTRY:
        if (q in tool.title_ar.lower() or
            q in tool.title_en.lower() or
            q in tool.description_ar.lower() or
            any(q in tag.lower() for tag in tool.tags)):
            results.append(tool)
    return results

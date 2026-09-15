# -*- coding: utf-8 -*-
"""
SINAX Quick Tool Registry
Central catalog of all available Quick Tools with metadata, multilingual search,
Arabic/English synonym matching, category organization, and execution dispatchers.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.quick_tools.models import InputType, QuickToolDefinition, SafetyLevel
from app.services.quick_tools.tools.calculator_tools import CalculatorTools
from app.services.quick_tools.tools.clipboard_tools import ClipboardTools
from app.services.quick_tools.tools.conversion_tools import ConversionTools
from app.services.quick_tools.tools.datetime_tools import DateTimeTools
from app.services.quick_tools.tools.developer_tools import DeveloperTools
from app.services.quick_tools.tools.encoding_tools import EncodingTools
from app.services.quick_tools.tools.file_tools import FileTools
from app.services.quick_tools.tools.folder_tools import FolderTools
from app.services.quick_tools.tools.generation_tools import GenerationTools
from app.services.quick_tools.tools.hash_tools import HashTools
from app.services.quick_tools.tools.list_tools import ListTools
from app.services.quick_tools.tools.naming_tools import NamingTools
from app.services.quick_tools.tools.password_tools import PasswordTools
from app.services.quick_tools.tools.qr_barcode_tools import QrBarcodeTools
from app.services.quick_tools.tools.system_tools import SystemTools
from app.services.quick_tools.tools.text_tools import TextTools
from app.services.quick_tools.tools.web_tools import WebTools


CATEGORIES = [
    ("all", "الكل", "tools"),
    ("favorites", "المفضلة", "favorite"),
    ("hash", "Hash والبصمة", "hash"),
    ("encoding", "الترميز والتشفير", "convert"),
    ("qr", "QR والباركود", "qr"),
    ("password", "الأمان وكلمات المرور", "security"),
    ("text", "مختبر النصوص", "text"),
    ("file", "أدوات الملفات", "file"),
    ("folder", "أدوات المجلدات", "folder"),
    ("generation", "توليد الملفات", "create"),
    ("conversion", "التحويلات والحساب", "calculator"),
    ("datetime", "الوقت والتاريخ", "history"),
    ("developer", "أدوات المطورين", "code"),
    ("clipboard", "الحافظة", "clipboard"),
    ("system", "بيئة ويندوز", "windows"),
    ("naming", "الأسماء والسلاسل", "rename"),
    ("list", "مختبر القوائم", "organize"),
    ("batch", "المعالجة الدفعية", "duplicate"),
]


class QuickToolRegistry:
    """Master registry managing all quick tool definitions and search indexing."""

    _tools: Dict[str, QuickToolDefinition] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """Initializes and registers all tools in the system."""
        if cls._initialized:
            return

        cls._tools.clear()

        # ----------------------------------------------------
        # 1. Hash & Checksum Lab
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="hash_calculator",
            title_ar="حاسبة بصمة الهاش (Hash Calculator)",
            title_en="Hash Calculator",
            category="hash",
            icon="hash",
            description_ar="حساب بصمات التجزئة للنصوص والملفات (SHA-256, MD5, SHA-512, BLAKE2)",
            description_en="Computes cryptographic hashes for text and files.",
            aliases=["hash", "sha256", "md5", "sha1", "sha512", "checksum", "بصمة", "هاش", "تجزئة", "تأكد من سلامة الملف"],
            keywords=["sha-256", "sha-512", "md5", "sha-1", "blake2b", "blake2s", "digest"],
            input_types=[InputType.TEXT, InputType.FILE],
            supports_batch=True,
            handler=HashTools.compute_text_hash,
        ))

        cls._register(QuickToolDefinition(
            id="hash_verify",
            title_ar="التحقق من صحة البصمة (Verify Checksum)",
            title_en="Verify Checksum",
            category="hash",
            icon="check",
            description_ar="مقارنة بصمة الملف الحالية مع البصمة المتوقعة المعتمدة للتحقق من سلامة التحميل",
            description_en="Compares computed file hash against expected digest.",
            aliases=["verify", "match", "مطابقة", "فحص البصمة", "تحقق من التحميل", "سلامة الملف"],
            keywords=["match", "compare", "integrity", "verify", "sha256"],
            input_types=[InputType.FILE, InputType.HASH],
            handler=HashTools.verify_checksum,
        ))

        cls._register(QuickToolDefinition(
            id="folder_manifest",
            title_ar="مانيفست سلامة المجلد (Folder Manifest)",
            title_en="Folder Integrity Manifest",
            category="hash",
            icon="folder",
            description_ar="إنشاء ملف بصمات SHA-256 لكافة ملفات المجلد ومقارنته لاحقاً لكشف أي تعديل أو فقدان",
            description_en="Generates and verifies directory-wide checksum manifests.",
            aliases=["manifest", "folder hash", "هاش مجلد", "مانيفست", "حماية النسخ الاحتياطي", "كشف التعديل"],
            keywords=["manifest", "tree", "integrity", "backup", "verify folder"],
            input_types=[InputType.FOLDER],
            supports_batch=True,
            handler=HashTools.generate_folder_manifest,
        ))

        cls._register(QuickToolDefinition(
            id="hash_guesser",
            title_ar="تخمين نوع البصمة (Hash Format Guesser)",
            title_en="Hash Format Guesser",
            category="hash",
            icon="search",
            description_ar="التعرف على خوارزمية الهاش المرجحة بناءً على طول النص السداسي عشري (Hex Length)",
            description_en="Guesses hash algorithm based on hex string length.",
            aliases=["guess hash", "identify hash", "تخمين نوع الهاش", "معرفة الهاش"],
            keywords=["md5", "sha1", "sha256", "length"],
            input_types=[InputType.TEXT, InputType.HASH],
            handler=HashTools.guess_hash_format,
        ))

        # ----------------------------------------------------
        # 2. Base64 & Encoding Lab
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="base64_tool",
            title_ar="ترميز وفك Base64",
            title_en="Base64 Encoder / Decoder",
            category="encoding",
            icon="convert",
            description_ar="تحويل النصوص والملفات الثنائية من وإلى ترميز Base64 الآمن",
            description_en="Encode and decode text and binary files to Base64.",
            aliases=["base64", "b64", "ترميز", "فك ترميز", "base64 encode", "base64 decode"],
            keywords=["base64", "encode", "decode", "binary", "ascii"],
            input_types=[InputType.TEXT, InputType.FILE],
            handler=EncodingTools.text_to_base64,
        ))

        cls._register(QuickToolDefinition(
            id="hex_converter",
            title_ar="تحويل Hex إلى نص والعكس",
            title_en="Hex / Text Converter",
            category="encoding",
            icon="convert",
            description_ar="تحويل النصوص الصريحة إلى قيم سداسية عشرية Hexadecimal وبالعكس",
            description_en="Convert plain text to Hex bytes and Hex to text.",
            aliases=["hex", "hexadecimal", "سداسي عشري", "بايت", "hex to text"],
            keywords=["hex", "bytes", "binary", "decode"],
            input_types=[InputType.TEXT],
            handler=EncodingTools.text_to_hex,
        ))

        cls._register(QuickToolDefinition(
            id="binary_converter",
            title_ar="تحويل Binary ثنائي إلى نص والعكس",
            title_en="Binary / Text Converter",
            category="encoding",
            icon="convert",
            description_ar="تحويل النصوص إلى رموز ثنائية أصفار وآحاد (01001000) وبالعكس",
            description_en="Convert text to binary representation and back.",
            aliases=["binary", "ثنائي", "أصفار وآحاد", "bits", "01"],
            keywords=["binary", "bits", "bytes", "ascii"],
            input_types=[InputType.TEXT],
            handler=EncodingTools.text_to_binary,
        ))

        cls._register(QuickToolDefinition(
            id="url_encoder",
            title_ar="ترميز وفك روابط URL",
            title_en="URL Encoder / Decoder",
            category="encoding",
            icon="globe",
            description_ar="ترميز وفك الرموز الخاصة والمسافات في الروابط (Percent-encoding)",
            description_en="Encode and decode URL parameters and safe path characters.",
            aliases=["url encode", "url decode", "ترميز رابط", "فك رابط", "%20"],
            keywords=["url", "percent", "escape", "query"],
            input_types=[InputType.TEXT, InputType.URL],
            handler=EncodingTools.url_encode,
        ))

        cls._register(QuickToolDefinition(
            id="html_entities",
            title_ar="ترميز وفك كيانات HTML Entities",
            title_en="HTML Entities Encoder / Decoder",
            category="encoding",
            icon="code",
            description_ar="تحويل الرموز الخاصة مثل < و > و & إلى كيانات HTML صالحة للعرض بأمان",
            description_en="Convert characters to HTML entities and back.",
            aliases=["html encode", "html entities", "كيانات html", "&amp;", "&lt;"],
            keywords=["html", "entities", "escape", "unescape"],
            input_types=[InputType.TEXT],
            handler=EncodingTools.html_encode,
        ))

        cls._register(QuickToolDefinition(
            id="unicode_inspector",
            title_ar="فاحص محارف يونيكود (Unicode Inspector)",
            title_en="Unicode & Character Inspector",
            category="encoding",
            icon="search",
            description_ar="استعراض تفاصيل الحرف: نقطة الرمز (U+XXXX)، البايتات في UTF-8، والاسم القياسي",
            description_en="Inspect character codepoints, names, and UTF-8 byte representations.",
            aliases=["unicode", "character", "يونيكود", "رمز المحرف", "فحص الحرف", "codepoint"],
            keywords=["unicode", "codepoint", "utf-8", "character name", "ascii"],
            input_types=[InputType.TEXT],
            handler=EncodingTools.inspect_character,
        ))

        cls._register(QuickToolDefinition(
            id="bom_inspector",
            title_ar="فاحص ومعدل علامة BOM للملفات",
            title_en="BOM Inspector & Modifier",
            category="encoding",
            icon="file",
            description_ar="كشف وجود علامة ترتيب البايتات (Byte Order Mark) وإضافتها أو إزالتها بنقرة واحدة",
            description_en="Inspect, add, or remove UTF-8 and UTF-16 Byte Order Marks.",
            aliases=["bom", "utf8 bom", "remove bom", "إزالة bom", "علامة ترتيب البايتات"],
            keywords=["bom", "utf-8", "utf-16", "encoding", "header"],
            input_types=[InputType.FILE],
            safety_level=SafetyLevel.MODIFIES_FILE,
            modifies_source=True,
            handler=EncodingTools.inspect_bom,
        ))

        # ----------------------------------------------------
        # 3. QR & Barcode Studio
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="qr_generator",
            title_ar="صانع رمز الاستجابة السريعة (QR Generator)",
            title_en="QR Code Generator",
            category="qr",
            icon="qr",
            description_ar="توليد رموز QR نقية محلياً للنصوص، الروابط، شبكات Wi-Fi، وجهات الاتصال vCard",
            description_en="Create offline QR codes for text, URLs, Wi-Fi networks, and contacts.",
            aliases=["qr", "qrcode", "كيو ار", "باركود كيو ار", "رمز استجابة", "qr generator"],
            keywords=["qr", "barcode", "wifi qr", "vcard", "contact qr", "share qr"],
            input_types=[InputType.TEXT, InputType.URL],
            output_type="qr_image",
            handler=QrBarcodeTools.generate_styled_qr,
        ))

        cls._register(QuickToolDefinition(
            id="wifi_qr",
            title_ar="إنشاء QR لشبكة Wi-Fi",
            title_en="Wi-Fi QR Code Maker",
            category="qr",
            icon="wifi",
            description_ar="توليد QR لمشاركة الاتصال بشبكة الواي فاي مع الهواتف دون الحاجة لكتابة كلمة السر",
            description_en="Generates Wi-Fi connection QR for instant mobile access.",
            aliases=["wifi qr", "واي فاي qr", "شبكة qr", "مشاركة الواي فاي"],
            keywords=["wifi", "qr", "network", "password"],
            input_types=[InputType.TEXT],
            output_type="qr_image",
            handler=QrBarcodeTools.format_wifi_qr,
        ))

        cls._register(QuickToolDefinition(
            id="barcode_generator",
            title_ar="مُولّد الباركود الخطي (Barcode Generator)",
            title_en="1D Barcode Generator",
            category="qr",
            icon="qr",
            description_ar="إنشاء باركود أحادي الأبعاد متجهي وعالي الدقة (Code 39, Code 128) قابل للطباعة",
            description_en="Generate high-resolution 1D linear barcodes (Code 39 / 128).",
            aliases=["barcode", "باركود", "باركود خطي", "code39", "code128"],
            keywords=["barcode", "1d", "code 39", "code 128", "retail"],
            input_types=[InputType.TEXT],
            output_type="qr_image",
            handler=QrBarcodeTools.generate_barcode,
        ))

        # ----------------------------------------------------
        # 4. Password & Security Utilities
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="password_generator",
            title_ar="مُولّد كلمات المرور القوية",
            title_en="Secure Password Generator",
            category="password",
            icon="security",
            description_ar="توليد كلمات مرور عشوائية مشفرة ومعقدة مع خيارات تخصيص الأحرف والرموز واستبعاد المتشابهات",
            description_en="Generates cryptographically random passwords with customizable charsets.",
            aliases=["password", "pass", "كلمة سر", "كلمة مرور", "توليد باسوورد", "مولد باسوورد"],
            keywords=["password", "generator", "random", "secure", "cryptography"],
            input_types=[InputType.NONE],
            safety_level=SafetyLevel.SENSITIVE,
            handler=PasswordTools.generate_password,
        ))

        cls._register(QuickToolDefinition(
            id="passphrase_generator",
            title_ar="مُولّد العبارات السرية السهلة الحفظ (Passphrase)",
            title_en="Memorable Passphrase Generator",
            category="password",
            icon="security",
            description_ar="توليد عبارات مرور طويلة وآمنة جداً مبنية من كلمات واضحة يسهل تذكرها",
            description_en="Generates multi-word memorable passphrases.",
            aliases=["passphrase", "عبارة مرور", "كلمة سر سهلة الحفظ", "diceware"],
            keywords=["passphrase", "memorable", "words", "security"],
            input_types=[InputType.NONE],
            safety_level=SafetyLevel.SENSITIVE,
            handler=PasswordTools.generate_passphrase,
        ))

        cls._register(QuickToolDefinition(
            id="password_strength",
            title_ar="فاحص قوة كلمة المرور والإنتروبيا",
            title_en="Password Strength & Entropy Estimator",
            category="password",
            icon="doctor",
            description_ar="تقدير محلي ودقيق لقوة كلمة المرور ومستوى الإنتروبيا (Bits) وتقديم نصائح التحسين دون أي إرسال للخارج",
            description_en="Estimates entropy and strength of a password 100% locally.",
            aliases=["strength", "قوة كلمة المرور", "فحص الباسوورد", "إنتروبيا", "entropy"],
            keywords=["entropy", "strength", "security", "bits"],
            input_types=[InputType.TEXT],
            safety_level=SafetyLevel.SENSITIVE,
            handler=PasswordTools.estimate_password_strength,
        ))

        cls._register(QuickToolDefinition(
            id="uuid_generator",
            title_ar="مُولّد المعرفات الفريدة (UUID / GUID Generator)",
            title_en="UUID / GUID Generator",
            category="password",
            icon="code",
            description_ar="توليد معرفات UUID v4 أو v1 قياسية بشكل فردي أو دفعة واحدة (حتى 1000 معرف)",
            description_en="Generate standard UUID v4/v1 tokens in batches.",
            aliases=["uuid", "guid", "معرف فريد", "توليد uuid", "uuid generator"],
            keywords=["uuid", "guid", "token", "unique id"],
            input_types=[InputType.NONE],
            handler=PasswordTools.generate_uuid,
        ))

        # ----------------------------------------------------
        # 5. Text Laboratory
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="text_cleaner",
            title_ar="منظف النصوص الشامل (Text Cleaner)",
            title_en="Text Cleaner Pipeline",
            category="text",
            icon="clean",
            description_ar="إزالة الفراغات الزائدة، الأسطر الفارغة، المسافات المكررة، وتحويل علامات الجدولة",
            description_en="Trims lines, cleans redundant spaces, and removes blank lines.",
            aliases=["clean text", "تنظيف النص", "حذف الفراغات", "مسح الأسطر الفارغة", "trim"],
            keywords=["clean", "spaces", "trim", "blank lines", "normalize"],
            input_types=[InputType.TEXT],
            handler=TextTools.clean_text,
        ))

        cls._register(QuickToolDefinition(
            id="duplicate_lines_remover",
            title_ar="حذف الأسطر المكررة (Remove Duplicate Lines)",
            title_en="Remove Duplicate Lines",
            category="text",
            icon="duplicate",
            description_ar="حذف الأسطر المتطابقة من القوائم والنصوص مع الحفاظ على الترتيب الأصلي",
            description_en="Removes duplicate lines while preserving original sequence.",
            aliases=["dedup", "duplicate lines", "حذف التكرار", "إزالة المكرر", "أسطر مكررة"],
            keywords=["dedup", "duplicates", "unique", "lines"],
            input_types=[InputType.TEXT],
            handler=TextTools.remove_duplicate_lines,
        ))

        cls._register(QuickToolDefinition(
            id="sort_lines",
            title_ar="فرز وترتيب الأسطر (Sort Lines)",
            title_en="Sort Lines",
            category="text",
            icon="organize",
            description_ar="ترتيب الأسطر أبجدياً (أ-ي أو A-Z)، رقمياً، تصاعدياً، تنازلياً، أو عشوائياً",
            description_en="Sort lines alphabetically, numerically, naturally, or randomly.",
            aliases=["sort", "order", "ترتيب الأسطر", "فرز", "أبجدي", "تصاعدي"],
            keywords=["sort", "order", "alphabetical", "natural", "shuffle"],
            input_types=[InputType.TEXT],
            handler=TextTools.sort_lines,
        ))

        cls._register(QuickToolDefinition(
            id="change_case",
            title_ar="تغيير حالة الأحرف (Change Case)",
            title_en="Change Text Case",
            category="text",
            icon="text",
            description_ar="التحويل بين: أحرف كبيرة، صغيرة، Title Case، camelCase، snake_case، kebab-case",
            description_en="Convert between uppercase, lowercase, camelCase, snake_case, etc.",
            aliases=["case", "uppercase", "lowercase", "camelcase", "snake_case", "حالة الأحرف", "كبير وصغير"],
            keywords=["case", "capital", "upper", "lower", "title", "snake", "kebab"],
            input_types=[InputType.TEXT],
            handler=TextTools.change_case,
        ))

        cls._register(QuickToolDefinition(
            id="word_counter",
            title_ar="عدّاد الكلمات والإحصائيات النصية",
            title_en="Word & Character Counter",
            category="text",
            icon="performance",
            description_ar="حساب عدد الأحرف، الكلمات، الأسطر، الفقرات، البايتات، ووقت القراءة التقديري",
            description_en="Calculates characters, words, sentences, and estimated reading time.",
            aliases=["word count", "count words", "عدد الكلمات", "كم حرف", "احسب الكلمات", "عد الكلمات"],
            keywords=["words", "characters", "lines", "metrics", "stats"],
            input_types=[InputType.TEXT],
            handler=TextTools.calculate_text_metrics,
        ))

        cls._register(QuickToolDefinition(
            id="arabic_cleaner",
            title_ar="معالج النصوص العربية وتجريد التشكيل",
            title_en="Arabic Text Cleaner",
            category="text",
            icon="text",
            description_ar="إزالة التشكيل والحركات، حذف التطويل (ـ)، وتوحيد أشكال الألف (أ، إ، آ إلى ا)",
            description_en="Normalizes Arabic text, strips diacritics, and removes tatweel.",
            aliases=["arabic", "تجريد التشكيل", "إزالة الحركات", "حذف التشكيل", "تنظيف عربي", "تطويل"],
            keywords=["arabic", "tashkeel", "diacritics", "tatweel", "alef"],
            input_types=[InputType.TEXT],
            handler=TextTools.clean_arabic_text,
        ))

        cls._register(QuickToolDefinition(
            id="invisible_chars",
            title_ar="كاشف المحارف الخفية (Invisible Characters)",
            title_en="Invisible Character Inspector",
            category="text",
            icon="search",
            description_ar="كشف وإبراز المسافات غير المرئية (Zero Width Space, NBSP) وإزالتها بنقرة واحدة",
            description_en="Detect and remove zero-width and non-breaking invisible spaces.",
            aliases=["invisible", "zero width", "محارف خفية", "مسافات وهمية", "zwsp", "nbsp"],
            keywords=["invisible", "zero width", "whitespace", "hidden characters"],
            input_types=[InputType.TEXT],
            handler=TextTools.inspect_invisible_characters,
        ))

        cls._register(QuickToolDefinition(
            id="line_endings",
            title_ar="محول نهايات الأسطر (Line Endings)",
            title_en="Line Endings Converter",
            category="text",
            icon="convert",
            description_ar="التحويل بين نهايات أسطر ويندوز (CRLF) ونظام لينكس/ماك (LF)",
            description_en="Convert line endings between Windows (CRLF) and Unix (LF).",
            aliases=["crlf", "lf", "line endings", "نهايات الأسطر", "تحويل الأسطر"],
            keywords=["crlf", "lf", "newline", "windows", "unix"],
            input_types=[InputType.TEXT],
            handler=TextTools.convert_line_endings,
        ))

        cls._register(QuickToolDefinition(
            id="text_diff",
            title_ar="مقارنة النصوص وتلوين الفروقات (Text Diff)",
            title_en="Text Diff & Comparison",
            category="text",
            icon="duplicate",
            description_ar="مقارنة نصين جنباً إلى جنب وتلوين الأسطر المضافة، المحذوفة، والمعدلة",
            description_en="Compare two texts side-by-side with color-coded line diffs.",
            aliases=["diff", "compare text", "مقارنة نصين", "فرق النصوص", "تلوين الفروق"],
            keywords=["diff", "compare", "difflib", "changes"],
            input_types=[InputType.TEXT],
            handler=TextTools.compute_text_diff,
        ))

        cls._register(QuickToolDefinition(
            id="entity_extractor",
            title_ar="مستخرج البيانات (Extract Emails, URLs, IPs)",
            title_en="Entity & Pattern Extractor",
            category="text",
            icon="search",
            description_ar="استخراج رسائل البريد الإلكتروني، روابط الويب، أرقام الهواتف، أو عناوين IP من النصوص",
            description_en="Extracts emails, URLs, IP addresses, and numbers from text.",
            aliases=["extract", "extract emails", "استخراج الايميلات", "استخراج الروابط", "عناوين ip"],
            keywords=["extract", "email", "url", "ipv4", "phone", "scrape"],
            input_types=[InputType.TEXT],
            handler=TextTools.extract_entities,
        ))

        cls._register(QuickToolDefinition(
            id="regex_tester",
            title_ar="مختبر التعبيرات النمطية (Regex Tester)",
            title_en="Regular Expression Tester",
            category="text",
            icon="code",
            description_ar="اختبار ومطابقة التعبيرات النمطية (RegEx) مع عرض المطابقات ومجموعات الالتقاط Groups",
            description_en="Test and debug regular expressions with match and group inspection.",
            aliases=["regex", "regexp", "تعبيرات نمطية", "مختبر regex", "اختبار regex"],
            keywords=["regex", "pattern", "match", "groups", "tester"],
            input_types=[InputType.TEXT],
            handler=TextTools.test_regex,
        ))

        # ----------------------------------------------------
        # 6. File Quick Tools
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="file_inspector",
            title_ar="فاحص تفاصيل الملف (File Inspector)",
            title_en="File Inspector & Metadata",
            category="file",
            icon="file",
            description_ar="استعراض شامل للحجم، التواريخ، السمات، نوع MIME، والبصمة",
            description_en="Inspects comprehensive metadata, size, timestamps, and attributes.",
            aliases=["file info", "معلومات الملف", "حجم الملف", "تفاصيل الملف", "سمات الملف"],
            keywords=["file", "stat", "metadata", "size", "timestamps"],
            input_types=[InputType.FILE],
            handler=FileTools.inspect_file,
        ))

        cls._register(QuickToolDefinition(
            id="copy_path_variants",
            title_ar="نسخ المسارات بصيغ متعددة (Copy Path)",
            title_en="Copy Path Variants",
            category="file",
            icon="duplicate",
            description_ar="نسخ مسار الملف بصيغة Windows، Quoted، PowerShell، Python raw string، أو URI",
            description_en="Copy file paths formatted for CMD, PowerShell, Python, or Web URI.",
            aliases=["copy path", "نسخ المسار", "مسار ويندوز", "مسار بايثون", "path quoted"],
            keywords=["path", "copy", "uri", "powershell", "python"],
            input_types=[InputType.FILE, InputType.FOLDER],
            handler=FileTools.get_path_copy_variants,
        ))

        cls._register(QuickToolDefinition(
            id="timestamp_editor",
            title_ar="محرر تواريخ الملفات مع إمكانية التراجع",
            title_en="File Timestamp Editor",
            category="file",
            icon="history",
            description_ar="تعديل تاريخ ووقت الإنشاء والتعديل للملف مع تسجيل القيم القديمة للتراجع عنها",
            description_en="Modify file creation and modified timestamps with undo support.",
            aliases=["timestamp", "change date", "تغيير تاريخ الملف", "تعديل الوقت", "touch"],
            keywords=["timestamp", "mtime", "atime", "undo", "date"],
            input_types=[InputType.FILE],
            safety_level=SafetyLevel.MODIFIES_FILE,
            modifies_source=True,
            handler=FileTools.change_timestamps,
        ))

        cls._register(QuickToolDefinition(
            id="magic_bytes_inspector",
            title_ar="فاحص التوقيع الرقمي والامتداد المزيف",
            title_en="File Signature & Extension Inspector",
            category="file",
            icon="security",
            description_ar="قراءة البايتات السحرية (Magic Bytes) لكشف الامتدادات المزدوجة والملفات المتخفية (photo.jpg.exe)",
            description_en="Detect genuine file signatures and double extensions.",
            aliases=["magic bytes", "file signature", "امتداد مزيف", "فحص الامتداد", "نوع الملف الحقيقي"],
            keywords=["magic", "header", "double extension", "security", "mime"],
            input_types=[InputType.FILE],
            handler=FileTools.inspect_magic_signature,
        ))

        # ----------------------------------------------------
        # 7. Folder Quick Tools
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="folder_size_stats",
            title_ar="حجم المجلد وإحصائياته الحية (Folder Size)",
            title_en="Folder Size & Statistics",
            category="folder",
            icon="storage",
            description_ar="حساب الحجم الإجمالي، عدد الملفات والمجلدات، أكبر وأحدث ملف، وتوزيع الامتدادات",
            description_en="Calculate live folder size, file counts, and extension breakdown.",
            aliases=["folder size", "حجم المجلد", "كم حجم المجلد", "إحصائيات المجلد", "مساحة المجلد"],
            keywords=["folder", "size", "disk", "stats", "count"],
            input_types=[InputType.FOLDER],
            handler=FolderTools.calculate_folder_stats,
        ))

        cls._register(QuickToolDefinition(
            id="directory_tree",
            title_ar="مُولّد شجرة المجلدات (Directory Tree)",
            title_en="Directory Tree Generator",
            category="folder",
            icon="treemap",
            description_ar="إنشاء شجرة بصرية لهيكل المجلد بصيغة نصية أو Markdown أو JSON لمشاركتها",
            description_en="Generates directory visual tree hierarchy in Unicode, ASCII, or Markdown.",
            aliases=["tree", "dir tree", "شجرة المجلد", "مخطط المجلد", "هيكل المجلد"],
            keywords=["tree", "directory", "structure", "markdown", "unicode"],
            input_types=[InputType.FOLDER],
            handler=FolderTools.generate_directory_tree,
        ))

        cls._register(QuickToolDefinition(
            id="extract_filenames",
            title_ar="استخراج أسماء الملفات (Extract File Names)",
            title_en="Extract File Names to List",
            category="folder",
            icon="export",
            description_ar="استخراج قائمة بأسماء كافة الملفات الموجودة في مجلد وحفظها كـ TXT أو CSV أو JSON",
            description_en="Extract listing of all filenames in a directory to CSV/JSON/TXT.",
            aliases=["list files", "extract names", "أسماء الملفات", "جرد المجلد", "تصدير الملفات"],
            keywords=["inventory", "filenames", "csv", "json", "list"],
            input_types=[InputType.FOLDER],
            handler=FolderTools.extract_file_names,
        ))

        cls._register(QuickToolDefinition(
            id="compare_folders",
            title_ar="مقارنة محتويات مجلدين (Compare Folders)",
            title_en="Folder Listing Comparison",
            category="folder",
            icon="duplicate",
            description_ar="مقارنة محتويات مجلدين لكشف الملفات الموجودة في أحدهما فقط أو الملفات ذات الأحجام المختلفة",
            description_en="Compares listings between two folders without full byte hashing.",
            aliases=["compare folders", "مقارنة مجلدين", "فروقات المجلدات", "مجلد أ ومجلد ب"],
            keywords=["compare", "folders", "diff", "missing"],
            input_types=[InputType.FOLDER],
            handler=FolderTools.compare_folder_listings,
        ))

        cls._register(QuickToolDefinition(
            id="empty_folders_finder",
            title_ar="كاشف المجلدات الفارغة (Empty Folders)",
            title_en="Empty Folder Finder",
            category="folder",
            icon="clean",
            description_ar="البحث عن كافة المجلدات الفارغة التي لا تحتوي على أي ملفات مع معاينتها بأمان",
            description_en="Find all empty directories with safe preview.",
            aliases=["empty folders", "مجلدات فارغة", "البحث عن المجلدات الفارغة", "تنظيف الفوارغ"],
            keywords=["empty", "folders", "cleanup", "zero bytes"],
            input_types=[InputType.FOLDER],
            handler=FolderTools.find_empty_folders,
        ))

        # ----------------------------------------------------
        # 8. File Generation Lab
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="custom_size_file",
            title_ar="إنشاء ملف بحجم مخصص (Custom Size File)",
            title_en="Custom Sized Dummy File Generator",
            category="generation",
            icon="create",
            description_ar="إنشاء ملف بحجم محدد (1MB إلى 10GB) مملوء بأصفار أو بيانات عشوائية لاختبار النقل والتخزين",
            description_en="Creates files of exact byte sizes with zeros, patterns, or random data.",
            aliases=["dummy file", "ملف وهمي", "إنشاء ملف بحجم", "ملف تجريبي", "test file"],
            keywords=["size", "generator", "dummy", "test", "sparse"],
            input_types=[InputType.NONE],
            safety_level=SafetyLevel.MODIFIES_FILE,
            handler=GenerationTools.generate_custom_size_file,
        ))

        cls._register(QuickToolDefinition(
            id="lorem_ipsum",
            title_ar="مُولّد نصوص تجريبية (Lorem Ipsum & Arabic)",
            title_en="Lorem Ipsum & Dummy Text Generator",
            category="generation",
            icon="text",
            description_ar="توليد فقرات نصية بديلة باللغتين العربية واللاتينية لاختبار النماذج والتخطيطات",
            description_en="Generate sample placeholder text in Arabic and Latin.",
            aliases=["lorem", "ipsum", "نص تجريبي", "نص بديل", "توليد نص"],
            keywords=["lorem", "ipsum", "placeholder", "dummy text"],
            input_types=[InputType.NONE],
            handler=GenerationTools.generate_lorem_ipsum,
        ))

        cls._register(QuickToolDefinition(
            id="sample_csv_generator",
            title_ar="مُولّد بيانات CSV تجريبية (Sample CSV)",
            title_en="Sample CSV Data Generator",
            category="generation",
            icon="table",
            description_ar="إنشاء جدول CSV تجريبي بأعمدة وأسماء وبريد إلكتروني لاختبار قواعد البيانات والتحويلات",
            description_en="Generates dummy tabular CSV datasets for testing.",
            aliases=["sample csv", "csv generator", "جدول تجريبي", "بيانات وهمية csv"],
            keywords=["csv", "sample", "dataset", "mock"],
            input_types=[InputType.NONE],
            handler=GenerationTools.generate_sample_csv,
        ))

        # ----------------------------------------------------
        # 9. Number & Conversion Lab
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="data_size_converter",
            title_ar="محول أحجام البيانات (Data Size Converter)",
            title_en="Data Units Converter",
            category="conversion",
            icon="convert",
            description_ar="تحويل دقيق بين وحدات البيانات الرقمية (Bytes, KB, KiB, MB, MiB, GB, GiB, TB)",
            description_en="Converts between decimal (SI) and binary (IEC) data units.",
            aliases=["convert size", "mb to gb", "gb to mb", "تحويل الحجم", "بايت الى ميجا", "جيجا"],
            keywords=["bytes", "kb", "mb", "gb", "tib", "gib", "conversion"],
            input_types=[InputType.NUMBER, InputType.TEXT],
            handler=ConversionTools.convert_data_size,
        ))

        cls._register(QuickToolDefinition(
            id="network_speed_converter",
            title_ar="محول سرعة الإنترنت (Mbps ↔ MB/s)",
            title_en="Network Speed Converter",
            category="conversion",
            icon="speedtest",
            description_ar="التحويل بين الميغابت بالثانية (Mbps) والميغابايت بالثانية (MB/s) وسرعات التحميل الفعلية",
            description_en="Convert network transmission rates between Mbps, MB/s, Gbps, etc.",
            aliases=["speed converter", "mbps to mb", "تحويل سرعة النت", "ميجابت الى ميجابايت"],
            keywords=["mbps", "mb/s", "bandwidth", "speed", "rate"],
            input_types=[InputType.NUMBER, InputType.TEXT],
            handler=ConversionTools.convert_network_speed,
        ))

        cls._register(QuickToolDefinition(
            id="transfer_time_calculator",
            title_ar="حاسبة وقت التحميل والنقل (Transfer ETA)",
            title_en="Download & Transfer Time Calculator",
            category="conversion",
            icon="history",
            description_ar="حساب الوقت المتوقع لتحميل أو نقل ملف بحجم معين بناءً على سرعة الاتصال مع احتساب الفاقد",
            description_en="Calculates estimated transfer duration based on size and bandwidth.",
            aliases=["download time", "وقت التحميل", "كم يستغرق التحميل", "حساب وقت النقل", "eta"],
            keywords=["transfer", "download", "eta", "duration", "file transfer"],
            input_types=[InputType.TEXT],
            handler=ConversionTools.calculate_transfer_time,
        ))

        cls._register(QuickToolDefinition(
            id="storage_overhead_calculator",
            title_ar="حاسبة السعة الفعلية للأقراص في ويندوز",
            title_en="Real Usable Storage Calculator",
            category="conversion",
            icon="storage",
            description_ar="توضيح الفرق الحسابي بين سعة القرص التجارية (GB) والسعة الفعلية المقروءة في ويندوز (GiB)",
            description_en="Explains commercial GB vs Windows GiB discrepancy.",
            aliases=["usable storage", "لماذا القرص ناقص", "سعة القرص الفعلية", "فرق السعة"],
            keywords=["storage", "gib", "ntfs", "usable", "capacity"],
            input_types=[InputType.NUMBER, InputType.TEXT],
            handler=ConversionTools.calculate_usable_storage,
        ))

        cls._register(QuickToolDefinition(
            id="number_base_converter",
            title_ar="محول أنظمة العد (Base Converter)",
            title_en="Number Base Converter",
            category="conversion",
            icon="calculator",
            description_ar="التحويل بين النظام العشري (DEC)، الثنائي (BIN)، الثماني (OCT)، والسداسي عشري (HEX)",
            description_en="Convert numbers between Decimal, Hex, Binary, and Octal.",
            aliases=["base converter", "dec to hex", "hex to dec", "أنظمة العد", "عشري وثنائي"],
            keywords=["binary", "hex", "octal", "decimal", "base"],
            input_types=[InputType.NUMBER, InputType.TEXT],
            handler=ConversionTools.convert_number_base,
        ))

        cls._register(QuickToolDefinition(
            id="scientific_calculator",
            title_ar="الحاسبة العلمية الآمنة (Safe Calculator)",
            title_en="Safe Scientific Calculator",
            category="conversion",
            icon="calculator",
            description_ar="حاسبة علمية متقدمة تدعم الجذور، اللوغاريتمات، النسب المثلثية، والأقواس بدون eval()",
            description_en="Evaluates mathematical expressions safely using AST without eval().",
            aliases=["calculator", "calc", "حاسبة", "آلة حاسبة", "حساب رياضي", "scientific calc"],
            keywords=["calc", "math", "sqrt", "sin", "cos", "log", "pi"],
            input_types=[InputType.TEXT],
            handler=CalculatorTools.evaluate_expression,
        ))

        # ----------------------------------------------------
        # 10. Date & Time Tools
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="unix_timestamp_converter",
            title_ar="محول الطابع الزمني (Unix Timestamp)",
            title_en="Unix Epoch Timestamp Converter",
            category="datetime",
            icon="history",
            description_ar="تحويل أرقام Unix Epoch بالثواني أو الميلي ثانية إلى تاريخ ووقت محلي وعالمي وبالعكس",
            description_en="Convert between Unix epoch timestamps and human dates.",
            aliases=["unix timestamp", "epoch", "طابع زمني", "تحويل الوقت unix", "epoch to date"],
            keywords=["unix", "epoch", "timestamp", "datetime", "utc"],
            input_types=[InputType.NUMBER, InputType.TEXT],
            handler=DateTimeTools.unix_to_datetime,
        ))

        cls._register(QuickToolDefinition(
            id="working_days_calculator",
            title_ar="حاسبة أيام العمل الفعلية (Working Days)",
            title_en="Business Working Days Calculator",
            category="datetime",
            icon="history",
            description_ar="حساب عدد أيام العمل بين تاريخين مع استبعاد عطلات نهاية الأسبوع المختارة",
            description_en="Calculates business days between dates excluding chosen weekends.",
            aliases=["working days", "أيام العمل", "حساب أيام الدوام", "business days"],
            keywords=["calendar", "working days", "weekends", "duration"],
            input_types=[InputType.TEXT],
            handler=DateTimeTools.calculate_working_days,
        ))

        # ----------------------------------------------------
        # 11. Developer Micro Tools
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="json_formatter",
            title_ar="منسق وفاحص JSON (JSON Formatter)",
            title_en="JSON Formatter & Validator",
            category="developer",
            icon="code",
            description_ar="تنسيق وترتيب ملفات JSON، تصغيرها (Minify)، وكشف مكان أخطاء الصياغة برقم السطر والعمود",
            description_en="Pretty print, minify, and validate JSON with exact syntax line/col errors.",
            aliases=["json", "format json", "تنسيق json", "فحص json", "json minify"],
            keywords=["json", "pretty", "minify", "validate", "syntax"],
            input_types=[InputType.TEXT, InputType.JSON],
            handler=DeveloperTools.format_json,
        ))

        cls._register(QuickToolDefinition(
            id="jwt_inspector",
            title_ar="فاحص رموز JWT (JWT Inspector)",
            title_en="JWT Token Inspector",
            category="developer",
            icon="security",
            description_ar="فك محتوى Header و Payload لرموز JWT محلياً واستعراض الصلاحيات وتاريخ الانتهاء",
            description_en="Decodes and inspects JSON Web Tokens locally with safety notes.",
            aliases=["jwt", "token inspector", "فك jwt", "فحص jwt", "json web token"],
            keywords=["jwt", "token", "payload", "claims", "auth"],
            input_types=[InputType.TEXT],
            safety_level=SafetyLevel.SENSITIVE,
            handler=DeveloperTools.inspect_jwt,
        ))

        cls._register(QuickToolDefinition(
            id="color_converter",
            title_ar="محول صيغ الألوان (Color Converter)",
            title_en="Color Formats Converter",
            category="developer",
            icon="convert",
            description_ar="التحويل التلقائي بين صيغ الألوان HEX و RGB و RGBA و HSL مع معاينة اللون المباشرة",
            description_en="Convert color codes between HEX, RGB, and HSL with preview swatch.",
            aliases=["color", "hex to rgb", "rgb to hex", "ألوان", "تحويل اللون", "كود اللون"],
            keywords=["color", "hex", "rgb", "hsl", "css color"],
            input_types=[InputType.TEXT],
            handler=DeveloperTools.convert_color,
        ))

        cls._register(QuickToolDefinition(
            id="cron_helper",
            title_ar="مفسر تعبيرات Cron (Cron Helper)",
            title_en="Cron Expression Explainer",
            category="developer",
            icon="history",
            description_ar="ترجمة تعبيرات جدولة المهام Cron المكونة من 5 حقول إلى جمل واضحة باللغة العربية",
            description_en="Explains 5-field cron schedule expressions in plain language.",
            aliases=["cron", "crontab", "تفسير cron", "جدولة cron"],
            keywords=["cron", "schedule", "crontab", "time"],
            input_types=[InputType.TEXT],
            handler=DeveloperTools.explain_cron,
        ))

        # ----------------------------------------------------
        # 12. Clipboard Laboratory
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="clipboard_inspector",
            title_ar="فاحص محتوى الحافظة (Clipboard Inspector)",
            title_en="System Clipboard Inspector",
            category="clipboard",
            icon="clipboard",
            description_ar="معاينة البيانات الموجودة في ذاكرة النسخ الحالية (نص، صورة، قائمة ملفات)",
            description_en="Inspects active data in Windows system clipboard.",
            aliases=["clipboard", "الحافظة", "فحص الحافظة", "ما في الحافظة"],
            keywords=["clipboard", "paste", "copy", "mime"],
            input_types=[InputType.NONE],
            handler=ClipboardTools.inspect_clipboard,
        ))

        cls._register(QuickToolDefinition(
            id="copy_plain_text",
            title_ar="تجريد الحافظة إلى نص صريح (Plain Text)",
            title_en="Strip Formatting to Plain Text",
            category="clipboard",
            icon="clean",
            description_ar="إزالة كافة التنسيقات والألوان ورموز HTML من النص المنسوخ حالياً في الحافظة",
            description_en="Clears rich formatting and HTML tags from copied clipboard text.",
            aliases=["plain text", "تجريد التنسيق", "نص صريح", "نسخ بدون تنسيق"],
            keywords=["clipboard", "plain", "clean", "format"],
            input_types=[InputType.NONE],
            handler=ClipboardTools.copy_as_plain_text,
        ))

        # ----------------------------------------------------
        # 13. System Micro Utilities
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="system_identifiers",
            title_ar="نسخ معلومات الحاسوب السريعة (System Info)",
            title_en="Quick System Identifiers",
            category="system",
            icon="windows",
            description_ar="نسخ فوري بنقرة واحدة لاسم الحاسوب، اسم المستخدم، إصدار ويندوز، والـ IP المحلي",
            description_en="Quick one-click copy for Computer Name, User, OS, and Local IP.",
            aliases=["computer name", "username", "اسم الكمبيوتر", "اسم المستخدم", "ip المحلي"],
            keywords=["hostname", "user", "ip", "windows"],
            input_types=[InputType.NONE],
            handler=SystemTools.get_system_quick_identifiers,
        ))

        cls._register(QuickToolDefinition(
            id="env_variables_viewer",
            title_ar="مستعرض متغيرات البيئة (Environment Variables)",
            title_en="Windows Environment Variables",
            category="system",
            icon="settings",
            description_ar="استعراض والبحث في كافة متغيرات بيئة النظام ومسارات المستخدم (PATH, TEMP, etc.)",
            description_en="Inspect and search all Windows environment variables.",
            aliases=["env", "environment", "متغيرات البيئة", "مسارات النظام", "path var"],
            keywords=["env", "variables", "path", "temp", "userprofile"],
            input_types=[InputType.NONE],
            handler=SystemTools.get_environment_variables,
        ))

        cls._register(QuickToolDefinition(
            id="path_duplicate_inspector",
            title_ar="فاحص مسارات PATH وكشف التكرار والمسارات المفقودة",
            title_en="PATH Environment Inspector",
            category="system",
            icon="doctor",
            description_ar="تقسيم متغير PATH إلى مدخلات مستقلة، والتحقق من وجودها على القرص ورصد المكرر",
            description_en="Inspects PATH entries, validates existence, and detects duplicate paths.",
            aliases=["path", "فحص path", "مسارات مكررة", "تكرار path"],
            keywords=["path", "duplicates", "missing", "windows"],
            input_types=[InputType.NONE],
            handler=SystemTools.inspect_path_variable,
        ))

        # ----------------------------------------------------
        # 14. Naming & Slug Tools
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="filename_sanitizer",
            title_ar="معالج ومطهر أسماء الملفات (Filename Sanitizer)",
            title_en="Windows Filename Sanitizer",
            category="naming",
            icon="rename",
            description_ar="تحويل أي نص إلى اسم ملف صالح لنظام ويندوز مع إزالة الرموز الممنوعة والأسماء المحجوزة",
            description_en="Sanitizes strings into safe, valid Windows filenames.",
            aliases=["sanitize", "اسم ملف صالح", "تصحيح اسم الملف", "رموز ممنوعة"],
            keywords=["filename", "safe", "windows", "reserved"],
            input_types=[InputType.TEXT],
            handler=NamingTools.sanitize_filename,
        ))

        cls._register(QuickToolDefinition(
            id="slug_generator",
            title_ar="مُولّد الروابط المختصرة (URL Slug Generator)",
            title_en="Safe URL & File Slug Generator",
            category="naming",
            icon="globe",
            description_ar="تحويل العناوين والنصوص إلى روابط نصية نظيفة وآمنة تفصل بينها شرطات (Slug)",
            description_en="Converts titles into clean, lowercase URL-safe slugs.",
            aliases=["slug", "url slug", "سلوغ", "رابط نظيف", "تحويل العنوان الى رابط"],
            keywords=["slug", "url", "seo", "web"],
            input_types=[InputType.TEXT],
            handler=NamingTools.generate_slug,
        ))

        # ----------------------------------------------------
        # 15. List Laboratory
        # ----------------------------------------------------
        cls._register(QuickToolDefinition(
            id="list_set_operations",
            title_ar="عمليات المجموعات للقوائم (Set Operations)",
            title_en="List Intersect, Difference & Union",
            category="list",
            icon="organize",
            description_ar="مقارنة قائمتين لحساب: التقاطع المشترك، العناصر الموجودة في أ فقط، والاتحاد الكلي",
            description_en="Computes set intersection, differences, and union between two lists.",
            aliases=["intersect", "set", "تقاطع القوائم", "مقارنة قائمتين", "فرق القائمتين"],
            keywords=["set", "intersect", "difference", "union", "compare"],
            input_types=[InputType.TEXT],
            handler=ListTools.set_operations,
        ))

        cls._register(QuickToolDefinition(
            id="list_random_picker",
            title_ar="السحب والاختيار العشوائي من قائمة (Random Picker)",
            title_en="Random Item Picker & Shuffler",
            category="list",
            icon="shuffle",
            description_ar="اختيار فائز أو عنصر عشوائي من قائمة مدخلة، أو إعادة خلط وترتيب القائمة عشوائياً",
            description_en="Picks random items from a list or shuffles order.",
            aliases=["picker", "قرعة", "سحب عشوائي", "اختيار عشوائي", "shuffle list"],
            keywords=["random", "lottery", "picker", "sample", "shuffle"],
            input_types=[InputType.TEXT],
            handler=ListTools.pick_random,
        ))

        cls._initialized = True

    @classmethod
    def _register(cls, tool: QuickToolDefinition):
        cls._tools[tool.id] = tool

    @classmethod
    def get_all_tools(cls) -> List[QuickToolDefinition]:
        cls.initialize()
        return list(cls._tools.values())

    @classmethod
    def get_tool(cls, tool_id: str) -> Optional[QuickToolDefinition]:
        cls.initialize()
        return cls._tools.get(tool_id)

    @classmethod
    def get_tools_by_category(cls, category: str) -> List[QuickToolDefinition]:
        cls.initialize()
        if category in ("all", ""):
            return list(cls._tools.values())
        return [t for t in cls._tools.values() if t.category == category]

    @classmethod
    def search(cls, query: str, category: Optional[str] = None) -> List[QuickToolDefinition]:
        """
        Searches all tools using Arabic & English synonyms, aliases, IDs, and keywords.
        Returns relevance-sorted list of matching tools.
        """
        cls.initialize()
        clean = query.strip().lower()
        if not clean:
            return cls.get_tools_by_category(category or "all")

        # Standardize search terms
        import re
        tokens = re.findall(r"\w+", clean)

        matched: List[Tuple[QuickToolDefinition, int]] = []

        pool = list(cls._tools.values())
        if category and category not in ("all", "favorites"):
            pool = [t for t in pool if t.category == category]

        for tool in pool:
            score = 0

            # 1. Exact ID match
            if clean == tool.id.lower():
                score += 100
            elif clean in tool.id.lower():
                score += 40

            # 2. Exact Title match
            if clean in tool.title_ar.lower() or clean in tool.title_en.lower():
                score += 50

            # 3. Aliases match
            for alias in tool.aliases:
                if clean == alias.lower():
                    score += 60
                elif any(tok in alias.lower() for tok in tokens):
                    score += 25

            # 4. Keyword tokens
            for kw in tool.keywords:
                if clean in kw.lower():
                    score += 20
                elif any(tok in kw.lower() for tok in tokens):
                    score += 10

            # 5. Descriptions
            if any(tok in tool.description_ar.lower() for tok in tokens):
                score += 10
            if any(tok in tool.description_en.lower() for tok in tokens):
                score += 10

            if score > 0:
                matched.append((tool, score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in matched]

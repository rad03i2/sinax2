# -*- coding: utf-8 -*-
"""
Security Tool Registry for SINAX Privacy & Security Center.
Provides a unified catalog of all security and privacy tools, detailing
their requirements, safety levels, local/online execution badges,
and administrative privileges.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from app.services.privacy_security.models import SafetyLevel, SecurityToolDefinition


@dataclass
class ToolBadge:
    """Badge representation for tool UI presentation."""
    text_ar: str
    text_en: str
    bg_color: str
    fg_color: str
    icon: str


class SecurityToolRegistry:
    """Central registry for all tools in SINAX Privacy & Security Center."""

    _tools: Dict[str, SecurityToolDefinition] = {}
    _handlers: Dict[str, Any] = {}

    @classmethod
    def register_tool(cls, tool: SecurityToolDefinition, handler: Optional[Any] = None) -> None:
        if handler:
            tool.handler = handler
            cls._handlers[tool.id] = handler
        elif tool.handler:
            cls._handlers[tool.id] = tool.handler
        cls._tools[tool.id] = tool

    @classmethod
    def get_tool(cls, tool_id: str) -> Optional[SecurityToolDefinition]:
        return cls._tools.get(tool_id)

    @classmethod
    def get_handler(cls, tool_id: str) -> Optional[Any]:
        return cls._handlers.get(tool_id)

    @classmethod
    def get_all_tools(cls) -> List[SecurityToolDefinition]:
        return list(cls._tools.values())

    @classmethod
    def get_tools_by_category(cls, category: str) -> List[SecurityToolDefinition]:
        return [t for t in cls._tools.values() if t.category == category]


    @classmethod
    def get_badges_for_tool(cls, tool: SecurityToolDefinition) -> List[ToolBadge]:
        """Computes visual badges for a tool."""
        badges: List[ToolBadge] = []

        # 1. Local vs Online
        if tool.requires_network or tool.sends_data_externally:
            badges.append(ToolBadge(
                text_ar="أونلاين (Online)",
                text_en="Online",
                bg_color="#1E3A5F",
                fg_color="#38BDF8",
                icon="network"
            ))
        else:
            badges.append(ToolBadge(
                text_ar="محلي 100% (Local)",
                text_en="100% Local",
                bg_color="#132E22",
                fg_color="#34D399",
                icon="shield"
            ))

        # 2. Requires Admin
        if tool.requires_admin:
            badges.append(ToolBadge(
                text_ar="يتطلب مسؤول (Admin)",
                text_en="Requires Admin",
                bg_color="#451A03",
                fg_color="#FBBF24",
                icon="security"
            ))

        # 3. Modifies Files
        if tool.modifies_files:
            badges.append(ToolBadge(
                text_ar="يعدل ملفات",
                text_en="Modifies Files",
                bg_color="#3B1C38",
                fg_color="#F472B6",
                icon="rename"
            ))
        else:
            badges.append(ToolBadge(
                text_ar="فحص للقراءة فقط",
                text_en="Read Only",
                bg_color="#1E293B",
                fg_color="#94A3B8",
                icon="eye"
            ))

        # 4. Batch support
        if tool.supports_batch:
            badges.append(ToolBadge(
                text_ar="دعم الدفعات (Batch)",
                text_en="Batch Ready",
                bg_color="#1E293B",
                fg_color="#93C5FD",
                icon="duplicate"
            ))

        return badges


# Populate initial registry catalog
_CATALOG = [
    # 1. File Safety & Signatures
    SecurityToolDefinition(
        id="file_safety_inspector",
        title_ar="فاحص سلامة الملفات",
        title_en="File Safety Inspector",
        description_ar="فحص محلي للملفات وكشف الامتدادات المزدوجة والمطابقة مع البصمة السحرية Magic Bytes دون تنفيذ الملف.",
        description_en="Local inspection detecting double extensions and verifying magic bytes without execution.",
        category="file_safety",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=True,
        icon="eye"
    ),
    SecurityToolDefinition(
        id="defender_scanner",
        title_ar="فحص Microsoft Defender",
        title_en="Microsoft Defender Scan",
        description_ar="إجراء فحص مخصص عبر محرك الحماية الرسمي المدمج بنظام Windows دون إنشاء محرك وهمي.",
        description_en="Custom scan utilizing Windows native Microsoft Defender engine.",
        category="file_safety",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=True,
        icon="shield"
    ),
    SecurityToolDefinition(
        id="authenticode_verifier",
        title_ar="فاحص التواقيع الرقمية Authenticode",
        title_en="Digital Signature Verifier",
        description_ar="التحقق من صحة التواقيع الرقمية للبرامج والتطبيقات التنفيذية واستخراج بيانات شهادات X.509.",
        description_en="Verifies Authenticode signatures and inspects X.509 certificates.",
        category="digital_signature",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=True,
        icon="signature"
    ),

    # 2. Integrity & Monitoring
    SecurityToolDefinition(
        id="integrity_manifest_builder",
        title_ar="مانيفست سلامة المجلدات",
        title_en="Integrity Manifest Generator",
        description_ar="إنشاء وتدقيق بصمات SHA-256 الجماعية للمجلدات لكشف أي تعديل أو عبث غير مرخص.",
        description_en="Generates and verifies SHA-256 manifests to detect unauthorized changes.",
        category="integrity",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=True,
        icon="hash"
    ),
    SecurityToolDefinition(
        id="realtime_file_monitor",
        title_ar="مراقب تغييرات الملفات الحي",
        title_en="Realtime File Change Monitor",
        description_ar="مراقبة حية فورية ومستمرة للمجلدات الحساسة والتنبيه الفوري عند حدوث تعديل أو حذف.",
        description_en="Real-time monitoring of sensitive directories with change alerts.",
        category="file_monitoring",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=False,
        icon="doctor"
    ),

    # 3. Privacy & Sanitization
    SecurityToolDefinition(
        id="metadata_sanitizer",
        title_ar="منظف البيانات الوصفية والخصوصية",
        title_en="Privacy Metadata Sanitizer",
        description_ar="تطهير بيانات EXIF وإحداثيات GPS وبيانات مؤلفي PDF ومستندات Office بإنشاء نسخة آمنة منفصلة.",
        description_en="Sanitizes EXIF, GPS, author info from images, PDFs, and Office files into safe copies.",
        category="metadata_privacy",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=True,
        sends_data_externally=False,
        supports_batch=True,
        icon="clean"
    ),
    SecurityToolDefinition(
        id="safe_share_studio",
        title_ar="استوديو تجهيز الملفات للمشاركة الآمنة",
        title_en="Safe Share Studio",
        description_ar="خط أنابيب متكامل من 7 مراحل لتنظيف وفحص وتأمين الملفات قبل إرسالها للآخرين أو رفعها.",
        description_en="7-stage end-to-end pipeline preparing clean, verified, and safe copies for sharing.",
        category="safe_share",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=True,
        sends_data_externally=False,
        supports_batch=True,
        icon="share"
    ),
    SecurityToolDefinition(
        id="sensitive_data_scanner",
        title_ar="كاشف البيانات الحساسة والأسرار البرمجية",
        title_en="Sensitive Data & Secrets Scanner",
        description_ar="فحص محلي للمستندات والمشاريع البرمجية لكشف المفاتيح البرمجية والرموز السرية وبيانات PII مع التعتيم.",
        description_en="Local scanner detecting API keys, tokens, and PII with masked previews.",
        category="safe_share",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=True,
        icon="search"
    ),

    # 4. Encryption & Vaults
    SecurityToolDefinition(
        id="portable_vault_crypto",
        title_ar="خزنة SINAX المشفرة المحمولة (.sinaxvault)",
        title_en="Portable SINAX Vault",
        description_ar="تشفير قياسي موثوق بمعيار AES-256-GCM واشتقاق مفاتيح scrypt/Argon2id دون أي خوارزميات مخصصة.",
        description_en="Authenticated AES-256-GCM encryption with scrypt KDF for secure portable containers.",
        category="encryption_vault",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=True,
        sends_data_externally=False,
        supports_batch=True,
        icon="vault"
    ),
    SecurityToolDefinition(
        id="dpapi_windows_crypto",
        title_ar="تشفير Windows المقيد بالحساب (DPAPI)",
        title_en="Windows Account DPAPI Encryption",
        description_ar="تشفير سريع وسلس مقيد بحساب المستخدم الحالي بنظام Windows دون الحاجة لكلمة مرور.",
        description_en="Zero-password encryption bound securely to the active Windows account via DPAPI.",
        category="encryption_vault",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=True,
        sends_data_externally=False,
        supports_batch=True,
        icon="key"
    ),

    # 5. Secure Delete
    SecurityToolDefinition(
        id="secure_shredder",
        title_ar="الحذف الآمن الصادق علمياً",
        title_en="Media-Aware Secure Eraser",
        description_ar="كشف نوع وسيط التخزين (HDD مقابل SSD/NVMe) وتطبيق الحذف الآمن المناسب مع تحذيرات NIST 800-88.",
        description_en="Hardware-aware file shredder reporting honest flash wear-leveling limitations.",
        category="secure_delete",
        safety_level=SafetyLevel.REVIEW_NEEDED,
        requires_admin=False,
        requires_network=False,
        modifies_files=True,
        sends_data_externally=False,
        supports_batch=True,
        icon="shred"
    ),

    # 6. Windows Security & Telemetry
    SecurityToolDefinition(
        id="windows_security_dashboard",
        title_ar="لوحة حماية وأمان Windows",
        title_en="Windows Native Security Dashboard",
        description_ar="عرض الحالة الحية لميزات أمان Windows: Defender, SmartScreen, Ransomware Protection, BitLocker.",
        description_en="Live telemetry for Windows Defender, SmartScreen, CFA, and BitLocker status.",
        category="windows_security",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=False,
        icon="security"
    ),

    # 7. Advanced NTFS Tools
    SecurityToolDefinition(
        id="ads_stream_inspector",
        title_ar="محلل تدفقات NTFS البديلة (ADS)",
        title_en="NTFS Alternate Data Streams Inspector",
        description_ar="كشف التدفقات المخفية وإدارة وسم الإنترنت Zone.Identifier (Mark of the Web) بأمان وشفافية.",
        description_en="Enumerates hidden ADS streams and safely manages Zone.Identifier Mark of the Web.",
        category="advanced_tools",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=True,
        sends_data_externally=False,
        supports_batch=True,
        icon="tools"
    ),
    SecurityToolDefinition(
        id="ntfs_permissions_inspector",
        title_ar="فاحص أذونات وصلاحيات NTFS",
        title_en="NTFS Permissions & ACL Inspector",
        description_ar="قراءة وتدقيق قوائم التحكم بالوصول ACL وكشف الحسابات العامة (Everyone) وتصدير تقارير الصلاحيات.",
        description_en="Audits NTFS Access Control Lists and warns against insecure public write permissions.",
        category="advanced_tools",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=False,
        icon="tools"
    ),

    # 8. Password & Privacy Tools
    SecurityToolDefinition(
        id="clipboard_privacy_guard",
        title_ar="حارس خصوصية الحافظة (Clipboard)",
        title_en="Clipboard Privacy Guard",
        description_ar="مسح الحافظة تلقائياً بعد فترة زمنية محددة عند نسخ كلمات مرور أو معلومات حساسة.",
        description_en="Timed auto-clear of clipboard buffers when holding sensitive data or credentials.",
        category="passwords",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=False,
        icon="clipboard"
    ),

    # 9. Audit & Reports
    SecurityToolDefinition(
        id="privacy_audit_reporter",
        title_ar="مدقق وتقارير الخصوصية الشاملة",
        title_en="Comprehensive Privacy Audit Reporter",
        description_ar="توليد تقارير أمنية شاملة بصيغ HTML/JSON/TXT مع نمط حجب البيانات الحساسة (Privacy Mode).",
        description_en="Generates multi-format privacy audit reports with privacy masking mode enabled.",
        category="privacy_reports",
        safety_level=SafetyLevel.SAFE,
        requires_admin=False,
        requires_network=False,
        modifies_files=False,
        sends_data_externally=False,
        supports_batch=False,
        icon="chart"
    ),
]

for _tool in _CATALOG:
    SecurityToolRegistry.register_tool(_tool)

# -*- coding: utf-8 -*-
"""
Data Models for SINAX Maintenance & Repair Center.
Defines risk levels, severity ratings, diagnostic issues, maintenance actions,
repair plans, and before/after snapshot baselines.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RiskLevel(Enum):
    """Risk tier of a maintenance or repair action."""
    LEVEL_0_READ_ONLY = "level_0"       # Read-only diagnosis / inspection
    LEVEL_1_LOW_RISK = "level_1"        # Safe temp cleanup, harmless cache reset
    LEVEL_2_SYSTEM_CHANGE = "level_2"   # Disabling startup app, resetting network
    LEVEL_3_REQUIRES_RESTART = "level_3"# CHKDSK on C:, DISM servicing reboot
    LEVEL_4_ADVANCED_RECOVERY = "level_4" # Clean Boot, system restore, deep reset


class Severity(Enum):
    """Severity of a detected system issue."""
    INFO = "info"                       # Information only (معلومة)
    SUGGESTION = "suggestion"           # Maintenance recommendation (اقتراح)
    REVIEW_NEEDED = "review_needed"     # Needs user review (يحتاج مراجعة)
    WARNING = "warning"                 # Potential performance or storage impact (تحذير)
    CRITICAL_ISSUE = "critical"         # System corruption, disk failure, BSOD (مشكلة مكتشفة)


class ScanMode(Enum):
    """Scan depth for SINAX Maintenance Doctor."""
    QUICK = "quick"                     # Seconds to 1-2 minutes
    FULL = "full"                       # Comprehensive checks
    CUSTOM = "custom"                   # Selected diagnostic components


@dataclass
class DiagnosticIssue:
    """Represents an issue or observation detected by Maintenance Doctor."""
    id: str
    title_ar: str
    title_en: str
    category: str                       # e.g. "storage", "startup", "system_files", "network"
    severity: Severity
    description_ar: str
    description_en: str
    evidence: str                       # Why was this detected? (الدليل)
    suggested_action_id: Optional[str] = None
    action_label_ar: str = ""
    technical_details: str = ""
    timestamp: float = 0.0


@dataclass
class MaintenanceAction:
    """Represents an actionable maintenance or repair operation."""
    id: str
    title_ar: str
    title_en: str
    category: str
    description_ar: str
    description_en: str
    what_will_it_do_ar: str             # ما الذي سيفعله؟
    expected_outcome_ar: str            # ما المتوقع؟
    does_delete_user_files: bool = False # هل يحذف ملفات المستخدم الشخصية؟
    risk_level: RiskLevel = RiskLevel.LEVEL_1_LOW_RISK
    requires_admin: bool = False
    requires_restart: bool = False
    requires_internet: bool = False
    requires_ac_power: bool = False
    estimated_duration_sec: int = 10    # In seconds (e.g. 5, 60, 300)
    estimated_duration_str: str = "عدة ثوانٍ"
    is_reversible: bool = False
    backup_supported: bool = False
    affected_size_bytes: int = 0        # Size freed or processed
    handler_name: str = ""
    verification_handler_name: str = ""
    is_safe_default: bool = True        # Can be pre-checked in plan?


@dataclass
class MaintenancePlan:
    """Consolidated plan of recommended actions generated after a diagnostic scan."""
    session_id: str
    timestamp: float
    scan_mode: ScanMode
    issues_found: List[DiagnosticIssue] = field(default_factory=list)
    recommended_actions: List[MaintenanceAction] = field(default_factory=list)
    total_reclaimable_bytes: int = 0
    requires_restart_count: int = 0
    requires_admin_count: int = 0


@dataclass
class BeforeAfterSnapshot:
    """Snapshot measuring system metrics before and after maintenance operations."""
    timestamp: float
    free_space_c_bytes: int = 0
    temp_files_bytes: int = 0
    high_impact_startup_count: int = 0
    system_files_status: str = "لم يتم الفحص"
    pending_reboot: bool = False
    cpu_idle_percent: float = 0.0
    ram_usage_percent: float = 0.0
    disk_health_status: str = "Healthy"


@dataclass
class CBSLogEntry:
    """Parsed entry from Windows CBS.log regarding SFC operations."""
    timestamp_str: str
    status: str                         # "Repaired", "Cannot repair", "Info"
    file_path: str
    details: str


@dataclass
class CrashEvent:
    """Parsed application crash or unexpected shutdown event."""
    timestamp: float
    timestamp_str: str
    event_type: str                     # "AppCrash", "UnexpectedShutdown", "BSOD"
    app_name: str
    fault_module: str = ""
    exception_code: str = ""
    details: str = ""

# -*- coding: utf-8 -*-
"""
SINAX Privacy & Security Models
Defines data structures, enums, and descriptors for privacy, security,
authenticode signatures, encryption vaults, file integrity, and metadata sanitization.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class SafetyLevel(str, Enum):
    SAFE = "safe"
    REVIEW_NEEDED = "review_needed"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SignatureStatus(str, Enum):
    VALID = "valid"
    UNSIGNED = "unsigned"
    INVALID = "invalid"
    EXPIRED = "expired"
    UNTRUSTED = "untrusted"
    HASH_MISMATCH = "hash_mismatch"
    UNKNOWN = "unknown"


class StorageType(str, Enum):
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    UNKNOWN = "unknown"


class PrivacyPreset(str, Enum):
    SOCIAL = "social"          # Image/Video for social media (strip GPS, EXIF, tags)
    WORK_DOC = "work_doc"      # Office/PDF doc (strip author, revision history, comments)
    PUBLIC_PDF = "public_pdf"  # PDF for general public (strip metadata, annotations, attachments)
    TECH_SUPPORT = "support"   # Diagnostic file (strip username, IP, passwords, tokens)
    CODE_PROJECT = "project"   # Source code project (strip .env, keys, credentials, db dumps)


@dataclass
class FileSafetyReport:
    """Non-executable static safety report of a file."""
    path: str
    filename: str
    size_bytes: int
    extension: str
    detected_mime: str
    detected_type_name: str
    is_extension_mismatch: bool = False
    is_double_extension: bool = False
    real_executable_type: Optional[str] = None
    sha256: str = ""
    sha512: str = ""
    creation_time: str = ""
    modified_time: str = ""
    signature_status: SignatureStatus = SignatureStatus.UNKNOWN
    publisher: str = ""
    is_downloaded_from_internet: bool = False
    zone_id: Optional[int] = None
    alternate_data_streams: List[Dict[str, Any]] = field(default_factory=list)
    defender_scan_status: str = "لم يتم الفحص بعد"
    recommendations: List[str] = field(default_factory=list)
    safety_level: SafetyLevel = SafetyLevel.SAFE


@dataclass
class CertificateDetails:
    """X.509 Certificate details extracted from Authenticode signature."""
    subject: str = ""
    issuer: str = ""
    serial_number: str = ""
    valid_from: str = ""
    valid_to: str = ""
    thumbprint: str = ""
    signature_algorithm: str = ""
    is_timestamped: bool = False
    timestamp_time: str = ""
    chain_summary: List[str] = field(default_factory=list)


@dataclass
class VaultHeader:
    """Header metadata for encrypted .sinaxvault files."""
    magic: bytes = b"SINAXVLT"
    version: int = 1
    kdf_name: str = "scrypt"       # scrypt or argon2id
    kdf_salt: bytes = b""          # 32 bytes CSPRNG salt
    kdf_n: int = 16384             # CPU/memory cost
    kdf_r: int = 8                 # block size
    kdf_p: int = 1                 # parallelization
    cipher_name: str = "AES-256-GCM"
    nonce: bytes = b""             # 12 bytes CSPRNG nonce
    chunk_size: int = 1048576      # 1 MB streaming chunks
    total_files_count: int = 1
    is_directory_vault: bool = False
    auth_tag: bytes = b""          # 16 bytes authentication tag


@dataclass
class SensitiveMatch:
    """Match information for sensitive data scanner."""
    kind: str                      # email, phone, ipv4, api_key, secret_file, token
    file_path: str
    line_number: int
    masked_value: str              # sk-••••••••••••9A
    context_snippet: str
    severity: SafetyLevel = SafetyLevel.REVIEW_NEEDED


@dataclass
class IntegrityEntry:
    """Folder baseline integrity entry."""
    relative_path: str
    size_bytes: int
    sha256: str
    modified_time: float


@dataclass
class IntegrityDiff:
    """Comparison results between current folder state and baseline manifest."""
    unchanged_count: int = 0
    changed_count: int = 0
    deleted_count: int = 0
    new_count: int = 0
    changed_items: List[str] = field(default_factory=list)
    deleted_items: List[str] = field(default_factory=list)
    new_items: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return (self.changed_count > 0) or (self.deleted_count > 0) or (self.new_count > 0)

    @property
    def unchanged_files(self) -> List[Dict[str, Any]]:
        return [{"relative_path": f"item_{i}"} for i in range(self.unchanged_count)]

    @property
    def modified_files(self) -> List[Dict[str, Any]]:
        return [{"relative_path": p} for p in self.changed_items]

    @property
    def missing_files(self) -> List[Dict[str, Any]]:
        return [{"relative_path": p} for p in self.deleted_items]

    @property
    def new_files(self) -> List[Dict[str, Any]]:
        return [{"relative_path": p} for p in self.new_items]


@dataclass
class NTFSPermissionInfo:
    """NTFS Access Control List (ACL) summary."""
    owner: str = ""
    is_inherited: bool = True
    entries: List[Dict[str, Any]] = field(default_factory=list)
    has_everyone_write: bool = False
    has_unrestricted_modify: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass
class SecurityToolDefinition:
    """Registry definition for security and privacy tools."""
    id: str
    title_ar: str = ""
    title_en: str = ""
    description_ar: str = ""
    description_en: str = ""
    category: str = ""
    risk_level: SafetyLevel = SafetyLevel.SAFE
    safety_level: Optional[SafetyLevel] = None
    requires_admin: bool = False
    requires_network: bool = False
    modifies_files: bool = False
    sends_data_externally: bool = False
    data_leaving_description: str = ""   # e.g., "بصمة الهاش فقط"
    supports_batch: bool = True
    icon: str = "security"
    handler: Optional[Callable[..., Any]] = None

    def __post_init__(self):
        if self.safety_level is not None:
            self.risk_level = self.safety_level
        else:
            self.safety_level = self.risk_level

    @property
    def title(self) -> str:
        return self.title_ar or self.title_en

    @property
    def description(self) -> str:
        return self.description_ar or self.description_en



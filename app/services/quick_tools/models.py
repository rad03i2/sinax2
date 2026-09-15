# -*- coding: utf-8 -*-
"""
SINAX Quick Tools Data Models & Enums
Defines core data structures for tool metadata, input classification, safety levels,
and batch operation management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class InputType(Enum):
    """Categorizes incoming input from user, clipboard, or drag-and-drop."""
    NONE = "none"
    TEXT = "text"
    FILE = "file"
    FOLDER = "folder"
    URL = "url"
    JSON = "json"
    HASH = "hash"
    IMAGE = "image"
    NUMBER = "number"


class SafetyLevel(Enum):
    """Indicates operation safety and authorization requirements."""
    READ_ONLY = "read_only"          # Does not modify any disk data or settings
    MODIFIES_FILE = "modifies_file"  # Alters timestamps, attributes, or file contents
    SENSITIVE = "sensitive"          # Generates or inspects passwords/tokens (no history logged)
    REQUIRES_ADMIN = "requires_admin"# Requires elevated Windows UAC permissions


@dataclass
class QuickToolDefinition:
    """Complete metadata and execution hooks for a Quick Tool."""
    id: str
    title_ar: str
    title_en: str
    category: str                   # e.g., 'hash', 'text', 'encoding', 'file', 'dev', etc.
    description_ar: str
    description_en: str
    icon: str = "tools"
    aliases: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    input_types: List[InputType] = field(default_factory=lambda: [InputType.TEXT])
    output_type: str = "text"       # 'text', 'file', 'json', 'table', 'qr_image', 'none'
    supports_batch: bool = False
    modifies_source: bool = False
    safety_level: SafetyLevel = SafetyLevel.READ_ONLY
    requires_admin: bool = False
    handler: Optional[Callable[..., Any]] = None
    default_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchTaskItem:
    """Individual item in a batch operation queue."""
    index: int
    source_path: str
    status: str = "pending"         # 'pending', 'processing', 'completed', 'failed', 'skipped'
    result: Any = None
    error_message: str = ""
    duration_ms: float = 0.0


@dataclass
class BatchTaskResult:
    """Aggregated outcome of a batch execution."""
    total_items: int
    successful_count: int
    failed_count: int
    skipped_count: int
    total_duration_sec: float
    items: List[BatchTaskItem] = field(default_factory=list)
    export_path: str = ""

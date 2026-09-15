# -*- coding: utf-8 -*-
"""
SINAX Base Converter Interface
Unified abstract contract for all file converters in the SINAX ecosystem.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable


class BaseConverter(ABC):
    """
    Abstract base class defining the contract for all converters.
    """
    converter_id: str = "base"
    name_ar: str = "محول أساسي"
    category: str = "general"
    required_tools: List[str] = []

    def is_available(self) -> bool:
        """Checks whether all necessary dependencies/tools for this converter are present."""
        from app.services.conversion.dependency_manager import dependency_manager
        for tool in self.required_tools:
            if not dependency_manager.is_tool_available(tool):
                return False
        return True

    def get_missing_tools(self) -> List[str]:
        """Returns list of missing tool IDs needed by this converter."""
        from app.services.conversion.dependency_manager import dependency_manager
        missing = []
        for tool in self.required_tools:
            if not dependency_manager.is_tool_available(tool):
                missing.append(tool)
        return missing

    def validate_input(self, source_path: Path) -> Tuple[bool, str]:
        """Validates that the source file exists, is non-empty, and readable."""
        if not source_path.exists():
            return False, f"الملف المصدر غير موجود: {source_path.name}"
        if not source_path.is_file():
            return False, f"المسار ليس ملفاً: {source_path.name}"
        try:
            sz = source_path.stat().st_size
            if sz == 0:
                return False, f"الملف فارغ (الحجم 0 بايت): {source_path.name}"
        except Exception as e:
            return False, f"تعذر قراءة خصائص الملف: {e}"
        return True, "جاهز للتحويل"

    def get_options_schema(self) -> Dict[str, Any]:
        """
        Returns a dictionary schema describing available conversion options.
        Example schema format:
        {
            "quality": {"type": "int", "min": 1, "max": 100, "default": 85, "label": "الجودة"},
            "resize": {"type": "select", "options": ["original", "1080p", "720p"], "default": "original", "label": "الأبعاد"}
        }
        """
        return {}

    @abstractmethod
    def convert(
        self,
        source: Path,
        destination: Path,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        """
        Executes real conversion from source to destination.
        
        Args:
            source: Source file path
            destination: Target file path
            options: Conversion parameters
            progress_callback: Callback(percent 0.0..100.0, status_message)
            cancel_token: Callable returning True if cancellation was requested
            
        Returns:
            Tuple[bool, str]: (Success, Message or Error Details)
        """
        pass

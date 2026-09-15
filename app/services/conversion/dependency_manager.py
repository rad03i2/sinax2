# -*- coding: utf-8 -*-
"""
SINAX Dependency Manager
Detects installed external tools, standard Windows paths, and Python libraries.
Provides instructions, winget commands, and custom path configurations.
"""

import shutil
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("dependency_manager")

KNOWN_TOOL_LOCATIONS = {
    "ffmpeg": [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\Users\*\AppData\Local\Microsoft\WinGet\Packages\*\ffmpeg.exe",
        r"C:\Users\*\AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe",
    ],
    "soffice": [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ],
    "pandoc": [
        r"C:\Program Files\Pandoc\pandoc.exe",
        r"C:\Users\*\AppData\Local\Pandoc\pandoc.exe",
    ],
    "ebook-convert": [
        r"C:\Program Files\Calibre2\ebook-convert.exe",
        r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
    ],
    "magick": [
        r"C:\Program Files\ImageMagick-*\magick.exe",
        r"C:\Program Files (x86)\ImageMagick-*\magick.exe",
    ],
    "7z": [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ],
}

TOOL_METADATA = {
    "ffmpeg": {
        "name_ar": "FFmpeg (محرك الصوت والفيديو)",
        "description_ar": "محرك عالمي لمعالجة وضغط وتحويل جميع ملفات الصوت والفيديو والرسوم المتحركة.",
        "winget": "winget install Gyan.FFmpeg",
        "url": "https://ffmpeg.org/download.html",
        "category": "audio_video"
    },
    "soffice": {
        "name_ar": "LibreOffice (المستندات والعروض المكتبية)",
        "description_ar": "محرك مكتبي مفتوح المصدر لتحويل ملفات Word و PowerPoint و Excel و ODF بدقة عالية.",
        "winget": "winget install TheDocumentFoundation.LibreOffice",
        "url": "https://www.libreoffice.org/download/download/",
        "category": "office"
    },
    "pandoc": {
        "name_ar": "Pandoc (محول المستندات والنصوص)",
        "description_ar": "محول متقدم لمعالجة ملفات Markdown و HTML و Word و RTF.",
        "winget": "winget install JohnMacFarlane.Pandoc",
        "url": "https://pandoc.org/installing.html",
        "category": "documents"
    },
    "ebook-convert": {
        "name_ar": "Calibre (محرك الكتب الإلكترونية)",
        "description_ar": "أداة متخصصة لتحويل الكتب الإلكترونية EPUB و PDF والمجلات.",
        "winget": "winget install KovidGoyal.Calibre",
        "url": "https://calibre-ebook.com/download_windows",
        "category": "ebooks"
    },
    "magick": {
        "name_ar": "ImageMagick (محرك الصور المتقدم)",
        "description_ar": "محرك لمعالجة الصيغ النادرة والمعقدة للصور مثل RAW و HEIC و TIFF متعدد الصفحات.",
        "winget": "winget install ImageMagick.ImageMagick",
        "url": "https://imagemagick.org/script/download.php",
        "category": "images"
    },
    "7z": {
        "name_ar": "7-Zip (محرك الأرشيفات المضغوطة)",
        "description_ar": "أداة لضغط وفك حزم وأرشيفات 7z و ZIP و RAR عالية الكفاءة.",
        "winget": "winget install 7zip.7zip",
        "url": "https://www.7-zip.org/download.html",
        "category": "archives"
    },
}


class DependencyManager:
    """Singleton managing external binaries, python libraries, and their availability."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DependencyManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self._cache: Dict[str, Optional[Path]] = {}
        self._custom_paths = config.get("external_tools", {})
        self.refresh()

    def refresh(self):
        """Scans PATH and standard folders to detect all tools."""
        self._cache.clear()
        self._custom_paths = config.get("external_tools", {})

        for tool_id in TOOL_METADATA.keys():
            # 1. Check custom path in config first
            custom = self._custom_paths.get(tool_id)
            if custom and Path(custom).is_file() and Path(custom).suffix.lower() == ".exe":
                self._cache[tool_id] = Path(custom)
                continue

            # 2. Check system PATH
            which_res = shutil.which(tool_id)
            if which_res:
                self._cache[tool_id] = Path(which_res)
                continue

            # 3. Check known standard Windows installation directories
            found_path = None
            for pattern in KNOWN_TOOL_LOCATIONS.get(tool_id, []):
                matches = glob.glob(pattern)
                if matches:
                    found_path = Path(matches[0])
                    break

            # 4. Fallback for ffmpeg via imageio_ffmpeg bundled binary
            if not found_path and tool_id == "ffmpeg":
                try:
                    import imageio_ffmpeg
                    img_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    if img_exe and Path(img_exe).is_file():
                        found_path = Path(img_exe)
                except Exception:
                    pass

            self._cache[tool_id] = found_path

    def is_tool_available(self, tool_id: str) -> bool:
        """Returns True if the tool binary is discovered and executable."""
        return self._cache.get(tool_id) is not None

    def get_tool_path(self, tool_id: str) -> Optional[Path]:
        """Returns the full Path to the executable binary or None."""
        return self._cache.get(tool_id)

    def set_custom_path(self, tool_id: str, path_str: str) -> bool:
        """Saves a user-specified path to the tool binary."""
        p = Path(path_str)
        if p.is_file():
            self._custom_paths[tool_id] = str(p)
            config.set("external_tools", self._custom_paths, auto_save=True)
            self._cache[tool_id] = p
            logger.info(f"Configured custom path for {tool_id}: {p}")
            return True
        return False

    def get_tool_info(self, tool_id: str) -> Dict[str, Any]:
        """Returns UI and installation metadata for the given tool."""
        meta = TOOL_METADATA.get(tool_id, {
            "name_ar": tool_id,
            "description_ar": "",
            "winget": "",
            "url": "",
            "category": "general"
        }).copy()
        meta["is_available"] = self.is_tool_available(tool_id)
        meta["path"] = str(self.get_tool_path(tool_id)) if meta["is_available"] else None
        return meta

    def get_all_tools_summary(self) -> List[Dict[str, Any]]:
        """Returns summary list for settings or dependency dialogs."""
        return [self.get_tool_info(tid) for tid in TOOL_METADATA.keys()]


dependency_manager = DependencyManager()

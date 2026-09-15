# -*- coding: utf-8 -*-
"""
SINAX RenameRule Model
Defines the parameters and transformations for batch file renaming.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class RenameConfig:
    # Mode: 'preset', 'custom', 'replace', 'advanced'
    mode: str = "custom"
    
    # Pattern template e.g. "محاضرة {n}", "Lecture {n}", "{orig}_{date}"
    pattern: str = "ملف {n}"
    
    # Numbering configurations
    start_number: int = 1
    step: int = 1
    padding: int = 1  # 1 -> 1, 2 -> 01, 3 -> 001, 4 -> 0001
    number_system: str = "western"  # western, arabic_indic, arabic_alpha, arabic_words, english_upper, english_lower, english_words
    
    # Affixes
    prefix: str = ""
    suffix: str = ""
    
    # Text Replacement
    find_text: str = ""
    replace_text: str = ""
    case_sensitive_replace: bool = False
    
    # Text Removal
    remove_text: str = ""
    
    # Letter Casing (for Latin strings): 'none', 'upper', 'lower', 'title'
    case_transform: str = "none"
    
    # Date variables
    include_date: bool = False
    date_type: str = "modified"  # 'modified', 'created', 'current'
    date_format: str = "%Y-%m-%d"
    
    # Safety and Extensions
    keep_extension: bool = True
    custom_extension: str = ""
    
    # Sorting method before numbering:
    # 'name_asc', 'name_desc', 'date_asc', 'date_desc', 'size_asc', 'size_desc', 'smart_numeric'
    sort_by: str = "smart_numeric"

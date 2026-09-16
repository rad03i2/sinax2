# -*- coding: utf-8 -*-
"""
SINAX Core Constants
Defines global application metadata, category mappings, and system guards.
"""

import os
from pathlib import Path

APP_NAME = "SINAX"
APP_NAME_AR = "ساينكس"
APP_VERSION = "1.1.3"
APP_TAGLINE_AR = "نظام إدارة الحاسوب والملفات"
APP_DESCRIPTION = "نظام إدارة الحاسوب والملفات"
DEVELOPER_NAME = "رضوان عبد الهادي"
APP_COPYRIGHT = "© 2026 SINAX — برمجة وتطوير رضوان عبد الهادي. جميع الحقوق محفوظة."

# Windows forbidden filename characters
WINDOWS_RESERVED_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

# Critical Windows System Paths requiring strict confirmation
SYSTEM_PATHS = [
    Path(os.environ.get('WINDIR', 'C:\\Windows')).resolve(),
    Path(os.environ.get('ProgramFiles', 'C:\\Program Files')).resolve(),
    Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')).resolve(),
    Path(os.environ.get('SystemRoot', 'C:\\Windows')).resolve(),
]

# File Category Definitions with Arabic names, extensions, and colors
FILE_CATEGORIES = {
    'all': {
        'label_ar': 'جميع الملفات',
        'extensions': set(),
        'color': '#0078D4'
    },
    'pdf': {
        'label_ar': 'ملفات PDF',
        'extensions': {'.pdf'},
        'color': '#E53935'
    },
    'images': {
        'label_ar': 'الصور',
        'extensions': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.ico', '.raw', '.heic'},
        'color': '#43A047'
    },
    'videos': {
        'label_ar': 'الفيديوهات',
        'extensions': {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'},
        'color': '#1E88E5'
    },
    'audio': {
        'label_ar': 'الصوتيات',
        'extensions': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'},
        'color': '#FB8C00'
    },
    'word': {
        'label_ar': 'مستندات Word',
        'extensions': {'.docx', '.doc', '.dotx', '.rtf'},
        'color': '#1565C0'
    },
    'excel': {
        'label_ar': 'جداول Excel',
        'extensions': {'.xlsx', '.xls', '.csv', '.xlsm', '.xltx'},
        'color': '#2E7D32'
    },
    'powerpoint': {
        'label_ar': 'عروض PowerPoint',
        'extensions': {'.pptx', '.ppt', '.ppsx', '.potx'},
        'color': '#D84315'
    },
    'archives': {
        'label_ar': 'الملفات المضغوطة',
        'extensions': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.iso'},
        'color': '#8E24AA'
    },
    'text': {
        'label_ar': 'ملفات نصية',
        'extensions': {'.txt', '.md', '.log', '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg'},
        'color': '#546E7A'
    },
    'other': {
        'label_ar': 'ملفات أخرى',
        'extensions': set(),
        'color': '#757575'
    }
}

EXTENSION_TO_CATEGORY = {}
for cat_key, cat_data in FILE_CATEGORIES.items():
    if cat_key != 'all' and cat_key != 'other':
        for ext in cat_data['extensions']:
            EXTENSION_TO_CATEGORY[ext.lower()] = cat_key

# Number Systems
NUMBER_SYSTEMS = {
    'western': 'أرقام غربية (1, 2, 3...)',
    'arabic_indic': 'أرقام مشرقية عربية (١, ٢, ٣...)',
    'arabic_alpha': 'أبجدية عربية (أ, ب, ج, د...)',
    'arabic_words': 'أعداد لفظية عربية (الأول, الثاني, الثالث...)',
    'english_upper': 'حروف إنجليزية كبيرة (A, B, C...)',
    'english_lower': 'حروف إنجليزية صغيرة (a, b, c...)',
    'english_words': 'أعداد لفظية إنجليزية (First, Second...)',
}

ARABIC_INDIC_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

ARABIC_ALPHABET = [
    'أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش',
    'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'هـ', 'و', 'ي'
]

ARABIC_ORDINALS = [
    'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس', 'السابع', 'الثامن', 'التاسع', 'العاشر',
    'الحادي عشر', 'الثاني عشر', 'الثالث عشر', 'الرابع عشر', 'الخامس عشر',
    'السادس عشر', 'السابع عشر', 'الثامن عشر', 'التاسع عشر', 'العشرون',
    'الحادي والعشرون', 'الثاني والعشرون', 'الثالث والعشرون', 'الرابع والعشرون', 'الخامس والعشرون',
    'السادس والعشرون', 'السابع والعشرون', 'الثامن والعشرون', 'التاسع والعشرون', 'الثلاثون',
    'الحادي والثلاثون', 'الثاني والثلاثون', 'الثالث والثلاثون', 'الرابع والثلاثون', 'الخامس والثلاثون',
    'السادس والثلاثون', 'السابع والثلاثون', 'الثامن والثلاثون', 'التاسع والثلاثون', 'الأربعون',
    'الحادي والأربعون', 'الثاني والأربعون', 'الثالث والأربعون', 'الرابع والأربعون', 'الخامس والأربعون',
    'السادس والأربعون', 'السابع والأربعون', 'الثامن والأربعون', 'التاسع والأربعون', 'الخمسون'
]

ENGLISH_ORDINALS = [
    'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth',
    'Eleventh', 'Twelfth', 'Thirteenth', 'Fourteenth', 'Fifteenth', 'Sixteenth', 'Seventeenth', 'Eighteenth', 'Nineteenth', 'Twentieth',
    'Twenty-First', 'Twenty-Second', 'Twenty-Third', 'Twenty-Fourth', 'Twenty-Fifth', 'Twenty-Sixth', 'Twenty-Seventh', 'Twenty-Eighth', 'Twenty-Ninth', 'Thirtieth'
]

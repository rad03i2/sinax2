# -*- coding: utf-8 -*-
"""
File Reputation Provider for SINAX Privacy & Security.
Lookup reputation using local SHA-256 hashes only. Never uploads files automatically.
Requires explicit double confirmation and user-provided API keys (stored safely via DPAPI).
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from app.services.privacy_security.providers.encryption_provider import WindowsDpapiProvider

SETTINGS_FILE = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".sinax", "reputation_keys.bin")


class FileReputationProvider:
    """Base reputation service interface."""

    def check_hash(self, sha256_hash: str) -> Tuple[bool, str, Dict[str, Any]]:
        raise NotImplementedError


class VirusTotalProvider(FileReputationProvider):
    """
    Privacy-first VirusTotal API v3 integration.
    Only queries the SHA-256 hash. Zero file transmission without separate user opt-in.
    """

    @classmethod
    def save_api_key(cls, api_key: str):
        """Encrypts and stores API key using Windows DPAPI."""
        try:
            cipher = WindowsDpapiProvider.protect(api_key.strip().encode("utf-8"), description="SINAX VT API Key")
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "wb") as f:
                f.write(cipher)
        except Exception:
            pass

    @classmethod
    def get_api_key(cls) -> str:
        """Retrieves and decrypts the API key from DPAPI storage."""
        if not os.path.exists(SETTINGS_FILE):
            return ""
        try:
            with open(SETTINGS_FILE, "rb") as f:
                cipher = f.read()
            return WindowsDpapiProvider.unprotect(cipher).decode("utf-8")
        except Exception:
            return ""

    def check_hash(self, sha256_hash: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Queries VirusTotal API v3 using SHA-256 hash only."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "مفتاح API الخاص بـ VirusTotal غير مُعرّف (يمكنك إدخاله في الإعدادات)", {}

        url = f"https://www.virustotal.com/api/v3/files/{sha256_hash.lower()}"
        headers = {
            "x-apikey": api_key,
            "User-Agent": "SINAX-Client/1.0"
        }

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    attr = data.get("data", {}).get("attributes", {})
                    stats = attr.get("last_analysis_stats", {})
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    undetected = stats.get("undetected", 0)
                    harmless = stats.get("harmless", 0)
                    total = malicious + suspicious + undetected + harmless

                    summary = {
                        "malicious": malicious,
                        "suspicious": suspicious,
                        "undetected": undetected,
                        "total_engines": total,
                        "names": attr.get("names", [])[:3],
                        "permalink": f"https://www.virustotal.com/gui/file/{sha256_hash}",
                    }

                    if malicious == 0 and suspicious == 0:
                        msg = f"معروف ومصنف سليم (0 كشف من أصل {total} محرك فحص)"
                    else:
                        msg = f"تم الإبلاغ عن {malicious} كشف مشبوه من أصل {total} محرك فحص"
                    return True, msg, summary

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, "لم يتم العثور على تقرير سابق لهذا الملف في قاعدة البيانات.", {"not_found": True}
            elif e.code == 401 or e.code == 403:
                return False, "مفتاح VirusTotal API غير صالح أو غير مصرح له.", {}
            elif e.code == 429:
                return False, "تم تجاوز الحد المسموح للاستعلامات المجانية (Rate Limit Exceeded).", {}
            return False, f"خطأ من المزود الخارجي: كود {e.code}", {}
        except Exception as e:
            return False, f"تعذر الاتصال بخدمة التحقق: {str(e)}", {}

        return False, "استجابة غير متوقعة من المزود", {}

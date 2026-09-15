# -*- coding: utf-8 -*-
"""
SINAX Web Utility Tools
Domain extractor, safe HTML tag stripper, basic code minifier, and User-Agent parser.
"""

import html
import re
from typing import Any, Dict, Optional
import urllib.parse


class WebTools:
    """Offline web format manipulation and string analyzers."""

    @staticmethod
    def extract_domain(url_str: str) -> Dict[str, str]:
        """Extracts protocol, hostname, port, and apex domain from URL."""
        clean = url_str.strip()
        if not clean.startswith(("http://", "https://")):
            clean = "http://" + clean

        parsed = urllib.parse.urlsplit(clean)
        hostname = parsed.hostname or ""

        # Extract probable apex domain
        parts = hostname.split(".")
        if len(parts) >= 2:
            apex = ".".join(parts[-2:])
        else:
            apex = hostname

        return {
            "full_host": hostname,
            "apex_domain": apex,
            "scheme": parsed.scheme,
            "path": parsed.path or "/",
        }

    @staticmethod
    def html_to_plain_text(html_content: str) -> str:
        """Safely removes HTML tags, scripts, and decodes character entities."""
        # Strip script and style blocks
        clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", " ", clean)
        # Decode entities
        clean = html.unescape(clean)
        # Normalize whitespace
        clean = re.sub(r"[ \t]+", " ", clean)
        clean = re.sub(r"\n\s*\n+", "\n\n", clean)
        return clean.strip()

    @staticmethod
    def simple_minify_css(css_text: str) -> str:
        """Strips CSS comments and redundant whitespace."""
        clean = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
        clean = re.sub(r"\s+", " ", clean)
        clean = re.sub(r"\s*([\{\};:,])\s*", r"\1", clean)
        return clean.strip()

    @staticmethod
    def parse_user_agent(ua_string: str) -> Dict[str, str]:
        """Heuristically inspects browser, operating system, and architecture from UA string."""
        ua = ua_string.strip()
        browser = "غير معروف"
        os_name = "غير معروف"

        # OS detection
        if "Windows NT 10.0" in ua:
            os_name = "Windows 10 / Windows 11"
        elif "Windows" in ua:
            os_name = "Windows"
        elif "Macintosh" in ua or "Mac OS X" in ua:
            os_name = "macOS"
        elif "Android" in ua:
            os_name = "Android"
        elif "iPhone" in ua or "iPad" in ua:
            os_name = "iOS"
        elif "Linux" in ua:
            os_name = "Linux"

        # Browser detection
        if "Edg/" in ua:
            browser = "Microsoft Edge"
        elif "Chrome/" in ua and "Chromium" not in ua:
            browser = "Google Chrome"
        elif "Firefox/" in ua:
            browser = "Mozilla Firefox"
        elif "Safari/" in ua and "Chrome" not in ua:
            browser = "Apple Safari"
        elif "OPR/" in ua or "Opera" in ua:
            browser = "Opera"

        return {
            "browser": browser,
            "os": os_name,
            "raw_user_agent": ua,
        }

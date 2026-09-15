# -*- coding: utf-8 -*-
"""
SINAX Developer Micro Tools
JSON / XML / CSV formatters, converters, validators with line/column errors,
URL & Query builders, HTTP header parsers, JWT claim inspector, Color converter, and Cron helpers.
"""

import base64
import csv
from datetime import datetime, timezone
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import xml.dom.minidom
import xml.etree.ElementTree as ET


class DeveloperTools:
    """Micro tools and formatters tailored for software developers."""

    # --- JSON Formatter & Validator ---
    @staticmethod
    def format_json(raw_json: str, indent: int = 2, minify: bool = False) -> Dict[str, Any]:
        """Formats or minifies JSON string, returning exact error location if invalid."""
        clean = raw_json.strip()
        if not clean:
            return {"is_valid": False, "error": "النص فارغ", "result": ""}

        try:
            parsed = json.loads(clean)
            if minify:
                formatted = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
            else:
                formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)
            return {
                "is_valid": True,
                "error": "",
                "line": None,
                "column": None,
                "result": formatted,
            }
        except json.JSONDecodeError as e:
            return {
                "is_valid": False,
                "error": f"خطأ في الصياغة (سطر {e.lineno}، عمود {e.colno}): {e.msg}",
                "line": e.lineno,
                "column": e.colno,
                "result": clean,
            }

    # --- XML Formatter ---
    @staticmethod
    def format_xml(raw_xml: str, minify: bool = False) -> Dict[str, Any]:
        """Validates and formats XML string."""
        clean = raw_xml.strip()
        if not clean:
            return {"is_valid": False, "error": "النص فارغ", "result": ""}

        try:
            elem = ET.fromstring(clean)
            if minify:
                result = re.sub(r">\s+<", "><", clean)
                return {"is_valid": True, "error": "", "result": result}
            else:
                rough_string = ET.tostring(elem, encoding="utf-8")
                reparsed = xml.dom.minidom.parseString(rough_string)
                return {
                    "is_valid": True,
                    "error": "",
                    "result": reparsed.toprettyxml(indent="  "),
                }
        except ET.ParseError as e:
            return {
                "is_valid": False,
                "error": f"خطأ XML: {e}",
                "result": clean,
            }

    # --- CSV Tools ---
    @staticmethod
    def convert_csv_delimiter(csv_text: str, from_delim: str = ",", to_delim: str = ";") -> str:
        """Converts delimiters between comma, semicolon, tab, or pipe."""
        reader = csv.reader(io.StringIO(csv_text), delimiter=from_delim)
        out = io.StringIO()
        writer = csv.writer(out, delimiter=to_delim)
        for row in reader:
            writer.writerow(row)
        return out.getvalue()

    @staticmethod
    def csv_to_json(csv_text: str, delimiter: str = ",") -> str:
        """Converts CSV text to JSON array of objects."""
        reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
        rows = list(reader)
        return json.dumps(rows, indent=2, ensure_ascii=False)

    @staticmethod
    def json_to_csv(json_text: str, delimiter: str = ",") -> str:
        """Converts JSON array of objects to CSV."""
        data = json.loads(json_text)
        if not isinstance(data, list) or not data:
            return ""
        headers = list(data[0].keys())
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=headers, delimiter=delimiter)
        writer.writeheader()
        for item in data:
            writer.writerow(item)
        return out.getvalue()

    # --- URL Parser & Query String Builder ---
    @staticmethod
    def parse_url(url_str: str) -> Dict[str, Any]:
        """Breaks down a URL into its constituent components."""
        parsed = urllib.parse.urlsplit(url_str.strip())
        query_dict = urllib.parse.parse_qs(parsed.query)

        return {
            "scheme": parsed.scheme or "http",
            "netloc": parsed.netloc,
            "hostname": parsed.hostname or "",
            "port": parsed.port or (443 if parsed.scheme == "https" else 80),
            "path": parsed.path or "/",
            "query_raw": parsed.query,
            "query_params": query_dict,
            "fragment": parsed.fragment,
        }

    # --- JWT Inspector ---
    @staticmethod
    def inspect_jwt(token: str) -> Dict[str, Any]:
        """
        Decodes unencrypted JWT headers and payload locally.
        Explicitly warns that decode is NOT signature verification.
        """
        parts = token.strip().split(".")
        if len(parts) < 2:
            return {"is_valid": False, "error": "رمز JWT غير صالح (يجب أن يحتوي على قسمين على الأقل مفصولين بنقطة)"}

        def _b64_decode(s: str) -> str:
            padded = s + "=" * ((4 - len(s) % 4) % 4)
            return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")

        try:
            header_json = _b64_decode(parts[0])
            payload_json = _b64_decode(parts[1])

            header = json.loads(header_json)
            payload = json.loads(payload_json)

            # Human friendly expiration
            exp = payload.get("exp")
            exp_date = "غير محدد"
            if isinstance(exp, (int, float)):
                exp_date = datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            return {
                "is_valid": True,
                "header": header,
                "payload": payload,
                "algorithm": header.get("alg", "Unknown"),
                "token_type": header.get("typ", "JWT"),
                "expiration": exp_date,
                "warning": "تنبيه أمني: تم فك تشفير المحتوى محلياً (Decode) لمعاينة البيانات. لا يعني هذا التحقق من صحة التوقيع الرقمي (Signature Verification).",
            }
        except Exception as e:
            return {"is_valid": False, "error": f"فشل قراءة حمولة JWT: {e}"}

    # --- Color Converter ---
    @staticmethod
    def convert_color(hex_color: str) -> Dict[str, str]:
        """Converts HEX color string to RGB, RGBA, and HSL formats."""
        clean = hex_color.strip().lstrip("#")
        if len(clean) == 3:
            clean = "".join(c * 2 for c in clean)
        if len(clean) != 6:
            return {"error": "تنسيق HEX غير صالح (مثال: #3B82F6)"}

        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)

        # HSL calculation
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        mx = max(rf, gf, bf)
        mn = min(rf, gf, bf)
        df = mx - mn

        l = (mx + mn) / 2.0
        if df == 0:
            h = s = 0.0
        else:
            s = df / (2.0 - mx - mn) if l > 0.5 else df / (mx + mn)
            if mx == rf:
                h = (gf - bf) / df + (6.0 if gf < bf else 0.0)
            elif mx == gf:
                h = (bf - rf) / df + 2.0
            else:
                h = (rf - gf) / df + 4.0
            h /= 6.0

        return {
            "hex": f"#{clean.upper()}",
            "rgb": f"rgb({r}, {g}, {b})",
            "rgba": f"rgba({r}, {g}, {b}, 1.0)",
            "hsl": f"hsl({round(h * 360)}, {round(s * 100)}%, {round(l * 100)}%)",
        }

    # --- CSS Unit Converter ---
    @staticmethod
    def convert_css_units(val: float, unit_from: str = "px", base_font_px: float = 16.0) -> Dict[str, str]:
        """Converts CSS sizing units relative to root font size."""
        if unit_from == "px":
            px = val
        elif unit_from in ("rem", "em"):
            px = val * base_font_px
        elif unit_from == "%":
            px = (val / 100.0) * base_font_px
        else:
            px = val

        return {
            "px": f"{px:,.2f}px",
            "rem": f"{px / base_font_px:,.3f}rem",
            "em": f"{px / base_font_px:,.3f}em",
            "percent": f"{(px / base_font_px) * 100:,.1f}%",
        }

    # --- Cron Expression Helper ---
    @staticmethod
    def explain_cron(cron_expr: str) -> str:
        """Explains a 5-part cron expression in friendly Arabic."""
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return "تعبير Cron غير قياسي (يجب أن يتكون من 5 حقول: دقيقة، ساعة، يوم الشهر، الشهر، يوم الأسبوع)"

        m, h, dom, mon, dow = parts
        if m == "*" and h == "*":
            return "يعمل كل دقيقة على مدار الساعة."
        elif m.startswith("*/") and h == "*":
            return f"يعمل كل {m[2:]} دقيقة باستمرار."
        elif h.startswith("*/") and m == "0":
            return f"يعمل كل {h[2:]} ساعة في بداية الساعة."
        elif dom == "*" and mon == "*" and dow == "*":
            return f"يعمل يومياً عند الساعة {h}:{m.zfill(2)}."
        return f"تعبير Cron مخصص: [دقيقة: {m} | ساعة: {h} | يوم: {dom} | شهر: {mon} | أسبوع: {dow}]"

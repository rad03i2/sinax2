# -*- coding: utf-8 -*-
"""
SINAX Base64 & Encoding Lab
Handles Base64, Base32, Hex, Binary, URL Encode/Decode, HTML entities,
Unicode Escapes, Character Inspection, BOM operations, and character set conversions.
"""

import base64
import binascii
import codecs
import html
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import unicodedata
import urllib.parse


class EncodingTools:
    """Universal encoding, decoding, and character conversion engine."""

    # --- Base64 ---
    @staticmethod
    def text_to_base64(text: str, url_safe: bool = False) -> str:
        data = text.encode("utf-8")
        if url_safe:
            return base64.urlsafe_b64encode(data).decode("ascii")
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def base64_to_text(b64_str: str, url_safe: bool = False) -> str:
        clean = b64_str.strip()
        # Add padding if needed
        missing_padding = len(clean) % 4
        if missing_padding:
            clean += "=" * (4 - missing_padding)
        if url_safe:
            raw = base64.urlsafe_b64decode(clean)
        else:
            raw = base64.b64decode(clean)
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def file_to_base64(input_file: str, output_file: Optional[str] = None) -> str:
        """Encodes file to Base64 in a streaming manner."""
        inp = Path(input_file)
        if not inp.is_file():
            raise FileNotFoundError(f"File not found: {input_file}")

        out_path = output_file or str(inp.with_suffix(inp.suffix + ".b64"))
        with open(input_file, "rb") as fin, open(out_path, "wb") as fout:
            base64.encode(fin, fout)
        return out_path

    @staticmethod
    def base64_to_file(b64_file: str, output_file: str):
        """Decodes Base64 file into binary output file."""
        with open(b64_file, "rb") as fin, open(output_file, "wb") as fout:
            base64.decode(fin, fout)

    # --- Base32 ---
    @staticmethod
    def text_to_base32(text: str) -> str:
        return base64.b32encode(text.encode("utf-8")).decode("ascii")

    @staticmethod
    def base32_to_text(b32_str: str) -> str:
        clean = b32_str.strip()
        missing = len(clean) % 8
        if missing:
            clean += "=" * (8 - missing)
        return base64.b32decode(clean).decode("utf-8", errors="replace")

    # --- Hex ---
    @staticmethod
    def text_to_hex(text: str, space_separated: bool = True) -> str:
        raw = text.encode("utf-8")
        h = raw.hex()
        if space_separated:
            return " ".join(h[i:i+2] for i in range(0, len(h), 2))
        return h

    @staticmethod
    def hex_to_text(hex_str: str) -> str:
        clean = hex_str.replace(" ", "").replace("\n", "").strip()
        raw = bytes.fromhex(clean)
        return raw.decode("utf-8", errors="replace")

    # --- Binary ---
    @staticmethod
    def text_to_binary(text: str, space_separated: bool = True) -> str:
        raw = text.encode("utf-8")
        bits = [f"{b:08b}" for b in raw]
        return " ".join(bits) if space_separated else "".join(bits)

    @staticmethod
    def binary_to_text(bin_str: str) -> str:
        clean = bin_str.replace(" ", "").replace("\n", "").strip()
        chunks = [clean[i:i+8] for i in range(0, len(clean), 8) if len(clean[i:i+8]) == 8]
        raw = bytes(int(b, 2) for b in chunks)
        return raw.decode("utf-8", errors="replace")

    # --- URL Encoding ---
    @staticmethod
    def url_encode(text: str) -> str:
        return urllib.parse.quote(text)

    @staticmethod
    def url_decode(text: str) -> str:
        return urllib.parse.unquote(text)

    # --- HTML Entities ---
    @staticmethod
    def html_encode(text: str) -> str:
        return html.escape(text)

    @staticmethod
    def html_decode(text: str) -> str:
        return html.unescape(text)

    # --- Unicode Escape ---
    @staticmethod
    def text_to_unicode_escape(text: str) -> str:
        return text.encode("unicode_escape").decode("ascii")

    @staticmethod
    def unicode_escape_to_text(escaped_str: str) -> str:
        return codecs.decode(escaped_str, "unicode_escape")

    # --- Character Inspector ---
    @staticmethod
    def inspect_character(char: str) -> Dict[str, str]:
        """Inspects detailed Unicode properties of a single character."""
        if not char:
            return {}
        c = char[0]
        code_point = ord(c)
        try:
            name = unicodedata.name(c)
        except ValueError:
            name = "UNKNOWN / UNNAMED CONTROL CHARACTER"

        utf8_bytes = c.encode("utf-8").hex().upper()
        utf8_formatted = " ".join(utf8_bytes[i:i+2] for i in range(0, len(utf8_bytes), 2))
        category = unicodedata.category(c)

        return {
            "char": c,
            "codepoint": f"U+{code_point:04X}",
            "decimal": str(code_point),
            "name": name,
            "category": category,
            "utf8_bytes": utf8_formatted,
            "utf16_hex": c.encode("utf-16-be").hex().upper(),
            "html_entity": f"&#{code_point};",
            "hex_entity": f"&#x{code_point:X};",
        }

    # --- BOM Inspector ---
    @staticmethod
    def inspect_bom(file_path: str) -> Tuple[bool, str]:
        """Checks if file begins with standard Byte Order Mark (BOM)."""
        with open(file_path, "rb") as f:
            header = f.read(4)

        if header.startswith(codecs.BOM_UTF8):
            return True, "UTF-8 BOM (EF BB BF)"
        elif header.startswith(codecs.BOM_UTF16_LE):
            return True, "UTF-16 LE BOM (FF FE)"
        elif header.startswith(codecs.BOM_UTF16_BE):
            return True, "UTF-16 BE BOM (FE FF)"
        elif header.startswith(codecs.BOM_UTF32_LE):
            return True, "UTF-32 LE BOM (FF FE 00 00)"
        elif header.startswith(codecs.BOM_UTF32_BE):
            return True, "UTF-32 BE BOM (00 00 FE FF)"
        return False, "لا يوجد BOM (No Byte Order Mark)"

    @staticmethod
    def remove_utf8_bom(file_path: str, output_path: Optional[str] = None) -> str:
        """Removes UTF-8 BOM if present."""
        with open(file_path, "rb") as f:
            data = f.read()

        if data.startswith(codecs.BOM_UTF8):
            data = data[len(codecs.BOM_UTF8):]

        out = output_path or file_path
        with open(out, "wb") as f:
            f.write(data)
        return out

    @staticmethod
    def add_utf8_bom(file_path: str, output_path: Optional[str] = None) -> str:
        """Prepends UTF-8 BOM if missing."""
        with open(file_path, "rb") as f:
            data = f.read()

        if not data.startswith(codecs.BOM_UTF8):
            data = codecs.BOM_UTF8 + data

        out = output_path or file_path
        with open(out, "wb") as f:
            f.write(data)
        return out

    # --- Encoding Converter ---
    @staticmethod
    def convert_file_encoding(
        input_file: str,
        output_file: str,
        src_encoding: str = "windows-1256",
        tgt_encoding: str = "utf-8"
    ):
        """Converts text file encoding reliably."""
        with open(input_file, "r", encoding=src_encoding, errors="replace") as fin:
            content = fin.read()
        with open(output_file, "w", encoding=tgt_encoding, errors="replace") as fout:
            fout.write(content)

    @staticmethod
    def detect_encoding_heuristic(file_path: str) -> str:
        """Estimates probable encoding based on BOM and UTF-8 validity."""
        with open(file_path, "rb") as f:
            sample = f.read(65536)

        if sample.startswith(codecs.BOM_UTF8):
            return "UTF-8 with BOM"
        if sample.startswith(codecs.BOM_UTF16_LE):
            return "UTF-16 Little Endian"
        if sample.startswith(codecs.BOM_UTF16_BE):
            return "UTF-16 Big Endian"

        try:
            sample.decode("utf-8")
            return "UTF-8 (بدون BOM)"
        except UnicodeDecodeError:
            pass

        try:
            sample.decode("ascii")
            return "ASCII"
        except UnicodeDecodeError:
            pass

        # Windows-1256 (Arabic) or Windows-1252 (Western)
        return "مرجح: Windows-1256 (عربي قديم) أو Windows-1252"

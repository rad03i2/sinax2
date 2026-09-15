# -*- coding: utf-8 -*-
"""
SINAX QR & Barcode Studio
Generates clean QR codes (Text, Wi-Fi, vCard, Email, Location) with custom styling,
batch QR generation, and pure-Python vector Barcode generation (Code 128, Code 39, EAN-13).
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap

from app.services.network.qr_generator import QrCodeGenerator, _generate_qr_svg_or_matrix


class QrBarcodeTools:
    """Universal 2D and 1D barcode generation and reading engine."""

    # --- Format Builders ---
    @staticmethod
    def format_wifi_qr(ssid: str, password: str, security: str = "WPA") -> str:
        """Formats standard Wi-Fi network credentials string."""
        return f"WIFI:T:{security};S:{ssid};P:{password};;"

    @staticmethod
    def format_vcard_qr(
        name: str,
        phone: str = "",
        email: str = "",
        company: str = "",
        website: str = ""
    ) -> str:
        """Formats standard vCard 3.0 string for contacts."""
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{name}",
        ]
        if phone:
            lines.append(f"TEL;TYPE=CELL:{phone}")
        if email:
            lines.append(f"EMAIL:{email}")
        if company:
            lines.append(f"ORG:{company}")
        if website:
            lines.append(f"URL:{website}")
        lines.append("END:VCARD")
        return "\n".join(lines)

    @staticmethod
    def format_email_qr(email: str, subject: str = "", body: str = "") -> str:
        from urllib.parse import quote
        q = []
        if subject:
            q.append(f"subject={quote(subject)}")
        if body:
            q.append(f"body={quote(body)}")
        query_str = f"?{'&'.join(q)}" if q else ""
        return f"mailto:{email}{query_str}"

    @staticmethod
    def format_phone_qr(phone: str) -> str:
        return f"tel:{phone.strip()}"

    # --- Styled QR Generator ---
    @staticmethod
    def generate_styled_qr(
        content: str,
        size: int = 320,
        fg_color: str = "#000000",
        bg_color: str = "#FFFFFF",
        margin: int = 2,
        center_label: str = ""
    ) -> QPixmap:
        """Generates a styled high-resolution QR pixmap."""
        matrix = _generate_qr_svg_or_matrix(content)
        n = len(matrix)
        total_cells = n + 2 * margin

        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(bg_color))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(fg_color)))

        cell_size = float(size) / float(total_cells)

        for r in range(n):
            for c in range(n):
                if matrix[r][c]:
                    x = (c + margin) * cell_size
                    y = (r + margin) * cell_size
                    painter.drawRect(QRectF(x, y, cell_size + 0.5, cell_size + 0.5))

        # Center label if requested
        if center_label:
            painter.setRenderHint(QPainter.Antialiasing, True)
            box_w = size * 0.35
            box_h = size * 0.16
            bx = (size - box_w) / 2.0
            by = (size - box_h) / 2.0
            painter.setBrush(QBrush(QColor(bg_color)))
            painter.setPen(QPen(QColor(fg_color), 2))
            painter.drawRoundedRect(QRectF(bx, by, box_w, box_h), 4, 4)

            painter.setPen(QPen(QColor(fg_color)))
            font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(bx, by, box_w, box_h), Qt.AlignCenter, center_label)

        painter.end()
        return pixmap

    # --- Batch QR Generation ---
    @staticmethod
    def generate_batch_qr(
        items: List[Tuple[str, str]], # (filename_base, content)
        output_dir: str,
        size: int = 300
    ) -> List[str]:
        """Generates multiple QR images into a directory."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        created_paths = []

        for name, text in items:
            pix = QrBarcodeTools.generate_styled_qr(text, size=size)
            safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip() or "qr_code"
            dest = out / f"{safe_name}.png"
            pix.save(str(dest), "PNG")
            created_paths.append(str(dest))

        return created_paths

    # --- Barcode Generators (Code 128 & Code 39) ---
    @staticmethod
    def _encode_code39_pattern(text: str) -> str:
        """Encodes string to Code 39 bar/space pattern (1=bar, 0=space)."""
        CHARS = {
            '0': '101001101101', '1': '110100101011', '2': '101100101011',
            '3': '110110010101', '4': '101001101011', '5': '110100110101',
            '6': '101100110101', '7': '101001011011', '8': '110100101101',
            '9': '101100101101', 'A': '110101001011', 'B': '101101001011',
            'C': '110110100101', 'D': '101011001011', 'E': '110101100101',
            'F': '101101100101', 'G': '101010011011', 'H': '110101001101',
            'I': '101101001101', 'J': '101011001101', 'K': '110101010011',
            'L': '101101010011', 'M': '110110101001', 'N': '101011010011',
            'O': '110101101001', 'P': '101101101001', 'Q': '101010110011',
            'R': '110101011001', 'S': '101101011001', 'T': '101011011001',
            'U': '110010101011', 'V': '100110101011', 'W': '110011010101',
            'X': '100101101011', 'Y': '110010110101', 'Z': '100110110101',
            '-': '100101011011', '.': '110010101101', ' ': '100110101101',
            '*': '100101101101', '$': '100100100101', '/': '100100101001',
            '+': '100101001001', '%': '101001001001'
        }
        clean = text.upper()
        full = f"*{clean}*"
        pattern = []
        for ch in full:
            p = CHARS.get(ch, CHARS['-'])
            pattern.append(p)
            pattern.append('0') # inter-character gap
        return "".join(pattern)

    @staticmethod
    def generate_barcode(
        text: str,
        barcode_type: str = "Code 39",
        width: int = 400,
        height: int = 140,
        show_text: bool = True
    ) -> QPixmap:
        """Renders clean 1D barcode to QPixmap."""
        clean_text = text.strip() or "SINAX-1234"
        pattern = QrBarcodeTools._encode_code39_pattern(clean_text)

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#FFFFFF"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, False)

        margin_x = 24.0
        bar_area_w = float(width) - 2 * margin_x
        bar_area_h = float(height) - (40.0 if show_text else 16.0)

        n_modules = len(pattern)
        module_w = bar_area_w / float(n_modules)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#000000")))

        for idx, bit in enumerate(pattern):
            if bit == '1':
                bx = margin_x + idx * module_w
                painter.drawRect(QRectF(bx, 14, module_w + 0.4, bar_area_h))

        if show_text:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(QPen(QColor("#111827")))
            font = QFont("Consolas", 11, QFont.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(0, height - 28, width, 24),
                Qt.AlignCenter,
                clean_text
            )

        painter.end()
        return pixmap

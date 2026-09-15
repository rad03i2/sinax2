# -*- coding: utf-8 -*-
"""
SINAX Number & Conversion Lab
Units conversion (Data, Speed, Time, Temperature, Length, Area, Volume, Mass),
Download/Transfer ETA calculator, Storage overhead converter, percentages, and bitwise math.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


class ConversionTools:
    """Universal physical, digital, and mathematical conversions."""

    # --- Data Size Converter ---
    @staticmethod
    def convert_data_size(val: float, unit_from: str) -> Dict[str, str]:
        """Converts digital data magnitude to all standard binary and decimal units."""
        factors_to_bytes = {
            "bit": 0.125,
            "byte": 1.0,
            "KB": 1000.0,
            "KiB": 1024.0,
            "MB": 1000.0**2,
            "MiB": 1024.0**2,
            "GB": 1000.0**3,
            "GiB": 1024.0**3,
            "TB": 1000.0**4,
            "TiB": 1024.0**4,
            "PB": 1000.0**5,
            "PiB": 1024.0**5,
        }
        b = val * factors_to_bytes.get(unit_from, 1.0)
        return {
            "Bits": f"{b * 8:,.0f} bit",
            "Bytes": f"{b:,.0f} B",
            "KB (Dec)": f"{b / 1000.0:,.3f} KB",
            "KiB (Bin)": f"{b / 1024.0:,.3f} KiB",
            "MB (Dec)": f"{b / (1000**2):,.3f} MB",
            "MiB (Bin)": f"{b / (1024**2):,.3f} MiB",
            "GB (Dec)": f"{b / (1000**3):,.3f} GB",
            "GiB (Bin)": f"{b / (1024**3):,.3f} GiB",
            "TB (Dec)": f"{b / (1000**4):,.3f} TB",
            "TiB (Bin)": f"{b / (1024**4):,.3f} TiB",
        }

    # --- Network Speed Converter ---
    @staticmethod
    def convert_network_speed(val: float, unit_from: str) -> Dict[str, str]:
        """Converts speed rates between bits and bytes per second."""
        factors_to_bps = {
            "bps": 1.0,
            "Kbps": 1000.0,
            "KB/s": 8000.0,
            "Mbps": 1_000_000.0,
            "MB/s": 8_000_000.0,
            "Gbps": 1_000_000_000.0,
            "GB/s": 8_000_000_000.0,
        }
        bps = val * factors_to_bps.get(unit_from, 1_000_000.0)
        return {
            "Kbps": f"{bps / 1000.0:,.2f} Kbps",
            "KB/s": f"{bps / 8000.0:,.2f} KB/s",
            "Mbps": f"{bps / 1_000_000.0:,.2f} Mbps",
            "MB/s": f"{bps / 8_000_000.0:,.2f} MB/s",
            "Gbps": f"{bps / 1_000_000_000.0:,.3f} Gbps",
            "GB/s": f"{bps / 8_000_000_000.0:,.3f} GB/s",
        }

    # --- Transfer & Download Time Calculator ---
    @staticmethod
    def calculate_transfer_time(
        file_size_gb: float,
        speed_mbps: float,
        overhead_pct: float = 5.0
    ) -> Dict[str, Any]:
        """Estimates total transfer time taking network protocol overhead into account."""
        if speed_mbps <= 0:
            return {"error": "السرعة يجب أن تكون أكبر من صفر"}

        total_bits = (file_size_gb * 1000.0**3 * 8.0) * (1.0 + (overhead_pct / 100.0))
        speed_bps = speed_mbps * 1_000_000.0
        sec = total_bits / speed_bps

        hours = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)

        formatted = []
        if hours > 0:
            formatted.append(f"{hours} ساعة")
        if mins > 0:
            formatted.append(f"{mins} دقيقة")
        formatted.append(f"{secs} ثانية")

        return {
            "total_seconds": round(sec, 1),
            "formatted_eta": " و ".join(formatted),
            "effective_mb_per_sec": round((speed_mbps / 8.0) / (1.0 + overhead_pct / 100.0), 2),
        }

    # --- Storage Usable Capacity Calculator ---
    @staticmethod
    def calculate_usable_storage(advertised_capacity_gb: float) -> Dict[str, str]:
        """
        Explains why a 1 TB drive shows ~931 GiB in Windows.
        Manufacturers count 1,000,000,000 bytes per GB; Windows uses 1,073,741,824 bytes (GiB).
        """
        raw_bytes = advertised_capacity_gb * (1000.0**3)
        usable_gib = raw_bytes / (1024.0**3)
        usable_tib = raw_bytes / (1024.0**4)

        return {
            "advertised": f"{advertised_capacity_gb:,.0f} GB (سعة المصنع التجارية)",
            "windows_gib": f"{usable_gib:,.1f} GiB (في مستكشف ويندوز)",
            "windows_tib": f"{usable_tib:,.2f} TiB",
            "difference": f"{advertised_capacity_gb - usable_gib:,.1f} GB فرق حسابي طبيعي (وليس عطلاً)",
        }

    # --- Temperature ---
    @staticmethod
    def convert_temperature(val: float, unit_from: str) -> Dict[str, str]:
        if unit_from == "C":
            c = val
        elif unit_from == "F":
            c = (val - 32.0) * (5.0 / 9.0)
        else: # K
            c = val - 273.15

        f = (c * (9.0 / 5.0)) + 32.0
        k = c + 273.15
        return {
            "Celsius (°C)": f"{c:,.2f} °C",
            "Fahrenheit (°F)": f"{f:,.2f} °F",
            "Kelvin (K)": f"{k:,.2f} K",
        }

    # --- Number Base Converter ---
    @staticmethod
    def convert_number_base(val_str: str, from_base: int) -> Dict[str, str]:
        """Converts an integer representation between Binary, Octal, Decimal, and Hex."""
        clean = val_str.replace(" ", "").strip()
        num = int(clean, from_base)
        return {
            "Decimal": f"{num:,}",
            "Hexadecimal": hex(num).upper().replace("0X", "0x"),
            "Binary": bin(num).replace("0b", ""),
            "Octal": oct(num).replace("0o", ""),
        }

    # --- Bitwise Calculator ---
    @staticmethod
    def calculate_bitwise(a: int, b: int, op: str) -> Dict[str, Any]:
        """Calculates bitwise operations with binary output view."""
        if op == "AND":
            res = a & b
        elif op == "OR":
            res = a | b
        elif op == "XOR":
            res = a ^ b
        elif op == "NOT":
            res = ~a
        elif op == "LSHIFT":
            res = a << b
        elif op == "RSHIFT":
            res = a >> b
        else:
            res = 0

        return {
            "result_decimal": res,
            "result_hex": hex(res),
            "result_binary": bin(res),
        }

    # --- Percentages ---
    @staticmethod
    def calculate_percentage(
        part: Optional[float] = None,
        total: Optional[float] = None,
        percent: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculates percentage, part, or total based on provided fields."""
        if percent is not None and total is not None:
            return {"part": round((percent / 100.0) * total, 4)}
        elif part is not None and total is not None and total != 0:
            return {"percentage": round((part / total) * 100.0, 2)}
        return {}

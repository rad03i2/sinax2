# -*- coding: utf-8 -*-
"""
SINAX Display & Monitor Service (خدمة الشاشات ومعلومات العرض)
Detects connected displays, resolutions, refresh rates, scaling/DPI, primary flags,
decodes EDID metadata (WmiMonitorID) for manufacturer and year, and maps multi-monitor layouts.
"""

import os
import subprocess
from typing import Any, Dict, List, Optional

from PySide6.QtGui import QGuiApplication

from app.core.logger import get_logger
from app.services.devices.hardware_models import MonitorDetails

logger = get_logger("display_service")

# Common 3-letter EDID Manufacturer codes
EDID_VENDORS = {
    "AAC": "Acer",
    "ACR": "Acer",
    "AOC": "AOC",
    "APP": "Apple",
    "AUS": "ASUS",
    "BNQ": "BenQ",
    "CMN": "Chimei Innolux",
    "DEL": "Dell",
    "ENC": "Eizo",
    "HPN": "HP",
    "HWP": "HP",
    "LEN": "Lenovo",
    "LGD": "LG Display",
    "NEC": "NEC",
    "PHL": "Philips",
    "SAM": "Samsung",
    "SEC": "Samsung",
    "SNY": "Sony",
    "VSC": "ViewSonic",
}


class DisplayService:
    """Manages display monitors, resolutions, refresh rates, and EDID data."""

    @classmethod
    def get_connected_monitors(cls) -> List[MonitorDetails]:
        """Discovers all connected monitors combining Qt Screen APIs and WMI EDID."""
        monitors: List[MonitorDetails] = []
        app = QGuiApplication.instance()
        screens = app.screens() if app else []

        edid_data = cls._query_edid_monitors()

        if not screens:
            import ctypes
            try:
                user32 = ctypes.windll.user32
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
            except Exception:
                w, h = 1920, 1080

            edid = edid_data[0] if edid_data else {}
            monitors.append(MonitorDetails(
                display_index=1,
                device_name="\\\\.\\DISPLAY1",
                friendly_name=edid.get("friendly_name") or "شاشة العرض الأساسية",
                manufacturer=edid.get("manufacturer") or "شاشة قياسية",
                product_code=edid.get("product_code") or "غير متوفر",
                serial_number=edid.get("serial") or "غير متوفر",
                manufacture_year=edid.get("year"),
                resolution=f"{w}×{h}",
                width_pixels=w,
                height_pixels=h,
                refresh_rate_hz=60.0,
                scaling_dpi_percent=100,
                orientation="أفقي (Landscape)" if w >= h else "رأسي (Portrait)",
                is_primary=True
            ))
            return monitors

        for idx, s in enumerate(screens):
            name = s.name()
            geo = s.geometry()
            w, h = geo.width(), geo.height()
            refresh = round(s.refreshRate(), 1)
            dpr = s.devicePixelRatio()
            scaling = int(round(dpr * 100))
            is_primary = (s == app.primaryScreen()) if app else (idx == 0)
            orient = "أفقي (Landscape)" if w >= h else "رأسي (Portrait)"

            # Match with EDID info if available
            edid = edid_data[idx] if idx < len(edid_data) else {}

            friendly = edid.get("friendly_name") or f"شاشة عرض {idx + 1}"
            manuf = edid.get("manufacturer") or "شاشة قياسية"
            prod_code = edid.get("product_code") or "غير متوفر"
            serial = edid.get("serial") or "غير متوفر"
            year = edid.get("year")

            monitors.append(MonitorDetails(
                display_index=idx + 1,
                device_name=name,
                friendly_name=friendly,
                manufacturer=manuf,
                product_code=prod_code,
                serial_number=serial,
                manufacture_year=year,
                resolution=f"{w}×{h}",
                width_pixels=w,
                height_pixels=h,
                refresh_rate_hz=refresh,
                scaling_dpi_percent=scaling,
                orientation=orient,
                is_primary=is_primary
            ))

        return monitors

    @classmethod
    def _query_edid_monitors(cls) -> List[Dict[str, Any]]:
        """Queries WmiMonitorID from root\\wmi to decode manufacturer, serial, and year."""
        results = []
        try:
            import win32com.client
            wmi = win32com.client.GetObject(r"winmgmts:\\.\root\wmi")
            for mon in wmi.InstancesOf("WmiMonitorID"):
                manuf_code = cls._decode_char_array(getattr(mon, "ManufacturerName", None))
                prod_code = cls._decode_char_array(getattr(mon, "ProductCodeID", None))
                serial = cls._decode_char_array(getattr(mon, "SerialNumberID", None))
                friendly = cls._decode_char_array(getattr(mon, "UserFriendlyName", None))
                year = getattr(mon, "YearOfManufacture", None)

                vendor = EDID_VENDORS.get(manuf_code.upper(), manuf_code or "شاشة عرض")

                results.append({
                    "manufacturer": vendor,
                    "product_code": prod_code or "Panel",
                    "serial": serial or "غير متوفر",
                    "friendly_name": friendly or f"{vendor} Monitor",
                    "year": int(year) if year and str(year).isdigit() else None
                })
        except Exception as e:
            logger.debug(f"WmiMonitorID query error: {e}")

        return results

    @staticmethod
    def _decode_char_array(arr) -> str:
        """Converts an integer array from WMI into a clean string."""
        if not arr:
            return ""
        try:
            chars = [chr(c) for c in arr if c != 0]
            return "".join(chars).strip()
        except Exception:
            return ""

    @classmethod
    def open_display_settings(cls) -> bool:
        """Launches Windows Settings to the Display page."""
        try:
            os.system("start ms-settings:display")
            return True
        except Exception:
            return False

    @classmethod
    def get_monitors(cls) -> List[MonitorDetails]:
        """Convenience alias for get_connected_monitors."""
        return cls.get_connected_monitors()

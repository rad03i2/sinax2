# -*- coding: utf-8 -*-
"""
SINAX Battery & Power Service (خدمة البطارية والطاقة)
Detects laptop battery presence, extracts design capacity vs full charge capacity,
computes the capacity ratio without medical claims, tracks charge cycles,
and generates the official Microsoft Windows Battery Report (powercfg /batteryreport).
"""

import os
import subprocess
import tempfile
import webbrowser
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

import psutil

from app.core.logger import get_logger
from app.services.devices.hardware_models import BatteryDetails

logger = get_logger("battery_service")


class BatteryService:
    """Manages battery hardware metrics, power status, and official battery reports."""

    _cached_details: Optional[BatteryDetails] = None

    @classmethod
    def get_battery_details(cls, force_refresh: bool = False) -> BatteryDetails:
        """Gathers battery telemetry from psutil and powercfg XML report."""
        if cls._cached_details is not None and not force_refresh:
            return cls._cached_details

        ps_bat = psutil.sensors_battery()
        if not ps_bat:
            # Desktop PC without battery
            res = BatteryDetails(
                present=False,
                charging_state="لا توجد بطارية (جهاز مكتبي)",
                power_source="تيار كهربائي مباشر (Direct AC)"
            )
            cls._cached_details = res
            return res

        percent = int(ps_bat.percent)
        is_plugged = ps_bat.power_plugged
        secs_left = ps_bat.secsleft

        if is_plugged:
            charging_state = "مشحونة بالكامل" if percent >= 99 else "قيد الشحن (متصل بالتيار)"
            power_source = "تيار كهربائي (شاحن AC)"
        else:
            charging_state = "تفريغ (على البطارية)"
            power_source = "طاقة البطارية"

        time_remaining = "غير متوفر"
        if secs_left and secs_left > 0 and secs_left != psutil.POWER_TIME_UNLIMITED:
            hrs = secs_left // 3600
            mins = (secs_left % 3600) // 60
            time_remaining = f"{hrs} ساعة و {mins} دقيقة تقريباً" if hrs > 0 else f"{mins} دقيقة تقريباً"

        # Query XML battery report for Design vs Full Charge Capacity and Cycles
        design_cap, full_cap, cycles, chem = cls._query_battery_report_xml()

        ratio = None
        if design_cap and full_cap and design_cap > 0:
            ratio = round((full_cap / design_cap) * 100.0, 1)

        details = BatteryDetails(
            present=True,
            charge_percent=percent,
            charging_state=charging_state,
            power_source=power_source,
            time_remaining_formatted=time_remaining,
            chemistry=chem or "Lithium-ion",
            design_capacity_mwh=design_cap,
            full_charge_capacity_mwh=full_cap,
            capacity_ratio_percent=ratio,
            cycle_count=cycles
        )

        cls._cached_details = details
        return details

    @classmethod
    def _query_battery_report_xml(cls) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[str]]:
        """Parses temporary powercfg XML for exact design/full capacities and cycle count."""
        temp_xml = os.path.join(tempfile.gettempdir(), f"sinax_bat_{os.getpid()}.xml")
        try:
            res = subprocess.run(
                ["powercfg", "/batteryreport", "/xml", "/output", temp_xml],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            if res.returncode == 0 and os.path.exists(temp_xml):
                tree = ET.parse(temp_xml)
                ns = {"b": "http://schemas.microsoft.com/battery/2012"}
                for bat in tree.findall(".//b:Battery", namespaces=ns):
                    design_txt = bat.findtext("b:DesignCapacity", namespaces=ns)
                    full_txt = bat.findtext("b:FullChargeCapacity", namespaces=ns)
                    cycle_txt = bat.findtext("b:CycleCount", namespaces=ns)
                    chem_txt = bat.findtext("b:Chemistry", namespaces=ns)

                    design_cap = int(design_txt) if design_txt and design_txt.isdigit() else None
                    full_cap = int(full_txt) if full_txt and full_txt.isdigit() else None
                    cycles = int(cycle_txt) if cycle_txt and cycle_txt.isdigit() else None
                    return design_cap, full_cap, cycles, chem_txt
        except Exception as e:
            logger.debug(f"powercfg xml query failed: {e}")
        finally:
            if os.path.exists(temp_xml):
                try:
                    os.remove(temp_xml)
                except Exception:
                    pass

        return None, None, None, None

    @classmethod
    def generate_official_battery_report(cls, output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Generates the official HTML battery life report and opens it in the browser.
        Returns (success, report_path_or_error).
        """
        target_dir = output_dir or tempfile.gettempdir()
        report_path = os.path.join(target_dir, "SINAX_Windows_Battery_Report.html")
        try:
            res = subprocess.run(
                ["powercfg", "/batteryreport", "/output", report_path],
                capture_output=True,
                text=True,
                timeout=8.0
            )
            if res.returncode == 0 and os.path.exists(report_path):
                webbrowser.open(f"file:///{report_path.replace(os.sep, '/')}")
                return True, report_path
            return False, f"فشل تشغيل أمر تقرير البطارية: {res.stderr}"
        except Exception as e:
            return False, f"خطأ أثناء توليد تقرير البطارية: {e}"

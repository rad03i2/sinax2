# -*- coding: utf-8 -*-
"""
SINAX Device Information & Diagnostic Report Service
Queries and compiles hardware, operating system, and system environment specifications:
- OS Edition, Build, Architecture, Boot Uptime
- Processor details (Name, Cores, Threads, Clock speed)
- Memory (Installed, Usable, Virtual)
- Graphics Adapters (GPUs, Drivers, VRAM)
- Motherboard and BIOS information
- Battery & Power status
- Multi-format Export: TXT, JSON, CSV, HTML
"""

import csv
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psutil
from app.core.logger import get_logger
from app.services.system_storage.storage_scanner import format_bytes

logger = get_logger("device_info_service")


@dataclass
class GPUInfo:
    name: str
    driver_version: str
    vram_bytes: int
    vram_formatted: str


@dataclass
class BatteryStatus:
    has_battery: bool
    percent: float
    is_plugged: bool
    secs_left: Optional[int] = None
    time_left_formatted: str = ""


@dataclass
class SystemSpecs:
    # OS
    os_name: str
    os_release: str
    os_version: str
    os_arch: str
    computer_name: str
    username: str
    uptime_seconds: float
    uptime_formatted: str
    boot_time: str
    # CPU
    cpu_name: str
    cpu_cores_physical: int
    cpu_cores_logical: int
    cpu_freq_max_mhz: float
    cpu_freq_current_mhz: float
    cpu_arch: str
    # Memory
    ram_total_bytes: int
    ram_total_formatted: str
    ram_available_bytes: int
    ram_available_formatted: str
    swap_total_bytes: int
    swap_total_formatted: str
    # Motherboard & BIOS
    motherboard_manufacturer: str
    motherboard_product: str
    bios_version: str
    # Graphics
    gpus: List[GPUInfo] = field(default_factory=list)
    # Battery
    battery: Optional[BatteryStatus] = None


class DeviceInfoService:
    """Collects system and hardware specifications and exports comprehensive reports."""

    _cached_specs: Optional[SystemSpecs] = None
    _cache_time: float = 0.0

    @classmethod
    def get_system_specs(cls, force_refresh: bool = False) -> SystemSpecs:
        """Gather all hardware and OS information."""
        now = time.time()
        if not force_refresh and cls._cached_specs is not None and (now - cls._cache_time < 300.0):
            return cls._cached_specs

        # 1. OS & Uptime
        boot_ts = psutil.boot_time()
        uptime_sec = max(0.0, now - boot_ts)
        boot_dt = datetime.fromtimestamp(boot_ts).strftime("%Y-%m-%d %H:%M:%S")

        # Format uptime (X days, Y hours, Z minutes)
        td = timedelta(seconds=int(uptime_sec))
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_parts = []
        if days > 0:
            uptime_parts.append(f"{days} يوم")
        if hours > 0:
            uptime_parts.append(f"{hours} ساعة")
        uptime_parts.append(f"{minutes} دقيقة")
        uptime_str = " و ".join(uptime_parts)

        # 2. CPU
        cpu_name = platform.processor() or "معالج قياسي"
        try:
            # Query friendly CPU name from registry on Windows
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                val, _ = winreg.QueryValueEx(k, "ProcessorNameString")
                if val:
                    cpu_name = str(val).strip()
        except Exception:
            pass

        phys_cores = psutil.cpu_count(logical=False) or 1
        log_cores = psutil.cpu_count(logical=True) or phys_cores
        f_max = 0.0
        f_curr = 0.0
        try:
            cf = psutil.cpu_freq()
            if cf:
                f_max = cf.max
                f_curr = cf.current
        except Exception:
            pass

        # 3. Memory
        try:
            vm = psutil.virtual_memory()
            ram_tot = vm.total
            ram_avail = vm.available
        except Exception:
            ram_tot, ram_avail = 0, 0

        try:
            sm = psutil.swap_memory()
            swap_tot = sm.total
        except Exception:
            swap_tot = 0

        # 4 & 5. Motherboard, BIOS & GPU via a single combined PowerShell command
        mb_man = "غير متوفرة"
        mb_prod = "لوحة أم قياسية"
        bios_ver = "غير متوفرة"
        gpus: List[GPUInfo] = []

        try:
            cmd = 'powershell -NoProfile -Command "@{\\"bb\\"=(Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product); \\"bios\\"=(Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, Version); \\"vc\\"=(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM)} | ConvertTo-Json"'
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if res.returncode == 0 and res.stdout.strip():
                comb = json.loads(res.stdout)
                bb_data = comb.get("bb") or {}
                mb_man = bb_data.get("Manufacturer") or mb_man
                mb_prod = bb_data.get("Product") or mb_prod

                bios_data = comb.get("bios") or {}
                bios_ver = bios_data.get("SMBIOSBIOSVersion") or bios_data.get("Version") or bios_ver

                vc_data = comb.get("vc")
                if isinstance(vc_data, dict):
                    vc_list = [vc_data]
                elif isinstance(vc_data, list):
                    vc_list = vc_data
                else:
                    vc_list = []

                for g in vc_list:
                    g_name = g.get("Name") or "كارت شاشة"
                    d_ver = g.get("DriverVersion") or "غير متوفر"
                    v_ram = int(g.get("AdapterRAM", 0) or 0)
                    gpus.append(GPUInfo(
                        name=g_name,
                        driver_version=d_ver,
                        vram_bytes=v_ram,
                        vram_formatted=format_bytes(v_ram) if v_ram > 0 else "غير محدد"
                    ))
        except Exception:
            pass

        # 6. Battery
        battery_status = None
        try:
            sb = psutil.sensors_battery()
            if sb is not None:
                secs = sb.secsleft if sb.secsleft not in (psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED) else None
                time_str = ""
                if secs is not None:
                    h, m = divmod(secs // 60, 60)
                    time_str = f"{h} ساعة و {m} دقيقة متبقية"
                battery_status = BatteryStatus(
                    has_battery=True,
                    percent=round(sb.percent, 1),
                    is_plugged=sb.power_plugged,
                    secs_left=secs,
                    time_left_formatted=time_str
                )
        except Exception:
            pass

        return SystemSpecs(
            os_name=platform.system(),
            os_release=platform.release(),
            os_version=platform.version(),
            os_arch=platform.machine(),
            computer_name=platform.node(),
            username=os.environ.get("USERNAME", "مستخدم"),
            uptime_seconds=uptime_sec,
            uptime_formatted=uptime_str,
            boot_time=boot_dt,
            cpu_name=cpu_name,
            cpu_cores_physical=phys_cores,
            cpu_cores_logical=log_cores,
            cpu_freq_max_mhz=f_max,
            cpu_freq_current_mhz=f_curr,
            cpu_arch=platform.architecture()[0],
            ram_total_bytes=ram_tot,
            ram_total_formatted=format_bytes(ram_tot),
            ram_available_bytes=ram_avail,
            ram_available_formatted=format_bytes(ram_avail),
            swap_total_bytes=swap_tot,
            swap_total_formatted=format_bytes(swap_tot),
            motherboard_manufacturer=mb_man,
            motherboard_product=mb_prod,
            bios_version=bios_ver,
            gpus=gpus,
            battery=battery_status
        )
        cls._cached_specs = specs
        cls._cache_time = now
        return specs

    @classmethod
    def export_report(cls, specs: SystemSpecs, output_path: str, format_type: str = "txt") -> bool:
        """Export hardware and diagnostic report to TXT, JSON, CSV, or HTML."""
        fmt = format_type.lower()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            if fmt == "json":
                data = asdict(specs)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True

            if fmt == "csv":
                with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["المكون", "القيمة"])
                    writer.writerow(["نظام التشغيل", f"{specs.os_name} {specs.os_release} ({specs.os_version})"])
                    writer.writerow(["اسم الكمبيوتر", specs.computer_name])
                    writer.writerow(["اسم المستخدم", specs.username])
                    writer.writerow(["مدة التشغيل", specs.uptime_formatted])
                    writer.writerow(["وقت الإقلاع", specs.boot_time])
                    writer.writerow(["المعالج (CPU)", specs.cpu_name])
                    writer.writerow(["الأنوية الفيزيائية", specs.cpu_cores_physical])
                    writer.writerow(["الأنوية المنطقية", specs.cpu_cores_logical])
                    writer.writerow(["الذاكرة العشوائية (RAM)", specs.ram_total_formatted])
                    writer.writerow(["الذاكرة المتاحة", specs.ram_available_formatted])
                    writer.writerow(["اللوحة الأم", f"{specs.motherboard_manufacturer} - {specs.motherboard_product}"])
                    writer.writerow(["إصدار BIOS", specs.bios_version])
                    for idx, g in enumerate(specs.gpus):
                        writer.writerow([f"بطاقة الرسوميات {idx+1}", f"{g.name} (VRAM: {g.vram_formatted})"])
                return True

            if fmt == "html":
                gpu_rows = "".join(f"<tr><td>بطاقة الرسوميات</td><td>{g.name} (تعريف: {g.driver_version} - ذاكرة: {g.vram_formatted})</td></tr>" for g in specs.gpus)
                html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>تقرير مواصفات جهاز الحاسوب - SINAX</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0D1117; color: #C9D1D9; padding: 24px; direction: rtl; }}
.card {{ background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 24px; max-width: 800px; margin: 0 auto; }}
h1 {{ color: #58A6FF; border-bottom: 1px solid #30363D; padding-bottom: 12px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th, td {{ padding: 10px 14px; text-align: right; border-bottom: 1px solid #21262D; }}
th {{ color: #8B949E; width: 35%; }}
td {{ color: #F0F6FC; font-weight: 500; }}
</style>
</head>
<body>
<div class="card">
<h1>تقرير مواصفات النظام والتخزين - SINAX</h1>
<table>
<tr><th>نظام التشغيل</th><td>{specs.os_name} {specs.os_release} ({specs.os_arch})</td></tr>
<tr><th>اسم الحاسوب والمستخدم</th><td>{specs.computer_name} ({specs.username})</td></tr>
<tr><th>مدة التشغيل</th><td>{specs.uptime_formatted} (أُقلع في: {specs.boot_time})</td></tr>
<tr><th>المعالج (CPU)</th><td>{specs.cpu_name} ({specs.cpu_cores_physical} أنوية حقيقية / {specs.cpu_cores_logical} خيط معالجة)</td></tr>
<tr><th>الذاكرة العشوائية (RAM)</th><td>{specs.ram_total_formatted} (المتاح: {specs.ram_available_formatted})</td></tr>
<tr><th>اللوحة الأم</th><td>{specs.motherboard_manufacturer} - {specs.motherboard_product}</td></tr>
<tr><th>إصدار BIOS</th><td>{specs.bios_version}</td></tr>
{gpu_rows}
</table>
</div>
</body>
</html>"""
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                return True

            # Default TXT
            txt_lines = [
                "============================================================",
                "              تقرير مواصفات جهاز الحاسوب - SINAX             ",
                "============================================================",
                f"تاريخ التقرير : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "[ نظام التشغيل ]",
                f"- النظام      : {specs.os_name} {specs.os_release} (Build {specs.os_version})",
                f"- المعمارية   : {specs.os_arch}",
                f"- اسم الجهاز  : {specs.computer_name}",
                f"- المستخدم    : {specs.username}",
                f"- مدة التشغيل : {specs.uptime_formatted}",
                f"- وقت الإقلاع : {specs.boot_time}",
                "",
                "[ المعالج CPU ]",
                f"- الاسم       : {specs.cpu_name}",
                f"- الأنوية     : {specs.cpu_cores_physical} نواة فيزيائية / {specs.cpu_cores_logical} نواة منطقية",
                "",
                "[ الذاكرة العشوائية RAM ]",
                f"- الإجمالي    : {specs.ram_total_formatted}",
                f"- المتاح      : {specs.ram_available_formatted}",
                f"- ملف التبديل : {specs.swap_total_formatted}",
                "",
                "[ اللوحة الأم و BIOS ]",
                f"- الشركة      : {specs.motherboard_manufacturer}",
                f"- الموديل     : {specs.motherboard_product}",
                f"- BIOS        : {specs.bios_version}",
                "",
                "[ بطاقات الرسوميات GPU ]"
            ]
            for g in specs.gpus:
                txt_lines.append(f"- {g.name} (تعريف: {g.driver_version} | VRAM: {g.vram_formatted})")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(txt_lines))
            return True

        except Exception as e:
            logger.error(f"Failed to export specs report: {e}")
            return False

# -*- coding: utf-8 -*-
"""
SINAX Hardware Report & Snapshot Diff Service (خدمة تقارير العتاد ومقارنة اللقطات)
Generates Simple & Advanced Hardware Reports across HTML, JSON, TXT, and CSV formats,
enforces Global Privacy Mode masking (Serials, MACs, Usernames),
and performs point-in-time diff comparisons between hardware snapshots.
"""

import csv
import io
import json
import time
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.devices.battery_service import BatteryService
from app.services.devices.cpu_service import CpuService
from app.services.devices.display_service import DisplayService
from app.services.devices.driver_service import DriverService
from app.services.devices.gpu_service import GpuService
from app.services.devices.hardware_db import HardwareDatabase
from app.services.devices.hardware_models import HardwareSnapshot, SystemSummary
from app.services.devices.memory_service import MemoryService
from app.services.devices.motherboard_bios_service import MotherboardBiosService
from app.services.devices.sensor_service import SensorService
from app.services.devices.storage_hardware_service import StorageHardwareService
from app.services.devices.windows_info_service import WindowsInfoService

logger = get_logger("hardware_report_service")


class HardwareReportService:
    """Manages compiling system summaries, hardware exports, and snapshot diffs."""

    @classmethod
    def get_system_summary(cls) -> SystemSummary:
        """Compiles the high-level system summary for the hero card and quick exports."""
        mb = MotherboardBiosService.get_motherboard_info()
        bios = MotherboardBiosService.get_bios_info()
        cpu = CpuService.get_cpu_specs()
        ram = MemoryService.get_memory_info()
        gpus = GpuService.get_all_gpus()
        disks = StorageHardwareService.get_physical_storage_devices()
        bat = BatteryService.get_battery_details()
        win = WindowsInfoService.get_windows_details()
        dev_type = WindowsInfoService.detect_device_type()

        primary_gpu = gpus[0].name if gpus else "غير متوفر"
        # Prioritize dedicated GPU if present
        for g in gpus:
            if g.gpu_type == "منفصل (Dedicated)":
                primary_gpu = g.name
                break

        primary_disk = disks[0].model if disks else "غير متوفر"
        if disks:
            primary_disk = f"{disks[0].model} ({disks[0].capacity_formatted} {disks[0].media_type})"

        ram_summary = f"{ram.total_installed_formatted} ({ram.used_slots}/{ram.total_slots} منافذ)"
        if ram.modules:
            ram_summary = f"{ram.total_installed_formatted} {ram.modules[0].memory_type} ({ram.used_slots}/{ram.total_slots})"

        summary = SystemSummary(
            manufacturer=mb.manufacturer,
            model=mb.product,
            system_sku=mb.system_sku,
            device_type=dev_type,
            cpu_name=cpu.name,
            ram_total_gb=round(ram.total_installed_bytes / (1024 ** 3), 1),
            ram_summary=ram_summary,
            primary_gpu=primary_gpu,
            primary_storage=primary_disk,
            os_name=win.edition,
            os_build=win.build,
            os_arch=win.architecture,
            motherboard=f"{mb.manufacturer} {mb.product}",
            bios_version=bios.version,
            has_battery=bat.present,
            battery_percent=bat.charge_percent if bat.present else None,
            battery_status_ar=bat.charging_state if bat.present else "تيار مباشر",
            cpu_temp_c=cpu.temperature_package_c,
            gpu_temp_c=gpus[0].temperature_c if gpus and gpus[0].temperature_c else None
        )
        return summary

    @classmethod
    def compile_full_hardware_data(cls, privacy_mode: bool = False) -> Dict[str, Any]:
        """Compiles complete system data structure across all components."""
        summary = cls.get_system_summary()
        cpu = CpuService.get_cpu_specs()
        ram = MemoryService.get_memory_info()
        gpus = GpuService.get_all_gpus()
        disks = StorageHardwareService.get_physical_storage_devices()
        mb = MotherboardBiosService.get_motherboard_info()
        bios = MotherboardBiosService.get_bios_info()
        bat = BatteryService.get_battery_details()
        monitors = DisplayService.get_connected_monitors()
        win = WindowsInfoService.get_windows_details()
        sensors = SensorService.get_all_sensors()
        problems = DriverService.get_problem_devices()

        def mask(val: str) -> str:
            if not val or val == "غير متوفر":
                return val
            if privacy_mode:
                return "••••••••"
            return val

        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "privacy_mode": privacy_mode,
            "system_summary": summary.to_dict(),
            "windows": {
                "edition": win.edition,
                "version": win.version,
                "build": win.build,
                "architecture": win.architecture,
                "computer_name": mask(win.computer_name),
                "username": mask(win.username),
                "uptime": win.uptime_formatted,
                "activation": win.activation_status
            },
            "processor": {
                "name": cpu.name,
                "manufacturer": cpu.manufacturer,
                "physical_cores": cpu.cores_physical,
                "logical_processors": cpu.cores_logical,
                "max_clock_mhz": cpu.max_clock_mhz,
                "socket": cpu.socket,
                "virtualization": cpu.virtualization_firmware_enabled
            },
            "memory": {
                "total_installed": ram.total_installed_formatted,
                "usable": ram.usable_formatted,
                "slots_used": ram.used_slots,
                "slots_total": ram.total_slots,
                "max_capacity": ram.max_capacity_formatted,
                "modules": [
                    {
                        "slot": m.slot,
                        "capacity": m.capacity_formatted,
                        "manufacturer": m.manufacturer,
                        "speed": f"{m.speed_mts} MT/s",
                        "type": m.memory_type,
                        "serial": mask(m.serial_number),
                        "part_number": m.part_number
                    }
                    for m in ram.modules
                ]
            },
            "graphics": [
                {
                    "name": g.name,
                    "vendor": g.vendor,
                    "type": g.gpu_type,
                    "driver_version": g.driver_version,
                    "vram": g.dedicated_vram_formatted
                }
                for g in gpus
            ],
            "motherboard": {
                "manufacturer": mb.manufacturer,
                "product": mb.product,
                "serial": mask(mb.serial_number),
                "bios_version": bios.version,
                "bios_date": bios.release_date,
                "bios_mode": bios.bios_mode,
                "secure_boot": bios.secure_boot,
                "tpm": bios.tpm_status_ar
            },
            "storage_devices": [
                {
                    "model": d.model,
                    "media_type": d.media_type_ar,
                    "bus_type": d.bus_type,
                    "capacity": d.capacity_formatted,
                    "health": d.health_status_ar,
                    "temperature": f"{d.temperature_c}°C" if d.temperature_c else "غير متوفر",
                    "serial": mask(d.serial_number)
                }
                for d in disks
            ],
            "battery": {
                "present": bat.present,
                "charge_percent": f"{bat.charge_percent}%" if bat.present else "N/A",
                "charging_state": bat.charging_state,
                "capacity_ratio": f"{bat.capacity_ratio_percent}%" if bat.capacity_ratio_percent else "غير متوفر",
                "cycle_count": bat.cycle_count or "غير متوفر"
            },
            "displays": [
                {
                    "name": m.friendly_name,
                    "resolution": m.resolution,
                    "refresh_rate": f"{m.refresh_rate_hz} Hz",
                    "scaling": f"{m.scaling_dpi_percent}%",
                    "primary": m.is_primary,
                    "serial": mask(m.serial_number)
                }
                for m in monitors
            ],
            "problem_devices_count": len(problems),
            "sensors_count": len(sensors)
        }
        return data

    @classmethod
    def export_text_report(cls, data: Dict[str, Any]) -> str:
        """Formats hardware data into a readable Arabic text report."""
        lines = [
            "==================================================================",
            "             تقرير مواصفات وعتاد الحاسوب - SINAX                  ",
            "==================================================================",
            f"تاريخ التقرير: {data.get('timestamp')}",
            f"وضع الخصوصية: {'مفعّل (تم حجب الأرقام التسلسلية)' if data.get('privacy_mode') else 'معطل'}",
            "------------------------------------------------------------------",
            "[نظام التشغيل والبيئة]",
            f"  الإصدار: {data['windows']['edition']} (Build {data['windows']['build']})",
            f"  اسم الكمبيوتر: {data['windows']['computer_name']}",
            f"  مدة التشغيل: {data['windows']['uptime']}",
            f"  حالة الترخيص: {data['windows']['activation']}",
            "------------------------------------------------------------------",
            "[المعالج المركزي CPU]",
            f"  الاسم: {data['processor']['name']}",
            f"  الأنوية والخيوط: {data['processor']['physical_cores']} أنوية حقيقية / {data['processor']['logical_processors']} خيطاً منطقياً",
            f"  التردد الأقصى: {data['processor']['max_clock_mhz']} MHz",
            f"  المقبس: {data['processor']['socket']}",
            "------------------------------------------------------------------",
            "[الذاكرة العشوائية RAM]",
            f"  الذاكرة المثبتة: {data['memory']['total_installed']} (المتاح للاستخدام: {data['memory']['usable']})",
            f"  المنافذ: {data['memory']['slots_used']} مستخدمة من أصل {data['memory']['slots_total']} منفذ (أقصى سعة: {data['memory']['max_capacity']})",
        ]
        for m in data["memory"]["modules"]:
            lines.append(f"    - {m['slot']}: {m['capacity']} {m['type']} @ {m['speed']} ({m['manufacturer']})")

        lines.extend([
            "------------------------------------------------------------------",
            "[معالجات الرسوميات GPU]",
        ])
        for g in data["graphics"]:
            lines.append(f"  - {g['name']} ({g['type']}) | تعريف: {g['driver_version']} | VRAM: {g['vram']}")

        lines.extend([
            "------------------------------------------------------------------",
            "[اللوحة الأم والـ BIOS]",
            f"  اللوحة: {data['motherboard']['manufacturer']} {data['motherboard']['product']}",
            f"  إصدار BIOS: {data['motherboard']['bios_version']} (بتاريخ: {data['motherboard']['bios_date']})",
            f"  الوضع والأمان: {data['motherboard']['bios_mode']} | Secure Boot: {data['motherboard']['secure_boot']}",
            f"  وحدة TPM: {data['motherboard']['tpm']}",
            "------------------------------------------------------------------",
            "[وحدات التخزين الفيزيائية]",
        ])
        for d in data["storage_devices"]:
            lines.append(f"  - {d['model']} | {d['capacity']} {d['media_type']} ({d['bus_type']}) | الحالة: {d['health']} | الحرارة: {d['temperature']}")

        lines.extend([
            "------------------------------------------------------------------",
            "[البطارية والطاقة]",
            f"  الحالة: {data['battery']['charging_state']} ({data['battery']['charge_percent']})",
            f"  نسبة السعة الحالية إلى التصميمية: {data['battery']['capacity_ratio']}",
            f"  دورات الشحن: {data['battery']['cycle_count']}",
            "------------------------------------------------------------------",
            "[الشاشات]",
        ])
        for mon in data["displays"]:
            prim_str = " (الشاشة الرئيسية)" if mon["primary"] else ""
            lines.append(f"  - {mon['name']}: {mon['resolution']} @ {mon['refresh_rate']} | تحجيم: {mon['scaling']}{prim_str}")

        lines.append("==================================================================")
        return "\n".join(lines)

    @classmethod
    def export_csv_report(cls, data: Dict[str, Any]) -> str:
        """Formats core hardware components into CSV rows with UTF-8."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["القسم", "العنصر", "القيمة"])
        writer.writerow(["النظام", "الإصدار", data["windows"]["edition"]])
        writer.writerow(["النظام", "البناء", data["windows"]["build"]])
        writer.writerow(["المعالج", "الاسم", data["processor"]["name"]])
        writer.writerow(["المعالج", "الأنوية الحقيقية", data["processor"]["physical_cores"]])
        writer.writerow(["المعالج", "الخيوط المنطقية", data["processor"]["logical_processors"]])
        writer.writerow(["الذاكرة", "الإجمالي", data["memory"]["total_installed"]])
        writer.writerow(["الذاكرة", "المنافذ المستخدمة", data["memory"]["slots_used"]])
        for g in data["graphics"]:
            writer.writerow(["كرت الشاشة", g["name"], g["vram"]])
        for d in data["storage_devices"]:
            writer.writerow(["التخزين", d["model"], f"{d['capacity']} ({d['media_type']})"])
        for mon in data["displays"]:
            writer.writerow(["الشاشات", mon["name"], f"{mon['resolution']} @ {mon['refresh_rate']}"])
        return output.getvalue()

    @classmethod
    def export_html_report(cls, data: Dict[str, Any]) -> str:
        """Generates a responsive modern HTML hardware report."""
        summary = data.get("system_summary", {})
        win = data.get("windows", {})
        cpu = data.get("processor", {})
        mem = data.get("memory", {})
        mb = data.get("motherboard", {})
        bat = data.get("battery", {})

        gpus_html = "".join(f"<li><b>{g.get('name')}</b> ({g.get('type')}) - VRAM: {g.get('vram')}</li>" for g in data.get("graphics", []))
        disks_html = "".join(f"<li><b>{d.get('model')}</b> ({d.get('capacity')} {d.get('media_type')}) - الحالة: {d.get('health')}</li>" for d in data.get("storage_devices", []))
        displays_html = "".join(f"<li><b>{m.get('name')}</b>: {m.get('resolution')} @ {m.get('refresh_rate')}</li>" for m in data.get("displays", []))

        html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>تقرير عتاد الحاسوب - SINAX</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0F172A; color: #F8FAFC; margin: 0; padding: 24px; direction: rtl; }}
.header {{ background: #1E293B; border-radius: 12px; padding: 24px; border: 1px solid #334155; margin-bottom: 20px; }}
h1 {{ margin: 0 0 8px 0; color: #38BDF8; font-size: 24px; }}
.meta {{ color: #94A3B8; font-size: 13px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.card {{ background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px; }}
.card h2 {{ color: #38BDF8; font-size: 16px; margin-top: 0; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
.row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }}
.label {{ color: #94A3B8; }}
.val {{ font-weight: bold; color: #F8FAFC; }}
ul {{ margin: 0; padding-right: 20px; color: #CBD5E1; font-size: 13px; }}
li {{ margin-bottom: 6px; }}
</style>
</head>
<body>
<div class="header">
<h1>تقرير مواصفات وعتاد الحاسوب - SINAX</h1>
<div class="meta">تاريخ التقرير: {data.get('timestamp')} | الجهاز: {summary.get('manufacturer', '')} {summary.get('model', '')}</div>
</div>
<div class="grid">
<div class="card">
<h2>نظام التشغيل والبيئة</h2>
<div class="row"><span class="label">الإصدار:</span><span class="val">{win.get('edition')}</span></div>
<div class="row"><span class="label">البناء:</span><span class="val">{win.get('build')}</span></div>
<div class="row"><span class="label">المعمارية:</span><span class="val">{win.get('architecture')}</span></div>
<div class="row"><span class="label">اسم الجهاز:</span><span class="val">{win.get('computer_name')}</span></div>
<div class="row"><span class="label">مدة التشغيل:</span><span class="val">{win.get('uptime')}</span></div>
</div>
<div class="card">
<h2>المعالج المركزي (CPU)</h2>
<div class="row"><span class="label">الاسم:</span><span class="val">{cpu.get('name')}</span></div>
<div class="row"><span class="label">الأنوية والمسارات:</span><span class="val">{cpu.get('physical_cores')} حقيقية / {cpu.get('logical_processors')} مسار</span></div>
<div class="row"><span class="label">التردد الأقصى:</span><span class="val">{cpu.get('max_clock_mhz')} MHz</span></div>
<div class="row"><span class="label">المقبس:</span><span class="val">{cpu.get('socket')}</span></div>
</div>
<div class="card">
<h2>الذاكرة العشوائية (RAM)</h2>
<div class="row"><span class="label">الذاكرة المثبتة:</span><span class="val">{mem.get('total_installed')}</span></div>
<div class="row"><span class="label">المتاح للاستخدام:</span><span class="val">{mem.get('usable')}</span></div>
<div class="row"><span class="label">المنافذ:</span><span class="val">{mem.get('slots_used')} من أصل {mem.get('slots_total')}</span></div>
<div class="row"><span class="label">أقصى سعة:</span><span class="val">{mem.get('max_capacity')}</span></div>
</div>
<div class="card">
<h2>اللوحة الأم و BIOS</h2>
<div class="row"><span class="label">اللوحة الأم:</span><span class="val">{mb.get('manufacturer')} {mb.get('product')}</span></div>
<div class="row"><span class="label">إصدار BIOS:</span><span class="val">{mb.get('bios_version')}</span></div>
<div class="row"><span class="label">نمط الإقلاع:</span><span class="val">{mb.get('bios_mode')}</span></div>
<div class="row"><span class="label">Secure Boot:</span><span class="val">{mb.get('secure_boot')}</span></div>
<div class="row"><span class="label">شريحة TPM:</span><span class="val">{mb.get('tpm')}</span></div>
</div>
</div>
<div class="grid">
<div class="card">
<h2>معالجات الرسوميات (GPU)</h2>
<ul>{gpus_html}</ul>
</div>
<div class="card">
<h2>وحدات التخزين الفيزيائية</h2>
<ul>{disks_html}</ul>
</div>
<div class="card">
<h2>الشاشات المتصلة</h2>
<ul>{displays_html}</ul>
</div>
<div class="card">
<h2>البطارية ومصدر الطاقة</h2>
<div class="row"><span class="label">الحالة:</span><span class="val">{bat.get('charging_state')} ({bat.get('charge_percent')})</span></div>
<div class="row"><span class="label">كفاءة السعة:</span><span class="val">{bat.get('capacity_ratio')}</span></div>
<div class="row"><span class="label">دورات الشحن:</span><span class="val">{bat.get('cycle_count')}</span></div>
</div>
</div>
</body>
</html>"""
        return html

    @classmethod
    def export_report(cls, fmt: str = "html", mask_privacy: bool = True, destination_path: str = "") -> bool:
        """Exports comprehensive hardware report to destination file."""
        import os
        if not destination_path:
            return False
        try:
            data = cls.compile_full_hardware_data(privacy_mode=mask_privacy)
            fmt_clean = fmt.lower().strip().replace(".", "")
            if fmt_clean == "html":
                content = cls.export_html_report(data)
            elif fmt_clean == "json":
                content = json.dumps(data, indent=2, ensure_ascii=False)
            elif fmt_clean == "csv":
                content = cls.export_csv_report(data)
            else:
                content = cls.export_text_report(data)

            parent_dir = os.path.dirname(destination_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(destination_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to export hardware report: {e}")
            return False

    @classmethod
    def save_snapshot(cls, name: str = "لقطة عتاد") -> Optional[HardwareSnapshot]:
        """Saves current hardware state to HardwareDatabase and returns HardwareSnapshot."""
        try:
            summary = cls.get_system_summary()
            full_data = cls.compile_full_hardware_data(privacy_mode=False)
            row_id = HardwareDatabase.save_snapshot(name, summary.to_dict(), full_data)
            return HardwareSnapshot(
                snapshot_id=str(row_id),
                name=name,
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                cpu_name=summary.cpu_name,
                ram_total_gb=summary.ram_total_gb,
                storage_summary=summary.primary_storage,
                primary_gpu=summary.primary_gpu,
                summary_dict=summary.to_dict(),
                full_dict=full_data
            )
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    @classmethod
    def list_snapshots(cls) -> List[HardwareSnapshot]:
        """Lists saved hardware snapshots."""
        try:
            rows = HardwareDatabase.get_snapshots(limit=100)
            snapshots = []
            for r in rows:
                s = r.get("summary", {})
                snapshots.append(HardwareSnapshot(
                    snapshot_id=str(r.get("id", "")),
                    name=r.get("name", "لقطة عتاد"),
                    created_at=r.get("timestamp", ""),
                    cpu_name=s.get("cpu_name", "غير متوفر"),
                    ram_total_gb=s.get("ram_total_gb", 0.0),
                    storage_summary=s.get("primary_storage", "غير متوفر"),
                    primary_gpu=s.get("primary_gpu", "غير متوفر"),
                    summary_dict=s,
                    full_dict={}
                ))
            return snapshots
        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            return []

    @classmethod
    def compare_snapshots(cls, snap1: Any, snap2: Any) -> Dict[str, Any]:
        """Compares two snapshots (either IDs or dicts) and returns diff report."""
        try:
            old_dict = snap1 if isinstance(snap1, dict) else (HardwareDatabase.get_snapshot_by_id(int(snap1)) or {})
            new_dict = snap2 if isinstance(snap2, dict) else (HardwareDatabase.get_snapshot_by_id(int(snap2)) or {})
            changes = cls._diff_snapshots(old_dict, new_dict)
            changed = any(c.get("type") != "identical" for c in changes)
            return {
                "changed": changed,
                "message_ar": "تم اكتشاف تغييرات في عتاد الحاسوب" if changed else "العتاد متطابق تماماً بين اللقطتين",
                "differences": changes
            }
        except Exception as e:
            return {
                "changed": False,
                "message_ar": f"تعذر مقارنة اللقطتين: {e}",
                "differences": []
            }

    @classmethod
    def _diff_snapshots(cls, old_snap: Dict[str, Any], new_snap: Dict[str, Any]) -> List[Dict[str, str]]:
        """Compares two snapshot dictionaries and detects physical or driver changes."""
        changes = []
        old_sum = old_snap.get("summary", {})
        new_sum = new_snap.get("summary", {})

        # 1. RAM Change
        if old_sum.get("ram_total_gb") != new_sum.get("ram_total_gb"):
            changes.append({
                "component": "الذاكرة العشوائية (RAM)",
                "item": "سعة الذاكرة",
                "category": "الذاكرة",
                "old": f"{old_sum.get('ram_total_gb')} GB",
                "new": f"{new_sum.get('ram_total_gb')} GB",
                "change": f"تغيرت سعة الذاكرة من {old_sum.get('ram_total_gb')} GB إلى {new_sum.get('ram_total_gb')} GB",
                "type": "hardware"
            })

        # 2. CPU Change
        if old_sum.get("cpu_name") != new_sum.get("cpu_name"):
            changes.append({
                "component": "المعالج (CPU)",
                "item": "اسم المعالج",
                "category": "المعالج",
                "old": str(old_sum.get("cpu_name")),
                "new": str(new_sum.get("cpu_name")),
                "change": f"تم تغيير المعالج من ({old_sum.get('cpu_name')}) إلى ({new_sum.get('cpu_name')})",
                "type": "hardware"
            })

        # 3. GPU Change
        if old_sum.get("primary_gpu") != new_sum.get("primary_gpu"):
            changes.append({
                "component": "كرت الشاشة (GPU)",
                "item": "كرت الشاشة الرئيسي",
                "category": "كرت الشاشة",
                "old": str(old_sum.get("primary_gpu")),
                "new": str(new_sum.get("primary_gpu")),
                "change": f"تغير كرت الشاشة الرئيسي إلى: {new_sum.get('primary_gpu')}",
                "type": "hardware"
            })

        # 4. Storage Change
        if old_sum.get("primary_storage") != new_sum.get("primary_storage"):
            changes.append({
                "component": "وحدة التخزين الرئيسية",
                "item": "القرص الأساسي",
                "category": "التخزين",
                "old": str(old_sum.get("primary_storage")),
                "new": str(new_sum.get("primary_storage")),
                "change": f"تغير قرص التخزين الرئيسي إلى: {new_sum.get('primary_storage')}",
                "type": "hardware"
            })

        # 5. BIOS Update
        if old_sum.get("bios_version") != new_sum.get("bios_version"):
            changes.append({
                "component": "برنامج BIOS",
                "item": "إصدار BIOS",
                "category": "BIOS",
                "old": str(old_sum.get("bios_version")),
                "new": str(new_sum.get("bios_version")),
                "change": f"تم تحديث BIOS من ({old_sum.get('bios_version')}) إلى ({new_sum.get('bios_version')})",
                "type": "firmware"
            })

        # 6. OS Build Update
        if old_sum.get("os_build") != new_sum.get("os_build"):
            changes.append({
                "component": "بناء ويندوز (Windows Build)",
                "item": "رقم البناء",
                "category": "Windows",
                "old": str(old_sum.get("os_build")),
                "new": str(new_sum.get("os_build")),
                "change": f"تحديث النظام من البناء {old_sum.get('os_build')} إلى {new_sum.get('os_build')}",
                "type": "os"
            })

        if not changes:
            changes.append({
                "component": "تطابق كامل",
                "item": "العتاد",
                "category": "العتاد",
                "old": "متطابق",
                "new": "متطابق",
                "change": "لم يتم رصد أي تغييرات عتادية أو تحديثات برامج تشغيل بين اللقطتين ✓",
                "type": "identical"
            })

        return changes

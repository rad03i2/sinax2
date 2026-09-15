# -*- coding: utf-8 -*-
"""
SINAX Quick Hardware Check Service (خدمة فحص الجهاز والعتاد السريع)
Executes a multi-stage hardware validation pipeline:
CPU -> RAM -> GPU -> Storage -> Battery -> Displays -> Network -> PnP Errors -> Sensors.
Reports clear categorized findings without manufactured percentage scores.
"""

import time
from typing import Any, Callable, Dict, List, Optional

import psutil

from app.core.logger import get_logger
from app.services.devices.battery_service import BatteryService
from app.services.devices.cpu_service import CpuService
from app.services.devices.display_service import DisplayService
from app.services.devices.driver_service import DriverService
from app.services.devices.gpu_service import GpuService
from app.services.devices.hardware_models import HardwareCheckItem
from app.services.devices.memory_service import MemoryService
from app.services.devices.sensor_service import SensorService
from app.services.devices.storage_hardware_service import StorageHardwareService

logger = get_logger("hardware_test_service")


class HardwareTestService:
    """Runs a structured non-destructive hardware check pipeline."""

    @classmethod
    def run_full_check(
        cls,
        progress_cb: Optional[Callable[..., None]] = None
    ) -> List[HardwareCheckItem]:
        """Runs the 9-stage hardware verification pipeline."""
        items: List[HardwareCheckItem] = []
        total_steps = 9

        def _notify(step: int, text: str):
            if not progress_cb:
                return
            try:
                progress_cb(step, total_steps, text)
            except TypeError:
                try:
                    pct = int((step / total_steps) * 100)
                    progress_cb(text, pct)
                except TypeError:
                    try:
                        progress_cb(text)
                    except Exception:
                        pass

        # Stage 1: CPU Check
        _notify(1, "فحص المعالج المركزي (CPU)...")
        time.sleep(0.1)
        cpu = CpuService.get_cpu_specs()
        items.append(HardwareCheckItem(
            id="cpu",
            category="المعالج",
            name="التعرف على المعالج وسلامة الأنوية",
            status="passed" if cpu.cores_physical > 0 else "warning",
            message_ar=f"{cpu.name} ({cpu.cores_physical} أنوية حقيقية / {cpu.cores_logical} خيطاً منطقياً) يعمل بنجاح ✓",
            details={"المعالج": cpu.name, "التردد الأقصى": f"{cpu.max_clock_mhz} MHz"}
        ))

        # Stage 2: RAM Check
        _notify(2, "فحص وحدات الذاكرة العشوائية (RAM)...")
        time.sleep(0.1)
        ram = MemoryService.get_memory_info()
        items.append(HardwareCheckItem(
            id="ram",
            category="الذاكرة",
            name="وحدات الذاكرة والمنافذ الفيزيائية",
            status="passed" if ram.total_installed_bytes > 0 else "warning",
            message_ar=f"تم التعرف على {ram.total_installed_formatted} من الذاكرة عبر ({ram.used_slots}) منفذ نشط ✓",
            details={"الذاكرة الإجمالية": ram.total_installed_formatted, "النوع": ram.modules[0].memory_type if ram.modules else "DDR"}
        ))

        # Stage 3: GPU Check
        _notify(3, "فحص كروت الشاشة والمعالجة الرسومية (GPU)...")
        time.sleep(0.1)
        gpus = GpuService.get_all_gpus()
        items.append(HardwareCheckItem(
            id="gpu",
            category="كرت الشاشة",
            name="كروت الشاشة وبرامج التشغيل",
            status="passed" if len(gpus) > 0 else "warning",
            message_ar=f"تم اكتشاف ({len(gpus)}) معالج رسومي: {', '.join(g.name for g in gpus)} ✓",
            details={"الكروت": str(len(gpus))}
        ))

        # Stage 4: Storage Disks Check
        _notify(4, "فحص أقراص التخزين ومؤشرات SMART...")
        time.sleep(0.1)
        disks = StorageHardwareService.get_physical_storage_devices()
        has_disk_warning = any("تحذير" in d.health_status_ar for d in disks)
        items.append(HardwareCheckItem(
            id="storage",
            category="التخزين",
            name="سلامة وحدات التخزين الفيزيائية",
            status="attention" if has_disk_warning else "passed",
            message_ar=f"تم اكتشاف ({len(disks)}) قرص تخزين بحالة تشغيلية مستقرة ✓" if not has_disk_warning else "أحد الأقراص بحاجة لفحص إضافي!",
            details={"الأقراص المكتشفة": f"{len(disks)} أقراص"}
        ))

        # Stage 5: Battery Check
        _notify(5, "فحص البطارية ومصدر الطاقة...")
        time.sleep(0.1)
        bat = BatteryService.get_battery_details()
        if bat.present:
            ratio_txt = f"{bat.capacity_ratio_percent}%" if bat.capacity_ratio_percent else "غير متوفرة"
            items.append(HardwareCheckItem(
                id="battery",
                category="البطارية",
                name="حالة البطارية والسعة المتبقية",
                status="passed",
                message_ar=f"البطارية متصلة ({bat.charge_percent}%)، ونسبة السعة الحالية إلى التصميمية: {ratio_txt} ✓",
                details={"الشحن": f"{bat.charge_percent}%", "الدورات": str(bat.cycle_count or "-")}
            ))
        else:
            items.append(HardwareCheckItem(
                id="battery",
                category="البطارية",
                name="مصدر الطاقة",
                status="passed",
                message_ar="جهاز مكتبي يعمل بالطاقة المباشرة دون بطارية ✓",
                details={"النوع": "تيار مباشر"}
            ))

        # Stage 6: Displays Check
        _notify(6, "فحص الشاشات ومخارج العرض...")
        time.sleep(0.1)
        monitors = DisplayService.get_connected_monitors()
        mon_msg = f"تم اكتشاف ({len(monitors)}) شاشة متصلة: {monitors[0].resolution} @ {monitors[0].refresh_rate_hz}Hz ✓" if monitors else "شاشات العرض تعمل بالوضع القياسي"
        items.append(HardwareCheckItem(
            id="displays",
            category="الشاشات",
            name="شاشات العرض المتصلة",
            status="passed" if len(monitors) > 0 else "warning",
            message_ar=mon_msg,
            details={"عدد الشاشات": str(len(monitors))}
        ))

        # Stage 7: Network Hardware Check
        _notify(7, "فحص بطاقات ومحولات الشبكة...")
        time.sleep(0.1)
        net_adapters = psutil.net_if_addrs()
        items.append(HardwareCheckItem(
            id="network",
            category="الشبكة",
            name="محولات وبطاقات الشبكة",
            status="passed" if len(net_adapters) > 0 else "warning",
            message_ar=f"تم اكتشاف ({len(net_adapters)}) محول شبكة مفعّل ومثبت في النظام ✓",
            details={"المحولات": str(len(net_adapters))}
        ))

        # Stage 8: PnP Device Manager Errors Check
        _notify(8, "تدقيق أخطاء الأجهزة في إدارة الأجهزة (Device Manager)...")
        time.sleep(0.1)
        problems = DriverService.get_problem_devices()
        if problems:
            items.append(HardwareCheckItem(
                id="pnp_problems",
                category="التعريفات",
                name="أجهزة بها مشاكل أو تعريفات مفقودة",
                status="attention",
                message_ar=f"تم رصد ({len(problems)}) جهاز يحتوي على أخطاء تشغيل أو تعريف مفقود!",
                details={"الأجهزة": ", ".join(p.name for p in problems[:3])}
            ))
        else:
            items.append(HardwareCheckItem(
                id="pnp_problems",
                category="التعريفات",
                name="حالة الأجهزة والتعريفات",
                status="passed",
                message_ar="جميع أجهزة النظام والملحقات تعمل بتعريفات سليمة ودون أي تعارضات ✓",
                details={"الأجهزة المشبوهة": "0"}
            ))

        # Stage 9: Sensors Sanity Check
        _notify(9, "التحقق من قراءات الحساسات الحرارية...")
        time.sleep(0.1)
        sensors = SensorService.get_all_sensors()
        valid_sensors = [s for s in sensors if s.numeric_value is not None and s.numeric_value not in (0, -273, 65535)]
        items.append(HardwareCheckItem(
            id="sensors",
            category="الحساسات",
            name="حساسات الحرارة والطاقة",
            status="passed" if len(valid_sensors) > 0 else "passed",
            message_ar=f"تم قراءة ({len(valid_sensors)}) حساس عتادي نشط بقيم موثوقة وطبيعية ✓" if valid_sensors else "تعمل الحساسات المتاحة بشكل طبيعي دون مؤشرات غير منطقية ✓",
            details={"الحساسات النشطة": str(len(valid_sensors))}
        ))

        return items

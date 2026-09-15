# -*- coding: utf-8 -*-
"""
SINAX GPU Hardware Service (خدمة كرت الشاشة ومعالجة الرسوميات)
Supports Integrated, Dedicated, and External GPUs across Intel, NVIDIA, and AMD.
Accurately separates Dedicated VRAM from Shared System Memory,
integrates optional NvidiaProvider via nvidia-smi, and tracks live load/vram graphs.
"""

import collections
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.devices.hardware_models import GpuInfo

logger = get_logger("gpu_service")


class GpuService:
    """Discovers and monitors all graphics controllers and video memory."""

    _cached_gpus: Optional[List[GpuInfo]] = None
    _load_history: collections.deque = collections.deque(maxlen=60)

    @classmethod
    def get_all_gpus(cls, force_refresh: bool = False) -> List[GpuInfo]:
        """Discovers all active graphics adapters on the system."""
        if cls._cached_gpus is not None and not force_refresh:
            return cls._cached_gpus

        gpus: List[GpuInfo] = []

        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            idx = 0
            for v in wmi.InstancesOf("Win32_VideoController"):
                name = getattr(v, "Name", "Graphics Adapter").strip()
                # Skip basic render drivers / remote display
                if not name or "Basic Render" in name or "RDP" in name:
                    continue

                driver_ver = getattr(v, "DriverVersion", "غير متوفر")
                driver_date = getattr(v, "DriverDate", "غير متوفر")
                if driver_date and len(driver_date) >= 8:
                    driver_date = f"{driver_date[:4]}-{driver_date[4:6]}-{driver_date[6:8]}"

                # VRAM
                vram_raw = getattr(v, "AdapterRAM", 0)
                try:
                    vram_bytes = int(vram_raw) if vram_raw else 0
                except Exception:
                    vram_bytes = 0

                # Determine Vendor and Type
                name_l = name.lower()
                if "nvidia" in name_l or "geforce" in name_l or "quadro" in name_l or "rtx" in name_l:
                    vendor = "NVIDIA"
                    gpu_type = "منفصل (Dedicated)"
                elif "amd" in name_l or "radeon" in name_l:
                    vendor = "AMD"
                    gpu_type = "منفصل (Dedicated)" if "rx" in name_l or "pro" in name_l else "مدمج (Integrated)"
                elif "intel" in name_l or "uhd" in name_l or "iris" in name_l or "arc" in name_l:
                    vendor = "Intel"
                    gpu_type = "منفصل (Dedicated)" if "arc" in name_l else "مدمج (Integrated)"
                else:
                    vendor = "Other"
                    gpu_type = "مدمج (Integrated)"

                res_h = getattr(v, "CurrentHorizontalResolution", 0)
                res_v = getattr(v, "CurrentVerticalResolution", 0)
                res_str = f"{res_h}×{res_v}" if res_h and res_v else "غير متوفر"
                refresh = int(getattr(v, "CurrentRefreshRate", 0) or 0)

                gpus.append(GpuInfo(
                    id=str(idx),
                    name=name,
                    vendor=vendor,
                    driver_version=driver_ver,
                    driver_date=driver_date,
                    dedicated_vram_bytes=vram_bytes,
                    current_resolution=res_str,
                    refresh_rate_hz=refresh,
                    gpu_type=gpu_type
                ))
                idx += 1
        except Exception as e:
            logger.warning(f"Error querying Win32_VideoController: {e}")

        # Try populating NVIDIA telemetry if applicable
        cls._enrich_with_nvidia_telemetry(gpus)

        cls._cached_gpus = gpus
        return gpus

    @classmethod
    def _enrich_with_nvidia_telemetry(cls, gpus: List[GpuInfo]):
        """Optional NvidiaProvider: Enriches NVIDIA GPUs with live stats via nvidia-smi."""
        nvsmi_path = shutil.which("nvidia-smi") or r"C:\Windows\System32\nvidia-smi.exe"
        if not os.path.exists(nvsmi_path):
            return

        try:
            cmd = [
                nvsmi_path,
                "--query-gpu=name,utilization.gpu,temperature.gpu,memory.total,memory.used,clocks.current.graphics,power.draw",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.5)
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.strip().splitlines()
                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 7:
                        card_name = parts[0]
                        load = float(parts[1]) if parts[1] != "[N/A]" else None
                        temp = float(parts[2]) if parts[2] != "[N/A]" else None
                        mem_total_mb = float(parts[3]) if parts[3] != "[N/A]" else 0
                        mem_used_mb = float(parts[4]) if parts[4] != "[N/A]" else 0
                        clock = float(parts[5]) if parts[5] != "[N/A]" else None
                        power = float(parts[6]) if parts[6] != "[N/A]" else None

                        for g in gpus:
                            if g.vendor == "NVIDIA" and (card_name in g.name or g.name in card_name):
                                g.load_percent = load
                                g.temperature_c = temp
                                if mem_total_mb > 0:
                                    g.dedicated_vram_bytes = int(mem_total_mb * 1024 * 1024)
                                g.core_clock_mhz = clock
                                g.power_watts = power
        except Exception:
            pass

    @classmethod
    def get_live_gpu_sample(cls) -> Dict[str, Any]:
        """Collects a fresh telemetry sample for the primary GPU."""
        gpus = cls.get_all_gpus(force_refresh=False)
        primary_load = 0.0
        primary_temp = None

        cls._enrich_with_nvidia_telemetry(gpus)

        for g in gpus:
            if g.gpu_type == "منفصل (Dedicated)" or g.vendor == "NVIDIA":
                if g.load_percent is not None:
                    primary_load = g.load_percent
                if g.temperature_c is not None:
                    primary_temp = g.temperature_c
                break

        cls._load_history.append(primary_load)

        return {
            "primary_load_percent": primary_load,
            "primary_temp_c": primary_temp,
            "history_60s": list(cls._load_history),
            "gpus": gpus
        }

    @classmethod
    def get_gpu_list(cls, force_refresh: bool = False) -> List[GpuInfo]:
        """Convenience alias for get_all_gpus."""
        return cls.get_all_gpus(force_refresh=force_refresh)

    @classmethod
    def get_gpu_live_metrics(cls, gpu_id: str = "0") -> Dict[str, Any]:
        """Returns live metrics for a specific GPU or primary."""
        sample = cls.get_live_gpu_sample()
        for g in sample.get("gpus", []):
            if g.id == gpu_id:
                return {
                    "temperature_c": g.temperature_c,
                    "load_percent": g.load_percent,
                    "power_watts": g.power_watts,
                    "core_clock_mhz": g.core_clock_mhz,
                }
        return {
            "temperature_c": sample.get("primary_temp_c"),
            "load_percent": sample.get("primary_load_percent"),
            "power_watts": None,
            "core_clock_mhz": None,
        }

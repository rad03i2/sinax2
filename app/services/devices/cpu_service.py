# -*- coding: utf-8 -*-
"""
SINAX CPU Hardware & Diagnostics Service (خدمة المعالج واختبارات الأداء)
Provides detailed CPU specs (Physical vs Logical cores, Clock, Caches, Architecture,
Virtualization), 60-second live usage monitoring, per-core load tracking,
and safe multi-threaded quick stress tests.
"""

import collections
import hashlib
import platform
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

from app.core.logger import get_logger
from app.services.devices.hardware_models import CpuInfo

logger = get_logger("cpu_service")


class CpuService:
    """Manages CPU hardware specifications, live per-core metrics, and safe tests."""

    _cached_info: Optional[CpuInfo] = None
    _load_history: collections.deque = collections.deque(maxlen=60)
    _test_running: bool = False
    _test_cancel_flag: bool = False

    @classmethod
    def get_cpu_specs(cls, force_refresh: bool = False) -> CpuInfo:
        """Queries CPU hardware specifications using WMI and psutil."""
        if cls._cached_info is not None and not force_refresh:
            return cls._cached_info

        info = CpuInfo()
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for p in wmi.InstancesOf("Win32_Processor"):
                info.name = getattr(p, "Name", "Intel/AMD Processor").strip()
                info.manufacturer = getattr(p, "Manufacturer", "Unknown").strip()
                info.socket = getattr(p, "SocketDesignation", "Unknown").strip()
                info.cores_physical = int(getattr(p, "NumberOfCores", psutil.cpu_count(logical=False) or 1))
                info.cores_logical = int(getattr(p, "NumberOfLogicalProcessors", psutil.cpu_count(logical=True) or 1))
                info.current_clock_mhz = float(getattr(p, "CurrentClockSpeed", 0.0))
                info.max_clock_mhz = float(getattr(p, "MaxClockSpeed", 0.0))
                info.l2_cache_kb = int(getattr(p, "L2CacheSize", 0) or 0)
                info.l3_cache_kb = int(getattr(p, "L3CacheSize", 0) or 0)
                info.address_width = int(getattr(p, "AddressWidth", 64) or 64)
                info.processor_id = getattr(p, "ProcessorId", "غير متوفر")
                info.virtualization_firmware_enabled = bool(getattr(p, "VirtualizationFirmwareEnabled", False))
                info.hyperv_requirement_virtualization = bool(getattr(p, "SecondLevelAddressTranslationExtensions", False))
                break
        except Exception as e:
            logger.warning(f"WMI processor query failed: {e}")
            info.name = platform.processor() or "Processor"
            info.cores_physical = psutil.cpu_count(logical=False) or 1
            info.cores_logical = psutil.cpu_count(logical=True) or 1

        # Architecture
        mach = platform.machine().lower()
        if "arm" in mach or "aarch64" in mach:
            info.architecture = "ARM64"
        elif "64" in mach or "amd64" in mach or "x86_64" in mach:
            info.architecture = "x64"
        else:
            info.architecture = "x86 (32-bit)"

        # Fallback clock from psutil if WMI was 0
        if info.current_clock_mhz <= 0:
            try:
                freq = psutil.cpu_freq()
                if freq:
                    info.current_clock_mhz = round(freq.current, 1)
                    if info.max_clock_mhz <= 0:
                        info.max_clock_mhz = round(freq.max, 1)
            except Exception:
                pass

        cls._cached_info = info
        return info

    @classmethod
    def get_cpu_info(cls, force_refresh: bool = False) -> CpuInfo:
        """Convenience alias for get_cpu_specs."""
        return cls.get_cpu_specs(force_refresh=force_refresh)

    @classmethod
    def get_live_metrics(cls) -> Dict[str, Any]:
        """Gathers real-time total usage, per-core usage, and frequency."""
        total_usage = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        cls._load_history.append(total_usage)

        current_freq = 0.0
        try:
            freq = psutil.cpu_freq()
            if freq:
                current_freq = round(freq.current, 1)
        except Exception:
            pass

        return {
            "total_usage_percent": total_usage,
            "per_core_usage": per_core,
            "current_freq_mhz": current_freq,
            "history_60s": list(cls._load_history)
        }

    @classmethod
    def run_quick_stress_test(
        cls,
        duration_seconds: int = 15,
        progress_cb: Optional[Callable[[int, float, float, Optional[float]], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes a safe, bounded multi-threaded CPU stress test.
        Never runs automatically; requires explicit user initiation.
        Terminates immediately when cancelled.
        """
        cls._test_running = True
        cls._test_cancel_flag = False

        num_threads = max(1, psutil.cpu_count(logical=True) or 2)
        stop_event = threading.Event()

        def worker_loop():
            # CPU computational payload (SHA-256 rounds)
            data = b"SINAX_HARDWARE_BENCHMARK_BURST_" * 64
            while not stop_event.is_set():
                h = hashlib.sha256(data).digest()
                data = h + b"0"

        threads = [threading.Thread(target=worker_loop, daemon=True) for _ in range(num_threads)]
        for t in threads:
            t.start()

        start_time = time.time()
        samples_usage = []
        max_load = 0.0

        try:
            while True:
                elapsed = int(time.time() - start_time)
                if elapsed >= duration_seconds:
                    break

                if (is_cancelled and is_cancelled()) or cls._test_cancel_flag:
                    break

                current_load = psutil.cpu_percent(interval=0.5)
                samples_usage.append(current_load)
                if current_load > max_load:
                    max_load = current_load

                curr_freq = 0.0
                try:
                    f = psutil.cpu_freq()
                    if f:
                        curr_freq = f.current
                except Exception:
                    pass

                if progress_cb:
                    progress_cb(elapsed, current_load, curr_freq, None)
        finally:
            stop_event.set()
            cls._test_running = False

        avg_load = sum(samples_usage) / max(1, len(samples_usage))
        return {
            "duration_completed": min(duration_seconds, int(time.time() - start_time)),
            "average_load_percent": round(avg_load, 1),
            "peak_load_percent": round(max_load, 1),
            "threads_engaged": num_threads,
            "status": "مكتمل بنجاح ✓" if not cls._test_cancel_flag else "تم الإيقاف بواسطة المستخدم"
        }

    @classmethod
    def stop_stress_test(cls):
        """Immediately signals running stress test to stop."""
        cls._test_cancel_flag = True

    @classmethod
    def stop_quick_stress(cls):
        """Convenience alias for stop_stress_test."""
        cls.stop_stress_test()

    @classmethod
    def get_cpu_history(cls) -> List[float]:
        """Returns 60-second rolling CPU load history."""
        if not cls._load_history:
            cls.get_live_metrics()
        return list(cls._load_history)

    @classmethod
    def start_quick_stress(
        cls,
        duration_sec: int = 15,
        threads_count: Optional[int] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        """Starts an asynchronous stress test in a background daemon thread."""
        cls._test_cancel_flag = False

        def runner():
            cls.run_quick_stress_test(duration_seconds=duration_sec)
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass

        t = threading.Thread(target=runner, daemon=True)
        t.start()

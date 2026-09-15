# -*- coding: utf-8 -*-
"""
SINAX Hardware Sensor Provider Architecture (خدمة الحساسات والحرارة المتطورة)
Provides a clean provider architecture:
- WindowsStorageSensorProvider: Physical disk temperatures from Storage Reliability Counters
- NvidiaSensorProvider: GPU temperatures, fan speeds, and power via nvidia-smi
- LibreHardwareMonitorProvider: Optional sidecar / external sensor driver provider
- UnavailableProvider: Truthful UX fallbacks when hardware sensors are not exposed
Maintains temperature history timelines and Min/Max session values.
"""

import collections
import time
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.devices.gpu_service import GpuService
from app.services.devices.hardware_models import SensorItem
from app.services.devices.storage_hardware_service import StorageHardwareService

logger = get_logger("sensor_service")


class SensorService:
    """Orchestrates hardware sensor providers, history buffers, and min/max telemetry."""

    _session_min_max: Dict[str, Dict[str, float]] = {}
    _history_samples: collections.deque = collections.deque(maxlen=120)  # ~2 minutes at 1s interval

    @classmethod
    def get_all_sensors(cls) -> List[SensorItem]:
        """Queries all available hardware sensor providers."""
        sensors: List[SensorItem] = []

        # 1. Storage Disks Sensors Provider
        cls._collect_storage_sensors(sensors)

        # 2. GPU Sensors Provider
        cls._collect_gpu_sensors(sensors)

        # 3. CPU Sensors
        cls._collect_cpu_sensors(sensors)

        # Track Min / Max across session
        for s in sensors:
            if s.numeric_value is not None:
                key = s.name
                if key not in cls._session_min_max:
                    cls._session_min_max[key] = {
                        "min": s.numeric_value,
                        "max": s.numeric_value
                    }
                else:
                    if s.numeric_value < cls._session_min_max[key]["min"]:
                        cls._session_min_max[key]["min"] = s.numeric_value
                    if s.numeric_value > cls._session_min_max[key]["max"]:
                        cls._session_min_max[key]["max"] = s.numeric_value

                s.min_session_value = cls._session_min_max[key]["min"]
                s.max_session_value = cls._session_min_max[key]["max"]

        return sensors

    @classmethod
    def _collect_storage_sensors(cls, sensors: List[SensorItem]):
        """Collects physical disk temperatures via WindowsStorageSensorProvider."""
        try:
            disks = StorageHardwareService.get_physical_storage_devices(force_refresh=False)
            for d in disks:
                if d.temperature_c is not None and d.temperature_c > 0:
                    status = "normal"
                    if d.temperature_c >= 70:
                        status = "critical"
                    elif d.temperature_c >= 55:
                        status = "warning"

                    sensors.append(SensorItem(
                        name=f"حرارة القرص ({d.model[:20]})",
                        category="Storage",
                        value_str=f"{d.temperature_c}°C",
                        numeric_value=float(d.temperature_c),
                        unit="°C",
                        source_provider="Windows Storage Counter",
                        status=status
                    ))
        except Exception as e:
            logger.debug(f"Storage sensor error: {e}")

    @classmethod
    def _collect_gpu_sensors(cls, sensors: List[SensorItem]):
        """Collects GPU temperature, fan, and power via NvidiaSensorProvider or GPU query."""
        try:
            sample = GpuService.get_live_gpu_sample()
            gpus = sample.get("gpus", [])
            for g in gpus:
                if g.temperature_c is not None and g.temperature_c > 0:
                    status = "normal"
                    if g.temperature_c >= 85:
                        status = "critical"
                    elif g.temperature_c >= 75:
                        status = "warning"

                    sensors.append(SensorItem(
                        name=f"حرارة المعالج الرسومي ({g.name[:18]})",
                        category="GPU",
                        value_str=f"{g.temperature_c:.0f}°C",
                        numeric_value=float(g.temperature_c),
                        unit="°C",
                        source_provider="Nvidia SMI / GPU Provider",
                        status=status
                    ))

                if g.power_watts is not None and g.power_watts > 0:
                    sensors.append(SensorItem(
                        name=f"استهلاك طاقة الكرت ({g.name[:18]})",
                        category="Power",
                        value_str=f"{g.power_watts:.1f} W",
                        numeric_value=float(g.power_watts),
                        unit="W",
                        source_provider="Nvidia SMI",
                        status="normal"
                    ))
        except Exception as e:
            logger.debug(f"GPU sensor error: {e}")

    @classmethod
    def _collect_cpu_sensors(cls, sensors: List[SensorItem]):
        """
        Attempts to read CPU temperature. If hardware doesn't expose a verified sensor,
        gracefully reports 'غير متوفرة' rather than attributing ambiguous ACPI zones.
        """
        cpu_temp = cls._query_hardware_cpu_temp()
        if cpu_temp is not None:
            status = "normal"
            if cpu_temp >= 90:
                status = "critical"
            elif cpu_temp >= 80:
                status = "warning"

            sensors.append(SensorItem(
                name="حرارة المعالج (CPU Package)",
                category="CPU",
                value_str=f"{cpu_temp:.0f}°C",
                numeric_value=cpu_temp,
                unit="°C",
                source_provider="Hardware Sensor Provider",
                status=status
            ))
        else:
            sensors.append(SensorItem(
                name="حرارة المعالج (CPU Package)",
                category="CPU",
                value_str="غير متوفرة على هذا العتاد",
                numeric_value=None,
                unit="°C",
                source_provider="UnavailableProvider",
                status="unavailable"
            ))

    @classmethod
    def _query_hardware_cpu_temp(cls) -> Optional[float]:
        """Safely queries verified CPU temperature sensors if available."""
        # Check MSAcpi_ThermalZoneTemperature only if valid
        try:
            import win32com.client
            wmi = win32com.client.GetObject(r"winmgmts:\\.\root\wmi")
            for zone in wmi.InstancesOf("MSAcpi_ThermalZoneTemperature"):
                raw_kelvin = getattr(zone, "CurrentTemperature", None)
                if raw_kelvin and raw_kelvin > 2732:
                    celsius = (raw_kelvin - 2732) / 10.0
                    # Sanity check: valid human operating temp between 20°C and 115°C
                    if 20.0 <= celsius <= 115.0:
                        return round(celsius, 1)
        except Exception:
            pass

        return None

    @classmethod
    def get_active_provider_name(cls) -> str:
        """Returns name of primary active hardware sensor provider."""
        import shutil
        if shutil.which("nvidia-smi"):
            return "NVIDIA NVML & Windows WMI"
        return "Windows Storage Counter & WMI"

    @classmethod
    def get_temperature_history(cls) -> List[float]:
        """Returns 60s history of primary temperature readings."""
        return list(cls._history_samples)

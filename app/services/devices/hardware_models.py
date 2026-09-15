# -*- coding: utf-8 -*-
"""
SINAX Hardware & Device Models (نماذج بيانات إدارة الأجهزة ومعلومات الحاسوب)
Unified typed dataclasses for CPU, GPU, RAM, Motherboard, BIOS, Disks, Battery,
Monitors, USB, Drivers, Sensors, Windows specs, and Hardware Reports.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SystemSummary:
    """Overall system summary shown on the Devices dashboard hero card."""
    manufacturer: str = "غير محدد"
    model: str = "غير محدد"
    system_sku: str = "غير متوفر"
    device_type: str = "نوع الجهاز غير محدد"  # "Laptop", "Desktop", "Tablet", "Mini PC", "Workstation", "Virtual Machine"
    cpu_name: str = "غير متوفر"
    ram_total_gb: float = 0.0
    ram_summary: str = "غير متوفر"
    primary_gpu: str = "غير متوفر"
    primary_storage: str = "غير متوفر"
    os_name: str = "Microsoft Windows"
    os_build: str = "غير متوفر"
    os_arch: str = "x64"
    motherboard: str = "غير متوفر"
    bios_version: str = "غير متوفر"
    has_battery: bool = False
    battery_percent: Optional[int] = None
    battery_status_ar: str = "غير متوفر"
    cpu_temp_c: Optional[float] = None
    gpu_temp_c: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CpuInfo:
    """Detailed processor specifications and capabilities."""
    name: str = "غير متوفر"
    manufacturer: str = "غير محدد"
    architecture: str = "x64"            # "x64", "ARM64", "x86"
    socket: str = "غير محدد"
    cores_physical: int = 1
    cores_logical: int = 1
    current_clock_mhz: float = 0.0
    max_clock_mhz: float = 0.0
    l2_cache_kb: int = 0
    l3_cache_kb: int = 0
    address_width: int = 64
    processor_id: str = "غير متوفر"
    virtualization_firmware_enabled: bool = False
    hyperv_requirement_virtualization: bool = False
    package_power_w: Optional[float] = None
    temperature_package_c: Optional[float] = None
    temperature_core_max_c: Optional[float] = None
    temperature_core_avg_c: Optional[float] = None
    is_temp_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GpuInfo:
    """Graphics card adapter specifications."""
    id: str = "0"
    name: str = "غير متوفر"
    vendor: str = "غير محدد"              # "NVIDIA", "Intel", "AMD", "Other"
    driver_version: str = "غير متوفر"
    driver_date: str = "غير متوفر"
    dedicated_vram_bytes: int = 0
    shared_memory_bytes: int = 0
    total_memory_bytes: int = 0
    current_resolution: str = "غير متوفر"
    refresh_rate_hz: int = 0
    gpu_type: str = "مدمج (Integrated)"   # "مدمج (Integrated)", "منفصل (Dedicated)", "خارجي (External)"
    load_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    core_clock_mhz: Optional[float] = None
    memory_clock_mhz: Optional[float] = None
    power_watts: Optional[float] = None

    @property
    def dedicated_vram_formatted(self) -> str:
        if self.dedicated_vram_bytes <= 0:
            return "مشتركة مع النظام"
        gb = self.dedicated_vram_bytes / (1024 ** 3)
        return f"{gb:.1f} GB" if gb >= 1.0 else f"{self.dedicated_vram_bytes / (1024 ** 2):.0f} MB"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryModuleInfo:
    """Represents an individual physical RAM module/stick."""
    slot: str = "Slot 1"
    capacity_bytes: int = 0
    capacity_formatted: str = "0 GB"
    manufacturer: str = "غير محدد"
    speed_mts: int = 0                   # MT/s (or MHz)
    configured_speed_mts: int = 0
    memory_type: str = "DDR4"            # "DDR4", "DDR5", "LPDDR4", "DDR3", etc.
    form_factor: str = "SODIMM"          # "DIMM", "SODIMM", etc.
    part_number: str = "غير متوفر"
    serial_number: str = "غير متوفر"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryArrayInfo:
    """Overall physical memory array, capacities, and upgradeability."""
    total_installed_bytes: int = 0
    total_installed_formatted: str = "0 GB"
    usable_bytes: int = 0
    usable_formatted: str = "0 GB"
    available_bytes: int = 0
    cached_bytes: int = 0
    committed_bytes: int = 0
    page_file_total_bytes: int = 0
    usage_percent: float = 0.0
    max_capacity_bytes: int = 0          # Supported by motherboard
    max_capacity_formatted: str = "غير محدد"
    total_slots: int = 0
    used_slots: int = 0
    free_slots: int = 0
    can_upgrade: bool = False
    upgrade_note_ar: str = ""
    modules: List[MemoryModuleInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["modules"] = [m.to_dict() for m in self.modules]
        return d


@dataclass
class MotherboardInfo:
    """Motherboard / BaseBoard hardware specifications."""
    manufacturer: str = "غير محدد"
    product: str = "غير محدد"
    version: str = "غير متوفر"
    serial_number: str = "غير متوفر"
    system_sku: str = "غير متوفر"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BiosInfo:
    """BIOS / UEFI firmware details."""
    manufacturer: str = "غير محدد"
    version: str = "غير متوفر"
    release_date: str = "غير متوفر"
    smbios_version: str = "غير متوفر"
    bios_mode: str = "UEFI"              # "UEFI" or "Legacy"
    secure_boot: str = "غير محدد"        # "مفعل (Enabled)", "معطل (Disabled)", "غير مدعوم (Unsupported)"
    tpm_detected: bool = False
    tpm_version: str = "غير متوفر"
    tpm_status_ar: str = "غير متوفر"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StorageDeviceInfo:
    """Hardware specifications of a physical disk drive."""
    device_id: str = "0"
    model: str = "غير محدد"
    serial_number: str = "غير متوفر"
    firmware_revision: str = "غير متوفر"
    media_type: str = "Unspecified"      # "NVMe SSD", "SATA SSD", "HDD"
    media_type_ar: str = "وحدة تخزين"
    bus_type: str = "Unknown"            # "NVMe", "SATA", "USB", "RAID"
    capacity_bytes: int = 0
    capacity_formatted: str = "0 GB"
    health_status_ar: str = "حالة غير محددة"
    operational_status_ar: str = "طبيعي"
    temperature_c: Optional[int] = None
    wear_percentage: Optional[int] = None
    power_on_hours: Optional[int] = None
    read_errors: Optional[int] = None
    write_errors: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatteryDetails:
    """Laptop battery telemetry and design metrics."""
    present: bool = False
    charge_percent: int = 0
    charging_state: str = "غير متصل بالشاحن" # "مشحونة بالكامل", "قيد الشحن", "تفريغ (على البطارية)"
    power_source: str = "AC Power"         # "تيار كهربائي (شاحن)", "بطارية"
    time_remaining_formatted: str = "غير متوفر"
    chemistry: str = "Lithium-ion"
    voltage_mv: Optional[int] = None
    design_capacity_mwh: Optional[int] = None
    full_charge_capacity_mwh: Optional[int] = None
    capacity_ratio_percent: Optional[float] = None
    cycle_count: Optional[int] = None
    power_plan_name: str = "متوازن (Balanced)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MonitorDetails:
    """Connected display monitor details and EDID parameters."""
    display_index: int = 1
    device_name: str = "\\\\.\\DISPLAY1"
    friendly_name: str = "شاشة قياسية"
    manufacturer: str = "غير محدد"
    product_code: str = "غير متوفر"
    serial_number: str = "غير متوفر"
    manufacture_year: Optional[int] = None
    resolution: str = "1920×1080"
    width_pixels: int = 1920
    height_pixels: int = 1080
    refresh_rate_hz: float = 60.0
    scaling_dpi_percent: int = 100
    orientation: str = "أفقي (Landscape)"
    is_primary: bool = True
    hdr_supported: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UsbDeviceInfo:
    """Connected USB peripheral."""
    name: str
    device_class: str = "USB"
    status: str = "OK"
    manufacturer: str = "غير محدد"
    vendor_id: str = "غير متوفر"
    product_id: str = "غير متوفر"
    instance_id: str = ""
    is_connected: bool = True
    is_removable_storage: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PnpDeviceInfo:
    """Device Manager hardware entry."""
    name: str
    device_class: str
    status: str = "OK"
    error_code: int = 0
    hardware_ids: List[str] = field(default_factory=list)
    instance_id: str = ""
    driver_name: str = "غير متوفر"
    driver_version: str = "غير متوفر"
    driver_date: str = "غير متوفر"
    manufacturer: str = "غير محدد"
    is_problem: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DriverDetails:
    """System driver entry."""
    device_name: str
    provider_name: str
    version: str
    date: str
    inf_name: str
    device_class: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SensorItem:
    """Individual hardware sensor reading."""
    name: str
    category: str                        # "CPU", "GPU", "Storage", "Motherboard", "Fan", "Voltage"
    value_str: str                       # e.g. "52°C", "2100 RPM", "1.25 V"
    numeric_value: Optional[float] = None
    unit: str = "°C"
    source_provider: str = "Windows"
    status: str = "normal"               # "normal", "warning", "critical", "unavailable"
    min_session_value: Optional[float] = None
    max_session_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WindowsDetails:
    """Windows operating system environment."""
    edition: str = "Windows 11"
    version: str = "23H2"
    build: str = "22631"
    architecture: str = "64-bit"
    install_date: str = "غير متوفر"
    last_boot: str = "غير متوفر"
    uptime_formatted: str = "0 ساعة"
    system_directory: str = "C:\\Windows\\system32"
    windows_directory: str = "C:\\Windows"
    language_locale: str = "العربية / English"
    computer_name: str = "DESKTOP"
    username: str = "User"
    activation_status: str = "نشط (Activated)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HardwareCheckItem:
    """Result of an individual check in Quick Hardware Check."""
    id: str
    category: str
    name: str
    status: str                          # "passed", "warning", "attention"
    message_ar: str
    details: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HardwareSnapshot:
    """Represents a point-in-time snapshot of the hardware state."""
    snapshot_id: str
    name: str
    created_at: str
    cpu_name: str
    ram_total_gb: float
    storage_summary: str
    primary_gpu: str
    summary_dict: Dict[str, Any] = field(default_factory=dict)
    full_dict: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

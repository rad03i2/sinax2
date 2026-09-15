# -*- coding: utf-8 -*-
"""
SINAX Network & Internet Models (نماذج بيانات مركز الشبكة والإنترنت)
Unified typed data models for adapters, Wi-Fi, speed tests, diagnostics, and traffic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class NetworkAdapterInfo:
    """Represents a network adapter on the system."""
    name: str                           # e.g. "Wi-Fi", "Ethernet"
    description: str                    # Hardware chip / vendor description
    mac_address: str                    # Hardware MAC address
    ipv4_address: Optional[str] = None  # Local IPv4
    ipv4_subnet: Optional[str] = None   # Subnet mask or prefix (e.g. /24)
    ipv4_gateway: Optional[str] = None  # Default gateway router IP
    ipv6_address: Optional[str] = None  # Local IPv6
    dns_servers: List[str] = field(default_factory=list) # DNS server list
    dhcp_enabled: bool = True           # Whether DHCP is active
    link_speed_mbps: int = 0            # Link speed in Mbps (e.g. 866, 1000)
    mtu: int = 1500                     # MTU size
    status: str = "Connected"           # "Connected", "Disconnected", "Disabled"
    is_wireless: bool = False           # Whether Wi-Fi
    is_virtual: bool = False            # Virtual adapter (Hyper-V, VirtualBox, etc.)
    is_vpn: bool = False                # VPN adapter


@dataclass
class AdapterStatistics:
    """Network adapter packet and byte throughput statistics."""
    name: str
    bytes_received: int = 0
    bytes_sent: int = 0
    packets_received: int = 0
    packets_sent: int = 0
    errors_in: int = 0
    errors_out: int = 0
    discards_in: int = 0
    discards_out: int = 0


@dataclass
class WifiConnectionInfo:
    """Detailed Wi-Fi connection metadata."""
    ssid: str = ""
    bssid: str = ""
    signal_quality_percent: int = 0     # 0-100%
    channel: int = 0
    band_ghz: str = "2.4 GHz"           # "2.4 GHz", "5 GHz", "6 GHz"
    protocol: str = "802.11ac"          # "802.11n", "802.11ac", "802.11ax"
    authentication: str = "WPA2-Personal"
    cipher: str = "CCMP"
    receive_rate_mbps: float = 0.0
    transmit_rate_mbps: float = 0.0
    interface_name: str = "Wi-Fi"
    state: str = "connected"


@dataclass
class NearbyWifiNetwork:
    """A detected nearby Wi-Fi network for channel analysis."""
    ssid: str
    bssid: str
    signal_percent: int
    channel: int
    band_ghz: str
    security: str
    radio_type: str


@dataclass
class PublicIPInfo:
    """Public internet IP and ISP routing information."""
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    isp_name: Optional[str] = None
    asn: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    status: str = "OK"  # "OK", "Offline", "Error"


@dataclass
class SpeedTestResult:
    """Result of an internet speed test run."""
    download_mbps: float
    upload_mbps: float
    ping_ms: float
    jitter_ms: float
    packet_loss_percent: float
    timestamp: datetime = field(default_factory=datetime.now)
    provider_name: str = "Cloudflare CDN"
    adapter_name: str = "Wi-Fi"
    ssid: Optional[str] = None
    id: Optional[int] = None

    @property
    def download_mbyte_s(self) -> float:
        """Convert download Mbps to MB/s."""
        return round(self.download_mbps / 8.0, 2)

    @property
    def upload_mbyte_s(self) -> float:
        """Convert upload Mbps to MB/s."""
        return round(self.upload_mbps / 8.0, 2)

    def estimate_download_time_str(self, gigabytes: float = 10.0) -> str:
        """Calculates estimated download time for a given size in GB."""
        mb_per_sec = self.download_mbyte_s
        if mb_per_sec <= 0.05:
            return "غير متاح (السرعة منخفضة جداً)"
        total_mb = gigabytes * 1024.0
        seconds = total_mb / mb_per_sec
        if seconds < 60:
            return f"{int(seconds)} ثانية تقريباً"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            sec = int(seconds % 60)
            return f"{minutes} دقيقة و {sec} ثانية"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours} ساعة و {mins} دقيقة"

    def get_service_rating(self) -> Dict[str, str]:
        """Provides objective rating badges for common activities."""
        dl = self.download_mbps
        ping = self.ping_ms
        loss = self.packet_loss_percent

        ratings = {}
        # Browsing
        if dl >= 15 and ping <= 100:
            ratings["التصفح والويب"] = "ممتاز"
        elif dl >= 5:
            ratings["التصفح والويب"] = "جيد"
        else:
            ratings["التصفح والويب"] = "بطيء"

        # 4K Streaming
        if dl >= 50 and loss <= 1:
            ratings["فيديو 4K"] = "ممتاز"
        elif dl >= 25:
            ratings["فيديو 4K"] = "جيد"
        elif dl >= 10:
            ratings["فيديو 4K"] = "مقبول (1080p)"
        else:
            ratings["فيديو 4K"] = "غير مناسب"

        # Gaming
        if ping <= 35 and loss == 0 and self.jitter_ms <= 5:
            ratings["الألعاب أونلاين"] = "ممتاز"
        elif ping <= 70 and loss <= 2:
            ratings["الألعاب أونلاين"] = "جيد جداً"
        elif ping <= 120:
            ratings["الألعاب أونلاين"] = "مقبول"
        else:
            ratings["الألعاب أونلاين"] = "مرتفع الـ Ping"

        # Voice / Video Calls
        if ping <= 60 and self.jitter_ms <= 10 and loss <= 1 and self.upload_mbps >= 3:
            ratings["مكالمات الفيديو"] = "ممتاز"
        elif ping <= 120 and self.upload_mbps >= 1.5:
            ratings["مكالمات الفيديو"] = "جيد"
        else:
            ratings["مكالمات الفيديو"] = "تقطيع محتمل"

        # File Uploading
        if self.upload_mbps >= 30:
            ratings["رفع الملفات"] = "سريع جداً"
        elif self.upload_mbps >= 10:
            ratings["رفع الملفات"] = "جيد"
        else:
            ratings["رفع الملفات"] = "عادي"

        return ratings


@dataclass
class DiagnosticCheckStage:
    """Individual stage check result for Network Doctor."""
    id: str                             # "adapter", "ip", "gateway", "dns", "https"
    title: str                          # Stage title in Arabic
    status: str                         # "passed", "warning", "failed", "pending", "running"
    summary: str                        # Human readable diagnostic finding
    suggested_fix: Optional[str] = None # Recommended repair step key if any
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class DoctorDiagnosticReport:
    """Comprehensive report output from Network Doctor."""
    stages: List[DiagnosticCheckStage]
    overall_health: str                 # "healthy", "warning", "critical", "offline"
    root_cause_ar: str                  # Pinpointed root cause explanation
    recommended_action_ar: str          # Safe actionable recommendation
    timestamp: datetime = field(default_factory=datetime.now)
    config_snapshot_saved: bool = False

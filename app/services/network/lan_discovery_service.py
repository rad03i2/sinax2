# -*- coding: utf-8 -*-
"""
SINAX LAN Device Discovery Service (خدمة اكتشاف الأجهزة المحلية)
Inspects the Windows Neighbor Cache, performs lightweight local subnet sweeps,
matches MAC OUI vendors, tracks First/Last Seen dates, and opens router dashboard.
"""

import socket
import subprocess
import threading
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.services.network.network_db import NetworkDatabase
from app.services.network.network_info_service import NetworkInfoService


@dataclass
class LanDevice:
    """Represents a device discovered on the local network."""
    ip_address: str
    mac_address: str
    vendor: str = "غير معروف"
    hostname: Optional[str] = None
    custom_name: Optional[str] = None
    state: str = "Active"
    is_gateway: bool = False
    first_seen: str = ""
    last_seen: str = ""


# Well-known MAC OUI prefixes
MAC_VENDORS = {
    "00:1A:11": "Google",
    "08:00:27": "VirtualBox",
    "00:0C:29": "VMware",
    "00:50:56": "VMware",
    "40:1A:58": "MediaTek",
    "68:FF:7B": "TP-Link",
    "50:D4:F7": "TP-Link",
    "F4:F2:6D": "TP-Link",
    "E4:5F:01": "Raspberry Pi",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "00:1E:67": "Intel",
    "3C:D9:2B": "HP",
    "48:BA:4E": "HP",
    "5C:B9:01": "HP",
    "B4:B6:86": "Dell",
    "00:14:22": "Dell",
    "AC:BC:32": "Apple",
    "BC:D1:1F": "Apple",
    "F0:18:98": "Apple",
    "38:F9:D3": "Apple",
    "F8:38:80": "Samsung",
    "34:82:C5": "Samsung",
    "C8:02:10": "Samsung",
    "54:E4:3A": "Xiaomi",
    "78:11:DC": "Xiaomi",
    "70:70:8B": "Huawei",
    "48:46:FB": "Huawei",
}


class LanDiscoveryService:
    """Discovers LAN devices safely and honestly without port scanning or ARP spoofing."""

    @classmethod
    def get_mac_vendor(cls, mac: str) -> str:
        """Looks up hardware vendor from MAC OUI prefix."""
        clean = mac.upper().replace("-", ":")
        prefix = clean[:8]
        return MAC_VENDORS.get(prefix, "جهاز محلي")

    @classmethod
    def get_neighbor_devices(cls) -> List[LanDevice]:
        """Queries Windows Neighbor Cache (`Get-NetNeighbor`) for known LAN devices."""
        devices: List[LanDevice] = []
        conn_info = NetworkInfoService.get_active_connection_summary()
        gateway = conn_info.get("gateway", "")
        my_ip = conn_info.get("ipv4", "")

        ps_cmd = (
            "Get-NetNeighbor -AddressFamily IPv4 | "
            "Where-Object { $_.State -notin @('Unreachable') -and $_.IPAddress -notmatch '^(224\\.|239\\.|255\\.)' } | "
            "Select-Object IPAddress, LinkLayerAddress, State | ConvertTo-Json -Depth 2"
        )
        data = NetworkInfoService.run_powershell_json(ps_cmd, timeout=5)
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        seen_ips = set()
        for row in data:
            if not isinstance(row, dict):
                continue
            ip = row.get("IPAddress")
            mac = row.get("LinkLayerAddress")
            if not ip or not mac or ip in seen_ips:
                continue
            seen_ips.add(ip)

            is_gw = (ip == gateway)
            vendor = cls.get_mac_vendor(mac)
            if is_gw:
                vendor = f"{vendor} (الراوتر الافتراضي)"

            devices.append(LanDevice(
                ip_address=ip,
                mac_address=mac,
                vendor=vendor,
                is_gateway=is_gw,
                state="متصل",
                first_seen=now_str,
                last_seen="الآن"
            ))

        # Add this PC if not present
        if my_ip and my_ip != "غير متوفر" and my_ip not in seen_ips:
            devices.insert(0, LanDevice(
                ip_address=my_ip,
                mac_address="هذا الجهاز (المحلي)",
                vendor="جهاز الكمبيوتر الحالي",
                is_gateway=False,
                state="نشط الآن",
                first_seen=now_str,
                last_seen="الآن"
            ))

        return devices

    @classmethod
    def scan_local_subnet(
        cls,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[LanDevice]:
        """
        Lightweight discovery: Sends quick socket probes to hosts on current /24 subnet.
        Strictly limited to user's private local subnet (e.g. 192.168.1.1 to 192.168.1.254).
        """
        conn_info = NetworkInfoService.get_active_connection_summary()
        my_ip = conn_info.get("ipv4", "")

        if not my_ip or my_ip == "غير متوفر" or my_ip.startswith("169.254."):
            return cls.get_neighbor_devices()

        parts = my_ip.split(".")
        if len(parts) != 4:
            return cls.get_neighbor_devices()

        subnet_base = f"{parts[0]}.{parts[1]}.{parts[2]}"

        # Scan 1..254 in parallel threads
        def ping_host(target_ip: str):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.18)
                s.connect((target_ip, 80)) # Try common web port
                s.close()
            except Exception:
                pass

        threads: List[threading.Thread] = []
        total = 64  # Fast sample of 64 surrounding IPs to be very respectful of network load
        curr_last = int(parts[3])
        start_host = max(1, curr_last - 32)
        end_host = min(254, curr_last + 32)

        count = 0
        for h in range(start_host, end_host + 1):
            if is_cancelled and is_cancelled():
                break
            ip = f"{subnet_base}.{h}"
            t = threading.Thread(target=ping_host, args=(ip,), daemon=True)
            threads.append(t)
            t.start()
            count += 1
            if progress_cb and count % 10 == 0:
                progress_cb(count / (end_host - start_host + 1), f"فحص النطاق المحلي {ip}...")
            time.sleep(0.015)

        for t in threads:
            t.join(timeout=0.3)

        # Now retrieve populated Neighbor Cache
        return cls.get_neighbor_devices()

    @classmethod
    def open_router_page(cls) -> bool:
        """Opens default gateway URL (e.g. http://192.168.1.1) in default browser."""
        conn_info = NetworkInfoService.get_active_connection_summary()
        gw = conn_info.get("gateway")
        if gw and gw != "غير متوفر":
            webbrowser.open(f"http://{gw}")
            return True
        return False

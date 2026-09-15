# -*- coding: utf-8 -*-
"""
SINAX Network Info Service (خدمة معلومات الشبكة والاتصال)
Retrieves active adapter information, IP configuration, gateway router, DNS servers,
Wi-Fi status, public IP with multi-provider fallback, and VPN/Proxy detection.
"""

import json
import socket
import ssl
import subprocess
import urllib.request
from typing import Any, Dict, List, Optional

from app.services.network.network_models import (
    NetworkAdapterInfo,
    PublicIPInfo,
    WifiConnectionInfo,
)


class NetworkInfoService:
    """Provides unified discovery of system networking status."""

    @classmethod
    def run_powershell_json(cls, command: str, timeout: int = 6) -> Any:
        """Runs a PowerShell command and returns parsed JSON if successful."""
        try:
            full_cmd = f"$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8; {command} | ConvertTo-Json -Depth 3 -Compress"
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout.strip())
        except Exception:
            pass
        return None

    @classmethod
    def get_active_connection_summary(cls) -> Dict[str, Any]:
        """
        Retrieves a fast, comprehensive overview of the active connection:
        - Connection type (Wi-Fi, Ethernet, Disconnected)
        - Local IPv4 & IPv6
        - Default Gateway router IP
        - DNS servers
        - Wi-Fi SSID, Signal %, Link Speed
        - Internet reachability status
        """
        summary = {
            "connected": False,
            "connection_type": "غير متصل",
            "interface_alias": "غير متوفر",
            "ipv4": "غير متوفر",
            "ipv6": "غير متوفر",
            "gateway": "غير متوفر",
            "dns_servers": [],
            "link_speed_mbps": 0,
            "wifi_ssid": None,
            "wifi_signal_percent": 0,
            "public_ip": None,
            "isp_name": None,
            "internet_status": "فحص الاتصال..."
        }

        # 1. Fetch IP Configuration via Get-NetIPConfiguration
        ps_ip_cmd = "Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null } | Select-Object InterfaceAlias, InterfaceDescription, IPv4Address, IPv6LinkLocalAddress, IPv4DefaultGateway, DNSServer"
        ip_data = cls.run_powershell_json(ps_ip_cmd)

        if isinstance(ip_data, list) and len(ip_data) > 0:
            ip_data = ip_data[0]

        if isinstance(ip_data, dict):
            summary["connected"] = True
            summary["interface_alias"] = ip_data.get("InterfaceAlias") or "Ethernet"

            # Parse IPv4
            ipv4_val = ip_data.get("IPv4Address")
            if isinstance(ipv4_val, dict):
                summary["ipv4"] = ipv4_val.get("IPAddress", "غير متوفر")
            elif isinstance(ipv4_val, list) and len(ipv4_val) > 0:
                summary["ipv4"] = ipv4_val[0].get("IPAddress", "غير متوفر") if isinstance(ipv4_val[0], dict) else str(ipv4_val[0])
            elif isinstance(ipv4_val, str):
                summary["ipv4"] = ipv4_val

            # Parse Gateway
            gw_val = ip_data.get("IPv4DefaultGateway")
            if isinstance(gw_val, dict):
                summary["gateway"] = gw_val.get("NextHop", "غير متوفر")
            elif isinstance(gw_val, list) and len(gw_val) > 0:
                summary["gateway"] = gw_val[0].get("NextHop", "غير متوفر") if isinstance(gw_val[0], dict) else str(gw_val[0])
            elif isinstance(gw_val, str):
                summary["gateway"] = gw_val

            # Parse DNS
            dns_val = ip_data.get("DNSServer")
            dns_list = []
            if isinstance(dns_val, list):
                for d in dns_val:
                    if isinstance(d, dict) and d.get("ServerAddresses"):
                        dns_list.extend(d["ServerAddresses"])
            elif isinstance(dns_val, dict) and dns_val.get("ServerAddresses"):
                dns_list.extend(dns_val["ServerAddresses"])
            summary["dns_servers"] = dns_list if dns_list else ["تلقائي"]

            # Connection Type
            alias_lower = summary["interface_alias"].lower()
            if "wi-fi" in alias_lower or "wlan" in alias_lower or "wireless" in alias_lower:
                summary["connection_type"] = "Wi-Fi"
            elif "cellular" in alias_lower or "mobile" in alias_lower:
                summary["connection_type"] = "بيانات خلوية"
            else:
                summary["connection_type"] = "إيثرنت (Ethernet)"

        # 2. Check Wi-Fi details if connection is Wi-Fi or available
        wifi_info = cls.get_wifi_status()
        if wifi_info and wifi_info.ssid:
            summary["wifi_ssid"] = wifi_info.ssid
            summary["wifi_signal_percent"] = wifi_info.signal_quality_percent
            summary["link_speed_mbps"] = int(wifi_info.receive_rate_mbps or wifi_info.transmit_rate_mbps or 0)
            if summary["connection_type"] == "غير متصل":
                summary["connection_type"] = "Wi-Fi"
                summary["connected"] = True

        # 3. Quick Internet Verification
        is_online = cls.check_internet_quick()
        summary["internet_status"] = "متصل بالإنترنت ✓" if is_online else "لا يوجد اتصال بالإنترنت ✗"

        return summary

    @classmethod
    def get_wifi_status(cls) -> Optional[WifiConnectionInfo]:
        """Parses `netsh wlan show interfaces` for native Wi-Fi connection info."""
        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=4,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode != 0 or not res.stdout:
                return None

            lines = res.stdout.splitlines()
            info = WifiConnectionInfo()
            has_interface = False

            for line in lines:
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()

                if k == "Name":
                    info.interface_name = v
                    has_interface = True
                elif k == "State":
                    info.state = v
                elif k == "SSID":
                    info.ssid = v
                elif k == "BSSID" or k == "AP BSSID":
                    info.bssid = v
                elif k == "Signal":
                    try:
                        info.signal_quality_percent = int(v.replace("%", "").strip())
                    except ValueError:
                        pass
                elif k == "Radio type":
                    info.protocol = v
                elif k == "Band":
                    info.band_ghz = v
                elif k == "Channel":
                    try:
                        info.channel = int(v)
                    except ValueError:
                        pass
                elif k == "Authentication":
                    info.authentication = v
                elif k == "Cipher":
                    info.cipher = v
                elif k == "Receive rate (Mbps)":
                    try:
                        info.receive_rate_mbps = float(v)
                    except ValueError:
                        pass
                elif k == "Transmit rate (Mbps)":
                    try:
                        info.transmit_rate_mbps = float(v)
                    except ValueError:
                        pass

            return info if (has_interface and info.state == "connected") else None
        except Exception:
            return None

    @classmethod
    def check_internet_quick(cls, timeout: float = 1.8) -> bool:
        """Quickly checks whether the internet is reachable via fast TCP connect."""
        test_targets = [
            ("1.1.1.1", 53),
            ("8.8.8.8", 53),
            ("1.0.0.1", 443),
        ]
        for host, port in test_targets:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((host, port))
                s.close()
                return True
            except Exception:
                continue
        return False

    @classmethod
    def fetch_public_ip(cls) -> PublicIPInfo:
        """
        Fetches Public IP and ISP details with multi-provider fallback:
        Provider 1: api.ipify.org
        Provider 2: ipinfo.io
        Provider 3: icanhazip.com
        """
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Attempt ipinfo.io first (provides IP + ISP + Region in one shot)
        try:
            req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "SINAX/1.0"})
            with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
                return PublicIPInfo(
                    ipv4=data.get("ip"),
                    isp_name=data.get("org"),
                    region=data.get("region"),
                    country=data.get("country"),
                    status="OK"
                )
        except Exception:
            pass

        # Fallback to ipify.org
        try:
            req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "SINAX/1.0"})
            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
                return PublicIPInfo(
                    ipv4=data.get("ip"),
                    status="OK"
                )
        except Exception:
            pass

        # Fallback to icanhazip.com
        try:
            req = urllib.request.Request("https://icanhazip.com", headers={"User-Agent": "SINAX/1.0"})
            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as r:
                ip_text = r.read().decode("utf-8", errors="replace").strip()
                if ip_text:
                    return PublicIPInfo(ipv4=ip_text, status="OK")
        except Exception:
            pass

        return PublicIPInfo(status="Offline")

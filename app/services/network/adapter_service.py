# -*- coding: utf-8 -*-
"""
SINAX Adapter & Routing Service (خدمة محولات الشبكة وجداول التوجيه)
Queries network adapters, interface throughput statistics, routing table routes,
firewall profile status, and system proxy settings.
"""

import subprocess
from typing import Any, Dict, List, Optional

from app.services.network.network_info_service import NetworkInfoService
from app.services.network.network_models import (
    AdapterStatistics,
    NetworkAdapterInfo,
)


class AdapterService:
    """Provides adapter hardware metrics, routing inspection, and firewall checks."""

    @classmethod
    def get_all_adapters(cls) -> List[NetworkAdapterInfo]:
        """Returns all detected physical and virtual network adapters."""
        adapters: List[NetworkAdapterInfo] = []
        ps_cmd = "Get-NetAdapter | Select-Object Name, InterfaceDescription, MacAddress, Status, LinkSpeed, MtuSize, Virtual | ConvertTo-Json -Depth 2"
        data = NetworkInfoService.run_powershell_json(ps_cmd)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []

        # Also get IP configs to merge addresses
        ip_map = cls._get_adapter_ip_map()

        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("Name", "Unknown")
            desc = item.get("InterfaceDescription", "")
            mac = item.get("MacAddress", "00-00-00-00-00-00")
            status = item.get("Status", "Disconnected")
            link_str = str(item.get("LinkSpeed", "0 bps"))
            mtu = int(item.get("MtuSize", 1500))
            is_virt = bool(item.get("Virtual", False))

            # Parse LinkSpeed into Mbps
            link_mbps = 0
            try:
                if "Gbps" in link_str:
                    link_mbps = int(float(link_str.replace("Gbps", "").strip()) * 1000)
                elif "Mbps" in link_str:
                    link_mbps = int(float(link_str.replace("Mbps", "").strip()))
                elif "Kbps" in link_str:
                    link_mbps = max(1, int(float(link_str.replace("Kbps", "").strip()) / 1000))
            except Exception:
                pass

            name_lower = name.lower()
            desc_lower = desc.lower()
            is_wireless = "wi-fi" in name_lower or "wlan" in name_lower or "wireless" in desc_lower
            is_vpn = "vpn" in name_lower or "tap" in name_lower or "wireguard" in name_lower or "tunnel" in desc_lower

            ip_info = ip_map.get(name, {})

            adapters.append(NetworkAdapterInfo(
                name=name,
                description=desc,
                mac_address=mac,
                ipv4_address=ip_info.get("ipv4"),
                ipv4_subnet=ip_info.get("subnet"),
                ipv4_gateway=ip_info.get("gateway"),
                ipv6_address=ip_info.get("ipv6"),
                dns_servers=ip_info.get("dns", []),
                link_speed_mbps=link_mbps,
                mtu=mtu,
                status="متصل" if status == "Up" else ("معطل" if status == "Disabled" else "غير متصل"),
                is_wireless=is_wireless,
                is_virtual=is_virt,
                is_vpn=is_vpn
            ))

        return adapters

    @classmethod
    def _get_adapter_ip_map(cls) -> Dict[str, Dict[str, Any]]:
        """Maps adapter names to their IP addresses, gateways, and DNS."""
        result_map: Dict[str, Dict[str, Any]] = {}
        ps_cmd = "Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4Address, IPv6LinkLocalAddress, IPv4DefaultGateway, DNSServer"
        data = NetworkInfoService.run_powershell_json(ps_cmd)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            return result_map

        for row in data:
            if not isinstance(row, dict):
                continue
            alias = row.get("InterfaceAlias")
            if not alias:
                continue

            entry: Dict[str, Any] = {"ipv4": None, "gateway": None, "ipv6": None, "dns": []}

            # IPv4
            ipv4_val = row.get("IPv4Address")
            if isinstance(ipv4_val, dict):
                entry["ipv4"] = ipv4_val.get("IPAddress")
            elif isinstance(ipv4_val, list) and len(ipv4_val) > 0:
                entry["ipv4"] = ipv4_val[0].get("IPAddress") if isinstance(ipv4_val[0], dict) else str(ipv4_val[0])
            elif isinstance(ipv4_val, str):
                entry["ipv4"] = ipv4_val

            # Gateway
            gw_val = row.get("IPv4DefaultGateway")
            if isinstance(gw_val, dict):
                entry["gateway"] = gw_val.get("NextHop")
            elif isinstance(gw_val, list) and len(gw_val) > 0:
                entry["gateway"] = gw_val[0].get("NextHop") if isinstance(gw_val[0], dict) else str(gw_val[0])
            elif isinstance(gw_val, str):
                entry["gateway"] = gw_val

            # IPv6
            ipv6_val = row.get("IPv6LinkLocalAddress")
            if isinstance(ipv6_val, dict):
                entry["ipv6"] = ipv6_val.get("IPAddress")
            elif isinstance(ipv6_val, str):
                entry["ipv6"] = ipv6_val

            # DNS
            dns_val = row.get("DNSServer")
            if isinstance(dns_val, list):
                for d in dns_val:
                    if isinstance(d, dict) and d.get("ServerAddresses"):
                        entry["dns"].extend(d["ServerAddresses"])
            elif isinstance(dns_val, dict) and dns_val.get("ServerAddresses"):
                entry["dns"].extend(dns_val["ServerAddresses"])

            result_map[alias] = entry

        return result_map

    @classmethod
    def get_adapter_statistics(cls) -> List[AdapterStatistics]:
        """Returns live packet and byte statistics for all adapters."""
        stats: List[AdapterStatistics] = []
        ps_cmd = "Get-NetAdapterStatistics | Select-Object Name, ReceivedBytes, SentBytes, ReceivedDiscardedPackets, OutboundDiscardedPackets, ReceivedPacketErrors, OutboundPacketErrors"
        data = NetworkInfoService.run_powershell_json(ps_cmd)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []

        for row in data:
            if not isinstance(row, dict):
                continue
            stats.append(AdapterStatistics(
                name=row.get("Name", "Unknown"),
                bytes_received=int(row.get("ReceivedBytes", 0)),
                bytes_sent=int(row.get("SentBytes", 0)),
                discards_in=int(row.get("ReceivedDiscardedPackets", 0)),
                discards_out=int(row.get("OutboundDiscardedPackets", 0)),
                errors_in=int(row.get("ReceivedPacketErrors", 0)),
                errors_out=int(row.get("OutboundPacketErrors", 0)),
            ))
        return stats

    @classmethod
    def get_routing_table(cls) -> List[Dict[str, Any]]:
        """Returns the IPv4 routing table and marks default routes."""
        routes: List[Dict[str, Any]] = []
        ps_cmd = "Get-NetRoute -AddressFamily IPv4 | Select-Object DestinationPrefix, NextHop, InterfaceAlias, RouteMetric | Sort-Object RouteMetric | Select-Object -First 30"
        data = NetworkInfoService.run_powershell_json(ps_cmd)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []

        for row in data:
            if not isinstance(row, dict):
                continue
            dest = row.get("DestinationPrefix", "")
            routes.append({
                "destination": dest,
                "next_hop": row.get("NextHop", ""),
                "interface": row.get("InterfaceAlias", ""),
                "metric": row.get("RouteMetric", 0),
                "is_default": (dest == "0.0.0.0/0")
            })
        return routes

    @classmethod
    def get_firewall_status(cls) -> Dict[str, bool]:
        """Returns status of Windows Firewall profiles (Domain, Private, Public)."""
        profiles = {"Domain": False, "Private": False, "Public": False}
        ps_cmd = "Get-NetFirewallProfile | Select-Object Name, Enabled"
        data = NetworkInfoService.run_powershell_json(ps_cmd)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            return profiles

        for row in data:
            if isinstance(row, dict):
                name = row.get("Name")
                enabled = row.get("Enabled") in (1, True, "True")
                if name in profiles:
                    profiles[name] = enabled

        return profiles

    @classmethod
    def get_proxy_info(cls) -> Dict[str, Any]:
        """Queries Windows Internet Settings registry to detect proxy."""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            )
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            try:
                proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            except Exception:
                proxy_server = ""
            winreg.CloseKey(key)

            return {
                "enabled": bool(proxy_enable),
                "server": proxy_server if proxy_enable else "لا يوجد وكيل نشط (Direct Connection)",
                "type": "Manual Proxy" if proxy_enable else "Direct"
            }
        except Exception:
            return {"enabled": False, "server": "مباشر (لا يوجد وكيل)", "type": "Direct"}

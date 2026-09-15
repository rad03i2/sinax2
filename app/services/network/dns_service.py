# -*- coding: utf-8 -*-
"""
SINAX DNS Center Service (خدمة مركز DNS الشامل والمقارن)
Provides multi-record DNS lookups (A, AAAA, MX, TXT, NS, PTR), DNS server benchmarking,
safe DNS switching with presets, and configuration backups.
"""

import socket
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.network.network_db import NetworkDatabase
from app.services.network.network_info_service import NetworkInfoService

# Popular DNS benchmark targets
POPULAR_DNS_SERVERS = [
    {"name": "Cloudflare", "primary": "1.1.1.1", "secondary": "1.0.0.1", "desc": "أسرع خادم عام ومحمي للخصوصية"},
    {"name": "Google DNS", "primary": "8.8.8.8", "secondary": "8.8.4.4", "desc": "خوادم جوجل العالمية الموثوقة"},
    {"name": "Quad9", "primary": "9.9.9.9", "secondary": "149.112.112.112", "desc": "حماية متقدمة من المواقع الضارة والتهديدات"},
    {"name": "OpenDNS", "primary": "208.67.222.222", "secondary": "208.67.220.220", "desc": "خوادم سيسكو مع تصفية أمان اختيارية"},
]


class DnsService:
    """Manages DNS lookups, benchmarks, and DNS settings."""

    @classmethod
    def lookup_records(cls, domain: str, record_type: str = "A") -> List[Dict[str, Any]]:
        """Queries DNS records for a given domain using Resolve-DnsName."""
        records: List[Dict[str, Any]] = []
        ps_cmd = f"Resolve-DnsName -Name '{domain}' -Type {record_type} -QuickTimeout | Select-Object Name, Type, IPAddress, NameHost, Strings, TTL | ConvertTo-Json"
        data = NetworkInfoService.run_powershell_json(ps_cmd, timeout=5)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []

        for row in data:
            if not isinstance(row, dict):
                continue
            ip = row.get("IPAddress") or row.get("NameHost") or str(row.get("Strings", ""))
            records.append({
                "name": row.get("Name", domain),
                "type": record_type,
                "value": ip,
                "ttl": row.get("TTL", 300)
            })

        # Fallback to standard socket if PS empty for type A
        if not records and record_type in ("A", "ALL"):
            try:
                ip = socket.gethostbyname(domain)
                records.append({"name": domain, "type": "A", "value": ip, "ttl": 300})
            except Exception:
                pass

        return records

    @classmethod
    def benchmark_dns_servers(cls, domain: str = "google.com") -> List[Dict[str, Any]]:
        """Benchmarks resolution response times across popular public DNS servers and current DNS."""
        results: List[Dict[str, Any]] = []

        # Current DNS
        conn_info = NetworkInfoService.get_active_connection_summary()
        current_servers = conn_info.get("dns_servers", [])
        current_ip = current_servers[0] if current_servers else "1.1.1.1"

        servers_to_test = [{"name": "الخادم الحالي (Current)", "ip": current_ip}]
        for s in POPULAR_DNS_SERVERS:
            servers_to_test.append({"name": s["name"], "ip": s["primary"]})

        for s in servers_to_test:
            ip = s["ip"]
            # Test 2 queries and take average
            rtts = []
            success = False
            resolved_ip = ""

            for _ in range(2):
                t0 = time.perf_counter()
                try:
                    # Test socket connect to DNS port 53 first
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.5)
                    sock.connect((ip, 53))
                    sock.close()
                    dt = (time.perf_counter() - t0) * 1000.0
                    rtts.append(dt)
                    success = True
                except Exception:
                    pass
                time.sleep(0.04)

            avg_ms = round(sum(rtts) / len(rtts), 1) if rtts else 0.0

            results.append({
                "name": s["name"],
                "ip": ip,
                "latency_ms": avg_ms if success else 999.0,
                "status": "ناجح ✓" if success else "فشل ✗",
                "is_fastest": False
            })

        # Sort by latency
        results.sort(key=lambda x: x["latency_ms"])
        if results and results[0]["latency_ms"] < 999.0:
            results[0]["is_fastest"] = True

        return results

    @classmethod
    def set_dns_server(cls, adapter_name: str, primary: Optional[str] = None, secondary: Optional[str] = None) -> Tuple[bool, str]:
        """
        Sets DNS servers for an adapter.
        If primary is None, reverts to automatic DHCP.
        """
        # Backup current configuration first
        conn_info = NetworkInfoService.get_active_connection_summary()
        NetworkDatabase.save_snapshot("pre_dns_change_snapshot", conn_info)

        if not primary:
            # Revert to DHCP
            ps_cmd = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return True, f"تمت استعادة إعدادات DNS التلقائية (DHCP) للمحول {adapter_name} بنجاح."
            return False, "قد تتطلب عملية تغيير DNS تشغيل البرنامج كمسؤول (Administrator)."

        addrs = [f"'{primary}'"]
        if secondary:
            addrs.append(f"'{secondary}'")
        addrs_str = ", ".join(addrs)

        ps_cmd = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ServerAddresses ({addrs_str})"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            return True, f"تم تعيين ملقمات DNS بنجاح للمحول {adapter_name}."
        return False, "تعذر تطبيق الإعدادات. يرجى التأكد من تشغيل البرنامج بصلاحية المسؤول."

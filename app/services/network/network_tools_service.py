# -*- coding: utf-8 -*-
"""
SINAX Network Tools & Support Exporter Service (خدمة أدوات الشبكة المتقدمة والتقارير الفنية)
Provides:
1. Continuous Ping with rolling latency timeline
2. Traceroute hop tracer
3. Diagnostic common port inspection on user-owned hosts
4. Comprehensive Network Support Report exporter (TXT, JSON, HTML, CSV) with Privacy Mode
"""

import json
import re
import socket
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.network.network_info_service import NetworkInfoService

COMMON_DIAGNOSTIC_PORTS = [
    (22, "SSH - إدارة آمنة"),
    (53, "DNS - نظام النطاقات"),
    (80, "HTTP - خادم ويب عادي"),
    (443, "HTTPS - خادم ويب مشفر"),
    (445, "SMB - مشاركة ملفات ويندوز"),
    (3389, "RDP - سطح المكتب البعيد"),
]


class NetworkToolsService:
    """Provides ping diagnostics, traceroute, port checks, and exportable reports."""

    @classmethod
    def ping_single(cls, host: str, timeout: float = 1.5) -> Tuple[bool, float]:
        """Pings a host once and returns (success, latency_ms)."""
        t0 = time.perf_counter()
        try:
            # Quick socket test on common port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, 80 if not host.startswith("1.1.") else 53))
            s.close()
            dt = (time.perf_counter() - t0) * 1000.0
            return True, round(dt, 1)
        except Exception:
            pass

        # Fallback to ICMP ping
        try:
            res = subprocess.run(
                ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host],
                capture_output=True,
                text=True,
                timeout=timeout + 0.8
            )
            if res.returncode == 0:
                dt = (time.perf_counter() - t0) * 1000.0
                return True, round(dt, 1)
        except Exception:
            pass
        return False, 0.0

    @classmethod
    def traceroute_host(
        cls,
        host: str,
        max_hops: int = 15,
        hop_cb: Optional[Callable[[int, str, float], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[Dict[str, Any]]:
        """Executes a visual traceroute hop timeline up to max_hops."""
        hops: List[Dict[str, Any]] = []
        try:
            proc = subprocess.Popen(
                ["tracert", "-d", "-h", str(max_hops), "-w", "800", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            hop_regex = re.compile(r"^\s*(\d+)\s+(.+?)\s+(\d+\.\d+\.\d+\.\d+|[a-fA-F0-9:]+)")

            for line in proc.stdout:
                if is_cancelled and is_cancelled():
                    proc.kill()
                    break

                match = hop_regex.search(line)
                if match:
                    hop_num = int(match.group(1))
                    times_part = match.group(2)
                    ip_addr = match.group(3)

                    # Extract first ms time
                    ms_val = 0.0
                    ms_match = re.search(r"(\d+)\s*ms", times_part)
                    if ms_match:
                        ms_val = float(ms_match.group(1))

                    hop_data = {"hop": hop_num, "ip": ip_addr, "latency_ms": ms_val}
                    hops.append(hop_data)
                    if hop_cb:
                        hop_cb(hop_num, ip_addr, ms_val)

            proc.wait(timeout=2.0)
        except Exception:
            pass

        return hops

    @classmethod
    def scan_diagnostic_ports(cls, host: str, timeout: float = 1.0) -> List[Dict[str, Any]]:
        """
        Diagnostic check on standard common ports for user-owned LAN device.
        Strictly no stealth scanning.
        """
        results = []
        for port, service_name in COMMON_DIAGNOSTIC_PORTS:
            t0 = time.perf_counter()
            is_open = False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((host, port))
                s.close()
                is_open = True
                dt = (time.perf_counter() - t0) * 1000.0
            except Exception:
                dt = 0.0

            results.append({
                "port": port,
                "service": service_name,
                "status": "مفتوح (Open) ✓" if is_open else "مغلق (Closed) ✗",
                "latency_ms": round(dt, 1) if is_open else 0.0
            })
        return results

    @classmethod
    def generate_support_report(cls, privacy_mode: bool = False) -> Dict[str, Any]:
        """Gathers a comprehensive diagnostic support report for technical support."""
        conn_info = NetworkInfoService.get_active_connection_summary()
        pub_info = NetworkInfoService.fetch_public_ip()

        ipv4 = conn_info.get("ipv4", "غير متوفر")
        gateway = conn_info.get("gateway", "غير متوفر")
        public_ip = pub_info.ipv4 or "غير متوفر"

        if privacy_mode:
            # Mask sensitive IPs
            def mask_ip(ip_str: str) -> str:
                if "." in ip_str:
                    parts = ip_str.split(".")
                    return f"{parts[0]}.{parts[1]}.***.***"
                return "***.***.***"

            ipv4 = mask_ip(ipv4)
            gateway = mask_ip(gateway)
            public_ip = mask_ip(public_ip)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system": "Microsoft Windows",
            "privacy_mode": privacy_mode,
            "connection_type": conn_info.get("connection_type"),
            "interface": conn_info.get("interface_alias"),
            "ipv4_local": ipv4,
            "gateway_router": gateway,
            "dns_servers": conn_info.get("dns_servers", []),
            "wifi_ssid": conn_info.get("wifi_ssid") or "N/A",
            "wifi_signal": f"{conn_info.get('wifi_signal_percent', 0)}%",
            "link_speed": f"{conn_info.get('link_speed_mbps', 0)} Mbps",
            "public_ip": public_ip,
            "isp_name": pub_info.isp_name or "N/A",
            "internet_status": conn_info.get("internet_status")
        }
        return report

    @classmethod
    def export_report_to_text(cls, report: Dict[str, Any]) -> str:
        """Formats the support report into clean readable Arabic text."""
        lines = [
            "============================================================",
            "             تقرير الدعم الفني للشبكة - SINAX               ",
            "============================================================",
            f"وقت التقرير: {report.get('timestamp')}",
            f"وضع حماية الخصوصية: {'مفعّل (تم إخفاء العناوين الحساسة)' if report.get('privacy_mode') else 'معطل'}",
            "------------------------------------------------------------",
            f"نوع الاتصال: {report.get('connection_type')}",
            f"محول الشبكة: {report.get('interface')}",
            f"عنوان IP المحلي: {report.get('ipv4_local')}",
            f"بوابة الراوتر (Gateway): {report.get('gateway_router')}",
            f"خوادم DNS: {', '.join(report.get('dns_servers', []))}",
            f"شبكة Wi-Fi: {report.get('wifi_ssid')}",
            f"قوة إشارة اللاسلكي: {report.get('wifi_signal')}",
            f"سرعة الربط مع الراوتر: {report.get('link_speed')}",
            "------------------------------------------------------------",
            f"عنوان IP العام (Public IP): {report.get('public_ip')}",
            f"مزود الخدمة (ISP): {report.get('isp_name')}",
            f"حالة الوصول للإنترنت: {report.get('internet_status')}",
            "============================================================",
            "لا يتضمن هذا التقرير كلمات المرور ولا محتوى حزم البيانات إطلاقاً."
        ]
        return "\n".join(lines)

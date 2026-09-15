# -*- coding: utf-8 -*-
"""
SINAX Network Doctor Service (طبيب تشخيص وإصلاح الشبكة الآمن)
Executes a 5-stage diagnostic pipeline (Adapter -> IP/APIPA -> Gateway -> DNS -> HTTPS)
and provides safe sequential 1-click repair routines with rollback/backup support.
"""

import socket
import ssl
import subprocess
import time
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

from app.services.network.network_db import NetworkDatabase
from app.services.network.network_info_service import NetworkInfoService
from app.services.network.network_models import (
    DiagnosticCheckStage,
    DoctorDiagnosticReport,
)


class NetworkDoctorService:
    """Diagnoses network issues and guides safe automated repair steps."""

    @classmethod
    def run_full_diagnosis(
        cls,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> DoctorDiagnosticReport:
        """
        Executes the 5-stage sequential diagnosis:
        Stage 1: Network Adapter Check
        Stage 2: IP Configuration & APIPA Detection
        Stage 3: Default Gateway / Router Ping
        Stage 4: DNS Lookup & Resolution
        Stage 5: HTTPS Internet Reachability
        """
        stages: List[DiagnosticCheckStage] = []
        overall_health = "healthy"
        root_cause = "لا توجد مشاكل تم رصدها، الاتصال مستقر وسليم ✓"
        recommended_action = "الشبكة تعمل بكفاءة، لا يتطلب أي إجراء."

        conn_info = NetworkInfoService.get_active_connection_summary()

        # Save config snapshot before testing
        try:
            NetworkDatabase.save_snapshot("pre_diagnostic_snapshot", conn_info)
            snapshot_saved = True
        except Exception:
            snapshot_saved = False

        # --- Stage 1: Network Adapter ---
        if progress_cb:
            progress_cb(1, 5, "فحص محول الشبكة (Network Adapter)...")
        time.sleep(0.15)

        adapter_name = conn_info.get("interface_alias", "غير متوفر")
        is_connected = conn_info.get("connected", False)

        if not is_connected or adapter_name == "غير متوفر":
            s1 = DiagnosticCheckStage(
                id="adapter",
                title="محول الشبكة (Network Adapter)",
                status="failed",
                summary="لم يتم العثور على محول شبكة مفعّل ومتصل في جهازك.",
                suggested_fix="restart_adapter",
                details={"المحول": adapter_name, "الحالة": "معطل أو غير متصل"}
            )
            stages.append(s1)
            return DoctorDiagnosticReport(
                stages=stages,
                overall_health="critical",
                root_cause_ar="محول الشبكة (Wi-Fi أو Ethernet) معطل أو مفصول عن العمل.",
                recommended_action_ar="تأكد من تشغيل زر Wi-Fi أو توصيل كابل الإيثرنت، أو جرّب إعادة تشغيل كرت الشبكة.",
                config_snapshot_saved=snapshot_saved
            )
        else:
            s1 = DiagnosticCheckStage(
                id="adapter",
                title="محول الشبكة (Network Adapter)",
                status="passed",
                summary=f"محول الشبكة ({adapter_name}) مفعّل ويعمل بنجاح.",
                details={"اسم المحول": adapter_name, "النوع": conn_info.get("connection_type", "")}
            )
            stages.append(s1)

        # --- Stage 2: IP Configuration & APIPA Detection ---
        if progress_cb:
            progress_cb(2, 5, "فحص عنوان IP وتكوين DHCP...")
        time.sleep(0.15)

        ipv4 = conn_info.get("ipv4", "")
        if not ipv4 or ipv4 == "غير متوفر":
            s2 = DiagnosticCheckStage(
                id="ip",
                title="تكوين عنوان IP",
                status="failed",
                summary="الجهاز لم يحصل على عنوان IP من خادم DHCP.",
                suggested_fix="renew_dhcp",
                details={"IPv4": "غير متوفر"}
            )
            stages.append(s2)
            return DoctorDiagnosticReport(
                stages=stages,
                overall_health="critical",
                root_cause_ar="الجهاز غير قادر على استلام عنوان IP صالح من الراوتر.",
                recommended_action_ar="قم بتجديد عنوان IP عبر تجديد استئجار DHCP (Renew DHCP).",
                config_snapshot_saved=snapshot_saved
            )
        elif ipv4.startswith("169.254."):
            # APIPA detected
            s2 = DiagnosticCheckStage(
                id="ip",
                title="تكوين عنوان IP (APIPA)",
                status="failed",
                summary=f"عنوان IP تلقائي مؤقت ({ipv4}): خادم DHCP في الراوتر لم يقم بتعيين عنوان.",
                suggested_fix="renew_dhcp",
                details={"IPv4": ipv4, "المشكلة": "APIPA (Automatic Private IP Addressing)"}
            )
            stages.append(s2)
            return DoctorDiagnosticReport(
                stages=stages,
                overall_health="critical",
                root_cause_ar="تعذر على الراوتر تعيين عنوان IP لجهازك، مما جعل ويندوز يستخدم عنوان APIPA تلقائي.",
                recommended_action_ar="اضغط على زر تجديد استئجار IP (Renew DHCP)، أو أعد تشغيل الراوتر المنزلي.",
                config_snapshot_saved=snapshot_saved
            )
        else:
            s2 = DiagnosticCheckStage(
                id="ip",
                title="تكوين عنوان IP",
                status="passed",
                summary=f"تم تخصيص عنوان IP صالح بنجاح: {ipv4}",
                details={"IPv4": ipv4, "النوع": "صالح"}
            )
            stages.append(s2)

        # --- Stage 3: Gateway / Router Reachability ---
        if progress_cb:
            progress_cb(3, 5, "فحص الاتصال بالراوتر (Default Gateway)...")
        time.sleep(0.15)

        gateway = conn_info.get("gateway", "")
        gateway_ok = False
        gateway_rtt_ms = 0.0

        if gateway and gateway != "غير متوفر":
            gateway_ok, gateway_rtt_ms = cls.test_ping_host(gateway, timeout=1.5)

        if not gateway_ok:
            s3 = DiagnosticCheckStage(
                id="gateway",
                title="بوابة الاتصال (Router Gateway)",
                status="failed",
                summary=f"الراوتر الافتراضي ({gateway or 'غير معروف'}) لا يستجيب لطلبات الاتصال.",
                suggested_fix="renew_dhcp",
                details={"البوابة": gateway or "غير محددة", "الاستجابة": "فشل الاتصال"}
            )
            stages.append(s3)
            return DoctorDiagnosticReport(
                stages=stages,
                overall_health="critical",
                root_cause_ar="المشكلة محلية تماماً بين جهاز الكمبيوتر والراوتر (البوابة لا تستجيب).",
                recommended_action_ar="تأكد من الاقتراب من الراوتر أو فحص كابل التوصيل وإعادة تشغيل الراوتر.",
                config_snapshot_saved=snapshot_saved
            )
        else:
            s3 = DiagnosticCheckStage(
                id="gateway",
                title="بوابة الاتصال (Router Gateway)",
                status="passed",
                summary=f"الراوتر يستجيب بسرعة ممتازة ({gateway_rtt_ms:.1f} ms) على العنوان {gateway}.",
                details={"البوابة": gateway, "زمن الاستجابة": f"{gateway_rtt_ms:.1f} ms"}
            )
            stages.append(s3)

        # --- Stage 4: DNS Lookup & Resolution ---
        if progress_cb:
            progress_cb(4, 5, "فحص استجابة ودقة خوادم DNS...")
        time.sleep(0.15)

        dns_ok, dns_resolved_ip = cls.test_dns_lookup("google.com", timeout=2.5)

        if not dns_ok:
            s4 = DiagnosticCheckStage(
                id="dns",
                title="نظام أسماء النطاقات (DNS Lookup)",
                status="failed",
                summary="فشل تحليل أسماء النطاقات عبر خادم DNS الحالي.",
                suggested_fix="flush_dns",
                details={"النطاق المختبر": "google.com", "النتيجة": "تعذر التحليل"}
            )
            stages.append(s4)
            return DoctorDiagnosticReport(
                stages=stages,
                overall_health="warning",
                root_cause_ar="الشبكة المحلية والراوتر يعملان، لكن خادم DNS لا يستجيب أو بيانات الكاش معطوبة.",
                recommended_action_ar="اضغط على زر (مسح DNS Cache)، أو جرّب التبديل إلى خوادم DNS سريعة وموثوقة مثل Cloudflare أو Google.",
                config_snapshot_saved=snapshot_saved
            )
        else:
            s4 = DiagnosticCheckStage(
                id="dns",
                title="نظام أسماء النطاقات (DNS Lookup)",
                status="passed",
                summary=f"خادم DNS يعمل بدقة عالية (تم حل google.com إلى {dns_resolved_ip}).",
                details={"العنوان المسترجع": dns_resolved_ip, "الخوادم": ", ".join(conn_info.get("dns_servers", []))}
            )
            stages.append(s4)

        # --- Stage 5: HTTPS Internet Reachability ---
        if progress_cb:
            progress_cb(5, 5, "فحص تبادل بيانات الويب الآمن (HTTPS)...")
        time.sleep(0.15)

        https_ok = cls.test_https_connect("https://1.1.1.1", timeout=3.0)

        if not https_ok:
            s5 = DiagnosticCheckStage(
                id="https",
                title="اتصال الويب الآمن (HTTPS)",
                status="warning",
                summary="تعذر إتمام اتصال HTTPS مباشر مع شبكة الإنترنت.",
                suggested_fix="winsock_reset",
                details={"البروتوكول": "HTTPS (Port 443)", "الحالة": "محظور أو بطيء جداً"}
            )
            stages.append(s5)
            overall_health = "warning"
            root_cause = "يوجد اتصال بالشبكة، ولكن حزم HTTPS تواجه عائقاً أو وسيطاً (Proxy / Firewall)."
            recommended_action = "تحقق من إعدادات البروكسي (Proxy) أو جدار الحماية، أو نفذ مسح Winsock Catalog."
        else:
            s5 = DiagnosticCheckStage(
                id="https",
                title="اتصال الويب الآمن (HTTPS)",
                status="passed",
                summary="اتصال الإنترنت الخارجي وحزم HTTPS تعمل بكامل سرعتها واستقرارها ✓",
                details={"بروتوكول": "TLS / HTTPS", "الحالة": "متصل بنجاح"}
            )
            stages.append(s5)

        return DoctorDiagnosticReport(
            stages=stages,
            overall_health=overall_health,
            root_cause_ar=root_cause,
            recommended_action_ar=recommended_action,
            config_snapshot_saved=snapshot_saved
        )

    @classmethod
    def test_ping_host(cls, host: str, timeout: float = 1.5) -> Tuple[bool, float]:
        """Tests connectivity to a host or IP via socket connect."""
        t0 = time.perf_counter()
        try:
            # Try port 80 or 53 or 443 or 135
            for port in [80, 53, 443, 135]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    s.connect((host, port))
                    s.close()
                    dt = (time.perf_counter() - t0) * 1000.0
                    return True, dt
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback to ICMP ping command
        try:
            res = subprocess.run(
                ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host],
                capture_output=True,
                text=True,
                timeout=timeout + 1.0
            )
            if res.returncode == 0:
                dt = (time.perf_counter() - t0) * 1000.0
                return True, dt
        except Exception:
            pass

        return False, 0.0

    @classmethod
    def test_dns_lookup(cls, domain: str = "google.com", timeout: float = 2.5) -> Tuple[bool, str]:
        """Tests DNS resolution using socket.gethostbyname."""
        try:
            socket.setdefaulttimeout(timeout)
            ip = socket.gethostbyname(domain)
            return True, ip
        except Exception:
            pass

        # PowerShell fallback
        try:
            cmd = f"Resolve-DnsName -Name {domain} -QuickTimeout | Select-Object -ExpandProperty IPAddress -First 1"
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=timeout + 1.5
            )
            if res.returncode == 0 and res.stdout.strip():
                return True, res.stdout.strip()
        except Exception:
            pass

        return False, ""

    @classmethod
    def test_https_connect(cls, url: str = "https://1.1.1.1", timeout: float = 3.0) -> bool:
        """Tests actual HTTPS handshake with a known reliable endpoint."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SINAX/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.status in (200, 301, 302, 403, 404)
        except Exception:
            return False

    # --- 1-Click Safe Repairs ---

    @classmethod
    def repair_flush_dns(cls) -> Tuple[bool, str]:
        """
        Executes Clear-DnsClientCache / ipconfig /flushdns.
        Very safe, zero risk, immediate effect.
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-DnsClientCache"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return True, "تم تفريغ ومسح ذاكرة التخزين المؤقت (DNS Cache) بنجاح."
            # Fallback
            sub = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=5)
            if sub.returncode == 0:
                return True, "تم تفريغ كاش DNS بنجاح."
        except Exception as e:
            return False, f"حدث خطأ أثناء مسح الكاش: {e}"
        return False, "تعذر مسح ذاكرة DNS."

    @classmethod
    def repair_renew_dhcp(cls) -> Tuple[bool, str]:
        """
        Releases and renews DHCP lease: ipconfig /release && ipconfig /renew.
        Safe, temporarily interrupts connection for 2-4 seconds.
        """
        try:
            subprocess.run(["ipconfig", "/release"], capture_output=True, text=True, timeout=8)
            res = subprocess.run(["ipconfig", "/renew"], capture_output=True, text=True, timeout=12)
            if res.returncode == 0:
                return True, "تم تجديد عنوان IP واستئجار DHCP بنجاح من الراوتر."
            return True, "تم إرسال طلب تجديد DHCP."
        except Exception as e:
            return False, f"خطأ أثناء تجديد DHCP: {e}"

    @classmethod
    def repair_restart_adapter(cls, adapter_name: str = "Wi-Fi") -> Tuple[bool, str]:
        """
        Disables and enables network adapter (requires elevation if not admin).
        """
        ps_cmd = f"Restart-NetAdapter -Name '{adapter_name}' -Confirm:$false"
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                return True, f"تمت إعادة تشغيل محول الشبكة ({adapter_name}) بنجاح."
            return False, "قد تتطلب إعادة تشغيل كرت الشبكة تشغيل البرنامج كمسؤول (Run as Administrator)."
        except Exception as e:
            return False, f"تعذر إعادة تشغيل المحول: {e}"

    @classmethod
    def repair_winsock_reset(cls) -> Tuple[bool, str]:
        """
        Resets Winsock catalog via `netsh winsock reset`.
        Safe system repair, requires Windows restart.
        """
        try:
            res = subprocess.run(
                ["netsh", "winsock", "reset"],
                capture_output=True,
                text=True,
                timeout=6
            )
            if res.returncode == 0:
                return True, "تمت إعادة ضبط كتالوج Winsock بنجاح. يُفضل إعادة تشغيل جهاز الكمبيوتر لتطبيق التغييرات."
            return False, "يتطلب إعادة ضبط Winsock صلاحية مسؤول النظام."
        except Exception as e:
            return False, f"خطأ: {e}"

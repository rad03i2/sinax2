# -*- coding: utf-8 -*-
"""
SINAX Wi-Fi Service (خدمة فحص وتحليل شبكات Wi-Fi)
Provides native Windows Wi-Fi inspection, nearby network scanning,
channel congestion analysis, signal history tracking, and Wi-Fi report generation.
"""

import collections
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.network.network_info_service import NetworkInfoService
from app.services.network.network_models import NearbyWifiNetwork, WifiConnectionInfo


class WifiService:
    """Manages Wi-Fi adapter queries, signal monitoring, and channel analysis."""

    _signal_history: collections.deque = collections.deque(maxlen=60)

    @classmethod
    def get_current_wifi_info(cls) -> Optional[WifiConnectionInfo]:
        """Returns the current connected Wi-Fi metadata."""
        info = NetworkInfoService.get_wifi_status()
        if info:
            cls._signal_history.append((time.time(), info.signal_quality_percent))
        return info

    @classmethod
    def get_signal_history(cls) -> List[Tuple[float, int]]:
        """Returns recorded signal history as list of (timestamp, percent)."""
        return list(cls._signal_history)

    @classmethod
    def scan_nearby_networks(cls) -> List[NearbyWifiNetwork]:
        """
        Scans for visible Wi-Fi networks using `netsh wlan show networks mode=bssid`.
        Strictly passive scan, no password extraction or cracking.
        """
        networks: List[NearbyWifiNetwork] = []
        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True,
                text=True,
                timeout=6,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode != 0 or not res.stdout:
                return networks

            current_ssid = ""
            current_auth = ""
            current_enc = ""

            lines = res.stdout.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("SSID "):
                    parts = line.split(":", 1)
                    current_ssid = parts[1].strip() if len(parts) > 1 else "Unknown"
                    if not current_ssid:
                        current_ssid = "(شبكة مخفية)"
                elif line.startswith("Authentication"):
                    parts = line.split(":", 1)
                    current_auth = parts[1].strip() if len(parts) > 1 else ""
                elif line.startswith("Encryption"):
                    parts = line.split(":", 1)
                    current_enc = parts[1].strip() if len(parts) > 1 else ""
                elif line.startswith("BSSID "):
                    parts = line.split(":", 1)
                    bssid = parts[1].strip() if len(parts) > 1 else ""

                    signal = 0
                    radio = "802.11n"
                    band = "2.4 GHz"
                    channel = 1

                    # Look ahead for BSSID parameters
                    j = i + 1
                    while j < len(lines):
                        subline = lines[j].strip()
                        if subline.startswith("BSSID ") or subline.startswith("SSID "):
                            break
                        if subline.startswith("Signal"):
                            s_val = subline.split(":", 1)[1].replace("%", "").strip()
                            try:
                                signal = int(s_val)
                            except ValueError:
                                pass
                        elif subline.startswith("Radio type"):
                            radio = subline.split(":", 1)[1].strip()
                        elif subline.startswith("Band"):
                            band = subline.split(":", 1)[1].strip()
                        elif subline.startswith("Channel"):
                            c_val = subline.split(":", 1)[1].strip()
                            try:
                                channel = int(c_val)
                            except ValueError:
                                pass
                        j += 1

                    sec_str = f"{current_auth} ({current_enc})" if current_enc else current_auth
                    networks.append(NearbyWifiNetwork(
                        ssid=current_ssid,
                        bssid=bssid,
                        signal_percent=signal,
                        channel=channel,
                        band_ghz=band,
                        security=sec_str or "WPA2",
                        radio_type=radio
                    ))
                    i = j - 1
                i += 1

        except Exception:
            pass

        return networks

    @classmethod
    def analyze_channels(cls, networks: List[NearbyWifiNetwork]) -> Dict[str, Any]:
        """
        Analyzes channel congestion across 2.4 GHz and 5 GHz bands.
        Returns channel distribution counts and smart recommendations.
        """
        ch_counts_24: Dict[int, int] = collections.defaultdict(int)
        ch_counts_5: Dict[int, int] = collections.defaultdict(int)

        for net in networks:
            if "5" in net.band_ghz:
                ch_counts_5[net.channel] += 1
            else:
                ch_counts_24[net.channel] += 1

        # Evaluate 2.4 GHz main channels (1, 6, 11)
        best_24 = 1
        min_24 = 999
        for ch in [1, 6, 11]:
            cnt = ch_counts_24.get(ch, 0)
            if cnt < min_24:
                min_24 = cnt
                best_24 = ch

        recommendations = []
        if networks:
            curr = cls.get_current_wifi_info()
            if curr:
                if "2.4" in curr.band_ghz:
                    recommendations.append(
                        f"أنت متصل بالتردد 2.4 GHz على القناة {curr.channel}. "
                        "إذا كان الراوتر وجهازك يدعمان التردد 5 GHz، فإن الانتقال إليه سيعطيك سرعات أعلى وتداخلاً أقل."
                    )
                else:
                    recommendations.append(
                        f"أنت متصل بالتردد السريع {curr.band_ghz} على القناة {curr.channel}، وهو تردد قليل الازدحام وممتاز للألعاب والمكالمات."
                    )
            recommendations.append(
                f"القناة الأقل ازدحاماً حالياً على تردد 2.4 GHz هي القناة {best_24} بعدد ({min_24}) شبكات مجاورة."
            )

        return {
            "channels_24": dict(ch_counts_24),
            "channels_5": dict(ch_counts_5),
            "best_channel_24": best_24,
            "total_networks": len(networks),
            "recommendations": recommendations
        }

    @classmethod
    def generate_wifi_report(cls) -> str:
        """Generates a comprehensive text report of Wi-Fi status and parameters."""
        info = cls.get_current_wifi_info()
        conn = NetworkInfoService.get_active_connection_summary()

        lines = [
            "============================================================",
            "                 تقرير شبكة Wi-Fi - SINAX                   ",
            "============================================================",
            f"التاريخ والوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"اسم المحول (Interface): {info.interface_name if info else 'غير متوفر'}",
            f"الحالة: {info.state if info else 'غير متصل'}",
            f"اسم الشبكة (SSID): {info.ssid if info else 'غير متوفر'}",
            f"عنوان نقطة الوصول (BSSID): {info.bssid if info else 'غير متوفر'}",
            f"قوة الإشارة: {info.signal_quality_percent if info else 0}%",
            f"القناة (Channel): {info.channel if info else 'غير متوفر'}",
            f"نطاق التردد (Band): {info.band_ghz if info else 'غير متوفر'}",
            f"المعيار اللاسلكي (Protocol): {info.protocol if info else 'غير متوفر'}",
            f"نوع الأمان (Auth): {info.authentication if info else 'غير متوفر'}",
            f"التشفير (Cipher): {info.cipher if info else 'غير متوفر'}",
            f"سرعة الاستقبال (Rx Rate): {info.receive_rate_mbps if info else 0} Mbps",
            f"سرعة الإرسال (Tx Rate): {info.transmit_rate_mbps if info else 0} Mbps",
            "------------------------------------------------------------",
            f"عنوان IPv4 المحلي: {conn.get('ipv4', 'غير متوفر')}",
            f"بوابة الراوتر (Gateway): {conn.get('gateway', 'غير متوفر')}",
            f"خوادم DNS: {', '.join(conn.get('dns_servers', []))}",
            "============================================================",
            "ملاحظة أمنية: هذا التقرير لا يتضمن كلمات المرور حفاظاً على الخصوصية."
        ]
        return "\n".join(lines)

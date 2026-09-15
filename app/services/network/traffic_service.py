# -*- coding: utf-8 -*-
"""
SINAX Traffic & Bandwidth Service (خدمة مراقبة استهلاك الإنترنت وسرعة الترافيك)
Tracks real-time bandwidth (Download/Upload MB/s), records rolling line-graph data,
computes daily/weekly usage, and monitors user-defined data caps.
"""

import collections
import time
from typing import Dict, List, Optional, Tuple

import psutil


class TrafficService:
    """Manages bandwidth speed tracking and usage statistics."""

    _last_time: float = 0.0
    _last_bytes_recv: int = 0
    _last_bytes_sent: int = 0

    # Rolling history for live graphs (last 60 ticks)
    _download_history: collections.deque = collections.deque(maxlen=60)
    _upload_history: collections.deque = collections.deque(maxlen=60)

    # Session peak records
    _peak_download_mbps: float = 0.0
    _peak_upload_mbps: float = 0.0

    @classmethod
    def sample_live_bandwidth(cls) -> Dict[str, float]:
        """
        Samples net_io_counters and computes instant download and upload speeds.
        Returns speeds in MB/s and Mbps, plus current peaks.
        """
        curr_time = time.perf_counter()
        io = psutil.net_io_counters()
        curr_recv = io.bytes_recv
        curr_sent = io.bytes_sent

        if cls._last_time <= 0:
            cls._last_time = curr_time
            cls._last_bytes_recv = curr_recv
            cls._last_bytes_sent = curr_sent
            return {
                "download_mb_s": 0.0,
                "upload_mb_s": 0.0,
                "download_mbps": 0.0,
                "upload_mbps": 0.0,
                "peak_download_mbps": cls._peak_download_mbps,
                "peak_upload_mbps": cls._peak_upload_mbps
            }

        dt = curr_time - cls._last_time
        if dt < 0.2:
            return {
                "download_mb_s": cls._download_history[-1] if cls._download_history else 0.0,
                "upload_mb_s": cls._upload_history[-1] if cls._upload_history else 0.0,
                "download_mbps": (cls._download_history[-1] * 8.0) if cls._download_history else 0.0,
                "upload_mbps": (cls._upload_history[-1] * 8.0) if cls._upload_history else 0.0,
                "peak_download_mbps": cls._peak_download_mbps,
                "peak_upload_mbps": cls._peak_upload_mbps
            }

        # Calculate bytes transferred in dt
        delta_recv = max(0, curr_recv - cls._last_bytes_recv)
        delta_sent = max(0, curr_sent - cls._last_bytes_sent)

        cls._last_time = curr_time
        cls._last_bytes_recv = curr_recv
        cls._last_bytes_sent = curr_sent

        down_mb_s = (delta_recv / dt) / (1024.0 * 1024.0)
        up_mb_s = (delta_sent / dt) / (1024.0 * 1024.0)

        down_mbps = down_mb_s * 8.0
        up_mbps = up_mb_s * 8.0

        if down_mbps > cls._peak_download_mbps:
            cls._peak_download_mbps = round(down_mbps, 1)
        if up_mbps > cls._peak_upload_mbps:
            cls._peak_upload_mbps = round(up_mbps, 1)

        cls._download_history.append(down_mb_s)
        cls._upload_history.append(up_mb_s)

        return {
            "download_mb_s": round(down_mb_s, 2),
            "upload_mb_s": round(up_mb_s, 2),
            "download_mbps": round(down_mbps, 1),
            "upload_mbps": round(up_mbps, 1),
            "peak_download_mbps": cls._peak_download_mbps,
            "peak_upload_mbps": cls._peak_upload_mbps
        }

    @classmethod
    def get_bandwidth_history(cls) -> Tuple[List[float], List[float]]:
        """Returns the rolling 60 samples of (download_mb_s, upload_mb_s)."""
        return list(cls._download_history), list(cls._upload_history)

    @classmethod
    def get_per_adapter_consumption(cls) -> Dict[str, Dict[str, float]]:
        """Returns total GB received and sent per network interface."""
        per_nic = psutil.net_io_counters(pernic=True)
        usage = {}
        for nic_name, stats in per_nic.items():
            if "loopback" in nic_name.lower():
                continue
            recv_gb = stats.bytes_recv / (1024.0 ** 3)
            sent_gb = stats.bytes_sent / (1024.0 ** 3)
            usage[nic_name] = {
                "recv_gb": round(recv_gb, 2),
                "sent_gb": round(sent_gb, 2),
                "total_gb": round(recv_gb + sent_gb, 2)
            }
        return usage

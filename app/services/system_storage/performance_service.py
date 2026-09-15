# -*- coding: utf-8 -*-
"""
SINAX Performance Monitoring Service
Collects real-time system metrics (CPU, RAM, Disk I/O) with:
- 60-second rolling history buffers for smooth live charts
- Top resource-consuming processes (CPU & Memory)
- Thread-safe background sampler
"""

import collections
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import psutil
from app.core.logger import get_logger
from app.services.system_storage.storage_scanner import format_bytes

logger = get_logger("performance_service")


@dataclass
class TopProcessItem:
    pid: int
    name: str
    cpu_percent: float
    memory_rss: int
    memory_formatted: str
    memory_percent: float


@dataclass
class PerformanceSnapshot:
    timestamp: float
    cpu_percent: float
    cpu_per_core: List[float]
    cpu_cores_logical: int
    cpu_cores_physical: int
    cpu_freq_current: float     # MHz
    ram_total: int
    ram_used: int
    ram_available: int
    ram_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    disk_read_mb_s: float
    disk_write_mb_s: float
    top_cpu_processes: List[TopProcessItem] = field(default_factory=list)
    top_mem_processes: List[TopProcessItem] = field(default_factory=list)


class PerformanceService:
    """Manages real-time metric sampling and rolling history buffers."""

    def __init__(self, history_len: int = 60):
        self.history_len = history_len
        self.cpu_history: collections.deque = collections.deque(maxlen=history_len)
        self.ram_history: collections.deque = collections.deque(maxlen=history_len)
        self.disk_read_history: collections.deque = collections.deque(maxlen=history_len)
        self.disk_write_history: collections.deque = collections.deque(maxlen=history_len)

        self._lock = threading.Lock()
        self._last_snapshot: Optional[PerformanceSnapshot] = None
        self._last_disk_io: Optional[tuple] = None
        self._last_disk_time: float = 0.0

        # Initialize psutil non-blocking
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def sample(self) -> PerformanceSnapshot:
        """Take a single synchronous sample of system performance."""
        now = time.time()

        # 1. CPU
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_per_core = psutil.cpu_percent(percpu=True)
        except Exception:
            cpu_percent = 0.0
            cpu_per_core = []

        phys_cores = psutil.cpu_count(logical=False) or 1
        log_cores = psutil.cpu_count(logical=True) or phys_cores

        freq_curr = 0.0
        try:
            cf = psutil.cpu_freq()
            if cf:
                freq_curr = cf.current
        except Exception:
            pass

        # 2. RAM & Swap
        try:
            vm = psutil.virtual_memory()
            ram_total = vm.total
            ram_used = vm.used
            ram_avail = vm.available
            ram_pct = vm.percent
        except Exception:
            ram_total, ram_used, ram_avail, ram_pct = 0, 0, 0, 0.0

        try:
            sm = psutil.swap_memory()
            swap_total = sm.total
            swap_used = sm.used
            swap_pct = sm.percent
        except Exception:
            swap_total, swap_used, swap_pct = 0, 0, 0.0

        # 3. Disk I/O throughput
        disk_read_mb = 0.0
        disk_write_mb = 0.0
        try:
            dio = psutil.disk_io_counters()
            if dio:
                if self._last_disk_io is not None and self._last_disk_time > 0:
                    dt = max(0.001, now - self._last_disk_time)
                    dr = dio.read_bytes - self._last_disk_io[0]
                    dw = dio.write_bytes - self._last_disk_io[1]
                    disk_read_mb = max(0.0, (dr / (1024.0 * 1024.0)) / dt)
                    disk_write_mb = max(0.0, (dw / (1024.0 * 1024.0)) / dt)
                self._last_disk_io = (dio.read_bytes, dio.write_bytes)
                self._last_disk_time = now
        except Exception:
            pass

        # 4. Top Consumers
        top_cpu, top_mem = self._get_top_consumers()

        snapshot = PerformanceSnapshot(
            timestamp=now,
            cpu_percent=round(cpu_percent, 1),
            cpu_per_core=[round(c, 1) for c in cpu_per_core],
            cpu_cores_logical=log_cores,
            cpu_cores_physical=phys_cores,
            cpu_freq_current=round(freq_curr, 0),
            ram_total=ram_total,
            ram_used=ram_used,
            ram_available=ram_avail,
            ram_percent=round(ram_pct, 1),
            swap_total=swap_total,
            swap_used=swap_used,
            swap_percent=round(swap_pct, 1),
            disk_read_mb_s=round(disk_read_mb, 2),
            disk_write_mb_s=round(disk_write_mb, 2),
            top_cpu_processes=top_cpu,
            top_mem_processes=top_mem
        )

        with self._lock:
            self._last_snapshot = snapshot
            self.cpu_history.append(snapshot.cpu_percent)
            self.ram_history.append(snapshot.ram_percent)
            self.disk_read_history.append(snapshot.disk_read_mb_s)
            self.disk_write_history.append(snapshot.disk_write_mb_s)

        return snapshot

    def _get_top_consumers(self) -> tuple[List[TopProcessItem], List[TopProcessItem]]:
        """Collect top 5 processes by CPU and Memory."""
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'memory_percent']):
            try:
                info = p.info
                rss = info['memory_info'].rss if info.get('memory_info') else 0
                procs.append({
                    'pid': info['pid'],
                    'name': info['name'] or 'مجهول',
                    'cpu_percent': info.get('cpu_percent') or 0.0,
                    'memory_rss': rss,
                    'memory_percent': info.get('memory_percent') or 0.0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort top CPU
        by_cpu = sorted(procs, key=lambda x: x['cpu_percent'], reverse=True)[:5]
        top_cpu = [
            TopProcessItem(
                pid=x['pid'],
                name=x['name'],
                cpu_percent=round(x['cpu_percent'], 1),
                memory_rss=x['memory_rss'],
                memory_formatted=format_bytes(x['memory_rss']),
                memory_percent=round(x['memory_percent'], 1)
            )
            for x in by_cpu
        ]

        # Sort top RAM
        by_mem = sorted(procs, key=lambda x: x['memory_rss'], reverse=True)[:5]
        top_mem = [
            TopProcessItem(
                pid=x['pid'],
                name=x['name'],
                cpu_percent=round(x['cpu_percent'], 1),
                memory_rss=x['memory_rss'],
                memory_formatted=format_bytes(x['memory_rss']),
                memory_percent=round(x['memory_percent'], 1)
            )
            for x in by_mem
        ]

        return top_cpu, top_mem

    def get_last_snapshot(self) -> Optional[PerformanceSnapshot]:
        with self._lock:
            return self._last_snapshot

    def get_history(self) -> Dict[str, List[float]]:
        with self._lock:
            return {
                "cpu": list(self.cpu_history),
                "ram": list(self.ram_history),
                "disk_read": list(self.disk_read_history),
                "disk_write": list(self.disk_write_history),
            }

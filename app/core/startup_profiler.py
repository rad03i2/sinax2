# -*- coding: utf-8 -*-
"""
SINAX Startup Profiler & Benchmark
Tracks milestone durations during application initialization to guarantee
instant startup (< 1.5s) and monitor lazy module loading efficiency.
"""

import time
from typing import Dict, List, Tuple
from app.core.logger import get_logger

logger = get_logger("startup_profiler")


class StartupProfiler:
    """Singleton profiler tracking startup milestones."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StartupProfiler, cls).__new__(cls)
            cls._instance._start_time = time.perf_counter()
            cls._instance._milestones: List[Tuple[str, float]] = []
        return cls._instance

    @classmethod
    def record_milestone(cls, name: str):
        inst = cls()
        elapsed = time.perf_counter() - inst._start_time
        inst._milestones.append((name, elapsed))
        logger.info(f"[STARTUP] {name} reached at +{elapsed*1000:.1f}ms")

    @classmethod
    def get_summary(cls) -> Dict[str, float]:
        inst = cls()
        now = time.perf_counter()
        total_sec = now - inst._start_time
        summary = {"total_sec": round(total_sec, 3)}
        prev = 0.0
        for name, t in inst._milestones:
            duration = t - prev
            summary[name] = round(duration, 3)
            prev = t
        return summary

    @classmethod
    def print_benchmark_report(cls):
        inst = cls()
        total = time.perf_counter() - inst._start_time
        print("\n" + "=" * 45)
        print("  ⚡ SINAX STARTUP BENCHMARK REPORT")
        print("=" * 45)
        prev = 0.0
        for name, t in inst._milestones:
            delta = t - prev
            print(f"  ✓ {name:<26} : {delta*1000:6.1f} ms  (+{t*1000:6.1f} ms)")
            prev = t
        print("-" * 45)
        print(f"  TOTAL STARTUP TIME         : {total:6.3f} s")
        print("=" * 45 + "\n")

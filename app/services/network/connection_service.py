# -*- coding: utf-8 -*-
"""
SINAX Connection & Port Service (خدمة الاتصالات والمنافذ النشطة)
Inspects active TCP/UDP connections, maps endpoints to process PIDs and executable names,
provides local port availability testing, and checks remote host port accessibility.
"""

import socket
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import psutil


@dataclass
class ConnectionRecord:
    """Represents a network socket connection."""
    pid: Optional[int]
    process_name: str
    protocol: str       # "TCP" or "UDP"
    local_address: str
    local_port: int
    remote_address: str
    remote_port: Optional[int]
    state: str          # "ESTABLISHED", "LISTEN", "TIME_WAIT", etc.


class ConnectionService:
    """Manages active network connection queries and port diagnostics."""

    @classmethod
    def get_active_connections(cls, filter_established_only: bool = False) -> List[ConnectionRecord]:
        """Returns all current active inet connections with process names."""
        records: List[ConnectionRecord] = []
        try:
            conns = psutil.net_connections(kind="inet")
            proc_cache: Dict[int, str] = {}

            for c in conns:
                if filter_established_only and c.status != "ESTABLISHED":
                    continue

                pid = c.pid
                pname = "System"
                if pid:
                    if pid in proc_cache:
                        pname = proc_cache[pid]
                    else:
                        try:
                            pname = psutil.Process(pid).name()
                        except Exception:
                            pname = "منتهية"
                        proc_cache[pid] = pname

                l_ip = c.laddr.ip if c.laddr else "*"
                l_port = c.laddr.port if c.laddr else 0
                r_ip = c.raddr.ip if c.raddr else "*"
                r_port = c.raddr.port if c.raddr else None

                proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                status = c.status if c.status else ("LISTEN" if not r_ip or r_ip == "*" else "NONE")

                records.append(ConnectionRecord(
                    pid=pid,
                    process_name=pname,
                    protocol=proto,
                    local_address=l_ip,
                    local_port=l_port,
                    remote_address=r_ip,
                    remote_port=r_port,
                    state=status
                ))
        except Exception:
            pass

        return records

    @classmethod
    def find_process_by_port(cls, port: int) -> Optional[Dict[str, Any]]:
        """Looks up which application is listening or bound to a specific local port."""
        conns = cls.get_active_connections()
        for c in conns:
            if c.local_port == port:
                return {
                    "port": port,
                    "pid": c.pid,
                    "process_name": c.process_name,
                    "protocol": c.protocol,
                    "state": c.state,
                    "local_address": c.local_address
                }
        return None

    @classmethod
    def test_local_port_availability(cls, port: int) -> Tuple[bool, str]:
        """
        Tests if a port is free to bind locally or already occupied.
        Returns (is_available, message_ar).
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            s.close()
            return True, f"المنفذ {port} متاح محلياً وغير مستخدم حالياً ✓"
        except OSError:
            occ = cls.find_process_by_port(port)
            if occ:
                return False, f"المنفذ {port} مشغول بواسطة البرنامج ({occ['process_name']}) برقم العملية PID: {occ['pid']} ✗"
            return False, f"المنفذ {port} قيد الاستخدام أو محجوز من النظام ✗"

    @classmethod
    def test_remote_host_port(cls, host: str, port: int, timeout: float = 2.5) -> Tuple[bool, str, float]:
        """
        Tests TCP connection to a remote host:port.
        Returns (success, message_ar, latency_ms).
        """
        t0 = socket.getdefaulttimeout()
        import time
        start = time.perf_counter()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return True, f"الاتصال بالمنفذ {port} على {host} نجح بنجاح ({elapsed_ms:.1f} ms) ✓", round(elapsed_ms, 1)
        except Exception as e:
            return False, f"فشل الاتصال بالمنفذ {port} على {host}: {e} ✗", 0.0

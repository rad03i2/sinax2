# -*- coding: utf-8 -*-
"""
SINAX Process & File Lock Service
Manages system processes and identifies which processes are locking files/folders:
- Full process listing with CPU, Memory, User, and Path
- Detailed inspection (Parent, command line, open files)
- Critical process guardrails (protects csrss, lsass, smss, services, etc.)
- File Lock Finder ("من يستخدم هذا الملف؟")
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import psutil
from app.core.logger import get_logger
from app.services.system_storage.storage_scanner import format_bytes

logger = get_logger("process_service")

# Critical Windows Processes that must NEVER be terminated
CRITICAL_SYSTEM_PROCESSES: Set[str] = {
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "winlogon.exe",
    "dwminit.exe",
}


@dataclass
class ProcessInfo:
    pid: int
    name: str
    exe: str
    cmdline: str
    status: str
    status_ar: str
    cpu_percent: float
    memory_rss: int
    memory_formatted: str
    memory_percent: float
    num_threads: int
    username: str
    create_time: float
    is_critical: bool = False


@dataclass
class ProcessDetail:
    pid: int
    name: str
    exe: str
    cmdline: List[str]
    cwd: str
    ppid: int
    parent_name: str
    num_threads: int
    memory_rss: int
    memory_vms: int
    cpu_percent: float
    username: str
    open_files: List[str] = field(default_factory=list)
    is_critical: bool = False


@dataclass
class FileLockerInfo:
    pid: int
    name: str
    exe: str
    username: str
    locked_file_path: str


class ProcessService:
    """Provides process inspection, safe termination, and file lock discovery."""

    @staticmethod
    def _status_ar(status: str) -> str:
        s = (status or "").lower()
        mapping = {
            "running": "يعمل حالياً",
            "sleeping": "خامل / قيد الانتظار",
            "disk-sleep": "انتظار القرص",
            "stopped": "متوقف",
            "zombie": "معلق (Zombie)",
        }
        return mapping.get(s, s)

    @classmethod
    def list_processes(cls) -> List[ProcessInfo]:
        """Fetch list of all running processes."""
        current_pid = os.getpid()
        results: List[ProcessInfo] = []

        attrs = ['pid', 'name', 'exe', 'cmdline', 'status', 'cpu_percent',
                 'memory_info', 'memory_percent', 'num_threads', 'username', 'create_time']

        for p in psutil.process_iter(attrs):
            try:
                info = p.info
                pid = info['pid']
                name = info['name'] or 'مجهول'
                exe = info['exe'] or ''
                cmd_list = info['cmdline'] or []
                cmdline = " ".join(cmd_list) if cmd_list else ''
                status = info['status'] or 'unknown'
                mem_rss = info['memory_info'].rss if info.get('memory_info') else 0
                mem_pct = info.get('memory_percent') or 0.0
                cpu_pct = info.get('cpu_percent') or 0.0
                threads = info.get('num_threads') or 1
                user = info.get('username') or ''
                c_time = info.get('create_time') or 0.0

                is_crit = (name.lower() in CRITICAL_SYSTEM_PROCESSES or pid in (0, 4) or pid == current_pid)

                results.append(ProcessInfo(
                    pid=pid,
                    name=name,
                    exe=exe,
                    cmdline=cmdline,
                    status=status,
                    status_ar=cls._status_ar(status),
                    cpu_percent=round(cpu_pct, 1),
                    memory_rss=mem_rss,
                    memory_formatted=format_bytes(mem_rss),
                    memory_percent=round(mem_pct, 1),
                    num_threads=threads,
                    username=user,
                    create_time=c_time,
                    is_critical=is_crit
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return sorted(results, key=lambda x: x.memory_rss, reverse=True)

    @classmethod
    def get_process_detail(cls, pid: int) -> Optional[ProcessDetail]:
        """Get in-depth information about a specific process."""
        try:
            p = psutil.Process(pid)
            name = p.name()
            exe = ""
            try:
                exe = p.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            cmdline = []
            try:
                cmdline = p.cmdline()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            cwd = ""
            try:
                cwd = p.cwd()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            ppid = 0
            pname = ""
            try:
                ppid = p.ppid()
                parent = p.parent()
                if parent:
                    pname = parent.name()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            mem_info = p.memory_info()
            cpu_pct = p.cpu_percent(interval=None)
            threads = p.num_threads()

            user = ""
            try:
                user = p.username()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            open_files = []
            try:
                for f in p.open_files():
                    open_files.append(f.path)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            is_crit = (name.lower() in CRITICAL_SYSTEM_PROCESSES or pid in (0, 4))

            return ProcessDetail(
                pid=pid,
                name=name,
                exe=exe,
                cmdline=cmdline,
                cwd=cwd,
                ppid=ppid,
                parent_name=pname,
                num_threads=threads,
                memory_rss=mem_info.rss,
                memory_vms=mem_info.vms,
                cpu_percent=cpu_pct,
                username=user,
                open_files=open_files[:50],
                is_critical=is_crit
            )
        except Exception as e:
            logger.debug(f"Failed to get process detail for {pid}: {e}")
            return None

    @classmethod
    def terminate_process(cls, pid: int, force: bool = False) -> tuple[bool, str]:
        """Safely terminate or kill a process with strict guards on system processes."""
        current_pid = os.getpid()
        if pid == current_pid:
            return False, "لا يمكن إغلاق نافذة SINAX من خلال هذا الزر."

        if pid in (0, 4):
            return False, "عملية النظام الأساسية محمية ولا يمكن إنهاؤها."

        try:
            p = psutil.Process(pid)
            name = p.name().lower()

            if name in CRITICAL_SYSTEM_PROCESSES:
                return False, f"العملية '{p.name()}' حيوية لنظام التشغيل، وإيقافها يؤدي لخلل في ويندوز."

            if force:
                p.kill()
            else:
                p.terminate()

            return True, f"تم إنهاء العملية '{p.name()}' بنجاح."
        except psutil.NoSuchProcess:
            return False, "العملية لم تعد قيد التشغيل."
        except psutil.AccessDenied:
            return False, "تم رفض الوصول: تتطلب هذه العملية صلاحيات مسؤول لإنهائها."
        except Exception as e:
            return False, f"حدث خطأ أثناء إنهاء العملية: {str(e)}"

    @classmethod
    def find_file_lockers(cls, target_path: str) -> List[FileLockerInfo]:
        """Find processes currently holding an open handle to the target file or folder."""
        target_norm = os.path.normpath(os.path.abspath(target_path)).lower()
        is_dir = os.path.isdir(target_norm)
        lockers: List[FileLockerInfo] = []
        seen_pids: Set[int] = set()

        for p in psutil.process_iter(['pid', 'name', 'exe', 'username']):
            try:
                pid = p.info['pid']
                if pid in seen_pids or pid in (0, 4):
                    continue

                open_files = p.open_files()
                for of in open_files:
                    of_path = os.path.normpath(of.path).lower()
                    matched = False
                    if is_dir:
                        if of_path.startswith(target_norm + "\\") or of_path == target_norm:
                            matched = True
                    else:
                        if of_path == target_norm:
                            matched = True

                    if matched:
                        seen_pids.add(pid)
                        lockers.append(FileLockerInfo(
                            pid=pid,
                            name=p.info.get('name') or 'مجهول',
                            exe=p.info.get('exe') or '',
                            username=p.info.get('username') or '',
                            locked_file_path=of.path
                        ))
                        break
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            except Exception:
                continue

        return lockers

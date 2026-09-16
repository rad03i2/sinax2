# -*- coding: utf-8 -*-
"""Standalone SINAX updater.

Built as SINAX-Updater.exe. It waits for the running SINAX process to exit,
validates the patch payload, backs up touched files, applies replacements and
deletions, and rolls back automatically if installation fails.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def safe_rel_path(value: str) -> Path:
    p = Path(value.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unsafe patch path: {value}")
    return p


def wait_for_pid(pid: int, timeout_seconds: int = 90) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        SYNCHRONIZE = 0x00100000
        WAIT_OBJECT_0 = 0x00000000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return
        try:
            result = ctypes.windll.kernel32.WaitForSingleObject(handle, timeout_seconds * 1000)
            if result != WAIT_OBJECT_0:
                raise TimeoutError("SINAX did not exit in time")
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        return

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.25)
        except OSError:
            return
    raise TimeoutError("SINAX did not exit in time")


def extract_patch(package: Path, staging: Path) -> dict:
    with zipfile.ZipFile(package, "r") as zf:
        for name in zf.namelist():
            safe_rel_path(name)
        zf.extractall(staging)
    manifest_path = staging / "patch-manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("patch-manifest.json is missing")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def validate_payload(staging: Path, manifest: dict) -> None:
    for item in manifest.get("files", []):
        rel = safe_rel_path(str(item["path"]))
        src = staging / "files" / rel
        if not src.exists() or not src.is_file():
            raise RuntimeError(f"Missing patch file: {rel}")
        expected = str(item.get("sha256", "")).lower()
        if expected and sha256_file(src) != expected:
            raise RuntimeError(f"SHA-256 mismatch: {rel}")


def apply_patch(staging: Path, target: Path, manifest: dict, backup: Path) -> None:
    backup.mkdir(parents=True, exist_ok=True)
    touched = []

    try:
        for item in manifest.get("files", []):
            rel = safe_rel_path(str(item["path"]))
            src = staging / "files" / rel
            dst = target / rel
            bak = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            bak.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                shutil.copy2(dst, bak)
            touched.append((dst, bak, dst.exists()))
            tmp_dst = dst.with_suffix(dst.suffix + ".sinax-new")
            shutil.copy2(src, tmp_dst)
            os.replace(tmp_dst, dst)

        for raw in manifest.get("delete", []):
            rel = safe_rel_path(str(raw))
            dst = target / rel
            bak = backup / rel
            if dst.exists() and dst.is_file():
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bak)
                touched.append((dst, bak, True))
                dst.unlink()
    except Exception:
        for dst, bak, existed_before in reversed(touched):
            try:
                if existed_before and bak.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bak, dst)
                elif not existed_before and dst.exists():
                    dst.unlink()
            except Exception:
                pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--relaunch", required=True)
    args = parser.parse_args()

    package = Path(args.package).resolve()
    target = Path(args.target).resolve()
    relaunch = Path(args.relaunch).resolve()
    if not package.exists():
        raise FileNotFoundError(package)
    if not target.exists():
        raise FileNotFoundError(target)

    wait_for_pid(args.pid)

    staging = Path(tempfile.mkdtemp(prefix="sinax-update-"))
    try:
        manifest = extract_patch(package, staging)
        validate_payload(staging, manifest)
        from_version = str(manifest.get("from_version", "unknown"))
        to_version = str(manifest.get("to_version", "unknown"))
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = target / ".sinax-update-backup" / f"{from_version}-to-{to_version}-{stamp}"
        apply_patch(staging, target, manifest, backup)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    if relaunch.exists():
        subprocess.Popen([str(relaunch)], cwd=str(target), close_fds=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            log_dir = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "SINAX" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "updater-error.log").write_text(str(exc), encoding="utf-8")
        except Exception:
            pass
        raise

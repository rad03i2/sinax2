# -*- coding: utf-8 -*-
"""SINAX incremental update client.

Checks GitHub Releases for an update manifest, downloads only the patch that
matches the installed version, verifies SHA-256, then hands installation to the
separate SINAX-Updater.exe so the running application can be replaced safely.

For a private GitHub repository, set SINAX_GITHUB_TOKEN in the environment for
developer testing. Production clients should use a public release feed; no token
is ever embedded or persisted by SINAX.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, QCoreApplication

from app.core.constants import APP_VERSION
from app.core.logger import get_logger

logger = get_logger("update_service")

_RELEASES_API = "https://api.github.com/repos/rad03i2/sinax2/releases/latest"
_USER_AGENT = "SINAX-Updater/1.0"


def _version_tuple(value: str) -> tuple[int, ...]:
    value = (value or "0").strip().lstrip("vV")
    parts = []
    for token in value.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts or [0])


def _human_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


class UpdateService(QObject):
    changed = Signal()
    errorOccurred = Signal(str)
    updateFound = Signal(str)
    downloadFinished = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._state = "idle"
        self._status = "جاهز لفحص التحديثات"
        self._latest_version = APP_VERSION
        self._progress = 0
        self._update_available = False
        self._update_size = ""
        self._release_notes = ""
        self._selected_patch: Optional[Dict[str, Any]] = None
        self._release_assets: Dict[str, Dict[str, Any]] = {}
        self._busy = False

    @Property(str, notify=changed)
    def currentVersion(self) -> str:
        return APP_VERSION

    @Property(str, notify=changed)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(str, notify=changed)
    def state(self) -> str:
        return self._state

    @Property(str, notify=changed)
    def statusText(self) -> str:
        return self._status

    @Property(int, notify=changed)
    def progress(self) -> int:
        return self._progress

    @Property(bool, notify=changed)
    def updateAvailable(self) -> bool:
        return self._update_available

    @Property(str, notify=changed)
    def updateSize(self) -> str:
        return self._update_size

    @Property(str, notify=changed)
    def releaseNotes(self) -> str:
        return self._release_notes

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    def _set(self, *, state: Optional[str] = None, status: Optional[str] = None,
             progress: Optional[int] = None, busy: Optional[bool] = None) -> None:
        if state is not None:
            self._state = state
        if status is not None:
            self._status = status
        if progress is not None:
            self._progress = max(0, min(100, progress))
        if busy is not None:
            self._busy = busy
        self.changed.emit()

    def _headers(self, binary: bool = False) -> Dict[str, str]:
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("SINAX_GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _read_url(self, url: str, *, binary: bool = False) -> bytes:
        req = urllib.request.Request(url, headers=self._headers(binary=binary))
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()

    def _asset_bytes(self, asset: Dict[str, Any]) -> bytes:
        token = os.environ.get("SINAX_GITHUB_TOKEN", "").strip()
        url = asset.get("url") if token else asset.get("browser_download_url")
        if not url:
            raise RuntimeError("رابط ملف التحديث غير متاح")
        return self._read_url(url, binary=bool(token))

    @Slot()
    def checkForUpdates(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._selected_patch = None
        self._update_available = False
        self._progress = 0
        self._set(state="checking", status="جارٍ فحص GitHub Releases...", busy=True)
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            release = json.loads(self._read_url(_RELEASES_API).decode("utf-8"))
            tag = str(release.get("tag_name", "")).lstrip("vV")
            self._latest_version = tag or APP_VERSION
            self._release_notes = str(release.get("body") or "")[:4000]
            assets = release.get("assets") or []
            self._release_assets = {str(a.get("name")): a for a in assets if a.get("name")}

            if not tag or _version_tuple(tag) <= _version_tuple(APP_VERSION):
                self._update_available = False
                self._update_size = ""
                self._set(state="current", status="أنت تستخدم أحدث إصدار من SINAX", busy=False)
                return

            manifest_asset = self._release_assets.get("update-manifest.json")
            if not manifest_asset:
                self._set(
                    state="unsupported",
                    status="يوجد إصدار أحدث، لكن لا تتوفر له حزمة تحديث جزئي",
                    busy=False,
                )
                return

            manifest = json.loads(self._asset_bytes(manifest_asset).decode("utf-8"))
            patches = manifest.get("patches") or []
            selected = next(
                (p for p in patches if str(p.get("from_version", "")).lstrip("vV") == APP_VERSION),
                None,
            )
            if not selected:
                self._set(
                    state="unsupported",
                    status=f"الإصدار {tag} متاح، لكن لا يوجد Patch مباشر من {APP_VERSION}",
                    busy=False,
                )
                return

            asset_name = str(selected.get("asset", ""))
            if asset_name not in self._release_assets:
                raise RuntimeError("ملف Patch المذكور في manifest غير موجود في Release")

            self._selected_patch = selected
            self._update_available = True
            self._update_size = _human_size(int(selected.get("size", 0) or 0))
            self._set(
                state="available",
                status=f"يتوفر تحديث {tag} — الحجم {self._update_size}",
                busy=False,
            )
            self.updateFound.emit(tag)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                msg = (
                    "تعذر الوصول إلى مصدر التحديث. إذا كان مستودع GitHub خاصًا، "
                    "استخدم Release feed عامًا أو SINAX_GITHUB_TOKEN للاختبار فقط."
                )
            else:
                msg = f"فشل فحص التحديثات (HTTP {exc.code})"
            logger.warning("Update check failed: %s", exc)
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)
        except Exception as exc:
            logger.exception("Update check failed")
            msg = f"تعذر فحص التحديثات: {exc}"
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)

    @Slot()
    def downloadAndInstall(self) -> None:
        if self._busy or not self._selected_patch:
            return
        if not getattr(sys, "frozen", False):
            self._set(
                state="error",
                status="التثبيت التلقائي يعمل من نسخة SINAX المجمعة EXE فقط",
                busy=False,
            )
            return

        updater = Path(sys.executable).resolve().parent / "SINAX-Updater.exe"
        if not updater.exists():
            self._set(state="error", status="SINAX-Updater.exe غير موجود بجانب البرنامج", busy=False)
            return

        self._set(state="downloading", status="جارٍ تنزيل ملفات التحديث فقط...", progress=0, busy=True)
        threading.Thread(target=self._download_worker, args=(updater,), daemon=True).start()

    def _download_worker(self, updater: Path) -> None:
        try:
            patch = dict(self._selected_patch or {})
            asset_name = str(patch.get("asset", ""))
            asset = self._release_assets[asset_name]
            expected_size = int(asset.get("size", 0) or patch.get("size", 0) or 0)
            token = os.environ.get("SINAX_GITHUB_TOKEN", "").strip()
            url = asset.get("url") if token else asset.get("browser_download_url")
            if not url:
                raise RuntimeError("تعذر تحديد رابط تنزيل Patch")

            update_root = Path(tempfile.gettempdir()) / "SINAX" / "updates" / self._latest_version
            update_root.mkdir(parents=True, exist_ok=True)
            package_path = update_root / asset_name
            req = urllib.request.Request(url, headers=self._headers(binary=bool(token)))
            digest = hashlib.sha256()
            downloaded = 0
            with urllib.request.urlopen(req, timeout=60) as response, package_path.open("wb") as out:
                total = int(response.headers.get("Content-Length") or expected_size or 0)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if total:
                        self._set(progress=int(downloaded * 100 / total))

            expected_hash = str(patch.get("sha256", "")).lower().strip()
            actual_hash = digest.hexdigest().lower()
            if expected_hash and actual_hash != expected_hash:
                package_path.unlink(missing_ok=True)
                raise RuntimeError("فشل التحقق من SHA-256 لحزمة التحديث")

            target_dir = Path(sys.executable).resolve().parent
            args = [
                str(updater),
                "--package", str(package_path),
                "--target", str(target_dir),
                "--pid", str(os.getpid()),
                "--relaunch", str(Path(sys.executable).resolve()),
            ]
            subprocess.Popen(args, cwd=str(target_dir), close_fds=True)
            self._set(state="installing", status="تم التنزيل. سيُغلق SINAX لتطبيق التحديث...", progress=100, busy=False)
            self.downloadFinished.emit(str(package_path))
            QCoreApplication.quit()
        except Exception as exc:
            logger.exception("Update download failed")
            msg = f"فشل تنزيل أو تجهيز التحديث: {exc}"
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)


update_service = UpdateService()

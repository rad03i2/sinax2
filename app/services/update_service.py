# -*- coding: utf-8 -*-
"""SINAX incremental update client.

Checks GitHub Releases for a version-specific patch, downloads only changed
files, verifies SHA-256, and hands installation to SINAX-Updater.exe.
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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, QCoreApplication

from app.core.constants import APP_VERSION
from app.core.logger import get_logger

logger = get_logger("update_service")

_REPO = "rad03i2/sinax2"
_DEFAULT_RELEASES_API = f"https://api.github.com/repos/{_REPO}/releases/latest"
_RELEASES_API = os.environ.get("SINAX_UPDATE_API", _DEFAULT_RELEASES_API).strip() or _DEFAULT_RELEASES_API
_LATEST_MANIFEST_URL = f"https://github.com/{_REPO}/releases/latest/download/update-manifest.json"
_LATEST_ASSET_BASE = f"https://github.com/{_REPO}/releases/latest/download/"
_USER_AGENT = "SINAX-Updater/1.2"


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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def _latest_asset_url(name: str) -> str:
    return _LATEST_ASSET_BASE + urllib.parse.quote(name, safe="")


class UpdateService(QObject):
    changed = Signal()
    errorOccurred = Signal(str)
    updateFound = Signal(str)
    downloadFinished = Signal(str)
    installReady = Signal()
    quitRequested = Signal()

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
        self._auto_install = False

        self.installReady.connect(self._start_download_on_main)
        self.quitRequested.connect(QCoreApplication.quit)

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

    def _headers(self, binary: bool = False, *, include_token: bool = True) -> Dict[str, str]:
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("SINAX_GITHUB_TOKEN", "").strip()
        if include_token and token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _public_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": _USER_AGENT,
            "Accept": "*/*",
        }

    def _read_url(self, url: str, *, binary: bool = False) -> bytes:
        """Read GitHub API URL, retrying anonymously if a stale token fails."""
        req = urllib.request.Request(url, headers=self._headers(binary=binary))
        try:
            with urllib.request.urlopen(req, timeout=30 if not binary else 90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            token = os.environ.get("SINAX_GITHUB_TOKEN", "").strip()
            if token and exc.code in (401, 403, 404):
                logger.warning("Authenticated request failed (%s); retrying anonymously", exc.code)
                public_req = urllib.request.Request(
                    url,
                    headers=self._headers(binary=binary, include_token=False),
                )
                with urllib.request.urlopen(public_req, timeout=30 if not binary else 90) as response:
                    return response.read()
            raise

    def _read_public(self, url: str, *, timeout: int = 90) -> bytes:
        """Read a public GitHub release download URL without using the API/token."""
        req = urllib.request.Request(url, headers=self._public_headers())
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()

    @staticmethod
    def _asset_download_url(asset: Dict[str, Any]) -> str:
        return str(asset.get("browser_download_url") or asset.get("url") or "")

    def _asset_bytes(self, asset: Dict[str, Any]) -> bytes:
        url = self._asset_download_url(asset)
        if not url:
            raise RuntimeError("رابط ملف التحديث غير متاح")
        if url.startswith("https://github.com/"):
            return self._read_public(url)
        return self._read_url(url, binary=True)

    def _configure_from_manifest(self, manifest: Dict[str, Any]) -> bool:
        tag = str(manifest.get("version", "")).strip().lstrip("vV")
        self._latest_version = tag or APP_VERSION
        self._release_notes = ""
        logger.info("Public update manifest version=%s", tag)

        if not tag or _version_tuple(tag) <= _version_tuple(APP_VERSION):
            self._update_available = False
            self._update_size = ""
            self._auto_install = False
            self._set(state="current", status="أنت تستخدم أحدث إصدار من SINAX", busy=False)
            return True

        patches = manifest.get("patches") or []
        selected = next(
            (p for p in patches if str(p.get("from_version", "")).lstrip("vV") == APP_VERSION),
            None,
        )
        if not selected:
            self._auto_install = False
            self._set(
                state="unsupported",
                status=f"الإصدار {tag} متاح، لكن لا يوجد Patch مباشر من {APP_VERSION}",
                busy=False,
            )
            return True

        asset_name = str(selected.get("asset", "")).strip()
        if not asset_name:
            raise RuntimeError("اسم حزمة التحديث غير موجود في manifest")

        self._release_assets = {
            asset_name: {
                "name": asset_name,
                "browser_download_url": _latest_asset_url(asset_name),
                "size": int(selected.get("size", 0) or 0),
            },
            "SINAX-Updater.exe": {
                "name": "SINAX-Updater.exe",
                "browser_download_url": _latest_asset_url("SINAX-Updater.exe"),
            },
        }
        self._selected_patch = selected
        self._update_available = True
        self._update_size = _human_size(int(selected.get("size", 0) or 0))
        auto_install = self._auto_install
        self._auto_install = False
        self._set(
            state="available",
            status=f"يتوفر تحديث {tag} — الحجم {self._update_size}",
            busy=False,
        )
        self.updateFound.emit(tag)
        logger.info("Patch selected from public manifest: %s -> %s (%s)", APP_VERSION, tag, asset_name)
        if auto_install:
            self.installReady.emit()
        return True

    def _check_via_api(self) -> None:
        release = json.loads(self._read_url(_RELEASES_API).decode("utf-8"))
        tag = str(release.get("tag_name", "")).lstrip("vV")
        self._latest_version = tag or APP_VERSION
        self._release_notes = str(release.get("body") or "")[:4000]
        assets = release.get("assets") or []
        self._release_assets = {str(a.get("name")): a for a in assets if a.get("name")}
        logger.info("Latest GitHub API release=%s assets=%s", tag, len(self._release_assets))

        if not tag or _version_tuple(tag) <= _version_tuple(APP_VERSION):
            self._update_available = False
            self._update_size = ""
            self._auto_install = False
            self._set(state="current", status="أنت تستخدم أحدث إصدار من SINAX", busy=False)
            return

        manifest_asset = self._release_assets.get("update-manifest.json")
        if not manifest_asset:
            self._auto_install = False
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
            self._auto_install = False
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
        auto_install = self._auto_install
        self._auto_install = False
        self._set(
            state="available",
            status=f"يتوفر تحديث {tag} — الحجم {self._update_size}",
            busy=False,
        )
        self.updateFound.emit(tag)
        if auto_install:
            self.installReady.emit()

    @Slot()
    def checkForUpdates(self) -> None:
        logger.info("Update check requested. current=%s busy=%s", APP_VERSION, self._busy)
        if self._busy:
            self._set(status="هناك عملية تحديث قيد التنفيذ، انتظر قليلًا.")
            return
        self._busy = True
        self._selected_patch = None
        self._update_available = False
        self._progress = 0
        self._set(state="checking", status="جارٍ فحص تحديثات SINAX...", busy=True)
        threading.Thread(target=self._check_worker, name="sinax-update-check", daemon=True).start()

    def _check_worker(self) -> None:
        public_error: Optional[Exception] = None
        try:
            # Prefer a direct public Release asset. This avoids GitHub API rate limits
            # and does not require a token for the public repository.
            manifest = json.loads(self._read_public(_LATEST_MANIFEST_URL, timeout=45).decode("utf-8"))
            self._configure_from_manifest(manifest)
            return
        except Exception as exc:
            public_error = exc
            logger.warning("Public manifest check failed; falling back to GitHub API: %s", exc)

        try:
            self._check_via_api()
        except urllib.error.HTTPError as exc:
            self._auto_install = False
            msg = f"تعذر الوصول إلى تحديثات GitHub (HTTP {exc.code})."
            if exc.code == 403:
                msg += " قد يكون حد طلبات GitHub API قد تم تجاوزه مؤقتًا."
            logger.warning("API update check failed after public fallback: %s", exc)
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)
        except Exception as exc:
            self._auto_install = False
            logger.exception("Update check failed")
            detail = public_error or exc
            msg = f"تعذر فحص التحديثات: {detail}"
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)

    @Slot()
    def downloadAndInstall(self) -> None:
        logger.info(
            "Install button clicked. busy=%s patch=%s frozen=%s exe=%s",
            self._busy,
            bool(self._selected_patch),
            getattr(sys, "frozen", False),
            sys.executable,
        )
        if self._busy:
            self._set(status="هناك عملية تحديث قيد التنفيذ، انتظر قليلًا.")
            return

        if not self._selected_patch:
            self._auto_install = True
            self._set(state="checking", status="جارٍ تجهيز التحديث تلقائيًا...", progress=0, busy=False)
            self.checkForUpdates()
            return

        self._start_download_on_main()

    @Slot()
    def _start_download_on_main(self) -> None:
        if self._busy:
            return
        if not self._selected_patch:
            self._set(state="error", status="لم يتم تحديد حزمة تحديث صالحة. أعد الفحص.", busy=False)
            return
        if not getattr(sys, "frozen", False):
            msg = "التثبيت التلقائي يعمل من نسخة SINAX المجمعة EXE فقط"
            logger.error("Updater refused: application is not frozen. executable=%s", sys.executable)
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)
            return

        target_dir = Path(sys.executable).resolve().parent
        self._set(
            state="downloading",
            status="جارٍ تنزيل ملفات التحديث فقط...",
            progress=0,
            busy=True,
        )
        threading.Thread(
            target=self._download_worker,
            args=(target_dir,),
            name="sinax-update-download",
            daemon=True,
        ).start()

    def _ensure_updater(self, target_dir: Path) -> Path:
        updater = target_dir / "SINAX-Updater.exe"
        if updater.exists() and updater.is_file() and updater.stat().st_size > 0:
            return updater

        asset = self._release_assets.get("SINAX-Updater.exe") or {
            "browser_download_url": _latest_asset_url("SINAX-Updater.exe")
        }
        self._set(status="محرك التحديث غير موجود محليًا؛ جارٍ تنزيله تلقائيًا...")
        data = self._asset_bytes(asset)
        expected_digest = str(asset.get("digest") or "").lower().strip()
        if expected_digest.startswith("sha256:"):
            expected_hash = expected_digest.split(":", 1)[1]
            if _sha256_bytes(data) != expected_hash:
                raise RuntimeError("فشل التحقق من SINAX-Updater.exe")

        tmp = updater.with_suffix(".exe.sinax-new")
        tmp.write_bytes(data)
        os.replace(tmp, updater)
        logger.info("Downloaded missing updater to %s", updater)
        return updater

    def _download_worker(self, target_dir: Path) -> None:
        try:
            updater = self._ensure_updater(target_dir)
            patch = dict(self._selected_patch or {})
            asset_name = str(patch.get("asset", ""))
            asset = self._release_assets.get(asset_name) or {
                "browser_download_url": _latest_asset_url(asset_name),
                "size": int(patch.get("size", 0) or 0),
            }
            expected_size = int(asset.get("size", 0) or patch.get("size", 0) or 0)
            url = self._asset_download_url(asset)
            if not url:
                raise RuntimeError("تعذر تحديد رابط تنزيل Patch")

            update_root = Path(tempfile.gettempdir()) / "SINAX" / "updates" / self._latest_version
            update_root.mkdir(parents=True, exist_ok=True)
            package_path = update_root / asset_name
            req = urllib.request.Request(url, headers=self._public_headers())
            digest = hashlib.sha256()
            downloaded = 0
            logger.info("Downloading patch from %s", url)
            with urllib.request.urlopen(req, timeout=120) as response, package_path.open("wb") as out:
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

            args = [
                str(updater),
                "--package", str(package_path),
                "--target", str(target_dir),
                "--pid", str(os.getpid()),
                "--relaunch", str(Path(sys.executable).resolve()),
            ]
            logger.info("Launching external updater: %s", updater)
            subprocess.Popen(args, cwd=str(target_dir), close_fds=True)
            self._set(
                state="installing",
                status="تم التنزيل بنجاح. سيُغلق SINAX الآن لتطبيق التحديث...",
                progress=100,
                busy=False,
            )
            self.downloadFinished.emit(str(package_path))
            self.quitRequested.emit()
        except Exception as exc:
            logger.exception("Update download/install preparation failed")
            msg = f"فشل تنزيل أو تجهيز التحديث: {exc}"
            self._set(state="error", status=msg, busy=False)
            self.errorOccurred.emit(msg)


update_service = UpdateService()

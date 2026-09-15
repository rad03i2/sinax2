# -*- coding: utf-8 -*-
"""
SINAX Before & After Format Backup & Restore Service
Exports application inventory into JSON, WinGet export, standalone HTML reports, and CSV.
Provides post-format application restoration checklist and sequential re-installation queue.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.apps_manager.app_model import InstalledApp, format_bytes
from app.services.apps_manager.providers.winget_provider import WingetProvider

logger = logging.getLogger("SINAX.apps_manager.backup_restore_service")


@dataclass
class RestoreItemResult:
    package_id: str
    name: str
    success: bool
    exit_code: int = 0
    message: str = ""


@dataclass
class BatchRestoreReport:
    total_requested: int = 0
    succeeded: List[RestoreItemResult] = field(default_factory=list)
    failed: List[RestoreItemResult] = field(default_factory=list)
    cancelled: bool = False


class BackupRestoreService:
    """Handles software inventory backups before format and batch restoration after format."""

    @classmethod
    def export_backup_bundle(cls, apps: List[InstalledApp], destination_dir: str) -> Dict[str, str]:
        """Exports full software inventory bundle (JSON, WinGet JSON, HTML, CSV)."""
        os.makedirs(destination_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}

        # 1. SINAX Native JSON Backup
        json_path = os.path.join(destination_dir, f"SINAX_Apps_Backup_{timestamp}.json")
        backup_payload = {
            "version": "1.0",
            "generator": "SINAX - ساينكس",
            "created_at": datetime.now().isoformat(),
            "total_apps": len(apps),
            "disclaimer": "تحفظ هذه النسخة قائمة البرامج ومصادر تثبيتها التلقائي، وليست نسخة احتياطية من الملفات الشخصية أو إعدادات البرامج.",
            "apps": [
                {
                    "name": a.name,
                    "version": a.version,
                    "publisher": a.publisher,
                    "package_id": a.package_id,
                    "source": a.source,
                    "architecture": a.architecture,
                    "install_location": a.install_location,
                    "help_link": a.help_link or a.url_info_about,
                    "size_bytes": a.effective_size_bytes,
                }
                for a in apps
            ],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, ensure_ascii=False, indent=2)
        results["json"] = json_path

        # 2. WinGet Native Export
        if WingetProvider.is_available():
            winget_path = os.path.join(destination_dir, f"winget_packages_{timestamp}.json")
            if WingetProvider.export_packages(winget_path):
                results["winget"] = winget_path

        # 3. Formatted HTML Report
        html_path = os.path.join(destination_dir, f"SINAX_Apps_Report_{timestamp}.html")
        cls._generate_html_report(apps, html_path)
        results["html"] = html_path

        # 4. CSV Spreadsheet
        csv_path = os.path.join(destination_dir, f"SINAX_Apps_List_{timestamp}.csv")
        cls._generate_csv_report(apps, csv_path)
        results["csv"] = csv_path

        logger.info(f"Exported backup bundle to {destination_dir}: {list(results.keys())}")
        return results

    @classmethod
    def inspect_backup_file(cls, file_path: str) -> Dict[str, Any]:
        """
        Parses a backup JSON file (either SINAX backup or winget export) and returns
        a structured inventory ready for interactive re-installation.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"ملف النسخة الاحتياطية غير موجود: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        installable_items = []
        manual_items = []

        # Case A: SINAX Backup format
        if "apps" in data and isinstance(data["apps"], list):
            for item in data["apps"]:
                pkg_id = item.get("package_id")
                name = item.get("name", "برنامج بدون اسم")
                pub = item.get("publisher", "")
                ver = item.get("version", "")
                link = item.get("help_link", "")

                entry = {
                    "name": name,
                    "publisher": pub,
                    "version": ver,
                    "package_id": pkg_id,
                    "help_link": link,
                    "installable_via_winget": bool(pkg_id and not pkg_id.startswith("ARP\\")),
                    "selected": bool(pkg_id and not pkg_id.startswith("ARP\\")),
                }
                if entry["installable_via_winget"]:
                    installable_items.append(entry)
                else:
                    manual_items.append(entry)

        # Case B: Standard WinGet export format
        elif "Sources" in data and isinstance(data["Sources"], list):
            for src in data["Sources"]:
                packages = src.get("Packages", [])
                for p in packages:
                    pkg_id = p.get("PackageIdentifier")
                    entry = {
                        "name": pkg_id or "WinGet Package",
                        "publisher": "WinGet Source",
                        "version": p.get("Version", ""),
                        "package_id": pkg_id,
                        "help_link": "",
                        "installable_via_winget": True,
                        "selected": True,
                    }
                    installable_items.append(entry)

        return {
            "total_count": len(installable_items) + len(manual_items),
            "installable_count": len(installable_items),
            "manual_count": len(manual_items),
            "installable_items": installable_items,
            "manual_items": manual_items,
        }

    @classmethod
    def execute_restore_queue(
        cls,
        items_to_install: List[Dict[str, Any]],
        progress_cb: Optional[Callable[[int, int, str, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> BatchRestoreReport:
        """Executes sequential batch installation of restored applications via WinGet."""
        report = BatchRestoreReport(total_requested=len(items_to_install))

        for idx, item in enumerate(items_to_install):
            if cancel_token and cancel_token():
                report.cancelled = True
                logger.info("Restore queue cancelled by user.")
                break

            pkg_id = item.get("package_id")
            name = item.get("name", pkg_id)

            if progress_cb:
                progress_cb(idx + 1, len(items_to_install), name, f"جارٍ تثبيت: {name} ({pkg_id})...")

            cmd = [
                "winget", "install",
                "--id", pkg_id,
                "--accept-source-agreements",
                "--accept-package-agreements",
                "--silent",
            ]

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if res.returncode == 0:
                    report.succeeded.append(RestoreItemResult(package_id=pkg_id, name=name, success=True, message="تم التثبيت بنجاح."))
                else:
                    report.failed.append(
                        RestoreItemResult(
                            package_id=pkg_id,
                            name=name,
                            success=False,
                            exit_code=res.returncode,
                            message=f"فشل التثبيت (كود {res.returncode}): {res.stderr.strip() or res.stdout.strip()[:100]}",
                        )
                    )
            except Exception as e:
                report.failed.append(RestoreItemResult(package_id=pkg_id, name=name, success=False, exit_code=-1, message=str(e)))

            time.sleep(1.0)

        return report

    @classmethod
    def _generate_html_report(cls, apps: List[InstalledApp], output_path: str):
        """Creates a standalone, modern HTML inventory document."""
        rows_html = []
        for a in apps:
            size_str = a.display_size
            date_str = a.formatted_install_date
            link_html = f'<a href="{a.help_link}" target="_blank">الموقع</a>' if a.help_link else "-"
            winget_badge = f'<span class="badge badge-winget">{a.package_id}</span>' if a.package_id else '<span class="badge badge-manual">يدوي</span>'

            rows_html.append(f"""
            <tr>
                <td><strong>{a.name}</strong></td>
                <td>{a.version}</td>
                <td>{a.publisher}</td>
                <td>{size_str}</td>
                <td>{date_str}</td>
                <td>{winget_badge}</td>
                <td>{link_html}</td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تقرير البرامج المثبتة - SINAX</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0D1117; color: #C9D1D9; margin: 0; padding: 24px; }}
        .header {{ background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
        h1 {{ color: #58A6FF; margin: 0 0 10px 0; }}
        .meta {{ color: #8B949E; font-size: 14px; }}
        .disclaimer {{ background: #1F242C; border-right: 4px solid #F0883E; padding: 10px 14px; margin-top: 14px; border-radius: 4px; font-size: 13px; }}
        table {{ width: 100%; border-collapse: collapse; background: #161B22; border-radius: 12px; overflow: hidden; border: 1px solid #30363D; }}
        th, td {{ padding: 12px 16px; text-align: right; border-bottom: 1px solid #21262D; }}
        th {{ background: #21262D; color: #F0F6FC; font-size: 14px; }}
        tr:hover {{ background: #1C2128; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .badge-winget {{ background: #1F6FEB; color: white; }}
        .badge-manual {{ background: #30363D; color: #8B949E; }}
        a {{ color: #58A6FF; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>قائمة البرامج المثبتة (نسخة قبل الفورمات)</h1>
        <div class="meta">تم التصدير بواسطة SINAX – ساينكس بتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | إجمالي البرامج: {len(apps)}</div>
        <div class="disclaimer">تنبيه: هذه القائمة تحفظ بيانات البرامج ومعرفات تثبيتها لإعادة تنصيبها بعد تثبيت ويندوز، ولا تحتوي على ملفات أو إعدادات البرامج الداخلية.</div>
    </div>
    <table>
        <thead>
            <tr>
                <th>اسم البرنامج</th>
                <th>الإصدار</th>
                <th>الناشر</th>
                <th>الحجم</th>
                <th>تاريخ التثبيت</th>
                <th>معرف WinGet</th>
                <th>رابط الموقع</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows_html)}
        </tbody>
    </table>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    @classmethod
    def _generate_csv_report(cls, apps: List[InstalledApp], output_path: str):
        """Generates UTF-8 BOM CSV table for Excel compatibility."""
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["اسم البرنامج", "الإصدار", "الناشر", "الحجم التقديري", "تاريخ التثبيت", "معرف WinGet", "المسار", "رابط الموقع"])
            for a in apps:
                writer.writerow([
                    a.name,
                    a.version,
                    a.publisher,
                    a.display_size,
                    a.formatted_install_date,
                    a.package_id or "",
                    a.install_location or "",
                    a.help_link or a.url_info_about or "",
                ])

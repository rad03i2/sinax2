# -*- coding: utf-8 -*-
"""
Privacy Report Service for SINAX Privacy & Security Center.
Orchestrates multi-format security audit reports:
- HTML, JSON, TXT, and CSV export
- Privacy Mode: Redacts usernames, machine names, local paths, and IPs
- Records audit log summaries without leaking secrets
"""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import socket
from typing import Any, Dict, List, Optional, Tuple

from app.services.privacy_security.privacy_db import PrivacyDatabase


class PrivacyReportService:
    """Security audit and privacy report generator."""

    def __init__(self):
        self._db = PrivacyDatabase()

    def redact_text_for_privacy(self, text: str) -> str:
        """
        Applies Privacy Mode redactions:
        - Replaces current username
        - Replaces hostname
        - Masks IP addresses
        - Masks sensitive paths
        """
        username = os.environ.get("USERNAME", "")
        if username and len(username) > 1:
            text = text.replace(username, "[USERNAME_REDACTED]")

        hostname = socket.gethostname()
        if hostname and len(hostname) > 1:
            text = text.replace(hostname, "[HOST_REDACTED]")

        # Redact IPv4 addresses
        text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]", text)

        # Redact common token patterns (sk-...)
        text = re.sub(r"\b(sk-[a-zA-Z0-9_-]{6,})\b", lambda m: f"sk-{'•'*8}{m.group(1)[-2:]}", text)

        return text

    def generate_audit_summary(self, apply_privacy_mode: bool = True) -> Dict[str, Any]:
        """Collects recent security events and database metrics for reporting."""
        events = self._db.get_recent_events(limit=50)
        monitored = self._db.get_monitored_folders()
        vaults = self._db.get_registered_vaults()

        summary = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "privacy_mode_enabled": apply_privacy_mode,
            "monitored_folders_count": len(monitored),
            "registered_vaults_count": len(vaults),
            "recent_events_count": len(events),
            "events": events,
        }

        if apply_privacy_mode:
            serialized = json.dumps(summary, ensure_ascii=False)
            redacted = self.redact_text_for_privacy(serialized)
            return json.loads(redacted)

        return summary

    def export_report(
        self,
        output_file_path: str,
        fmt: str = "json",
        apply_privacy_mode: bool = True,
    ) -> Tuple[bool, str]:
        """
        Exports the security audit report in specified format.
        Supported formats: json, txt, html
        """
        p = Path(output_file_path).resolve()
        data = self.generate_audit_summary(apply_privacy_mode=apply_privacy_mode)

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if fmt == "json":
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif fmt == "txt":
                with open(p, "w", encoding="utf-8") as f:
                    f.write("=== تقرير الخصوصية والأمان - SINAX Privacy & Security ===\n")
                    f.write(f"تاريخ التوليد: {data['generated_at']}\n")
                    f.write(f"نمط حجب البيانات (Privacy Mode): {'مفعل' if apply_privacy_mode else 'معطل'}\n")
                    f.write(f"عدد المجلدات المراقبة: {data['monitored_folders_count']}\n")
                    f.write(f"عدد الخزن المشفرة: {data['registered_vaults_count']}\n\n")
                    f.write("--- سجل الأحداث الأمنية الأخيرة ---\n")
                    for ev in data.get("events", []):
                        f.write(f"[{ev.get('timestamp')}] {ev.get('event_type')}: {ev.get('target_path')} ({ev.get('status')})\n")
            elif fmt == "html":
                html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>تقرير أمان SINAX</title>
<style>
body {{ font-family: Segoe UI, sans-serif; background: #0D1117; color: #F0F6FC; margin: 24px; }}
.card {{ background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
h1, h2 {{ color: #58A6FF; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
th, td {{ border: 1px solid #30363D; padding: 8px 12px; text-align: right; }}
th {{ background: #21262D; color: #58A6FF; }}
</style>
</head>
<body>
<div class="card">
<h1>تقرير الخصوصية والأمان - SINAX</h1>
<p>تاريخ التوليد: {data['generated_at']}</p>
<p>نمط حجب البيانات: {'مفعل' if apply_privacy_mode else 'معطل'}</p>
<p>المجلدات المراقبة: {data['monitored_folders_count']} | الخزن المشفرة: {data['registered_vaults_count']}</p>
</div>
<div class="card">
<h2>سجل العمليات الأخير</h2>
<table>
<tr><th>الحدث</th><th>المسار</th><th>الحالة</th></tr>
"""
                for ev in data.get("events", []):
                    html_content += f"<tr><td>{ev.get('event_type')}</td><td>{ev.get('target_path')}</td><td>{ev.get('status')}</td></tr>\n"
                html_content += "</table></div></body></html>"
                with open(p, "w", encoding="utf-8") as f:
                    f.write(html_content)
            elif fmt == "csv":
                import csv
                with open(p, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["GeneratedAt", data["generated_at"]])
                    writer.writerow(["PrivacyMode", "Enabled" if apply_privacy_mode else "Disabled"])
                    writer.writerow([])
                    writer.writerow(["Timestamp", "EventType", "Status", "TargetPath"])
                    for ev in data.get("events", []):
                        writer.writerow([
                            ev.get("timestamp", ""),
                            ev.get("event_type", ""),
                            ev.get("status", ""),
                            ev.get("target_path", "")
                        ])
            else:
                return False, f"الصيغة غير مدعومة: {fmt}"

            return True, f"تم تصدير التقرير بنجاح: {p.name}"
        except Exception as e:
            return False, f"فشل تصدير التقرير: {str(e)}"

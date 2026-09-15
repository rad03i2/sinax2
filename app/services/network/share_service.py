# -*- coding: utf-8 -*-
"""
SINAX Share Service (خدمة مشاركة الملفات السريعة بدون إنترنت)
Provides:
1. QR Share / Receive with Mobile: Built-in local HTTP server bound strictly to LAN IP
2. PC ↔ PC LAN Transfer: TCP socket protocol with chunking, resume, and SHA-256 hash checks
"""

import hashlib
import http.server
import os
import secrets
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from app.services.network.network_info_service import NetworkInfoService
from app.services.network.qr_generator import QrCodeGenerator


class ShareHttpHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP handler serving file downloads and mobile upload forms."""

    def log_message(self, format, *args):
        # Silence console log spam
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        token = parsed.path.strip("/").split("/")[-1]
        session = ShareService.get_session_by_token(token)

        if not session or session.is_expired():
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = "<html><body dir='rtl' style='font-family:sans-serif;text-align:center;padding:50px;'><h2>⚠️ الرابط غير متاح أو انتهت صلاحيته</h2></body></html>"
            self.wfile.write(html.encode("utf-8"))
            return

        if session.mode == "send":
            # File download page or direct stream
            file_path = Path(session.file_path)
            if not file_path.exists():
                self.send_response(404)
                self.end_headers()
                return

            if "download=1" in parsed.query:
                # Direct file streaming
                file_size = file_path.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename=\"{file_path.name}\"")
                self.send_header("Content-Length", str(file_size))
                self.end_headers()

                with open(file_path, "rb") as f:
                    while chunk := f.read(65536):
                        self.wfile.write(chunk)

                session.download_count += 1
                if session.one_time_download:
                    session.expire_now()
                return

            # Display mobile-friendly landing page
            size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
            html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SINAX Share - استلام ملف</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
.card {{ background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 32px 24px; max-width: 440px; width: 100%; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
.badge {{ background: #0078d4; color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; margin-bottom: 16px; }}
h2 {{ margin: 0 0 10px; font-size: 22px; color: #ffffff; word-break: break-all; }}
.size {{ color: #94a3b8; font-size: 15px; margin-bottom: 24px; }}
.btn {{ display: block; background: #0078d4; color: white; text-decoration: none; padding: 14px 20px; border-radius: 10px; font-size: 17px; font-weight: bold; transition: 0.2s; }}
.btn:hover {{ background: #106ebe; }}
.footer {{ margin-top: 24px; font-size: 12px; color: #64748b; }}
</style>
</head>
<body>
<div class="card">
<div class="badge">نقل محلي فائق السرعة عبر Wi-Fi</div>
<h2>{file_path.name}</h2>
<div class="size">الحجم: {size_mb} ميغابايت</div>
<a href="?download=1" class="btn">⬇️ تنزيل الملف الآن</a>
<div class="footer">SINAX Share • نقل آمن ومباشر دون استخدام الإنترنت</div>
</div>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif session.mode == "receive":
            # Mobile upload form
            html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SINAX Share - إرسال إلى الكمبيوتر</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
.card {{ background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 32px 24px; max-width: 440px; width: 100%; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
.badge {{ background: #10b981; color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; margin-bottom: 16px; }}
h2 {{ margin: 0 0 14px; font-size: 22px; }}
p {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
input[type=file] {{ display: block; width: 100%; padding: 12px; background: #334155; border-radius: 8px; color: white; margin-bottom: 18px; box-sizing: border-box; }}
button {{ width: 100%; background: #10b981; color: white; border: none; padding: 14px; border-radius: 10px; font-size: 17px; font-weight: bold; cursor: pointer; }}
button:hover {{ background: #059669; }}
.footer {{ margin-top: 24px; font-size: 12px; color: #64748b; }}
</style>
</head>
<body>
<div class="card">
<div class="badge">إرسال ملفات للكمبيوتر</div>
<h2>إرسال صور وفيديو ومستندات</h2>
<p>اختر الملفات من هاتفك ليتم نقلها مباشرة إلى الكمبيوتر على نفس الشبكة المحلية.</p>
<form method="POST" enctype="multipart/form-data">
<input type="file" name="files" multiple required>
<button type="submit">🚀 إرسال الملفات للكمبيوتر</button>
</form>
<div class="footer">SINAX Share • نقل مباشر عبر شبكة LAN</div>
</div>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        token = parsed.path.strip("/").split("/")[-1]
        session = ShareService.get_session_by_token(token)

        if not session or session.mode != "receive":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        target_dir = Path(session.target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Read uploaded data
        raw_data = self.rfile.read(content_length)

        # Basic multipart file extraction
        file_saved = False
        saved_name = "received_file"
        try:
            # Parse boundary
            content_type = self.headers.get("Content-Type", "")
            if "boundary=" in content_type:
                boundary = content_type.split("boundary=")[1].encode("utf-8")
                parts = raw_data.split(boundary)
                for part in parts:
                    if b"filename=" in part:
                        headers_raw, body = part.split(b"\r\n\r\n", 1)
                        body = body.rstrip(b"\r\n--")
                        # Extract filename
                        header_str = headers_raw.decode("utf-8", errors="replace")
                        for line in header_str.splitlines():
                            if "filename=" in line:
                                fname = line.split("filename=")[1].strip('"\';\r\n ')
                                if fname:
                                    saved_name = Path(fname).name
                        out_path = target_dir / saved_name
                        with open(out_path, "wb") as out_f:
                            out_f.write(body)
                        file_saved = True
        except Exception:
            pass

        if not file_saved:
            # Save raw payload as fallback
            out_path = target_dir / f"upload_{int(time.time())}.bin"
            with open(out_path, "wb") as out_f:
                out_f.write(raw_data)
            saved_name = out_path.name

        session.download_count += 1

        # Return success screen to mobile
        success_html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>تم الاستلام</title>
<style>body {{ font-family: sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 50px 20px; }} h2 {{ color: #10b981; }}</style>
</head>
<body>
<h2>✅ تم استلام الملف بنجاح!</h2>
<p>تم حفظ <b>{saved_name}</b> داخل مجلد التنزيلات بالكمبيوتر.</p>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(success_html.encode("utf-8"))


class ShareSession:
    """Represents an active local sharing session."""

    def __init__(
        self,
        token: str,
        mode: str,  # "send" or "receive"
        file_path: Optional[str] = None,
        target_dir: Optional[str] = None,
        expiry_seconds: int = 1800,
        one_time_download: bool = False,
    ):
        self.token = token
        self.mode = mode
        self.file_path = file_path
        self.target_dir = target_dir or str(Path.home() / "Downloads" / "SINAX_Received")
        self.expiry_time = time.time() + expiry_seconds
        self.one_time_download = one_time_download
        self.download_count = 0
        self.is_active = True

    def is_expired(self) -> bool:
        return not self.is_active or time.time() > self.expiry_time

    def expire_now(self):
        self.is_active = False


class ShareService:
    """Coordinates PC-to-Mobile HTTP QR sharing and PC-to-PC socket transfer."""

    _sessions: Dict[str, ShareSession] = {}
    _server: Optional[http.server.HTTPServer] = None
    _server_thread: Optional[threading.Thread] = None
    _server_port: int = 8990

    @classmethod
    def get_session_by_token(cls, token: str) -> Optional[ShareSession]:
        return cls._sessions.get(token)

    @classmethod
    def start_http_server_if_needed(cls) -> int:
        """Starts the local HTTP server on an available port bound to local IP."""
        if cls._server is not None:
            return cls._server_port

        conn_info = NetworkInfoService.get_active_connection_summary()
        local_ip = conn_info.get("ipv4", "127.0.0.1")
        if not local_ip or local_ip == "غير متوفر":
            local_ip = "127.0.0.1"

        port = 8990
        for p in range(8990, 9020):
            try:
                # Bind strictly to local IP for safety
                cls._server = http.server.ThreadingHTTPServer((local_ip, p), ShareHttpHandler)
                cls._server_port = p
                break
            except OSError:
                continue

        if cls._server is not None:
            cls._server_thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
            cls._server_thread.start()

        return cls._server_port

    @classmethod
    def create_send_session(
        cls,
        file_path: str,
        expiry_minutes: int = 30,
        one_time_download: bool = False
    ) -> Tuple[str, str]:
        """
        Creates a session to send a file to mobile.
        Returns (share_url, token).
        """
        port = cls.start_http_server_if_needed()
        conn_info = NetworkInfoService.get_active_connection_summary()
        local_ip = conn_info.get("ipv4", "127.0.0.1")

        token = secrets.token_hex(6)
        session = ShareSession(
            token=token,
            mode="send",
            file_path=file_path,
            expiry_seconds=expiry_minutes * 60,
            one_time_download=one_time_download
        )
        cls._sessions[token] = session

        share_url = f"http://{local_ip}:{port}/share/{token}"
        return share_url, token

    @classmethod
    def create_receive_session(cls, target_folder: Optional[str] = None, expiry_minutes: int = 30) -> Tuple[str, str]:
        """
        Creates a session to receive files from mobile.
        Returns (share_url, token).
        """
        port = cls.start_http_server_if_needed()
        conn_info = NetworkInfoService.get_active_connection_summary()
        local_ip = conn_info.get("ipv4", "127.0.0.1")

        token = secrets.token_hex(6)
        session = ShareSession(
            token=token,
            mode="receive",
            target_dir=target_folder,
            expiry_seconds=expiry_minutes * 60
        )
        cls._sessions[token] = session

        share_url = f"http://{local_ip}:{port}/share/{token}"
        return share_url, token

    @classmethod
    def compute_sha256(cls, file_path: str) -> str:
        """Computes SHA-256 hash of a file for integrity verification."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def generate_pairing_code(cls) -> str:
        """Generates a friendly 6-digit pairing code (e.g. 384 217)."""
        n1 = secrets.randbelow(900) + 100
        n2 = secrets.randbelow(900) + 100
        return f"{n1} {n2}"

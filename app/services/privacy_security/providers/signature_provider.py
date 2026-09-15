# -*- coding: utf-8 -*-
"""
Authenticode Signature Provider for SINAX Privacy & Security.
Validates digital signatures of executables, DLLs, MSIs, and scripts
using Windows Authenticode APIs and PowerShell fallback with Certificate extraction.
"""

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from app.services.privacy_security.models import CertificateDetails, SignatureStatus


class WindowsAuthenticodeProvider:
    """Primary Authenticode signature verifier for Windows."""

    @staticmethod
    def verify_file(file_path: str) -> Tuple[SignatureStatus, str, Optional[CertificateDetails]]:
        """
        Verifies the Authenticode signature of a given file.
        Returns: (SignatureStatus, publisher_name, CertificateDetails)
        """
        p = Path(file_path).resolve()
        if not p.exists():
            return SignatureStatus.UNKNOWN, "الملف غير موجود", None

        # Execute PowerShell Get-AuthenticodeSignature with JSON serialization
        ps_cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            f"""
            $sig = Get-AuthenticodeSignature -LiteralPath '{str(p)}'
            $cert = $sig.SignerCertificate
            $obj = @{{
                Status = $sig.Status.ToString()
                StatusMessage = $sig.StatusMessage
                Path = $sig.Path
                HasCert = ($cert -ne $null)
                Subject = if ($cert) {{ $cert.Subject }} else {{ "" }}
                Issuer = if ($cert) {{ $cert.Issuer }} else {{ "" }}
                SerialNumber = if ($cert) {{ $cert.SerialNumber }} else {{ "" }}
                ValidFrom = if ($cert) {{ $cert.NotBefore.ToString("yyyy-MM-dd HH:mm:ss") }} else {{ "" }}
                ValidTo = if ($cert) {{ $cert.NotAfter.ToString("yyyy-MM-dd HH:mm:ss") }} else {{ "" }}
                Thumbprint = if ($cert) {{ $cert.Thumbprint }} else {{ "" }}
                SignatureAlgorithm = if ($cert) {{ $cert.SignatureAlgorithm.FriendlyName }} else {{ "" }}
            }}
            $obj | ConvertTo-Json
            """
        ]

        try:
            res = subprocess.run(
                ps_cmd,
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                status_raw = str(data.get("Status") or "Unknown").lower()

                cert_details = None
                publisher = "غير معروف"

                if data.get("HasCert"):
                    subject = data.get("Subject", "")
                    # Extract CN (Common Name) for publisher
                    if "CN=" in subject:
                        parts = [x.strip() for x in subject.split(",") if x.strip().startswith("CN=")]
                        if parts:
                            publisher = parts[0][3:]
                        else:
                            publisher = subject
                    else:
                        publisher = subject or "غير محدد"

                    cert_details = CertificateDetails(
                        subject=subject,
                        issuer=data.get("Issuer", ""),
                        serial_number=data.get("SerialNumber", ""),
                        valid_from=data.get("ValidFrom", ""),
                        valid_to=data.get("ValidTo", ""),
                        thumbprint=data.get("Thumbprint", ""),
                        signature_algorithm=data.get("SignatureAlgorithm", ""),
                    )

                if status_raw == "valid":
                    return SignatureStatus.VALID, publisher, cert_details
                elif status_raw in ("notconfigured", "notpresent", "unknownfiletype"):
                    return SignatureStatus.UNSIGNED, "غير موقع رقمياً (Unsigned)", cert_details
                elif "expired" in status_raw:
                    return SignatureStatus.EXPIRED, publisher, cert_details
                elif "hashmismatch" in status_raw or "hash mismatch" in status_raw:
                    return SignatureStatus.HASH_MISMATCH, publisher, cert_details
                elif "untrusted" in status_raw or "untrustedroot" in status_raw:
                    return SignatureStatus.UNTRUSTED, publisher, cert_details
                elif status_raw in ("invalid", "invalidsignature"):
                    return SignatureStatus.INVALID, publisher, cert_details
                else:
                    return SignatureStatus.UNKNOWN, data.get("StatusMessage") or "حالة غير محددة", cert_details

        except Exception as e:
            pass

        return SignatureStatus.UNKNOWN, "تعذر قراءة التوقيع الرقمي", None


class SigcheckProvider:
    """Optional adapter for Microsoft Sysinternals Sigcheck utility if installed."""

    @staticmethod
    def is_available() -> bool:
        try:
            res = subprocess.run(
                ["sigcheck.exe", "-?"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    def scan_file(file_path: str) -> Optional[Dict[str, Any]]:
        """Runs sigcheck if available; otherwise returns None."""
        if not SigcheckProvider.is_available():
            return None

        try:
            res = subprocess.run(
                ["sigcheck.exe", "-a", "-c", file_path],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return {"output": res.stdout.strip()}
        except Exception:
            return None

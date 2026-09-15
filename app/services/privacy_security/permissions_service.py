# -*- coding: utf-8 -*-
"""
NTFS Permissions & Network Share Privacy Inspector for SINAX Privacy & Security.
Answers: "Who can access this file or folder?"
Inspects NTFS Access Control Lists (ACLs), Owner, Everyone write permissions,
and checks if folders are exposed over the local network.
"""

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from app.services.privacy_security.models import NTFSPermissionInfo


class PermissionsService:
    """NTFS Access Control List and network exposure inspector."""

    @classmethod
    def inspect_permissions(cls, path: str) -> NTFSPermissionInfo:
        """
        Inspects NTFS permissions for the specified file or folder using icacls / PowerShell.
        """
        p = Path(path).resolve()
        info = NTFSPermissionInfo()

        if not p.exists():
            info.warnings.append("المسار غير موجود.")
            return info

        try:
            # Query via PowerShell Get-Acl
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"""
                $acl = Get-Acl -LiteralPath '{str(p)}'
                $entries = @()
                foreach ($access in $acl.Access) {{
                    $entries += @{{
                        Identity = $access.IdentityReference.Value
                        AccessControlType = $access.AccessControlType.ToString()
                        Rights = $access.FileSystemRights.ToString()
                        IsInherited = $access.IsInherited
                    }}
                }}
                @{{
                    Owner = $acl.Owner
                    Entries = $entries
                }} | ConvertTo-Json -Depth 3
                """
            ]

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                info.owner = data.get("Owner", "غير محدد")
                raw_entries = data.get("Entries", [])
                if isinstance(raw_entries, dict):
                    raw_entries = [raw_entries]

                for e in raw_entries:
                    ident = str(e.get("Identity", ""))
                    rights = str(e.get("Rights", ""))
                    act = str(e.get("AccessControlType", ""))
                    is_inh = bool(e.get("IsInherited", False))

                    entry_dict = {
                        "identity": ident,
                        "rights": rights,
                        "type": act,
                        "inherited": is_inh,
                    }
                    info.entries.append(entry_dict)

                    ident_lower = ident.lower()
                    if ("everyone" in ident_lower or "الجميع" in ident_lower) and ("write" in rights.lower() or "fullcontrol" in rights.lower()):
                        info.has_everyone_write = True
                        info.warnings.append("تحذير أمني: مجموعة الجميع (Everyone) تملك صلاحية كتابة أو تحكم كامل في هذا الملف.")

                    if "users" in ident_lower and "fullcontrol" in rights.lower():
                        info.has_unrestricted_modify = True
                        info.warnings.append("ملاحظة: مجموعة المستخدمين العاديين تملك تحكماً كاملاً في هذا العنصر.")

        except Exception as e:
            info.warnings.append(f"تعذر استرداد أذونات NTFS: {str(e)}")

        return info

    @classmethod
    def check_network_share(cls, folder_path: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if the local folder is exposed via Windows SMB file sharing.
        Returns: (is_shared: bool, share_name: Optional[str])
        """
        p = Path(folder_path).resolve()
        if not p.exists() or not p.is_dir():
            return False, None

        str_p = str(p).lower()
        try:
            # Query net share
            res = subprocess.run(
                ["net", "share"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if str_p in line.lower():
                        share_name = line.split()[0]
                        return True, share_name
        except Exception:
            pass

        return False, None

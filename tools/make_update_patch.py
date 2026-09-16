# -*- coding: utf-8 -*-
"""Build a file-level SINAX update patch from two ONEDIR builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

# The updater is the process applying the patch. Replacing/deleting its own
# executable while it is running is unsafe on Windows, so it is shipped only
# with full releases and deliberately excluded from incremental patches.
IGNORED_PATHS = {"SINAX-Updater.exe"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def file_map(root: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in IGNORED_PATHS:
            continue
        result[rel] = {
            "path": path,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    return result


def _load_public_manifest(path: Path, to_version: str) -> dict:
    if not path.exists():
        return {"schema": 1, "version": to_version, "patches": []}
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": 1, "version": to_version, "patches": []}
    if str(existing.get("version", "")) != str(to_version):
        return {"schema": 1, "version": to_version, "patches": []}
    patches = existing.get("patches")
    if not isinstance(patches, list):
        patches = []
    return {"schema": 1, "version": to_version, "patches": patches}


def build_patch(previous: Path, current: Path, from_version: str, to_version: str,
                output_zip: Path, release_manifest: Path) -> dict:
    old = file_map(previous)
    new = file_map(current)

    changed = []
    for rel, info in new.items():
        old_info = old.get(rel)
        if not old_info or old_info["sha256"] != info["sha256"]:
            changed.append(rel)
    deleted = sorted(set(old) - set(new))

    staging = Path(tempfile.mkdtemp(prefix="sinax-patch-build-"))
    try:
        files_root = staging / "files"
        entries = []
        for rel in changed:
            src = new[rel]["path"]
            dst = files_root / Path(rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            entries.append({
                "path": rel,
                "sha256": new[rel]["sha256"],
                "size": new[rel]["size"],
            })

        patch_manifest = {
            "schema": 1,
            "from_version": from_version,
            "to_version": to_version,
            "files": entries,
            "delete": deleted,
        }
        (staging / "patch-manifest.json").write_text(
            json.dumps(patch_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        output_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(staging).as_posix())
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    patch_sha = sha256_file(output_zip)
    patch_size = output_zip.stat().st_size
    patch_info = {
        "from_version": from_version,
        "asset": output_zip.name,
        "sha256": patch_sha,
        "size": patch_size,
        "changed_files": len(changed),
        "deleted_files": len(deleted),
    }

    # Preserve patches generated from other supported installed versions. This
    # lets one Release contain direct patches such as 1.1.0 -> 1.1.2 and
    # 1.1.1 -> 1.1.2, so users do not need to install every intermediate build.
    public_manifest = _load_public_manifest(release_manifest, to_version)
    public_manifest["patches"] = [
        p for p in public_manifest["patches"]
        if str(p.get("from_version", "")) != str(from_version)
    ]
    public_manifest["patches"].append(patch_info)
    public_manifest["patches"].sort(key=lambda p: str(p.get("from_version", "")))
    release_manifest.write_text(
        json.dumps(public_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return public_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    previous = Path(args.previous).resolve()
    current = Path(args.current).resolve()
    if not previous.is_dir() or not current.is_dir():
        raise SystemExit("Both previous and current build directories must exist")

    result = build_patch(
        previous,
        current,
        args.from_version,
        args.to_version,
        Path(args.output).resolve(),
        Path(args.manifest).resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""
SINAX Icon System Builder & Validator CLI
Validates SVG assets, audits IconRegistry consistency, and generates icons.qrc.
"""

import os
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.icon_registry import IconRegistry, ICON_CATEGORIES, RTL_MIRRORABLE_ICONS


def validate_svg_files(icons_dir: Path) -> tuple[int, list[str]]:
    """Validates that all SVG files are well-formed XML and have 24x24 viewBox."""
    errors = []
    svg_count = 0

    if not icons_dir.is_dir():
        return 0, [f"Icons directory not found: {icons_dir}"]

    for svg_path in icons_dir.rglob("*.svg"):
        svg_count += 1
        rel_path = svg_path.relative_to(icons_dir)
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            # Strip XML namespace if present
            tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
            if tag != "svg":
                errors.append(f"[{rel_path}] Root element is <{tag}>, expected <svg>")

            viewbox = root.attrib.get("viewBox", "")
            if viewbox != "0 0 24 24":
                errors.append(f"[{rel_path}] Unexpected viewBox='{viewbox}', expected '0 0 24 24'")

        except ET.ParseError as pe:
            errors.append(f"[{rel_path}] Malformed XML: {pe}")
        except Exception as ex:
            errors.append(f"[{rel_path}] Read error: {ex}")

    return svg_count, errors


def validate_registry(icons_dir: Path) -> tuple[dict, list[str]]:
    """Audits IconRegistry against disk SVG assets."""
    errors = []
    reg = IconRegistry.get_all()
    aliases = IconRegistry.get_aliases()
    all_disk_svgs = {p.stem: p for p in icons_dir.rglob("*.svg")}

    # 1. Check all canonical icons have SVG files
    for name, meta in reg.items():
        if name not in all_disk_svgs:
            errors.append(f"Registered icon '{name}' has no matching SVG file on disk")
        else:
            actual_category = all_disk_svgs[name].parent.name
            if meta.category != actual_category:
                errors.append(f"Icon '{name}' declared category '{meta.category}', but file is in '{actual_category}'")

    # 2. Check all aliases point to canonical icons
    for alias_name, canonical_target in aliases.items():
        if canonical_target not in reg:
            errors.append(f"Alias '{alias_name}' points to unknown target '{canonical_target}'")

    # 3. Check RTL mirror definitions
    for mirror_icon in RTL_MIRRORABLE_ICONS:
        if mirror_icon not in reg:
            errors.append(f"RTL_MIRRORABLE_ICONS entry '{mirror_icon}' is not in IconRegistry")

    stats = {
        "canonical_registered": len(reg),
        "aliases_count": len(aliases),
        "disk_svg_files": len(all_disk_svgs),
        "categories_count": len(ICON_CATEGORIES),
        "rtl_mirrorable": len(RTL_MIRRORABLE_ICONS)
    }

    return stats, errors


def generate_qrc(icons_dir: Path, output_qrc: Path):
    """Generates an icons.qrc resource file for Qt resource bundling."""
    svg_files = sorted(icons_dir.rglob("*.svg"))
    lines = [
        '<RCC>',
        '    <qresource prefix="/icons">'
    ]
    for svg_file in svg_files:
        rel_to_icons = svg_file.relative_to(icons_dir).as_posix()
        rel_to_qrc = os.path.relpath(svg_file, output_qrc.parent).replace(os.sep, '/')
        lines.append(f'        <file alias="{rel_to_icons}">{rel_to_qrc}</file>')
    lines.append('    </qresource>')
    lines.append('</RCC>')
    lines.append('')

    output_qrc.parent.mkdir(parents=True, exist_ok=True)
    output_qrc.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description="SINAX Icon System Builder & Validator")
    parser.add_argument("--check", action="store_true", help="Validate SVG XML syntax and registry consistency")
    parser.add_argument("--qrc", action="store_true", help="Generate icons.qrc resource file")
    args = parser.parse_args()

    # Default to both if neither specified
    run_all = not args.check and not args.qrc
    do_check = args.check or run_all
    do_qrc = args.qrc or run_all

    icons_dir = PROJECT_ROOT / "resources" / "icons"
    output_qrc = PROJECT_ROOT / "app" / "resources" / "icons.qrc"

    print("=" * 60)
    print("SINAX ICON SYSTEM BUILDER & VALIDATOR")
    print(f"Icons directory: {icons_dir}")
    print("=" * 60)

    exit_code = 0

    if do_check:
        print("\n[1/2] Validating SVG Files...")
        svg_count, svg_errors = validate_svg_files(icons_dir)
        print(f"Scanned {svg_count} SVG files.")
        if svg_errors:
            print(f"FAILED: {len(svg_errors)} SVG error(s):")
            for err in svg_errors:
                print(f"  - {err}")
            exit_code = 1
        else:
            print("OK: All SVG files are valid XML and standard 24x24 viewBox.")

        print("\n[2/2] Auditing Icon Registry Consistency...")
        stats, reg_errors = validate_registry(icons_dir)
        print(f"Canonical icons: {stats['canonical_registered']}")
        print(f"Aliases defined: {stats['aliases_count']}")
        print(f"Disk SVG count:  {stats['disk_svg_files']}")
        print(f"Categories:      {stats['categories_count']}")
        print(f"RTL Mirrorable:  {stats['rtl_mirrorable']}")

        if reg_errors:
            print(f"FAILED: {len(reg_errors)} registry error(s):")
            for err in reg_errors:
                print(f"  - {err}")
            exit_code = 1
        else:
            print("OK: Icon registry matches disk assets perfectly (0 errors).")

    if do_qrc and exit_code == 0:
        print(f"\nGenerating Qt Resource file: {output_qrc}")
        generate_qrc(icons_dir, output_qrc)
        print(f"OK: Successfully generated {output_qrc} with {len(list(icons_dir.rglob('*.svg')))} entries.")

    print("=" * 60)
    if exit_code == 0:
        print("ALL ICON CHECKS PASSED.")
    else:
        print("SOME CHECKS FAILED.")
    print("=" * 60)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Bump LeMinhTTS version across all project files in a single step.

Usage:
    python scripts/bump_version.py <new_version>

Example:
    python scripts/bump_version.py 1.1.0
    python scripts/bump_version.py 2.0.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def bump_version(new_version: str) -> None:
    # Validate semver format
    clean_ver = new_version.strip().lstrip("vV")
    parts = clean_ver.split(".")
    if len(parts) < 2 or not parts[0].isdigit():
        print(f"Error: Invalid version format '{new_version}'. Expected format like 1.0.0 or 1.1")
        sys.exit(1)

    major = parts[0]
    display_title = f"LeMinhTTS V{major}"
    setup_name = f"LeMinhTTS_V{major}_Setup"
    exe_name = f"LeMinhTTS V{major}.exe"

    print(f"Bumping version to: {clean_ver} (Display: {display_title})")

    # 1. Update src/vienetts_app/__init__.py
    init_path = ROOT / "src" / "vienetts_app" / "__init__.py"
    if init_path.exists():
        content = init_path.read_text(encoding="utf-8")
        updated = re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{clean_ver}"', content)
        init_path.write_text(updated, encoding="utf-8")
        print(f"  ✓ Updated {init_path.relative_to(ROOT)}")

    # 2. Update pyproject.toml
    pyproject_path = ROOT / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        updated = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{clean_ver}"', content, count=1)
        pyproject_path.write_text(updated, encoding="utf-8")
        print(f"  ✓ Updated {pyproject_path.relative_to(ROOT)}")

    # 3. Update packaging/installer.iss
    iss_path = ROOT / "packaging" / "installer.iss"
    if iss_path.exists():
        content = iss_path.read_text(encoding="utf-8")
        content = re.sub(r'#define MyAppName "[^"]+"', f'#define MyAppName "{display_title}"', content)
        content = re.sub(r'#define MyAppVersion "[^"]+"', f'#define MyAppVersion "{clean_ver}"', content)
        content = re.sub(r'#define MyAppExeName "[^"]+"', f'#define MyAppExeName "{exe_name}"', content)
        content = re.sub(r'OutputBaseFilename=\S+', f'OutputBaseFilename={setup_name}', content)
        source_repl = f'Source: "..\\\\dist\\\\{display_title}\\\\*"'
        content = re.sub(r'Source:\s*"\.\.\\dist\\[^\\]+\\\*"', lambda m: f'Source: "..\\dist\\{display_title}\\*"', content)
        iss_path.write_text(content, encoding="utf-8")
        print(f"  ✓ Updated {iss_path.relative_to(ROOT)}")

    print(f"\nSuccessfully bumped version to {clean_ver}!")
    print("Files configured: QML and PyInstaller will automatically adapt at runtime/build.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/bump_version.py <new_version>")
        print("Example: python scripts/bump_version.py 1.1.0")
        sys.exit(1)
    bump_version(sys.argv[1])

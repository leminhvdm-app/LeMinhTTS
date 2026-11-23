#!/usr/bin/env python3
"""One-Click Build and Release Automation for LeMinhTTS.

This script:
1. Bumps project version across all config files.
2. Builds the executable with PyInstaller.
3. Compiles the installer with Inno Setup.
4. Commits and pushes changes to GitHub.
5. Pushes git release tags (vX.X.X and VX).
6. Opens the GitHub Release page and the dist/ folder for instant drag-and-drop.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_iscc() -> str | None:
    """Find Inno Setup compiler executable."""
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        shutil.which("iscc") or "",
        shutil.which("ISCC.exe") or "",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return str(c)
    return None


def run_cmd(cmd: list[str] | str, check: bool = True, shell: bool = False) -> None:
    """Execute a system command with real-time output."""
    if isinstance(cmd, list):
        print(f"\n[RUN] {' '.join(cmd)}")
    else:
        print(f"\n[RUN] {cmd}")
    res = subprocess.run(cmd, check=check, shell=shell, cwd=str(ROOT))
    if res.returncode != 0 and check:
        print(f"\n❌ Lệnh thất bại với mã lỗi: {res.returncode}")
        sys.exit(res.returncode)


def main() -> None:
    print("=" * 60)
    print("🚀 LE MINH TTS — CÔNG CỤ TỰ ĐỘNG PHÁT HÀNH BẢN MỚI (1-CLICK)")
    print("=" * 60)

    # 1. Nhận số phiên bản
    if len(sys.argv) > 1:
        new_version = sys.argv[1].strip()
    else:
        # Đọc phiên bản hiện tại
        init_file = ROOT / "src" / "vienetts_app" / "__init__.py"
        cur_ver = "2.0.0"
        if init_file.exists():
            m = re.search(r'__version__\s*=\s*"([^"]+)"', init_file.read_text(encoding="utf-8"))
            if m:
                cur_ver = m.group(1)

        print(f"\n📌 Phiên bản hiện tại: {cur_ver}")
        try:
            val = input("Nhập phiên bản mới cần phát hành (ví dụ: 2.0.1 hoặc 2.1.0) [Enter để hủy]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nĐã hủy.")
            return

        if not val:
            print("Đã hủy.")
            return
        new_version = val

    clean_ver = new_version.strip().lstrip("vV")
    parts = clean_ver.split(".")
    if parts and parts[0].isdigit():
        if len(parts) == 1:
            clean_ver = f"{parts[0]}.0.0"
        elif len(parts) == 2:
            clean_ver = f"{parts[0]}.{parts[1]}.0"

    major = clean_ver.split(".")[0]
    display_title = f"LeMinhTTS V{major}"
    setup_name = f"LeMinhTTS_V{major}_Setup.exe"

    print(f"\n🎯 Chuẩn bị phát hành: Phiên bản {clean_ver} ({display_title})")
    print("-" * 60)

    # 2. Cập nhật số phiên bản
    print("\n[1/5] 📝 Đang cập nhật số phiên bản...")
    bump_script = ROOT / "scripts" / "bump_version.py"
    python_exe = sys.executable
    run_cmd([python_exe, str(bump_script), clean_ver])

    # 3. Đóng gói PyInstaller
    print("\n[2/5] 📦 Đang đóng gói ứng dụng bằng PyInstaller...")
    spec_path = ROOT / "packaging" / "vienetts-app.spec"
    run_cmd([python_exe, "-m", "PyInstaller", str(spec_path), "--noconfirm", "--distpath", "dist"])

    # 4. Biên dịch Inno Setup
    print("\n[3/5] 🔨 Đang biên dịch bộ cài đặt Inno Setup...")
    iscc_path = find_iscc()
    if not iscc_path:
        print("⚠️ Cảnh báo: Không tìm thấy Inno Setup 6 (ISCC.exe). Bỏ qua bước đóng gói Installer.")
    else:
        iss_path = ROOT / "packaging" / "installer.iss"
        run_cmd([iscc_path, str(iss_path)])

    # 5. Git Commit & Push
    print("\n[4/5] ☁️ Đang commit và đẩy mã nguồn lên GitHub...")
    run_cmd(["git", "add", "-A"])
    # Commit nếu có thay đổi
    try:
        subprocess.run(["git", "commit", "-m", f"feat: release {display_title} ({clean_ver})"], cwd=str(ROOT), check=False)
    except Exception:
        pass
    run_cmd(["git", "push", "origin", "main"])

    # 6. Git Tag & Push Tag
    tag_name = f"v{clean_ver}"
    print(f"\n[5/5] 🏷️ Đang tạo và đẩy Tag '{tag_name}' lên GitHub...")
    subprocess.run(["git", "tag", "-d", tag_name], cwd=str(ROOT), capture_output=True)
    subprocess.run(["git", "push", "origin", f":refs/tags/{tag_name}"], cwd=str(ROOT), capture_output=True)
    run_cmd(["git", "tag", "-a", tag_name, "-m", f"Release {display_title}"])
    run_cmd(["git", "push", "origin", tag_name])

    # Tag V{major}
    major_tag = f"V{major}"
    subprocess.run(["git", "tag", "-d", major_tag], cwd=str(ROOT), capture_output=True)
    subprocess.run(["git", "push", "origin", f":refs/tags/{major_tag}"], cwd=str(ROOT), capture_output=True)
    run_cmd(["git", "tag", "-a", major_tag, "-m", f"Release {display_title}"])
    run_cmd(["git", "push", "origin", major_tag])

    # 7. Mở trang tạo Release trên GitHub và mở thư mục dist
    print("\n" + "=" * 60)
    print("🎉 HOÀN THÀNH TẤT CẢ CÁC BƯỚC TỰ ĐỘNG!")
    print("=" * 60)
    setup_file = ROOT / "dist" / setup_name
    if setup_file.exists():
        size_mb = setup_file.stat().st_size / (1024 * 1024)
        print(f"\n📁 File bộ cài đặt đã tạo thành công: {setup_file.name} ({size_mb:.1f} MB)")
    
    release_url = f"https://github.com/leminhvdm-app/LeMinhTTS/releases/new?tag={tag_name}&title={display_title}"
    print(f"\n🌐 Đang mở trang phát hành GitHub Release trên trình duyệt: {release_url}")
    print("👉 Bạn chỉ cần KÉO THẢ file trong thư mục 'dist' vào ô Attach Binaries và bấm 'Publish Release' là xong!")

    try:
        webbrowser.open(release_url)
    except Exception:
        pass

    try:
        # Mở thư mục dist trong Windows Explorer
        os.startfile(str(ROOT / "dist"))
    except Exception:
        pass


if __name__ == "__main__":
    main()

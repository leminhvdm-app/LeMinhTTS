"""Auto-Update Controller for LeMinhTTS via GitHub Releases API."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, QSettings, Signal, Slot

from vienetts_app import __version__

logger = logging.getLogger(__name__)

DEFAULT_REPO = "leminhvdm-app/LeMinhTTS"


def parse_version_tuple(ver_str: str) -> tuple[int, ...]:
    """Parse version string into a numeric tuple for comparison."""
    clean = ver_str.strip().lstrip("vV")
    numbers = re.findall(r"\d+", clean)
    return tuple(map(int, numbers)) if numbers else (0,)


class UpdateController(QObject):
    """QML controller for checking and installing updates from GitHub Releases."""

    statusChanged = Signal()
    isCheckingChanged = Signal()
    isDownloadingChanged = Signal()
    downloadProgressChanged = Signal()
    isUpdateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    releaseNotesChanged = Signal()
    releaseUrlChanged = Signal()
    githubRepoChanged = Signal()

    def __init__(self, parent: QObject | None = None, settings: QSettings | None = None) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings("LeMinhTTS", "Updater")
        self._github_repo: str = str(self._settings.value("github_repo", DEFAULT_REPO)).strip()
        if not self._github_repo:
            self._github_repo = DEFAULT_REPO

        self._status_message: str = ""
        self._is_checking: bool = False
        self._is_downloading: bool = False
        self._download_progress: int = 0
        self._is_update_available: bool = False
        self._latest_version: str = __version__
        self._release_notes: str = ""
        self._release_url: str = f"https://github.com/{self._github_repo}/releases"
        self._download_asset_url: str = ""
        self._download_asset_name: str = ""

    # --- Properties exposed to QML ---

    @Property(str, notify=statusChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(bool, notify=isCheckingChanged)
    def isChecking(self) -> bool:
        return self._is_checking

    @Property(bool, notify=isDownloadingChanged)
    def isDownloading(self) -> bool:
        return self._is_downloading

    @Property(int, notify=downloadProgressChanged)
    def downloadProgress(self) -> int:
        return self._download_progress

    @Property(bool, notify=isUpdateAvailableChanged)
    def isUpdateAvailable(self) -> bool:
        return self._is_update_available

    @Property(str, constant=True)
    def currentVersion(self) -> str:
        major = __version__.split(".")[0] if "." in __version__ else __version__
        return major

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(str, notify=releaseNotesChanged)
    def releaseNotes(self) -> str:
        return self._release_notes

    @Property(str, notify=releaseUrlChanged)
    def releaseUrl(self) -> str:
        return self._release_url

    @Property(str, notify=githubRepoChanged)
    def githubRepo(self) -> str:
        return self._github_repo

    # --- Slots ---

    @Slot(str)
    def setGithubRepo(self, repo: str) -> None:
        repo = repo.strip().replace("https://github.com/", "")
        if repo and repo != self._github_repo:
            self._github_repo = repo
            self._settings.setValue("github_repo", repo)
            self._release_url = f"https://github.com/{self._github_repo}/releases"
            self.githubRepoChanged.emit()
            self.releaseUrlChanged.emit()

    @Slot(bool)
    def checkForUpdates(self, silent: bool = False) -> None:
        """Check GitHub Releases API asynchronously for newer version."""
        if self._is_checking or self._is_downloading:
            return

        self._is_checking = True
        self.isCheckingChanged.emit()
        self._status_message = "Đang kiểm tra bản cập nhật mới..."
        self.statusChanged.emit()

        thread = threading.Thread(
            target=self._worker_check_update,
            args=(silent,),
            daemon=True,
        )
        thread.start()

    def _worker_check_update(self, silent: bool) -> None:
        api_url = f"https://api.github.com/repos/{self._github_repo}/releases/latest"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "LeMinhTTS-App-Updater",
        }

        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            remote_ver_str = tag_name.lstrip("vV")
            current_tuple = parse_version_tuple(__version__)
            remote_tuple = parse_version_tuple(remote_ver_str)

            self._latest_version = remote_ver_str
            self._release_notes = data.get("body", "Không có thông tin mô tả chi tiết.")
            self._release_url = data.get("html_url", f"https://github.com/{self._github_repo}/releases")

            # Look for setup/installer asset
            assets: list[dict[str, Any]] = data.get("assets", [])
            setup_asset = None
            for asset in assets:
                name = asset.get("name", "")
                if name.lower().endswith(".exe") and ("setup" in name.lower() or "leminhtts" in name.lower()):
                    setup_asset = asset
                    break
            if not setup_asset and assets:
                for asset in assets:
                    if asset.get("name", "").lower().endswith(".exe"):
                        setup_asset = asset
                        break

            if setup_asset:
                self._download_asset_url = setup_asset.get("browser_download_url", "")
                self._download_asset_name = setup_asset.get("name", "LeMinhTTS_Setup.exe")
            else:
                self._download_asset_url = ""
                self._download_asset_name = ""

            major = __version__.split(".")[0] if "." in __version__ else __version__
            if remote_tuple > current_tuple:
                self._is_update_available = True
                self._status_message = f"Đã có phiên bản mới: V{remote_ver_str}"
            else:
                self._is_update_available = False
                self._status_message = f"Bạn đang sử dụng phiên bản mới nhất (V{major})"

        except urllib.error.HTTPError as e:
            major = __version__.split(".")[0] if "." in __version__ else __version__
            if e.code == 404:
                self._is_update_available = False
                self._status_message = f"Bạn đang sử dụng phiên bản mới nhất (V{major})"
            else:
                self._status_message = f"Lỗi máy chủ cập nhật ({e.code})"
            logger.warning("GitHub update check HTTP error: %s", e)
        except Exception as e:
            self._is_update_available = False
            self._status_message = "Không thể kiểm tra (vui lòng kiểm tra kết nối mạng)"
            logger.warning("GitHub update check error: %s", e)
        finally:
            self._is_checking = False
            self.isCheckingChanged.emit()
            self.isUpdateAvailableChanged.emit()
            self.latestVersionChanged.emit()
            self.releaseNotesChanged.emit()
            self.releaseUrlChanged.emit()
            self.statusChanged.emit()

    @Slot()
    def startUpdate(self) -> None:
        """Download latest release installer and launch it, then quit app."""
        if not self._download_asset_url:
            # Fallback to browser if direct exe is not in release assets
            self.openReleasePage()
            return

        if self._is_downloading:
            return

        self._is_downloading = True
        self._download_progress = 0
        self.isDownloadingChanged.emit()
        self.downloadProgressChanged.emit()
        self._status_message = "Đang tải xuống bộ cài mới..."
        self.statusChanged.emit()

        thread = threading.Thread(target=self._worker_download_and_run, daemon=True)
        thread.start()

    def _worker_download_and_run(self) -> None:
        target_dir = Path(tempfile.gettempdir()) / "LeMinhTTS_Update"
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = self._download_asset_name or "LeMinhTTS_Setup.exe"
        installer_path = target_dir / filename

        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": "LeMinhTTS-App-Updater",
        }

        try:
            req = urllib.request.Request(self._download_asset_url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 128 * 1024  # 128 KB chunks

                with open(installer_path, "wb") as out_file:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            if pct != self._download_progress:
                                self._download_progress = pct
                                self.downloadProgressChanged.emit()

            self._download_progress = 100
            self.downloadProgressChanged.emit()
            self._status_message = "Đang khởi chạy bộ cài đặt..."
            self.statusChanged.emit()

            # Launch installer detached
            # On Windows, Inno Setup handles elevation and closes old version if running
            if os.name == "nt":
                subprocess.Popen([str(installer_path)], shell=True)
            else:
                subprocess.Popen([str(installer_path)])

            # Exit current app cleanly after a short pause so installer takes over
            QCoreApplication.quit()

        except Exception as e:
            logger.error("Download update failed: %s", e)
            self._status_message = f"Tải bản cập nhật thất bại: {e}"
            self.statusChanged.emit()
            self._is_downloading = False
            self.isDownloadingChanged.emit()

    @Slot()
    def openReleasePage(self) -> None:
        """Open GitHub Releases page in external default browser."""
        url = self._release_url or f"https://github.com/{self._github_repo}/releases"
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.warning("Failed to open browser: %s", e)

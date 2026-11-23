"""Machine Key (HWID) & Firebase License Verification System for LeMinhTTS."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)

# Default Firebase Realtime Database URL (user can change in Settings or Admin App)
DEFAULT_FIREBASE_URL = "https://leminhtts-license-default-rtdb.asia-southeast1.firebasedatabase.app"
GRACE_PERIOD_SECONDS = 3 * 24 * 3600  # 3 days offline grace period


def get_machine_raw_hwid() -> str:
    """Retrieve unique hardware identifier from Windows motherboard or fallback."""
    if os.name == "nt":
        try:
            # Query motherboard UUID from WMI via CIM
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            val = res.stdout.strip()
            if val and len(val) >= 16 and "UUID" not in val:
                return val
        except Exception:
            pass

        try:
            # Fallback to WMIC
            res = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            if len(lines) > 1 and len(lines[1]) >= 16:
                return lines[1]
        except Exception:
            pass

    # Generic fallback: node name + MAC address
    return f"{platform.node()}-{uuid.getnode()}"


def generate_machine_key() -> str:
    """Generate a clean, standardized 16-character Machine Key (e.g. LMTTS-XXXX-XXXX-XXXX)."""
    raw = get_machine_raw_hwid()
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    return f"LMTTS-{h[0:4]}-{h[4:8]}-{h[8:12]}"


class LicenseController(QObject):
    """QML controller for checking and managing machine activation status via Firebase."""

    statusChanged = Signal()
    isCheckingChanged = Signal()
    isLicensedChanged = Signal()
    licenseStatusChanged = Signal()
    firebaseUrlChanged = Signal()

    def __init__(self, parent: QObject | None = None, settings: QSettings | None = None) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings("LeMinhTTS", "Licensing")
        self._machine_key: str = generate_machine_key()
        self._firebase_url: str = str(
            self._settings.value("firebase_url", DEFAULT_FIREBASE_URL)
        ).strip().rstrip("/")
        if not self._firebase_url:
            self._firebase_url = DEFAULT_FIREBASE_URL

        self._is_checking: bool = False
        self._is_licensed: bool = True  # Default to active until verified or blocked
        self._license_status: str = "active"  # "active" | "pending" | "blocked" | "expired"
        self._status_message: str = "Đang xác thực bản quyền..."
        self._customer_name: str = ""
        self._cache_file = Path(os.environ.get("LOCALAPPDATA", tempfile_fallback())) / "LeMinhTTS" / ".lic_cache"

        # Load local cache first for instant startup
        self._load_local_cache()

    # --- Properties ---

    @Property(str, constant=True)
    def machineKey(self) -> str:
        return self._machine_key

    @Property(bool, notify=isLicensedChanged)
    def isLicensed(self) -> bool:
        return self._is_licensed

    @Property(str, notify=licenseStatusChanged)
    def licenseStatus(self) -> str:
        return self._license_status

    @Property(str, notify=statusChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=statusChanged)
    def customerName(self) -> str:
        return self._customer_name

    @Property(bool, notify=isCheckingChanged)
    def isChecking(self) -> bool:
        return self._is_checking

    @Property(str, notify=firebaseUrlChanged)
    def firebaseUrl(self) -> str:
        return self._firebase_url

    # --- Slots ---

    @Slot(str)
    def setFirebaseUrl(self, url: str) -> None:
        clean = url.strip().rstrip("/")
        if clean and clean != self._firebase_url:
            self._firebase_url = clean
            self._settings.setValue("firebase_url", clean)
            self.firebaseUrlChanged.emit()
            self.verifyLicense()

    @Slot()
    def copyMachineKey(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._machine_key)

    @Slot()
    def verifyLicense(self) -> None:
        """Asynchronously query Firebase Realtime Database for this machine key."""
        if self._is_checking:
            return

        self._is_checking = True
        self.isCheckingChanged.emit()
        self._status_message = "Đang kiểm tra trạng thái từ máy chủ..."
        self.statusChanged.emit()

        thread = threading.Thread(target=self._worker_verify, daemon=True)
        thread.start()

    def _worker_verify(self) -> None:
        url = f"{self._firebase_url}/devices/{self._machine_key}.json"
        now = int(time.time())

        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "LeMinhTTS-Licensing"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data_raw = resp.read().decode("utf-8")
                data = json.loads(data_raw) if data_raw != "null" else None

            if data is None:
                # Device not registered yet -> auto-register as pending for admin approval
                self._register_new_device(url, now)
                self._license_status = "pending"
                self._is_licensed = False
                self._status_message = "Máy đang chờ quản trị viên kích hoạt trên điện thoại."
            else:
                status = str(data.get("status", "active")).lower()
                self._customer_name = str(data.get("customer_name", ""))
                expires_at = int(data.get("expires_at", 0))

                if status == "blocked":
                    self._license_status = "blocked"
                    self._is_licensed = False
                    self._status_message = "Thiết bị này đã bị khóa bởi quản trị viên."
                elif status == "pending":
                    self._license_status = "pending"
                    self._is_licensed = False
                    self._status_message = "Mã máy đang chờ duyệt. Vui lòng liên hệ Admin để mở app."
                elif expires_at > 0 and now > expires_at:
                    self._license_status = "expired"
                    self._is_licensed = False
                    self._status_message = "Bản quyền ứng dụng trên máy này đã hết hạn."
                else:
                    self._license_status = "active"
                    self._is_licensed = True
                    self._status_message = "Bản quyền hợp lệ (Đã kích hoạt)."
                    self._save_local_cache(now)

                # Ping last_seen in background
                self._ping_last_seen(url, now)

        except urllib.error.URLError as e:
            logger.warning("License check network error: %s", e)
            # Evaluate offline grace period
            if self._has_valid_offline_grace(now):
                self._license_status = "active"
                self._is_licensed = True
                self._status_message = "Đang chạy chế độ ngoại tuyến (Hợp lệ)."
            else:
                self._license_status = "offline_expired"
                self._is_licensed = False
                self._status_message = "Cần kết nối mạng để xác thực lại bản quyền ứng dụng."
        except Exception as e:
            logger.error("License check error: %s", e)
            self._status_message = f"Lỗi xác thực: {e}"
        finally:
            self._is_checking = False
            self.isCheckingChanged.emit()
            self.isLicensedChanged.emit()
            self.licenseStatusChanged.emit()
            self.statusChanged.emit()

    def _register_new_device(self, url: str, now: int) -> None:
        """Register unknown device in Firebase so it shows up on the mobile app."""
        payload = {
            "machine_key": self._machine_key,
            "device_name": platform.node(),
            "os": platform.platform(),
            "status": "pending",
            "customer_name": "Máy mới",
            "note": "Tự động đăng ký khi khởi động",
            "created_at": now,
            "last_seen": now,
            "expires_at": 0,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="PUT",
            )
            with urllib.request.urlopen(req, timeout=6):
                pass
        except Exception as e:
            logger.warning("Failed to auto-register device in Firebase: %s", e)

    def _ping_last_seen(self, url: str, now: int) -> None:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"last_seen": now}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="PATCH",
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass

    def _save_local_cache(self, now: int) -> None:
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            token = f"{self._machine_key}:{now}:ACTIVE"
            sig = hashlib.sha256(token.encode("utf-8")).hexdigest()
            data = {"key": self._machine_key, "time": now, "sig": sig}
            self._cache_file.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _load_local_cache(self) -> None:
        if not self._cache_file.exists():
            return
        try:
            content = json.loads(self._cache_file.read_text(encoding="utf-8"))
            if content.get("key") == self._machine_key:
                ts = int(content.get("time", 0))
                token = f"{self._machine_key}:{ts}:ACTIVE"
                expected_sig = hashlib.sha256(token.encode("utf-8")).hexdigest()
                if content.get("sig") == expected_sig and (time.time() - ts) < GRACE_PERIOD_SECONDS:
                    self._is_licensed = True
                    self._license_status = "active"
                    self._status_message = "Bản quyền hợp lệ (Đã lưu cache)."
        except Exception:
            pass

    def _has_valid_offline_grace(self, now: int) -> bool:
        if not self._cache_file.exists():
            return False
        try:
            content = json.loads(self._cache_file.read_text(encoding="utf-8"))
            if content.get("key") == self._machine_key:
                ts = int(content.get("time", 0))
                return (now - ts) < GRACE_PERIOD_SECONDS
        except Exception:
            pass
        return False


def tempfile_fallback() -> str:
    import tempfile
    return tempfile.gettempdir()

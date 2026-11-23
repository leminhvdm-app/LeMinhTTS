"""Launch VieNeuTTS GUI cleanly on the user's interactive desktop."""

from __future__ import annotations

import ctypes
import subprocess
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = ROOT / ".venv" / "Scripts" / "pythonw.exe"


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_char_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


def launch() -> int | None:
    exe = str(VENV_PYTHONW if VENV_PYTHONW.is_file() else VENV_PYTHON)
    cmd = f'"{exe}" -m vienetts_app'
    cwd = str(ROOT)

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    si.lpDesktop = "WinSta0\\Default"
    pi = PROCESS_INFORMATION()

    # DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200)
    flags = 0x00000008 | 0x00000200

    success = ctypes.windll.kernel32.CreateProcessW(
        None,
        cmd,
        None,
        None,
        False,
        flags,
        None,
        cwd,
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not success:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"Direct CreateProcess failed (error {err}), falling back to subprocess...")
        p = subprocess.Popen([exe, "-m", "vienetts_app"], cwd=cwd)
        print(f"Launched PID {p.pid} via subprocess.")
        return p.pid

    pid = pi.dwProcessId
    print(f"Successfully launched VieNeuTTS (PID {pid}) on interactive desktop WinSta0\\Default.")
    ctypes.windll.kernel32.CloseHandle(pi.hProcess)
    ctypes.windll.kernel32.CloseHandle(pi.hThread)
    return pid


if __name__ == "__main__":
    launch()

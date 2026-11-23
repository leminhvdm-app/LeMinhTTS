"""Daemon launcher for VieNeuTTS GUI on the interactive desktop."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


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


def main() -> int:
    exe = str(VENV_PYTHON)
    cmd = f'"{exe}" -m vienetts_app'
    cwd = str(ROOT)

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    si.lpDesktop = "WinSta0\\Default"
    pi = PROCESS_INFORMATION()

    print(f"Launching VieNeuTTS from {cwd}...")
    success = ctypes.windll.kernel32.CreateProcessW(
        None,
        cmd,
        None,
        None,
        False,
        0,
        None,
        cwd,
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not success:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"CreateProcess failed with error {err}", file=sys.stderr)
        return 1

    print(f"VieNeuTTS started successfully (PID {pi.dwProcessId}) on WinSta0\\Default.")
    ctypes.windll.kernel32.CloseHandle(pi.hThread)
    # Wait until user closes the application window
    ctypes.windll.kernel32.WaitForSingleObject(pi.hProcess, 0xFFFFFFFF)
    ctypes.windll.kernel32.CloseHandle(pi.hProcess)
    print("VieNeuTTS window closed by user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

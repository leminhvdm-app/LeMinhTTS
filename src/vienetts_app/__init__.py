"""LeMinhTTS desktop app — on-device Vietnamese/English TTS powered by VieNeu-TTS v3 Turbo."""

from __future__ import annotations

import contextlib
import os
import sys

__version__ = "3.0.0"


def setup_crash_protection() -> None:
    """Configure low-level fault handling, OpenMP safety, and thread exception hooks."""
    # 1. Prevent OpenMP / MKL duplicate library abort crash on Windows
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    # 2. Limit CPU thread contention across OpenMP / BLAS / NumExpr
    cpu_count = os.cpu_count() or 1
    cpu_threads = str(max(1, min(4, cpu_count)))
    os.environ.setdefault("OMP_NUM_THREADS", cpu_threads)
    os.environ.setdefault("MKL_NUM_THREADS", cpu_threads)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", cpu_threads)
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", cpu_threads)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", cpu_threads)

    # 3. Prefer local cached models to prevent DNS/network retry stalls when offline
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    # 4. Silence Qt multimedia / QPA debug messages on Windows
    os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false;qt.qpa.*=false;*.debug=false")

    # 5. Suppress third-party future/deprecation warnings (e.g. google.generativeai)
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", module="google")

    # 6. Enable C/C++ faulthandler to dump native traces on segfaults / access violations
    with contextlib.suppress(Exception):
        import faulthandler

        faulthandler.enable(all_threads=True)

    # 4. Install global Python unhandled exception hooks
    import threading
    import traceback
    from datetime import datetime

    def _log_unhandled_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
        thread_name: str = "MainThread",
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log_entry = f"\n[{timestamp}] [CRASH IN {thread_name}]\n{err_msg}\n"
        with contextlib.suppress(Exception):
            if sys.stderr is not None:
                sys.stderr.write(log_entry)
                sys.stderr.flush()
        # Also write to persistent crash.log
        with contextlib.suppress(Exception):
            with open("crash.log", "a", encoding="utf-8", errors="replace") as f:
                f.write(log_entry)

    def _sys_excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        _log_unhandled_exception(exc_type, exc_value, exc_traceback, "MainThread")

    def _threading_excepthook(args: Any) -> None:
        _log_unhandled_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            args.thread.name if args.thread else "Thread",
        )

    sys.excepthook = _sys_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _threading_excepthook


def ensure_windowed_stdio() -> None:
    """Replace ``None`` stdio with devnull (windowed-exe safety net) and initialize crash guards.

    PyInstaller ``console=False`` (and ``pythonw.exe``) starts the process
    with ``sys.stdout``/``sys.stderr`` set to ``None``. Any library that
    writes progress to the console — tqdm (used by ``huggingface_hub`` for
    weight downloads), ``print()``, ``traceback`` — then dies with
    ``AttributeError: 'NoneType' object has no attribute 'write'``, which
    the engine seam surfaces as ``Engine initialization failed: ...`` on
    first synthesis. Redirecting to devnull keeps the windowed process
    silent instead of crashing; a no-op when stdio already exists.
    """
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")  # noqa: PTH123,SIM115 — kept open as stdio
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")  # noqa: PTH123,SIM115 — kept open as stdio
    if sys.stdin is None:
        with contextlib.suppress(OSError):
            sys.stdin = open(os.devnull)  # noqa: PTH123,SIM115 — read-only guard
    setup_crash_protection()

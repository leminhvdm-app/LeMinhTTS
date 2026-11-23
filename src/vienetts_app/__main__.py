"""Dual entry: ``python -m vienetts_app`` (no args) opens the GUI shell
(FR-2.1); ``--smoke TEXT`` keeps the Phase 1 headless CLI — synthesis
end-to-end through the threaded worker, exit 0 only on a valid WAV (AC-4).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import site
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Ensure 'src' is in sys.path if invoked directly via script path
_app_root = Path(__file__).resolve().parent.parent.parent
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# If run directly outside the virtualenv, automatically link project .venv site-packages
try:
    import PySide6  # noqa: F401
except ImportError:
    for candidate in [
        _app_root / ".venv" / "Lib" / "site-packages",
        *_app_root.glob(".venv/lib/python*/site-packages"),
    ]:
        if candidate.is_dir():
            site.addsitedir(str(candidate))
            if sys.platform == "win32":
                pyside_dir = candidate / "PySide6"
                shiboken_dir = candidate / "shiboken6"
                if pyside_dir.is_dir():
                    if hasattr(os, "add_dll_directory"):
                        with contextlib.suppress(Exception):
                            os.add_dll_directory(str(pyside_dir))
                    os.environ["PATH"] = f"{pyside_dir};{os.environ.get('PATH', '')}"
                if shiboken_dir.is_dir():
                    if hasattr(os, "add_dll_directory"):
                        with contextlib.suppress(Exception):
                            os.add_dll_directory(str(shiboken_dir))
                    os.environ["PATH"] = f"{shiboken_dir};{os.environ.get('PATH', '')}"
            break

SMOKE_TIMEOUT_SECONDS = 600.0  # cold start + long text budget


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vienetts-app", description="LeMinhTTS desktop app (GUI) + headless smoke CLI"
    )
    parser.add_argument(
        "--smoke",
        metavar="TEXT",
        help="synthesize TEXT end-to-end and exit (omit to open the GUI)",
    )
    parser.add_argument("--voice", default="Adam", help="preset voice id (default: Adam)")
    parser.add_argument("--stream", action="store_true", help="use the streaming path")
    parser.add_argument("-o", "--output", default="out.wav", help="output WAV path")
    parser.add_argument(
        "--software-render",
        action="store_true",
        help="force software rasterizer rendering (useful on low-spec/non-GPU machines)",
    )
    return parser


def run_smoke(
    text: str,
    voice: str,
    output: str | Path,
    stream: bool = False,
    engine_factory: Callable[..., Any] | None = None,
    timeout: float = SMOKE_TIMEOUT_SECONDS,
) -> int:
    """Synthesize ``text`` via the worker; return a process exit code."""
    from vienetts_app import ensure_windowed_stdio

    ensure_windowed_stdio()
    # Smoke-only imports (deferred so the GUI path never pays for the
    # engine/worker/numpy import chain before argparse runs).
    from PySide6.QtCore import QCoreApplication

    from vienetts_app.core.artifacts import SynthesisArtifact
    from vienetts_app.core.detector import detect_hardware, detected_engine_info
    from vienetts_app.core.engine import TTSEngine
    from vienetts_app.core.jobs import new_synthesis_job
    from vienetts_app.core.models import TTSRequest
    from vienetts_app.workers.inference_worker import InferenceWorker

    app = QCoreApplication.instance() or QCoreApplication([])

    hw = detect_hardware()
    info = detected_engine_info(hw)
    print(f"engine: {info.note} (backend={info.backend}, precision={info.precision})")

    engine = (engine_factory or (lambda **kw: TTSEngine(**kw)))(
        backend=info.backend, precision=info.precision
    )
    worker = InferenceWorker(engine)
    outcome: dict[str, Any] = {}

    def on_terminal(event: Any) -> None:
        if event.state == "completed" and isinstance(event.value, SynthesisArtifact):
            outcome["artifact"] = event.value
        elif event.state == "completed":
            outcome["error"] = "smoke synthesis produced no artifact"
        elif event.state == "cancelled":
            outcome["error"] = "Cancelled by user"
        else:
            outcome["error"] = str(event.error)

    worker.terminal.connect(on_terminal)
    worker.start()
    try:
        job = new_synthesis_job(
            "text",
            "interactive",
            TTSRequest(text=text, voice=voice, mode="stream" if stream else "infer"),
            artifact_path=Path(output),
        )
        worker.submit(job)
        deadline = time.monotonic() + timeout
        while "artifact" not in outcome and "error" not in outcome:
            if time.monotonic() > deadline:
                print("error: smoke run timed out", file=sys.stderr)
                return 1
            app.processEvents()
            time.sleep(0.01)

        if "error" in outcome:
            print(f"error: {outcome['error']}", file=sys.stderr)
            return 1

        artifact = outcome["artifact"]
        print(f"output: {artifact.path} ({artifact.duration_ms / 1000:.2f}s)")
        return 0
    finally:
        worker.stop()


def main(
    argv: list[str] | None = None,
    engine_factory: Callable[..., Any] | None = None,
    gui_runner: Callable[[], int] | None = None,
) -> int:
    from vienetts_app import ensure_windowed_stdio

    ensure_windowed_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "software_render", False):
        import os
        os.environ["LEMINHTTS_SOFTWARE_RENDER"] = "1"
        os.environ["QSG_RHI_BACKEND"] = "software"
    if args.smoke is None:
        # FR-2.1: no args → GUI. Injectable so tests never spin a real loop.
        if sys.platform == "win32":
            with contextlib.suppress(Exception):
                from vienetts_app.ui.windows import hide_windows_console

                hide_windows_console()
        if gui_runner is None:
            from vienetts_app.app import run_gui

            gui_runner = run_gui
        return gui_runner()
    if not args.smoke.strip():
        parser.error("--smoke text must not be blank")
    return run_smoke(
        text=args.smoke,
        voice=args.voice,
        output=args.output,
        stream=args.stream,
        engine_factory=engine_factory,
    )


if __name__ == "__main__":
    raise SystemExit(main())

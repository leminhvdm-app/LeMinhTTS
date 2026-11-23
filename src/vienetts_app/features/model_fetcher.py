"""Gemini API model fetcher & catalog manager."""

from __future__ import annotations

import logging
import re
from typing import Sequence

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODELS: list[str] = [
    "gemini-3.5-flash",
    "gemini-3.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash-8b",
]


class ModelFetchWorker(QThread):
    """Background worker to query latest available Gemini models from the API."""

    models_fetched = Signal(list)  # list[str]
    fetch_error = Signal(str)
    progress = Signal(str)

    def __init__(self, api_keys: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.api_keys: list[str] = [
            k.strip() for k in re.split(r"[,;\s]+", api_keys) if k.strip()
        ]

    def run(self) -> None:
        if not self.api_keys:
            self.fetch_error.emit("Vui lòng nhập API Key để lấy danh sách model từ Google Gemini.")
            return

        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import google.generativeai as genai

            last_error = ""
            for key in self.api_keys:
                try:
                    self.progress.emit(
                        f"[+] Đang kết nối API bằng key {key[:8]}... để lấy danh sách model..."
                    )
                    genai.configure(api_key=key, transport="rest")
                    models_iter = genai.list_models()
                    discovered: list[str] = []

                    for m in models_iter:
                        name = getattr(m, "name", "")
                        if name.startswith("models/"):
                            name = name[7:]
                        methods = getattr(m, "supported_generation_methods", [])
                        # Include models supporting content generation
                        if "generateContent" in methods or "gemini" in name.lower():
                            discovered.append(name)

                    if discovered:
                        # Prioritize default models at top, then append newly discovered
                        combined: list[str] = []
                        # Put default models that match or exist
                        for def_m in DEFAULT_GEMINI_MODELS:
                            combined.append(def_m)

                        for disc_m in discovered:
                            if disc_m not in combined:
                                combined.append(disc_m)

                        self.progress.emit(
                            f"[+] Lấy danh sách thành công! Tìm thấy {len(discovered)} model từ Google."
                        )
                        self.models_fetched.emit(combined)
                        return
                except Exception as e:
                    last_error = str(e)
                    self.progress.emit(f"[-] Lỗi với key {key[:8]}...: {last_error}")
                    continue

            self.fetch_error.emit(
                f"Không thể lấy danh sách model từ API. Lỗi cuối cùng: {last_error}"
            )
        except Exception as e:
            self.fetch_error.emit(f"Lỗi khởi tạo: {e}")

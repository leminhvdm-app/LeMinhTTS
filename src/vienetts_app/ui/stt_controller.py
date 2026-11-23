"""STT UI Controller: QML-exposed bridge for Speech-to-Text features."""

from __future__ import annotations

import logging
import os
import re
import tempfile

from PySide6.QtCore import Property, QObject, QSettings, QThread, Signal, Slot

from vienetts_app.features.model_fetcher import DEFAULT_GEMINI_MODELS, ModelFetchWorker
from vienetts_app.features.stt_tab import STTWorker

logger = logging.getLogger(__name__)


def text_to_srt(text: str) -> str:
    """Convert recognized text with or without timestamps into valid SRT subtitle format."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    if "-->" in text:
        return text

    srt_entries: list[str] = []
    range_pattern = re.compile(
        r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]\s*(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[:\-–]?\s*(.*)",
        re.IGNORECASE,
    )
    single_pattern = re.compile(
        r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[:\-–]?\s*(.*)",
        re.IGNORECASE,
    )

    def to_srt_time(t_str: str) -> str:
        parts = t_str.split(":")
        if len(parts) == 2:
            h, m, s = 0, int(parts[0]), int(parts[1])
        elif len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            return "00:00:00,000"
        return f"{h:02d}:{m:02d}:{s:02d},000"

    current_sec = 0
    idx = 1
    for line in lines:
        if line.startswith("--- File:"):
            continue
        m_range = range_pattern.match(line)
        if m_range:
            start_t = to_srt_time(m_range.group(1))
            end_t = to_srt_time(m_range.group(2))
            dialogue = m_range.group(3).strip()
            srt_entries.append(f"{idx}\n{start_t} --> {end_t}\n{dialogue}\n")
            idx += 1
            continue

        m_single = single_pattern.match(line)
        if m_single:
            start_t = to_srt_time(m_single.group(1))
            parts = m_single.group(1).split(":")
            sec = (
                int(parts[0]) * 60 + int(parts[1])
                if len(parts) == 2
                else int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            )
            end_sec = sec + 3
            end_h = end_sec // 3600
            end_m = (end_sec % 3600) // 60
            end_s = end_sec % 60
            end_t = f"{end_h:02d}:{end_m:02d}:{end_s:02d},000"
            dialogue = m_single.group(2).strip()
            srt_entries.append(f"{idx}\n{start_t} --> {end_t}\n{dialogue}\n")
            idx += 1
            continue

        start_h = current_sec // 3600
        start_m = (current_sec % 3600) // 60
        start_s = current_sec % 60
        start_t = f"{start_h:02d}:{start_m:02d}:{start_s:02d},000"
        current_sec += 4
        end_h = current_sec // 3600
        end_m = (current_sec % 3600) // 60
        end_s = current_sec % 60
        end_t = f"{end_h:02d}:{end_m:02d}:{end_s:02d},000"
        srt_entries.append(f"{idx}\n{start_t} --> {end_t}\n{line}\n")
        idx += 1

    return "\n".join(srt_entries)


class STTDownloadWorker(QThread):
    """Background worker for downloading video/audio links using yt-dlp."""

    progress = Signal(str)
    percent = Signal(float)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, urls: list[str], output_dir: str) -> None:
        super().__init__()
        self.urls = urls
        self.output_dir = output_dir
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            from vienetts_app.features.media_tools import download_videos_ytdlp

            os.makedirs(self.output_dir, exist_ok=True)
            before_files = set(os.listdir(self.output_dir))

            self.progress.emit(f"[+] Bắt đầu tải {len(self.urls)} liên kết video/audio...")
            ok, msg = download_videos_ytdlp(
                urls=self.urls,
                output_dir=self.output_dir,
                quality="M4A",
                progress_cb=self.percent.emit,
                log_cb=self.progress.emit,
                cancel_check=lambda: self._is_cancelled,
            )

            after_files = set(os.listdir(self.output_dir))
            new_files = [
                os.path.join(self.output_dir, f)
                for f in (after_files - before_files)
                if os.path.isfile(os.path.join(self.output_dir, f))
            ]

            if ok or new_files:
                self.progress.emit(f"[+] Đã tải về thành công {len(new_files)} tệp!")
                self.finished.emit(new_files)
            else:
                self.error.emit(msg or "Tải video/audio thất bại.")
        except Exception as e:
            self.error.emit(str(e))


class SttController(QObject):
    """QML controller for Speech-to-Text."""

    apiKeysChanged = Signal()
    saveKeyChanged = Signal()
    selectedFilesChanged = Signal()
    modelNameChanged = Signal()
    availableModelsChanged = Signal()
    isFetchingModelsChanged = Signal()
    isProcessingChanged = Signal()
    statusTextChanged = Signal()
    consoleLogsChanged = Signal()
    recognizedTextChanged = Signal()
    hasResultChanged = Signal()
    outputModeChanged = Signal()
    isDownloadingChanged = Signal()
    videoUrlsChanged = Signal()
    downloadPercentChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("VieNeu", "OCRTab")
        self._save_key: bool = self._settings.value("save_key_v2", False, type=bool)
        self._api_keys: str = self._settings.value("api_key_v2", "") if self._save_key else ""
        self._selected_files: list[str] = []

        saved_models = self._settings.value("cached_models_v2", None)
        models = list(DEFAULT_GEMINI_MODELS)
        if isinstance(saved_models, list) and saved_models:
            for m in saved_models:
                if isinstance(m, str) and m not in models:
                    models.append(m)
        self._available_models: list[str] = models

        saved_selected_model = self._settings.value("selected_model_v2", "gemini-3.5-flash")
        if saved_selected_model in self._available_models:
            self._model_name: str = str(saved_selected_model)
        else:
            self._model_name = "gemini-3.5-flash"

        self._output_mode: str = "plain"  # "plain" or "timestamp"
        self._is_fetching_models: bool = False
        self._fetcher: ModelFetchWorker | None = None
        self._is_processing: bool = False
        self._is_downloading: bool = False
        self._download_percent: float = 0.0
        self._video_urls: str = ""
        self._download_worker: STTDownloadWorker | None = None
        self._status_text: str = ""
        self._console_logs: str = ""
        self._recognized_text: str = ""
        self._worker: STTWorker | None = None

    @Property(str, notify=apiKeysChanged)
    def apiKeys(self) -> str:
        return self._api_keys

    @apiKeys.setter
    def apiKeys(self, val: str) -> None:
        if self._api_keys != val:
            self._api_keys = val
            if self._save_key:
                self._settings.setValue("api_key_v2", val)
            self.apiKeysChanged.emit()

    @Property(bool, notify=saveKeyChanged)
    def saveKey(self) -> bool:
        return self._save_key

    @saveKey.setter
    def saveKey(self, val: bool) -> None:
        if self._save_key != val:
            self._save_key = val
            self._settings.setValue("save_key_v2", val)
            if val:
                self._settings.setValue("api_key_v2", self._api_keys)
            else:
                self._settings.setValue("api_key_v2", "")
            self.saveKeyChanged.emit()

    @Property(list, notify=selectedFilesChanged)
    def selectedFiles(self) -> list[str]:
        return self._selected_files

    @Property(int, notify=selectedFilesChanged)
    def fileCount(self) -> int:
        return len(self._selected_files)

    @Property(str, notify=modelNameChanged)
    def modelName(self) -> str:
        return self._model_name

    @modelName.setter
    def modelName(self, val: str) -> None:
        if self._model_name != val and val:
            self._model_name = val
            self._settings.setValue("selected_model_v2", val)
            if val not in self._available_models:
                self._available_models.append(val)
                self._settings.setValue("cached_models_v2", self._available_models)
                self.availableModelsChanged.emit()
            self.modelNameChanged.emit()

    @Property(list, notify=availableModelsChanged)
    def availableModels(self) -> list[str]:
        return self._available_models

    @Property(bool, notify=isFetchingModelsChanged)
    def isFetchingModels(self) -> bool:
        return self._is_fetching_models

    @Property(bool, notify=isProcessingChanged)
    def isProcessing(self) -> bool:
        return self._is_processing

    @Property(str, notify=outputModeChanged)
    def outputMode(self) -> str:
        return self._output_mode

    @outputMode.setter
    def outputMode(self, val: str) -> None:
        if self._output_mode != val:
            self._output_mode = val
            self.outputModeChanged.emit()

    @Property(bool, notify=isDownloadingChanged)
    def isDownloading(self) -> bool:
        return self._is_downloading

    @Property(float, notify=downloadPercentChanged)
    def downloadPercent(self) -> float:
        return self._download_percent

    @Property(str, notify=videoUrlsChanged)
    def videoUrls(self) -> str:
        return self._video_urls

    @videoUrls.setter
    def videoUrls(self, val: str) -> None:
        if self._video_urls != val:
            self._video_urls = val
            self.videoUrlsChanged.emit()

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(str, notify=consoleLogsChanged)
    def consoleLogs(self) -> str:
        return self._console_logs

    @Property(str, notify=recognizedTextChanged)
    def recognizedText(self) -> str:
        return self._recognized_text

    @recognizedText.setter
    def recognizedText(self, val: str) -> None:
        if self._recognized_text != val:
            self._recognized_text = val
            self.recognizedTextChanged.emit()
            self.hasResultChanged.emit()

    @Property(bool, notify=hasResultChanged)
    def hasResult(self) -> bool:
        return bool(self._recognized_text.strip())

    @Slot(str, result=bool)
    def isVideoFile(self, path: str) -> bool:
        if not path:
            return False
        ext = os.path.splitext(path)[1].lower()
        return ext in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".ts", ".m4v"}

    @Slot(list)
    def setFiles(self, files: list[str]) -> None:
        self._selected_files = [f for f in files if f and os.path.exists(f)]
        self.selectedFilesChanged.emit()

    @Slot(str)
    def addFile(self, file_path: str) -> None:
        if file_path and os.path.exists(file_path) and file_path not in self._selected_files:
            self._selected_files.append(file_path)
            self.selectedFilesChanged.emit()

    @Slot(int)
    def removeFileAt(self, index: int) -> None:
        if 0 <= index < len(self._selected_files):
            self._selected_files.pop(index)
            self.selectedFilesChanged.emit()

    @Slot()
    def clearFiles(self) -> None:
        self._selected_files = []
        self.selectedFilesChanged.emit()

    @Slot(str, result=bool)
    def loadKeysFromFile(self, file_path: str) -> bool:
        try:
            if not os.path.exists(file_path):
                return False
            with open(file_path, encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                if self._api_keys:
                    self.apiKeys = f"{self._api_keys}, {content}"
                else:
                    self.apiKeys = content
                return True
            return False
        except Exception as e:
            logger.warning("Failed to load API keys: %s", e)
            return False

    @Slot()
    def refreshModelsFromApi(self) -> None:
        """Fetch latest models from Gemini API in background."""
        if not self._api_keys.strip():
            self._console_logs += "[-] Vui lòng nhập API Key trước khi cập nhật model.\n"
            self._status_text = "Chưa có API Key!"
            self.consoleLogsChanged.emit()
            self.statusTextChanged.emit()
            return

        if self._is_fetching_models:
            return

        self._is_fetching_models = True
        self.isFetchingModelsChanged.emit()
        self._console_logs += "[+] Đang kết nối Google Gemini API để cập nhật model mới nhất...\n"
        self.consoleLogsChanged.emit()

        self._fetcher = ModelFetchWorker(self._api_keys)
        self._fetcher.progress.connect(self._on_fetch_progress)
        self._fetcher.models_fetched.connect(self._on_models_fetched)
        self._fetcher.fetch_error.connect(self._on_fetch_error)
        self._fetcher.start()

    def _on_fetch_progress(self, msg: str) -> None:
        self._console_logs += f"{msg}\n"
        self.consoleLogsChanged.emit()

    def _on_models_fetched(self, models: list[str]) -> None:
        self._is_fetching_models = False
        self.isFetchingModelsChanged.emit()

        for m in models:
            if m not in self._available_models:
                self._available_models.append(m)

        self._settings.setValue("cached_models_v2", self._available_models)
        self.availableModelsChanged.emit()

        self._console_logs += (
            f"[+] Đã cập nhật thành công danh sách {len(self._available_models)} models!\n"
        )
        self._status_text = "Đã cập nhật danh sách model!"
        self.consoleLogsChanged.emit()
        self.statusTextChanged.emit()

    def _on_fetch_error(self, err_msg: str) -> None:
        self._is_fetching_models = False
        self.isFetchingModelsChanged.emit()
        self._console_logs += f"[-] {err_msg}\n"
        self._status_text = err_msg
        self.consoleLogsChanged.emit()
        self.statusTextChanged.emit()

    @Slot(str)
    def addCustomModel(self, model_name: str) -> None:
        """Add a custom model name manually."""
        name = model_name.strip()
        if not name:
            return
        if name not in self._available_models:
            self._available_models.append(name)
            self._settings.setValue("cached_models_v2", self._available_models)
            self.availableModelsChanged.emit()
        self.modelName = name

    @Slot()
    def downloadLinks(self) -> None:
        """Download video/audio from input URLs in background."""
        if self._is_downloading:
            return
        urls = [
            u.strip()
            for u in self._video_urls.splitlines()
            if u.strip() and not u.strip().startswith("#")
        ]
        if not urls:
            self._status_text = "Vui lòng nhập ít nhất 1 đường dẫn video!"
            self._console_logs += "[-] Vui lòng dán link video (YouTube, TikTok, Facebook...)\n"
            self.statusTextChanged.emit()
            self.consoleLogsChanged.emit()
            return

        output_dir = os.path.join(tempfile.gettempdir(), "vienetts_stt_downloads")

        self._is_downloading = True
        self._download_percent = 0.0
        self.isDownloadingChanged.emit()
        self.downloadPercentChanged.emit()

        self._console_logs += f"[+] Đang chuẩn bị tải {len(urls)} link video/audio...\n"
        self._status_text = "Đang tải video/âm thanh..."
        self.consoleLogsChanged.emit()
        self.statusTextChanged.emit()

        self._download_worker = STTDownloadWorker(urls=urls, output_dir=output_dir)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.percent.connect(self._on_download_percent)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_progress(self, msg: str) -> None:
        self._console_logs += f"{msg}\n"
        self._status_text = msg
        self.consoleLogsChanged.emit()
        self.statusTextChanged.emit()

    def _on_download_percent(self, pct: float) -> None:
        self._download_percent = pct
        self.downloadPercentChanged.emit()

    def _on_download_finished(self, files: list[str]) -> None:
        self._is_downloading = False
        self._download_percent = 100.0
        self.isDownloadingChanged.emit()
        self.downloadPercentChanged.emit()

        added_count = 0
        for f in files:
            if f and os.path.exists(f) and f not in self._selected_files:
                self._selected_files.append(f)
                added_count += 1

        if added_count > 0:
            self.selectedFilesChanged.emit()
            self._status_text = f"Đã tải xong và thêm {added_count} tệp vào danh sách!"
            self._console_logs += f"[+] Đã thêm {added_count} tệp tải về vào hàng đợi nhận diện.\n"
        else:
            self._status_text = "Tải hoàn tất!"
        self.statusTextChanged.emit()
        self.consoleLogsChanged.emit()

    def _on_download_error(self, err_msg: str) -> None:
        self._is_downloading = False
        self.isDownloadingChanged.emit()
        self._status_text = f"Lỗi tải video: {err_msg}"
        self._console_logs += f"[-] Lỗi tải video: {err_msg}\n"
        self.statusTextChanged.emit()
        self.consoleLogsChanged.emit()

    @Slot()
    def startStt(self) -> None:
        if not self._selected_files or not self._api_keys.strip() or self._is_processing:
            return

        self._is_processing = True
        self.isProcessingChanged.emit()
        self._console_logs = (
            f"[+] Bắt đầu nhận diện giọng nói (Model: {self._model_name}, "
            f"Chế độ: {self._output_mode})...\n"
        )
        self.consoleLogsChanged.emit()
        self._status_text = "Đang xử lý âm thanh/video..."
        self.statusTextChanged.emit()

        self._worker = STTWorker(
            api_keys=self._api_keys,
            file_paths=self._selected_files,
            model_name=self._model_name,
            output_mode=self._output_mode,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, msg: str) -> None:
        self._console_logs += f"{msg}\n"
        self._status_text = msg
        self.consoleLogsChanged.emit()
        self.statusTextChanged.emit()

    def _on_finished(self, text_output: str) -> None:
        self._is_processing = False
        self._recognized_text = text_output
        self._status_text = "Hoàn tất nhận diện!"
        self._console_logs += "\n=== KẾT QUẢ VĂN BẢN ===\n" + text_output + "\n"

        self.isProcessingChanged.emit()
        self.recognizedTextChanged.emit()
        self.hasResultChanged.emit()
        self.statusTextChanged.emit()
        self.consoleLogsChanged.emit()

    def _on_error(self, err_msg: str) -> None:
        self._is_processing = False
        self._status_text = f"Lỗi: {err_msg}"
        self._console_logs += f"\n[-] LỖI: {err_msg}\n"
        self.isProcessingChanged.emit()
        self.statusTextChanged.emit()
        self.consoleLogsChanged.emit()

    @Slot(str, result=bool)
    def exportText(self, path: str) -> bool:
        if not self._recognized_text or not path:
            return False
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._recognized_text)
            return True
        except Exception as e:
            logger.warning("Failed to export text: %s", e)
            return False

    @Slot(str, result=bool)
    def exportDocx(self, path: str) -> bool:
        if not self._recognized_text or not path:
            return False
        try:
            import docx

            doc = docx.Document()
            for line in self._recognized_text.splitlines():
                if line.strip():
                    doc.add_paragraph(line)
            doc.save(path)
            return True
        except Exception as e:
            logger.warning("Failed to export DOCX: %s", e)
            return False

    @Slot(str, result=bool)
    def exportSrt(self, path: str) -> bool:
        """Export recognized text formatted as an SRT subtitle file."""
        if not self._recognized_text or not path:
            return False
        try:
            srt_content = text_to_srt(self._recognized_text)
            with open(path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return True
        except Exception as e:
            logger.warning("Failed to export SRT: %s", e)
            return False

    def shutdown(self) -> None:
        """Cleanly terminate any active background worker on app exit."""
        if self._worker is not None and self._worker.isRunning():
            try:
                self._worker.terminate()
                self._worker.wait(500)
            except Exception:
                pass
            self._worker = None
        if self._fetcher is not None and self._fetcher.isRunning():
            try:
                self._fetcher.terminate()
                self._fetcher.wait(500)
            except Exception:
                pass
            self._fetcher = None
        if self._download_worker is not None and self._download_worker.isRunning():
            try:
                self._download_worker.cancel()
                self._download_worker.terminate()
                self._download_worker.wait(500)
            except Exception:
                pass
            self._download_worker = None

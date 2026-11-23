"""Media UI Controller: QML-exposed controller for Media Tools (Video Split, MP3 Split,
Video Merge, Audio Convert, Copyright Bypass, and Video Downloader).
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

from vienetts_app.features.media_tools import (
    bypass_video_copyright,
    convert_audio_files,
    download_videos_ytdlp,
    get_ffmpeg_path,
    get_ffprobe_path,
    get_ytdlp_path,
    merge_videos,
    split_audio_by_length,
    split_audio_by_parts,
    split_audio_custom_times,
    split_video_by_length,
    split_video_by_parts,
    split_video_custom_times,
    update_ytdlp_binary,
)

logger = logging.getLogger(__name__)


class MediaController(QObject):
    """QML Controller managing all Media Processing features."""

    # General state signals
    subTabChanged = Signal()
    isProcessingChanged = Signal()
    progressChanged = Signal()
    statusTextChanged = Signal()
    consoleLogsChanged = Signal()
    lastSuccessMessageChanged = Signal()
    lastErrorMessageChanged = Signal()

    # Split video signals
    splitVideoInputChanged = Signal()
    splitVideoOutputChanged = Signal()
    splitVideoLengthChanged = Signal()
    splitVideoPartsChanged = Signal()
    splitVideoCustomRangesChanged = Signal()

    # Split mp3 signals
    splitMp3InputChanged = Signal()
    splitMp3OutputChanged = Signal()
    splitMp3LengthChanged = Signal()
    splitMp3PartsChanged = Signal()
    splitMp3CustomRangesChanged = Signal()

    # Merge video signals
    mergeFilesChanged = Signal()
    mergeOutputChanged = Signal()
    mergeUseXfadeChanged = Signal()
    mergeXfadeTypeChanged = Signal()
    mergeXfadeDurChanged = Signal()
    mergeResolutionChanged = Signal()
    mergeLogoPathChanged = Signal()
    mergeLogoPositionChanged = Signal()
    mergeSubtitlePathChanged = Signal()

    # Convert audio signals
    convertFilesChanged = Signal()
    convertOutputChanged = Signal()
    convertFormatChanged = Signal()
    convertBitrateChanged = Signal()

    # Bypass signals
    bypassInputChanged = Signal()
    bypassOutputChanged = Signal()
    bypassOnlyMd5Changed = Signal()
    bypassHflipChanged = Signal()
    bypassSpeedChanged = Signal()
    bypassCropChanged = Signal()
    bypassColorChanged = Signal()
    bypassNoiseChanged = Signal()
    bypassVolumeChanged = Signal()

    # Download signals
    downloadUrlsChanged = Signal()
    downloadOutputChanged = Signal()
    downloadQualityChanged = Signal()

    # Tool paths availability signals
    toolsStatusChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("VieNeu", "MediaTools")

        # General
        self._sub_tab: str = "split_video"
        self._is_processing: bool = False
        self._progress: float = 0.0
        self._status_text: str = ""
        self._console_logs: str = ""
        self._last_success_message: str = ""
        self._last_error_message: str = ""
        self._cancel_flag: bool = False
        self._worker_thread: threading.Thread | None = None

        # Split Video
        self._split_video_input: str = ""
        self._split_video_output: str = self._settings.value("split_video_output", "")
        self._split_video_length: int = int(self._settings.value("split_video_length", 120))
        self._split_video_parts: int = int(self._settings.value("split_video_parts", 6))
        self._split_video_custom_ranges: list[str] = []

        # Split MP3
        self._split_mp3_input: str = ""
        self._split_mp3_output: str = self._settings.value("split_mp3_output", "")
        self._split_mp3_length: int = int(self._settings.value("split_mp3_length", 120))
        self._split_mp3_parts: int = int(self._settings.value("split_mp3_parts", 6))
        self._split_mp3_custom_ranges: list[str] = []

        # Merge Video
        self._merge_files: list[str] = []
        self._merge_output: str = self._settings.value("merge_output", "")
        self._merge_use_xfade: bool = bool(
            self._settings.value("merge_use_xfade", False, type=bool)
        )
        self._merge_xfade_type: str = str(self._settings.value("merge_xfade_type", "fade"))
        self._merge_xfade_dur: float = float(self._settings.value("merge_xfade_dur", 1.0))
        self._merge_resolution: str = str(self._settings.value("merge_resolution", "1280x720 (HD)"))
        self._merge_logo_path: str = ""
        self._merge_logo_position: str = "Trên-Phải"
        self._merge_subtitle_path: str = ""

        # Convert Audio
        self._convert_files: list[str] = []
        self._convert_output: str = self._settings.value("convert_output", "")
        self._convert_format: str = str(self._settings.value("convert_format", "MP3 (Phổ biến)"))
        self._convert_bitrate: str = str(self._settings.value("convert_bitrate", "320k"))

        # Bypass
        self._bypass_input: str = ""
        self._bypass_output: str = self._settings.value("bypass_output", "")
        self._bypass_only_md5: bool = False
        self._bypass_hflip: bool = True
        self._bypass_speed: bool = True
        self._bypass_crop: bool = True
        self._bypass_color: bool = True
        self._bypass_noise: bool = False
        self._bypass_volume: bool = True

        # Download
        self._download_urls: str = ""
        self._download_output: str = self._settings.value("download_output", "")
        self._download_quality: str = str(
            self._settings.value("download_quality", "Video tốt nhất + Audio (MP4)")
        )

    # ---------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------

    @Property(str, notify=subTabChanged)
    def subTab(self) -> str:
        return self._sub_tab

    @subTab.setter
    def subTab(self, value: str) -> None:
        if self._sub_tab != value:
            self._sub_tab = value
            self.subTabChanged.emit()

    @Property(bool, notify=isProcessingChanged)
    def isProcessing(self) -> bool:
        return self._is_processing

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(str, notify=consoleLogsChanged)
    def consoleLogs(self) -> str:
        return self._console_logs

    @Property(str, notify=lastSuccessMessageChanged)
    def lastSuccessMessage(self) -> str:
        return self._last_success_message

    @Property(str, notify=lastErrorMessageChanged)
    def lastErrorMessage(self) -> str:
        return self._last_error_message

    # Split Video Properties
    @Property(str, notify=splitVideoInputChanged)
    def splitVideoInput(self) -> str:
        return self._split_video_input

    @splitVideoInput.setter
    def splitVideoInput(self, val: str) -> None:
        if self._split_video_input != val:
            self._split_video_input = val
            self.splitVideoInputChanged.emit()

    @Property(str, notify=splitVideoOutputChanged)
    def splitVideoOutput(self) -> str:
        return self._split_video_output

    @splitVideoOutput.setter
    def splitVideoOutput(self, val: str) -> None:
        if self._split_video_output != val:
            self._split_video_output = val
            self._settings.setValue("split_video_output", val)
            self.splitVideoOutputChanged.emit()

    @Property(int, notify=splitVideoLengthChanged)
    def splitVideoLength(self) -> int:
        return self._split_video_length

    @splitVideoLength.setter
    def splitVideoLength(self, val: int) -> None:
        if self._split_video_length != val:
            self._split_video_length = val
            self._settings.setValue("split_video_length", val)
            self.splitVideoLengthChanged.emit()

    @Property(int, notify=splitVideoPartsChanged)
    def splitVideoParts(self) -> int:
        return self._split_video_parts

    @splitVideoParts.setter
    def splitVideoParts(self, val: int) -> None:
        if self._split_video_parts != val:
            self._split_video_parts = val
            self._settings.setValue("split_video_parts", val)
            self.splitVideoPartsChanged.emit()

    @Property(list, notify=splitVideoCustomRangesChanged)
    def splitVideoCustomRanges(self) -> list[str]:
        return self._split_video_custom_ranges

    # Split MP3 Properties
    @Property(str, notify=splitMp3InputChanged)
    def splitMp3Input(self) -> str:
        return self._split_mp3_input

    @splitMp3Input.setter
    def splitMp3Input(self, val: str) -> None:
        if self._split_mp3_input != val:
            self._split_mp3_input = val
            self.splitMp3InputChanged.emit()

    @Property(str, notify=splitMp3OutputChanged)
    def splitMp3Output(self) -> str:
        return self._split_mp3_output

    @splitMp3Output.setter
    def splitMp3Output(self, val: str) -> None:
        if self._split_mp3_output != val:
            self._split_mp3_output = val
            self._settings.setValue("split_mp3_output", val)
            self.splitMp3OutputChanged.emit()

    @Property(int, notify=splitMp3LengthChanged)
    def splitMp3Length(self) -> int:
        return self._split_mp3_length

    @splitMp3Length.setter
    def splitMp3Length(self, val: int) -> None:
        if self._split_mp3_length != val:
            self._split_mp3_length = val
            self._settings.setValue("split_mp3_length", val)
            self.splitMp3LengthChanged.emit()

    @Property(int, notify=splitMp3PartsChanged)
    def splitMp3Parts(self) -> int:
        return self._split_mp3_parts

    @splitMp3Parts.setter
    def splitMp3Parts(self, val: int) -> None:
        if self._split_mp3_parts != val:
            self._split_mp3_parts = val
            self._settings.setValue("split_mp3_parts", val)
            self.splitMp3PartsChanged.emit()

    @Property(list, notify=splitMp3CustomRangesChanged)
    def splitMp3CustomRanges(self) -> list[str]:
        return self._split_mp3_custom_ranges

    # Merge Video Properties
    @Property(list, notify=mergeFilesChanged)
    def mergeFiles(self) -> list[str]:
        return self._merge_files

    @Property(str, notify=mergeOutputChanged)
    def mergeOutput(self) -> str:
        return self._merge_output

    @mergeOutput.setter
    def mergeOutput(self, val: str) -> None:
        if self._merge_output != val:
            self._merge_output = val
            self._settings.setValue("merge_output", val)
            self.mergeOutputChanged.emit()

    @Property(bool, notify=mergeUseXfadeChanged)
    def mergeUseXfade(self) -> bool:
        return self._merge_use_xfade

    @mergeUseXfade.setter
    def mergeUseXfade(self, val: bool) -> None:
        if self._merge_use_xfade != val:
            self._merge_use_xfade = val
            self._settings.setValue("merge_use_xfade", val)
            self.mergeUseXfadeChanged.emit()

    @Property(str, notify=mergeXfadeTypeChanged)
    def mergeXfadeType(self) -> str:
        return self._merge_xfade_type

    @mergeXfadeType.setter
    def mergeXfadeType(self, val: str) -> None:
        if self._merge_xfade_type != val:
            self._merge_xfade_type = val
            self._settings.setValue("merge_xfade_type", val)
            self.mergeXfadeTypeChanged.emit()

    @Property(float, notify=mergeXfadeDurChanged)
    def mergeXfadeDur(self) -> float:
        return self._merge_xfade_dur

    @mergeXfadeDur.setter
    def mergeXfadeDur(self, val: float) -> None:
        if self._merge_xfade_dur != val:
            self._merge_xfade_dur = val
            self._settings.setValue("merge_xfade_dur", val)
            self.mergeXfadeDurChanged.emit()

    @Property(str, notify=mergeResolutionChanged)
    def mergeResolution(self) -> str:
        return self._merge_resolution

    @mergeResolution.setter
    def mergeResolution(self, val: str) -> None:
        if self._merge_resolution != val:
            self._merge_resolution = val
            self._settings.setValue("merge_resolution", val)
            self.mergeResolutionChanged.emit()

    @Property(str, notify=mergeLogoPathChanged)
    def mergeLogoPath(self) -> str:
        return self._merge_logo_path

    @mergeLogoPath.setter
    def mergeLogoPath(self, val: str) -> None:
        if self._merge_logo_path != val:
            self._merge_logo_path = val
            self.mergeLogoPathChanged.emit()

    @Property(str, notify=mergeLogoPositionChanged)
    def mergeLogoPosition(self) -> str:
        return self._merge_logo_position

    @mergeLogoPosition.setter
    def mergeLogoPosition(self, val: str) -> None:
        if self._merge_logo_position != val:
            self._merge_logo_position = val
            self.mergeLogoPositionChanged.emit()

    @Property(str, notify=mergeSubtitlePathChanged)
    def mergeSubtitlePath(self) -> str:
        return self._merge_subtitle_path

    @mergeSubtitlePath.setter
    def mergeSubtitlePath(self, val: str) -> None:
        if self._merge_subtitle_path != val:
            self._merge_subtitle_path = val
            self.mergeSubtitlePathChanged.emit()

    # Convert Audio Properties
    @Property(list, notify=convertFilesChanged)
    def convertFiles(self) -> list[str]:
        return self._convert_files

    @Property(str, notify=convertOutputChanged)
    def convertOutput(self) -> str:
        return self._convert_output

    @convertOutput.setter
    def convertOutput(self, val: str) -> None:
        if self._convert_output != val:
            self._convert_output = val
            self._settings.setValue("convert_output", val)
            self.convertOutputChanged.emit()

    @Property(str, notify=convertFormatChanged)
    def convertFormat(self) -> str:
        return self._convert_format

    @convertFormat.setter
    def convertFormat(self, val: str) -> None:
        if self._convert_format != val:
            self._convert_format = val
            self._settings.setValue("convert_format", val)
            self.convertFormatChanged.emit()

    @Property(str, notify=convertBitrateChanged)
    def convertBitrate(self) -> str:
        return self._convert_bitrate

    @convertBitrate.setter
    def convertBitrate(self, val: str) -> None:
        if self._convert_bitrate != val:
            self._convert_bitrate = val
            self._settings.setValue("convert_bitrate", val)
            self.convertBitrateChanged.emit()

    # Bypass Properties
    @Property(str, notify=bypassInputChanged)
    def bypassInput(self) -> str:
        return self._bypass_input

    @bypassInput.setter
    def bypassInput(self, val: str) -> None:
        if self._bypass_input != val:
            self._bypass_input = val
            self.bypassInputChanged.emit()

    @Property(str, notify=bypassOutputChanged)
    def bypassOutput(self) -> str:
        return self._bypass_output

    @bypassOutput.setter
    def bypassOutput(self, val: str) -> None:
        if self._bypass_output != val:
            self._bypass_output = val
            self._settings.setValue("bypass_output", val)
            self.bypassOutputChanged.emit()

    @Property(bool, notify=bypassOnlyMd5Changed)
    def bypassOnlyMd5(self) -> bool:
        return self._bypass_only_md5

    @bypassOnlyMd5.setter
    def bypassOnlyMd5(self, val: bool) -> None:
        if self._bypass_only_md5 != val:
            self._bypass_only_md5 = val
            self.bypassOnlyMd5Changed.emit()

    @Property(bool, notify=bypassHflipChanged)
    def bypassHflip(self) -> bool:
        return self._bypass_hflip

    @bypassHflip.setter
    def bypassHflip(self, val: bool) -> None:
        if self._bypass_hflip != val:
            self._bypass_hflip = val
            self.bypassHflipChanged.emit()

    @Property(bool, notify=bypassSpeedChanged)
    def bypassSpeed(self) -> bool:
        return self._bypass_speed

    @bypassSpeed.setter
    def bypassSpeed(self, val: bool) -> None:
        if self._bypass_speed != val:
            self._bypass_speed = val
            self.bypassSpeedChanged.emit()

    @Property(bool, notify=bypassCropChanged)
    def bypassCrop(self) -> bool:
        return self._bypass_crop

    @bypassCrop.setter
    def bypassCrop(self, val: bool) -> None:
        if self._bypass_crop != val:
            self._bypass_crop = val
            self.bypassCropChanged.emit()

    @Property(bool, notify=bypassColorChanged)
    def bypassColor(self) -> bool:
        return self._bypass_color

    @bypassColor.setter
    def bypassColor(self, val: bool) -> None:
        if self._bypass_color != val:
            self._bypass_color = val
            self.bypassColorChanged.emit()

    @Property(bool, notify=bypassNoiseChanged)
    def bypassNoise(self) -> bool:
        return self._bypass_noise

    @bypassNoise.setter
    def bypassNoise(self, val: bool) -> None:
        if self._bypass_noise != val:
            self._bypass_noise = val
            self.bypassNoiseChanged.emit()

    @Property(bool, notify=bypassVolumeChanged)
    def bypassVolume(self) -> bool:
        return self._bypass_volume

    @bypassVolume.setter
    def bypassVolume(self, val: bool) -> None:
        if self._bypass_volume != val:
            self._bypass_volume = val
            self.bypassVolumeChanged.emit()

    # Download Properties
    @Property(str, notify=downloadUrlsChanged)
    def downloadUrls(self) -> str:
        return self._download_urls

    @downloadUrls.setter
    def downloadUrls(self, val: str) -> None:
        if self._download_urls != val:
            self._download_urls = val
            self.downloadUrlsChanged.emit()

    @Property(str, notify=downloadOutputChanged)
    def downloadOutput(self) -> str:
        return self._download_output

    @downloadOutput.setter
    def downloadOutput(self, val: str) -> None:
        if self._download_output != val:
            self._download_output = val
            self._settings.setValue("download_output", val)
            self.downloadOutputChanged.emit()

    @Property(str, notify=downloadQualityChanged)
    def downloadQuality(self) -> str:
        return self._download_quality

    @downloadQuality.setter
    def downloadQuality(self, val: str) -> None:
        if self._download_quality != val:
            self._download_quality = val
            self._settings.setValue("download_quality", val)
            self.downloadQualityChanged.emit()

    # Tool status check
    @Property(str, notify=toolsStatusChanged)
    def ffmpegPath(self) -> str:
        return get_ffmpeg_path()

    @Property(str, notify=toolsStatusChanged)
    def ffprobePath(self) -> str:
        return get_ffprobe_path()

    @Property(str, notify=toolsStatusChanged)
    def ytdlpPath(self) -> str:
        return get_ytdlp_path()

    # ---------------------------------------------------------------------
    # Internal state helpers
    # ---------------------------------------------------------------------

    def _set_processing(self, processing: bool, status: str = "") -> None:
        self._is_processing = processing
        self.isProcessingChanged.emit()
        if status:
            self._status_text = status
            self.statusTextChanged.emit()

    def _update_progress(self, val: float) -> None:
        self._progress = max(0.0, min(100.0, float(val)))
        self.progressChanged.emit()

    def _log(self, text: str) -> None:
        clean = str(text).strip()
        if clean:
            self._console_logs += clean + "\n"
            self.consoleLogsChanged.emit()

    def _check_cancelled(self) -> bool:
        return self._cancel_flag

    # ---------------------------------------------------------------------
    # Slots / Methods
    # ---------------------------------------------------------------------

    @Slot(str)
    def setSubTab(self, tab_id: str) -> None:
        self.subTab = tab_id

    @Slot(str)
    def appendLog(self, msg: str) -> None:
        self._log(msg)

    @Slot()
    def clearLogs(self) -> None:
        self._console_logs = ""
        self.consoleLogsChanged.emit()

    @Slot()
    def cancelOperation(self) -> None:
        self._cancel_flag = True
        self._log("⚠️ Yêu cầu hủy tác vụ đang chạy...")
        self._status_text = "Đang hủy..."
        self.statusTextChanged.emit()

    # ========================== CHIA VIDEO ==========================

    @Slot()
    def startSplitVideoByLength(self) -> None:
        if not self._split_video_input or not os.path.isfile(self._split_video_input):
            self._show_error("Vui lòng chọn video đầu vào hợp lệ!")
            return
        if not self._split_video_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return

        def task():
            self._set_processing(True, f"Đang chia video theo {self._split_video_length}s...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = split_video_by_length(
                self._split_video_input,
                self._split_video_output,
                self._split_video_length,
                log_cb=self._log,
            )
            self._update_progress(100.0 if ok else 0.0)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    @Slot()
    def startSplitVideoByParts(self) -> None:
        if not self._split_video_input or not os.path.isfile(self._split_video_input):
            self._show_error("Vui lòng chọn video đầu vào hợp lệ!")
            return
        if not self._split_video_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return

        def task():
            self._set_processing(True, f"Đang chia video thành {self._split_video_parts} phần...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = split_video_by_parts(
                self._split_video_input,
                self._split_video_output,
                self._split_video_parts,
                log_cb=self._log,
            )
            self._update_progress(100.0 if ok else 0.0)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    @Slot(str, str)
    def addSplitVideoRange(self, start: str, end: str) -> None:
        if not start.strip() or not end.strip():
            return
        self._split_video_custom_ranges.append(f"{start.strip()},{end.strip()}")
        self.splitVideoCustomRangesChanged.emit()

    @Slot()
    def clearSplitVideoRanges(self) -> None:
        self._split_video_custom_ranges = []
        self.splitVideoCustomRangesChanged.emit()

    @Slot()
    def startSplitVideoCustom(self) -> None:
        if not self._split_video_input or not os.path.isfile(self._split_video_input):
            self._show_error("Vui lòng chọn video đầu vào hợp lệ!")
            return
        if not self._split_video_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return
        if not self._split_video_custom_ranges:
            self._show_error("Vui lòng thêm ít nhất một khoảng thời gian cần cắt!")
            return

        ranges = [
            (item.split(",")[0], item.split(",")[1])
            for item in self._split_video_custom_ranges
            if "," in item
        ]

        def task():
            self._set_processing(True, "Đang cắt video theo mốc thời gian...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = split_video_custom_times(
                self._split_video_input,
                self._split_video_output,
                ranges,
                log_cb=self._log,
            )
            self._update_progress(100.0 if ok else 0.0)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    # ========================== CHIA MP3 ==========================

    @Slot()
    def startSplitMp3ByLength(self) -> None:
        if not self._split_mp3_input or not os.path.isfile(self._split_mp3_input):
            self._show_error("Vui lòng chọn file âm thanh đầu vào hợp lệ!")
            return
        if not self._split_mp3_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return

        def task():
            self._set_processing(True, f"Đang chia âm thanh theo {self._split_mp3_length}s...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = split_audio_by_length(
                self._split_mp3_input,
                self._split_mp3_output,
                self._split_mp3_length,
                log_cb=self._log,
            )
            self._update_progress(100.0 if ok else 0.0)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    @Slot()
    def startSplitMp3ByParts(self) -> None:
        if not self._split_mp3_input or not os.path.isfile(self._split_mp3_input):
            self._show_error("Vui lòng chọn file âm thanh đầu vào hợp lệ!")
            return
        if not self._split_mp3_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return

        def task():
            self._set_processing(True, f"Đang chia âm thanh thành {self._split_mp3_parts} phần...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = split_audio_by_parts(
                self._split_mp3_input,
                self._split_mp3_output,
                self._split_mp3_parts,
                log_cb=self._log,
            )
            self._update_progress(100.0 if ok else 0.0)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    @Slot(str, str)
    def addSplitMp3Range(self, start: str, end: str) -> None:
        if not start.strip() or not end.strip():
            return
        self._split_mp3_custom_ranges.append(f"{start.strip()},{end.strip()}")
        self.splitMp3CustomRangesChanged.emit()

    @Slot()
    def clearSplitMp3Ranges(self) -> None:
        self._split_mp3_custom_ranges = []
        self.splitMp3CustomRangesChanged.emit()

    @Slot()
    def startSplitMp3Custom(self) -> None:
        if not self._split_mp3_input or not os.path.isfile(self._split_mp3_input):
            self._show_error("Vui lòng chọn file âm thanh đầu vào hợp lệ!")
            return
        if not self._split_mp3_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return
        if not self._split_mp3_custom_ranges:
            self._show_error("Vui lòng thêm ít nhất một khoảng thời gian cần cắt!")
            return

        ranges = [
            (item.split(",")[0], item.split(",")[1])
            for item in self._split_mp3_custom_ranges
            if "," in item
        ]

        def task():
            self._set_processing(True, "Đang cắt MP3 theo mốc thời gian...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = split_audio_custom_times(
                self._split_mp3_input,
                self._split_mp3_output,
                ranges,
                log_cb=self._log,
            )
            self._update_progress(100.0 if ok else 0.0)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    # ========================== GHÉP VIDEO ==========================

    @Slot(list)
    def addMergeFiles(self, files: list[Any]) -> None:
        for f in files:
            path_str = self._clean_file_url(str(f))
            if path_str and path_str not in self._merge_files:
                self._merge_files.append(path_str)
        self.mergeFilesChanged.emit()

    @Slot(int)
    def removeMergeFile(self, index: int) -> None:
        if 0 <= index < len(self._merge_files):
            self._merge_files.pop(index)
            self.mergeFilesChanged.emit()

    @Slot()
    def clearMergeFiles(self) -> None:
        self._merge_files = []
        self.mergeFilesChanged.emit()

    @Slot()
    def startMerge(self) -> None:
        if len(self._merge_files) < 2:
            self._show_error("Vui lòng thêm ít nhất 2 video để ghép nối!")
            return
        if not self._merge_output:
            self._show_error("Vui lòng chọn file đầu ra output (.mp4)!")
            return

        def task():
            self._set_processing(True, "Đang ghép nối video...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = merge_videos(
                video_files=self._merge_files,
                output_file=self._merge_output,
                use_xfade=self._merge_use_xfade,
                xfade_type=self._merge_xfade_type,
                xfade_duration=self._merge_xfade_dur,
                resolution=self._merge_resolution,
                logo_path=self._merge_logo_path,
                logo_position=self._merge_logo_position,
                subtitle_path=self._merge_subtitle_path,
                progress_cb=self._update_progress,
                log_cb=self._log,
                cancel_check=self._check_cancelled,
            )
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    # ========================== CHUYỂN ĐỔI AUDIO ==========================

    @Slot(list)
    def addConvertFiles(self, files: list[Any]) -> None:
        for f in files:
            path_str = self._clean_file_url(str(f))
            if path_str and path_str not in self._convert_files:
                self._convert_files.append(path_str)
        self.convertFilesChanged.emit()

    @Slot(int)
    def removeConvertFile(self, index: int) -> None:
        if 0 <= index < len(self._convert_files):
            self._convert_files.pop(index)
            self.convertFilesChanged.emit()

    @Slot()
    def clearConvertFiles(self) -> None:
        self._convert_files = []
        self.convertFilesChanged.emit()

    @Slot()
    def startAudioConvert(self) -> None:
        if not self._convert_files:
            self._show_error("Vui lòng chọn ít nhất 1 file cần chuyển đổi!")
            return
        if not self._convert_output:
            self._show_error("Vui lòng chọn thư mục lưu output!")
            return

        def task():
            self._set_processing(
                True, f"Đang chuyển đổi {len(self._convert_files)} file sang audio..."
            )
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = convert_audio_files(
                input_files=self._convert_files,
                output_dir=self._convert_output,
                output_format=self._convert_format,
                bitrate=self._convert_bitrate,
                progress_cb=self._update_progress,
                log_cb=self._log,
                cancel_check=self._check_cancelled,
            )
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    # ========================== LÁCH BẢN QUYỀN ==========================

    @Slot()
    def startBypass(self) -> None:
        if not self._bypass_input or not os.path.isfile(self._bypass_input):
            self._show_error("Vui lòng chọn video đầu vào hợp lệ!")
            return
        if not self._bypass_output:
            self._show_error("Vui lòng chọn nơi lưu file xuất (.mp4)!")
            return

        def task():
            self._set_processing(True, "Đang xử lý lách bản quyền...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = bypass_video_copyright(
                input_file=self._bypass_input,
                output_file=self._bypass_output,
                only_md5=self._bypass_only_md5,
                hflip=self._bypass_hflip,
                speed=self._bypass_speed,
                crop=self._bypass_crop,
                color=self._bypass_color,
                noise=self._bypass_noise,
                volume=self._bypass_volume,
                progress_cb=self._update_progress,
                log_cb=self._log,
                cancel_check=self._check_cancelled,
            )
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    # ========================== TẢI VIDEO ==========================

    @Slot()
    def startDownload(self) -> None:
        urls = [u.strip() for u in self._download_urls.split("\n") if u.strip()]
        if not urls:
            self._show_error("Vui lòng nhập ít nhất 1 liên kết video!")
            return
        if not self._download_output:
            self._show_error("Vui lòng chọn thư mục lưu video tải về!")
            return

        def task():
            self._set_processing(True, f"Đang tải {len(urls)} video...")
            self._update_progress(0.0)
            self._cancel_flag = False
            ok, msg = download_videos_ytdlp(
                urls=urls,
                output_dir=self._download_output,
                quality=self._download_quality,
                progress_cb=self._update_progress,
                log_cb=self._log,
                cancel_check=self._check_cancelled,
            )
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    @Slot()
    def startUpdateYtdlp(self) -> None:
        def task():
            self._set_processing(True, "Đang cập nhật yt-dlp...")
            self._cancel_flag = False
            ok, msg = update_ytdlp_binary(log_cb=self._log)
            self._set_processing(False, msg)
            if ok:
                self._show_success(msg)
            else:
                self._show_error(msg)

        self._start_worker(task)

    # ---------------------------------------------------------------------
    # Worker thread management & messaging
    # ---------------------------------------------------------------------

    def _start_worker(self, target: Any) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            self._show_error("Đang có một tác vụ khác đang chạy. Vui lòng chờ hoặc bấm Hủy!")
            return
        self._worker_thread = threading.Thread(target=target, daemon=True)
        self._worker_thread.start()

    def _clean_file_url(self, raw_path: str) -> str:
        s = str(raw_path).strip()
        if s.startswith("file:///"):
            s = s[8:]
        elif s.startswith("file://"):
            s = s[7:]
        # On Windows file:///D:/path -> D:/path
        if len(s) >= 3 and s[0] == "/" and s[2] == ":":
            s = s[1:]
        return os.path.normpath(s)

    def _show_success(self, msg: str) -> None:
        self._last_success_message = msg
        self._log(f"✅ {msg}")
        self.lastSuccessMessageChanged.emit()

    def _show_error(self, msg: str) -> None:
        self._last_error_message = msg
        self._log(f"❌ {msg}")
        self.lastErrorMessageChanged.emit()

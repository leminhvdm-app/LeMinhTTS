"""Unit tests for OCRTab and STTTab features."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from vienetts_app.features.model_fetcher import DEFAULT_GEMINI_MODELS, ModelFetchWorker
from vienetts_app.features.ocr_tab import OCRTab, OCRWorker
from vienetts_app.features.stt_tab import STTTab, STTWorker
from vienetts_app.ui.ocr_controller import OcrController
from vienetts_app.ui.stt_controller import SttController


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_ocr_worker_init() -> None:
    worker = OCRWorker(
        api_keys="key1, key2; key3",
        file_paths=["dummy.png"],
        model_name="gemini-3.5-flash",
        translate=True,
    )
    assert worker.api_keys == ["key1", "key2", "key3"]
    assert worker.file_paths == ["dummy.png"]
    assert worker.model_name == "gemini-3.5-flash"
    assert worker.translate is True


def test_stt_worker_init() -> None:
    worker = STTWorker(
        api_keys="keyA, keyB",
        file_paths=["audio.wav"],
        model_name="gemini-3.5-flash",
    )
    assert worker.api_keys == ["keyA", "keyB"]
    assert worker.file_paths == ["audio.wav"]
    assert worker.model_name == "gemini-3.5-flash"


def test_model_fetcher_worker_init() -> None:
    worker = ModelFetchWorker(api_keys="key1, key2")
    assert worker.api_keys == ["key1", "key2"]
    assert "gemini-3.5-flash" in DEFAULT_GEMINI_MODELS


def test_ocr_controller_models() -> None:
    from PySide6.QtCore import QSettings

    s = QSettings("VieNeu", "OCRTab")
    s.remove("selected_model_v2")
    s.remove("cached_models_v2")

    ctrl = OcrController()
    assert "gemini-3.5-flash" in ctrl.availableModels
    assert ctrl.modelName == "gemini-3.5-flash"

    # Add custom model
    ctrl.addCustomModel("gemini-test-custom")
    assert "gemini-test-custom" in ctrl.availableModels
    assert ctrl.modelName == "gemini-test-custom"

    s.remove("selected_model_v2")
    s.remove("cached_models_v2")


def test_stt_controller_models() -> None:
    from PySide6.QtCore import QSettings

    s = QSettings("VieNeu", "OCRTab")
    s.remove("selected_model_v2")
    s.remove("cached_models_v2")

    ctrl = SttController()
    assert "gemini-3.5-flash" in ctrl.availableModels
    assert ctrl.modelName == "gemini-3.5-flash"

    # Add custom model
    ctrl.addCustomModel("gemini-custom-stt")
    assert "gemini-custom-stt" in ctrl.availableModels
    assert ctrl.modelName == "gemini-custom-stt"

    s.remove("selected_model_v2")
    s.remove("cached_models_v2")


def test_ocr_tab_widget_init() -> None:
    app = QCoreApplication.instance()
    if app is not None and not isinstance(app, QApplication):
        pytest.skip("Process has QCoreApplication/QGuiApplication instead of QApplication")
    _ensure_qapp()
    tab = OCRTab()
    assert tab is not None
    assert hasattr(tab, "select_files")
    assert hasattr(tab, "start_ocr")
    assert hasattr(tab, "generate_and_open_html")


def test_stt_tab_widget_init() -> None:
    app = QCoreApplication.instance()
    if app is not None and not isinstance(app, QApplication):
        pytest.skip("Process has QCoreApplication/QGuiApplication instead of QApplication")
    _ensure_qapp()
    tab = STTTab()
    assert tab is not None
    assert hasattr(tab, "select_files")
    assert hasattr(tab, "start_stt")
    assert hasattr(tab, "save_result")


def test_direct_import_alias() -> None:
    import vienetts_app.ocr_tab as ocr_alias
    import vienetts_app.stt_tab as stt_alias

    assert hasattr(ocr_alias, "OCRTab")
    assert hasattr(ocr_alias, "OCRWorker")
    assert hasattr(stt_alias, "STTTab")
    assert hasattr(stt_alias, "STTWorker")


def test_ocr_worker_text_attachments(tmp_path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Dữ liệu thử nghiệm bảng hỏi", encoding="utf-8")

    worker = OCRWorker(
        api_keys="fake_key_123",
        file_paths=[str(txt_file)],
        model_name="gemini-3.5-flash",
        translate=True,
    )
    assert len(worker.file_paths) == 1


def test_stt_worker_output_modes() -> None:
    w1 = STTWorker(api_keys="k", file_paths=["a.mp4"], output_mode="plain")
    assert w1.output_mode == "plain"
    w2 = STTWorker(api_keys="k", file_paths=["a.mp4"], output_mode="timestamp")
    assert w2.output_mode == "timestamp"


def test_is_video_file() -> None:
    from vienetts_app.features.stt_tab import is_video_file

    assert is_video_file("video.mp4") is True
    assert is_video_file("movie.mkv") is True
    assert is_video_file("clip.avi") is True
    assert is_video_file("audio.wav") is False
    assert is_video_file("song.mp3") is False


def test_text_to_srt_conversion() -> None:
    from vienetts_app.ui.stt_controller import text_to_srt

    sample = "[00:01 - 00:04] Xin chào các bạn.\n[00:05 - 00:10] Hôm nay chúng ta cùng xem phim."
    srt = text_to_srt(sample)
    assert "00:00:01,000 --> 00:00:04,000" in srt
    assert "Xin chào các bạn." in srt
    assert "00:00:05,000 --> 00:00:10,000" in srt


def test_stt_controller_video_and_srt(tmp_path) -> None:
    ctrl = SttController()
    assert ctrl.isVideoFile("movie.mp4") is True
    assert ctrl.isVideoFile("track.mp3") is False

    ctrl.outputMode = "timestamp"
    assert ctrl.outputMode == "timestamp"

    ctrl.videoUrls = "https://youtube.com/watch?v=123"
    assert ctrl.videoUrls == "https://youtube.com/watch?v=123"

    ctrl.recognizedText = "[00:02 - 00:05] Lời thoại phim"
    srt_file = tmp_path / "sub.srt"
    ok = ctrl.exportSrt(str(srt_file))
    assert ok is True
    assert srt_file.exists()
    content = srt_file.read_text(encoding="utf-8")
    assert "00:00:02,000 --> 00:00:05,000" in content
    assert "Lời thoại phim" in content


def test_ocr_worker_custom_prompt() -> None:
    # 1. Custom prompt provided
    w1 = OCRWorker(
        api_keys="key1",
        file_paths=["dummy.png"],
        custom_prompt="Quy tắc trích xuất hóa đơn VAT đặc biệt",
    )
    assert w1.custom_prompt == "Quy tắc trích xuất hóa đơn VAT đặc biệt"

    # 2. Default when omitted
    w2 = OCRWorker(api_keys="key1", file_paths=["dummy.png"])
    assert w2.custom_prompt == ""


def test_ocr_controller_custom_prompt(tmp_path) -> None:
    ctrl = OcrController()
    ctrl.saveCustomPrompt = True
    assert ctrl.saveCustomPrompt is True

    # Test manual setting
    ctrl.customPrompt = "Trích xuất bảng dữ liệu tài chính chính xác"
    assert ctrl.customPrompt == "Trích xuất bảng dữ liệu tài chính chính xác"

    # Test loading from .txt file
    prompt_file = tmp_path / "custom_rules.txt"
    prompt_file.write_text("Quy trình OCR từ file: Chỉ lấy các cột số tiền", encoding="utf-8")

    loaded = ctrl.loadCustomPromptFromFile(str(prompt_file))
    assert loaded is True
    assert ctrl.customPrompt == "Quy trình OCR từ file: Chỉ lấy các cột số tiền"

    # Test clearing
    ctrl.clearCustomPrompt()
    assert ctrl.customPrompt == ""

    # Test reset to hardcoded default prompt (OCR_Anh)
    ctrl.resetToDefaultPrompt()
    assert "OCR ENGINE 01" in ctrl.customPrompt

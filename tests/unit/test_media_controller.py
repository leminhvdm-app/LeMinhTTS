"""Unit tests for MediaController QML bridge."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication

from vienetts_app.ui.media_controller import MediaController


def _ensure_app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_media_controller_properties() -> None:
    _ensure_app()
    ctrl = MediaController()

    assert ctrl.subTab == "split_video"
    ctrl.setSubTab("merge")
    assert ctrl.subTab == "merge"

    assert ctrl.isProcessing is False
    assert ctrl.progress == 0.0

    ctrl.appendLog("Test line 1")
    assert "Test line 1" in ctrl.consoleLogs
    ctrl.clearLogs()
    assert ctrl.consoleLogs == ""


def test_media_controller_merge_list() -> None:
    _ensure_app()
    ctrl = MediaController()
    ctrl.clearMergeFiles()
    assert ctrl.mergeFiles == []

    ctrl.addMergeFiles(["file:///D:/test/v1.mp4", "D:\\test\\v2.mp4"])
    assert len(ctrl.mergeFiles) == 2

    ctrl.removeMergeFile(0)
    assert len(ctrl.mergeFiles) == 1

    ctrl.clearMergeFiles()
    assert len(ctrl.mergeFiles) == 0


def test_media_controller_convert_list() -> None:
    _ensure_app()
    ctrl = MediaController()
    ctrl.clearConvertFiles()

    ctrl.addConvertFiles(["file:///D:/test/a1.mp3", "D:\\test\\a2.wav"])
    assert len(ctrl.convertFiles) == 2

    ctrl.removeConvertFile(1)
    assert len(ctrl.convertFiles) == 1

    ctrl.clearConvertFiles()
    assert len(ctrl.convertFiles) == 0


def test_media_controller_custom_ranges() -> None:
    _ensure_app()
    ctrl = MediaController()

    ctrl.addSplitVideoRange("00:00:10", "00:01:00")
    assert len(ctrl.splitVideoCustomRanges) == 1
    assert ctrl.splitVideoCustomRanges[0] == "00:00:10,00:01:00"

    ctrl.clearSplitVideoRanges()
    assert len(ctrl.splitVideoCustomRanges) == 0

    ctrl.addSplitMp3Range("00:00:05", "00:00:45")
    assert len(ctrl.splitMp3CustomRanges) == 1
    ctrl.clearSplitMp3Ranges()
    assert len(ctrl.splitMp3CustomRanges) == 0


def test_media_controller_cancel() -> None:
    _ensure_app()
    ctrl = MediaController()
    assert ctrl._cancel_flag is False
    ctrl.cancelOperation()
    assert ctrl._cancel_flag is True


def test_media_tools_tab_qml_loads() -> None:
    from pathlib import Path

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

    from vienetts_app.ui.bridge import ShellBridge

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    qml_dir = Path(__file__).parent.parent.parent / "src" / "vienetts_app" / "ui" / "qml"
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))

    bridge = ShellBridge()
    media_ctrl = MediaController()
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.rootContext().setContextProperty("mediaController", media_ctrl)

    component = QQmlComponent(engine, str(qml_dir / "MediaToolsTab.qml"))
    assert not component.isError(), [e.toString() for e in component.errors()]


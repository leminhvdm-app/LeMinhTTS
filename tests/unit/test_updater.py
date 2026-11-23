"""Unit tests for LeMinhTTS Auto-Update Controller and version parser."""

from __future__ import annotations

import pytest

from PySide6.QtCore import QSettings

from vienetts_app import __version__
from vienetts_app.ui.update_controller import UpdateController, parse_version_tuple


def test_parse_version_tuple() -> None:
    assert parse_version_tuple("1.0.0") == (1, 0, 0)
    assert parse_version_tuple("v1.0.3") == (1, 0, 3)
    assert parse_version_tuple("V2.1.0-alpha") == (2, 1, 0)
    assert parse_version_tuple("v2") == (2,)

    # Version comparison tests
    assert parse_version_tuple("v1.1.0") > parse_version_tuple("1.0.0")
    assert parse_version_tuple("v2.0.0") > parse_version_tuple("v1.9.9")
    assert parse_version_tuple("v1.0.0") == parse_version_tuple("1.0.0")
    assert parse_version_tuple("v1.0.0") < parse_version_tuple("1.0.1")


def test_update_controller_initial_state(tmp_path) -> None:
    s = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    ctrl = UpdateController(settings=s)
    assert ctrl.currentVersion == __version__
    assert ctrl.isChecking is False
    assert ctrl.isDownloading is False
    assert ctrl.isUpdateAvailable is False
    assert ctrl.downloadProgress == 0
    assert "LeMinhTTS" in ctrl.githubRepo


def test_update_controller_set_repo(tmp_path) -> None:
    s = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    ctrl = UpdateController(settings=s)
    changed = []
    ctrl.githubRepoChanged.connect(lambda: changed.append(True))
    ctrl.setGithubRepo("myuser/MyTTSApp")
    assert ctrl.githubRepo == "myuser/MyTTSApp"
    assert "myuser/MyTTSApp" in ctrl.releaseUrl
    assert len(changed) == 1

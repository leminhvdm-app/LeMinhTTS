"""Unit tests for media_tools feature engine."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from vienetts_app.features.media_tools import (
    bypass_video_copyright,
    convert_audio_files,
    download_videos_ytdlp,
    get_ffmpeg_path,
    get_ffprobe_path,
    get_media_duration,
    get_ytdlp_path,
    merge_videos,
    parse_time_to_seconds,
    split_audio_by_length,
    split_audio_by_parts,
    split_audio_custom_times,
    split_video_by_length,
    split_video_by_parts,
    split_video_custom_times,
    update_ytdlp_binary,
)


def test_tool_paths_exist_or_fallback() -> None:
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    ytdlp = get_ytdlp_path()
    assert isinstance(ffmpeg, str) and len(ffmpeg) > 0
    assert isinstance(ffprobe, str) and len(ffprobe) > 0
    assert isinstance(ytdlp, str) and len(ytdlp) > 0


def test_parse_time_to_seconds() -> None:
    assert parse_time_to_seconds("01:20:30") == "01:20:30"
    assert parse_time_to_seconds("1h 20m 30s") == str(1 * 3600 + 20 * 60 + 30)
    assert parse_time_to_seconds("2 giờ 15 phút") == str(2 * 3600 + 15 * 60)
    assert parse_time_to_seconds("45s") == "45"
    assert parse_time_to_seconds("120") == "120"
    assert parse_time_to_seconds("") == ""


def test_get_media_duration_nonexistent() -> None:
    assert get_media_duration("nonexistent_file_xyz.mp4") is None


def test_split_video_validation(tmp_path) -> None:
    # Non-existent input
    ok, msg = split_video_by_length("nonexistent.mp4", str(tmp_path), 60)
    assert not ok
    assert "không tồn tại" in msg

    # Invalid length
    dummy = tmp_path / "dummy.mp4"
    dummy.write_text("fake")
    ok, msg = split_video_by_length(str(dummy), str(tmp_path), 0)
    assert not ok
    assert "lớn hơn 0" in msg


def test_split_video_by_parts_duration_fail(tmp_path) -> None:
    dummy = tmp_path / "dummy.mp4"
    dummy.write_text("fake")
    with patch("vienetts_app.features.media_tools.get_media_duration", return_value=None):
        ok, msg = split_video_by_parts(str(dummy), str(tmp_path), 4)
        assert not ok
        assert "thời lượng" in msg


def test_split_video_custom_times_empty(tmp_path) -> None:
    dummy = tmp_path / "dummy.mp4"
    dummy.write_text("fake")
    ok, msg = split_video_custom_times(str(dummy), str(tmp_path), [])
    assert not ok


def test_split_audio_validation(tmp_path) -> None:
    ok, msg = split_audio_by_length("nonexistent.mp3", str(tmp_path), 60)
    assert not ok

    dummy = tmp_path / "dummy.mp3"
    dummy.write_text("fake")
    ok, msg = split_audio_by_length(str(dummy), str(tmp_path), -5)
    assert not ok

    with patch("vienetts_app.features.media_tools.get_media_duration", return_value=None):
        ok, msg = split_audio_by_parts(str(dummy), str(tmp_path), 4)
        assert not ok
        assert "thời lượng" in msg

    ok, msg = split_audio_custom_times(str(dummy), str(tmp_path), [])
    assert not ok


def test_merge_videos_validation(tmp_path) -> None:
    ok, msg = merge_videos([], str(tmp_path / "out.mp4"))
    assert not ok
    assert "ít nhất 2" in msg

    v1 = tmp_path / "v1.mp4"
    v1.write_text("fake1")
    ok, msg = merge_videos([str(v1)], str(tmp_path / "out.mp4"))
    assert not ok
    assert "ít nhất 2" in msg


def test_convert_audio_validation(tmp_path) -> None:
    ok, msg = convert_audio_files([], str(tmp_path))
    assert not ok


def test_bypass_md5(tmp_path) -> None:
    in_file = tmp_path / "sample.mp4"
    in_file.write_bytes(b"hello video content")
    out_file = tmp_path / "sample_bypass.mp4"

    ok, msg = bypass_video_copyright(
        str(in_file),
        str(out_file),
        only_md5=True,
    )
    assert ok
    assert os.path.exists(out_file)
    assert len(out_file.read_bytes()) > len(in_file.read_bytes())


def test_download_videos_validation(tmp_path) -> None:
    ok, msg = download_videos_ytdlp([], str(tmp_path))
    assert not ok
    assert "trống" in msg


def test_update_ytdlp_mock() -> None:
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("yt-dlp is up to date", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        ok, msg = update_ytdlp_binary()
        assert ok
        assert "up to date" in msg

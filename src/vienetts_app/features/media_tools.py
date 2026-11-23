"""Media processing feature engine: Video/Audio splitting, merging, conversion,
copyright bypass, and yt-dlp downloader ported from VDM_All_in_One 1.0.2.

Pure backend logic using ffmpeg, ffprobe, and yt-dlp with subprocess.
"""

from __future__ import annotations

import contextlib
import logging
import os
import random
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_base_search_paths() -> list[Path]:
    """Candidate root paths to search for bundled binaries."""
    paths: list[Path] = [Path(sys.executable).parent]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        paths.extend([exe_dir, exe_dir / "_internal", exe_dir / "tools"])
    else:
        app_dir = Path(__file__).resolve().parent.parent.parent.parent
        paths.extend([
            app_dir,
            app_dir / "VDM_All_in_One 1.0.3",
            app_dir / "VDM_All_in_One 1.0.2",
            app_dir / "tools",
            Path.cwd(),
            Path.cwd() / "VDM_All_in_One 1.0.3",
            Path.cwd() / "VDM_All_in_One 1.0.2",
        ])
    return paths


def get_ffmpeg_path() -> str:
    """Find ffmpeg binary path."""
    for p in get_base_search_paths():
        candidate = p / "ffmpeg.exe" if os.name == "nt" else p / "ffmpeg"
        if candidate.is_file():
            return str(candidate)
    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path
    return "ffmpeg"


def get_ffprobe_path() -> str:
    """Find ffprobe binary path."""
    for p in get_base_search_paths():
        candidate = p / "ffprobe.exe" if os.name == "nt" else p / "ffprobe"
        if candidate.is_file():
            return str(candidate)
    which_path = shutil.which("ffprobe")
    if which_path:
        return which_path
    return "ffprobe"


def get_ytdlp_path() -> str:
    """Find yt-dlp binary path."""
    for p in get_base_search_paths():
        candidate = p / "yt-dlp.exe" if os.name == "nt" else p / "yt-dlp"
        if candidate.is_file():
            return str(candidate)
    venv_candidate = Path(sys.prefix) / "Scripts" / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    if venv_candidate.is_file():
        return str(venv_candidate)
    which_path = shutil.which("yt-dlp")
    if which_path:
        return which_path
    return "yt-dlp"


def get_startupinfo() -> Any:
    """Return STARTUPINFO to hide console window on Windows."""
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo
    return None


def get_media_duration(filepath: str) -> float | None:
    """Retrieve media duration in seconds using ffprobe."""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        cmd = [
            get_ffprobe_path(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filepath,
        ]
        out = subprocess.check_output(cmd, startupinfo=get_startupinfo()).decode("utf-8").strip()
        return float(out)
    except Exception as e:
        logger.debug(f"Could not get duration for {filepath}: {e}")
        return None


def parse_time_to_seconds(time_str: str) -> str:
    """Parse time string like '1h 20m 30s', '120s', '01:20:30' to seconds string."""
    time_str = str(time_str).strip().lower()
    if not time_str:
        return ""
    if ":" in time_str:
        return time_str

    h, m, s = 0, 0, 0
    h_match = re.search(r"(\d+)\s*(?:h|giờ)", time_str)
    m_match = re.search(r"(\d+)\s*(?:m|phút)", time_str)
    s_match = re.search(r"(\d+)\s*(?:s|giây)", time_str)

    if h_match or m_match or s_match:
        if h_match:
            h = int(h_match.group(1))
        if m_match:
            m = int(m_match.group(1))
        if s_match:
            s = int(s_match.group(1))
        return str(h * 3600 + m * 60 + s)
    return time_str


# =========================================================================
# 1. CHIA VIDEO (Video Splitter)
# =========================================================================

def split_video_by_length(
    input_file: str,
    output_dir: str,
    segment_seconds: int,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Split video by fixed segment length in seconds without re-encoding."""
    if not os.path.isfile(input_file):
        return False, "File video đầu vào không tồn tại!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if segment_seconds <= 0:
        return False, "Độ dài đoạn phải lớn hơn 0!"

    base_name = Path(input_file).stem
    ext = Path(input_file).suffix or ".mp4"
    output_pattern = os.path.join(output_dir, f"{base_name}_part%03d{ext}")

    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i",
        input_file,
        "-c",
        "copy",
        "-map",
        "0",
        "-segment_time",
        str(segment_seconds),
        "-f",
        "segment",
        output_pattern,
    ]
    if log_cb:
        log_cb(f"Đang chia video theo độ dài {segment_seconds}s...")

    proc = subprocess.Popen(
        cmd,
        startupinfo=get_startupinfo(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        return True, f"Đã chia video theo độ dài {segment_seconds}s thành công vào: {output_dir}"
    return False, f"Lỗi chia video: {stderr.decode('utf-8', errors='ignore')}"


def split_video_by_parts(
    input_file: str,
    output_dir: str,
    num_parts: int,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Split video into equal number of parts without re-encoding."""
    if not os.path.isfile(input_file):
        return False, "File video đầu vào không tồn tại!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if num_parts <= 0:
        return False, "Số phần phải lớn hơn 0!"

    dur = get_media_duration(input_file)
    if not dur or dur <= 0:
        return False, "Không thể xác định thời lượng của video!"

    segment_seconds = max(1, int(dur / num_parts))
    base_name = Path(input_file).stem
    ext = Path(input_file).suffix or ".mp4"
    output_pattern = os.path.join(output_dir, f"{base_name}_part%03d{ext}")

    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i",
        input_file,
        "-c",
        "copy",
        "-map",
        "0",
        "-segment_time",
        str(segment_seconds),
        "-f",
        "segment",
        output_pattern,
    ]
    if log_cb:
        log_cb(f"Đang chia video thành {num_parts} phần (khoảng {segment_seconds}s mỗi đoạn)...")

    proc = subprocess.Popen(
        cmd,
        startupinfo=get_startupinfo(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        return True, f"Đã chia video thành {num_parts} phần thành công vào: {output_dir}"
    return False, f"Lỗi chia video: {stderr.decode('utf-8', errors='ignore')}"


def split_video_custom_times(
    input_file: str,
    output_dir: str,
    time_ranges: list[tuple[str, str]],
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Cut custom time segments from video."""
    if not os.path.isfile(input_file):
        return False, "File video đầu vào không tồn tại!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if not time_ranges:
        return False, "Danh sách khoảng thời gian trống!"

    base_name = Path(input_file).stem
    ext = Path(input_file).suffix or ".mp4"
    success_count = 0

    for i, (start_raw, end_raw) in enumerate(time_ranges):
        start = parse_time_to_seconds(start_raw)
        end = parse_time_to_seconds(end_raw)
        out_name = os.path.join(output_dir, f"{base_name}_cut_{i+1}{ext}")
        cmd = [
            get_ffmpeg_path(),
            "-y",
            "-i",
            input_file,
            "-ss",
            str(start),
            "-to",
            str(end),
            "-c",
            "copy",
            out_name,
        ]
        if log_cb:
            log_cb(f"Đang cắt đoạn {i+1}: {start_raw} -> {end_raw}...")

        proc = subprocess.Popen(
            cmd,
            startupinfo=get_startupinfo(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.communicate()
        if proc.returncode == 0:
            success_count += 1

    return True, f"Đã cắt xong {success_count}/{len(time_ranges)} đoạn video vào: {output_dir}"


# =========================================================================
# 2. CHIA MP3 / AUDIO (Audio Splitter)
# =========================================================================

def split_audio_by_length(
    input_file: str,
    output_dir: str,
    segment_seconds: int,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Split audio/MP3 by fixed segment length in seconds without re-encoding."""
    if not os.path.isfile(input_file):
        return False, "File âm thanh đầu vào không tồn tại!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if segment_seconds <= 0:
        return False, "Độ dài đoạn phải lớn hơn 0!"

    base_name = Path(input_file).stem
    ext = Path(input_file).suffix or ".mp3"
    output_pattern = os.path.join(output_dir, f"{base_name}_part%03d{ext}")

    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i",
        input_file,
        "-c",
        "copy",
        "-map",
        "0",
        "-segment_time",
        str(segment_seconds),
        "-f",
        "segment",
        output_pattern,
    ]
    if log_cb:
        log_cb(f"Đang chia âm thanh theo độ dài {segment_seconds}s...")

    proc = subprocess.Popen(
        cmd,
        startupinfo=get_startupinfo(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        return True, f"Đã chia âm thanh theo độ dài {segment_seconds}s thành công vào: {output_dir}"
    return False, f"Lỗi chia âm thanh: {stderr.decode('utf-8', errors='ignore')}"


def split_audio_by_parts(
    input_file: str,
    output_dir: str,
    num_parts: int,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Split audio into equal number of parts without re-encoding."""
    if not os.path.isfile(input_file):
        return False, "File âm thanh đầu vào không tồn tại!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if num_parts <= 0:
        return False, "Số phần phải lớn hơn 0!"

    dur = get_media_duration(input_file)
    if not dur or dur <= 0:
        return False, "Không thể xác định thời lượng của file âm thanh!"

    segment_seconds = max(1, int(dur / num_parts))
    base_name = Path(input_file).stem
    ext = Path(input_file).suffix or ".mp3"
    output_pattern = os.path.join(output_dir, f"{base_name}_part%03d{ext}")

    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i",
        input_file,
        "-c",
        "copy",
        "-map",
        "0",
        "-segment_time",
        str(segment_seconds),
        "-f",
        "segment",
        output_pattern,
    ]
    if log_cb:
        log_cb(f"Đang chia âm thanh thành {num_parts} phần...")

    proc = subprocess.Popen(
        cmd,
        startupinfo=get_startupinfo(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        return True, f"Đã chia âm thanh thành {num_parts} phần thành công vào: {output_dir}"
    return False, f"Lỗi chia âm thanh: {stderr.decode('utf-8', errors='ignore')}"


def split_audio_custom_times(
    input_file: str,
    output_dir: str,
    time_ranges: list[tuple[str, str]],
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Cut custom time segments from audio file."""
    if not os.path.isfile(input_file):
        return False, "File âm thanh đầu vào không tồn tại!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if not time_ranges:
        return False, "Danh sách khoảng thời gian trống!"

    base_name = Path(input_file).stem
    ext = Path(input_file).suffix or ".mp3"
    success_count = 0

    for i, (start_raw, end_raw) in enumerate(time_ranges):
        start = parse_time_to_seconds(start_raw)
        end = parse_time_to_seconds(end_raw)
        out_name = os.path.join(output_dir, f"{base_name}_cut_{i+1}{ext}")
        cmd = [
            get_ffmpeg_path(),
            "-y",
            "-i",
            input_file,
            "-ss",
            str(start),
            "-to",
            str(end),
            "-c",
            "copy",
            out_name,
        ]
        if log_cb:
            log_cb(f"Đang cắt đoạn {i+1}: {start_raw} -> {end_raw}...")

        proc = subprocess.Popen(
            cmd,
            startupinfo=get_startupinfo(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.communicate()
        if proc.returncode == 0:
            success_count += 1

    return True, f"Đã cắt xong {success_count}/{len(time_ranges)} đoạn MP3 vào: {output_dir}"


# =========================================================================
# 3. NỐI VIDEO (Media Merger)
# =========================================================================

def merge_videos(
    video_files: list[str],
    output_file: str,
    use_xfade: bool = False,
    xfade_type: str = "fade",
    xfade_duration: float = 1.0,
    resolution: str = "1280x720 (HD)",
    logo_path: str = "",
    logo_position: str = "Trên-Phải",
    subtitle_path: str = "",
    progress_cb: Callable[[float], None] | None = None,
    log_cb: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[bool, str]:
    """Merge a list of video files with optional xfade, logo, subtitle and resolution scaling."""
    if len(video_files) < 2:
        return False, "Vui lòng chọn ít nhất 2 video để ghép nối!"
    for f in video_files:
        if not os.path.isfile(f):
            return False, f"Tệp video không tồn tại: {f}"

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    ffmpeg = get_ffmpeg_path()
    list_file_path = os.path.join(output_dir or ".", "temp_merge_list.txt")

    try:
        # Calculate total duration for progress
        total_duration = 0.0
        fade_dur = float(xfade_duration) if use_xfade else 0.0

        for f in video_files:
            dur = get_media_duration(f)
            if dur:
                total_duration += dur
        if use_xfade and len(video_files) > 1:
            total_duration -= fade_dur * (len(video_files) - 1)

        use_logo = bool(logo_path and os.path.isfile(logo_path))
        use_sub = bool(subtitle_path and os.path.isfile(subtitle_path))

        res_filter = ""
        if "1280x720" in resolution or "720" in resolution and "1280" in resolution and "1280x720" in resolution:
            res_filter = "scale=1280:720"
        elif "1920x1080" in resolution:
            res_filter = "scale=1920:1080"
        elif "720x1280" in resolution:
            res_filter = "scale=720:1280"
        elif "1080x1920" in resolution:
            res_filter = "scale=1080:1920"
        elif "2560x1440" in resolution:
            res_filter = "scale=2560:1440"
        elif "3840x2160" in resolution:
            res_filter = "scale=3840:2160"

        if not use_xfade:
            # Simple concat
            with open(list_file_path, "w", encoding="utf-8") as f:
                for video in video_files:
                    clean_v = str(video).replace("\\", "/")
                    f.write(f"file '{clean_v}'\n")

            filters: list[str] = []
            if res_filter:
                filters.append(res_filter)
            if use_logo:
                pos = logo_position
                ol_str = (
                    "overlay=W-w-10:10"
                    if "Trên-Phải" in pos
                    else "overlay=10:10"
                    if "Trên-Trái" in pos
                    else "overlay=W-w-10:H-h-10"
                    if "Dưới-Phải" in pos
                    else "overlay=10:H-h-10"
                )
                filters.append(ol_str)
            if use_sub:
                escaped_sub = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
                filters.append(f"subtitles='{escaped_sub}'")

            cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file_path]
            if use_logo:
                cmd.extend(["-i", logo_path])
                if res_filter or use_sub:
                    complex_f = f"[0:v]{res_filter if res_filter else 'null'}[bg];[bg][1:v]{filters[-1]}[outv]"
                    cmd.extend(["-filter_complex", complex_f, "-map", "[outv]", "-map", "0:a?"])
                else:
                    cmd.extend(["-filter_complex", f"[0:v][1:v]{filters[0]}[outv]", "-map", "[outv]", "-map", "0:a?"])
            else:
                if filters:
                    cmd.extend(["-vf", ",".join(filters)])
                else:
                    cmd.extend(["-c", "copy"])

            cmd.append(output_file)
        else:
            # Complex xfade filtergraph
            cmd = [ffmpeg, "-y"]
            for f in video_files:
                cmd.extend(["-i", f])

            w, h = 1280, 720
            if "1920x1080" in resolution:
                w, h = 1920, 1080
            elif "720x1280" in resolution:
                w, h = 720, 1280
            elif "1080x1920" in resolution:
                w, h = 1080, 1920
            elif "2560x1440" in resolution:
                w, h = 2560, 1440
            elif "3840x2160" in resolution:
                w, h = 3840, 2160

            norm_v = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,fps=30,setsar=1"

            filter_complex = ""
            for i in range(len(video_files)):
                filter_complex += f"[{i}:v]{norm_v}[v{i}];"
                filter_complex += f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];"

            current_offset = 0.0
            last_v = "[v0]"
            last_a = "[a0]"

            for i in range(1, len(video_files)):
                dur = get_media_duration(video_files[i - 1]) or 5.0
                current_offset += max(0.1, dur - fade_dur)

                next_v = f"[v{i}]"
                next_a = f"[a{i}]"
                out_v = f"[v{i}_out]"
                out_a = f"[a{i}_out]"

                filter_complex += (
                    f"{last_v}{next_v}xfade=transition={xfade_type}:duration={fade_dur}:offset={current_offset:.2f}{out_v};"
                )
                filter_complex += f"{last_a}{next_a}acrossfade=d={fade_dur}{out_a};"

                last_v = out_v
                last_a = out_a

            final_v = last_v
            if use_logo:
                cmd.extend(["-i", logo_path])
                pos = logo_position
                ol_str = (
                    "overlay=W-w-10:10"
                    if "Trên-Phải" in pos
                    else "overlay=10:10"
                    if "Trên-Trái" in pos
                    else "overlay=W-w-10:H-h-10"
                    if "Dưới-Phải" in pos
                    else "overlay=10:H-h-10"
                )
                filter_complex += f"{final_v}[{len(video_files)}:v]{ol_str}[v_logo];"
                final_v = "[v_logo]"

            if use_sub:
                escaped_sub = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
                filter_complex += f"{final_v}subtitles='{escaped_sub}'[v_sub];"
                final_v = "[v_sub]"

            cmd.extend(["-filter_complex", filter_complex, "-map", final_v, "-map", last_a, output_file])

        if log_cb:
            log_cb(f"Bắt đầu render nối {len(video_files)} video...")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=get_startupinfo(),
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
        err_output = ""

        if proc.stdout:
            for line in proc.stdout:
                if cancel_check and cancel_check():
                    proc.kill()
                    return False, "Đã hủy tác vụ nối video."
                err_output += line
                match = time_pattern.search(line)
                if match and total_duration > 0 and progress_cb:
                    h, m, s = match.groups()
                    current_time = int(h) * 3600 + int(m) * 60 + float(s)
                    percent = min((current_time / total_duration) * 100, 99.9)
                    progress_cb(percent)

        proc.wait()
        if proc.returncode == 0:
            if progress_cb:
                progress_cb(100.0)
            return True, f"Nối video thành công: {output_file}"
        return False, f"Lỗi render video:\n{err_output[-500:]}"
    except Exception as e:
        logger.exception("Merge video failed")
        return False, f"Lỗi xử lý: {e}"
    finally:
        if os.path.exists(list_file_path):
            with contextlib.suppress(Exception):
                os.remove(list_file_path)


# =========================================================================
# 4. CHUYỂN ĐỔI AUDIO (Audio Converter / Video to Audio)
# =========================================================================

def convert_audio_files(
    input_files: list[str],
    output_dir: str,
    output_format: str = "MP3 (Phổ biến)",
    bitrate: str = "320k",
    progress_cb: Callable[[float], None] | None = None,
    log_cb: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[bool, str]:
    """Convert audio/video files to various audio formats."""
    if not input_files:
        return False, "Vui lòng chọn ít nhất 1 tệp âm thanh hoặc video!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    ffmpeg = get_ffmpeg_path()
    ext = ".mp3"
    acodec = "libmp3lame"
    if "AAC" in output_format:
        ext, acodec = ".m4a", "aac"
    elif "FLAC" in output_format:
        ext, acodec = ".flac", "flac"
    elif "WAV" in output_format:
        ext, acodec = ".wav", "pcm_s16le"
    elif "OGG" in output_format:
        ext, acodec = ".ogg", "libvorbis"
    elif "Opus" in output_format:
        ext, acodec = ".opus", "libopus"

    total_duration = 0.0
    for f in input_files:
        dur = get_media_duration(f)
        if dur:
            total_duration += dur

    current_completed_duration = 0.0
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
    success_count = 0

    for idx, f in enumerate(input_files):
        if cancel_check and cancel_check():
            return False, "Đã hủy chuyển đổi audio."

        basename = Path(f).stem
        out_path = os.path.join(output_dir, basename + ext)
        cmd = [ffmpeg, "-y", "-i", f, "-vn", "-c:a", acodec]
        if acodec not in ["flac", "pcm_s16le"]:
            cmd.extend(["-b:a", bitrate])
        cmd.append(out_path)

        if log_cb:
            log_cb(f"[{idx+1}/{len(input_files)}] Đang chuyển đổi: {os.path.basename(f)} -> {ext}...")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=get_startupinfo(),
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        if proc.stdout:
            for line in proc.stdout:
                if cancel_check and cancel_check():
                    proc.kill()
                    return False, "Đã hủy chuyển đổi audio."
                match = time_pattern.search(line)
                if match and total_duration > 0 and progress_cb:
                    h, m, s = match.groups()
                    current_time = int(h) * 3600 + int(m) * 60 + float(s)
                    percent = min(((current_completed_duration + current_time) / total_duration) * 100, 99.9)
                    progress_cb(percent)

        proc.wait()
        if proc.returncode == 0:
            success_count += 1
        file_dur = get_media_duration(f)
        if file_dur:
            current_completed_duration += file_dur

    if progress_cb:
        progress_cb(100.0)
    return True, f"Đã chuyển đổi thành công {success_count}/{len(input_files)} tệp vào: {output_dir}"


# =========================================================================
# 5. LÁCH BẢN QUYỀN (Copyright Bypass)
# =========================================================================

def bypass_video_copyright(
    input_file: str,
    output_file: str,
    only_md5: bool = False,
    hflip: bool = False,
    speed: bool = False,
    crop: bool = False,
    color: bool = False,
    noise: bool = False,
    volume: bool = False,
    progress_cb: Callable[[float], None] | None = None,
    log_cb: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[bool, str]:
    """Bypass copyright filters via MD5 tweak or technical transformations."""
    if not os.path.isfile(input_file):
        return False, "Tệp video đầu vào không tồn tại!"

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    if only_md5:
        if log_cb:
            log_cb("Đang thay đổi mã băm MD5 siêu nhanh...")
        shutil.copy2(input_file, output_file)
        with open(output_file, "ab") as f:
            f.write(random.randbytes(16))
        if progress_cb:
            progress_cb(100.0)
        return True, f"Đã lách MD5 thành công (siêu nhanh): {output_file}"

    ffmpeg = get_ffmpeg_path()
    cmd = [ffmpeg, "-y", "-i", input_file]

    vf_filters: list[str] = []
    af_filters: list[str] = []

    if hflip:
        vf_filters.append("hflip")
    if speed:
        vf_filters.append("setpts=0.95238*PTS")
        af_filters.append("atempo=1.05")
    if crop:
        vf_filters.append("crop=iw-4:ih-4")
    if color:
        vf_filters.append("eq=brightness=0.02:saturation=1.05")
    if noise:
        vf_filters.append("noise=alls=1:allf=t")
    if volume:
        af_filters.append("volume=1.05")

    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])
    if af_filters:
        cmd.extend(["-af", ",".join(af_filters)])

    cmd.extend(["-c:v", "libx264", "-c:a", "aac", output_file])

    if log_cb:
        log_cb("Bắt đầu xử lý lách bản quyền video...")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=get_startupinfo(),
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    total_duration = get_media_duration(input_file) or 0.0

    if proc.stdout:
        for line in proc.stdout:
            if cancel_check and cancel_check():
                proc.kill()
                return False, "Đã hủy tác vụ lách bản quyền."
            if total_duration > 0 and progress_cb:
                match = time_pattern.search(line)
                if match:
                    h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
                    current_time = h * 3600 + m * 60 + s
                    percent = min(99.9, (current_time / total_duration) * 100)
                    progress_cb(percent)

    proc.wait()
    if proc.returncode == 0:
        if progress_cb:
            progress_cb(100.0)
        return True, f"Đã lách bản quyền video thành công: {output_file}"
    return False, "Quá trình lách bản quyền thất bại."


# =========================================================================
# 6. TẢI VIDEO (Video Downloader - yt-dlp)
# =========================================================================

def download_videos_ytdlp(
    urls: list[str],
    output_dir: str,
    quality: str = "Video tốt nhất + Audio (MP4)",
    progress_cb: Callable[[float], None] | None = None,
    log_cb: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[bool, str]:
    """Download video/audio from URL list using yt-dlp."""
    clean_urls = [u.strip() for u in urls if u.strip() and not u.strip().startswith("#")]
    if not clean_urls:
        return False, "Danh sách liên kết tải về trống!"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    ytdlp = get_ytdlp_path()
    total_urls = len(clean_urls)
    success_count = 0
    progress_pattern = re.compile(r"\[download\]\s+(\d+\.\d+)%")

    for idx, url in enumerate(clean_urls):
        if cancel_check and cancel_check():
            return False, "Đã hủy tải video."

        if log_cb:
            log_cb(f"[{idx+1}/{total_urls}] Đang tải: {url}...")

        cmd = [ytdlp, "--newline"]
        if "Video tốt nhất" in quality:
            cmd.extend(["-S", "vcodec:h264,res,acodec:m4a"])
            cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--merge-output-format", "mp4"])
        elif "1080p" in quality:
            cmd.extend(["-S", "vcodec:h264,res,acodec:m4a"])
            cmd.extend(["-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best", "--merge-output-format", "mp4"])
        elif "720p" in quality:
            cmd.extend(["-S", "vcodec:h264,res,acodec:m4a"])
            cmd.extend(["-f", "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best", "--merge-output-format", "mp4"])
        elif "MP3" in quality:
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
        elif "M4A" in quality:
            cmd.extend(["-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "m4a"])

        cmd.extend(["-o", os.path.join(output_dir, "%(title).150B.%(ext)s")])
        cmd.append(url)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=get_startupinfo(),
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        if proc.stdout:
            for line in proc.stdout:
                if cancel_check and cancel_check():
                    proc.kill()
                    return False, "Đã hủy tải video."
                match = progress_pattern.search(line)
                if match and progress_cb:
                    single_pct = float(match.group(1))
                    overall_pct = ((idx + (single_pct / 100.0)) / total_urls) * 100.0
                    progress_cb(min(99.9, overall_pct))

        proc.wait()
        if proc.returncode == 0:
            success_count += 1

    if progress_cb:
        progress_cb(100.0)
    if success_count > 0:
        return True, f"Đã tải xong {success_count}/{total_urls} video vào: {output_dir}"
    return False, "Tải video thất bại cho tất cả các đường dẫn."


def update_ytdlp_binary(log_cb: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Run self-update on yt-dlp binary."""
    ytdlp = get_ytdlp_path()
    try:
        if log_cb:
            log_cb(f"Đang chạy lệnh cập nhật yt-dlp ({ytdlp} -U)...")
        proc = subprocess.Popen(
            [ytdlp, "-U"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=get_startupinfo(),
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            return True, stdout.strip() or "yt-dlp đã được cập nhật lên phiên bản mới nhất!"
        return False, stderr.strip() or "Cập nhật yt-dlp thất bại."
    except FileNotFoundError:
        return False, "Không tìm thấy tập tin yt-dlp.exe!"
    except Exception as e:
        return False, f"Lỗi: {e}"

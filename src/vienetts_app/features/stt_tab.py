import contextlib
import mimetypes
import os
import re
import subprocess
import tempfile

try:
    from PySide6.QtCore import QSettings, Qt, QThread
    from PySide6.QtCore import Signal as pyqtSignal
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFileDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PyQt6.QtCore import QSettings, QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFileDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

from vienetts_app.features.media_tools import get_ffmpeg_path, get_startupinfo

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".ts", ".m4v", ".3gp"
}


def is_video_file(path: str) -> bool:
    """Check if file path has a video extension."""
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTENSIONS


def extract_audio_if_needed(path: str, log_cb=None) -> tuple[str, bool]:
    """If path is a video file, extract its audio track into a lightweight AAC/M4A file.
    
    Returns (path_to_audio, is_temporary_file).
    """
    if not is_video_file(path):
        return path, False

    try:
        ffmpeg = get_ffmpeg_path()
        cache_dir = os.path.join(tempfile.gettempdir(), "vienetts_stt_cache")
        os.makedirs(cache_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(path))[0]
        safe_name = re.sub(r'[\\/*?:"<>| ]', "_", base_name)[:50]
        out_path = os.path.join(cache_dir, f"{safe_name}_{os.getpid()}_{abs(hash(path))}.m4a")

        if log_cb:
            log_cb(f"[+] Phát hiện video: {os.path.basename(path)}. Đang trích xuất audio bằng ffmpeg...")

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            path,
            "-vn",
            "-acodec",
            "aac",
            "-b:a",
            "64k",
            "-ac",
            "1",
            out_path,
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            startupinfo=get_startupinfo(),
            check=False,
        )
        if res.returncode == 0 and os.path.exists(out_path):
            size_kb = os.path.getsize(out_path) // 1024
            if log_cb:
                log_cb(f"[+] Trích xuất âm thanh thành công ({size_kb} KB): {os.path.basename(out_path)}")
            return out_path, True
        else:
            err = res.stderr.decode("utf-8", errors="ignore")
            if log_cb:
                log_cb(f"[-] ffmpeg không trích xuất được audio: {err[:150]}")
    except Exception as e:
        if log_cb:
            log_cb(f"[-] Lỗi khi trích xuất audio từ video: {e}")

    return path, False


class STTWorker(QThread):
    finished = pyqtSignal(str)  # output text
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        api_keys,
        file_paths,
        model_name="gemini-3.5-flash",
        output_mode="plain",
    ):
        super().__init__()
        self.api_keys = [k.strip() for k in re.split(r"[,;\s]+", api_keys) if k.strip()]
        self.file_paths = file_paths
        self.model_name = model_name
        self.output_mode = output_mode

    def run(self):
        if not self.api_keys:
            self.error.emit("Vui lòng nhập ít nhất 1 API Key của Google Gemini.")
            return

        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import google.generativeai as genai

            self.progress.emit("[+] Bắt đầu xử lý âm thanh/video...")

            if self.output_mode == "timestamp":
                prompt = (
                    "Bạn là chuyên gia bóc băng âm thanh (Speech-to-Text) chuyên nghiệp phục vụ làm phụ đề và dựng video reup/review phim.\n"
                    "Nhiệm vụ: Trích xuất toàn bộ lời thoại của tất cả các nhân vật trong âm thanh này, kèm mốc thời gian chi tiết.\n"
                    "Yêu cầu:\n"
                    "1. Định dạng mỗi câu thoại có mốc thời gian rõ ràng: [hh:mm:ss] hoặc [mm:ss] - [mm:ss]: <Lời thoại>.\n"
                    "2. Bắt trọn toàn bộ giọng nói, bỏ qua nhạc nền và tạp âm.\n"
                    "3. Chuẩn hóa chính tả tiếng Việt và điền dấu câu chính xác, tự nhiên.\n"
                    "4. Chỉ trả về danh sách lời thoại kèm mốc thời gian, không thêm lời chào hay giải thích nào khác."
                )
            else:
                prompt = (
                    "Chuyển đổi toàn bộ âm thanh này thành văn bản (Speech-to-Text) phục vụ làm kịch bản tóm tắt và reup phim.\n"
                    "Nhiệm vụ: Trích xuất đầy đủ, trung thực toàn bộ lời thoại và lời dẫn của các nhân vật.\n"
                    "Yêu cầu:\n"
                    "1. Lấy toàn bộ giọng nói, loại bỏ tạp âm và nhạc nền.\n"
                    "2. Điền dấu câu hợp lý, ngắt đoạn mạch lạc, sửa các lỗi phát âm cơ bản để văn bản đọc tự nhiên nhất khi làm reup.\n"
                    "3. Chỉ trả về phần nội dung văn bản kịch bản, không giải thích gì thêm."
                )

            success = False
            last_error = ""
            temp_files_to_clean = []

            for key in self.api_keys:
                try:
                    self.progress.emit(
                        f"[+] Đang kết nối tới máy chủ AI (Google) bằng Key bắt đầu với {key[:8]}..."
                    )
                    genai.configure(api_key=key, transport="rest")

                    results = []
                    for path in self.file_paths:
                        self.progress.emit(f"[+] Đang chuẩn bị: {os.path.basename(path)}...")

                        audio_path, is_temp = extract_audio_if_needed(path, log_cb=self.progress.emit)
                        if is_temp:
                            temp_files_to_clean.append(audio_path)

                        mime_type, _ = mimetypes.guess_type(audio_path)
                        if not mime_type:
                            ext = audio_path.lower().split(".")[-1]
                            if ext in ["wav", "mp3", "ogg", "flac"]:
                                mime_type = f"audio/{ext}"
                            elif ext in ["m4a", "mp4"]:
                                mime_type = "audio/mp4"
                            elif ext in ["aac"]:
                                mime_type = "audio/aac"
                            else:
                                mime_type = "audio/wav"

                        file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
                        uploaded_file = None

                        if file_size > 15 * 1024 * 1024:
                            self.progress.emit(
                                f"[+] Tệp dung lượng lớn ({file_size // (1024*1024)}MB), đang tải lên Gemini File API..."
                            )
                            uploaded_file = genai.upload_file(path=audio_path, mime_type=mime_type)
                            content_inputs = [uploaded_file, prompt]
                        else:
                            with open(audio_path, "rb") as f:
                                audio_bytes = f.read()
                            audio_data = {"mime_type": mime_type, "data": audio_bytes}
                            content_inputs = [audio_data, prompt]

                        self.progress.emit("[+] Đang phân tích giọng nói (Vui lòng chờ)...")
                        model = genai.GenerativeModel(self.model_name)

                        response = model.generate_content(content_inputs)
                        text_output = response.text.strip()
                        results.append(f"--- File: {os.path.basename(path)} ---\n{text_output}\n")

                        if uploaded_file is not None:
                            with contextlib.suppress(Exception):
                                genai.delete_file(uploaded_file.name)

                    self.progress.emit("[+] Nhận diện thành công!")
                    self.finished.emit("\n".join(results))
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    self.progress.emit(
                        f"[-] Lỗi API Key: {last_error}. Chuyển sang key tiếp theo..."
                    )
                    continue
                finally:
                    for tf in temp_files_to_clean:
                        with contextlib.suppress(Exception):
                            if os.path.exists(tf):
                                os.remove(tf)
                    temp_files_to_clean.clear()

            if not success:
                self.progress.emit("[-] Tất cả API Keys đều thất bại.")
                self.error.emit(f"Tất cả API Keys đều thất bại. Lỗi cuối cùng: {last_error}")

        except Exception:
            import traceback

            self.error.emit(traceback.format_exc())


class STTTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_files = []
        self.init_ui()
        self.apply_dark_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget#stt_main {
                background-color: #111827; /* Dark background */
                color: #e5e7eb;
            }
            QLabel {
                color: #e5e7eb;
            }
            QGroupBox {
                border: 1px solid #374151;
                border-radius: 8px;
                margin-top: 15px;
                background-color: #1f2937;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #ef4444; /* Red color */
                font-weight: bold;
                top: 0px;
            }
            QLineEdit, QComboBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                color: #f3f4f6;
                padding: 5px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #4b5563;
                color: #9ca3af;
            }
            QPushButton#process_btn {
                background-color: #10b981;
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
            }
            QPushButton#process_btn:hover {
                background-color: #059669;
            }
            QTextEdit {
                background-color: #111827;
                color: #3b82f6; /* Blue text */
                border: 1px solid #374151;
                border-radius: 4px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                padding: 10px;
            }
            QMessageBox {
                background-color: #1f2937;
            }
            QMessageBox QLabel {
                color: #f3f4f6;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #3b82f6;
                color: white;
                min-width: 80px;
                padding: 5px;
            }
        """)

    def init_ui(self):
        self.setObjectName("stt_main")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # API Keys & Model (Top Section)
        top_layout = QHBoxLayout()

        lbl_keys = QLabel("GEMINI API KEYS:")
        lbl_keys.setStyleSheet("color: #ef4444; font-weight: bold;")
        top_layout.addWidget(lbl_keys)
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Nhập các API Key, ngăn cách bằng dấu phẩy...")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        top_layout.addWidget(self.api_input)

        self.btn_toggle_eye = QPushButton("👁️")
        self.btn_toggle_eye.setCheckable(True)
        self.btn_toggle_eye.setFixedWidth(40)
        self.btn_toggle_eye.clicked.connect(self.toggle_api_visibility)
        top_layout.addWidget(self.btn_toggle_eye)

        self.btn_load_key = QPushButton("📄 Nhập từ file TXT")
        self.btn_load_key.clicked.connect(self.load_api_keys_from_txt)
        top_layout.addWidget(self.btn_load_key)

        self.chk_save_key = QCheckBox("Lưu Key")
        self.chk_save_key.setStyleSheet("color: #ef4444; font-weight: bold; margin-left: 10px;")
        self.chk_save_key.stateChanged.connect(self.save_api_key_settings)
        top_layout.addWidget(self.chk_save_key)

        top_layout.addSpacing(20)
        lbl_model = QLabel("MODEL:")
        lbl_model.setStyleSheet("color: #ef4444; font-weight: bold;")
        top_layout.addWidget(lbl_model)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(
            [
                "gemini-3.5-flash",
                "gemini-1.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash-8b",
                "gemini-1.5-flash-latest",
            ]
        )
        top_layout.addWidget(self.model_combo)

        main_layout.addLayout(top_layout)

        # Dùng chung QSettings với OCRTab để dùng chung API Key
        self.settings = QSettings("VieNeu", "OCRTab")
        # Xóa cache cũ theo yêu cầu
        self.settings.remove("api_key")
        self.settings.remove("save_key")

        saved_key = self.settings.value("api_key_v2", "")
        should_save = self.settings.value("save_key_v2", False, type=bool)
        if should_save:
            self.chk_save_key.setChecked(True)
            self.api_input.setText(saved_key)

        self.api_input.textChanged.connect(self.save_api_key_settings)

        # Section 1: Chọn File Âm Thanh
        group_file = QGroupBox("1. CHỌN FILE ÂM THANH:")
        file_layout = QVBoxLayout(group_file)
        file_layout.setSpacing(15)

        self.file_label = QLabel("Chưa chọn file.")
        self.file_label.setStyleSheet("color: #d1d5db; font-size: 14px;")
        file_layout.addWidget(self.file_label)

        self.upload_btn = QPushButton("📂 Chọn File Âm Thanh")
        self.upload_btn.setFixedWidth(200)
        self.upload_btn.clicked.connect(self.select_files)
        file_layout.addWidget(self.upload_btn)

        main_layout.addWidget(group_file)

        # Nút Xử lý Trung tâm
        self.process_btn = QPushButton("⏳ BẮT ĐẦU NHẬN DIỆN")
        self.process_btn.setObjectName("process_btn")
        self.process_btn.clicked.connect(self.start_stt)
        main_layout.addWidget(self.process_btn)

        # Log Console & Output
        group_out = QGroupBox("KẾT QUẢ:")
        out_layout = QVBoxLayout(group_out)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Trạng thái và kết quả sẽ hiển thị ở đây...")
        out_layout.addWidget(self.console)

        self.save_btn = QPushButton("💾 LƯU FILE KẾT QUẢ")
        self.save_btn.setStyleSheet(
            "background-color: #f59e0b; color: white; font-size: 14px; padding: 10px; border-radius: 6px; font-weight: bold;"
        )
        self.save_btn.clicked.connect(self.save_result)
        self.save_btn.setEnabled(False)
        out_layout.addWidget(self.save_btn)

        main_layout.addWidget(group_out)

    def load_api_keys_from_txt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file TXT chứa API Keys", "", "Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, encoding="utf-8") as f:
                    keys = f.read().strip()
                if keys:
                    current = self.api_input.text().strip()
                    if current:
                        self.api_input.setText(f"{current}, {keys}")
                    else:
                        self.api_input.setText(keys)
                    QMessageBox.information(self, "Thành công", "Đã nạp API Key từ file.")
                else:
                    QMessageBox.warning(self, "Lỗi", "File TXT trống.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đọc file: {str(e)}")

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn file âm thanh hoặc video",
            "",
            "Tệp Media (*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.mp4 *.mkv *.avi *.mov *.webm);;Audio (*.wav *.mp3 *.m4a *.flac *.ogg *.aac);;Video (*.mp4 *.mkv *.avi *.mov *.webm);;All Files (*.*)",
        )
        if file_paths:
            self.selected_files = file_paths
            self.file_label.setText(f"Đã chọn {len(file_paths)} tệp media.")

    def start_stt(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file âm thanh.")
            return
        if not self.api_input.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập API Key.")
            return

        self.process_btn.setEnabled(False)
        self.process_btn.setText("⏳ ĐANG XỬ LÝ (Có thể mất thời gian)...")
        self.console.clear()
        self.console.append("Sẵn sàng...")

        model_name = self.model_combo.currentText().strip()

        self.worker = STTWorker(self.api_input.text(), self.selected_files, model_name)
        self.worker.progress.connect(self.console.append)
        self.worker.finished.connect(self.on_stt_success)
        self.worker.error.connect(self.on_stt_error)
        self.worker.start()

    def on_stt_success(self, text_content):
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⏳ BẮT ĐẦU NHẬN DIỆN")

        self.console.append("\n=== KẾT QUẢ VĂN BẢN ===\n")
        self.console.append(text_content)

        self.final_text = text_content
        if hasattr(self, "save_btn"):
            self.save_btn.setEnabled(True)

    def save_result(self):
        if not hasattr(self, "final_text") or not self.final_text:
            QMessageBox.warning(self, "Trống", "Chưa có kết quả để lưu.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu file Kết quả",
            "",
            "Word Document (*.docx);;Excel Document (*.xlsx);;PDF Document (*.pdf);;Text File (*.txt);;Markdown File (*.md)",
        )

        if file_path:
            try:
                if file_path.lower().endswith(".docx"):
                    import docx

                    doc = docx.Document()
                    for line in self.final_text.split("\n"):
                        doc.add_paragraph(line)
                    doc.save(file_path)
                elif file_path.lower().endswith(".xlsx"):
                    import openpyxl

                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Ket Qua"
                    for i, line in enumerate(self.final_text.split("\n"), 1):
                        ws.cell(row=i, column=1, value=line)
                    wb.save(file_path)
                elif file_path.lower().endswith(".pdf"):
                    import os

                    from fpdf import FPDF

                    pdf = FPDF()
                    pdf.add_page()
                    # Cài đặt font hỗ trợ tiếng Việt (Arial trên Windows)
                    font_path = "C:/Windows/Fonts/arial.ttf"
                    if os.path.exists(font_path):
                        pdf.add_font("ArialVN", "", font_path, uni=True)
                        pdf.set_font("ArialVN", size=12)
                    else:
                        pdf.set_font("helvetica", size=12)
                    pdf.multi_cell(0, 10, txt=self.final_text)
                    pdf.output(file_path)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(self.final_text)
                QMessageBox.information(
                    self, "Thành công", f"Đã lưu kết quả thành công tại:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {str(e)}")

    def on_stt_error(self, err):
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⏳ BẮT ĐẦU NHẬN DIỆN")
        self.console.append(f"[-] LỖI NGHIÊM TRỌNG: {err}")
        # QMessageBox.critical(self, "Lỗi Nhận Diện", err)

    def toggle_api_visibility(self):
        if self.btn_toggle_eye.isChecked():
            self.api_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Password)

    def save_api_key_settings(self):
        if hasattr(self, "chk_save_key") and hasattr(self, "api_input"):
            if self.chk_save_key.isChecked():
                self.settings.setValue("save_key_v2", True)
                self.settings.setValue("api_key_v2", self.api_input.text())
            else:
                self.settings.setValue("save_key_v2", False)
                self.settings.setValue("api_key_v2", "")


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = STTTab()
    window.setWindowTitle("VieNeu - Giọng nói --> Văn bản")
    window.resize(950, 750)
    window.show()
    sys.exit(app.exec())

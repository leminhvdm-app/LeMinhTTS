import os
import re
import time
import webbrowser

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
        QProgressBar,
        QPushButton,
        QRadioButton,
        QScrollArea,
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
        QRadioButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )



def extract_gemini_response_text(response) -> str:
    """Safely extract text from Gemini response, handling finish_reason=4 (recitation/copyright) gracefully."""
    try:
        if hasattr(response, "text") and response.text:
            return response.text
    except Exception:
        pass

    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        parts_text = []
        if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    parts_text.append(part.text)
        if parts_text:
            return "".join(parts_text)

        finish_reason = getattr(candidate, "finish_reason", None)
        fr_str = str(finish_reason).upper()
        if "4" in fr_str or "RECITATION" in fr_str:
            raise ValueError(
                "Google Gemini chặn tài liệu này do chính sách bản quyền (Recitation Filter: nội dung sách/bài viết trùng lặp với cơ sở dữ liệu tác phẩm). "
                "Cách khắc phục: 1. Đổi sang model khác (ví dụ: gemini-1.5-flash hoặc gemini-2.5-flash); 2. Thêm vào ô Lệnh tùy chỉnh: 'Hãy trích xuất nội dung văn bản dưới dạng bản ghi học tập cá nhân, giữ nguyên bố cục HTML'."
            )
        elif "3" in fr_str or "SAFETY" in fr_str:
            raise ValueError("Google Gemini chặn do bộ lọc an toàn nội dung (Safety Filter).")
        elif "2" in fr_str or "MAX_TOKENS" in fr_str:
            raise ValueError("Đạt giới hạn độ dài phản hồi (Max tokens). Hãy chia nhỏ tài liệu và thử lại.")

    raise ValueError("Google AI không trả về nội dung văn bản hợp lệ cho tệp này.")


class OCRWorker(QThread):
    finished = pyqtSignal(str)  # html output
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        api_keys,
        file_paths,
        model_name="gemini-3.5-flash",
        translate=False,
        custom_prompt="",
    ):
        super().__init__()
        self.api_keys = [k.strip() for k in re.split(r"[,;\s]+", api_keys) if k.strip()]
        self.file_paths = file_paths
        self.model_name = model_name
        self.translate = translate
        self.custom_prompt = custom_prompt

    def run(self):
        if not self.api_keys:
            self.error.emit("Vui lòng nhập ít nhất 1 API Key của Google Gemini.")
            return

        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import google.generativeai as genai

            import pymupdf  # fitz
            from PIL import Image

            self.progress.emit("[+] Bắt đầu xử lý tài liệu & hình ảnh...")
            images = []
            text_attachments = []
            
            for path in self.file_paths:
                ext = os.path.splitext(path)[1].lower()
                self.progress.emit(f"[+] Đang đọc tệp: {os.path.basename(path)}")
                
                # 1. Các định dạng tài liệu hỗ trợ bởi PyMuPDF (PDF, XPS, EPUB, MOBI, FB2, CBZ, SVG)
                if ext in [".pdf", ".xps", ".oxps", ".epub", ".mobi", ".fb2", ".cbz", ".svg"]:
                    try:
                        doc = pymupdf.open(path)
                        for page_idx, page in enumerate(doc):
                            pix = page.get_pixmap(dpi=150)
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            images.append(img)
                        continue
                    except Exception as e:
                        self.progress.emit(f"[!] PyMuPDF không đọc được {os.path.basename(path)}: {e}")

                # 2. Tệp văn bản (.txt, .md, .csv, .log, .json)
                if ext in [".txt", ".md", ".csv", ".log", ".json"]:
                    try:
                        with open(path, encoding="utf-8", errors="ignore") as f:
                            raw_txt = f.read()
                        text_attachments.append(f"--- BẮT ĐẦU TỆP {os.path.basename(path)} ---\n{raw_txt}\n--- KẾT THÚC TỆP ---")
                        continue
                    except Exception as e:
                        self.progress.emit(f"[!] Không đọc được tệp văn bản {os.path.basename(path)}: {e}")

                # 3. Tệp tài liệu Word (.docx)
                if ext == ".docx":
                    try:
                        import docx
                        doc = docx.Document(path)
                        full_docx_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                        for table in doc.tables:
                            for row in table.rows:
                                full_docx_text += "\n" + "\t".join([cell.text.strip() for cell in row.cells])
                        text_attachments.append(f"--- BẮT ĐẦU TỆP WORD {os.path.basename(path)} ---\n{full_docx_text}\n--- KẾT THÚC TỆP ---")
                        continue
                    except Exception as e:
                        self.progress.emit(f"[!] Không đọc được tệp DOCX {os.path.basename(path)}: {e}")

                # 4. Tất cả các định dạng hình ảnh (PNG, JPG, JPEG, JFIF, WEBP, BMP, TIFF, GIF, ICO, TGA, etc.)
                try:
                    loaded_img = Image.open(path)
                    # Xử lý tệp ảnh nhiều trang/frame (TIFF đa trang, GIF hoạt hình)
                    num_frames = getattr(loaded_img, "n_frames", 1)
                    if num_frames > 1:
                        for frame_idx in range(num_frames):
                            loaded_img.seek(frame_idx)
                            images.append(loaded_img.convert("RGB"))
                    else:
                        images.append(loaded_img.convert("RGB"))
                except Exception as e:
                    self.progress.emit(f"[-] Không thể mở ảnh {os.path.basename(path)}: {e}")

            from vienetts_app.features.default_prompts import get_default_ocr_prompt

            active_custom = (
                self.custom_prompt.strip()
                if (self.custom_prompt and self.custom_prompt.strip())
                else get_default_ocr_prompt()
            )
            if active_custom:
                user_rules = active_custom
                if self.translate:
                    base_rules = (
                        "Đồng thời dịch sang tiếng Việt và giữ nguyên bố cục bằng HTML thuần. "
                        "Nếu có các khối văn bản nằm ngang hàng nhau, dùng thẻ <table width='100%' border='0'> để chia cột (không viền). "
                        "Nếu là bảng biểu dữ liệu, dùng thẻ <table border='1' style='border-collapse: collapse'> (có viền). "
                        "Các từ không chắc chắn bọc trong <span style='background-color: yellow'>...</span>. Trả về đúng HTML, không giải thích."
                    )
                else:
                    base_rules = (
                        "Bắt buộc giữ nguyên bố cục 100% như ảnh gốc bằng HTML thuần. "
                        "Nếu có các khối văn bản nằm ngang hàng nhau, dùng thẻ <table width='100%' border='0'> để chia cột (không viền). "
                        "Nếu là bảng biểu dữ liệu, dùng thẻ <table border='1' style='border-collapse: collapse'> (có viền). "
                        "Các đoạn căn giữa dùng <p align='center'>, căn phải <p align='right'>. Tuyệt đối không dùng CSS inline để căn lề. Trả về HTML chuẩn, không giải thích."
                    )
                prompt = (
                    "=== QUY TRÌNH & YÊU CẦU ƯU TIÊN HÀNG ĐẦU CỦA NGƯỜI DÙNG ===\n"
                    f"{user_rules}\n\n"
                    "=== QUY TẮC ĐỊNH DẠNG & CẤU TRÚC BỔ TRỢ ===\n"
                    f"{base_rules}"
                )
            else:
                if self.translate:
                    prompt = (
                        "Trích xuất toàn bộ văn bản và bảng biểu trong tài liệu này và dịch sang tiếng Việt. "
                        "Bắt buộc GIỮ NGUYÊN BỐ CỤC 100% như ảnh gốc bằng HTML thuần. "
                        "NẾU CÓ CÁC KHỐI VĂN BẢN NẰM NGANG HÀNG NHAU, BẮT BUỘC dùng thẻ <table width='100%' border='0'> để chia cột (KHÔNG VIỀN). "
                        "NẾU LÀ BẢNG BIỂU DỮ LIỆU CÓ THẬT, BẮT BUỘC dùng thẻ <table border='1' style='border-collapse: collapse'> (CÓ VIỀN). "
                        "Tuyệt đối không dùng CSS cho việc căn lề. "
                        "Những từ không chắc chắn bọc trong <span style='background-color: yellow'>...</span>. "
                        "Trả về đúng HTML, không giải thích."
                    )
                else:
                    prompt = (
                        "Trích xuất toàn bộ văn bản và bảng biểu trong tài liệu này. "
                        "Bắt buộc GIỮ NGUYÊN BỐ CỤC 100% như ảnh gốc bằng HTML thuần. "
                        "NẾU CÓ CÁC KHỐI VĂN BẢN NẰM NGANG HÀNG NHAU, BẮT BUỘC dùng thẻ <table width='100%' border='0'> để chia cột (BẢNG KHÔNG VIỀN). "
                        "NẾU LÀ BẢNG BIỂU DỮ LIỆU CÓ THẬT TRONG ẢNH, BẮT BUỘC dùng thẻ <table border='1' style='border-collapse: collapse'> (BẢNG CÓ VIỀN). "
                        "Các đoạn căn giữa dùng <p align='center'>, căn phải <p align='right'>. "
                        "Tuyệt đối không dùng CSS inline để căn lề. Trả về HTML chuẩn, không giải thích."
                    )

            if text_attachments:
                prompt += "\n\nNội dung các tệp văn bản đính kèm cần giữ nguyên cấu trúc/dịch tương tự:\n" + "\n\n".join(text_attachments)

            success = False
            last_error = ""
            for key in self.api_keys:
                try:
                    self.progress.emit(
                        f"[+] Đang kết nối tới máy chủ AI (Google) bằng Key bắt đầu với {key[:8]}..."
                    )
                    genai.configure(api_key=key, transport="rest")
                    model = genai.GenerativeModel(self.model_name)
                    contents = images + [prompt]
                    self.progress.emit(
                        "[+] Đang phân tích và quét nội dung (Vui lòng chờ, có thể tốn nhiều thời gian)..."
                    )
                    safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]
                    response = model.generate_content(
                        contents,
                        generation_config={"temperature": 0.25},
                        safety_settings=safety_settings,
                    )

                    html_output = extract_gemini_response_text(response)
                    if html_output.startswith("```html"):
                        html_output = html_output[7:]
                    if html_output.startswith("```"):
                        html_output = html_output[3:]
                    if html_output.endswith("```"):
                        html_output = html_output[:-3]

                    self.progress.emit("[+] Nhận diện thành công!")
                    self.finished.emit(html_output)
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    self.progress.emit(
                        f"[-] Lỗi API Key: {last_error}. Chuyển sang key tiếp theo..."
                    )
                    continue

            if not success:
                self.progress.emit("[-] Tất cả API Keys đều thất bại.")
                self.error.emit(f"Tất cả API Keys đều thất bại. Lỗi cuối cùng: {last_error}")

        except Exception:
            import traceback

            self.error.emit(traceback.format_exc())


class OCRTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_files = []
        self.init_ui()
        self.apply_dark_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget#ocr_main {
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
                color: red;
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
            }
            QPushButton#process_btn:hover {
                background-color: #059669;
            }
            QTextEdit {
                background-color: #111827;
                color: #34d399; /* Green text like terminal */
                border: none;
                font-family: Consolas, monospace;
            }
            QRadioButton {
                color: #e5e7eb;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 9px;
                border: 2px solid #6b7280;
                background-color: #374151;
            }
            QRadioButton::indicator:checked {
                background-color: #3b82f6;
                border: 2px solid #3b82f6;
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
        self.setObjectName("ocr_main")
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

        # Section 1: Chọn Ảnh Tài Liệu
        group_file = QGroupBox("1. CHỌN ẢNH TÀI LIỆU:")
        file_layout = QVBoxLayout(group_file)
        file_layout.setSpacing(15)

        self.file_label = QLabel("Chưa chọn file.")
        self.file_label.setStyleSheet("color: #d1d5db; font-size: 14px;")
        file_layout.addWidget(self.file_label)

        self.upload_btn = QPushButton("📂 Chọn Ảnh/PDF")
        self.upload_btn.setFixedWidth(150)
        self.upload_btn.clicked.connect(self.select_files)
        file_layout.addWidget(self.upload_btn)

        main_layout.addWidget(group_file)

        # Section 2: Tùy Chọn Xử Lý
        group_opt = QGroupBox("2. TÙY CHỌN XỬ LÝ:")
        opt_layout = QVBoxLayout(group_opt)
        opt_layout.setSpacing(10)

        self.radio_original = QRadioButton("Chỉ trích xuất văn bản gốc (Giữ nguyên ngôn ngữ gốc)")
        self.radio_original.setChecked(True)
        self.radio_translate = QRadioButton(
            "Dịch sang tiếng Việt (Bôi vàng chữ không rõ/thiếu chính xác)"
        )

        opt_layout.addWidget(self.radio_original)
        opt_layout.addWidget(self.radio_translate)

        main_layout.addWidget(group_opt)

        # Nút Xử lý Trung tâm
        self.process_btn = QPushButton("⏳ BẮT ĐẦU XỬ LÝ")
        self.process_btn.setObjectName("process_btn")
        self.process_btn.clicked.connect(self.start_ocr)
        main_layout.addWidget(self.process_btn)

        # Log Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Sẵn sàng...")
        main_layout.addWidget(self.console)

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
            "Chọn ảnh hoặc tài liệu quét OCR",
            "",
            "Tất cả định dạng hỗ trợ (*.png *.jpg *.jpeg *.jfif *.webp *.bmp *.tif *.tiff *.gif *.ico *.pdf *.xps *.oxps *.epub *.mobi *.fb2 *.cbz *.svg *.txt *.md *.docx);;Tệp hình ảnh (*.png *.jpg *.jpeg *.jfif *.webp *.bmp *.tif *.tiff *.gif *.ico *.svg *.tga *.ppm *.pgm *.pbm);;Tài liệu PDF (*.pdf);;Sách điện tử & XPS (*.epub *.mobi *.fb2 *.cbz *.xps *.oxps);;Tài liệu văn bản & Word (*.txt *.md *.csv *.json *.log *.docx);;Tất cả các tệp (*.*)",
        )
        if file_paths:
            self.selected_files = file_paths
            self.file_label.setText(f"Đã chọn {len(file_paths)} file.")

    def start_ocr(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file.")
            return
        if not self.api_input.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập API Key.")
            return

        self.process_btn.setEnabled(False)
        self.process_btn.setText("⏳ ĐANG XỬ LÝ (Có thể mất 15-30s)...")
        self.console.clear()
        self.console.append("Sẵn sàng...")

        translate_mode = self.radio_translate.isChecked()
        model_name = self.model_combo.currentText().strip()

        self.worker = OCRWorker(
            self.api_input.text(), self.selected_files, model_name, translate_mode
        )
        self.worker.progress.connect(self.console.append)
        self.worker.finished.connect(self.on_ocr_success)
        self.worker.error.connect(self.on_ocr_error)
        self.worker.start()

    def on_ocr_success(self, html_content):
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⏳ BẮT ĐẦU XỬ LÝ")

        # Generate full HTML file
        self.generate_and_open_html(html_content)

    def on_ocr_error(self, err):
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⏳ BẮT ĐẦU XỬ LÝ")
        self.console.append(f"[-] LỖI NGHIÊM TRỌNG: {err}")
        # QMessageBox.critical(self, "Lỗi Nhận Diện", err)

    def generate_and_open_html(self, content):
        timestamp = int(time.time())
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop_path, f"Ket_Qua_Quet_{timestamp}.html")

        html_template = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kết Quả OCR - Chỉnh Sửa & Xuất File</title>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=Roboto:wght@400;500;700&family=Times+New+Roman&display=swap" rel="stylesheet">
    
    <!-- Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Libraries for Client-side Export -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>

    <style>
        :root {{
            --primary: #006b5f;
            --primary-hover: #005047;
            --bg-page: #f1f5f9;
            --bg-sheet: #ffffff;
            --text-color: #0f172a;
            --border-color: #cbd5e1;
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Times New Roman', 'Be Vietnam Pro', 'Roboto', serif;
            background-color: var(--bg-page);
            color: var(--text-color);
            font-size: 14pt;
            line-height: 1.6;
            padding-bottom: 60px;
        }}

        /* Sticky Action Toolbar */
        .toolbar {{
            position: sticky;
            top: 0;
            z-index: 1000;
            background: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            padding: 12px 24px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            font-family: 'Be Vietnam Pro', Arial, sans-serif;
        }}

        .brand-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .brand-info i {{
            font-size: 22px;
            color: var(--primary);
        }}

        .brand-info h2 {{
            font-size: 16px;
            font-weight: 700;
            color: #1e293b;
        }}

        .btn-group {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: 'Be Vietnam Pro', sans-serif;
            text-decoration: none;
        }}

        .btn:active {{
            transform: translateY(1px);
        }}

        .btn-pdf {{
            background: #dc2626;
            color: #ffffff;
            box-shadow: 0 2px 4px rgba(220, 38, 38, 0.25);
        }}
        .btn-pdf:hover {{ background: #b91c1c; }}

        .btn-word {{
            background: #2563eb;
            color: #ffffff;
            box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);
        }}
        .btn-word:hover {{ background: #1d4ed8; }}

        .btn-excel {{
            background: #16a34a;
            color: #ffffff;
            box-shadow: 0 2px 4px rgba(22, 163, 74, 0.25);
        }}
        .btn-excel:hover {{ background: #15803d; }}

        .btn-print {{
            background: #475569;
            color: #ffffff;
        }}
        .btn-print:hover {{ background: #334155; }}

        .btn-reset {{
            background: #ffffff;
            color: #64748b;
            border-color: #cbd5e1;
        }}
        .btn-reset:hover {{ background: #f8fafc; color: #1e293b; }}

        .hint-bar {{
            background: #f0fdf4;
            border-left: 4px solid #16a34a;
            color: #166534;
            font-size: 13px;
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
            max-width: 1000px;
            margin: 20px auto 0 auto;
            font-family: 'Be Vietnam Pro', sans-serif;
        }}

        /* Document Container */
        .document-wrapper {{
            max-width: 1000px;
            margin: 16px auto;
            background: var(--bg-sheet);
            padding: 50px 60px;
            border-radius: 6px;
            box-shadow: var(--shadow);
            min-height: 1050px;
            outline: none;
            border: 1px solid #e2e8f0;
        }}

        .document-wrapper[contenteditable="true"] {{
            cursor: text;
        }}

        .document-wrapper:focus {{
            border-color: #94a3b8;
        }}

        /* Table & Content Formatting */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 13pt;
        }}

        table[border="1"], table.bordered {{
            border: 1px solid #000000;
        }}

        table[border="1"] th, table[border="1"] td,
        table.bordered th, table.bordered td {{
            border: 1px solid #000000;
            padding: 8px 10px;
            vertical-align: top;
        }}

        table[border="0"] th, table[border="0"] td,
        table.borderless th, table.borderless td {{
            border: none;
            padding: 6px 8px;
            vertical-align: top;
        }}

        p {{
            margin-bottom: 10px;
            line-height: 1.6;
        }}

        h1, h2, h3, h4 {{
            margin: 16px 0 10px 0;
            color: #0f172a;
            font-weight: bold;
        }}

        mark, .highlight, span[style*="background-color: yellow"] {{
            background-color: #fef08a !important;
            padding: 1px 3px;
            border-radius: 2px;
        }}

        /* Toast notification */
        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            font-size: 14px;
            font-weight: 500;
            font-family: 'Be Vietnam Pro', sans-serif;
            display: flex;
            align-items: center;
            gap: 10px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s ease;
            z-index: 2000;
        }}

        .toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}

        .toast.success {{ background: #065f46; }}
        .toast.error {{ background: #991b1b; }}
        .toast.info {{ background: #1e40af; }}

        /* Print Media Styles (Chuẩn khổ A4 Vector) */
        @page {{
            size: A4 portrait;
            margin: 10mm 12mm 10mm 12mm;
        }}

        @media print {{
            *, *:before, *:after {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            body {{
                background: #ffffff !important;
                color: #000000 !important;
                font-size: 11pt !important;
                line-height: 1.4 !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            .toolbar, .hint-bar, .toast {{
                display: none !important;
            }}
            .document-wrapper {{
                box-shadow: none !important;
                border: none !important;
                margin: 0 !important;
                padding: 0 !important;
                max-width: 100% !important;
                width: 100% !important;
                min-height: auto !important;
            }}
            table, tr, td, th, tbody, thead, h1, h2, h3, h4, p {{
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            table {{
                width: 100% !important;
                border-collapse: collapse !important;
                page-break-inside: auto !important;
            }}
            thead {{
                display: table-header-group !important;
            }}
            tr {{
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            table[border="1"], table.bordered, table[border="1"] td, table[border="1"] th {{
                border: 1px solid #000000 !important;
            }}
        }}
    </style>
</head>
<body>

    <!-- Sticky Action Toolbar -->
    <div class="toolbar">
        <div class="brand-info">
            <i class="fa-solid fa-file-waveform"></i>
            <h2>Kết Quả Nhận Diện OCR & Chỉnh Sửa Trực Tiếp</h2>
        </div>

        <div class="btn-group">
            <button class="btn btn-pdf" onclick="exportPDFVector()" title="In hoặc Lưu dưới dạng PDF chuẩn Vector A4 (Khuyên dùng - Nét 100%, không vỡ layout)">
                <i class="fa-solid fa-print"></i> In / Xuất PDF (Chuẩn A4)
            </button>

            <button class="btn btn-pdf" style="background: #b91c1c;" onclick="exportPDFDirect()" title="Tải trực tiếp file .pdf về máy">
                <i class="fa-solid fa-file-arrow-down"></i> Tải nhanh PDF (.pdf)
            </button>
            
            <button class="btn btn-word" onclick="exportWord()" title="Xuất file Microsoft Word (.doc / .docx)">
                <i class="fa-solid fa-file-word"></i> Xuất Word (.docx)
            </button>
            
            <button class="btn btn-excel" onclick="exportExcel()" title="Xuất dữ liệu bảng sang file Excel (.xlsx)">
                <i class="fa-solid fa-file-excel"></i> Xuất Excel (.xlsx)
            </button>

            <button class="btn btn-reset" onclick="resetContent()" title="Khôi phục lại nội dung ban đầu">
                <i class="fa-solid fa-rotate-left"></i> Đặt lại
            </button>
        </div>
    </div>

    <!-- Instruction Bar -->
    <div class="hint-bar">
        <i class="fa-solid fa-circle-check"></i>
        <span><strong>Gợi ý:</strong> Bạn có thể nhấp chuột trực tiếp vào bất kỳ vị trí nào trên văn bản hoặc bảng biểu bên dưới để chỉnh sửa nội dung trước khi bấm xuất file. Để có file PDF đẹp nhất, chọn <strong>"In / Xuất PDF (Chuẩn A4)"</strong> rồi chọn <em>"Lưu dưới dạng PDF"</em>.</span>
    </div>

    <!-- Editable Document Wrapper -->
    <div class="document-wrapper" id="editable_content" contenteditable="true" spellcheck="false">
        {content}
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toastMsg">
        <i class="fa-solid fa-circle-check"></i>
        <span id="toastText">Thao tác thành công!</span>
    </div>

    <!-- Exporters Logic -->
    <script>
        const originalHtml = document.getElementById("editable_content").innerHTML;

        function showToast(msg, type = 'success') {{
            const toast = document.getElementById('toastMsg');
            const text = document.getElementById('toastText');
            toast.className = `toast show ${{type}}`;
            text.innerText = msg;
            
            const icon = toast.querySelector('i');
            if (type === 'success') icon.className = 'fa-solid fa-circle-check';
            else if (type === 'error') icon.className = 'fa-solid fa-triangle-exclamation';
            else icon.className = 'fa-solid fa-circle-info';

            setTimeout(() => {{
                toast.className = 'toast';
            }}, 3200);
        }}

        function resetContent() {{
            if (confirm("Bạn có chắc chắn muốn đặt lại nội dung về bản quét gốc ban đầu?")) {{
                document.getElementById("editable_content").innerHTML = originalHtml;
                showToast("Đã khôi phục nội dung gốc ban đầu!", "info");
            }}
        }}

        // 1A. In / Xuất PDF Vector Chuẩn A4 (Khuyên dùng - Nét 100%, không bị cắt ngang dòng chữ/bảng)
        function exportPDFVector() {{
            showToast("Đang mở hộp thoại In / Lưu PDF A4...", "info");
            setTimeout(() => {{
                window.print();
            }}, 300);
        }}

        // 1B. Tải trực tiếp file PDF (.pdf) với kích thước A4 chuẩn hoá
        function exportPDFDirect() {{
            showToast("Đang kết xuất và tải file PDF...", "info");
            const element = document.getElementById('editable_content');

            const opt = {{
                margin: [8, 10, 8, 10], // mm
                filename: 'Ket_Qua_OCR_' + new Date().toISOString().slice(0, 10) + '.pdf',
                image: {{ type: 'jpeg', quality: 0.98 }},
                html2canvas: {{
                    scale: 2.5,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    backgroundColor: '#ffffff'
                }},
                jsPDF: {{
                    unit: 'mm',
                    format: 'a4',
                    orientation: 'portrait'
                }},
                pagebreak: {{
                    mode: ['avoid-all', 'css', 'legacy'],
                    avoid: ['tr', 'table', 'h1', 'h2', 'h3', 'p', 'div']
                }}
            }};

            if (typeof html2pdf !== 'undefined') {{
                html2pdf().set(opt).from(element).save().then(() => {{
                    showToast("Tải file PDF thành công!", "success");
                }}).catch(err => {{
                    console.error(err);
                    showToast("Đang mở hộp thoại In hệ thống...", "info");
                    window.print();
                }});
            }} else {{
                window.print();
            }}
        }}

        // 2. Xuất Word (.doc / .docx)
        function exportWord() {{
            try {{
                showToast("Đang tạo file Word...", "info");
                const content = document.getElementById("editable_content").innerHTML;
                
                const wordStyles = `
                    <style>
                        body {{ font-family: 'Times New Roman', serif; font-size: 13pt; line-height: 1.5; color: #000000; }}
                        table {{ width: 100%; border-collapse: collapse; margin: 12pt 0; }}
                        table[border="1"], table.bordered, table td, table th {{ border: 1pt solid #000000; padding: 6pt 8pt; }}
                        table[border="0"] td, table[border="0"] th, table.borderless td, table.borderless th {{ border: none; padding: 4pt 6pt; }}
                        p {{ margin: 6pt 0; text-align: justify; }}
                        h1, h2, h3 {{ color: #000000; margin: 12pt 0 6pt 0; }}
                        .highlight, mark {{ background-color: #ffff00; font-weight: bold; }}
                    </style>
                `;

                const wordHtml = `
                    <html xmlns:o='urn:schemas-microsoft-com:office:office' 
                          xmlns:w='urn:schemas-microsoft-com:office:word' 
                          xmlns='http://www.w3.org/TR/REC-html40'>
                    <head>
                        <meta charset='utf-8'>
                        <title>Ket Qua OCR</title>
                        <!--[if gte mso 9]>
                        <xml>
                            <w:WordDocument>
                                <w:View>Print</w:View>
                                <w:Zoom>100</w:Zoom>
                                <w:DoNotOptimizeForBrowser/>
                            </w:WordDocument>
                        </xml>
                        <![endif]-->
                        ${{wordStyles}}
                    </head>
                    <body>
                        ${{content}}
                    </body>
                    </html>
                `;

                const blob = new Blob(['\\ufeff' + wordHtml], {{
                    type: 'application/msword'
                }});

                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Ket_Qua_OCR_' + new Date().toISOString().slice(0, 10) + '.doc';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                setTimeout(() => {{
                    showToast("Xuất file Word thành công!", "success");
                }}, 400);
            }} catch (err) {{
                console.error(err);
                showToast("Lỗi khi tạo file Word: " + err.message, "error");
            }}
        }}

        // 3. Xuất Excel (.xlsx)
        function exportExcel() {{
            try {{
                showToast("Đang tạo file Excel...", "info");
                const container = document.getElementById("editable_content");
                const tables = container.querySelectorAll("table");

                if (typeof XLSX === 'undefined') {{
                    throw new Error("Thư viện SheetJS chưa được nạp");
                }}

                const wb = XLSX.utils.book_new();

                if (tables.length > 0) {{
                    tables.forEach((table, index) => {{
                        const ws = XLSX.utils.table_to_sheet(table);
                        const sheetName = tables.length === 1 ? "Ket_Qua_OCR" : "Bang_" + (index + 1);
                        XLSX.utils.book_append_sheet(wb, ws, sheetName);
                    }});
                }} else {{
                    const textLines = container.innerText.split("\\n").filter(l => l.trim().length > 0);
                    const rows = textLines.map(line => [line]);
                    const ws = XLSX.utils.aoa_to_sheet(rows);
                    ws['!cols'] = [{{ wch: 100 }}];
                    XLSX.utils.book_append_sheet(wb, ws, "Van_Ban_OCR");
                }}

                XLSX.writeFile(wb, 'Ket_Qua_OCR_' + new Date().toISOString().slice(0, 10) + '.xlsx');
                
                setTimeout(() => {{
                    showToast("Xuất file Excel thành công!", "success");
                }}, 400);
            }} catch (err) {{
                console.error(err);
                showToast("Lỗi khi tạo file Excel: " + err.message, "error");
            }}
        }}
    </script>
</body>
</html>
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_template)

            # Open in default browser
            webbrowser.open(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu file", str(e))

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
    window = OCRTab()
    window.setWindowTitle("VieNeu - OCR Ảnh & Tài Liệu")
    window.resize(950, 750)
    window.show()
    sys.exit(app.exec())

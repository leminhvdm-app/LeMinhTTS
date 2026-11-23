"""OCR UI Controller: QML-exposed bridge for OCR features."""

from __future__ import annotations

import logging
import os
import re
import tempfile
import webbrowser

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

from vienetts_app.features.default_prompts import get_default_ocr_prompt
from vienetts_app.features.model_fetcher import DEFAULT_GEMINI_MODELS, ModelFetchWorker
from vienetts_app.features.ocr_tab import OCRWorker

logger = logging.getLogger(__name__)


class OcrController(QObject):
    """QML controller for Image & PDF OCR."""

    apiKeysChanged = Signal()
    saveKeyChanged = Signal()
    selectedFilesChanged = Signal()
    modelNameChanged = Signal()
    availableModelsChanged = Signal()
    isFetchingModelsChanged = Signal()
    translateChanged = Signal()
    isProcessingChanged = Signal()
    statusTextChanged = Signal()
    consoleLogsChanged = Signal()
    htmlResultChanged = Signal()
    hasResultChanged = Signal()
    plainTextChanged = Signal()
    customPromptChanged = Signal()
    saveCustomPromptChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("VieNeu", "OCRTab")
        self._save_key: bool = self._settings.value("save_key_v2", False, type=bool)
        self._api_keys: str = self._settings.value("api_key_v2", "") if self._save_key else ""
        self._save_custom_prompt: bool = self._settings.value(
            "save_custom_prompt_v1", True, type=bool
        )
        saved_custom = str(self._settings.value("custom_prompt_v1", "")).strip() if self._save_custom_prompt else ""
        # Ghi nhớ cứng prompt "OCR_Anh" làm giá trị mặc định chuẩn
        self._custom_prompt: str = saved_custom if saved_custom else get_default_ocr_prompt()
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

        self._is_fetching_models: bool = False
        self._fetcher: ModelFetchWorker | None = None
        self._translate: bool = False
        self._is_processing: bool = False
        self._status_text: str = ""
        self._console_logs: str = ""
        self._html_result: str = ""
        self._plain_text: str = ""
        self._worker: OCRWorker | None = None

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

    @Property(bool, notify=translateChanged)
    def translate(self) -> bool:
        return self._translate

    @translate.setter
    def translate(self, val: bool) -> None:
        if self._translate != val:
            self._translate = val
            self.translateChanged.emit()

    @Property(bool, notify=isProcessingChanged)
    def isProcessing(self) -> bool:
        return self._is_processing

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(str, notify=consoleLogsChanged)
    def consoleLogs(self) -> str:
        return self._console_logs

    @Property(str, notify=htmlResultChanged)
    def htmlResult(self) -> str:
        return self._html_result

    @Property(str, notify=plainTextChanged)
    def plainText(self) -> str:
        return self._plain_text

    @Property(bool, notify=hasResultChanged)
    def hasResult(self) -> bool:
        return bool(self._html_result.strip())

    @Property(str, notify=customPromptChanged)
    def customPrompt(self) -> str:
        return self._custom_prompt

    @customPrompt.setter
    def customPrompt(self, val: str) -> None:
        if self._custom_prompt != val:
            self._custom_prompt = val
            if self._save_custom_prompt:
                self._settings.setValue("custom_prompt_v1", val)
            self.customPromptChanged.emit()

    @Property(bool, notify=saveCustomPromptChanged)
    def saveCustomPrompt(self) -> bool:
        return self._save_custom_prompt

    @saveCustomPrompt.setter
    def saveCustomPrompt(self, val: bool) -> None:
        if self._save_custom_prompt != val:
            self._save_custom_prompt = val
            self._settings.setValue("save_custom_prompt_v1", val)
            if val:
                self._settings.setValue("custom_prompt_v1", self._custom_prompt)
            else:
                self._settings.setValue("custom_prompt_v1", "")
            self.saveCustomPromptChanged.emit()

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

        # Update available models
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

    @Slot(str, result=bool)
    def loadCustomPromptFromFile(self, file_path: str) -> bool:
        """Load custom prompt instructions from a UTF-8 text file."""
        try:
            if not os.path.exists(file_path):
                return False
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if content:
                self.customPrompt = content
                self._console_logs += (
                    f"[+] Đã nạp quy trình/lệnh từ file: {os.path.basename(file_path)}\n"
                )
                self.consoleLogsChanged.emit()
                return True
            return False
        except Exception as e:
            logger.warning("Failed to load custom prompt: %s", e)
            return False

    @Slot()
    def resetToDefaultPrompt(self) -> None:
        """Reset custom prompt to the hardcoded 'OCR_Anh' default."""
        self.customPrompt = get_default_ocr_prompt()
        self._console_logs += "[+] Đã khôi phục quy trình/lệnh gốc chuẩn 'OCR_Anh'.\n"
        self.consoleLogsChanged.emit()

    @Slot()
    def clearCustomPrompt(self) -> None:
        """Clear custom prompt input."""
        self.customPrompt = ""

    @Slot()
    def startOcr(self) -> None:
        if self._is_processing:
            return

        if not self._api_keys.strip():
            self._status_text = "Vui lòng nhập API Key của Google Gemini!"
            self._console_logs += (
                "[-] LỖI: Vui lòng nhập API Key Google Gemini vào mục 1 trước khi bắt đầu OCR.\n"
            )
            self.statusTextChanged.emit()
            self.consoleLogsChanged.emit()
            return

        if not self._selected_files:
            self._status_text = "Vui lòng chọn ít nhất 1 tệp ảnh hoặc PDF!"
            self._console_logs += (
                "[-] LỖI: Chưa chọn tệp nào. "
                "Vui lòng nhấn nút 'Chọn tệp…' ở mục 3 để thêm ảnh hoặc tài liệu PDF.\n"
            )
            self.statusTextChanged.emit()
            self.consoleLogsChanged.emit()
            return

        self._is_processing = True
        self.isProcessingChanged.emit()
        self._console_logs = f"[+] Bắt đầu nhận diện OCR (Model: {self._model_name})...\n"
        if self._custom_prompt and self._custom_prompt.strip():
            self._console_logs += (
                f"[+] Áp dụng quy trình/lệnh tùy chỉnh ({len(self._custom_prompt)} ký tự)\n"
            )
        else:
            self._console_logs += "[+] Sử dụng quy trình nhận diện OCR tiêu chuẩn.\n"
        self.consoleLogsChanged.emit()
        self._status_text = "Đang xử lý..."
        self.statusTextChanged.emit()

        self._worker = OCRWorker(
            api_keys=self._api_keys,
            file_paths=self._selected_files,
            model_name=self._model_name,
            translate=self._translate,
            custom_prompt=self._custom_prompt,
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

    def _on_finished(self, html_output: str) -> None:
        self._is_processing = False
        self._html_result = html_output
        # Strip HTML tags for plain text representation
        clean_text = re.sub(r"<[^>]+>", " ", html_output)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        self._plain_text = clean_text

        self._status_text = "Hoàn tất nhận diện! Đang mở file HTML..."
        self._console_logs += "\n=== NHẬN DIỆN THÀNH CÔNG - ĐANG MỞ TRÌNH DUYỆT ĐỂ CHỈNH SỬA & XUẤT FILE ===\n"

        self.isProcessingChanged.emit()
        self.htmlResultChanged.emit()
        self.plainTextChanged.emit()
        self.hasResultChanged.emit()
        self.statusTextChanged.emit()
        self.consoleLogsChanged.emit()

        # Tự động mở trực tiếp file HTML trên trình duyệt để chỉnh sửa & xuất file
        try:
            self.openInBrowser()
        except Exception as e:
            logger.warning("Auto open HTML failed: %s", e)

    def _on_error(self, err_msg: str) -> None:
        self._is_processing = False
        self._status_text = f"Lỗi: {err_msg}"
        self._console_logs += f"\n[-] LỖI: {err_msg}\n"
        self.isProcessingChanged.emit()
        self.statusTextChanged.emit()
        self.consoleLogsChanged.emit()

    @Slot()
    def openInBrowser(self) -> None:
        if not self._html_result:
            return
        try:
            import time
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            out_file = os.path.join(temp_dir, f"Ket_Qua_OCR_{timestamp}.html")

            # Xử lý nội dung an toàn khi nhúng vào template JavaScript
            raw_content = self._html_result

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

        /* Document Container (Standard A4 Page Feeling) */
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
        {raw_content}
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toastMsg">
        <i class="fa-solid fa-circle-check"></i>
        <span id="toastText">Thao tác thành công!</span>
    </div>

    <!-- Exporters Logic -->
    <script>
        // Lưu trữ bản gốc để khôi phục khi cần
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
                    // Nếu tài liệu không có table, chuyển các dòng văn bản thành các hàng trong Excel
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
</html>"""
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(html_template)
            webbrowser.open(out_file)
        except Exception as e:
            logger.warning("Failed to open HTML in browser: %s", e)

    @Slot(str, result=bool)
    def exportHtml(self, path: str) -> bool:
        if not self._html_result or not path:
            return False
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._html_result)
            return True
        except Exception as e:
            logger.warning("Failed to export HTML: %s", e)
            return False

    @Slot(str, result=bool)
    def exportDocx(self, path: str) -> bool:
        if not self._plain_text or not path:
            return False
        try:
            import docx

            doc = docx.Document()
            for line in self._plain_text.splitlines():
                if line.strip():
                    doc.add_paragraph(line)
            doc.save(path)
            return True
        except Exception as e:
            logger.warning("Failed to export DOCX: %s", e)
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



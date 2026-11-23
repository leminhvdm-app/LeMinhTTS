// OCR Image & PDF tab using Google Gemini AI
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."
import "components"

Pane {
    id: root

    objectName: "ocrTab"
    padding: Theme.spacingLg

    background: Rectangle {
        color: Theme.bg
    }

    function toLocalPath(url) {
        const s = url.toString();
        if (!s.startsWith("file://"))
            return s;
        let path = decodeURIComponent(s.substring(7));
        if (/^\/[A-Za-z]:\//.test(path))
            path = path.substring(1);
        return path;
    }

    FileDialog {
        id: filePicker
        title: qsTr("Chọn ảnh hoặc tài liệu quét OCR")
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            qsTr("Tất cả định dạng hỗ trợ (*.png *.jpg *.jpeg *.jfif *.webp *.bmp *.tif *.tiff *.gif *.ico *.pdf *.xps *.oxps *.epub *.mobi *.fb2 *.cbz *.svg *.txt *.md *.docx)"),
            qsTr("Tệp hình ảnh (*.png *.jpg *.jpeg *.jfif *.webp *.bmp *.tif *.tiff *.gif *.ico *.svg *.tga *.ppm *.pgm *.pbm)"),
            qsTr("Tài liệu PDF (*.pdf)"),
            qsTr("Sách điện tử & XPS (*.epub *.mobi *.fb2 *.cbz *.xps *.oxps)"),
            qsTr("Tài liệu văn bản & Word (*.txt *.md *.csv *.json *.log *.docx)"),
            qsTr("Tất cả các tệp (*.*)")
        ]
        onAccepted: {
            for (let i = 0; i < selectedFiles.length; i++) {
                ocrController.addFile(root.toLocalPath(selectedFiles[i]));
            }
        }
    }

    FileDialog {
        id: keyFilePicker
        title: qsTr("Chọn tệp TXT chứa API Keys")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Tệp văn bản (*.txt)"]
        onAccepted: {
            ocrController.loadKeysFromFile(root.toLocalPath(selectedFile));
        }
    }

    FileDialog {
        id: promptFilePicker
        title: qsTr("Chọn tệp TXT chứa quy trình / lệnh OCR")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Tệp văn bản (*.txt)"]
        onAccepted: {
            ocrController.loadCustomPromptFromFile(root.toLocalPath(selectedFile));
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingLg

            PageHeader {
                title: qsTr("Nhận diện OCR Ảnh & PDF")
                subtitle: qsTr("Trích xuất văn bản từ Ảnh và tài liệu PDF bằng Google Gemini AI, giữ nguyên cấu trúc bảng biểu.")
            }

            // --- Cấu hình API & Model ---
            AppCard {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel {
                        text: qsTr("1. Cấu hình Google Gemini API")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        TextField {
                            id: apiKeyField
                            Layout.fillWidth: true
                            text: ocrController.apiKeys
                            placeholderText: qsTr("Nhập các Gemini API Key (ngăn cách bằng dấu phẩy)...")
                            echoMode: showKeyToggle.checked ? TextInput.Normal : TextInput.Password
                            onTextChanged: ocrController.apiKeys = text
                            color: Theme.text
                            placeholderTextColor: Theme.textMuted
                            background: Rectangle {
                                radius: Theme.radiusMd
                                color: Theme.surfaceAlt
                                border.color: apiKeyField.activeFocus ? Theme.borderFocus : Theme.border
                                border.width: 1
                            }
                        }

                        AppIconButton {
                            id: showKeyToggle
                            checkable: true
                            iconKind: checked ? "eye" : "close"
                            tooltipText: checked ? qsTr("Ẩn API Key") : qsTr("Hiện API Key")
                        }

                        AppButton {
                            text: qsTr("Nhập từ TXT")
                            iconKind: "file"
                            variant: "secondary"
                            size: "md"
                            onClicked: keyFilePicker.open()
                        }

                        AppToggle {
                            checked: ocrController.saveKey
                            text: qsTr("Lưu Key")
                            onToggled: ocrController.saveKey = checked
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        RowLayout {
                            spacing: Theme.spacingSm
                            Label {
                                text: qsTr("Mô hình AI:")
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                            }

                            AppCombo {
                                id: modelCombo
                                comboWidth: 220
                                model: ocrController.availableModels
                                currentIndex: Math.max(0, ocrController.availableModels.indexOf(ocrController.modelName))
                                onCurrentTextChanged: if (currentText) ocrController.modelName = currentText
                            }

                            AppButton {
                                text: qsTr("Cập nhật Model")
                                iconKind: "refresh"
                                variant: "secondary"
                                size: "sm"
                                busy: ocrController.isFetchingModels
                                enabled: !ocrController.isFetchingModels
                                tooltipText: qsTr("Kết nối Google Gemini API để quét và cập nhật danh sách model mới nhất")
                                onClicked: ocrController.refreshModelsFromApi()
                            }
                        }

                        AppToggle {
                            checked: ocrController.translate
                            text: qsTr("Dịch kết quả sang Tiếng Việt")
                            onToggled: ocrController.translate = checked
                        }
                    }
                }
            }

            // --- Quy trình / Lệnh bổ sung (Nhập tay hoặc chèn file .txt) ---
            AppCard {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        SectionLabel {
                            text: qsTr("2. Quy trình / Lệnh bổ sung (Tăng độ chính xác)")
                        }

                        Item { Layout.fillWidth: true }

                        AppButton {
                            text: qsTr("Chèn từ file .txt")
                            iconKind: "file"
                            variant: "secondary"
                            size: "sm"
                            tooltipText: qsTr("Đọc nội dung tệp .txt và đưa vào khung lệnh bên dưới")
                            onClicked: promptFilePicker.open()
                        }

                        AppButton {
                            text: qsTr("Lệnh gốc (OCR_Anh)")
                            iconKind: "refresh"
                            variant: "secondary"
                            size: "sm"
                            tooltipText: qsTr("Khôi phục lại quy trình lệnh gốc chuẩn OCR_Anh")
                            onClicked: ocrController.resetToDefaultPrompt()
                        }

                        AppButton {
                            text: qsTr("Xóa lệnh")
                            iconKind: "close"
                            variant: "quiet"
                            size: "sm"
                            visible: ocrController.customPrompt.trim() !== ""
                            tooltipText: qsTr("Xóa nội dung lệnh đã nhập")
                            onClicked: ocrController.clearCustomPrompt()
                        }

                        AppToggle {
                            checked: ocrController.saveCustomPrompt
                            text: qsTr("Ghi nhớ lệnh")
                            onToggled: ocrController.saveCustomPrompt = checked
                        }
                    }

                    ScrollView {
                        id: customPromptScroll
                        Layout.fillWidth: true
                        Layout.minimumHeight: 120
                        Layout.preferredHeight: 160
                        clip: true

                        ScrollBar.vertical: ScrollBar {
                            parent: customPromptScroll
                            x: customPromptScroll.mirrored ? 0 : customPromptScroll.width - width
                            y: customPromptScroll.topPadding
                            height: customPromptScroll.availableHeight
                            active: true
                            policy: ScrollBar.AlwaysOn
                            implicitWidth: 10
                            contentItem: Rectangle {
                                radius: 5
                                color: Theme.accent
                                opacity: 0.7
                            }
                            background: Rectangle {
                                radius: 5
                                color: Theme.surfaceAlt
                                opacity: 0.3
                            }
                        }

                        TextArea {
                            id: customPromptArea
                            width: customPromptScroll.availableWidth - 14
                            text: ocrController.customPrompt
                            placeholderText: qsTr("Nhập tay quy trình xử lý, yêu cầu đặc biệt, từ vựng chuyên ngành, ngữ cảnh tài liệu... hoặc bấm 'Chèn từ file .txt' ở trên để AI ưu tiên thực hiện...")
                            onTextChanged: ocrController.customPrompt = text
                            wrapMode: Text.Wrap
                            selectByMouse: true
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            background: Rectangle {
                                radius: Theme.radiusMd
                                color: Theme.surfaceAlt
                                border.color: customPromptArea.activeFocus ? Theme.borderFocus : Theme.border
                                border.width: 1
                            }
                        }
                    }
                }
            }

            // --- Danh sách tệp tin ---
            AppCard {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        SectionLabel {
                            text: qsTr("3. Danh sách tệp cần quét (%1 tệp)").arg(ocrController.fileCount)
                        }
                        Item { Layout.fillWidth: true }
                        AppButton {
                            text: qsTr("Chọn tệp…")
                            iconKind: "upload"
                            size: "md"
                            onClicked: filePicker.open()
                        }
                        AppButton {
                            text: qsTr("Xóa tất cả")
                            variant: "quiet"
                            size: "md"
                            visible: ocrController.fileCount > 0
                            onClicked: ocrController.clearFiles()
                        }
                    }

                    // Danh sách file chip
                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm
                        visible: ocrController.fileCount > 0

                        Repeater {
                            model: ocrController.selectedFiles
                            delegate: Rectangle {
                                radius: Theme.radiusPill
                                color: Theme.surfaceAlt
                                border.color: Theme.border
                                border.width: 1
                                height: 32
                                width: fileChipRow.implicitWidth + Theme.spacingMd * 2

                                RowLayout {
                                    id: fileChipRow
                                    anchors.centerIn: parent
                                    spacing: Theme.spacingSm

                                    AppIcon {
                                        kind: "file"
                                        iconColor: Theme.accent
                                        width: 14
                                        height: 14
                                    }

                                    Label {
                                        text: {
                                            const parts = modelData.split(/[\\/]/);
                                            return parts[parts.length - 1];
                                        }
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        elide: Text.ElideMiddle
                                        Layout.maximumWidth: 200
                                    }

                                    AppIconButton {
                                        iconKind: "close"
                                        width: 20
                                        height: 20
                                        onClicked: ocrController.removeFileAt(index)
                                    }
                                }
                            }
                        }
                    }

                    Label {
                        visible: ocrController.fileCount === 0
                        text: qsTr("Chưa chọn tệp ảnh hoặc tài liệu nào. Nhấn nút 'Chọn tệp…' ở trên.")
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                    }
                }
            }

            // --- Nút hành động ---
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingMd

                Button {
                    id: startOcrBtn
                    objectName: "startOcrBtn"
                    implicitHeight: 44
                    implicitWidth: Math.max(220, contentLayout.implicitWidth + 32)
                    enabled: !ocrController.isProcessing

                    background: Rectangle {
                        radius: Theme.radiusMd
                        color: ocrController.isProcessing
                            ? "#dc2626"
                            : (startOcrBtn.down ? Theme.accentHover : (startOcrBtn.hovered ? Theme.accentHover : Theme.accent))
                        border.color: ocrController.isProcessing ? "#b91c1c" : "transparent"
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
                    }

                    contentItem: RowLayout {
                        id: contentLayout
                        spacing: Theme.spacingSm
                        anchors.centerIn: parent

                        AppIcon {
                            id: btnIcon
                            kind: ocrController.isProcessing ? "spinner" : "ocr"
                            iconColor: "#ffffff"
                            Layout.preferredWidth: 18
                            Layout.preferredHeight: 18

                            RotationAnimation on rotation {
                                running: ocrController.isProcessing
                                loops: Animation.Infinite
                                from: 0
                                to: 360
                                duration: 800
                            }
                        }

                        Label {
                            text: ocrController.isProcessing ? qsTr("Đang nhận diện...") : qsTr("Bắt đầu nhận diện OCR")
                            color: "#ffffff"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeBase
                            font.weight: Theme.fontWeightHeading
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    onClicked: {
                        ocrController.startOcr();
                    }
                }

                Label {
                    text: ocrController.statusText
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeSm
                    Layout.fillWidth: true
                }
            }

            // --- Kết quả & Thao tác ---
            AppCard {
                Layout.fillWidth: true
                visible: ocrController.consoleLogs !== "" || ocrController.hasResult

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        SectionLabel {
                            text: qsTr("4. Kết quả & Thao tác")
                        }
                        Item { Layout.fillWidth: true }

                        AppButton {
                            text: qsTr("Mở HTML (Chỉnh sửa & Xuất PDF/Word/Excel)")
                            iconKind: "externalLink"
                            variant: "secondary"
                            size: "sm"
                            visible: ocrController.hasResult
                            onClicked: ocrController.openInBrowser()
                        }

                        AppButton {
                            text: qsTr("Đọc bằng TTS ▶")
                            iconKind: "text"
                            variant: "primary"
                            size: "sm"
                            visible: ocrController.hasResult
                            onClicked: {
                                if (ocrController.plainText) {
                                    bridge.sendToTts(ocrController.plainText, "text");
                                }
                            }
                        }
                    }

                    ScrollView {
                        id: consoleScroll
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        clip: true

                        ScrollBar.vertical: ScrollBar {
                            parent: consoleScroll
                            x: consoleScroll.mirrored ? 0 : consoleScroll.width - width
                            y: consoleScroll.topPadding
                            height: consoleScroll.availableHeight
                            active: true
                            policy: ScrollBar.AsNeeded
                            implicitWidth: 10
                            contentItem: Rectangle {
                                radius: 5
                                color: Theme.accent
                                opacity: 0.7
                            }
                            background: Rectangle {
                                radius: 5
                                color: Theme.surfaceCardAlt
                                opacity: 0.3
                            }
                        }

                        TextArea {
                            id: consoleArea
                            width: consoleScroll.availableWidth - 14
                            readOnly: true
                            text: ocrController.hasResult ? ocrController.plainText : ocrController.consoleLogs
                            wrapMode: Text.Wrap
                            selectByMouse: true
                            color: Theme.text
                            font.family: "Consolas, monospace"
                            font.pixelSize: Theme.fontSizeSm
                            background: Rectangle {
                                radius: Theme.radiusMd
                                color: Theme.surfaceCardAlt
                                border.color: Theme.border
                                border.width: 1
                            }
                        }
                    }
                }
            }
        }
    }
}

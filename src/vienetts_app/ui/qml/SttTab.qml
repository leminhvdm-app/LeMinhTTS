// Speech-to-Text tab using Google Gemini AI
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."
import "components"

Pane {
    id: root

    objectName: "sttTab"
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
        title: qsTr("Chọn tệp âm thanh hoặc video")
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "Tệp đa phương tiện (*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts)",
            "Tệp âm thanh (*.wav *.mp3 *.m4a *.flac *.ogg *.aac)",
            "Tệp video (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts)",
            "Tất cả các tệp (*)"
        ]
        onAccepted: {
            for (let i = 0; i < selectedFiles.length; i++) {
                sttController.addFile(root.toLocalPath(selectedFiles[i]));
            }
        }
    }

    FileDialog {
        id: keyFilePicker
        title: qsTr("Chọn tệp TXT chứa API Keys")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Tệp văn bản (*.txt)"]
        onAccepted: {
            sttController.loadKeysFromFile(root.toLocalPath(selectedFile));
        }
    }

    FileDialog {
        id: saveDocxDialog
        title: qsTr("Lưu file Word")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "docx"
        nameFilters: ["Tài liệu Word (*.docx)"]
        onAccepted: {
            sttController.exportDocx(root.toLocalPath(selectedFile));
        }
    }

    FileDialog {
        id: saveTxtDialog
        title: qsTr("Lưu file Text")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["Tệp văn bản (*.txt)"]
        onAccepted: {
            sttController.exportText(root.toLocalPath(selectedFile));
        }
    }

    FileDialog {
        id: saveSrtDialog
        title: qsTr("Lưu file Phụ đề SRT")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "srt"
        nameFilters: ["Tệp phụ đề (*.srt)"]
        onAccepted: {
            sttController.exportSrt(root.toLocalPath(selectedFile));
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingLg

            PageHeader {
                title: qsTr("Giọng nói → Văn bản (Speech-to-Text)")
                subtitle: qsTr("Chuyển đổi âm thanh & video thành văn bản chính xác cao, chuẩn hóa dấu câu và ngữ pháp qua Google Gemini AI.")
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
                            text: sttController.apiKeys
                            placeholderText: qsTr("Nhập các Gemini API Key (ngăn cách bằng dấu phẩy)...")
                            echoMode: showKeyToggle.checked ? TextInput.Normal : TextInput.Password
                            onTextChanged: sttController.apiKeys = text
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
                            checked: sttController.saveKey
                            text: qsTr("Lưu Key")
                            onToggled: sttController.saveKey = checked
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
                                model: sttController.availableModels
                                currentIndex: Math.max(0, sttController.availableModels.indexOf(sttController.modelName))
                                onCurrentTextChanged: if (currentText) sttController.modelName = currentText
                            }

                            AppButton {
                                text: qsTr("Cập nhật Model")
                                iconKind: "refresh"
                                variant: "secondary"
                                size: "sm"
                                busy: sttController.isFetchingModels
                                enabled: !sttController.isFetchingModels
                                tooltipText: qsTr("Kết nối Google Gemini API để quét và cập nhật danh sách model mới nhất")
                                onClicked: sttController.refreshModelsFromApi()
                            }
                        }

                        RowLayout {
                            spacing: Theme.spacingSm
                            Label {
                                text: qsTr("Chế độ nhận diện (Reup phim):")
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                            }

                            AppCombo {
                                id: modeCombo
                                comboWidth: 270
                                model: [
                                    qsTr("Kịch bản đọc (Lời thoại thuần)"),
                                    qsTr("Kèm mốc thời gian (Timestamps/SRT)")
                                ]
                                currentIndex: sttController.outputMode === "timestamp" ? 1 : 0
                                onCurrentIndexChanged: {
                                    sttController.outputMode = (currentIndex === 1 ? "timestamp" : "plain");
                                }
                            }
                        }
                    }
                }
            }

            // --- Danh sách tệp tin âm thanh / video ---
            AppCard {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        SectionLabel {
                            text: qsTr("2. Danh sách tệp âm thanh & video cần nhận diện (%1 tệp)").arg(sttController.fileCount)
                        }
                        Item { Layout.fillWidth: true }
                        AppButton {
                            text: qsTr("Chọn file (Audio / Video)…")
                            iconKind: "upload"
                            size: "md"
                            onClicked: filePicker.open()
                        }
                        AppButton {
                            text: qsTr("Xóa tất cả")
                            variant: "quiet"
                            size: "md"
                            visible: sttController.fileCount > 0
                            onClicked: sttController.clearFiles()
                        }
                    }

                    // Nhập link video trực tiếp
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        TextField {
                            id: videoUrlField
                            Layout.fillWidth: true
                            text: sttController.videoUrls
                            placeholderText: qsTr("Dán đường dẫn video (YouTube, TikTok, Facebook... mỗi link một dòng hoặc cách nhau khoảng trắng)...")
                            onTextChanged: sttController.videoUrls = text
                            color: Theme.text
                            placeholderTextColor: Theme.textMuted
                            background: Rectangle {
                                radius: Theme.radiusMd
                                color: Theme.surfaceAlt
                                border.color: videoUrlField.activeFocus ? Theme.borderFocus : Theme.border
                                border.width: 1
                            }
                        }

                        AppButton {
                            text: sttController.isDownloading ? qsTr("Đang tải...") : qsTr("Tải từ Link")
                            iconKind: "download"
                            variant: "secondary"
                            size: "md"
                            busy: sttController.isDownloading
                            enabled: !sttController.isDownloading && sttController.videoUrls.trim() !== ""
                            tooltipText: qsTr("Tự động tải luồng âm thanh từ các link video trên và thêm vào hàng đợi nhận diện")
                            onClicked: sttController.downloadLinks()
                        }
                    }

                    // Danh sách file chip
                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm
                        visible: sttController.fileCount > 0

                        Repeater {
                            model: sttController.selectedFiles
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
                                        kind: sttController.isVideoFile(modelData) ? "video" : "wave"
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
                                        onClicked: sttController.removeFileAt(index)
                                    }
                                }
                            }
                        }
                    }

                    Label {
                        visible: sttController.fileCount === 0
                        text: qsTr("Chưa chọn tệp nào. Bạn có thể nhấn nút 'Chọn file (Audio / Video)…' (Hỗ trợ MP3, WAV, M4A, MP4, MKV, AVI...) hoặc dán link video ở trên.")
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
                    id: startSttBtn
                    objectName: "startSttBtn"
                    implicitHeight: 44
                    implicitWidth: Math.max(220, contentLayout.implicitWidth + 32)
                    enabled: sttController.isProcessing || (sttController.fileCount > 0 && sttController.apiKeys.trim() !== "")

                    background: Rectangle {
                        radius: Theme.radiusMd
                        color: sttController.isProcessing
                            ? "#dc2626"
                            : (startSttBtn.enabled
                                ? (startSttBtn.down ? Theme.accentHover : (startSttBtn.hovered ? Theme.accentHover : Theme.accent))
                                : Theme.controlDisabledBg)
                        border.color: sttController.isProcessing ? "#b91c1c" : (startSttBtn.enabled ? "transparent" : Theme.controlDisabledBorder)
                        border.width: startSttBtn.enabled ? 0 : 1

                        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
                    }

                    contentItem: RowLayout {
                        id: contentLayout
                        spacing: Theme.spacingSm
                        anchors.centerIn: parent

                        AppIcon {
                            id: btnIcon
                            kind: sttController.isProcessing ? "spinner" : "stt"
                            iconColor: sttController.isProcessing ? "#ffffff" : (startSttBtn.enabled ? Theme.accentText : Theme.controlDisabledText)
                            Layout.preferredWidth: 18
                            Layout.preferredHeight: 18

                            RotationAnimation on rotation {
                                running: sttController.isProcessing
                                loops: Animation.Infinite
                                from: 0
                                to: 360
                                duration: 800
                            }
                        }

                        Label {
                            text: sttController.isProcessing ? qsTr("Đang nhận diện giọng nói...") : qsTr("Bắt đầu nhận diện giọng nói")
                            color: sttController.isProcessing ? "#ffffff" : (startSttBtn.enabled ? Theme.accentText : Theme.controlDisabledText)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeBase
                            font.weight: Theme.fontWeightHeading
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    HoverHandler {
                        cursorShape: startSttBtn.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    }

                    onClicked: {
                        if (!sttController.isProcessing) {
                            sttController.startStt();
                        }
                    }
                }

                Label {
                    text: sttController.statusText
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeSm
                    Layout.fillWidth: true
                }
            }

            // --- Kết quả & Thao tác ---
            AppCard {
                Layout.fillWidth: true
                visible: sttController.consoleLogs !== "" || sttController.hasResult

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        SectionLabel {
                            text: qsTr("3. Kết quả văn bản")
                        }
                        Item { Layout.fillWidth: true }

                        AppButton {
                            text: qsTr("Xuất Phụ đề (.srt)")
                            iconKind: "download"
                            variant: "secondary"
                            size: "sm"
                            visible: sttController.hasResult
                            onClicked: saveSrtDialog.open()
                        }

                        AppButton {
                            text: qsTr("Xuất Word (.docx)")
                            iconKind: "download"
                            variant: "secondary"
                            size: "sm"
                            visible: sttController.hasResult
                            onClicked: saveDocxDialog.open()
                        }

                        AppButton {
                            text: qsTr("Xuất Text (.txt)")
                            iconKind: "download"
                            variant: "secondary"
                            size: "sm"
                            visible: sttController.hasResult
                            onClicked: saveTxtDialog.open()
                        }

                        AppButton {
                            text: qsTr("Đọc bằng TTS ▶")
                            iconKind: "text"
                            variant: "primary"
                            size: "sm"
                            visible: sttController.hasResult
                            onClicked: {
                                if (sttController.recognizedText) {
                                    bridge.sendToTts(sttController.recognizedText, "text");
                                }
                            }
                        }
                    }

                    ScrollView {
                        id: textResultScroll
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        clip: true

                        ScrollBar.vertical: ScrollBar {
                            parent: textResultScroll
                            x: textResultScroll.mirrored ? 0 : textResultScroll.width - width
                            y: textResultScroll.topPadding
                            height: textResultScroll.availableHeight
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
                                color: Theme.surfaceCardAlt
                                opacity: 0.3
                            }
                        }

                        TextArea {
                            id: textResultArea
                            width: textResultScroll.availableWidth - 14
                            readOnly: false
                            text: sttController.hasResult ? sttController.recognizedText : sttController.consoleLogs
                            onTextChanged: {
                                if (sttController.hasResult) {
                                    sttController.recognizedText = text;
                                } else {
                                    cursorPosition = text.length;
                                }
                            }
                            wrapMode: Text.Wrap
                            selectByMouse: true
                            color: Theme.text
                            font.family: sttController.hasResult ? Theme.fontFamily : "Consolas, monospace"
                            font.pixelSize: Theme.fontSizeBase
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

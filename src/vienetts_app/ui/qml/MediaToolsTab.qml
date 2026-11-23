// Media Processing Studio: Split, Merge, Convert, Bypass, and Download tools.
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."
import "components"

Pane {
    id: root

    objectName: "mediaToolsTab"
    padding: Theme.spacingLg

    background: Rectangle {
        color: Theme.bg
    }

    function toLocalPath(url) {
        if (!url) return "";
        const s = url.toString();
        if (!s.startsWith("file://"))
            return s;
        let path = decodeURIComponent(s.substring(7));
        if (/^\/[A-Za-z]:\//.test(path))
            path = path.substring(1);
        return path;
    }

    // --- Dialogs ---
    // 1. Split Video Dialogs
    FileDialog {
        id: splitVideoInDialog
        title: qsTr("Chọn Video cần chia")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.webm)", "Tất cả các tệp (*)"]
        onAccepted: mediaController.splitVideoInput = root.toLocalPath(selectedFile)
    }

    FolderDialog {
        id: splitVideoOutDialog
        title: qsTr("Chọn thư mục lưu video đã chia")
        onAccepted: mediaController.splitVideoOutput = root.toLocalPath(selectedFolder)
    }

    // 2. Split MP3 Dialogs
    FileDialog {
        id: splitMp3InDialog
        title: qsTr("Chọn file Âm thanh cần chia")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Audio Files (*.mp3 *.wav *.aac *.m4a *.flac *.ogg)", "Tất cả các tệp (*)"]
        onAccepted: mediaController.splitMp3Input = root.toLocalPath(selectedFile)
    }

    FolderDialog {
        id: splitMp3OutDialog
        title: qsTr("Chọn thư mục lưu file âm thanh đã chia")
        onAccepted: mediaController.splitMp3Output = root.toLocalPath(selectedFolder)
    }

    // 3. Merge Video Dialogs
    FileDialog {
        id: mergeAddFilesDialog
        title: qsTr("Chọn các video cần ghép nối")
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Video Files (*.mp4 *.avi *.mkv *.mov *.webm)", "Tất cả các tệp (*)"]
        onAccepted: {
            var arr = [];
            for (var i = 0; i < selectedFiles.length; i++) {
                arr.push(root.toLocalPath(selectedFiles[i]));
            }
            mediaController.addMergeFiles(arr);
        }
    }

    FileDialog {
        id: mergeOutDialog
        title: qsTr("Chọn nơi lưu video sau khi ghép")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "mp4"
        nameFilters: ["MP4 Video (*.mp4)"]
        onAccepted: mediaController.mergeOutput = root.toLocalPath(selectedFile)
    }

    FileDialog {
        id: mergeLogoDialog
        title: qsTr("Chọn ảnh Logo (Watermark)")
        fileMode: FileDialog.OpenFile
        nameFilters: ["PNG Images (*.png *.jpg *.jpeg)"]
        onAccepted: mediaController.mergeLogoPath = root.toLocalPath(selectedFile)
    }

    FileDialog {
        id: mergeSubDialog
        title: qsTr("Chọn file phụ đề (Hardsub)")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Subtitles (*.srt *.ass *.vtt)"]
        onAccepted: mediaController.mergeSubtitlePath = root.toLocalPath(selectedFile)
    }

    // 4. Convert Audio Dialogs
    FileDialog {
        id: convertAddFilesDialog
        title: qsTr("Chọn tệp Video / Audio cần chuyển đổi")
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Media Files (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.flac *.aac *.ogg *.m4a *.webm)", "Tất cả các tệp (*)"]
        onAccepted: {
            var arr = [];
            for (var i = 0; i < selectedFiles.length; i++) {
                arr.push(root.toLocalPath(selectedFiles[i]));
            }
            mediaController.addConvertFiles(arr);
        }
    }

    FolderDialog {
        id: convertOutDialog
        title: qsTr("Chọn thư mục lưu file Audio đầu ra")
        onAccepted: mediaController.convertOutput = root.toLocalPath(selectedFolder)
    }

    // 5. Bypass Dialogs
    FileDialog {
        id: bypassInDialog
        title: qsTr("Chọn Video cần lách bản quyền")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Video Files (*.mp4 *.avi *.mkv *.mov *.webm)", "Tất cả các tệp (*)"]
        onAccepted: mediaController.bypassInput = root.toLocalPath(selectedFile)
    }

    FileDialog {
        id: bypassOutDialog
        title: qsTr("Chọn nơi lưu video xuất ra")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "mp4"
        nameFilters: ["MP4 Video (*.mp4)"]
        onAccepted: mediaController.bypassOutput = root.toLocalPath(selectedFile)
    }

    // 6. Download Dialogs
    FolderDialog {
        id: downloadOutDialog
        title: qsTr("Chọn thư mục lưu video tải về")
        onAccepted: mediaController.downloadOutput = root.toLocalPath(selectedFolder)
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingLg

            // --- Header ---
            PageHeader {
                title: qsTr("Xử lý Media & Video Tools")
                subtitle: qsTr("Bộ công cụ chuyên nghiệp: Cắt, Ghép, Chuyển đổi định dạng, Lách bản quyền và Tải video đa nền tảng.")
            }

            // --- Sub-navigation Tabs Bar ---
            Rectangle {
                Layout.fillWidth: true
                height: 44
                color: Theme.surface
                radius: Theme.radiusMd
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 4

                    Repeater {
                        model: [
                            { id: "split_video", label: qsTr("✂️ Chia Video") },
                            { id: "split_mp3", label: qsTr("🎵 Chia MP3") },
                            { id: "merge", label: qsTr("🔗 Ghép Video") },
                            { id: "convert", label: qsTr("🔄 Chuyển Đổi Audio") },
                            { id: "bypass", label: qsTr("🛡️ Lách Bản Quyền") },
                            { id: "download", label: qsTr("📥 Tải Video") }
                        ]

                        Button {
                            id: subNavBtn
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            flat: true
                            checked: mediaController ? mediaController.subTab === modelData.id : false
                            onClicked: if (mediaController) mediaController.setSubTab(modelData.id)

                            HoverHandler { cursorShape: Qt.PointingHandCursor }

                            contentItem: Label {
                                text: subNavBtn.modelData.label
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: subNavBtn.checked ? Theme.fontWeightBold : Theme.fontWeightNormal
                                color: subNavBtn.checked ? Theme.accent : (subNavBtn.hovered ? Theme.text : Theme.textMuted)
                            }

                            background: Rectangle {
                                radius: Theme.radiusSm
                                color: subNavBtn.checked ? Theme.accentSubtle : (subNavBtn.hovered ? Theme.surfaceHover : "transparent")
                                border.width: subNavBtn.checked ? 1 : 0
                                border.color: Theme.borderFocus
                                Behavior on color { ColorAnimation { duration: Theme.durationFast } }
                            }
                        }
                    }
                }
            }

            // =============================================================
            // TAB 1: CHIA VIDEO
            // =============================================================
            AppCard {
                Layout.fillWidth: true
                visible: mediaController ? mediaController.subTab === "split_video" : false

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel { text: qsTr("📁 1. Chọn Video & Thư mục lưu đầu ra") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Video...")
                            iconKind: "video"
                            size: "md"
                            onClicked: splitVideoInDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.splitVideoInput) ? mediaController.splitVideoInput : qsTr("Chưa chọn file nào")
                            color: (mediaController && mediaController.splitVideoInput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Thư mục lưu...")
                            iconKind: "folder"
                            size: "md"
                            onClicked: splitVideoOutDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.splitVideoOutput) ? mediaController.splitVideoOutput : qsTr("Chưa chọn thư mục nào")
                            color: (mediaController && mediaController.splitVideoOutput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("⏳ 2. Tùy chọn chia video") }

                    // Option 1 & 2
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.spacingLg
                        rowSpacing: Theme.spacingMd

                        // Fixed length
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label {
                                    text: qsTr("Chia theo độ dài cố định (giây)")
                                    font.weight: Theme.fontWeightBold
                                    color: Theme.text
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    TextField {
                                        id: splitVidLenField
                                        Layout.fillWidth: true
                                        text: mediaController ? String(mediaController.splitVideoLength) : "120"
                                        placeholderText: "120"
                                        onTextChanged: if (mediaController) mediaController.splitVideoLength = parseInt(text) || 120
                                    }

                                    AppButton {
                                        text: qsTr("Chia theo độ dài")
                                        variant: "primary"
                                        enabled: mediaController && !mediaController.isProcessing
                                        onClicked: if (mediaController) mediaController.startSplitVideoByLength()
                                    }
                                }
                            }
                        }

                        // Equal parts
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label {
                                    text: qsTr("Chia thành số phần bằng nhau")
                                    font.weight: Theme.fontWeightBold
                                    color: Theme.text
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    TextField {
                                        id: splitVidPartsField
                                        Layout.fillWidth: true
                                        text: mediaController ? String(mediaController.splitVideoParts) : "6"
                                        placeholderText: "6"
                                        onTextChanged: if (mediaController) mediaController.splitVideoParts = parseInt(text) || 6
                                    }

                                    AppButton {
                                        text: qsTr("Chia theo số phần")
                                        variant: "primary"
                                        enabled: mediaController && !mediaController.isProcessing
                                        onClicked: if (mediaController) mediaController.startSplitVideoByParts()
                                    }
                                }
                            }
                        }
                    }

                    // Option 3: Custom timestamps
                    Rectangle {
                        Layout.fillWidth: true
                        radius: Theme.radiusMd
                        color: Theme.surfaceAlt
                        border.color: Theme.borderSubtle
                        border.width: 1
                        implicitHeight: customVidCol.implicitHeight + Theme.spacingMd * 2

                        ColumnLayout {
                            id: customVidCol
                            anchors.fill: parent
                            anchors.margins: Theme.spacingMd
                            spacing: Theme.spacingSm

                            Label {
                                text: qsTr("🕒 Chia Video theo mốc thời gian tuỳ biến")
                                font.weight: Theme.fontWeightBold
                                color: Theme.text
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacingSm

                                TextField {
                                    id: vidTimeStart
                                    placeholderText: qsTr("Bắt đầu (vd: 00:01:00 hoặc 60s)")
                                    Layout.fillWidth: true
                                }
                                TextField {
                                    id: vidTimeEnd
                                    placeholderText: qsTr("Kết thúc (vd: 00:03:30 hoặc 210s)")
                                    Layout.fillWidth: true
                                }
                                AppButton {
                                    text: qsTr("+ Thêm đoạn")
                                    variant: "accent"
                                    onClicked: {
                                        if (vidTimeStart.text && vidTimeEnd.text) {
                                            mediaController.addSplitVideoRange(vidTimeStart.text, vidTimeEnd.text);
                                            vidTimeStart.text = "";
                                            vidTimeEnd.text = "";
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 100
                                color: Theme.bg
                                radius: Theme.radiusSm
                                border.color: Theme.borderSubtle
                                border.width: 1
                                clip: true

                                ListView {
                                    anchors.fill: parent
                                    anchors.margins: Theme.spacingSm
                                    model: mediaController ? mediaController.splitVideoCustomRanges : []
                                    delegate: Label {
                                        required property var modelData
                                        required property int index
                                        text: qsTr("Đoạn %1: Từ %2 đến %3").arg(index + 1).arg(modelData.split(",")[0]).arg(modelData.split(",")[1])
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacingSm

                                AppButton {
                                    text: qsTr("✂ Bắt đầu cắt các đoạn")
                                    variant: "primary"
                                    Layout.fillWidth: true
                                    enabled: mediaController && !mediaController.isProcessing && mediaController.splitVideoCustomRanges.length > 0
                                    onClicked: if (mediaController) mediaController.startSplitVideoCustom()
                                }

                                AppButton {
                                    text: qsTr("🗑 Xóa danh sách")
                                    variant: "quiet"
                                    onClicked: if (mediaController) mediaController.clearSplitVideoRanges()
                                }
                            }
                        }
                    }
                }
            }

            // =============================================================
            // TAB 2: CHIA MP3
            // =============================================================
            AppCard {
                Layout.fillWidth: true
                visible: mediaController ? mediaController.subTab === "split_mp3" : false

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel { text: qsTr("📁 1. Chọn File Âm thanh & Thư mục lưu đầu ra") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn File Âm thanh...")
                            iconKind: "audiobook"
                            size: "md"
                            onClicked: splitMp3InDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.splitMp3Input) ? mediaController.splitMp3Input : qsTr("Chưa chọn file nào")
                            color: (mediaController && mediaController.splitMp3Input) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Thư mục lưu...")
                            iconKind: "folder"
                            size: "md"
                            onClicked: splitMp3OutDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.splitMp3Output) ? mediaController.splitMp3Output : qsTr("Chưa chọn thư mục nào")
                            color: (mediaController && mediaController.splitMp3Output) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("⏳ 2. Tùy chọn chia file âm thanh") }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.spacingLg
                        rowSpacing: Theme.spacingMd

                        // Fixed length
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label {
                                    text: qsTr("Chia theo độ dài cố định (giây)")
                                    font.weight: Theme.fontWeightBold
                                    color: Theme.text
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    TextField {
                                        id: splitMp3LenField
                                        Layout.fillWidth: true
                                        text: mediaController ? String(mediaController.splitMp3Length) : "120"
                                        placeholderText: "120"
                                        onTextChanged: if (mediaController) mediaController.splitMp3Length = parseInt(text) || 120
                                    }

                                    AppButton {
                                        text: qsTr("Chia theo độ dài")
                                        variant: "primary"
                                        enabled: mediaController && !mediaController.isProcessing
                                        onClicked: if (mediaController) mediaController.startSplitMp3ByLength()
                                    }
                                }
                            }
                        }

                        // Equal parts
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label {
                                    text: qsTr("Chia thành số phần bằng nhau")
                                    font.weight: Theme.fontWeightBold
                                    color: Theme.text
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    TextField {
                                        id: splitMp3PartsField
                                        Layout.fillWidth: true
                                        text: mediaController ? String(mediaController.splitMp3Parts) : "6"
                                        placeholderText: "6"
                                        onTextChanged: if (mediaController) mediaController.splitMp3Parts = parseInt(text) || 6
                                    }

                                    AppButton {
                                        text: qsTr("Chia theo số phần")
                                        variant: "primary"
                                        enabled: mediaController && !mediaController.isProcessing
                                        onClicked: if (mediaController) mediaController.startSplitMp3ByParts()
                                    }
                                }
                            }
                        }
                    }

                    // Custom timestamps
                    Rectangle {
                        Layout.fillWidth: true
                        radius: Theme.radiusMd
                        color: Theme.surfaceAlt
                        border.color: Theme.borderSubtle
                        border.width: 1
                        implicitHeight: customMp3Col.implicitHeight + Theme.spacingMd * 2

                        ColumnLayout {
                            id: customMp3Col
                            anchors.fill: parent
                            anchors.margins: Theme.spacingMd
                            spacing: Theme.spacingSm

                            Label {
                                text: qsTr("🕒 Chia MP3 theo mốc thời gian tuỳ biến")
                                font.weight: Theme.fontWeightBold
                                color: Theme.text
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacingSm

                                TextField {
                                    id: mp3TimeStart
                                    placeholderText: qsTr("Bắt đầu (vd: 00:01:00 hoặc 60s)")
                                    Layout.fillWidth: true
                                }
                                TextField {
                                    id: mp3TimeEnd
                                    placeholderText: qsTr("Kết thúc (vd: 00:03:30 hoặc 210s)")
                                    Layout.fillWidth: true
                                }
                                AppButton {
                                    text: qsTr("+ Thêm đoạn")
                                    variant: "accent"
                                    onClicked: {
                                        if (mp3TimeStart.text && mp3TimeEnd.text) {
                                            mediaController.addSplitMp3Range(mp3TimeStart.text, mp3TimeEnd.text);
                                            mp3TimeStart.text = "";
                                            mp3TimeEnd.text = "";
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 100
                                color: Theme.bg
                                radius: Theme.radiusSm
                                border.color: Theme.borderSubtle
                                border.width: 1
                                clip: true

                                ListView {
                                    anchors.fill: parent
                                    anchors.margins: Theme.spacingSm
                                    model: mediaController ? mediaController.splitMp3CustomRanges : []
                                    delegate: Label {
                                        required property var modelData
                                        required property int index
                                        text: qsTr("Đoạn %1: Từ %2 đến %3").arg(index + 1).arg(modelData.split(",")[0]).arg(modelData.split(",")[1])
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacingSm

                                AppButton {
                                    text: qsTr("✂ Bắt đầu cắt các đoạn MP3")
                                    variant: "primary"
                                    Layout.fillWidth: true
                                    enabled: mediaController && !mediaController.isProcessing && mediaController.splitMp3CustomRanges.length > 0
                                    onClicked: if (mediaController) mediaController.startSplitMp3Custom()
                                }

                                AppButton {
                                    text: qsTr("🗑 Xóa danh sách")
                                    variant: "quiet"
                                    onClicked: if (mediaController) mediaController.clearSplitMp3Ranges()
                                }
                            }
                        }
                    }
                }
            }

            // =============================================================
            // TAB 3: GHÉP VIDEO (MERGER)
            // =============================================================
            AppCard {
                Layout.fillWidth: true
                visible: mediaController ? mediaController.subTab === "merge" : false

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel { text: qsTr("📚 1. Danh sách video ghép nối (theo thứ tự từ trên xuống)") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        AppButton {
                            text: qsTr("+ Thêm Video...")
                            iconKind: "upload"
                            onClicked: mergeAddFilesDialog.open()
                        }

                        AppButton {
                            text: qsTr("🗑 Xóa danh sách")
                            variant: "quiet"
                            onClicked: if (mediaController) mediaController.clearMergeFiles()
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: qsTr("%1 video đã chọn").arg(mediaController ? mediaController.mergeFiles.length : 0)
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 140
                        color: Theme.bg
                        radius: Theme.radiusMd
                        border.color: Theme.borderSubtle
                        border.width: 1
                        clip: true

                        ListView {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            model: mediaController ? mediaController.mergeFiles : []
                            delegate: RowLayout {
                                width: parent.width
                                spacing: Theme.spacingSm
                                required property var modelData
                                required property int index

                                Label {
                                    text: qsTr("[%1]").arg(index + 1)
                                    color: Theme.accent
                                    font.weight: Theme.fontWeightBold
                                }
                                Label {
                                    text: modelData
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                                AppButton {
                                    text: "✕"
                                    size: "sm"
                                    variant: "quiet"
                                    onClicked: if (mediaController) mediaController.removeMergeFile(index)
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("🎥 2. Tùy chọn hiệu ứng & Độ phân giải") }

                    // Options Grid
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.spacingLg
                        rowSpacing: Theme.spacingMd

                        // Xfade Transition
                        Rectangle {
                            Layout.fillWidth: true
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1
                            implicitHeight: xfadeCol.implicitHeight + Theme.spacingMd * 2

                            ColumnLayout {
                                id: xfadeCol
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                CheckBox {
                                    id: xfadeChk
                                    text: qsTr("Hiệu ứng chuyển cảnh (Xfade)")
                                    checked: mediaController ? mediaController.mergeUseXfade : false
                                    onCheckedChanged: if (mediaController) mediaController.mergeUseXfade = checked
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: xfadeChk.checked
                                    spacing: Theme.spacingSm

                                    ComboBox {
                                        id: xfadeTypeCombo
                                        Layout.fillWidth: true
                                        model: ["fade", "wipeleft", "wiperight", "slideleft", "slideright", "circlecrop"]
                                        currentIndex: model.indexOf(mediaController ? mediaController.mergeXfadeType : "fade")
                                        onActivated: if (mediaController) mediaController.mergeXfadeType = currentText
                                    }

                                    TextField {
                                        id: xfadeDurField
                                        Layout.preferredWidth: 80
                                        placeholderText: "1.0"
                                        text: mediaController ? String(mediaController.mergeXfadeDur) : "1.0"
                                        onTextChanged: if (mediaController) mediaController.mergeXfadeDur = parseFloat(text) || 1.0
                                    }
                                }
                            }
                        }

                        // Logo Watermark
                        Rectangle {
                            Layout.fillWidth: true
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1
                            implicitHeight: logoCol.implicitHeight + Theme.spacingMd * 2

                            ColumnLayout {
                                id: logoCol
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label { text: qsTr("Chèn Logo (Watermark PNG)"); font.weight: Theme.fontWeightBold; color: Theme.text }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    AppButton {
                                        text: qsTr("Chọn Logo...")
                                        size: "sm"
                                        onClicked: mergeLogoDialog.open()
                                    }

                                    ComboBox {
                                        id: logoPosCombo
                                        Layout.preferredWidth: 120
                                        model: ["Trên-Phải", "Trên-Trái", "Dưới-Phải", "Dưới-Trái"]
                                        currentIndex: model.indexOf(mediaController ? mediaController.mergeLogoPosition : "Trên-Phải")
                                        onActivated: if (mediaController) mediaController.mergeLogoPosition = currentText
                                    }
                                }

                                Label {
                                    text: (mediaController && mediaController.mergeLogoPath) ? mediaController.mergeLogoPath : qsTr("Chưa chọn logo")
                                    color: (mediaController && mediaController.mergeLogoPath) ? Theme.text : Theme.textMuted
                                    font.pixelSize: Theme.fontSizeXs
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        // Hardsub
                        Rectangle {
                            Layout.fillWidth: true
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1
                            implicitHeight: subCol.implicitHeight + Theme.spacingMd * 2

                            ColumnLayout {
                                id: subCol
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label { text: qsTr("Ghi đè phụ đề (Hardsub .srt, .ass)"); font.weight: Theme.fontWeightBold; color: Theme.text }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    AppButton {
                                        text: qsTr("Chọn File Phụ đề...")
                                        size: "sm"
                                        onClicked: mergeSubDialog.open()
                                    }

                                    AppButton {
                                        text: qsTr("Xóa sub")
                                        size: "sm"
                                        variant: "quiet"
                                        onClicked: if (mediaController) mediaController.mergeSubtitlePath = ""
                                    }
                                }

                                Label {
                                    text: (mediaController && mediaController.mergeSubtitlePath) ? mediaController.mergeSubtitlePath : qsTr("Chưa chọn phụ đề")
                                    color: (mediaController && mediaController.mergeSubtitlePath) ? Theme.text : Theme.textMuted
                                    font.pixelSize: Theme.fontSizeXs
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        // Resolution
                        Rectangle {
                            Layout.fillWidth: true
                            radius: Theme.radiusMd
                            color: Theme.surfaceAlt
                            border.color: Theme.borderSubtle
                            border.width: 1
                            implicitHeight: resCol.implicitHeight + Theme.spacingMd * 2

                            ColumnLayout {
                                id: resCol
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                spacing: Theme.spacingSm

                                Label { text: qsTr("Độ phân giải đầu ra:"); font.weight: Theme.fontWeightBold; color: Theme.text }

                                ComboBox {
                                    id: resCombo
                                    Layout.fillWidth: true
                                    model: [
                                        "1920x1080 (Full HD)",
                                        "1280x720 (HD)",
                                        "720x1280 (HD dọc)",
                                        "1080x1920 (Full HD dọc)",
                                        "2560x1440 (2K)",
                                        "3840x2160 (4K)"
                                    ]
                                    currentIndex: model.indexOf(mediaController ? mediaController.mergeResolution : "1280x720 (HD)")
                                    onActivated: if (mediaController) mediaController.mergeResolution = currentText
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("📁 3. Nơi lưu & Bắt đầu ghép nối") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn File Output...")
                            iconKind: "folder"
                            size: "md"
                            onClicked: mergeOutDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.mergeOutput) ? mediaController.mergeOutput : qsTr("Chưa chọn nơi lưu file .mp4")
                            color: (mediaController && mediaController.mergeOutput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: qsTr("🔗 Bắt đầu Ghép Video & Xử lý")
                        variant: "primary"
                        Layout.fillWidth: true
                        size: "lg"
                        enabled: mediaController && !mediaController.isProcessing && mediaController.mergeFiles.length >= 2
                        onClicked: if (mediaController) mediaController.startMerge()
                    }
                }
            }

            // =============================================================
            // TAB 4: CHUYỂN ĐỔI AUDIO (CONVERT)
            // =============================================================
            AppCard {
                Layout.fillWidth: true
                visible: mediaController ? mediaController.subTab === "convert" : false

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel { text: qsTr("➕ 1. Danh sách video / audio cần chuyển đổi") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        AppButton {
                            text: qsTr("+ Thêm File...")
                            iconKind: "upload"
                            onClicked: convertAddFilesDialog.open()
                        }

                        AppButton {
                            text: qsTr("🗑 Xóa tất cả")
                            variant: "quiet"
                            onClicked: if (mediaController) mediaController.clearConvertFiles()
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: qsTr("%1 file đã chọn").arg(mediaController ? mediaController.convertFiles.length : 0)
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 140
                        color: Theme.bg
                        radius: Theme.radiusMd
                        border.color: Theme.borderSubtle
                        border.width: 1
                        clip: true

                        ListView {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            model: mediaController ? mediaController.convertFiles : []
                            delegate: RowLayout {
                                width: parent.width
                                spacing: Theme.spacingSm
                                required property var modelData
                                required property int index

                                Label {
                                    text: qsTr("[%1]").arg(index + 1)
                                    color: Theme.accent
                                    font.weight: Theme.fontWeightBold
                                }
                                Label {
                                    text: modelData
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                                AppButton {
                                    text: "✕"
                                    size: "sm"
                                    variant: "quiet"
                                    onClicked: if (mediaController) mediaController.removeConvertFile(index)
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("⚙ 2. Cấu hình định dạng âm thanh đầu ra") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs
                            Label { text: qsTr("ĐỊNH DẠNG OUTPUT:"); font.weight: Theme.fontWeightBold; color: Theme.textMuted; font.pixelSize: Theme.fontSizeXs }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["MP3 (Phổ biến)", "AAC (Chất lượng tốt)", "FLAC (Lossless)", "WAV (Không nén)", "OGG (Mã nguồn mở)", "Opus (Hiệu quả cao)"]
                                currentIndex: model.indexOf(mediaController ? mediaController.convertFormat : "MP3 (Phổ biến)")
                                onActivated: if (mediaController) mediaController.convertFormat = currentText
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs
                            Label { text: qsTr("BITRATE:"); font.weight: Theme.fontWeightBold; color: Theme.textMuted; font.pixelSize: Theme.fontSizeXs }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["320k", "256k", "192k", "128k"]
                                currentIndex: model.indexOf(mediaController ? mediaController.convertBitrate : "320k")
                                onActivated: if (mediaController) mediaController.convertBitrate = currentText
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Thư mục lưu...")
                            iconKind: "folder"
                            size: "md"
                            onClicked: convertOutDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.convertOutput) ? mediaController.convertOutput : qsTr("Chưa chọn thư mục lưu")
                            color: (mediaController && mediaController.convertOutput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: qsTr("🎵 Bắt đầu Chuyển đổi Audio")
                        variant: "primary"
                        Layout.fillWidth: true
                        size: "lg"
                        enabled: mediaController && !mediaController.isProcessing && mediaController.convertFiles.length > 0
                        onClicked: if (mediaController) mediaController.startAudioConvert()
                    }
                }
            }

            // =============================================================
            // TAB 5: LÁCH BẢN QUYỀN (BYPASS)
            // =============================================================
            AppCard {
                Layout.fillWidth: true
                visible: mediaController ? mediaController.subTab === "bypass" : false

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel { text: qsTr("📂 1. Chọn File xử lý & Nơi lưu") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Video đầu vào...")
                            iconKind: "video"
                            size: "md"
                            onClicked: bypassInDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.bypassInput) ? mediaController.bypassInput : qsTr("Chưa chọn file")
                            color: (mediaController && mediaController.bypassInput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Nơi lưu Output...")
                            iconKind: "folder"
                            size: "md"
                            onClicked: bypassOutDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.bypassOutput) ? mediaController.bypassOutput : qsTr("Chưa chọn nơi lưu")
                            color: (mediaController && mediaController.bypassOutput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("🛡 2. Các tùy chọn biến đổi & Lách bản quyền") }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.spacingMd
                        rowSpacing: Theme.spacingSm

                        CheckBox {
                            text: qsTr("Chỉ thay đổi MD5 (Siêu nhanh, không re-encode)")
                            checked: mediaController ? mediaController.bypassOnlyMd5 : false
                            onCheckedChanged: if (mediaController) mediaController.bypassOnlyMd5 = checked
                        }

                        CheckBox {
                            text: qsTr("Lật video theo chiều ngang (hflip)")
                            checked: mediaController ? mediaController.bypassHflip : true
                            onCheckedChanged: if (mediaController) mediaController.bypassHflip = checked
                        }

                        CheckBox {
                            text: qsTr("Thay đổi tốc độ (1.05x video & audio)")
                            checked: mediaController ? mediaController.bypassSpeed : true
                            onCheckedChanged: if (mediaController) mediaController.bypassSpeed = checked
                        }

                        CheckBox {
                            text: qsTr("Cắt (crop) nhẹ 4px viền ngoài")
                            checked: mediaController ? mediaController.bypassCrop : true
                            onCheckedChanged: if (mediaController) mediaController.bypassCrop = checked
                        }

                        CheckBox {
                            text: qsTr("Điều chỉnh màu sắc & độ sáng nhẹ")
                            checked: mediaController ? mediaController.bypassColor : true
                            onCheckedChanged: if (mediaController) mediaController.bypassColor = checked
                        }

                        CheckBox {
                            text: qsTr("Thêm nhiễu nhẹ (Noise overlay)")
                            checked: mediaController ? mediaController.bypassNoise : false
                            onCheckedChanged: if (mediaController) mediaController.bypassNoise = checked
                        }

                        CheckBox {
                            text: qsTr("Tăng nhẹ âm lượng (Volume 1.05x)")
                            checked: mediaController ? mediaController.bypassVolume : true
                            onCheckedChanged: if (mediaController) mediaController.bypassVolume = checked
                        }
                    }

                    AppButton {
                        text: qsTr("▷ Bắt đầu Xử lý Lách bản quyền")
                        variant: "danger"
                        Layout.fillWidth: true
                        size: "lg"
                        enabled: mediaController && !mediaController.isProcessing && Boolean(mediaController.bypassInput)
                        onClicked: if (mediaController) mediaController.startBypass()
                    }
                }
            }

            // =============================================================
            // TAB 6: TẢI VIDEO (DOWNLOAD)
            // =============================================================
            AppCard {
                Layout.fillWidth: true
                visible: mediaController ? mediaController.subTab === "download" : false

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    SectionLabel { text: qsTr("🌐 1. Nhập liên kết video (YouTube, Facebook, TikTok, Reels, v.v...)") }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        clip: true

                        TextArea {
                            id: dlUrlsArea
                            placeholderText: qsTr("Dán danh sách đường dẫn video tại đây, mỗi đường dẫn 1 dòng...")
                            text: mediaController ? mediaController.downloadUrls : ""
                            onTextChanged: if (mediaController) mediaController.downloadUrls = text
                            wrapMode: TextEdit.Wrap
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    SectionLabel { text: qsTr("📥 2. Tùy chọn tải về") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs

                            Label { text: qsTr("CHẤT LƯỢNG / ĐỊNH DẠNG:"); font.weight: Theme.fontWeightBold; color: Theme.textMuted; font.pixelSize: Theme.fontSizeXs }

                            ComboBox {
                                Layout.fillWidth: true
                                model: [
                                    "Video tốt nhất + Audio (MP4)",
                                    "Video 1080p + Audio (MP4)",
                                    "Video 720p + Audio (MP4)",
                                    "Chỉ Audio (MP3 chất lượng cao)",
                                    "Chỉ Audio (M4A nguyên gốc)"
                                ]
                                currentIndex: model.indexOf(mediaController ? mediaController.downloadQuality : "Video tốt nhất + Audio (MP4)")
                                onActivated: if (mediaController) mediaController.downloadQuality = currentText
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("Chọn Thư mục lưu...")
                            iconKind: "folder"
                            size: "md"
                            onClicked: downloadOutDialog.open()
                        }

                        Label {
                            text: (mediaController && mediaController.downloadOutput) ? mediaController.downloadOutput : qsTr("Chưa chọn thư mục lưu video")
                            color: (mediaController && mediaController.downloadOutput) ? Theme.text : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        AppButton {
                            text: qsTr("📥 Bắt đầu Tải Video")
                            variant: "primary"
                            Layout.fillWidth: true
                            size: "lg"
                            enabled: mediaController && !mediaController.isProcessing && Boolean(mediaController.downloadUrls.trim())
                            onClicked: if (mediaController) mediaController.startDownload()
                        }

                        AppButton {
                            text: qsTr("🔄 Cập nhật yt-dlp")
                            variant: "quiet"
                            size: "lg"
                            enabled: mediaController && !mediaController.isProcessing
                            onClicked: if (mediaController) mediaController.startUpdateYtdlp()
                        }
                    }
                }
            }

            // =============================================================
            // STATUS & PROGRESS BAR & LOG BOX
            // =============================================================
            AppCard {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        StatusBadge {
                            text: (mediaController && mediaController.isProcessing) ? qsTr("Đang xử lý") : qsTr("Sẵn sàng")
                            status: (mediaController && mediaController.isProcessing) ? "warning" : "success"
                        }

                        Label {
                            text: (mediaController && mediaController.statusText) ? mediaController.statusText : qsTr("Hệ thống sẵn sàng tiếp nhận tác vụ.")
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        AppButton {
                            text: qsTr("Hủy tác vụ")
                            variant: "danger"
                            size: "sm"
                            visible: mediaController && mediaController.isProcessing
                            onClicked: if (mediaController) mediaController.cancelOperation()
                        }

                        AppButton {
                            text: qsTr("Xóa Log")
                            variant: "quiet"
                            size: "sm"
                            onClicked: if (mediaController) mediaController.clearLogs()
                        }
                    }

                    // Progress Bar
                    ProgressBar {
                        Layout.fillWidth: true
                        visible: mediaController && (mediaController.isProcessing || mediaController.progress > 0)
                        from: 0.0
                        to: 100.0
                        value: mediaController ? mediaController.progress : 0.0
                    }

                    // Console Log Viewer
                    Rectangle {
                        Layout.fillWidth: true
                        height: 120
                        color: Theme.bg
                        radius: Theme.radiusSm
                        border.color: Theme.borderSubtle
                        border.width: 1
                        clip: true

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm

                            TextArea {
                                text: mediaController ? mediaController.consoleLogs : ""
                                readOnly: true
                                color: Theme.textMuted
                                font.family: "Consolas, monospace"
                                font.pixelSize: Theme.fontSizeXs
                                wrapMode: TextEdit.Wrap
                            }
                        }
                    }
                }
            }
        }
    }
}

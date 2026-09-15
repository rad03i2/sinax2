import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    Rectangle {
        anchors.fill: parent
        color: Theme.background
        z: -1
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentCol.implicitHeight + Theme.spacing2XL
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        ColumnLayout {
            id: contentCol
            width: Math.min(parent.width - Theme.spacingXL * 2, 1280)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacingL

            // 1. Page Header with Breadcrumbs & Action
            SinaxPageHeader {
                Layout.fillWidth: true
                title: "مركز معالجة وهندسة الصوتيات"
                subtitle: "تحويل، ضغط، توحيد مستوى الصوت (Normalize)، إزالة التشويش، وقص المقاطع بدقة."
                iconName: "audio"
                breadcrumbCurrent: "مركز الصوت"
                showSearch: true
                placeholderText: "ابحث في أدوات الصوت (مثلاً: تحويل، ضغط، تنقية، رفع الصوت)..."
                onSearchChanged: function(text) { audioController.setSearch(text) }
                actionText: "تحويل دفعة صوتيات ←"
                onActionClicked: audioController.openTool("batch_audio_convert")
            }

            // 2. Drop Zone for Audio Files
            SinaxDropZone {
                Layout.fillWidth: true
                iconName: "audio"
                titleText: audioController.activeAudioPath ? "الملف الصوتي: " + audioController.activeAudioPath : "اسحب ملفاً صوتياً هنا للمعاينة ورسم الموجة الصوتية فورياً..."
                subtitleText: audioController.activeAudioPath ? "المدة: " + audioController.audioDurationStr + " | الجودة: " + audioController.audioBitrateStr + " | الحجم: " + audioController.audioSizeStr : "يدعم MP3, WAV, FLAC, AAC, M4A, OGG, Opus دون فقدان في نقاء الصوت"
                browseButtonText: "استعراض ملف صوتي"
                onFileDropped: function(path) { audioController.loadAudioFile(path) }
            }

            // 3. Downsampled Waveform Visualizer & Player Card (Visible when audio active)
            Rectangle {
                Layout.fillWidth: true
                visible: Boolean(audioController.activeAudioPath)
                implicitHeight: 120
                radius: Theme.radiusMedium
                color: Theme.surface2
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingS

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingM

                        // Play/Pause button
                        SinaxIconButton {
                            iconName: audioController.isPlaying ? "pause" : "play"
                            iconSize: 20
                            onClicked: audioController.togglePlay()
                        }

                        Text {
                            text: audioController.audioFormat + " • " + audioController.audioDurationStr
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: audioController.audioBitrateStr
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                        }
                    }

                    // Downsampled Waveform bars
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 3

                        Repeater {
                            model: audioController.waveformPoints

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.max(6, parent.height * modelData)
                                radius: 2
                                color: audioController.isPlaying ? Theme.primary : Theme.textSecondary
                                Layout.alignment: Qt.AlignVCenter

                                Behavior on color { ColorAnimation { duration: 150 } }
                            }
                        }
                    }
                }
            }

            // 4. Category Filter Chips
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                Repeater {
                    model: audioController.categories

                    delegate: Rectangle {
                        height: 32
                        implicitWidth: catRow.implicitWidth + Theme.spacingM * 2
                        radius: Theme.radiusMedium
                        color: audioController.activeCategory === modelData.id ? Theme.primary : (catMouse.containsMouse ? Theme.surfaceElevated : Theme.surface)
                        border.color: audioController.activeCategory === modelData.id ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            id: catRow
                            anchors.centerIn: parent
                            spacing: Theme.spacingXS
                            Text {
                                text: modelData.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: audioController.activeCategory === modelData.id
                                color: audioController.activeCategory === modelData.id ? Theme.textOnPrimary : Theme.textPrimary
                            }
                        }

                        MouseArea {
                            id: catMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: audioController.selectCategory(modelData.id)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }

            // 5. Section Header for Tools Catalog
            SinaxSectionHeader {
                Layout.fillWidth: true
                title: "أدوات معالجة الصوت المتاحة"
                subtitle: "فلاتر ومحولات صوتية مصممة للبودكاست والموسيقى والتسجيلات"
                badgeText: audioController.tools.length + " أداة"
                badgeType: "info"
            }

            // 6. Empty State if no tools matched search
            SinaxEmptyState {
                Layout.fillWidth: true
                visible: audioController.tools.length === 0
                title: "لم يتم العثور على أداة مطابقة"
                description: "جرب البحث بكلمات أخرى مثل: ضغط، تحويل، تنقية، صوت، بودكاست..."
                actionText: "عرض كافة الأدوات"
                onActionClicked: {
                    audioController.setSearch("");
                    audioController.selectCategory("all");
                }
            }

            // 7. Responsive Tool Grid
            GridLayout {
                Layout.fillWidth: true
                columns: width > 1000 ? 3 : (width > 650 ? 2 : 1)
                columnSpacing: Theme.spacingM
                rowSpacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft
                visible: audioController.tools.length > 0

                Repeater {
                    model: audioController.tools

                    delegate: SinaxToolCard {
                        Layout.fillWidth: true
                        title: modelData.title
                        description: modelData.description
                        iconName: modelData.icon || "audio"
                        badgeText: modelData.supportsBatch ? "دفعات متعددة" : "فوري"
                        badgeType: "success"
                        actionText: "تشغيل الأداة ←"
                        isFavorite: modelData.isFavorite
                        onActionClicked: audioController.openTool(modelData.id)
                        onFavoriteToggled: audioController.toggleFavorite(modelData.id)
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

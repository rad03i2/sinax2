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
                title: "مركز معالجة وإنتاج الفيديو"
                subtitle: "ضغط عالي الكفاءة، تحويل الصيغ، قص ودمج، وفصل الصوت بدعم التسريع العتادي."
                iconName: "video"
                breadcrumbCurrent: "مركز الفيديو"
                showSearch: true
                placeholderText: "ابحث في أدوات الفيديو (مثلاً: ضغط، تحويل، قص، ترجمة)..."
                onSearchChanged: function(text) { videoController.setSearch(text) }
                actionText: "تحويل دفعة فيديوهات ←"
                onActionClicked: videoController.openTool("batch_convert")
            }

            // 2. Hardware Acceleration Status Bar
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 48
                radius: Theme.radiusMedium
                color: Theme.surface2
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    SinaxIcon {
                        iconName: "performance"
                        size: 18
                        color: Theme.primary
                    }

                    Text {
                        text: "حالة التسريع العتادي (Hardware Acceleration):"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Repeater {
                        model: videoController.availableEncoders

                        delegate: Rectangle {
                            height: 26
                            implicitWidth: encRow.implicitWidth + Theme.spacingM
                            radius: Theme.radiusSmall
                            color: Theme.surfaceElevated
                            border.color: Theme.primary
                            border.width: 1

                            RowLayout {
                                id: encRow
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    text: modelData.name + " (" + modelData.badge + ")"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXS
                                    color: Theme.textPrimary
                                }
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }
                }
            }

            // 3. Drop Zone for Videos
            SinaxDropZone {
                Layout.fillWidth: true
                iconName: "video"
                titleText: videoController.activeVideoPath ? "الفيديو المحدد: " + videoController.activeVideoPath : "اسحب ملف فيديو هنا لقراءة بياناته والبدء بالمعالجة الفورية..."
                subtitleText: videoController.activeVideoPath ? "المدة: " + videoController.videoDurationStr + " | الأبعاد: " + videoController.videoResolutionStr + " | الترميز: " + videoController.videoCodec + " | الحجم: " + videoController.videoSizeStr : "يدعم MP4, MKV, MOV, AVI, WebM, TS حتى 50 GB دون استهلاك الذاكرة"
                browseButtonText: "استعراض فيديو"
                onFileDropped: function(path) { videoController.loadVideoFile(path) }
            }

            // 4. Category Filter Chips
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                Repeater {
                    model: videoController.categories

                    delegate: Rectangle {
                        height: 32
                        implicitWidth: catRow.implicitWidth + Theme.spacingM * 2
                        radius: Theme.radiusMedium
                        color: videoController.activeCategory === modelData.id ? Theme.primary : (catMouse.containsMouse ? Theme.surfaceElevated : Theme.surface)
                        border.color: videoController.activeCategory === modelData.id ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            id: catRow
                            anchors.centerIn: parent
                            spacing: Theme.spacingXS
                            Text {
                                text: modelData.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: videoController.activeCategory === modelData.id
                                color: videoController.activeCategory === modelData.id ? Theme.textOnPrimary : Theme.textPrimary
                            }
                        }

                        MouseArea {
                            id: catMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: videoController.selectCategory(modelData.id)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }

            // 5. Section Header for Tools Catalog
            SinaxSectionHeader {
                Layout.fillWidth: true
                title: "أدوات الفيديو المتاحة"
                subtitle: "معالجة فائقة السرعة معتمدة على محرك FFmpeg المتكامل"
                badgeText: videoController.tools.length + " أداة"
                badgeType: "info"
            }

            // 6. Empty State if no tools matched search
            SinaxEmptyState {
                Layout.fillWidth: true
                visible: videoController.tools.length === 0
                title: "لم يتم العثور على أداة مطابقة"
                description: "جرب البحث بكلمات أخرى مثل: ضغط، تحويل، قص، دمج، صوت..."
                actionText: "عرض كافة الأدوات"
                onActionClicked: {
                    videoController.setSearch("");
                    videoController.selectCategory("all");
                }
            }

            // 7. Responsive Tool Grid
            GridLayout {
                Layout.fillWidth: true
                columns: width > 1000 ? 3 : (width > 650 ? 2 : 1)
                columnSpacing: Theme.spacingM
                rowSpacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft
                visible: videoController.tools.length > 0

                Repeater {
                    model: videoController.tools

                    delegate: SinaxToolCard {
                        Layout.fillWidth: true
                        title: modelData.title
                        description: modelData.description
                        iconName: modelData.icon || "video"
                        badgeText: modelData.supportsBatch ? "دفعات متعددة" : "فوري"
                        badgeType: "success"
                        actionText: "تشغيل الأداة ←"
                        isFavorite: modelData.isFavorite
                        onActionClicked: videoController.openTool(modelData.id)
                        onFavoriteToggled: videoController.toggleFavorite(modelData.id)
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

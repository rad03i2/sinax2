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
                title: "مركز معالجة وتحسين الصور"
                subtitle: "ضغط ذكي، تحويل الصيغ، تغيير المقاسات، تحسين الجودة، وإزالة الخلفية محلياً."
                iconName: "image"
                breadcrumbCurrent: "مركز الصور"
                showSearch: true
                placeholderText: "ابحث في أدوات الصور (مثلاً: ضغط، قص، خلفية، تحويل)..."
                onSearchChanged: function(text) { imageController.setSearch(text) }
                actionText: "معالجة دفعة صور ←"
                onActionClicked: imageController.openTool("batch_compress")
            }

            // 2. Drop Zone for Single/Batch Images
            SinaxDropZone {
                Layout.fillWidth: true
                iconName: "file_image"
                titleText: imageController.activeImagePath ? "الصورة المحددة: " + imageController.activeImagePath : "اسحب صورة أو مجلد صور هنا للمعاينة والمعالجة الفورية..."
                subtitleText: imageController.activeImagePath ? "الأبعاد: " + imageController.imageWidth + "x" + imageController.imageHeight + " | الصيغة: " + imageController.imageFormat + " | الحجم: " + imageController.imageSizeStr : "يدعم PNG, JPG, WebP, BMP, TIFF, GIF مع الحفاظ على الألوان الأصلية"
                browseButtonText: "استعراض صورة"
                onFileDropped: function(path) { imageController.loadImageFile(path) }
            }

            // 3. Interactive Before / After Comparison Workspace (Visible if image active)
            ColumnLayout {
                Layout.fillWidth: true
                visible: Boolean(imageController.activeImagePath)
                spacing: Theme.spacingM

                SinaxSectionHeader {
                    Layout.fillWidth: true
                    title: "مقارنة الجودة والمعاينة التفاعلية (Before / After)"
                    subtitle: "اسحب الفاصل يميناً ويساراً لمقارنة الصورة الأصلية بالنتيجة المعالجة"
                    badgeText: "معاينة حية"
                    badgeType: "info"
                }

                BeforeAfterViewer {
                    Layout.fillWidth: true
                    implicitHeight: 360
                    beforeSource: imageController.activeImagePath ? "file:///" + imageController.activeImagePath.replace(/\\/g, "/") : ""
                    afterSource: imageController.processedImagePath ? "file:///" + imageController.processedImagePath.replace(/\\/g, "/") : ""
                }
            }

            // 4. Category Filter Chips
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                Repeater {
                    model: imageController.categories

                    delegate: Rectangle {
                        height: 32
                        implicitWidth: catRow.implicitWidth + Theme.spacingM * 2
                        radius: Theme.radiusMedium
                        color: imageController.activeCategory === modelData.id ? Theme.primary : (catMouse.containsMouse ? Theme.surfaceElevated : Theme.surface)
                        border.color: imageController.activeCategory === modelData.id ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            id: catRow
                            anchors.centerIn: parent
                            spacing: Theme.spacingXS
                            Text {
                                text: modelData.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: imageController.activeCategory === modelData.id
                                color: imageController.activeCategory === modelData.id ? Theme.textOnPrimary : Theme.textPrimary
                            }
                        }

                        MouseArea {
                            id: catMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: imageController.selectCategory(modelData.id)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }

            // 5. Section Header for Tools Catalog
            SinaxSectionHeader {
                Layout.fillWidth: true
                title: "أدوات معالجة الصور"
                subtitle: "محركات تحسين وضغط متقدمة مدمجة بدون حاجة للإنترنت"
                badgeText: imageController.tools.length + " أداة"
                badgeType: "info"
            }

            // 6. Empty State if no tools matched search
            SinaxEmptyState {
                Layout.fillWidth: true
                visible: imageController.tools.length === 0
                title: "لم يتم العثور على أداة مطابقة"
                description: "جرب البحث بكلمات أخرى مثل: ضغط، تحويل، أبعاد، علامة مائية..."
                actionText: "عرض كافة الأدوات"
                onActionClicked: {
                    imageController.setSearch("");
                    imageController.selectCategory("all");
                }
            }

            // 7. Responsive Tool Grid
            GridLayout {
                Layout.fillWidth: true
                columns: width > 1000 ? 3 : (width > 650 ? 2 : 1)
                columnSpacing: Theme.spacingM
                rowSpacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft
                visible: imageController.tools.length > 0

                Repeater {
                    model: imageController.tools

                    delegate: SinaxToolCard {
                        Layout.fillWidth: true
                        title: modelData.title
                        description: modelData.description
                        iconName: modelData.icon || "image"
                        badgeText: modelData.aiPowered ? "ذكاء اصطناعي محلي" : (modelData.supportsBatch ? "دفعات متعددة" : "فوري")
                        badgeType: modelData.aiPowered ? "info" : "success"
                        actionText: "تشغيل الأداة ←"
                        isFavorite: modelData.isFavorite
                        onActionClicked: imageController.openTool(modelData.id)
                        onFavoriteToggled: imageController.toggleFavorite(modelData.id)
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

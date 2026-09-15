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
                title: "مركز PDF الاحترافي الشامل"
                subtitle: "تنظيم، ضغط، استخراج، حماية، وتوقيع مستندات PDF محلياً بأقصى سرعة وأمان."
                iconName: "pdf"
                breadcrumbCurrent: "مركز PDF"
                showSearch: true
                placeholderText: "ابحث في أدوات PDF (مثلاً: دمج، ضغط، OCR)..."
                onSearchChanged: function(text) { pdfController.setSearch(text) }
                actionText: "فتح محرر PDF ←"
                onActionClicked: pdfController.openTool("merge")
            }

            // 2. File Drop Zone for PDFs
            SinaxDropZone {
                Layout.fillWidth: true
                iconName: "file_pdf"
                titleText: pdfController.activeFilePath ? "الملف المحدد: " + pdfController.activeFilePath : "اسحب ملف PDF هنا لبدء الضغط أو التقسيم أو الحماية فورياً..."
                subtitleText: pdfController.activeFilePath ? "عدد الصفحات: " + pdfController.pageCount + " | الحجم: " + pdfController.fileSizeStr : "يدعم كافة أنواع ملفات ومستندات PDF حتى 2 GB"
                browseButtonText: "استعراض ملف PDF"
                onFileDropped: function(path) { pdfController.loadPdfFile(path) }
                onBrowseClicked: {
                    // Trigger browser fallback
                }
            }

            // 3. Category Filter Chips
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                Repeater {
                    model: pdfController.categories

                    delegate: Rectangle {
                        height: 32
                        implicitWidth: catRow.implicitWidth + Theme.spacingM * 2
                        radius: Theme.radiusMedium
                        color: pdfController.activeCategory === modelData.id ? Theme.primary : (catMouse.containsMouse ? Theme.surfaceElevated : Theme.surface)
                        border.color: pdfController.activeCategory === modelData.id ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            id: catRow
                            anchors.centerIn: parent
                            spacing: Theme.spacingXS
                            Text {
                                text: modelData.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: pdfController.activeCategory === modelData.id
                                color: pdfController.activeCategory === modelData.id ? Theme.textOnPrimary : Theme.textPrimary
                            }
                        }

                        MouseArea {
                            id: catMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: pdfController.selectCategory(modelData.id)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }

            // 4. Section Header for Tools Catalog
            SinaxSectionHeader {
                Layout.fillWidth: true
                title: "أدوات PDF المتاحة"
                subtitle: "أدوات متخصصة لمعالجة ملفات PDF الفردية والدفعات الكبيرة"
                badgeText: pdfController.tools.length + " أداة"
                badgeType: "info"
            }

            // 5. Empty State if no tools matched search
            SinaxEmptyState {
                Layout.fillWidth: true
                visible: pdfController.tools.length === 0
                title: "لم يتم العثور على أداة مطابقة"
                description: "جرب البحث بكلمات أخرى مثل: ضغط، تقسيم، أمان، OCR، استخراج..."
                actionText: "عرض كافة الأدوات"
                onActionClicked: {
                    pdfController.setSearch("");
                    pdfController.selectCategory("all");
                }
            }

            // 6. Responsive Tool Grid
            GridLayout {
                Layout.fillWidth: true
                columns: width > 1000 ? 3 : (width > 650 ? 2 : 1)
                columnSpacing: Theme.spacingM
                rowSpacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft
                visible: pdfController.tools.length > 0

                Repeater {
                    model: pdfController.tools

                    delegate: SinaxToolCard {
                        Layout.fillWidth: true
                        title: modelData.title
                        description: modelData.description
                        iconName: modelData.icon || "pdf"
                        badgeText: modelData.status === "needs_dep" ? "يتطلب محركاً إضافياً" : (modelData.supportsBatch ? "دفعات متعددة" : "فوري")
                        badgeType: modelData.status === "needs_dep" ? "warning" : "success"
                        actionText: "تشغيل الأداة ←"
                        isFavorite: modelData.isFavorite
                        onActionClicked: pdfController.openTool(modelData.id)
                        onFavoriteToggled: pdfController.toggleFavorite(modelData.id)
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

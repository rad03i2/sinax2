import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"
import "./quick_tools"

Flickable {
    id: root

    contentWidth: width
    contentHeight: contentCol.implicitHeight + Theme.spacing2XL
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    SinaxScrollBar {
        flickable: root
    }

    ColumnLayout {
        id: contentCol
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: Theme.spacingL
        }
        spacing: Theme.spacingXL

        // 1. Page Header with Integrated Search
        SinaxPageHeader {
            title: "مختبر الأدوات السريعة والمساعدة"
            subtitle: "أكثر من 20 أداة فورية للحسابات، التجزئة، التشفير، ومعالجة النصوص دون مغادرة الواجهة."
            iconName: "tools"
            breadcrumb: "الرئيسية  ›  الأدوات السريعة"
            searchVisible: true
            searchPlaceholder: "ابحث في الأدوات (مثلاً: hash, base64, uuid, qr)..."
            onSearchChanged: function(q) {
                quickToolsController.setSearchQuery(q);
            }
        }

        // 2. Category Filter Chips Row
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spacingS
            layoutDirection: Qt.RightToLeft

            Repeater {
                model: [
                    { id: "all", label: "الكل", icon: "tools" },
                    { id: "hash", label: "الـHash والبصمة", icon: "hash" },
                    { id: "encoding", label: "الترميز Base64", icon: "convert" },
                    { id: "qr", label: "QR والباركود", icon: "qr" },
                    { id: "password", label: "كلمات المرور", icon: "security" },
                    { id: "text", label: "النصوص", icon: "text" },
                    { id: "developer", label: "المطورين", icon: "code" },
                    { id: "conversion", label: "التحويلات", icon: "calculator" },
                ]

                SinaxFilterChip {
                    text: modelData.label
                    iconName: modelData.icon
                    checked: quickToolsController.activeCategory === modelData.id
                    onClicked: {
                        quickToolsController.setCategory(modelData.id);
                    }
                }
            }
        }

        // 3. Smart Drag & Drop Zone for Quick Tools
        SinaxDropZone {
            Layout.fillWidth: true
            isCompact: true
            promptText: "اسحب أي ملف هنا لحساب بصمة التجزئة الرقمية SHA-256 فورياً..."
            formatHint: "يدعم جميع الملفات والأحجام"
            onFilesDropped: function(urls) {
                quickToolsController.handleDrop(urls);
            }
        }

        // 4. Integrated Tool Workbench
        ToolWorkbench {
            Layout.fillWidth: true
        }

        // 5. Section: Available Tools Grid
        SinaxSectionHeader {
            title: "قائمة الأدوات المتاحة"
            description: "انقر على أي أداة لتحميلها فورياً في مختبر المعالجة أعلاه"
            badgeText: String(quickToolsController.toolModel.rowCount()) + " أداة"
            badgeVariant: "info"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 280
            maxColumns: 4

            Repeater {
                model: quickToolsController.toolModel

                SinaxToolCard {
                    toolId: model.toolId
                    title: model.title
                    description: model.description
                    iconName: model.icon
                    iconColor: Theme.primary
                    badgeText: model.inputType === "file" ? "ملفات" : "نصوص"
                    badgeVariant: "default"
                    onClicked: quickToolsController.selectTool(model.toolId)
                }
            }
        }
    }
}

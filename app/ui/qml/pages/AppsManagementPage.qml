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

    ColumnLayout {
        id: contentCol
        anchors.fill: parent
        anchors.margins: Theme.spacingL
        spacing: Theme.spacingM

        // 1. Page Header with Breadcrumbs & Action
        SinaxPageHeader {
            Layout.fillWidth: true
            title: "إدارة البرامج والتطبيقات المثبتة"
            subtitle: "استعراض دقيق للبرامج، إزالة آمنة مع كشف البقايا، وتجهيز البرامج قبل الفورمات."
            iconName: "apps"
            breadcrumbCurrent: "إدارة البرامج"
            showSearch: true
            placeholderText: "ابحث في البرامج المثبتة (بالاسم أو المطور)..."
            onSearchChanged: function(text) { appsController.searchQuery = text }
            actionText: "تحديث القائمة ⟳"
            onActionClicked: appsController.refreshInventory(true)
        }

        // 2. Filter Tabs & Inventory Stats
        RowLayout {
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft
            spacing: Theme.spacingS

            Repeater {
                model: [
                    { id: "all", label: "كل البرامج" },
                    { id: "desktop", label: "برامج سطح المكتب" },
                    { id: "store", label: "تطبيقات متجر Microsoft" },
                    { id: "large", label: "البرامج الكبيرة (>100MB)" }
                ]

                delegate: Rectangle {
                    height: 32
                    implicitWidth: filterText.implicitWidth + Theme.spacingM * 2
                    radius: Theme.radiusMedium
                    color: appsController.activeFilter === modelData.id ? Theme.primary : (filtMouse.containsMouse ? Theme.surfaceElevated : Theme.surface)
                    border.color: appsController.activeFilter === modelData.id ? Theme.primary : Theme.borderSubtle
                    border.width: 1

                    Text {
                        id: filterText
                        anchors.centerIn: parent
                        text: modelData.label
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.bold: appsController.activeFilter === modelData.id
                        color: appsController.activeFilter === modelData.id ? Theme.textOnPrimary : Theme.textPrimary
                    }

                    MouseArea {
                        id: filtMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: appsController.activeFilter = modelData.id
                    }
                }
            }

            Item { Layout.fillWidth: true }

            SinaxBadge {
                text: String(appsController.filteredAppsCount) + " برنامج"
                variant: "info"
            }
        }

        // 3. Main Master/Detail Layout
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            // Left Panel (RTL: Right side): Apps Table / ListView
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Table Header
                    Rectangle {
                        Layout.fillWidth: true
                        height: 38
                        color: Theme.surface2

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spacingM
                            anchors.rightMargin: Theme.spacingM
                            layoutDirection: Qt.RightToLeft

                            Text {
                                text: "اسم البرنامج والتطبيق"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textSecondary
                                Layout.fillWidth: true
                            }

                            Text {
                                text: "المطور"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textSecondary
                                Layout.preferredWidth: 160
                            }

                            Text {
                                text: "الإصدار"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textSecondary
                                Layout.preferredWidth: 100
                            }

                            Text {
                                text: "الحجم التقديري"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textSecondary
                                Layout.preferredWidth: 110
                            }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Theme.divider
                        }
                    }

                    // Loading State
                    SinaxProgress {
                        Layout.fillWidth: true
                        visible: appsController.isLoading
                        indeterminate: true
                        barHeight: 3
                    }

                    // Apps ListView
                    ListView {
                        id: appList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: appsController.appsModel
                        boundsBehavior: Flickable.StopAtBounds

                        ScrollBar.vertical: SinaxScrollBar {}

                        delegate: Rectangle {
                            width: appList.width
                            height: 44
                            color: appMouse.containsMouse ? Theme.surfaceHover : (index % 2 === 1 ? Theme.surface2 : "transparent")

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spacingM
                                anchors.rightMargin: Theme.spacingM
                                layoutDirection: Qt.RightToLeft
                                spacing: Theme.spacingM

                                Text {
                                    text: model.name
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBody
                                    font.bold: true
                                    color: Theme.textPrimary
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: model.publisher
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    color: Theme.textSecondary
                                    elide: Text.ElideRight
                                    Layout.preferredWidth: 160
                                }

                                Text {
                                    text: model.version
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    color: Theme.textSecondary
                                    Layout.preferredWidth: 100
                                }

                                Text {
                                    text: model.sizeStr
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    font.bold: true
                                    color: Theme.primary
                                    Layout.preferredWidth: 110
                                }
                            }

                            MouseArea {
                                id: appMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: appsController.selectApp(index)
                            }
                        }
                    }
                }
            }

            // Right Panel (RTL: Left side): Selected App Details Card
            Rectangle {
                Layout.preferredWidth: 340
                Layout.fillHeight: true
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    Text {
                        text: "تفاصيل البرنامج المحدد"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.divider
                    }

                    Item {
                        visible: !appsController.selectedApp.name
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        SinaxEmptyState {
                            anchors.centerIn: parent
                            title: "اختر برنامجاً من القائمة"
                            description: "انقر على أي برنامج لعرض مواصفاته، مسار تثبيته، وإمكانية إزالته بأمان."
                        }
                    }

                    ColumnLayout {
                        visible: Boolean(appsController.selectedApp.name)
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingS

                        Text {
                            text: appsController.selectedApp.name || ""
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMedium
                            font.bold: true
                            color: Theme.primary
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "المطور:"
                            value: appsController.selectedApp.publisher || "—"
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "الإصدار:"
                            value: appsController.selectedApp.version || "—"
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "الحجم التقريبي:"
                            value: appsController.selectedApp.sizeStr || "—"
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "تاريخ التثبيت:"
                            value: appsController.selectedApp.installDate || "—"
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "المصدر:"
                            value: appsController.selectedApp.source === "uwp" ? "Microsoft Store" : "تطبيق سطح المكتب"
                        }

                        Item { Layout.fillHeight: true }

                        // Confidence Warning
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: confRow.implicitHeight + Theme.spacingM
                            radius: Theme.radiusSmall
                            color: Theme.surfaceElevated
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                id: confRow
                                anchors.fill: parent
                                anchors.margins: Theme.spacingS
                                spacing: Theme.spacingS
                                layoutDirection: Qt.RightToLeft

                                SinaxIcon {
                                    iconName: "check"
                                    size: Theme.iconSmall
                                    color: Theme.success
                                }

                                Text {
                                    text: "مستوى الثقة في الإزالة النظيفة: " + (appsController.selectedApp.confidence === "high" ? "مرتفع" : "متوسط")
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    color: Theme.textSecondary
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        SinaxButton {
                            Layout.fillWidth: true
                            text: "إلغاء التثبيت بأمان (Safe Uninstall)"
                            variant: "danger"
                            iconName: "delete"
                            enabled: Boolean(appsController.selectedApp.canUninstall)
                            onClicked: appsController.requestUninstall(appsController.selectedApp.name)
                        }
                    }
                }
            }
        }
    }
}

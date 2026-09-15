import QtQuick
import QtQuick.Layouts
import ".."
import "../components"

Rectangle {
    id: root
    color: Theme.background

    Component.onCompleted: {
        dashboardController.startMonitoring();
    }
    Component.onDestruction: {
        dashboardController.stopMonitoring();
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        contentWidth: width
        contentHeight: mainLayout.implicitHeight + 40
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        ColumnLayout {
            id: mainLayout
            width: parent.width
            spacing: Theme.spacingXL
            Layout.alignment: Qt.AlignTop

            // Padding Container
            Item { Layout.fillWidth: true; height: 4 }

            // 1. Executive Welcome Header
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                implicitHeight: 92
                radius: Theme.radiusLarge
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 24
                    spacing: 16
                    layoutDirection: Qt.RightToLeft

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        RowLayout {
                            spacing: 8
                            layoutDirection: Qt.RightToLeft

                            Text {
                                text: "مرحباً بك في SINAX"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontTitle
                                font.weight: Font.Black
                                color: Theme.textPrimary
                            }

                            SinaxBadge {
                                text: "النظام يعمل بكفاءة"
                                statusType: "success"
                            }
                        }

                        Text {
                            text: "لوحة القيادة الموحدة • " + dashboardController.windowsText
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textSecondary
                        }
                    }

                    SinaxButton {
                        text: "طبيب SINAX"
                        iconName: "doctor"
                        variant: "primary"
                        onClicked: dashboardController.openCenter("maintenance_doctor")
                    }
                }
            }

            // 2. Real-time Quick Stats Cards (4 Cards Grid)
            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                columns: root.width > 1100 ? 4 : (root.width > 750 ? 2 : 1)
                columnSpacing: 16
                rowSpacing: 16
                layoutDirection: Qt.RightToLeft

                // CPU Card
                SinaxCard {
                    Layout.fillWidth: true
                    title: "المعالج (CPU)"
                    iconName: "cpu"
                    iconColor: Theme.primary
                    statusText: Math.round(dashboardController.cpuPercent) + "%"
                    statusType: dashboardController.cpuPercent > 85 ? "error" : "normal"
                    accentBorder: dashboardController.cpuPercent > 85

                    ColumnLayout {
                        width: parent.width
                        spacing: 8

                        SinaxProgress {
                            Layout.fillWidth: true
                            value: dashboardController.cpuPercent
                            barColor: dashboardController.cpuPercent > 85 ? Theme.error : Theme.primary
                        }

                        Text {
                            text: "الاستهلاك اللحظي للمعالج"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textMuted
                            horizontalAlignment: Text.AlignRight
                            Layout.fillWidth: true
                        }
                    }
                }

                // RAM Card
                SinaxCard {
                    Layout.fillWidth: true
                    title: "الذاكرة العشوائية (RAM)"
                    iconName: "ram"
                    iconColor: "#10B981"
                    statusText: Math.round(dashboardController.ramPercent) + "%"
                    statusType: dashboardController.ramPercent > 90 ? "warning" : "normal"

                    ColumnLayout {
                        width: parent.width
                        spacing: 8

                        SinaxProgress {
                            Layout.fillWidth: true
                            value: dashboardController.ramPercent
                            barColor: "#10B981"
                        }

                        Text {
                            text: dashboardController.ramText
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                            horizontalAlignment: Text.AlignRight
                            Layout.fillWidth: true
                        }
                    }
                }

                // Disk C Card
                SinaxCard {
                    Layout.fillWidth: true
                    title: "قرص النظام (C:)"
                    iconName: "storage"
                    iconColor: "#F59E0B"
                    statusText: Math.round(dashboardController.diskPercent) + "% مستخدم"
                    statusType: dashboardController.diskPercent > 90 ? "error" : "normal"

                    ColumnLayout {
                        width: parent.width
                        spacing: 8

                        SinaxProgress {
                            Layout.fillWidth: true
                            value: dashboardController.diskPercent
                            barColor: dashboardController.diskPercent > 90 ? Theme.error : "#F59E0B"
                        }

                        Text {
                            text: dashboardController.diskText
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                            horizontalAlignment: Text.AlignRight
                            Layout.fillWidth: true
                        }
                    }
                }

                // Backup Card
                SinaxCard {
                    Layout.fillWidth: true
                    title: "حماية النظام"
                    iconName: "shield"
                    iconColor: "#8B5CF6"
                    statusText: "محمي"
                    statusType: "success"

                    ColumnLayout {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: dashboardController.backupText
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                            horizontalAlignment: Text.AlignRight
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "النسخ الاحتياطي والمزامنة نشطة"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textMuted
                            horizontalAlignment: Text.AlignRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // Section Header: Quick Access Centers
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                layoutDirection: Qt.RightToLeft

                Text {
                    text: "المراكز الرئيسية والوصول السريع"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLarge
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                }
                Item { Layout.fillWidth: true }
            }

            // 3. Quick Center Tiles (6 Centers Grid)
            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                columns: root.width > 1050 ? 3 : (root.width > 700 ? 2 : 1)
                columnSpacing: 16
                rowSpacing: 16
                layoutDirection: Qt.RightToLeft

                Repeater {
                    model: dashboardController.quickCenters
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 130
                        radius: Theme.radiusMedium
                        color: tileMouse.containsMouse ? Theme.surfaceHover : Theme.surface
                        border.color: tileMouse.containsMouse ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
                        Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                layoutDirection: Qt.RightToLeft
                                spacing: 10

                                SinaxIcon {
                                    iconName: modelData.icon
                                    size: 22
                                    color: tileMouse.containsMouse ? Theme.primary : Theme.textSecondary
                                }

                                Text {
                                    text: modelData.title
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontMedium
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                    horizontalAlignment: Text.AlignRight
                                    Layout.fillWidth: true
                                }
                            }

                            Text {
                                text: modelData.desc
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignRight
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                layoutDirection: Qt.RightToLeft

                                Item { Layout.fillWidth: true }

                                SinaxButton {
                                    text: "فتح المركز"
                                    isCompact: true
                                    variant: "secondary"
                                    onClicked: dashboardController.openCenter(modelData.route)
                                }
                            }
                        }

                        MouseArea {
                            id: tileMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: dashboardController.openCenter(modelData.route)
                        }
                    }
                }
            }

            // 4. Bottom Activity & Recommendation Row
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                spacing: 16
                layoutDirection: Qt.RightToLeft

                // Recent Activity Card
                SinaxCard {
                    Layout.fillWidth: true
                    title: "آخر العمليات المنجزة"
                    iconName: "history"

                    ColumnLayout {
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: dashboardController.recentOperations
                            delegate: RowLayout {
                                Layout.fillWidth: true
                                layoutDirection: Qt.RightToLeft
                                spacing: 10

                                SinaxIcon {
                                    iconName: "shield"
                                    size: 14
                                    color: Theme.success
                                }

                                Text {
                                    text: modelData.title
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBody
                                    color: Theme.textPrimary
                                    horizontalAlignment: Text.AlignRight
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.time
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    color: Theme.textMuted
                                }

                                SinaxBadge {
                                    text: modelData.status
                                    statusType: "success"
                                }
                            }
                        }
                    }
                }

                // Quick Tools Launcher Card
                SinaxCard {
                    Layout.fillWidth: true
                    title: "مختبر الأدوات السريعة"
                    iconName: "quick_tools"

                    ColumnLayout {
                        width: parent.width
                        spacing: 12

                        Text {
                            text: "حساب ومقارنة التجزئة (Hash)، فاحص المجلدات، ومولد QR كود، ومساعدات يومية فورية دون مغادرة البرنامج."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignRight
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            layoutDirection: Qt.RightToLeft
                            SinaxButton {
                                text: "استعراض الأدوات السريعة"
                                variant: "primary"
                                onClicked: dashboardController.openCenter("quick_tools")
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }

            Item { height: 16 }
        }
    }

    SinaxScrollBar {
        id: vScrollBar
        flickable: flickable
    }
}


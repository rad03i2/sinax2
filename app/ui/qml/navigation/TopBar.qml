import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Rectangle {
    id: root
    implicitHeight: 50
    color: Theme.surface
    border.color: Theme.borderSubtle
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12
        layoutDirection: Qt.RightToLeft

        // Back button
        SinaxIconButton {
            iconName: "chevron_right"
            iconSize: 14
            tooltipText: "الرجوع للخلف"
            enabled: navController.canGoBack
            opacity: enabled ? 1.0 : 0.4
            onClicked: navController.goBack()
        }

        // Forward button
        SinaxIconButton {
            iconName: "chevron_left"
            iconSize: 14
            tooltipText: "التقدم للأمام"
            enabled: navController.canGoForward
            opacity: enabled ? 1.0 : 0.4
            onClicked: navController.goForward()
        }

        // Breadcrumb & Page Title
        RowLayout {
            spacing: 6
            layoutDirection: Qt.RightToLeft

            Text {
                text: navController.currentBreadcrumb
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMedium
                font.weight: Font.Bold
                color: Theme.textPrimary
            }
        }

        // Spacer to push right/left items apart
        Item {
            Layout.fillWidth: true
        }

        // Global Command Palette (Ctrl+K) Trigger
        RowLayout {
            spacing: 6
            Rectangle {
                width: 140
                height: 28
                radius: Theme.radiusSmall
                color: Theme.surface2
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 4
                    layoutDirection: Qt.RightToLeft

                    Image {
                        width: 14
                        height: 14
                        source: "image://sinax/search/" + encodeURIComponent(Theme.textMuted) + "/14"
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        text: "بحث (Ctrl+K)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textMuted
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: searchMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof commandPaletteController !== "undefined") {
                            commandPaletteController.toggle();
                        }
                    }
                }

                SinaxTooltip {
                    trigger: searchMouse.containsMouse
                    text: "البحث في SINAX (Ctrl+K)"
                }
            }
        }

        // Job Center Drawer Trigger Button
        RowLayout {
            spacing: 2
            SinaxIconButton {
                iconName: "tools"
                iconSize: 16
                tooltipText: "مركز العمليات"
                onClicked: {
                    if (typeof root.openJobCenter !== "undefined") {
                        root.openJobCenter();
                    }
                }
            }

            SinaxBadge {
                visible: typeof jobController !== "undefined" && jobController.activeJobCount > 0
                text: typeof jobController !== "undefined" ? String(jobController.activeJobCount) : ""
                variant: "info"
            }
        }

        // System status badge
        SinaxBadge {
            text: "النظام يعمل بكفاءة"
            statusType: "success"
        }

        // 3-Mode Theme Selector Button & Menu
        Item {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32

            SinaxIconButton {
                id: themeBtn
                anchors.fill: parent
                iconName: (typeof themeController !== "undefined") ? themeController.currentIcon : "moon"
                iconSize: Theme.iconSmall
                tooltipText: "تغيير المظهر"
                showFocusBorder: false
                onClicked: themeMenu.open()
            }

            Popup {
                id: themeMenu
                y: themeBtn.height + 6
                x: LayoutMirroring.enabled ? 0 : (themeBtn.width - width)
                width: 175
                padding: 6
                modal: false
                closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape

                background: Rectangle {
                    color: Theme.surfaceElevated
                    radius: Theme.radiusSmall
                    border.color: Theme.borderSubtle
                    border.width: 1
                }

                contentItem: ColumnLayout {
                    spacing: 2

                    // Option 1: System
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 32
                        radius: Theme.radiusSmall
                        color: sysMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            layoutDirection: Qt.RightToLeft
                            SinaxIcon { iconName: "monitor"; size: 16; color: Theme.textSecondary }
                            Text {
                                text: "تلقائي (حسب النظام)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                            }
                            SinaxIcon {
                                visible: (typeof themeController !== "undefined") && themeController.themeMode === "system"
                                iconName: "check"
                                size: 14
                                color: Theme.primary
                            }
                        }
                        MouseArea {
                            id: sysMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof themeController !== "undefined") {
                                    themeController.setThemeMode("system");
                                }
                                themeMenu.close();
                            }
                        }
                    }

                    // Option 2: Light
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 32
                        radius: Theme.radiusSmall
                        color: lightMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            layoutDirection: Qt.RightToLeft
                            SinaxIcon { iconName: "sun"; size: 16; color: Theme.textSecondary }
                            Text {
                                text: "فاتح (Light)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                            }
                            SinaxIcon {
                                visible: (typeof themeController !== "undefined") && themeController.themeMode === "light"
                                iconName: "check"
                                size: 14
                                color: Theme.primary
                            }
                        }
                        MouseArea {
                            id: lightMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof themeController !== "undefined") {
                                    themeController.setThemeMode("light");
                                }
                                themeMenu.close();
                            }
                        }
                    }

                    // Option 3: Dark
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 32
                        radius: Theme.radiusSmall
                        color: darkMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            layoutDirection: Qt.RightToLeft
                            SinaxIcon { iconName: "moon"; size: 16; color: Theme.textSecondary }
                            Text {
                                text: "داكن (Dark)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                            }
                            SinaxIcon {
                                visible: (typeof themeController !== "undefined") && themeController.themeMode === "dark"
                                iconName: "check"
                                size: 14
                                color: Theme.primary
                            }
                        }
                        MouseArea {
                            id: darkMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof themeController !== "undefined") {
                                    themeController.setThemeMode("dark");
                                }
                                themeMenu.close();
                            }
                        }
                    }
                }
            }
        }

        // Settings Shortcut Button
        SinaxIconButton {
            iconName: "settings"
            iconSize: 16
            tooltipText: "الإعدادات"
            showFocusBorder: false
            onClicked: navController.openRoute("settings")
        }

        // About Shortcut Button
        SinaxIconButton {
            iconName: "info"
            iconSize: 16
            tooltipText: "حول البرنامج"
            showFocusBorder: false
            onClicked: navController.openRoute("about")
        }
    }

    signal openJobCenter()
}

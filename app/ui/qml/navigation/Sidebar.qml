import QtQuick
import QtQuick.Layouts
import ".."
import "../components"

Rectangle {
    id: root
    width: navController.isCollapsed ? 68 : 260
    color: Theme.sidebar
    border.color: Theme.borderSubtle
    border.width: 1

    Behavior on width {
        NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Top Brand Header
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: navController.isCollapsed ? 82 : 64
            color: "transparent"

            // Expanded Mode: 3-column Layout (Right: Logo | Center: Title + Subtitle | Left: Toggle)
            Item {
                visible: !navController.isCollapsed
                anchors.fill: parent

                // Right: Logo Button (toggles Quick About)
                Item {
                    id: logoContainer
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    width: 34
                    height: 34

                    SinaxIcon {
                        anchors.centerIn: parent
                        iconName: "logo"
                        size: 32
                        color: Theme.primary
                    }

                    MouseArea {
                        id: logoMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof quickAboutController !== "undefined") {
                                quickAboutController.toggle();
                            }
                        }
                    }

                    SinaxTooltip {
                        trigger: logoMouse.containsMouse
                        text: "حول SINAX"
                    }
                }

                // Center: Visually Centered Brand Titles
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 1

                    Text {
                        text: "SINAX"
                        font.family: Theme.fontFamily
                        font.pixelSize: 17
                        font.weight: Font.Black
                        color: Theme.primary
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Text {
                        text: "نظام إدارة الحاسوب والملفات"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.Medium
                        color: Theme.textSecondary
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }
                }

                // Left: Sidebar Toggle Ghost Button (No Blue Border)
                Item {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    width: 32
                    height: 32

                    SinaxIconButton {
                        anchors.fill: parent
                        iconName: "menu"
                        iconSize: 18
                        tooltipText: "طي القائمة"
                        showFocusBorder: false
                        onClicked: navController.toggleSidebar()
                    }
                }
            }

            // Collapsed Mode: Centered Logo + Toggle Button
            ColumnLayout {
                visible: navController.isCollapsed
                anchors.centerIn: parent
                spacing: 6

                // Centered Logo (toggles Quick About)
                Item {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignHCenter

                    SinaxIcon {
                        anchors.centerIn: parent
                        iconName: "logo"
                        size: 30
                        color: Theme.primary
                    }

                    MouseArea {
                        id: colLogoMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof quickAboutController !== "undefined") {
                                quickAboutController.toggle();
                            }
                        }
                    }

                    SinaxTooltip {
                        trigger: colLogoMouse.containsMouse
                        text: "حول SINAX"
                    }
                }

                // Centered Toggle Button
                Item {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignHCenter

                    SinaxIconButton {
                        anchors.fill: parent
                        iconName: "menu"
                        iconSize: 16
                        tooltipText: "توسيع القائمة"
                        showFocusBorder: false
                        onClicked: navController.toggleSidebar()
                    }
                }
            }
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Theme.borderSubtle
        }

        // 2. Instant Search Box (visible when expanded)
        Item {
            visible: !navController.isCollapsed
            Layout.fillWidth: true
            implicitHeight: 48

            SinaxSearchBox {
                anchors.centerIn: parent
                width: parent.width - 20
                onSearchChanged: function(q) {
                    navController.setSearchQuery(q);
                }
                onCleared: {
                    navController.setSearchQuery("");
                }
            }
        }

        // 3. Scrollable Navigation List
        ListView {
            id: navList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: navController.navModel
            delegate: SidebarItem {}
            boundsBehavior: Flickable.StopAtBounds
            spacing: 2
        }

        // 4. Bottom Fixed Panel (Settings, About, Version)
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Theme.borderSubtle
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Layout.topMargin: 6
            Layout.bottomMargin: 8

            // Settings Button
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 36
                color: setMouse.containsMouse ? Theme.sidebarHover : "transparent"
                radius: Theme.radiusSmall
                Layout.leftMargin: navController.isCollapsed ? 8 : 10
                Layout.rightMargin: navController.isCollapsed ? 8 : 10

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: navController.isCollapsed ? 0 : 10
                    anchors.rightMargin: navController.isCollapsed ? 0 : 12
                    spacing: 10
                    layoutDirection: Qt.RightToLeft

                    SinaxIcon {
                        Layout.alignment: navController.isCollapsed ? Qt.AlignCenter : Qt.AlignVCenter
                        iconName: "settings"
                        size: Theme.iconMedium
                        active: navController.currentRoute === "settings"
                        color: (navController.currentRoute === "settings" || setMouse.containsMouse) ? Theme.iconActive : Theme.iconDefault
                    }

                    Text {
                        visible: !navController.isCollapsed
                        text: "الإعدادات"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.weight: navController.currentRoute === "settings" ? Font.Bold : Font.Normal
                        color: (navController.currentRoute === "settings" || setMouse.containsMouse) ? Theme.textPrimary : Theme.textSecondary
                        horizontalAlignment: Text.AlignRight
                        Layout.fillWidth: true
                    }
                }

                MouseArea {
                    id: setMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: navController.openRoute("settings")
                }

                SinaxTooltip {
                    trigger: navController.isCollapsed && setMouse.containsMouse
                    text: "الإعدادات"
                }
            }

            // About Button
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 36
                color: (navController.currentRoute === "about") ? Theme.primaryTint : (abtMouse.containsMouse ? Theme.sidebarHover : "transparent")
                radius: Theme.radiusSmall
                Layout.leftMargin: navController.isCollapsed ? 8 : 10
                Layout.rightMargin: navController.isCollapsed ? 8 : 10

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: navController.isCollapsed ? 0 : 10
                    anchors.rightMargin: navController.isCollapsed ? 0 : 12
                    spacing: 10
                    layoutDirection: Qt.RightToLeft

                    SinaxIcon {
                        Layout.alignment: navController.isCollapsed ? Qt.AlignCenter : Qt.AlignVCenter
                        iconName: "info"
                        size: Theme.iconMedium
                        active: navController.currentRoute === "about"
                        color: (navController.currentRoute === "about" || abtMouse.containsMouse) ? Theme.iconActive : Theme.iconDefault
                    }

                    Text {
                        visible: !navController.isCollapsed
                        text: "حول البرنامج"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.weight: navController.currentRoute === "about" ? Font.Bold : Font.Normal
                        color: (navController.currentRoute === "about" || abtMouse.containsMouse) ? Theme.textPrimary : Theme.textSecondary
                        horizontalAlignment: Text.AlignRight
                        Layout.fillWidth: true
                    }
                }

                MouseArea {
                    id: abtMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: navController.openRoute("about")
                }

                SinaxTooltip {
                    trigger: navController.isCollapsed && abtMouse.containsMouse
                    text: "حول البرنامج"
                }
            }

            // Version Label
            Text {
                visible: !navController.isCollapsed
                Layout.alignment: Qt.AlignCenter
                Layout.topMargin: 4
                text: "SINAX v1.1.2 • إصلاح التحديث"
                font.family: Theme.fontFamily
                font.pixelSize: 10
                color: Theme.textMuted
            }
        }
    }
}

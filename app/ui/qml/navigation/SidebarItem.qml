import QtQuick
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    width: ListView.view ? ListView.view.width : 260
    visible: model.itemVisible !== false
    height: visible ? (model.isSub ? 34 : 40) : 0
    clip: true

    Behavior on height {
        NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic }
    }

    readonly property bool isCurrentActive: navController.currentRoute === model.itemId
    readonly property bool isCurrentParentActive: {
        var cr = navController.currentRoute;
        return model.isSection && (cr.startsWith(model.itemId) || (model.itemId === "multimedia" && (cr === "image_center" || cr === "video_center" || cr === "audio_center")));
    }
    readonly property bool isCollapsed: navController.isCollapsed

    Rectangle {
        id: bgBox
        anchors.fill: parent
        anchors.leftMargin: root.isCollapsed ? 8 : 10
        anchors.rightMargin: root.isCollapsed ? 8 : (model.isSub ? 20 : 10)
        radius: Theme.radiusSmall

        color: {
            if (mouseArea.pressed) return Theme.surfacePressed;
            if (root.isCurrentActive) return Theme.primaryTint;
            if (mouseArea.containsMouse) return Theme.sidebarHover;
            if (root.isCurrentParentActive && !root.isCollapsed) return Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08);
            return "transparent";
        }

        Behavior on color {
            ColorAnimation { duration: Theme.durationFast }
        }

        // Active indicator pill on the far right edge (in RTL layout)
        Rectangle {
            id: activePill
            visible: root.isCurrentActive
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: root.isCollapsed ? 20 : (model.isSub ? 16 : 22)
            radius: 1.5
            color: Theme.primary
        }

        // Content Row
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: root.isCollapsed ? 0 : 10
            anchors.rightMargin: root.isCollapsed ? 0 : 12
            spacing: 10
            layoutDirection: Qt.RightToLeft

            // 1. Leading Icon (placed rightmost in RTL, or centered in collapsed mode)
            Item {
                Layout.preferredWidth: model.isSub ? Theme.iconSmall : Theme.iconMedium
                Layout.preferredHeight: model.isSub ? Theme.iconSmall : Theme.iconMedium
                Layout.alignment: root.isCollapsed ? Qt.AlignCenter : Qt.AlignVCenter

                SinaxIcon {
                    anchors.centerIn: parent
                    iconName: model.itemIcon || "folder"
                    active: root.isCurrentActive
                    size: model.isSub ? Theme.iconSmall : Theme.iconMedium
                    color: {
                        if (root.isCurrentActive || root.isCurrentParentActive) return Theme.iconActive;
                        if (mouseArea.containsMouse) return Theme.iconHover;
                        return model.isSub ? Theme.iconMuted : Theme.iconDefault;
                    }
                }
            }

            // 2. Arabic Title Text (aligned right next to icon)
            Text {
                id: titleLabel
                visible: !root.isCollapsed
                text: model.itemTitle || ""
                font.family: Theme.fontFamily
                font.pixelSize: model.isSub ? Theme.fontSmall : Theme.fontBody
                font.weight: (root.isCurrentActive || root.isCurrentParentActive) ? Font.Bold : Font.Medium
                color: {
                    if (root.isCurrentActive || root.isCurrentParentActive) return Theme.primary;
                    if (mouseArea.containsMouse) return Theme.textPrimary;
                    return model.isSub ? Theme.textSecondary : Theme.textPrimary;
                }
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true
                elide: Text.ElideLeft
            }

            // 3. Badge (e.g. "قريباً")
            SinaxBadge {
                visible: !root.isCollapsed && model.badge !== ""
                text: model.badge || ""
                statusType: "info"
            }

            // 4. Trailing Accordion Chevron (Clean SVG with RTL awareness)
            Item {
                visible: !root.isCollapsed && model.isSection
                Layout.preferredWidth: Theme.iconSmall
                Layout.preferredHeight: Theme.iconSmall
                Layout.alignment: Qt.AlignVCenter

                SinaxIcon {
                    anchors.centerIn: parent
                    iconName: model.isOpen ? "chevron_down" : "chevron_left"
                    size: Theme.iconSmall
                    color: model.isOpen ? Theme.primary : Theme.textMuted
                }
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            if (root.ListView.view) {
                root.ListView.view.forceActiveFocus();
            }
            if (model.isSection) {
                // Single source of truth toggle for both Expanded and Collapsed modes
                navController.toggleSection(model.itemId);
                if (!root.isCollapsed) {
                    navController.openRoute(model.route);
                }
            } else {
                navController.openRoute(model.route);
                if (root.isCollapsed) {
                    navController.closeSection();
                }
            }
        }
    }

    // Tooltip in collapsed mode (suppressed when flyout is open for this section)
    SinaxTooltip {
        trigger: root.isCollapsed && mouseArea.containsMouse && navController.openSectionId !== model.itemId
        text: model.itemTitle || ""
    }
}

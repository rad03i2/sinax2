import QtQuick
import ".."

Rectangle {
    id: root
    property string iconName: "settings"
    property string variant: "regular"
    property int iconSize: Theme.iconMedium
    property bool active: false
    property string tooltipText: ""
    property string accessibleName: ""
    property color iconColor: !enabled ? Theme.iconDisabled : (mouseArea.containsMouse ? Theme.iconHover : (active ? Theme.iconActive : Theme.iconDefault))
    property bool showFocusBorder: true

    signal clicked()

    implicitWidth: 32
    implicitHeight: 32
    radius: Theme.radiusSmall
    opacity: enabled ? 1.0 : 0.5
    color: {
        if (!enabled) return "transparent";
        if (mouseArea.pressed) return Theme.surfacePressed;
        if (mouseArea.containsMouse) return Theme.surfaceHover;
        if (active) return Theme.primaryTint;
        return "transparent";
    }

    // Keyboard focus & accessibility
    activeFocusOnTab: true
    border.width: (showFocusBorder && activeFocus) ? 2 : 0
    border.color: Theme.focusRing

    Accessible.role: Accessible.Button
    Accessible.name: accessibleName !== "" ? accessibleName : (tooltipText !== "" ? tooltipText : iconName)
    Accessible.description: tooltipText

    SinaxIcon {
        anchors.centerIn: parent
        iconName: root.iconName
        variant: root.variant
        active: root.active
        size: root.iconSize
        color: root.iconColor
        enabled: root.enabled
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.enabled) {
                root.forceActiveFocus();
                root.clicked();
            }
        }
    }

    Keys.onReturnPressed: if (root.enabled) root.clicked()
    Keys.onSpacePressed: if (root.enabled) root.clicked()

    // Tooltip
    SinaxTooltip {
        trigger: mouseArea.containsMouse && root.tooltipText !== ""
        text: root.tooltipText
    }
}


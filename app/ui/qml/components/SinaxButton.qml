import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property string text: ""
    property string iconName: ""
    property string variant: "primary" // "primary", "secondary", "ghost", "danger"
    property bool isCompact: false
    property bool loading: false
    property alias isLoading: root.loading
    property bool active: false

    signal clicked()

    implicitWidth: Math.max(isCompact ? 64 : 80, contentLayout.implicitWidth + (isCompact ? 16 : 24))
    implicitHeight: isCompact ? 28 : 36
    radius: isCompact ? Theme.radiusSmall : Theme.radiusMedium

    // Accessible
    Accessible.role: Accessible.Button
    Accessible.name: text

    // State detection
    readonly property bool isHovered: mouseArea.containsMouse
    readonly property bool isPressed: mouseArea.pressed

    // Background color computation
    color: {
        if (!enabled) return Theme.surfaceElevated;
        if (variant === "primary") {
            if (isPressed) return Theme.primaryPressed;
            if (isHovered) return Theme.primaryHover;
            return Theme.primary;
        } else if (variant === "secondary") {
            if (isPressed) return Theme.surfacePressed;
            if (isHovered) return Theme.surfaceHover;
            return Theme.surfaceElevated;
        } else if (variant === "ghost") {
            if (isPressed) return Theme.surfacePressed;
            if (isHovered) return Theme.surfaceHover;
            return "transparent";
        } else if (variant === "danger") {
            if (isPressed) return "#B91C1C";
            if (isHovered) return "#DC2626";
            return Theme.error;
        }
        return Theme.surfaceElevated;
    }

    border.color: {
        if (variant === "secondary") return isHovered ? Theme.primary : Theme.borderSubtle;
        return "transparent";
    }
    border.width: variant === "secondary" ? 1 : 0

    Behavior on color {
        ColorAnimation { duration: Theme.durationFast }
    }

    RowLayout {
        id: contentLayout
        anchors.centerIn: parent
        spacing: Theme.spacingS
        layoutDirection: Qt.RightToLeft

        SinaxIcon {
            id: btnIcon
            visible: root.iconName !== "" && !root.loading
            iconName: root.iconName
            size: root.isCompact ? 14 : 16
            color: {
                if (!root.enabled) return Theme.textMuted;
                if (root.variant === "primary" || root.variant === "danger") return Theme.textOnPrimary;
                return root.isHovered ? Theme.primary : Theme.textPrimary;
            }
        }

        Text {
            id: btnText
            visible: root.text !== ""
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: root.isCompact ? Theme.fontSmall : Theme.fontBody
            font.weight: root.variant === "primary" ? Font.Bold : Font.Medium
            color: {
                if (!root.enabled) return Theme.textMuted;
                if (root.variant === "primary" || root.variant === "danger") return Theme.textOnPrimary;
                return Theme.textPrimary;
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.enabled && !root.loading) {
                root.clicked();
            }
        }
    }
}

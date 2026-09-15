import QtQuick
import ".."

Rectangle {
    id: root
    property string text: ""
    property string statusType: "normal" // "normal", "success", "warning", "error", "info"
    property alias variant: root.statusType

    readonly property color badgeColor: {
        switch (statusType) {
            case "success": return Theme.success;
            case "warning": return Theme.warning;
            case "error": return Theme.error;
            case "info": return Theme.info;
            default: return Theme.textSecondary;
        }
    }

    readonly property color badgeBg: {
        switch (statusType) {
            case "success": return Theme.successTint;
            case "warning": return Theme.warningTint;
            case "error": return Theme.errorTint;
            case "info": return Theme.infoTint;
            default: return Theme.surfaceElevated;
        }
    }

    implicitWidth: badgeText.implicitWidth + Theme.spacingM * 2
    implicitHeight: 22
    radius: Theme.radiusPill
    color: badgeBg
    border.color: Qt.rgba(badgeColor.r, badgeColor.g, badgeColor.b, 0.4)
    border.width: 1

    Text {
        id: badgeText
        anchors.centerIn: parent
        text: root.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
        font.weight: Font.DemiBold
        color: root.badgeColor
    }
}

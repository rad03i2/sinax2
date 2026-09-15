import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    property string message: ""
    property string toastType: "info" // "info", "success", "error"

    anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
    anchors.bottom: parent ? parent.bottom : undefined
    anchors.bottomMargin: 24
    z: 99998

    implicitWidth: toastBox.implicitWidth
    implicitHeight: toastBox.implicitHeight

    opacity: 0
    visible: opacity > 0

    Behavior on opacity {
        NumberAnimation { duration: Theme.durationNormal }
    }

    Rectangle {
        id: toastBox
        radius: Theme.radiusMedium
        color: Theme.surfaceElevated
        border.color: Theme.borderSubtle
        border.width: 1

        implicitWidth: toastRow.implicitWidth + Theme.spacingL * 2
        implicitHeight: 40

        RowLayout {
            id: toastRow
            anchors.centerIn: parent
            spacing: Theme.spacingM
            layoutDirection: Qt.RightToLeft

            SinaxIcon {
                iconName: {
                    if (root.toastType === "success") return "shield";
                    if (root.toastType === "error") return "doctor";
                    return "info";
                }
                color: {
                    if (root.toastType === "success") return Theme.success;
                    if (root.toastType === "error") return Theme.error;
                    return Theme.primary;
                }
                size: 16
            }

            Text {
                text: root.message
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textPrimary
            }
        }
    }

    Timer {
        id: autoHideTimer
        interval: 2500
        repeat: false
        onTriggered: {
            root.opacity = 0;
        }
    }

    function showToast(msg, type) {
        message = msg;
        toastType = type || "info";
        opacity = 1;
        autoHideTimer.restart();
    }
}

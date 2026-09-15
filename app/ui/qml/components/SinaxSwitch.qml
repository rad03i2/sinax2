import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    property bool checked: false
    property string text: ""
    property bool enabled: true

    signal toggled(bool checked)

    implicitWidth: rowLayout.implicitWidth
    implicitHeight: 24

    RowLayout {
        id: rowLayout
        anchors.fill: parent
        spacing: Theme.spacingS
        layoutDirection: Qt.RightToLeft

        Rectangle {
            id: track
            width: 40
            height: 20
            radius: 10
            color: root.checked ? Theme.primary : Theme.surfaceElevated
            border.color: root.checked ? Theme.primary : Theme.borderSubtle
            border.width: 1

            Behavior on color {
                ColorAnimation { duration: Theme.durationFast }
            }

            Rectangle {
                id: thumb
                width: 14
                height: 14
                radius: 7
                anchors.verticalCenter: parent.verticalCenter
                x: root.checked ? parent.width - width - 3 : 3
                color: root.checked ? Theme.textOnPrimary : Theme.textSecondary

                Behavior on x {
                    NumberAnimation { duration: Theme.durationFast; easing.type: Easing.OutCubic }
                }
            }
        }

        Text {
            id: label
            visible: root.text !== ""
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            color: root.enabled ? Theme.textPrimary : Theme.textMuted
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.checked = !root.checked;
            root.toggled(root.checked);
        }
    }
}

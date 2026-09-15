import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

FocusScope {
    id: root

    property string text: ""
    property string iconName: ""
    property bool checked: false
    property int count: -1

    signal clicked()

    implicitWidth: chipContent.implicitWidth + Theme.spacingL * 2
    implicitHeight: 32

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.checked: checked

    Rectangle {
        id: bgRect
        anchors.fill: parent
        radius: Theme.radiusPill

        color: {
            if (!root.enabled) return Theme.surfaceDisabled;
            if (root.checked) return Theme.primary;
            if (mouseArea.pressed) return Theme.surfacePressed;
            if (mouseArea.containsMouse) return Theme.surfaceHover;
            return Theme.surface2;
        }

        border.color: {
            if (root.activeFocus) return Theme.focusRing;
            if (root.checked) return Theme.primary;
            if (mouseArea.containsMouse) return Theme.borderHover;
            return Theme.borderSubtle;
        }
        border.width: (root.activeFocus || root.checked) ? 2 : 1

        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
        Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }

        RowLayout {
            id: chipContent
            anchors.centerIn: parent
            spacing: 6
            layoutDirection: Qt.RightToLeft

            SinaxIcon {
                visible: root.iconName !== ""
                iconName: root.iconName
                size: 14
                color: root.checked ? "#FFFFFF" : (mouseArea.containsMouse ? Theme.textPrimary : Theme.textSecondary)
            }

            Text {
                text: root.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                font.bold: root.checked
                color: root.checked ? "#FFFFFF" : Theme.textPrimary
            }

            Rectangle {
                visible: root.count >= 0
                implicitWidth: countText.implicitWidth + 8
                implicitHeight: 18
                radius: 9
                color: root.checked ? "#FFFFFF33" : Theme.surface3

                Text {
                    id: countText
                    anchors.centerIn: parent
                    text: String(root.count)
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.bold: true
                    color: root.checked ? "#FFFFFF" : Theme.textSecondary
                }
            }
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
    }

    Keys.onReturnPressed: if (root.enabled) root.clicked()
    Keys.onSpacePressed: if (root.enabled) root.clicked()
}

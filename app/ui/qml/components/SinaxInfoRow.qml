import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string label: ""
    property string value: ""
    property bool isMono: false
    property bool isLTR: false
    property bool copyable: false
    property string statusText: ""
    property string statusVariant: "default"
    property bool showDivider: true

    signal copied()

    implicitHeight: 44
    implicitWidth: parent ? parent.width : 500

    Rectangle {
        id: rowBg
        anchors.fill: parent
        color: rowMouse.containsMouse ? Theme.surfaceHover : "transparent"
        radius: Theme.radiusSmall

        Behavior on color { ColorAnimation { duration: Theme.durationFast } }

        RowLayout {
            anchors {
                fill: parent
                leftMargin: Theme.spacingM
                rightMargin: Theme.spacingM
            }
            spacing: Theme.spacingM
            layoutDirection: Qt.RightToLeft

            // Label (Right side in Arabic RTL)
            Text {
                text: root.label
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textSecondary
                Layout.preferredWidth: Math.min(220, root.width * 0.35)
                elide: Text.ElideRight
            }

            // Optional Status Pill
            SinaxBadge {
                visible: root.statusText.length > 0
                text: root.statusText
                variant: root.statusVariant
            }

            // Value (Middle / Left side)
            Text {
                id: valText
                text: root.value.length > 0 ? root.value : "غير متوفر"
                font.family: root.isMono ? Theme.fontMono : Theme.fontFamily
                font.pixelSize: root.isMono ? Theme.fontBody - 1 : Theme.fontBody
                font.bold: !root.isMono
                color: root.value.length > 0 ? Theme.textPrimary : Theme.textMuted
                Layout.fillWidth: true
                elide: Text.ElideMiddle
                horizontalAlignment: root.isLTR ? Text.AlignLeft : Text.AlignRight
            }

            // Copy button (if copyable)
            SinaxIconButton {
                visible: root.copyable && root.value.length > 0
                iconName: "copy"
                iconSize: 14
                tooltipText: "نسخ القيمة"
                onClicked: {
                    // Quick copy to clipboard via QML text edit or native
                    valText.selectAll();
                    valText.copy();
                    valText.deselect();
                    root.copied();
                }
            }
        }

        // Subtle bottom divider
        Rectangle {
            visible: root.showDivider
            anchors {
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                leftMargin: Theme.spacingM
                rightMargin: Theme.spacingM
            }
            height: 1
            color: Theme.divider
        }

        MouseArea {
            id: rowMouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton // Passthrough clicks
        }
    }
}

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string iconName: "folder"
    property string title: "لا توجد عناصر"
    property string description: ""
    property string actionText: ""
    property string actionIcon: ""

    signal actionClicked()

    implicitWidth: 360
    implicitHeight: emptyCol.implicitHeight + Theme.spacingXL * 2

    ColumnLayout {
        id: emptyCol
        anchors.centerIn: parent
        spacing: Theme.spacingM
        width: Math.min(parent.width - Theme.spacingXL * 2, 400)

        // Large icon circle
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 64
            height: 64
            radius: 32
            color: Theme.isDark ? "#1E293B" : "#F1F5F9"

            Image {
                anchors.centerIn: parent
                width: 32
                height: 32
                source: "image://sinax/" + root.iconName + "/" + encodeURIComponent(Theme.textSecondary) + "/32"
                fillMode: Image.PreserveAspectFit
            }
        }

        // Title
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: root.title
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontLarge
            font.bold: true
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        // Description (optional)
        Text {
            visible: root.description.length > 0
            Layout.alignment: Qt.AlignHCenter
            text: root.description
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            color: Theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            lineHeight: 1.2
        }

        Item { height: Theme.spacingS }

        // Action button (optional)
        SinaxButton {
            visible: root.actionText.length > 0
            Layout.alignment: Qt.AlignHCenter
            text: root.actionText
            iconName: root.actionIcon
            variant: "primary"
            onClicked: root.actionClicked()
        }
    }
}

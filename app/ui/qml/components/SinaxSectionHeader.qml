import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string title: ""
    property string description: ""
    property alias subtitle: root.description
    property string badgeText: ""
    property string badgeVariant: "info"
    property alias badgeType: root.badgeVariant
    property string actionText: ""
    property bool collapsible: false
    property bool isCollapsed: false

    signal actionClicked()
    signal toggled(bool collapsed)

    implicitHeight: mainRow.implicitHeight + Theme.spacingM
    implicitWidth: parent ? parent.width : 600

    RowLayout {
        id: mainRow
        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
        }
        spacing: Theme.spacingM
        layoutDirection: Qt.RightToLeft

        // Optional expand/collapse chevron
        SinaxIconButton {
            visible: root.collapsible
            iconName: root.isCollapsed ? "arrow-left" : "arrow-down"
            iconSize: 14
            onClicked: {
                root.isCollapsed = !root.isCollapsed;
                root.toggled(root.isCollapsed);
            }
        }

        // Section Title
        Text {
            text: root.title
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSectionTitle
            font.bold: true
            color: Theme.textPrimary
        }

        // Optional Badge
        SinaxBadge {
            visible: root.badgeText.length > 0
            text: root.badgeText
            variant: root.badgeVariant
        }

        // Optional Description
        Text {
            visible: root.description.length > 0
            text: root.description
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
            color: Theme.textSecondary
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Item {
            visible: root.description.length === 0
            Layout.fillWidth: true
        }

        // Optional Action link button
        Text {
            visible: root.actionText.length > 0
            text: root.actionText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            font.bold: true
            color: actionMouse.containsMouse ? Theme.primaryHover : Theme.primary

            MouseArea {
                id: actionMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.actionClicked()
            }
        }
    }
}

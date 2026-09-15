import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property string title: ""
    property string subtitle: ""
    property string value: ""
    property string iconName: ""
    property color iconColor: Theme.primary
    property alias accentColor: root.iconColor
    property string statusText: ""
    property string statusType: "normal"
    property bool hoverable: true
    property bool clickable: false
    property bool accentBorder: false
    default property alias content: innerContainer.data

    signal clicked()

    implicitWidth: 280
    implicitHeight: mainCol.implicitHeight + Theme.spacingL * 2
    radius: Theme.radiusMedium

    readonly property bool isHovered: hoverable && mouseArea.containsMouse

    color: isHovered ? Theme.surfaceHover : Theme.surface
    border.color: accentBorder ? Theme.primary : (isHovered ? Theme.borderAccent : Theme.borderSubtle)
    border.width: 1

    Behavior on color {
        ColorAnimation { duration: Theme.durationFast }
    }
    Behavior on border.color {
        ColorAnimation { duration: Theme.durationFast }
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: Theme.spacingL
        spacing: Theme.spacingM

        // Header Row
        RowLayout {
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft
            spacing: Theme.spacingM
            visible: root.title !== "" || root.iconName !== "" || root.statusText !== ""

            // Leading Icon
            SinaxIcon {
                visible: root.iconName !== ""
                iconName: root.iconName
                color: root.iconColor
                size: 20
            }

            // Titles
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    id: titleText
                    visible: root.title !== ""
                    text: root.title
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMedium
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    horizontalAlignment: Text.AlignRight
                    Layout.fillWidth: true
                }

                Text {
                    id: subText
                    visible: root.subtitle !== ""
                    text: root.subtitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    color: Theme.textSecondary
                    horizontalAlignment: Text.AlignRight
                    Layout.fillWidth: true
                }
            }

            // Status Badge (if any)
            SinaxBadge {
                visible: root.statusText !== ""
                text: root.statusText
                statusType: root.statusType
            }
        }

        // Value text (for Stat Cards)
        Text {
            visible: root.value !== ""
            text: root.value
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontHeader
            font.bold: true
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignRight
            Layout.fillWidth: true
        }

        // Inner dynamic container for card body
        Item {
            id: innerContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            implicitHeight: childrenRect.height
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        z: -1
        hoverEnabled: root.hoverable
        acceptedButtons: root.clickable ? Qt.LeftButton : Qt.NoButton
        cursorShape: root.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.clickable) {
                root.clicked();
            }
        }
    }
}

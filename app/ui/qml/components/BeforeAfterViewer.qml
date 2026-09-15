import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property url beforeSource: ""
    property url afterSource: ""
    property string beforeLabel: "قبل المعالجة"
    property string afterLabel: "بعد المعالجة"
    property real splitRatio: 0.5 // 0.0 to 1.0

    // Compatibility aliases
    property alias sliderPosition: root.splitRatio
    property alias beforeText: root.beforeLabel
    property alias afterText: root.afterLabel

    implicitWidth: 600
    implicitHeight: 400
    clip: true

    Rectangle {
        anchors.fill: parent
        color: Theme.surface
        radius: Theme.radiusMedium
        border.color: Theme.borderSubtle
        border.width: 1
        clip: true

        // 1. After Image (Background / Full Width)
        Image {
            id: afterImg
            anchors.fill: parent
            source: root.afterSource
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true
        }

        // 2. Before Image (Clipped to splitRatio)
        Item {
            id: beforeClippedContainer
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            width: parent.width * root.splitRatio
            clip: true

            Image {
                id: beforeImg
                width: root.width
                height: root.height
                source: root.beforeSource
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: true
            }
        }

        // 3. Draggable Divider Line & Handle
        Rectangle {
            id: dividerLine
            x: parent.width * root.splitRatio - width / 2
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 2
            color: Theme.primary
            z: 10

            // Handle Circle
            Rectangle {
                anchors.centerIn: parent
                width: 32
                height: 32
                radius: 16
                color: Theme.surface
                border.color: Theme.primary
                border.width: 2

                Row {
                    anchors.centerIn: parent
                    spacing: 3
                    Rectangle { width: 2; height: 12; radius: 1; color: Theme.textSecondary }
                    Rectangle { width: 2; height: 12; radius: 1; color: Theme.textSecondary }
                }
            }
        }

        // 4. Mouse Drag Area
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.SplitHCursor
            hoverEnabled: true

            onPositionChanged: function(mouse) {
                if (pressed) {
                    var r = mouse.x / width;
                    root.splitRatio = Math.max(0.05, Math.min(0.95, r));
                }
            }

            onPressed: function(mouse) {
                var r = mouse.x / width;
                root.splitRatio = Math.max(0.05, Math.min(0.95, r));
            }
        }

        // 5. Floating Labels
        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: Theme.spacingM
            height: 24
            radius: Theme.radiusSmall
            color: Qt.rgba(15/255, 23/255, 42/255, 0.75)
            border.color: Theme.borderSubtle
            border.width: 1
            z: 15

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingS
                anchors.rightMargin: Theme.spacingS
                Text {
                    text: root.beforeLabel
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.spacingM
            height: 24
            radius: Theme.radiusSmall
            color: Qt.rgba(15/255, 23/255, 42/255, 0.75)
            border.color: Theme.borderSubtle
            border.width: 1
            z: 15

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingS
                anchors.rightMargin: Theme.spacingS
                Text {
                    text: root.afterLabel
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.weight: Font.DemiBold
                    color: Theme.primary
                }
            }
        }
    }
}

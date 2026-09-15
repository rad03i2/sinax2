import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    property real value: 0.0 // 0.0 to 100.0
    property alias accentColor: root.barColor
    property color barColor: Theme.primary
    property color trackColor: Theme.surfaceElevated
    property bool showPercent: false
    property bool indeterminate: false
    property int barHeight: 6

    implicitWidth: 200
    implicitHeight: showPercent ? barHeight + 18 : barHeight

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        // Percentage text (if enabled)
        RowLayout {
            visible: root.showPercent && !root.indeterminate
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft

            Text {
                text: Math.round(root.value) + "%"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                font.weight: Font.DemiBold
                color: Theme.textSecondary
            }
            Item { Layout.fillWidth: true }
        }

        // Track & Fill bar
        Rectangle {
            id: trackRect
            Layout.fillWidth: true
            implicitHeight: root.barHeight
            radius: root.barHeight / 2
            color: root.trackColor
            clip: true

            // Determinate bar
            Rectangle {
                id: fillBar
                visible: !root.indeterminate
                height: parent.height
                radius: parent.radius
                color: root.barColor
                width: Math.max(0, Math.min(parent.width, parent.width * (root.value / 100.0)))

                Behavior on width {
                    NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic }
                }
            }

            // Indeterminate bar
            Rectangle {
                id: indetBar
                visible: root.indeterminate
                height: parent.height
                width: Math.max(40, trackRect.width * 0.3)
                radius: parent.radius
                color: root.barColor

                SequentialAnimation on x {
                    running: root.indeterminate && root.visible
                    loops: Animation.Infinite
                    NumberAnimation {
                        from: -indetBar.width
                        to: trackRect.width
                        duration: 1200
                        easing.type: Easing.InOutQuad
                    }
                }
            }
        }
    }
}

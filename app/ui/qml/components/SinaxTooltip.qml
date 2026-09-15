import QtQuick
import QtQuick.Controls
import ".."

ToolTip {
    id: control

    // Timing configuration (500ms delay, 4000ms timeout)
    // property int delay: 500
    // property int timeout: 4000
    delay: 500
    timeout: 4000
    property bool trigger: false
    visible: trigger && text !== ""

    contentItem: Text {
        text: control.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
        color: Theme.textPrimary
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        color: Theme.surfaceElevated
        border.color: Theme.borderSubtle
        border.width: 1
        radius: Theme.radiusSmall

        // Subtle elevated shadow
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1
            z: -1
            radius: Theme.radiusSmall + 1
            color: "#00000022"
        }
    }
}

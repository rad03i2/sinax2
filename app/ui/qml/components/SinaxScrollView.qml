import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    clip: true

    default property alias data: flickable.data
    property alias contentWidth: flickable.contentWidth
    property alias contentHeight: flickable.contentHeight
    property alias contentX: flickable.contentX
    property alias contentY: flickable.contentY
    property alias boundsBehavior: flickable.boundsBehavior
    property alias interactive: flickable.interactive
    property alias flickableItem: flickable
    property alias verticalScrollBar: vBar

    Flickable {
        id: flickable
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
    }

    SinaxScrollBar {
        id: vBar
        flickable: flickable
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        z: 99
        policy: ScrollBar.AsNeeded
    }
}

import QtQuick
import QtQuick.Controls
import ".."

ScrollBar {
    id: control
    objectName: orientation === Qt.Vertical ? "vScrollBar" : "hScrollBar"

    property Flickable flickable: null
    parent: flickable ? flickable : undefined

    // In RTL Arabic layout, vertical scrollbar is anchored to the LEFT edge
    anchors.left: parent ? parent.left : undefined
    anchors.right: undefined
    anchors.top: parent ? parent.top : undefined
    anchors.bottom: parent ? parent.bottom : undefined
    z: 99

    width: 10
    height: parent ? parent.height : 100
    policy: ScrollBar.AsNeeded
    hoverEnabled: true

    size: flickable ? flickable.visibleArea.heightRatio : visibleArea.heightRatio
    position: flickable ? flickable.visibleArea.yPosition : visibleArea.yPosition
    active: flickable ? (flickable.moving || flickable.flashing || hovered || pressed) : (hovered || pressed)
    visible: policy === ScrollBar.AlwaysOn || (policy === ScrollBar.AsNeeded && size < 0.999)

    onPositionChanged: {
        if (pressed && flickable) {
            flickable.contentY = position * flickable.contentHeight;
        }
    }

    contentItem: Rectangle {
        implicitWidth: 8
        implicitHeight: 48
        radius: 4
        color: control.pressed ? Theme.primary : (control.hovered ? Theme.iconHover : Theme.scrollbarThumb)
        opacity: (control.active || control.hovered || control.pressed) ? 1.0 : 0.45

        Behavior on opacity {
            NumberAnimation { duration: Theme.durationFast }
        }
        Behavior on color {
            ColorAnimation { duration: Theme.durationFast }
        }
    }

    background: Rectangle {
        implicitWidth: 10
        color: Theme.scrollbarTrack
    }
}

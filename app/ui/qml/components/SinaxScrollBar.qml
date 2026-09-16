import QtQuick
import QtQuick.Controls
import ".."

ScrollBar {
    id: control
    objectName: orientation === Qt.Vertical ? "vScrollBar" : "hScrollBar"

    property Flickable flickable: null
    property real touchpadScrollMultiplier: 2.8
    property real mouseWheelStepPixels: 96
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

    // Precision touchpads send pixelDelta values that Qt intentionally keeps very
    // small.  SINAX pages are long dashboards, so scale those deltas while keeping
    // ordinary wheel movement predictable.  The handler is scoped to the whole
    // Flickable even though it lives inside the reusable scrollbar component.
    WheelHandler {
        id: acceleratedWheel
        parent: control.flickable
        enabled: control.flickable !== null
        target: null
        orientation: Qt.Vertical
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad

        onWheel: function(event) {
            if (!control.flickable || control.flickable.contentHeight <= control.flickable.height)
                return

            var delta = 0
            if (event.pixelDelta.y !== 0) {
                // Windows precision touchpad / two-finger scrolling.
                delta = event.pixelDelta.y * control.touchpadScrollMultiplier
            } else if (event.angleDelta.y !== 0) {
                // Traditional mouse wheel: 120 angle units per common wheel step.
                delta = (event.angleDelta.y / 120.0) * control.mouseWheelStepPixels
            }

            if (delta === 0)
                return

            var maxY = Math.max(0, control.flickable.contentHeight - control.flickable.height)
            var nextY = control.flickable.contentY - delta
            control.flickable.contentY = Math.max(0, Math.min(maxY, nextY))
            event.accepted = true
        }
    }

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

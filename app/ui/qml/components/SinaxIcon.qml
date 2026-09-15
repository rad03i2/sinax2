import QtQuick
import ".."

Item {
    id: root
    property string iconName: "folder"
    property string variant: "regular" // "regular" | "filled"
    property bool active: false
    property color color: active ? Theme.iconActive : (!enabled ? Theme.iconDisabled : Theme.iconDefault)
    property int size: Theme.iconMedium
    property bool mirrored: false

    implicitWidth: size
    implicitHeight: size
    opacity: enabled ? 1.0 : 0.45

    // Directional icons that automatically mirror in RTL
    readonly property bool isDirectional: (
        iconName === "back" || iconName === "forward" ||
        iconName === "chevron_left" || iconName === "chevron_right" ||
        iconName === "undo" || iconName === "redo" ||
        iconName === "arrow_left" || iconName === "arrow_right" ||
        iconName === "prev" || iconName === "next"
    )

    readonly property bool shouldMirror: mirrored || (LayoutMirroring.enabled && isDirectional)
    readonly property string resolvedVariantName: (active || variant === "filled") ? (iconName + "_filled") : iconName

    visible: root.iconName !== ""

    Image {
        id: img
        anchors.centerIn: parent
        width: root.size
        height: root.size
        source: root.iconName !== "" ? ("image://sinax/" + root.resolvedVariantName + "/" + root.color + "/" + root.size + (root.shouldMirror ? "?mirrored=1" : "")) : ""
        sourceSize.width: root.size
        sourceSize.height: root.size
        fillMode: Image.PreserveAspectFit
        smooth: true
        asynchronous: false
    }
}


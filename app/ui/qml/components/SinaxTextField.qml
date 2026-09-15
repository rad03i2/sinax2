import QtQuick
import ".."

Rectangle {
    id: root
    property alias text: input.text
    property string placeholderText: ""
    property alias label: root.placeholderText
    property alias readOnly: input.readOnly
    property alias echoMode: input.echoMode
    property bool forceLTR: false

    signal accepted()
    signal textEdited()

    implicitWidth: 240
    implicitHeight: 36
    radius: Theme.radiusSmall
    color: Theme.surface
    border.color: input.activeFocus ? Theme.primary : Theme.borderSubtle
    border.width: 1

    Behavior on border.color {
        ColorAnimation { duration: Theme.durationFast }
    }

    // Smart detection: technical content (paths, IPs, hashes, code) -> LTR
    readonly property bool isTechnicalContent: {
        if (forceLTR) return true;
        var t = input.text.trim();
        if (t.length === 0) return false;
        // Check drive path (e.g. C:\ or /usr/), IP address, URL, or starting with latin char
        if (/^[A-Za-z]:\\|^\/|^https?:\/\/|^\d{1,3}\.\d{1,3}\./.test(t)) return true;
        // Check if first strong direction char is latin/digit
        var firstChar = t.charCodeAt(0);
        return (firstChar >= 48 && firstChar <= 57) || (firstChar >= 65 && firstChar <= 90) || (firstChar >= 97 && firstChar <= 122);
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingM
        anchors.rightMargin: Theme.spacingM
        verticalAlignment: TextInput.AlignVCenter
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBody
        color: Theme.textPrimary
        selectionColor: Theme.primary
        selectedTextColor: Theme.textOnPrimary
        clip: true

        // Smart text alignment
        horizontalAlignment: root.isTechnicalContent ? TextInput.AlignLeft : TextInput.AlignRight

        Text {
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: root.isTechnicalContent ? Text.AlignLeft : Text.AlignRight
            text: root.placeholderText
            color: Theme.textMuted
            font: input.font
            visible: !input.text && !input.activeFocus
        }

        onAccepted: root.accepted()
        onTextEdited: root.textEdited()
    }
}

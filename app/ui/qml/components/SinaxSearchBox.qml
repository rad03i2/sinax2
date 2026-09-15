import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property alias text: input.text
    property string placeholderText: "البحث السريع..."

    signal searchChanged(string query)
    signal cleared()

    implicitWidth: 220
    implicitHeight: 34
    radius: Theme.radiusSmall
    color: Theme.surfaceElevated
    border.color: input.activeFocus ? Theme.primary : Theme.borderSubtle
    border.width: 1

    Behavior on border.color {
        ColorAnimation { duration: Theme.durationFast }
    }

    function clearSearchFocus() {
        input.focus = false;
        if (root.parent) {
            root.parent.forceActiveFocus();
        }
    }

    onVisibleChanged: {
        if (!visible) {
            clearSearchFocus();
        }
    }

    Connections {
        target: typeof navController !== "undefined" ? navController : null
        function onCurrentRouteChanged() {
            root.clearSearchFocus();
        }
        function onOpenSectionIdChanged() {
            root.clearSearchFocus();
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 10
        spacing: 6
        layoutDirection: Qt.RightToLeft

        // Search Icon on the right
        SinaxIcon {
            iconName: "search"
            size: 15
            color: input.activeFocus ? Theme.primary : Theme.textSecondary
        }

        // Input Field
        TextInput {
            id: input
            Layout.fillWidth: true
            Layout.fillHeight: true
            verticalAlignment: TextInput.AlignVCenter
            horizontalAlignment: TextInput.AlignRight
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            color: Theme.textPrimary
            clip: true
            cursorVisible: activeFocus

            Keys.onEscapePressed: {
                root.clearSearchFocus();
            }

            Text {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                text: root.placeholderText
                color: Theme.textMuted
                font: input.font
                visible: !input.text && !input.activeFocus
            }

            onTextChanged: {
                root.searchChanged(input.text);
            }
        }

        // Clear button (X) on the left
        Item {
            visible: input.text !== ""
            width: 18
            height: 18

            Rectangle {
                anchors.centerIn: parent
                width: 16
                height: 16
                radius: 8
                color: clearMouse.containsMouse ? Theme.surfaceHover : "transparent"

                SinaxIcon {
                    anchors.centerIn: parent
                    iconName: "dismiss"
                    size: Theme.iconXS
                    color: Theme.textSecondary
                }

                MouseArea {
                    id: clearMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        input.text = "";
                        root.cleared();
                    }
                }
            }
        }
    }
}

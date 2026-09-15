import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root
    property string title: "تأكيد العملية"
    property string message: ""
    property string confirmText: "تأكيد"
    property string cancelText: "إلغاء"
    property string variant: "primary" // "primary" or "danger"
    property bool isDangerous: variant === "danger"
    property bool isOpen: false

    signal accepted()
    signal rejected()

    anchors.fill: parent
    visible: opacity > 0
    opacity: isOpen ? 1 : 0
    z: 99999

    Behavior on opacity {
        NumberAnimation { duration: Theme.durationNormal }
    }

    // Backdrop
    Rectangle {
        anchors.fill: parent
        color: "#AA000000"
        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.isOpen = false;
                root.rejected();
            }
        }
    }

    // Modal Card
    Rectangle {
        id: dialogCard
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 420)
        implicitHeight: dialogLayout.implicitHeight + Theme.spacingXL * 2
        radius: Theme.radiusLarge
        color: Theme.surfaceElevated
        border.color: root.isDangerous ? Theme.error : Theme.borderSubtle
        border.width: 1

        scale: root.isOpen ? 1.0 : 0.95
        Behavior on scale {
            NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic }
        }

        ColumnLayout {
            id: dialogLayout
            anchors.fill: parent
            anchors.margins: Theme.spacingXL
            spacing: Theme.spacingL

            // Title Row
            RowLayout {
                Layout.fillWidth: true
                layoutDirection: Qt.RightToLeft
                spacing: Theme.spacingM

                SinaxIcon {
                    iconName: root.isDangerous ? "shield" : "info"
                    color: root.isDangerous ? Theme.error : Theme.primary
                    size: 22
                }

                Text {
                    text: root.title
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLarge
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    horizontalAlignment: Text.AlignRight
                    Layout.fillWidth: true
                }
            }

            // Message text
            Text {
                text: root.message
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true
            }

            Item { height: 8 }

            // Action Buttons Row
            RowLayout {
                Layout.fillWidth: true
                layoutDirection: Qt.RightToLeft
                spacing: Theme.spacingM

                SinaxButton {
                    text: root.confirmText
                    variant: root.isDangerous ? "danger" : "primary"
                    Layout.preferredWidth: 120
                    onClicked: {
                        root.isOpen = false;
                        root.accepted();
                    }
                }

                SinaxButton {
                    text: root.cancelText
                    variant: "secondary"
                    Layout.preferredWidth: 100
                    onClicked: {
                        root.isOpen = false;
                        root.rejected();
                    }
                }

                Item { Layout.fillWidth: true }
            }
        }
    }

    function showDialog(titleText, msgText, isDanger) {
        title = titleText;
        message = msgText;
        variant = isDanger ? "danger" : "primary";
        isOpen = true;
    }
}

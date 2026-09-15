import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string logText: ""
    property bool isExpanded: false

    signal cleared()

    implicitWidth: parent ? parent.width : 700
    implicitHeight: root.isExpanded ? 240 : 44

    Behavior on implicitHeight { NumberAnimation { duration: Theme.durationNormal; easing.type: Theme.standardEasing } }

    Rectangle {
        anchors.fill: parent
        color: Theme.surface2
        radius: Theme.radiusMedium
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Header Bar
            Rectangle {
                Layout.fillWidth: true
                height: 44
                color: "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Image {
                        width: 16
                        height: 16
                        source: "image://sinax/tools/" + encodeURIComponent(Theme.textSecondary) + "/16"
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        text: "سجل العمليات والمخرجات التقنية (Technical Output)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Item { Layout.fillWidth: true }

                    // Copy Log
                    SinaxIconButton {
                        iconName: "copy"
                        iconSize: 14
                        tooltipText: "نسخ السجل"
                        onClicked: {
                            logEdit.selectAll();
                            logEdit.copy();
                            logEdit.deselect();
                        }
                    }

                    // Toggle Expand
                    SinaxButton {
                        text: root.isExpanded ? "تصغير السجل ▲" : "توسيع السجل ▼"
                        variant: "ghost"
                        onClicked: root.isExpanded = !root.isExpanded
                    }
                }

                Rectangle {
                    visible: root.isExpanded
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.divider
                }
            }

            // Monospaced Log Area
            ScrollView {
                visible: root.isExpanded
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                TextEdit {
                    id: logEdit
                    text: root.logText.length > 0 ? root.logText : "في انتظار بدء التشخيص..."
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textPrimary
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    padding: Theme.spacingM
                }
            }
        }
    }
}

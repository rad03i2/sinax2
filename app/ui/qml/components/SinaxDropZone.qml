import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string iconName: "folder"
    property string promptText: "اسحب الملفات أو المجلدات وأفلتها هنا..."
    property string formatHint: "يدعم جميع أنواع الملفات والمجلدات والمستندات"
    property string actionText: "أو استعراض الملفات"
    property bool isCompact: false
    property int droppedCount: 0

    // Compatibility aliases
    property alias titleText: root.promptText
    property alias subtitleText: root.formatHint
    property alias browseButtonText: root.actionText
    signal fileDropped(string fileUrl)

    signal filesDropped(var fileUrls)
    signal browseClicked()

    implicitWidth: 500
    implicitHeight: root.isCompact ? 90 : 160

    Rectangle {
        id: dropBox
        anchors.fill: parent
        radius: Theme.radiusLarge
        color: dropArea.containsDrag ? Theme.primaryTint : Theme.surface2
        border.color: dropArea.containsDrag ? Theme.primary : Theme.borderSubtle
        border.width: dropArea.containsDrag ? 2 : 1.5

        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
        Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }

        ColumnLayout {
            anchors.centerIn: parent
            spacing: root.isCompact ? 4 : Theme.spacingS
            width: Math.min(parent.width - Theme.spacingL * 2, 450)

            // Icon
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: root.isCompact ? 32 : 44
                height: root.isCompact ? 32 : 44
                radius: width / 2
                color: dropArea.containsDrag ? Theme.primary : (Theme.isDark ? "#1E293B" : "#E2E8F0")

                Image {
                    anchors.centerIn: parent
                    width: root.isCompact ? 16 : 22
                    height: root.isCompact ? 16 : 22
                    source: "image://sinax/" + (root.iconName.length > 0 ? root.iconName : "folder") + "/" + encodeURIComponent(dropArea.containsDrag ? "#FFFFFF" : Theme.primary) + "/22"
                    fillMode: Image.PreserveAspectFit
                }
            }

            // Prompt text
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.promptText
                font.family: Theme.fontFamily
                font.pixelSize: root.isCompact ? Theme.fontSmall : Theme.fontBody
                font.bold: true
                color: dropArea.containsDrag ? Theme.primary : Theme.textPrimary
                horizontalAlignment: Text.AlignHCenter
            }

            // Hint text
            Text {
                visible: !root.isCompact && root.formatHint.length > 0
                Layout.alignment: Qt.AlignHCenter
                text: root.formatHint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                color: Theme.textSecondary
                horizontalAlignment: Text.AlignHCenter
            }

            // Browse button link
            Text {
                visible: root.actionText.length > 0
                Layout.alignment: Qt.AlignHCenter
                text: root.actionText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                font.bold: true
                color: browseMouse.containsMouse ? Theme.primaryHover : Theme.primary

                MouseArea {
                    id: browseMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.browseClicked()
                }
            }
        }

        DropArea {
            id: dropArea
            anchors.fill: parent

            onEntered: function(drag) {
                if (drag.hasUrls) {
                    drag.acceptProposedAction();
                }
            }

            onDropped: function(drop) {
                if (drop.hasUrls) {
                    var urls = [];
                    for (var i = 0; i < drop.urls.length; ++i) {
                        urls.push(drop.urls[i]);
                    }
                    root.droppedCount = urls.length;
                    root.filesDropped(urls);
                    if (urls.length > 0) {
                        root.fileDropped(urls[0]);
                    }
                    drop.acceptProposedAction();
                }
            }
        }
    }
}

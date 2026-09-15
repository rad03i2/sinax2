import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string title: "حدث خطأ غير متوقع"
    property string message: "تعذر إكمال العملية بنجاح. يرجى التحقق من المدخلات أو المحاولة مرة أخرى."
    property string technicalDetails: ""
    property string retryText: "إعادة المحاولة"
    property bool showRetry: true

    signal retryClicked()

    implicitWidth: 420
    implicitHeight: errCol.implicitHeight + Theme.spacingXL * 2

    property bool detailsExpanded: false

    ColumnLayout {
        id: errCol
        anchors.centerIn: parent
        spacing: Theme.spacingM
        width: Math.min(parent.width - Theme.spacingXL * 2, 500)

        // Error icon circle
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 60
            height: 60
            radius: 30
            color: Theme.errorSurface

            Image {
                anchors.centerIn: parent
                width: 30
                height: 30
                source: "image://sinax/warning/" + encodeURIComponent(Theme.error) + "/30"
                fillMode: Image.PreserveAspectFit
            }
        }

        // Title
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: root.title
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontLarge
            font.bold: true
            color: Theme.error
            horizontalAlignment: Text.AlignHCenter
        }

        // Friendly message
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: root.message
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            color: Theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            lineHeight: 1.25
        }

        // Expandable Technical Details toggle
        RowLayout {
            visible: root.technicalDetails.length > 0
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spacingS

            Text {
                text: root.detailsExpanded ? "إخفاء التفاصيل التقنية ▲" : "عرض التفاصيل التقنية ▼"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                font.bold: true
                color: Theme.textMuted

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.detailsExpanded = !root.detailsExpanded
                }
            }
        }

        // Raw Technical Details box
        Rectangle {
            visible: root.detailsExpanded && root.technicalDetails.length > 0
            Layout.fillWidth: true
            implicitHeight: Math.min(160, techText.implicitHeight + Theme.spacingM * 2)
            color: Theme.surface2
            radius: Theme.radiusSmall
            border.color: Theme.borderSubtle
            clip: true

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spacingM

                TextEdit {
                    id: techText
                    text: root.technicalDetails
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textMuted
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                }
            }
        }

        Item { height: Theme.spacingS }

        // Retry Action Button
        SinaxButton {
            visible: root.showRetry
            Layout.alignment: Qt.AlignHCenter
            text: root.retryText
            iconName: "sync"
            variant: "primary"
            onClicked: root.retryClicked()
        }
    }
}

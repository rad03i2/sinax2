import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string fileName: "document_proposal.docx"
    property string sourcePath: "C:\\Users\\Work\\document_proposal.docx"
    property string sourceModified: "اليوم 14:30 (الحجم: 2.4 MB)"
    property string destinationPath: "D:\\Backups\\document_proposal.docx"
    property string destinationModified: "أمس 18:15 (الحجم: 2.1 MB)"

    signal resolveKeepSource()
    signal resolveKeepDestination()
    signal resolveKeepBoth()
    signal resolveSkip()

    implicitWidth: 620
    implicitHeight: mainCol.implicitHeight + Theme.spacingL * 2

    Rectangle {
        anchors.fill: parent
        color: Theme.surface
        radius: Theme.radiusLarge
        border.color: Theme.warning
        border.width: 1.5

        ColumnLayout {
            id: mainCol
            anchors.fill: parent
            anchors.margins: Theme.spacingL
            spacing: Theme.spacingM

            // Header: Warning Title
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                Rectangle {
                    width: 36
                    height: 36
                    radius: Theme.radiusSmall
                    color: Theme.warningSurface

                    Image {
                        anchors.centerIn: parent
                        width: 20
                        height: 20
                        source: "image://sinax/warning/" + encodeURIComponent(Theme.warning) + "/20"
                        fillMode: Image.PreserveAspectFit
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true

                    Text {
                        text: "تعارض في تزامن الملف: " + root.fileName
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMedium
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Text {
                        text: "الملف موجود في كلا الطرفين بتعديلات وتواريخ مختلفة. اختر كيف تريد التعامل مع التعارض:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                }
            }

            // Side-by-Side Version Cards
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                // Version A (Source)
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 80
                    radius: Theme.radiusMedium
                    color: Theme.surface2
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingM
                        spacing: 2

                        Text {
                            text: "النسخة المحلية (المصدر A)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.bold: true
                            color: Theme.primary
                        }

                        Text {
                            text: root.sourceModified
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                            color: Theme.textPrimary
                        }

                        Text {
                            text: root.sourcePath
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontCaption - 1
                            color: Theme.textMuted
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }
                }

                // Version B (Destination)
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 80
                    radius: Theme.radiusMedium
                    color: Theme.surface2
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingM
                        spacing: 2

                        Text {
                            text: "نسخة النسخ الاحتياطي (الوجهة B)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.bold: true
                            color: Theme.warning
                        }

                        Text {
                            text: root.destinationModified
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                            color: Theme.textPrimary
                        }

                        Text {
                            text: root.destinationPath
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontCaption - 1
                            color: Theme.textMuted
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // Resolution Action Buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                SinaxButton {
                    text: "الاحتفاظ بالمصدر (A)"
                    variant: "primary"
                    onClicked: root.resolveKeepSource()
                }

                SinaxButton {
                    text: "الاحتفاظ بالنسخة الاحتياطية (B)"
                    variant: "secondary"
                    onClicked: root.resolveKeepDestination()
                }

                SinaxButton {
                    text: "الاحتفاظ بالاثنين معاً"
                    variant: "secondary"
                    onClicked: root.resolveKeepBoth()
                }

                Item { Layout.fillWidth: true }

                SinaxButton {
                    text: "تخطي هذا الملف"
                    variant: "ghost"
                    onClicked: root.resolveSkip()
                }
            }
        }
    }
}

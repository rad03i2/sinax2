import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../.."
import "../../components"

Item {
    id: root

    implicitWidth: parent ? parent.width : 700
    implicitHeight: benchCol.implicitHeight + Theme.spacingL * 2

    Rectangle {
        anchors.fill: parent
        color: Theme.surface
        radius: Theme.radiusLarge
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            id: benchCol
            anchors.fill: parent
            anchors.margins: Theme.spacingL
            spacing: Theme.spacingM

            // Header Bar
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                Rectangle {
                    width: 36
                    height: 36
                    radius: Theme.radiusSmall
                    color: Theme.isDark ? "#1E293B" : "#F1F5F9"

                    Image {
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        source: "image://sinax/tools/" + encodeURIComponent(Theme.primary) + "/18"
                        fillMode: Image.PreserveAspectFit
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: quickToolsController.activeToolTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCardTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Text {
                        text: "معالجة فورية وتلقائية داخل المختبر"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textSecondary
                    }
                }

                SinaxBadge {
                    text: quickToolsController.statusMessage
                    variant: "success"
                }
            }

            // Input / Output Split in Row
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingL
                layoutDirection: Qt.RightToLeft

                // Input Box
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 180
                    color: Theme.surface2
                    radius: Theme.radiusMedium
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingM
                        spacing: Theme.spacingS

                        RowLayout {
                            Layout.fillWidth: true
                            layoutDirection: Qt.RightToLeft

                            Text {
                                text: "المدخلات (نص أو مسار ملف):"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textSecondary
                            }
                            Item { Layout.fillWidth: true }
                            SinaxIconButton {
                                iconName: "clean"
                                iconSize: 13
                                tooltipText: "مسح المدخل"
                                onClicked: {
                                    inEdit.text = "";
                                    quickToolsController.setWorkbenchInput("");
                                }
                            }
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            TextEdit {
                                id: inEdit
                                text: quickToolsController.workbenchInput
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontBody
                                color: Theme.textPrimary
                                selectByMouse: true
                                wrapMode: TextEdit.WrapAnywhere
                                onTextChanged: quickToolsController.setWorkbenchInput(text)
                            }
                        }
                    }
                }

                // Output Box
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 180
                    color: Theme.surface2
                    radius: Theme.radiusMedium
                    border.color: Theme.primary
                    border.width: 1.5

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingM
                        spacing: Theme.spacingS

                        RowLayout {
                            Layout.fillWidth: true
                            layoutDirection: Qt.RightToLeft

                            Text {
                                text: "النتيجة والمخرجات:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.primary
                            }
                            Item { Layout.fillWidth: true }
                            SinaxIconButton {
                                iconName: "copy"
                                iconSize: 13
                                tooltipText: "نسخ النتيجة"
                                onClicked: {
                                    outEdit.selectAll();
                                    outEdit.copy();
                                    outEdit.deselect();
                                }
                            }
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            TextEdit {
                                id: outEdit
                                text: quickToolsController.workbenchOutput
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontBody
                                color: Theme.textPrimary
                                readOnly: true
                                selectByMouse: true
                                wrapMode: TextEdit.WrapAnywhere
                            }
                        }
                    }
                }
            }

            // Workbench Actions Row
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                SinaxButton {
                    text: "تنفيذ المعالجة"
                    iconName: "play"
                    variant: "primary"
                    onClicked: quickToolsController.executeWorkbench()
                }

                SinaxButton {
                    text: "نسخ النتيجة إلى الحافظة"
                    variant: "secondary"
                    iconName: "copy"
                    onClicked: {
                        outEdit.selectAll();
                        outEdit.copy();
                        outEdit.deselect();
                    }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "يمكنك سحب أي ملف مباشرة إلى الصفحة لفحص بصمته فورياً"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textMuted
                }
            }
        }
    }
}

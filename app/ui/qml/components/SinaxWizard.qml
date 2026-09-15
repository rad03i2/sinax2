import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    // Array of step objects: [{ title: "المصادر", subtitle: "تحديد الملفات" }, ...]
    property var steps: []
    property int currentStep: 0
    property bool canNext: true
    property bool canBack: currentStep > 0
    property bool canFinish: currentStep === steps.length - 1
    property bool isBusy: false

    // Content container for custom step views
    default property alias contentData: stepStack.data

    signal nextClicked()
    signal backClicked()
    signal finishClicked()
    signal cancelClicked()

    implicitWidth: 700
    implicitHeight: 500

    Rectangle {
        anchors.fill: parent
        color: Theme.surface
        radius: Theme.radiusLarge
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Stepper Header
            Rectangle {
                Layout.fillWidth: true
                height: 72
                color: Theme.surface2
                radius: Theme.radiusLarge

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingS
                    layoutDirection: Qt.RightToLeft

                    Repeater {
                        model: root.steps

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingS
                            layoutDirection: Qt.RightToLeft

                            // Step Circle Indicator
                            Rectangle {
                                width: 28
                                height: 28
                                radius: 14
                                color: {
                                    if (index < root.currentStep) return Theme.success;
                                    if (index === root.currentStep) return Theme.primary;
                                    return Theme.surface3;
                                }

                                SinaxIcon {
                                    visible: index < root.currentStep
                                    anchors.centerIn: parent
                                    iconName: "check"
                                    size: Theme.iconSmall
                                    color: "#FFFFFF"
                                }

                                Text {
                                    visible: index >= root.currentStep
                                    anchors.centerIn: parent
                                    text: String(index + 1)
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    font.bold: true
                                    color: index === root.currentStep ? "#FFFFFF" : Theme.textMuted
                                }
                            }

                            // Step Title & Subtitle
                            ColumnLayout {
                                spacing: 0
                                Layout.fillWidth: true

                                Text {
                                    text: modelData.title ? modelData.title : ("خطوة " + (index + 1))
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    font.bold: index === root.currentStep
                                    color: index <= root.currentStep ? Theme.textPrimary : Theme.textMuted
                                    elide: Text.ElideRight
                                }

                                Text {
                                    visible: modelData.subtitle && modelData.subtitle.length > 0
                                    text: modelData.subtitle ? modelData.subtitle : ""
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontCaption
                                    color: Theme.textMuted
                                    elide: Text.ElideRight
                                }
                            }

                            // Connecting line between steps (except for the last step)
                            Rectangle {
                                visible: index < root.steps.length - 1
                                Layout.fillWidth: true
                                height: 2
                                color: index < root.currentStep ? Theme.success : Theme.divider
                            }
                        }
                    }
                }

                // Divider under stepper
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.divider
                }
            }

            // Step Content Area (Stack or placeholder)
            Item {
                id: stepStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
            }

            // Wizard Footer / Action Buttons
            Rectangle {
                Layout.fillWidth: true
                height: 60
                color: Theme.surface2

                Rectangle {
                    anchors.top: parent.top
                    width: parent.width
                    height: 1
                    color: Theme.divider
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    // Cancel button
                    SinaxButton {
                        text: "إلغاء"
                        variant: "ghost"
                        enabled: !root.isBusy
                        onClicked: root.cancelClicked()
                    }

                    Item { Layout.fillWidth: true } // Spacer

                    // Back button
                    SinaxButton {
                        visible: root.currentStep > 0
                        text: "السابق  →"
                        variant: "secondary"
                        enabled: root.canBack && !root.isBusy
                        onClicked: {
                            if (root.currentStep > 0) {
                                root.currentStep--;
                                root.backClicked();
                            }
                        }
                    }

                    // Next button (if not at last step)
                    SinaxButton {
                        visible: root.currentStep < root.steps.length - 1
                        text: "التالي  ←"
                        variant: "primary"
                        enabled: root.canNext && !root.isBusy
                        onClicked: {
                            if (root.currentStep < root.steps.length - 1) {
                                root.currentStep++;
                                root.nextClicked();
                            }
                        }
                    }

                    // Finish button (at last step)
                    SinaxButton {
                        visible: root.currentStep === root.steps.length - 1
                        text: "إنهاء وتطبيق"
                        iconName: "check"
                        variant: "primary"
                        enabled: root.canFinish && !root.isBusy
                        loading: root.isBusy
                        onClicked: root.finishClicked()
                    }
                }
            }
        }
    }
}

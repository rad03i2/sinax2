import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property bool isOpen: false

    signal closed()

    anchors.fill: parent
    visible: isOpen && opacity > 0
    opacity: isOpen ? 1 : 0
    enabled: isOpen

    Behavior on opacity { NumberAnimation { duration: Theme.durationNormal } }

    // Backdrop Scrim
    Rectangle {
        anchors.fill: parent
        color: Theme.overlay

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.isOpen = false;
                root.closed();
            }
        }
    }

    // Slide-in Drawer
    Rectangle {
        id: drawer
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        width: Math.min(parent.width, 420)
        color: Theme.surface
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Drawer Header
            Rectangle {
                Layout.fillWidth: true
                height: 56
                color: Theme.surface2

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingS
                    layoutDirection: Qt.RightToLeft

                    Text {
                        text: "مركز العمليات الجارية"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    SinaxBadge {
                        text: String(jobController.activeJobCount) + " نشطة"
                        variant: jobController.activeJobCount > 0 ? "info" : "default"
                    }

                    Item { Layout.fillWidth: true }

                    // Clear Finished Button
                    SinaxIconButton {
                        iconName: "clean"
                        iconSize: 15
                        tooltipText: "مسح العمليات المكتملة"
                        onClicked: jobController.clearFinished()
                    }

                    // Close Drawer Button
                    SinaxIconButton {
                        iconName: "close"
                        iconSize: 14
                        tooltipText: "إغلاق"
                        onClicked: {
                            root.isOpen = false;
                            root.closed();
                        }
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.divider
                }
            }

            // Jobs ListView
            ListView {
                id: jobListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: jobController.jobModel
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: SinaxScrollBar {}

                delegate: Rectangle {
                    width: jobListView.width
                    height: jobCol.implicitHeight + Theme.spacingM * 2
                    color: index % 2 === 1 ? Theme.surface2 : Theme.surface

                    ColumnLayout {
                        id: jobCol
                        anchors {
                            left: parent.left
                            right: parent.right
                            top: parent.top
                            margins: Theme.spacingM
                        }
                        spacing: Theme.spacingS

                        // Header: Title + Module + Status + Cancel
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingS
                            layoutDirection: Qt.RightToLeft

                            Text {
                                text: model.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                font.bold: true
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            SinaxBadge {
                                visible: model.module.length > 0
                                text: model.module
                                variant: "default"
                            }

                            SinaxBadge {
                                text: {
                                    if (model.status === "running") return "جارية";
                                    if (model.status === "completed") return "مكتملة";
                                    if (model.status === "failed") return "فشلت";
                                    if (model.status === "cancelled") return "ملغاة";
                                    return model.status;
                                }
                                variant: {
                                    if (model.status === "running") return "info";
                                    if (model.status === "completed") return "success";
                                    if (model.status === "failed") return "error";
                                    return "default";
                                }
                            }

                            SinaxIconButton {
                                visible: model.status === "running" && model.canCancel
                                iconName: "close"
                                iconSize: 12
                                tooltipText: "إلغاء العملية"
                                onClicked: jobController.cancelJob(model.jobId)
                            }
                        }

                        // Progress Bar (if running)
                        SinaxProgress {
                            visible: model.status === "running"
                            Layout.fillWidth: true
                            value: model.progress
                        }

                        // Step / Speed / ETA details
                        RowLayout {
                            Layout.fillWidth: true
                            layoutDirection: Qt.RightToLeft

                            Text {
                                visible: model.currentStep.length > 0
                                text: model.currentStep
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textMuted
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                visible: model.speed.length > 0
                                text: model.speed
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textSecondary
                            }

                            Text {
                                visible: model.eta.length > 0
                                text: "المتبقي: " + model.eta
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textMuted
                            }
                        }

                        // Error message if failed
                        Text {
                            visible: model.status === "failed" && model.error.length > 0
                            text: model.error
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                            color: Theme.error
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.divider
                    }
                }
            }

            // Empty State when no jobs
            SinaxEmptyState {
                visible: jobController.jobModel.rowCount() === 0
                Layout.alignment: Qt.AlignCenter
                iconName: "tools"
                title: "لا توجد عمليات جارية"
                description: "جميع المهام والعمليات الخلفية ستظهر هنا فور بدئها."
            }
        }
    }
}

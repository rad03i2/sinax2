import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    Rectangle {
        anchors.fill: parent
        color: Theme.background
        z: -1
    }

    ColumnLayout {
        id: contentCol
        anchors.fill: parent
        anchors.margins: Theme.spacingL
        spacing: Theme.spacingM

        // 1. Page Header with Breadcrumbs & Action
        SinaxPageHeader {
            Layout.fillWidth: true
            title: "سجل العمليات الموحد وإمكانية التراجع"
            subtitle: "سجل زمني شامل لعمليات إعادة التسمية، النقل، الدمج، والنسخ مع ميزة التراجع الفوري بنقرة واحدة."
            iconName: "history"
            breadcrumbCurrent: "سجل العمليات"
            actionText: "مسح السجل"
            primaryActionIcon: "delete"
            onActionClicked: historyController.clearHistory()
        }

        // 2. Toolbar & Status Counter
        RowLayout {
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft
            spacing: Theme.spacingM

            SinaxBadge {
                text: String(historyController.totalCount) + " عملية مسجلة"
                variant: "info"
            }

            Item { Layout.fillWidth: true }

            SinaxButton {
                text: "تحديث السجل ⟳"
                variant: "secondary"
                onClicked: historyController.refreshHistory()
            }
        }

        // 3. Operations History Table
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMedium
            color: Theme.surface
            border.color: Theme.borderSubtle
            border.width: 1
            clip: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Header Row
                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    color: Theme.surface2

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spacingM
                        anchors.rightMargin: Theme.spacingM
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingM

                        Text { text: "الوقت والتاريخ"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.textSecondary; Layout.preferredWidth: 130 }
                        Text { text: "نوع العملية"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.textSecondary; Layout.preferredWidth: 140 }
                        Text { text: "عدد الملفات"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.textSecondary; Layout.preferredWidth: 90 }
                        Text { text: "المجلد المستهدف / التفاصيل"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.textSecondary; Layout.fillWidth: true }
                        Text { text: "الحالة"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.textSecondary; Layout.preferredWidth: 80 }
                        Text { text: "الإجراء"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.textSecondary; Layout.preferredWidth: 100 }
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.divider
                    }
                }

                // ListView
                ListView {
                    id: historyList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: historyController.historyModel
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: SinaxScrollBar {}

                    delegate: Rectangle {
                        width: historyList.width
                        height: 48
                        color: index % 2 === 1 ? Theme.surface2 : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spacingM
                            anchors.rightMargin: Theme.spacingM
                            layoutDirection: Qt.RightToLeft
                            spacing: Theme.spacingM

                            Text {
                                text: model.timestamp
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                color: Theme.textSecondary
                                Layout.preferredWidth: 130
                            }

                            Text {
                                text: model.opType
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                font.bold: true
                                color: Theme.primary
                                Layout.preferredWidth: 140
                            }

                            Text {
                                text: String(model.fileCount) + " ملف"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                color: Theme.textPrimary
                                Layout.preferredWidth: 90
                            }

                            Text {
                                text: model.details + " (" + model.targetFolder + ")"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            SinaxBadge {
                                text: model.status
                                variant: model.status === "ناجحة" ? "success" : "danger"
                                Layout.preferredWidth: 80
                            }

                            SinaxButton {
                                visible: model.canRollback
                                text: "تراجع ↶"
                                variant: "secondary"
                                isCompact: true
                                Layout.preferredWidth: 100
                                onClicked: historyController.rollbackRecord(model.recordId)
                            }

                            Item {
                                visible: !model.canRollback
                                Layout.preferredWidth: 100
                            }
                        }
                    }
                }
            }
        }
    }
}

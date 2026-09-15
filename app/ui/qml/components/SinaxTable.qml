import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property var model: null
    property var columns: [] // Array of { id: "colId", title: "العنوان", width: 120, fill: false, align: "right" }
    property int selectedIndex: -1
    property bool alternatingRows: true
    property bool isLoading: false
    property string emptyText: "لا توجد بيانات متاحة"
    property string emptyIcon: "info"
    property int rowHeight: 40

    signal rowClicked(int index, var rowData)
    signal rowDoubleClicked(int index, var rowData)
    signal sortRequested(string columnId, bool ascending)

    property string sortColumn: ""
    property bool sortAscending: true

    implicitWidth: 600
    implicitHeight: 300

    Rectangle {
        anchors.fill: parent
        color: Theme.surface
        radius: Theme.radiusMedium
        border.color: Theme.borderSubtle
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Table Header
            Rectangle {
                Layout.fillWidth: true
                height: 38
                color: Theme.surface2

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacingM
                    anchors.rightMargin: Theme.spacingM
                    spacing: Theme.spacingS
                    layoutDirection: Qt.RightToLeft

                    Repeater {
                        model: root.columns

                        Rectangle {
                            Layout.preferredWidth: modelData.width ? modelData.width : (modelData.fill ? 200 : 100)
                            Layout.fillWidth: modelData.fill ? true : false
                            Layout.fillHeight: true
                            color: "transparent"

                            RowLayout {
                                anchors.fill: parent
                                spacing: 4
                                layoutDirection: Qt.RightToLeft

                                Text {
                                    text: modelData.title
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    font.bold: true
                                    color: Theme.textSecondary
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                    horizontalAlignment: modelData.align === "left" ? Text.AlignLeft : Text.AlignRight
                                }

                                Text {
                                    visible: root.sortColumn === modelData.id
                                    text: root.sortAscending ? "▲" : "▼"
                                    font.pixelSize: 9
                                    color: Theme.primary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (root.sortColumn === modelData.id) {
                                        root.sortAscending = !root.sortAscending;
                                    } else {
                                        root.sortColumn = modelData.id;
                                        root.sortAscending = true;
                                    }
                                    root.sortRequested(root.sortColumn, root.sortAscending);
                                }
                            }
                        }
                    }
                }

                // Divider under header
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.divider
                }
            }

            // Table Rows / ListView
            ListView {
                id: tableList
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: root.model
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    active: true
                    policy: tableList.contentHeight > tableList.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                }

                delegate: Rectangle {
                    width: tableList.width
                    height: root.rowHeight
                    color: {
                        if (index === root.selectedIndex) return Theme.primaryTint;
                        if (rowMouse.containsMouse) return Theme.surfaceHover;
                        if (root.alternatingRows && index % 2 === 1) return Theme.surface2;
                        return Theme.surface;
                    }

                    Behavior on color { ColorAnimation { duration: Theme.durationFast } }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spacingM
                        anchors.rightMargin: Theme.spacingM
                        spacing: Theme.spacingS
                        layoutDirection: Qt.RightToLeft

                        Repeater {
                            model: root.columns

                            Item {
                                Layout.preferredWidth: modelData.width ? modelData.width : (modelData.fill ? 200 : 100)
                                Layout.fillWidth: modelData.fill ? true : false
                                Layout.fillHeight: true

                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: modelData.align === "left" ? Text.AlignLeft : Text.AlignRight
                                    // Extract data role by column id or fallback to display
                                    text: {
                                        var roleName = modelData.id;
                                        if (model && model[roleName] !== undefined) return String(model[roleName]);
                                        if (model && model.display !== undefined) return String(model.display);
                                        return "";
                                    }
                                    font.family: modelData.isMono ? Theme.fontMono : Theme.fontFamily
                                    font.pixelSize: Theme.fontBody
                                    color: index === root.selectedIndex ? Theme.primary : Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    // Row divider
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.divider
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            root.selectedIndex = index;
                            root.rowClicked(index, model);
                        }
                        onDoubleClicked: {
                            root.selectedIndex = index;
                            root.rowDoubleClicked(index, model);
                        }
                    }
                }
            }
        }

        // Loading Overlay
        Rectangle {
            visible: root.isLoading
            anchors.fill: parent
            color: Theme.overlay

            SinaxProgress {
                anchors.centerIn: parent
                indeterminate: true
                implicitWidth: 160
            }
        }

        // Empty State Overlay
        SinaxEmptyState {
            visible: !root.isLoading && (root.model ? (root.model.count === 0 || root.model.rowCount === 0) : true)
            anchors.centerIn: parent
            title: root.emptyText
            iconName: root.emptyIcon
        }
    }
}

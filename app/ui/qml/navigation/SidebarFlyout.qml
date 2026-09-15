import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Rectangle {
    id: root
    width: 230
    implicitHeight: Math.min(contentCol.implicitHeight + 16, 420)
    radius: Theme.radiusMedium
    color: Theme.surfaceElevated
    border.color: Theme.borderSubtle
    border.width: 1

    Keys.onEscapePressed: navController.closeSection()

    ColumnLayout {
        id: contentCol
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4
        layoutDirection: Qt.RightToLeft

        // Header showing parent section title
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 6
            spacing: 8
            layoutDirection: Qt.RightToLeft

            SinaxIcon {
                iconName: {
                    for (var i = 0; i < navController.navModel.rowCount(); i++) {
                        var idx = navController.navModel.index(i, 0);
                        if (navController.navModel.data(idx, navController.navModel.IdRole) === navController.openSectionId) {
                            return navController.navModel.data(idx, navController.navModel.IconRole) || "folder";
                        }
                    }
                    return "folder";
                }
                size: Theme.iconSmall
                color: Theme.primary
            }

            Text {
                text: {
                    for (var i = 0; i < navController.navModel.rowCount(); i++) {
                        var idx = navController.navModel.index(i, 0);
                        if (navController.navModel.data(idx, navController.navModel.IdRole) === navController.openSectionId) {
                            return navController.navModel.data(idx, navController.navModel.TitleRole) || "";
                        }
                    }
                    return "";
                }
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                font.weight: Font.Bold
                color: Theme.primary
                Layout.fillWidth: true
                elide: Text.ElideLeft
            }

            SinaxIconButton {
                iconName: "dismiss"
                iconSize: 12
                tooltipText: "إغلاق"
                onClicked: navController.closeSection()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Theme.borderSubtle
        }

        // Child sub-items list
        ListView {
            id: flyoutList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds
            model: navController.navModel

            delegate: Item {
                id: itemDelegate
                width: flyoutList.width
                visible: model.isSub && model.parentId === navController.openSectionId
                height: visible ? 34 : 0

                readonly property bool isCurrent: navController.currentRoute === model.route

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radiusSmall
                    color: itemMouse.pressed ? Theme.surfacePressed : (isCurrent ? Theme.primaryTint : (itemMouse.containsMouse ? Theme.surfaceHover : "transparent"))

                    // Active indicator pill
                    Rectangle {
                        visible: itemDelegate.isCurrent
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: 3
                        height: 16
                        radius: 1.5
                        color: Theme.primary
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 10
                        spacing: 8
                        layoutDirection: Qt.RightToLeft

                        SinaxIcon {
                            iconName: model.itemIcon || "file"
                            size: Theme.iconSmall
                            active: itemDelegate.isCurrent
                            color: itemDelegate.isCurrent ? Theme.iconActive : (itemMouse.containsMouse ? Theme.iconHover : Theme.iconDefault)
                        }

                        Text {
                            text: model.itemTitle || ""
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.weight: itemDelegate.isCurrent ? Font.Bold : Font.Normal
                            color: itemDelegate.isCurrent ? Theme.primary : (itemMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                            Layout.fillWidth: true
                            elide: Text.ElideLeft
                        }

                        SinaxBadge {
                            visible: model.badge !== ""
                            text: model.badge || ""
                            statusType: "info"
                        }
                    }

                    MouseArea {
                        id: itemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            navController.openRoute(model.route);
                            navController.closeSection();
                        }
                    }
                }
            }
        }
    }
}

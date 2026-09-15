import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property int selectedIndex: 0

    anchors.fill: parent
    visible: commandPaletteController.isOpen
    z: 9999

    function closePalette() {
        searchInput.focus = false;
        commandPaletteController.setOpen(false);
        if (root.parent) {
            root.parent.forceActiveFocus();
        }
    }

    onVisibleChanged: {
        if (!visible) {
            searchInput.focus = false;
            if (root.parent) root.parent.forceActiveFocus();
        } else {
            searchInput.text = "";
            searchInput.forceActiveFocus();
        }
    }

    // Keyboard shortcut handler for Esc
    Keys.onEscapePressed: root.closePalette()

    // Backdrop Scrim
    Rectangle {
        anchors.fill: parent
        color: Theme.overlay

        MouseArea {
            anchors.fill: parent
            onClicked: root.closePalette()
        }
    }

    // Centered Search Box & Results Container
    Rectangle {
        id: paletteDialog
        width: Math.min(parent.width - Theme.spacingXL * 2, 600)
        height: Math.min(parent.height - Theme.spacingXL * 2, 460)
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -40
        radius: Theme.radiusLarge
        color: Theme.surface
        border.color: Theme.primary
        border.width: 1.5

        HoverHandler {
            id: paletteHover
            onHoveredChanged: {
                if (!hovered && root.visible) {
                    hoverLeaveTimer.restart();
                } else {
                    hoverLeaveTimer.stop();
                }
            }
        }

        Timer {
            id: hoverLeaveTimer
            interval: 350
            repeat: false
            onTriggered: {
                if (!paletteHover.hovered && root.visible) {
                    root.closePalette();
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Search Header Input Row
            Rectangle {
                Layout.fillWidth: true
                height: 56
                color: Theme.surface2
                radius: Theme.radiusLarge

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Image {
                        width: 20
                        height: 20
                        source: "image://sinax/search/" + encodeURIComponent(Theme.primary) + "/20"
                        fillMode: Image.PreserveAspectFit
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontLarge
                        color: Theme.textPrimary
                        clip: true
                        cursorVisible: activeFocus
                        focus: root.visible

                        // Custom placeholder
                        Text {
                            anchors.fill: parent
                            text: "ابحث عن أي أداة أو صفحة أو إعداد (Ctrl+K)..."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLarge
                            color: Theme.textMuted
                            visible: !searchInput.text && !searchInput.inputMethodComposing
                        }

                        onTextChanged: {
                            root.selectedIndex = 0;
                            commandPaletteController.search(text);
                        }

                        Keys.onDownPressed: {
                            if (resultsList.count > 0) {
                                root.selectedIndex = Math.min(root.selectedIndex + 1, resultsList.count - 1);
                                resultsList.positionViewAtIndex(root.selectedIndex, ListView.Contain);
                            }
                        }

                        Keys.onUpPressed: {
                            if (resultsList.count > 0) {
                                root.selectedIndex = Math.max(root.selectedIndex - 1, 0);
                                resultsList.positionViewAtIndex(root.selectedIndex, ListView.Contain);
                            }
                        }

                        Keys.onReturnPressed: {
                            if (resultsList.count > 0 && root.selectedIndex < resultsList.count) {
                                var currentItem = commandPaletteController.model.data(
                                    commandPaletteController.model.index(root.selectedIndex, 0),
                                    commandPaletteController.model.RouteRole
                                );
                                if (currentItem) {
                                    root.closePalette();
                                    commandPaletteController.selectCommand(currentItem);
                                }
                            }
                        }

                        Keys.onEscapePressed: root.closePalette()
                    }

                    SinaxBadge {
                        text: "Esc للخروج"
                        variant: "default"
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.divider
                }
            }

            // Results List
            ListView {
                id: resultsList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: commandPaletteController.model
                currentIndex: root.selectedIndex

                ScrollBar.vertical: SinaxScrollBar {}

                delegate: Rectangle {
                    width: resultsList.width
                    height: 54
                    color: index === root.selectedIndex ? Theme.primaryTint : (itemMouse.containsMouse ? Theme.surfaceHover : "transparent")

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingM
                        spacing: Theme.spacingM
                        layoutDirection: Qt.RightToLeft

                        // Command Icon
                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusSmall
                            color: Theme.isDark ? "#1E293B" : "#E2E8F0"

                            Image {
                                anchors.centerIn: parent
                                width: 16
                                height: 16
                                source: "image://sinax/" + model.icon + "/" + encodeURIComponent(Theme.primary) + "/16"
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        // Title + Subtitle
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            Text {
                                text: model.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                font.bold: true
                                color: index === root.selectedIndex ? Theme.primary : Theme.textPrimary
                                elide: Text.ElideRight
                            }

                            Text {
                                text: model.subtitle
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                            }
                        }

                        // Category Badge
                        SinaxBadge {
                            text: model.category
                            variant: "default"
                        }

                        Text {
                            text: "↵"
                            font.pixelSize: 14
                            font.bold: true
                            color: Theme.primary
                            visible: index === root.selectedIndex
                        }
                    }

                    MouseArea {
                        id: itemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.closePalette();
                            commandPaletteController.selectCommand(model.route);
                        }
                    }
                }
            }

            // Empty state
            SinaxEmptyState {
                visible: resultsList.count === 0
                Layout.alignment: Qt.AlignCenter
                iconName: "search"
                title: "لا توجد نتائج مطابقة"
                description: "جرب البحث بكلمة مختلفة مثل: نسخ، تشخيص، أدوات..."
            }
        }
    }
}

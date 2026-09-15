import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string toolId: ""
    property string title: ""
    property string description: ""
    property string iconName: "tools"
    property string iconColor: Theme.primary
    property string badgeText: "جاهز"
    property string badgeVariant: "success"
    property alias badgeType: root.badgeVariant
    property bool isReady: true
    property bool favorite: false
    property alias isFavorite: root.favorite
    property bool requiresAdmin: false
    property bool beta: false
    property string actionText: "فتح الأداة  ←"

    signal clicked()
    signal actionClicked()
    signal favoriteToggled(bool fav)

    implicitWidth: 320
    implicitHeight: cardContent.implicitHeight + Theme.spacingL * 2

    Rectangle {
        id: cardBg
        anchors.fill: parent
        radius: Theme.radiusLarge
        color: cardMouse.containsMouse ? Theme.surfaceHover : Theme.surface
        border.color: cardMouse.containsMouse ? Theme.primary : Theme.borderSubtle
        border.width: cardMouse.containsMouse ? 1.5 : 1

        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
        Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }

        ColumnLayout {
            id: cardContent
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: Theme.spacingL
            }
            spacing: Theme.spacingM

            // Top Row: Icon + Badges + Favorite Toggle
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                // Tool Icon Box
                Rectangle {
                    width: 42
                    height: 42
                    radius: Theme.radiusMedium
                    color: Theme.isDark ? "#1E293B" : "#F1F5F9"

                    Image {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        source: "image://sinax/" + root.iconName + "/" + encodeURIComponent(root.iconColor) + "/22"
                        fillMode: Image.PreserveAspectFit
                    }
                }

                Item { Layout.fillWidth: true } // Spacer

                // Admin Badge (if required)
                SinaxBadge {
                    visible: root.requiresAdmin
                    text: "مسؤول"
                    variant: "warning"
                }

                // Beta Badge (if applicable)
                SinaxBadge {
                    visible: root.beta
                    text: "تجريبي"
                    variant: "info"
                }

                // Status Badge
                SinaxBadge {
                    visible: root.badgeText.length > 0
                    text: root.badgeText
                    variant: root.isReady ? root.badgeVariant : "default"
                }

                // Favorite Star Button
                SinaxIconButton {
                    iconName: root.favorite ? "star-fill" : "star"
                    iconColor: root.favorite ? "#F59E0B" : Theme.textMuted
                    iconSize: 16
                    tooltipText: root.favorite ? "إزالة من المفضلة" : "إضافة إلى المفضلة"
                    onClicked: {
                        root.favorite = !root.favorite;
                        root.favoriteToggled(root.favorite);
                    }
                }
            }

            // Title
            Text {
                text: root.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCardTitle
                font.bold: true
                color: root.isReady ? Theme.textPrimary : Theme.textMuted
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignRight
            }

            // Description
            Text {
                text: root.description
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textSecondary
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideRight
                lineHeight: 1.25
                horizontalAlignment: Text.AlignRight
            }

            Item { height: Theme.spacingS } // Spacing

            // Action Row
            RowLayout {
                Layout.fillWidth: true
                layoutDirection: Qt.RightToLeft

                Item { Layout.fillWidth: true }

                Text {
                    text: root.actionText
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.bold: true
                    color: root.isReady ? (cardMouse.containsMouse ? Theme.primaryHover : Theme.primary) : Theme.textMuted
                }
            }
        }

        MouseArea {
            id: cardMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: root.isReady ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: {
                if (root.isReady) {
                    root.clicked();
                    root.actionClicked();
                }
            }
        }
    }
}

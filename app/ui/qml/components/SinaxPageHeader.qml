import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string iconName: ""
    property string iconColor: Theme.primary
    property string breadcrumb: ""
    property string primaryActionText: ""
    property string primaryActionIcon: ""
    property bool primaryActionEnabled: true
    property string secondaryActionText: ""
    property string secondaryActionIcon: ""
    property bool searchVisible: false
    property string searchPlaceholder: "بحث في هذه الصفحة..."
    property string searchText: ""

    // Compatibility aliases
    property alias actionText: root.primaryActionText
    property alias showSearch: root.searchVisible
    property alias placeholderText: root.searchPlaceholder
    property alias breadcrumbCurrent: root.breadcrumb

    signal primaryActionClicked()
    signal actionClicked()
    signal secondaryActionClicked()
    signal searchChanged(string query)

    implicitHeight: mainCol.implicitHeight + Theme.spacingL * 2
    implicitWidth: parent ? parent.width : 800

    ColumnLayout {
        id: mainCol
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: Theme.spacingL
        }
        spacing: Theme.spacingM

        // Breadcrumb row (if present)
        Text {
            visible: root.breadcrumb.length > 0
            text: root.breadcrumb
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
            color: Theme.textMuted
            Layout.fillWidth: true
            elide: Text.ElideLeft
            horizontalAlignment: Text.AlignRight
        }

        // Main Header Row: Title & Subtitle on Right (RTL), Actions & Search on Left
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            // Icon + Title & Subtitle block
            RowLayout {
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                Rectangle {
                    visible: root.iconName.length > 0
                    width: 44
                    height: 44
                    radius: Theme.radiusMedium
                    color: Theme.isDark ? "#1E293B" : "#E2E8F0"

                    SinaxIcon {
                        anchors.centerIn: parent
                        iconName: root.iconName
                        size: Theme.iconLarge
                        color: root.iconColor
                    }
                }

                ColumnLayout {
                    spacing: 2

                    Text {
                        text: root.title
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontPageTitle
                        font.bold: true
                        color: Theme.textPrimary
                        elide: Text.ElideRight
                    }

                    Text {
                        visible: root.subtitle.length > 0
                        text: root.subtitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.maximumWidth: 650
                    }
                }
            }

            Item { Layout.fillWidth: true } // Spacer

            // Actions & Search (Left side in RTL)
            RowLayout {
                spacing: Theme.spacingS
                layoutDirection: Qt.RightToLeft

                // Optional Search Box
                SinaxSearchBox {
                    visible: root.searchVisible
                    implicitWidth: 220
                    placeholderText: root.searchPlaceholder
                    onSearchChanged: function(text) {
                        root.searchText = text;
                        root.searchChanged(text);
                    }
                }

                // Secondary Action Button
                SinaxButton {
                    visible: root.secondaryActionText.length > 0
                    text: root.secondaryActionText
                    iconName: root.secondaryActionIcon
                    variant: "secondary"
                    onClicked: root.secondaryActionClicked()
                }

                // Primary Action Button
                SinaxButton {
                    visible: root.primaryActionText.length > 0
                    text: root.primaryActionText
                    iconName: root.primaryActionIcon
                    variant: "primary"
                    enabled: root.primaryActionEnabled
                    onClicked: {
                        root.primaryActionClicked();
                        root.actionClicked();
                    }
                }
            }
        }

        // Subtle divider underneath header
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.divider
            Layout.topMargin: Theme.spacingXS
        }
    }
}

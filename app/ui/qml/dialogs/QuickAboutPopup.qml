import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Rectangle {
    id: root
    width: 420
    height: 398
    radius: Theme.radiusLarge
    color: Theme.surfaceElevated
    border.color: Theme.borderSubtle
    border.width: 1

    // Dismiss on Escape
    Keys.onEscapePressed: {
        if (typeof quickAboutController !== "undefined") {
            quickAboutController.setOpen(false);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 12
        layoutDirection: Qt.RightToLeft

        // Header Row: Close button on left, Title on right
        RowLayout {
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft

            Text {
                text: "بطاقة التعريف بالبرنامج"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                font.weight: Font.DemiBold
                color: Theme.textMuted
                Layout.fillWidth: true
            }

            SinaxIconButton {
                iconName: "dismiss"
                iconSize: 14
                tooltipText: "إغلاق"
                onClicked: {
                    if (typeof quickAboutController !== "undefined") {
                        quickAboutController.setOpen(false);
                    }
                }
            }
        }

        // Centered App Identity Block
        ColumnLayout {
            Layout.alignment: Qt.AlignCenter
            spacing: 10

            // Official App Logo
            Item {
                Layout.alignment: Qt.AlignCenter
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64

                Image {
                    anchors.centerIn: parent
                    width: 64
                    height: 64
                    source: "image://sinax/logo/" + encodeURIComponent(Theme.primary) + "/64"
                    fillMode: Image.PreserveAspectFit
                }
            }

            // Application Name
            Text {
                Layout.alignment: Qt.AlignCenter
                text: typeof quickAboutController !== "undefined" ? quickAboutController.appName : "SINAX"
                font.family: Theme.fontFamily
                font.pixelSize: 24
                font.weight: Font.Black
                color: Theme.primary
            }

            // Official Arabic Tagline
            Text {
                Layout.alignment: Qt.AlignCenter
                text: typeof quickAboutController !== "undefined" ? quickAboutController.appSubtitle : "SINAX — نظام إدارة الحاسوب والملفات"
                font.family: Theme.fontFamily
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            // Dynamic Version Badge
            Rectangle {
                Layout.alignment: Qt.AlignCenter
                implicitWidth: versionText.implicitWidth + 18
                implicitHeight: 24
                radius: 12
                color: Theme.primaryTint
                border.color: Theme.primary
                border.width: 1

                Text {
                    id: versionText
                    anchors.centerIn: parent
                    text: "الإصدار v" + (typeof quickAboutController !== "undefined" ? quickAboutController.appVersion : "1.0.0")
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    font.bold: true
                    color: Theme.primary
                }
            }
        }

        // Brief Description
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 4
            text: "منظومة وطنية متكاملة ومتقدمة لإدارة الحاسوب، معالجة وتنظيم الملفات، التحويل الشامل، والأدوات السريعة بأقصى درجات الأمان والكفاءة."
            font.family: Theme.fontFamily
            font.pixelSize: 12
            color: Theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Theme.borderSubtle
            Layout.topMargin: 4
            Layout.bottomMargin: 4
        }

        // Developer Credit Section
        RowLayout {
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft
            spacing: 10

            Text {
                text: "المطور والمبرمج: " + (typeof quickAboutController !== "undefined" ? quickAboutController.developerName : "رضوان عبد الهادي")
                font.family: Theme.fontFamily
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: Theme.textPrimary
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
            }

            // Circular local developer avatar stored with SINAX resources.
            Rectangle {
                Layout.preferredWidth: 48
                Layout.preferredHeight: 48
                radius: 24
                color: Theme.surface
                border.color: Theme.primary
                border.width: 1

                Image {
                    anchors.centerIn: parent
                    width: 44
                    height: 44
                    source: Qt.resolvedUrl("../../../../resources/images/about/radwan_profile.png")
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    mipmap: true
                }
            }

            // Close Action Button
            SinaxButton {
                text: "إغلاق"
                variant: "secondary"
                implicitHeight: 30
                onClicked: {
                    if (typeof quickAboutController !== "undefined") {
                        quickAboutController.setOpen(false);
                    }
                }
            }
        }
    }
}

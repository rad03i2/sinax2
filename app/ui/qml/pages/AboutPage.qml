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

    Flickable {
        id: flickable
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentCol.implicitHeight + Theme.spacing2XL
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        ColumnLayout {
            id: contentCol
            width: Math.min(parent.width - Theme.spacingXL * 2, 800)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacingL

            // 1. Page Header with Breadcrumbs
            SinaxPageHeader {
                Layout.fillWidth: true
                title: "حول برنامج SINAX"
                subtitle: "SINAX — نظام إدارة الحاسوب والملفات والوسائط المتكامل لنظام التشغيل Windows."
                iconName: "info"
                breadcrumbCurrent: "حول البرنامج"
            }

            // 2. Main Identity & Version Card
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: mainCardCol.implicitHeight + Theme.spacingXL * 2
                radius: Theme.radiusLarge
                color: Theme.surface
                border.color: Theme.primary
                border.width: 1.5

                ColumnLayout {
                    id: mainCardCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingXL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingM

                        SinaxIcon {
                            iconName: "logo"
                            size: 48
                            color: Theme.primary
                        }

                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "SINAX"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontHeader
                                font.bold: true
                                color: Theme.primary
                            }
                            Text {
                                text: "SINAX — نظام إدارة الحاسوب والملفات"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                color: Theme.textSecondary
                            }
                        }

                        Item { Layout.fillWidth: true }

                        SinaxBadge {
                            text: "إصدار مستقر (Release)"
                            variant: "success"
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    SinaxInfoRow {
                        Layout.fillWidth: true
                        label: "المطور والمبرمج:"
                        value: "رضوان عبد الهادي"
                    }

                    SinaxInfoRow {
                        Layout.fillWidth: true
                        label: "رقم الإصدار (Version):"
                        value: "v1.1.1 (تجربة التحديث)"
                    }

                    SinaxInfoRow {
                        Layout.fillWidth: true
                        label: "بيئة التشغيل والواجهة:"
                        value: "Qt Quick 2.15 / QML + PySide6"
                    }

                    SinaxInfoRow {
                        Layout.fillWidth: true
                        label: "محرك المعالجة الخلفي:"
                        value: "Python 3.13 (64-bit)"
                    }

                    SinaxInfoRow {
                        Layout.fillWidth: true
                        label: "قاعدة البيانات المحلية:"
                        value: "SQLite 3 (محلي آمن)"
                    }

                    SinaxInfoRow {
                        Layout.fillWidth: true
                        label: "نظام التشغيل المدعوم:"
                        value: "Microsoft Windows 10 / Windows 11 (64-bit)"
                    }
                }
            }

            // 3. Open Source & Licenses Card
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: licCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: licCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingS

                    Text {
                        text: "المحركات المدمجة والتراخيص القانونية"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    Text {
                        text: "يعتمد SINAX على تقنيات ومحركات مفتوحة المصدر عالية الأداء، بما في ذلك:\n• FFmpeg: لمعالجة وتحويل وسائط الفيديو والصوت (LGPL / GPL).\n• PyMuPDF & pypdf: لمحركات إدارة وتقسيم مستندات PDF.\n• Pillow (PIL): لمعالجة وضغط وتغيير أبعاد الصور.\n• psutil & Windows Management Instrumentation (WMI): لمراقبة الأجهزة والعتاد."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        color: Theme.textSecondary
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

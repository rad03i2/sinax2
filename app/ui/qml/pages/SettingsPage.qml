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
            width: Math.min(parent.width - Theme.spacingXL * 2, 900)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacingL

            // 1. Page Header with Breadcrumbs & Action
            SinaxPageHeader {
                Layout.fillWidth: true
                title: "إعدادات البرنامج والتفضيلات"
                subtitle: "تخصيص المظهر، إدارة الأداء، تنبيهات الأمان، وخيارات المعالجة التلقائية."
                iconName: "settings"
                breadcrumbCurrent: "الإعدادات"
                actionText: "استعادة الافتراضيات ⟲"
                onActionClicked: settingsController.resetToDefaults()
            }

            // 2. Section 1: Appearance & Theme
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: appCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: appCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    Text {
                        text: "المظهر وتجربة الواجهة (Appearance)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    // Theme selector buttons
                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingM

                        Text {
                            text: "السمة والنمط البصري:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            spacing: Theme.spacingS

                            SinaxButton {
                                text: "تلقائي (حسب النظام)"
                                variant: themeController.themeMode === "system" ? "primary" : "secondary"
                                isCompact: true
                                onClicked: themeController.setThemeMode("system")
                            }

                            SinaxButton {
                                text: "الوضع الفاتح (Light)"
                                variant: themeController.themeMode === "light" ? "primary" : "secondary"
                                isCompact: true
                                onClicked: themeController.setThemeMode("light")
                            }

                            SinaxButton {
                                text: "الوضع الداكن (Dark)"
                                variant: themeController.themeMode === "dark" ? "primary" : "secondary"
                                isCompact: true
                                onClicked: themeController.setThemeMode("dark")
                            }
                        }
                    }

                    // Animations toggle
                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "تفعيل الانتقالات والتحريكات الانسيابية (Animations)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxSwitch {
                            checked: settingsController.animationsEnabled
                            onCheckedChanged: settingsController.setBoolSetting("animations", checked)
                        }
                    }
                }
            }

            // 3. Section 2: Performance & Caching
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: perfCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: perfCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    Text {
                        text: "الأداء وإدارة الذاكرة (Performance & Cache)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "حجم ذاكرة التخزين المؤقت للصفحات (Page Cache Size):"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxBadge {
                            text: settingsController.pageCacheSize + " صفحات نشطة"
                            variant: "info"
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "عدد خيوط المعالجة الخلفية الموازية (Worker Threads):"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxBadge {
                            text: settingsController.workerThreads + " خيوط"
                            variant: "default"
                        }
                    }
                }
            }

            // 4. Section 3: Guards & Safe Actions
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: guardCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: guardCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    Text {
                        text: "الأمان وسلوكيات النظام (Guards & Behavior)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "تأكيد الإجراءات الحساسة (الحذف، استبدال الملفات، إلغاء التثبيت)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxSwitch {
                            checked: settingsController.confirmDangerousActions
                            onCheckedChanged: settingsController.setBoolSetting("confirm_dangerous", checked)
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "تذكر آخر مجلد تم فتحه في إدارة الملفات"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxSwitch {
                            checked: settingsController.rememberLastFolder
                            onCheckedChanged: settingsController.setBoolSetting("remember_folder", checked)
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "إظهار الإشعارات المنبثقة التفاعلية (Toast Notifications)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxSwitch {
                            checked: settingsController.toastNotifications
                            onCheckedChanged: settingsController.setBoolSetting("toasts", checked)
                        }
                    }
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

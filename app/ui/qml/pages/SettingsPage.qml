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

            SinaxPageHeader {
                Layout.fillWidth: true
                title: "إعدادات البرنامج والتفضيلات"
                subtitle: "تخصيص المظهر، الأداء، الأمان، والتحديثات السحابية."
                iconName: "settings"
                breadcrumbCurrent: "الإعدادات"
                actionText: "استعادة الافتراضيات ⟲"
                onActionClicked: settingsController.resetToDefaults()
            }

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

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: updateCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: settingsController.updateAvailable ? Theme.accent : Theme.borderSubtle
                border.width: settingsController.updateAvailable ? 2 : 1

                ColumnLayout {
                    id: updateCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "تحديث SINAX من GitHub"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSectionTitle
                            font.bold: true
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }

                        SinaxBadge {
                            text: "الإصدار الحالي " + settingsController.currentVersion
                            variant: "info"
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    Text {
                        Layout.fillWidth: true
                        text: settingsController.updateStatus
                        horizontalAlignment: Text.AlignRight
                        wrapMode: Text.WordWrap
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        color: settingsController.updateState === "error" ? Theme.danger : Theme.textSecondary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        visible: settingsController.updateAvailable

                        SinaxBadge {
                            text: "الجديد " + settingsController.latestVersion
                            variant: "success"
                        }

                        SinaxBadge {
                            text: "حجم التحديث " + settingsController.updateSize
                            variant: "default"
                        }

                        Item { Layout.fillWidth: true }
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        visible: settingsController.updateState === "downloading" || settingsController.updateState === "installing"
                        from: 0
                        to: 100
                        value: settingsController.updateProgress
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft
                        spacing: Theme.spacingM

                        SinaxButton {
                            text: settingsController.updateBusy ? "جارٍ الفحص..." : "فحص التحديثات"
                            variant: "secondary"
                            enabled: !settingsController.updateBusy
                            onClicked: settingsController.checkForUpdates()
                        }

                        SinaxButton {
                            text: "تنزيل وتثبيت التحديث"
                            variant: "primary"
                            visible: settingsController.updateAvailable
                            enabled: !settingsController.updateBusy
                            onClicked: settingsController.downloadAndInstallUpdate()
                        }

                        Item { Layout.fillWidth: true }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "يُنزل SINAX الملفات التي تغيرت فقط، ويتحقق من SHA-256، ثم يستخدم SINAX-Updater.exe مع نسخة احتياطية وRollback تلقائي عند الفشل."
                        horizontalAlignment: Text.AlignRight
                        wrapMode: Text.WordWrap
                        font.family: Theme.fontFamily
                        font.pixelSize: Math.max(11, Theme.fontBody - 1)
                        color: Theme.textMuted
                    }
                }
            }

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

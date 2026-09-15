import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Flickable {
    id: root

    contentWidth: width
    contentHeight: contentCol.implicitHeight + Theme.spacing2XL
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    SinaxScrollBar {
        flickable: root
    }

    ColumnLayout {
        id: contentCol
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: Theme.spacingL
        }
        spacing: Theme.spacingXL

        // 1. Page Header
        SinaxPageHeader {
            title: "النظام والتخزين"
            subtitle: "لوحة التحكم المتكاملة لتحليل الأقراص ومراقبة أداء المعالج والذاكرة والتنظيف الآمن."
            iconName: "storage"
            breadcrumb: "الرئيسية  ›  النظام والتخزين"
            searchVisible: false
            primaryActionText: "تحليل التخزين الشامل  ←"
            primaryActionIcon: "treemap"
            onPrimaryActionClicked: systemStorageController.openSubpage("analyzer")
        }

        // 2. Hardware Vitals Cards (CPU, RAM, System Drive)
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            // Card 1: CPU
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 120

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingS

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "المعالج (CPU)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCardTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: String(systemStorageController.cpuPercent) + "%"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontLarge
                            font.bold: true
                            color: systemStorageController.cpuPercent > 80 ? Theme.error : Theme.primary
                        }
                    }

                    SinaxProgress {
                        Layout.fillWidth: true
                        value: systemStorageController.cpuPercent
                        accentColor: systemStorageController.cpuPercent > 80 ? Theme.error : Theme.primary
                    }

                    Text {
                        text: "الاستهلاك اللحظي للنواة"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textSecondary
                        horizontalAlignment: Text.AlignRight
                        Layout.fillWidth: true
                    }
                }
            }

            // Card 2: RAM
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 120

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingS

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "الذاكرة العشوائية (RAM)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCardTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: String(systemStorageController.ramPercent) + "%"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontLarge
                            font.bold: true
                            color: systemStorageController.ramPercent > 85 ? Theme.error : Theme.primary
                        }
                    }

                    SinaxProgress {
                        Layout.fillWidth: true
                        value: systemStorageController.ramPercent
                        accentColor: systemStorageController.ramPercent > 85 ? Theme.error : Theme.primary
                    }

                    Text {
                        text: systemStorageController.ramText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textSecondary
                        horizontalAlignment: Text.AlignRight
                        Layout.fillWidth: true
                    }
                }
            }

            // Card 3: Disk C:
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 120

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingS

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "قرص النظام (C:)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCardTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: String(systemStorageController.diskCPercent) + "%"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontLarge
                            font.bold: true
                            color: systemStorageController.diskCPercent > 90 ? Theme.error : Theme.primary
                        }
                    }

                    SinaxProgress {
                        Layout.fillWidth: true
                        value: systemStorageController.diskCPercent
                        accentColor: systemStorageController.diskCPercent > 90 ? Theme.error : Theme.primary
                    }

                    Text {
                        text: systemStorageController.diskCFreeText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textSecondary
                        horizontalAlignment: Text.AlignRight
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // 3. Section: Connected Storage Drives
        SinaxSectionHeader {
            title: "وسائط التخزين والأقراص المتصلة"
            description: "نظرة تفصيلية على سعة الأقراص المحلية وحالتها الصحية"
            badgeText: "أقراص نشطة"
            badgeVariant: "info"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 320
            maxColumns: 3

            Repeater {
                model: systemStorageController.driveModel

                SinaxCard {
                    implicitHeight: driveCol.implicitHeight + Theme.spacingL * 2

                    ColumnLayout {
                        id: driveCol
                        anchors.fill: parent
                        anchors.margins: Theme.spacingL
                        spacing: Theme.spacingM

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingM
                            layoutDirection: Qt.RightToLeft

                            Rectangle {
                                width: 42
                                height: 42
                                radius: Theme.radiusMedium
                                color: Theme.isDark ? "#1E293B" : "#F1F5F9"

                                Image {
                                    anchors.centerIn: parent
                                    width: 22
                                    height: 22
                                    source: "image://sinax/storage/" + encodeURIComponent(Theme.primary) + "/22"
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            ColumnLayout {
                                spacing: 1
                                Layout.fillWidth: true

                                Text {
                                    text: model.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontCardTitle
                                    font.bold: true
                                    color: Theme.textPrimary
                                }

                                Text {
                                    text: model.filesystem + " • " + model.driveType
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontCaption
                                    color: Theme.textMuted
                                }
                            }

                            SinaxBadge {
                                text: model.health
                                variant: "success"
                            }
                        }

                        SinaxProgress {
                            Layout.fillWidth: true
                            value: model.percent
                            accentColor: model.percent > 90 ? Theme.error : Theme.primary
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            layoutDirection: Qt.RightToLeft

                            Text {
                                text: "مستخدم: " + model.usedGb
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                color: Theme.textSecondary
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: "متاح: " + model.freeGb + " (من " + model.totalGb + ")"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textPrimary
                            }
                        }
                    }
                }
            }
        }

        // 4. Section: Storage Breakdown Bar ("أين ذهبت مساحة جهازي؟")
        SinaxCard {
            Layout.fillWidth: true
            implicitHeight: breakdownCol.implicitHeight + Theme.spacingL * 2

            ColumnLayout {
                id: breakdownCol
                anchors.fill: parent
                anchors.margins: Theme.spacingL
                spacing: Theme.spacingM

                RowLayout {
                    Layout.fillWidth: true
                    layoutDirection: Qt.RightToLeft

                    Text {
                        text: "أين ذهبت مساحة جهازي؟ (توزيع سعة التخزين التقريبي)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSectionTitle
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    Item { Layout.fillWidth: true }

                    SinaxButton {
                        text: "فتح محلل التخزين التفصيلي  ←"
                        variant: "ghost"
                        iconName: "treemap"
                        onClicked: systemStorageController.openSubpage("analyzer")
                    }
                }

                // Multi-segment horizontal bar
                RowLayout {
                    Layout.fillWidth: true
                    height: 16
                    spacing: 2

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: systemStorageController.breakdownSystem
                        radius: 3
                        color: "#38BDF8"
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: systemStorageController.breakdownApps
                        radius: 3
                        color: "#A855F7"
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: systemStorageController.breakdownDocs
                        radius: 3
                        color: "#22C55E"
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: systemStorageController.breakdownMedia
                        radius: 3
                        color: "#EAB308"
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: systemStorageController.breakdownTemp
                        radius: 3
                        color: "#EF4444"
                    }
                }

                // Legend row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingL
                    layoutDirection: Qt.RightToLeft

                    RowLayout {
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 2; color: "#38BDF8" }
                        Text { text: "ملفات النظام (35%)"; font.pixelSize: Theme.fontCaption; color: Theme.textSecondary; font.family: Theme.fontFamily }
                    }
                    RowLayout {
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 2; color: "#A855F7" }
                        Text { text: "البرامج والألعاب (25%)"; font.pixelSize: Theme.fontCaption; color: Theme.textSecondary; font.family: Theme.fontFamily }
                    }
                    RowLayout {
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 2; color: "#22C55E" }
                        Text { text: "المستندات والعمل (15%)"; font.pixelSize: Theme.fontCaption; color: Theme.textSecondary; font.family: Theme.fontFamily }
                    }
                    RowLayout {
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 2; color: "#EAB308" }
                        Text { text: "الوسائط والفيديو (15%)"; font.pixelSize: Theme.fontCaption; color: Theme.textSecondary; font.family: Theme.fontFamily }
                    }
                    RowLayout {
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 2; color: "#EF4444" }
                        Text { text: "المؤقت والكاش (10%)"; font.pixelSize: Theme.fontCaption; color: Theme.textSecondary; font.family: Theme.fontFamily }
                    }
                }
            }
        }

        // 5. Section: Subpage Shortcuts
        SinaxSectionHeader {
            title: "الأدوات والمراكز المتخصصة للنظام"
            description: "الوصول السريع إلى أدوات تنظيف الأقراص والعمليات وبدء التشغيل"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 280
            maxColumns: 3

            SinaxToolCard {
                title: "محلل التخزين التفاعلي"
                description: "استكشف أين ذهبت مساحة جهازك عبر الخريطة الشجرية وتعرف على أكبر المجلدات والملفات حجماً."
                iconName: "treemap"
                iconColor: "#38BDF8"
                badgeText: "خريطة تفاعلية"
                onClicked: systemStorageController.openSubpage("analyzer")
            }

            SinaxToolCard {
                title: "التنظيف الآمن للنظام"
                description: "تنظيف فوري وآمن للملفات المؤقتة، سلة المحذوفات، وتخزين التحديثات القديمة لتوفير مساحة فورية."
                iconName: "clean"
                iconColor: "#22C55E"
                badgeText: "تنظيف آمن"
                onClicked: systemStorageController.openSubpage("cleanup")
            }

            SinaxToolCard {
                title: "صحة الأقراص و S.M.A.R.T."
                description: "فحص المؤشرات الحيوية ودرجة الحرارة وساعات التشغيل وسلامة وسائط التخزين SSD و HDD."
                iconName: "storage"
                iconColor: "#EAB308"
                badgeText: "فحص العتاد"
                onClicked: systemStorageController.openSubpage("health")
            }

            SinaxToolCard {
                title: "إدارة العمليات وقفل الملفات"
                description: "مراقبة استهلاك البرامج للذاكرة والمعالج، مع كشف فوري للبرامج التي تقفل الملفات وتمنع حذفها."
                iconName: "process"
                iconColor: "#A855F7"
                badgeText: "تحكم فوري"
                onClicked: systemStorageController.openSubpage("processes")
            }

            SinaxToolCard {
                title: "إدارة بدء التشغيل"
                description: "تسريع إقلاع Windows عبر تعطيل البرامج غير الضرورية التي تبدأ تلقائياً مع تشغيل الجهاز."
                iconName: "startup"
                iconColor: "#EC4899"
                badgeText: "تسريع الإقلاع"
                onClicked: systemStorageController.openSubpage("startup")
            }

            SinaxToolCard {
                title: "مواصفات الجهاز والتقارير"
                description: "عرض تفصيلي لمواصفات الحاسوب ونظام التشغيل مع تصدير تقرير شامل بصيغ متعددة."
                iconName: "chart"
                iconColor: "#14B8A6"
                badgeText: "تقرير شامل"
                onClicked: systemStorageController.openSubpage("device")
            }
        }
    }
}

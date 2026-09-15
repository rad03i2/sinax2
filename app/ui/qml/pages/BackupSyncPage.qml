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

    property bool showWizard: false

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
            title: "النسخ الاحتياطي والمزامنة"
            subtitle: "المركز الشامل للنسخ الاحتياطي، المزامنة الذكية، والاستعادة المضمونة مع التحقق الرقمي."
            iconName: "backup"
            breadcrumb: "الرئيسية  ›  النسخ والمزامنة"
            searchVisible: false
            primaryActionText: "إنشاء خطة نسخ جديدة  +"
            primaryActionIcon: "tools"
            onPrimaryActionClicked: root.showWizard = true
        }

        // 2. Executive Vitals Row
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            // Vital 1: Last Backup Status
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 96

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusMedium
                        color: Theme.successSurface

                        Image {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: "image://sinax/backup/" + encodeURIComponent(Theme.success) + "/20"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true

                        Text {
                            text: "آخر نسخة احتياطية"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                        }
                        Text {
                            text: backupSyncController.lastBackupTime
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            font.bold: true
                            color: Theme.textPrimary
                        }
                    }
                }
            }

            // Vital 2: Data Integrity State
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 96

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusMedium
                        color: Theme.infoSurface

                        Image {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: "image://sinax/doctor/" + encodeURIComponent(Theme.primary) + "/20"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true

                        Text {
                            text: "سلامة البيانات والـ Hash"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                        }
                        Text {
                            text: backupSyncController.integrityState
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            font.bold: true
                            color: Theme.textPrimary
                        }
                    }
                }
            }

            // Vital 3: Protected Data Size
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 96

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingM
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusMedium
                        color: Theme.isDark ? "#1E293B" : "#F1F5F9"

                        Image {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: "image://sinax/storage/" + encodeURIComponent(Theme.primary) + "/20"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true

                        Text {
                            text: "إجمالي البيانات المحمية"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                        }
                        Text {
                            text: backupSyncController.protectedSize
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontBody
                            font.bold: true
                            color: Theme.textPrimary
                        }
                    }
                }
            }
        }

        // 3. Embedded SinaxWizard (Shown when user clicks "إنشاء خطة نسخ جديدة")
        Rectangle {
            visible: root.showWizard
            Layout.fillWidth: true
            implicitHeight: 480
            radius: Theme.radiusLarge
            color: "transparent"

            SinaxWizard {
                id: backupWizard
                anchors.fill: parent
                steps: [
                    { title: "المصادر", subtitle: "الملفات والمجلدات" },
                    { title: "الوجهة", subtitle: "قرص النسخ الاحتياطي" },
                    { title: "الخيارات", subtitle: "التشفير ونوع النسخ" },
                    { title: "المراجعة", subtitle: "تأكيد وبدء الخطة" }
                ]

                // Custom Step Content Views
                Item {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL

                    // Step 0: Sources
                    ColumnLayout {
                        visible: backupWizard.currentStep === 0
                        anchors.fill: parent
                        spacing: Theme.spacingM

                        Text {
                            text: "اختر المجلدات أو الملفات التي ترغب بحمايتها:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMedium
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        SinaxTextField {
                            Layout.fillWidth: true
                            label: "اسم خطة النسخ الاحتياطي"
                            text: backupSyncController.draftName
                            onTextChanged: backupSyncController.setDraftField("name", text)
                        }

                        SinaxTextField {
                            Layout.fillWidth: true
                            label: "مسار المصدر الأساسي"
                            text: backupSyncController.draftSource
                            onTextChanged: backupSyncController.setDraftField("source", text)
                        }
                    }

                    // Step 1: Destination
                    ColumnLayout {
                        visible: backupWizard.currentStep === 1
                        anchors.fill: parent
                        spacing: Theme.spacingM

                        Text {
                            text: "حدد القرص أو المجلد المخصص لحفظ النسخ الاحتياطية:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMedium
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        SinaxTextField {
                            Layout.fillWidth: true
                            label: "مسار الوجهة أو القرص الخارجي (USB / HDD)"
                            text: backupSyncController.draftDestination
                            onTextChanged: backupSyncController.setDraftField("destination", text)
                        }
                    }

                    // Step 2: Options
                    ColumnLayout {
                        visible: backupWizard.currentStep === 2
                        anchors.fill: parent
                        spacing: Theme.spacingM

                        Text {
                            text: "خيارات الأمان والنوع:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMedium
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        SinaxSwitch {
                            text: "تشفير النسخة الاحتياطية بمعيار AES-256-GCM"
                            checked: backupSyncController.draftEncrypted
                            onToggled: backupSyncController.setDraftField("encrypted", checked ? "true" : "false")
                        }

                        SinaxSwitch {
                            text: "نسخ تدريجي ذكي (Incremental - نسخ الملفات المتغيرة فقط)"
                            checked: true
                        }
                    }

                    // Step 3: Review
                    ColumnLayout {
                        visible: backupWizard.currentStep === 3
                        anchors.fill: parent
                        spacing: Theme.spacingS

                        Text {
                            text: "مراجعة إعدادات الخطة قبل الحفظ:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontMedium
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        SinaxInfoRow { label: "اسم الخطة"; value: backupSyncController.draftName }
                        SinaxInfoRow { label: "المصدر"; value: backupSyncController.draftSource; isMono: true }
                        SinaxInfoRow { label: "الوجهة"; value: backupSyncController.draftDestination; isMono: true }
                        SinaxInfoRow { label: "التشفير"; value: backupSyncController.draftEncrypted ? "AES-256 مفعل" : "معطل" }
                    }
                }

                onCancelClicked: root.showWizard = false
                onFinishClicked: {
                    backupSyncController.saveDraftProfile();
                    root.showWizard = false;
                }
            }
        }

        // 4. Section: Live Profiles List
        SinaxSectionHeader {
            title: "خطط النسخ الاحتياطي النشطة (Backup Profiles)"
            description: "إدارة خطط النسخ الاحتياطي المجدولة وتشغيلها فورياً بنقرة واحدة"
            badgeText: "خطط مسجلة"
            badgeVariant: "success"
        }

        ListView {
            id: profileList
            Layout.fillWidth: true
            implicitHeight: contentHeight
            interactive: false
            spacing: Theme.spacingM
            model: backupSyncController.profileModel

            delegate: SinaxCard {
                width: profileList.width
                implicitHeight: profCol.implicitHeight + Theme.spacingL * 2

                ColumnLayout {
                    id: profCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingM
                        layoutDirection: Qt.RightToLeft

                        Rectangle {
                            width: 40
                            height: 40
                            radius: Theme.radiusMedium
                            color: Theme.isDark ? "#1E293B" : "#F1F5F9"

                            Image {
                                anchors.centerIn: parent
                                width: 22
                                height: 22
                                source: "image://sinax/backup/" + encodeURIComponent(Theme.primary) + "/22"
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: model.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCardTitle
                                font.bold: true
                                color: Theme.textPrimary
                            }

                            Text {
                                text: "المصدر: " + model.source + "  ←  الوجهة: " + model.destination
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textMuted
                                elide: Text.ElideMiddle
                            }
                        }

                        SinaxBadge {
                            text: model.verificationState
                            variant: "success"
                        }

                        SinaxBadge {
                            visible: model.encrypted
                            text: "AES مشفر"
                            variant: "info"
                        }

                        SinaxButton {
                            text: "تشغيل الآن  ▶"
                            variant: "primary"
                            onClicked: backupSyncController.runBackupNow(model.profileId)
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "آخر تنفيذ: " + model.lastRun + " • القادم: " + model.nextRun
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                            color: Theme.textSecondary
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: "حجم النسخة: " + model.protectedSize + " (" + model.versionCount + " إصدارات)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                            font.bold: true
                            color: Theme.textPrimary
                        }
                    }
                }
            }
        }

        // 5. Section: Backup Subpages Grid
        SinaxSectionHeader {
            title: "أدوات ومراكز النسخ والاستعادة المتقدمة"
            description: "استعادة الملفات، سجل الإصدارات، حماية ما قبل الفورمات، والمزامنة"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 280
            maxColumns: 3

            SinaxToolCard {
                title: "احمِ ملفاتي المهمة"
                description: "نسخ فوري بنقرة واحدة لسطح المكتب والمستندات والصور الهامة دون تعقيد."
                iconName: "clean"
                iconColor: "#22C55E"
                badgeText: "نقرة واحدة"
                onClicked: backupSyncController.openSubpage("quick_backup")
            }

            SinaxToolCard {
                title: "تجهيز الجهاز قبل الفورمات"
                description: "حفظ شامل لكافة البيانات الشخصية، التعريفات، وقائمة البرامج قبل إعادة التثبيت."
                iconName: "system"
                iconColor: "#38BDF8"
                badgeText: "أمان شامل"
                onClicked: backupSyncController.openSubpage("before_format")
            }

            SinaxToolCard {
                title: "المزامنة الحية وسلة التراجع"
                description: "مزامنة ذكية ثنائية الاتجاه للمجلدات مع كشف التعارضات وسلة تراجع آمنة."
                iconName: "sync"
                iconColor: "#EAB308"
                badgeText: "مزامنة حية"
                onClicked: backupSyncController.openSubpage("sync")
            }

            SinaxToolCard {
                title: "استعادة الملفات والبحث"
                description: "استعادة ذكية للملفات مع البحث الشامل واسترجاع النسخ المحذوفة بسهولة."
                iconName: "restore"
                iconColor: "#A855F7"
                badgeText: "استعادة فورية"
                onClicked: backupSyncController.openSubpage("restore")
            }

            SinaxToolCard {
                title: "سجل الإصدارات والخط الزمني"
                description: "تتبع التعديلات التاريخية على الملفات والرجوع لأي إصدار سابق بدقة."
                iconName: "clock"
                iconColor: "#14B8A6"
                badgeText: "خط زمني"
                onClicked: backupSyncController.openSubpage("versions")
            }

            SinaxToolCard {
                title: "صحة النسخ واختبار الاستعادة"
                description: "طبيب النسخ الاحتياطي لفحص تجارب الاستعادة العشوائية وضمان سلامة البيانات."
                iconName: "doctor"
                iconColor: "#EC4899"
                badgeText: "اختبار دوري"
                onClicked: backupSyncController.openSubpage("health_drill")
            }
        }
    }
}

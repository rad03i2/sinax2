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
            title: "طبيب Windows ومركز الصيانة"
            subtitle: "التشخيص الذكي، فحص الأعطال الشائعة، إصلاح ملفات Windows وإعادة ضبط النظام بأمان فائق."
            iconName: "doctor"
            breadcrumb: "الرئيسية  ›  مركز الصيانة والإصلاح"
            searchVisible: false
            primaryActionText: maintenanceController.isScanning ? "جارٍ الفحص..." : "بدء الفحص الذكي الشامل  ▶"
            primaryActionIcon: "doctor"
            primaryActionEnabled: !maintenanceController.isScanning
            onPrimaryActionClicked: maintenanceController.startDiagnosis("full")
        }

        // 2. Symptom Triage Cards ("اختر مشكلتك للتشخيص الموجه")
        SinaxSectionHeader {
            title: "التشخيص الذكي حسب الأعراض (Symptom Triage)"
            description: "حدد العَرَض الذي تواجهه لبدء فحص مخصص واقتراح خطة الصيانة المعتمدة"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingM
            minItemWidth: 220
            maxColumns: 6

            SinaxToolCard {
                title: "الجهاز بطيء ومزدحم"
                description: "فحص استهلاك العمليات، البرامج الثقيلة، والملفات المؤقتة."
                iconName: "performance"
                iconColor: "#38BDF8"
                badgeText: "الأكثر شيوعاً"
                onClicked: maintenanceController.startDiagnosis("بطء في استجابة الجهاز")
            }

            SinaxToolCard {
                title: "المساحة منخفضة"
                description: "كشف الملفات المهملة، التحديثات القديمة، وتخزين الكاش."
                iconName: "clean"
                iconColor: "#22C55E"
                badgeText: "توفير مساحة"
                onClicked: maintenanceController.startDiagnosis("انخفاض مساحة التخزين")
            }

            SinaxToolCard {
                title: "انقطاع أو بطء الإنترنت"
                description: "فحص خوادم DNS، محولات الشبكة، ومصحح Windows."
                iconName: "network"
                iconColor: "#EAB308"
                badgeText: "فحص الشبكة"
                onClicked: maintenanceController.startDiagnosis("مشاكل الاتصال بالإنترنت")
            }

            SinaxToolCard {
                title: "فشل تحديثات Windows"
                description: "إصلاح خدمات Update المعلقة وإعادة ضبط الكتالوج."
                iconName: "update"
                iconColor: "#A855F7"
                badgeText: "تحديثات النظام"
                onClicked: maintenanceController.startDiagnosis("أخطاء Windows Update")
            }

            SinaxToolCard {
                title: "برامج لا تستجيب"
                description: "إنهاء العمليات المعلقة وتحليل سجلات تعطل التطبيقات."
                iconName: "apps"
                iconColor: "#EC4899"
                badgeText: "استقرار البرامج"
                onClicked: maintenanceController.startDiagnosis("تعليق وتوقف البرامج")
            }

            SinaxToolCard {
                title: "مشاكل الطابعة أو الصوت"
                description: "إعادة تشغيل Print Spooler ومصححات الصوت المدمجة."
                iconName: "devices"
                iconColor: "#14B8A6"
                badgeText: "الملحقات"
                onClicked: maintenanceController.startDiagnosis("الملحقات والطابعات")
            }
        }

        // 3. Scan Status & Progress Bar (Active when scanning)
        SinaxCard {
            Layout.fillWidth: true
            implicitHeight: scanCol.implicitHeight + Theme.spacingL * 2

            ColumnLayout {
                id: scanCol
                anchors.fill: parent
                anchors.margins: Theme.spacingL
                spacing: Theme.spacingM

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Image {
                        width: 24
                        height: 24
                        source: "image://sinax/doctor/" + encodeURIComponent(maintenanceController.isScanning ? Theme.primary : Theme.success) + "/24"
                        fillMode: Image.PreserveAspectFit
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: maintenanceController.isScanning ? "جارٍ تنفيذ التشخيص الذكي..." : "حالة فحص النظام الحالية"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCardTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Text {
                            text: maintenanceController.scanStep
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textSecondary
                        }
                    }

                    SinaxBadge {
                        text: maintenanceController.isScanning ? "نشط" : (maintenanceController.issuesCount > 0 ? (String(maintenanceController.issuesCount) + " توصيات") : "النظام سليم")
                        variant: maintenanceController.isScanning ? "info" : (maintenanceController.issuesCount > 0 ? "warning" : "success")
                    }
                }

                SinaxProgress {
                    Layout.fillWidth: true
                    value: maintenanceController.scanProgress
                    indeterminate: maintenanceController.isScanning && maintenanceController.scanProgress <= 10
                }
            }
        }

        // 4. Diagnostic Results Section
        SinaxSectionHeader {
            visible: maintenanceController.resultsModel.rowCount() > 0
            title: "نتائج الفحص وخطة الإصلاح المعتمدة"
            description: "قائمة بالإجراءات والتوصيات المبنية على فحص النظام الفعلي مع بيان درجة الأثر"
            badgeText: String(maintenanceController.issuesCount) + " عنصر تم رصده"
            badgeVariant: "warning"
        }

        ListView {
            visible: maintenanceController.resultsModel.rowCount() > 0
            Layout.fillWidth: true
            implicitHeight: contentHeight
            interactive: false
            spacing: Theme.spacingM
            model: maintenanceController.resultsModel

            delegate: SinaxCard {
                width: parent.width
                implicitHeight: itemCol.implicitHeight + Theme.spacingL * 2

                ColumnLayout {
                    id: itemCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingM
                        layoutDirection: Qt.RightToLeft

                        Rectangle {
                            width: 38
                            height: 38
                            radius: Theme.radiusMedium
                            color: model.severity === "problem" ? Theme.errorSurface : (model.severity === "warning" ? Theme.warningSurface : Theme.infoSurface)

                            Image {
                                anchors.centerIn: parent
                                width: 20
                                height: 20
                                source: "image://sinax/warning/" + encodeURIComponent(model.severity === "problem" ? Theme.error : (model.severity === "warning" ? Theme.warning : Theme.primary)) + "/20"
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: model.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCardTitle
                                font.bold: true
                                color: Theme.textPrimary
                            }

                            Text {
                                text: model.description
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }

                        SinaxBadge {
                            text: model.severity === "problem" ? "خلل حرج" : (model.severity === "warning" ? "تحذير" : "توصية")
                            variant: model.severity === "problem" ? "error" : (model.severity === "warning" ? "warning" : "info")
                        }

                        SinaxButton {
                            text: model.actionLabel
                            variant: model.severity === "problem" ? "danger" : "primary"
                            onClicked: maintenanceController.executeAction(model.issueId)
                        }
                    }

                    // Evidence text if present
                    Text {
                        visible: model.evidence.length > 0
                        text: "الدليل المرصود: " + model.evidence
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // 5. Expandable Technical Details Drawer
        TechnicalDetailsDrawer {
            Layout.fillWidth: true
            logText: maintenanceController.technicalLog
        }

        // 6. Section: Maintenance Subpages Grid
        SinaxSectionHeader {
            title: "أدوات الصيانة المتقدمة"
            description: "الوصول المباشر إلى أدوات فحص DISM، إدارة الإقلاع، وسجل الموثوقية"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 280
            maxColumns: 3

            SinaxToolCard {
                title: "إصلاح Windows: DISM & SFC"
                description: "فحص وإصلاح صورة نظام Windows وملفات النظام التالفة رسمياً دون فقد البيانات."
                iconName: "tools"
                iconColor: "#38BDF8"
                badgeText: "إصلاح رسمي"
                onClicked: maintenanceController.openSubpage("windows_repair")
            }

            SinaxToolCard {
                title: "التنظيف الآمن ومراجعة التنزيلات"
                description: "تنظيف آمن وشامل لملفات الكاش والملفات المؤقتة ومراجعة مجلد التنزيلات."
                iconName: "clean"
                iconColor: "#22C55E"
                badgeText: "تنظيف شفاف"
                onClicked: maintenanceController.openSubpage("cleanup")
            }

            SinaxToolCard {
                title: "بدء التشغيل ومساعد Clean Boot"
                description: "مراجعة البرامج ذات الأثر العالي وعزل التعارضات لتسريع بدء تشغيل الحاسوب."
                iconName: "startup"
                iconColor: "#EAB308"
                badgeText: "تسريع الإقلاع"
                onClicked: maintenanceController.openSubpage("startup")
            }

            SinaxToolCard {
                title: "التخزين وفحص الأقراص CHKDSK"
                description: "تشخيص قطاعات القرص ونظام الملفات NTFS واقتراح الفحص الآمن."
                iconName: "storage"
                iconColor: "#A855F7"
                badgeText: "سلامة القرص"
                onClicked: maintenanceController.openSubpage("storage_disk")
            }

            SinaxToolCard {
                title: "السجل والموثوقية والأعطال"
                description: "سجل انهيارات البرامج والشاشة الزرقاء BSOD ومؤشر موثوقية Windows."
                iconName: "doctor"
                iconColor: "#EC4899"
                badgeText: "تحليل الأعطال"
                onClicked: maintenanceController.openSubpage("reliability")
            }

            SinaxToolCard {
                title: "أدوات الصيانة المتقدمة"
                description: "إعادة تشغيل Explorer، مزامنة الوقت الذرية، وتصدير تقرير الصيانة."
                iconName: "tools"
                iconColor: "#14B8A6"
                badgeText: "أدوات فنية"
                onClicked: maintenanceController.openSubpage("advanced")
            }
        }
    }
}

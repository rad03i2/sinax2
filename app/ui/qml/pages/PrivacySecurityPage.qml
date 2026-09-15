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
            width: Math.min(parent.width - Theme.spacingXL * 2, 1280)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacingL

            // 1. Page Header with Breadcrumbs & Action
            SinaxPageHeader {
                Layout.fillWidth: true
                title: "مركز الخصوصية والأمان والتشفير"
                subtitle: "فحص سلامة الملفات، كشف التوقيعات الرقمية، تنظيف الـ Metadata، وتشفير البيانات الحساسة."
                iconName: "shield"
                breadcrumbCurrent: "الخصوصية والأمان"
                actionText: "فتح الخزنة المشفرة ←"
                onActionClicked: privacyController.openSubpage("vault")
            }

            // 2. Windows Security Real Health Dashboard (4 Cards)
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                SinaxCard {
                    Layout.fillWidth: true
                    title: "مكافح الفيروسات (Defender)"
                    value: privacyController.defenderStatus === "active" ? "حماية نشطة" : "معطل"
                    subtitle: "حماية لحظية ضد التهديدات"
                    iconName: "shield"
                    accentColor: privacyController.defenderStatus === "active" ? Theme.success : Theme.error
                }

                SinaxCard {
                    Layout.fillWidth: true
                    title: "جدار الحماية (Firewall)"
                    value: privacyController.firewallStatus === "active" ? "يعمل بكفاءة" : "معطل"
                    subtitle: "مراقبة الاتصالات الصادرة والواردة"
                    iconName: "lock"
                    accentColor: privacyController.firewallStatus === "active" ? Theme.success : Theme.error
                }

                SinaxCard {
                    Layout.fillWidth: true
                    title: "ميزة SmartScreen"
                    value: privacyController.smartScreenStatus === "active" ? "مفعلة" : "معطلة"
                    subtitle: "فحص البرامج والمواقع المشبوهة"
                    iconName: "eye"
                    accentColor: Theme.info
                }

                SinaxCard {
                    Layout.fillWidth: true
                    title: "تشفير الأقراص (BitLocker)"
                    value: privacyController.bitlockerStatus === "active" ? "مشفر بالكامل" : "متاح للنظام"
                    subtitle: "حماية البيانات ضد السرقة المادية"
                    iconName: "key"
                    accentColor: Theme.primary
                }
            }

            // 3. File Safety Inspector (فحص الملفات والتوقيع الرقمي)
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: inspCol.implicitHeight + Theme.spacingL * 2
                radius: Theme.radiusMedium
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                ColumnLayout {
                    id: inspCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: Theme.spacingM

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "فاحص أمان وسلامة الملفات (File Safety & Integrity Inspector)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSectionTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Item { Layout.fillWidth: true }

                        SinaxBadge {
                            text: "فحص أمان محلي"
                            variant: "info"
                        }
                    }

                    SinaxDropZone {
                        Layout.fillWidth: true
                        iconName: "eye"
                        titleText: privacyController.inspectedFilePath ? "الملف المفحوص: " + privacyController.inspectedFilePath : "اسحب أي برنامج أو ملف هنا للتحقق من سلامته، بصمته الرقمية، وتوقيعه المعتمد..."
                        subtitleText: "فحص فوري للبصمة (SHA-256 / MD5) وكشف التوقيعات الرقمية المشفرة دون اتصال بالإنترنت"
                        browseButtonText: "استعراض ملف للفحص"
                        onFileDropped: function(path) { privacyController.inspectFile(path) }
                    }

                    // Results Panel (Visible when file inspected)
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: Boolean(privacyController.inspectedFilePath)
                        spacing: Theme.spacingS

                        RowLayout {
                            Layout.fillWidth: true
                            layoutDirection: Qt.RightToLeft
                            spacing: Theme.spacingM

                            Text {
                                text: "حالة التوقيع الرقمي (Digital Signature):"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                font.bold: true
                                color: Theme.textPrimary
                            }

                            SinaxBadge {
                                text: privacyController.fileSignatureStatus === "valid" ? "توقيع رقمي موثوق ومعتمد" : "غير موقع (Unsigned File)"
                                variant: privacyController.fileSignatureStatus === "valid" ? "success" : "warning"
                            }
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "بصمة SHA-256:"
                            value: privacyController.fileSha256
                        }

                        SinaxInfoRow {
                            Layout.fillWidth: true
                            label: "بصمة MD5:"
                            value: privacyController.fileMd5
                        }
                    }
                }
            }

            // 4. Privacy & Vault Quick Tools Grid
            SinaxSectionHeader {
                Layout.fillWidth: true
                title: "أدوات الخصوصية وحماية البيانات المتقدمة"
                subtitle: "تنظيف البيانات التعريفية، التشفير القوي، والحذف الآمن غير القابل للاسترجاع"
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width > 1000 ? 3 : (width > 650 ? 2 : 1)
                columnSpacing: Theme.spacingM
                rowSpacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                SinaxToolCard {
                    Layout.fillWidth: true
                    title: "الخزنة المشفرة (Encrypted Vault)"
                    description: "إنشاء مساحة مشفرة بمعيار AES-256 لحفظ المستندات السرية ومفاتيح الحسابات."
                    iconName: "lock"
                    badgeText: "تشفير AES"
                    badgeType: "success"
                    actionText: "فتح الخزنة ←"
                    onActionClicked: privacyController.openSubpage("vault")
                }

                SinaxToolCard {
                    Layout.fillWidth: true
                    title: "تنظيف الـ Metadata والخصوصية"
                    description: "إزالة بيانات الموقع الجغرافي (GPS) واسم الكاميرا وتاريخ الإنشاء من الصور والمستندات قبل مشاركتها."
                    iconName: "clean"
                    badgeText: "حماية الخصوصية"
                    badgeType: "info"
                    actionText: "بدء التنظيف ←"
                    onActionClicked: privacyController.openSubpage("clean")
                }

                SinaxToolCard {
                    Layout.fillWidth: true
                    title: "الحذف الآمن والنهائي (Secure Delete)"
                    description: "طمس الملفات الحساسة نهائياً بعدة دورات كتابة لمنع أي برنامج استعادة من قراءتها."
                    iconName: "delete"
                    badgeText: "إتلاف آمن"
                    badgeType: "danger"
                    actionText: "حذف نهائي ←"
                    onActionClicked: privacyController.openSubpage("secure_delete")
                }
            }
        }
    }

    SinaxScrollBar {
        flickable: flickable
    }
}

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

    property string activeCategory: "overview"

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
            title: "إدارة الأجهزة ومعلومات الحاسوب"
            subtitle: "مركز استعلام وتشخيص ومراقبة عتاد الحاسوب، المعالج، الذاكرة، الأقراص، والتعريفات."
            iconName: "devices"
            breadcrumb: "الرئيسية  ›  إدارة الأجهزة"
            searchVisible: false
            primaryActionText: "الفحص السريع للعتاد  ←"
            primaryActionIcon: "doctor"
            onPrimaryActionClicked: devicesController.openSubpage("quick_check")
        }

        // 2. Hardware Overview Hero Card (Clean borderless Fluent presentation)
        SinaxCard {
            Layout.fillWidth: true
            implicitHeight: heroCol.implicitHeight + Theme.spacingL * 2

            ColumnLayout {
                id: heroCol
                anchors.fill: parent
                anchors.margins: Theme.spacingL
                spacing: Theme.spacingM

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    Rectangle {
                        width: 48
                        height: 48
                        radius: Theme.radiusMedium
                        color: Theme.isDark ? "#1E293B" : "#F1F5F9"

                        Image {
                            anchors.centerIn: parent
                            width: 26
                            height: 26
                            source: "image://sinax/devices/" + encodeURIComponent(Theme.primary) + "/26"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: devicesController.deviceName
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Text {
                            text: devicesController.osName
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textSecondary
                        }
                    }

                    SinaxBadge {
                        text: "العتاد متصل ويعمل"
                        variant: "success"
                    }
                }
            }
        }

        // 3. Section: Core Hardware Categories (Processor, Memory, Graphics, Storage)
        SinaxSectionHeader {
            title: "المواصفات الحيوية للعتاد"
            description: "بيانات معالجة العتاد الحقيقية مقاسة مباشرة من النظام"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            // CPU Card
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: cpuCol.implicitHeight + Theme.spacingL * 2

                ColumnLayout {
                    id: cpuCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: 0

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
                        SinaxIconButton {
                            iconName: "arrow-left"
                            iconSize: 14
                            tooltipText: "عرض تفاصيل المعالج"
                            onClicked: devicesController.openSubpage("cpu")
                        }
                    }

                    Item { height: Theme.spacingS }

                    SinaxInfoRow {
                        label: "المعالج"
                        value: devicesController.cpuName
                        copyable: true
                        showDivider: true
                    }
                    SinaxInfoRow {
                        label: "الأنوية والمسارات"
                        value: devicesController.cpuCores
                        isMono: true
                        showDivider: false
                    }
                }
            }

            // RAM Card
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: ramCol.implicitHeight + Theme.spacingL * 2

                ColumnLayout {
                    id: ramCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: 0

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
                        SinaxIconButton {
                            iconName: "arrow-left"
                            iconSize: 14
                            tooltipText: "عرض تفاصيل الذاكرة"
                            onClicked: devicesController.openSubpage("ram")
                        }
                    }

                    Item { height: Theme.spacingS }

                    SinaxInfoRow {
                        label: "إجمالي السعة"
                        value: devicesController.ramTotal
                        isMono: true
                        copyable: true
                        showDivider: true
                    }
                    SinaxInfoRow {
                        label: "النوع المعماري"
                        value: devicesController.ramType
                        isMono: true
                        showDivider: false
                    }
                }
            }
        }

        // Row 2: Battery & Storage
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            // Battery Card
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: batCol.implicitHeight + Theme.spacingL * 2

                ColumnLayout {
                    id: batCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "البطارية ومصدر الطاقة"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCardTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        SinaxIconButton {
                            iconName: "arrow-left"
                            iconSize: 14
                            tooltipText: "عرض تقرير البطارية"
                            onClicked: devicesController.openSubpage("battery")
                        }
                    }

                    Item { height: Theme.spacingS }

                    SinaxInfoRow {
                        label: "حالة الطاقة"
                        value: devicesController.battery
                        showDivider: false
                    }
                }
            }

            // Storage Card
            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: stoCol.implicitHeight + Theme.spacingL * 2

                ColumnLayout {
                    id: stoCol
                    anchors.fill: parent
                    anchors.margins: Theme.spacingL
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        layoutDirection: Qt.RightToLeft

                        Text {
                            text: "وسائط التخزين"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCardTitle
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        SinaxIconButton {
                            iconName: "arrow-left"
                            iconSize: 14
                            tooltipText: "عرض أقراص التخزين"
                            onClicked: devicesController.openSubpage("storage")
                        }
                    }

                    Item { height: Theme.spacingS }

                    SinaxInfoRow {
                        label: "التخزين الأساسي"
                        value: devicesController.storageSummary
                        showDivider: false
                    }
                }
            }
        }

        // 4. Section: Specialized Hardware Categories Grid
        SinaxSectionHeader {
            title: "كافة أقسام العتاد والأجهزة الملحقة"
            description: "الانتقال السريع إلى فحص كروت الشاشة، التعريفات، الشاشات ومنافذ USB"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 280
            maxColumns: 4

            SinaxToolCard {
                title: "كرت الشاشة (GPU)"
                description: "كروت الرسوميات المدمجة والمنفصلة وذاكرة VRAM والترددات."
                iconName: "gpu"
                iconColor: "#60CDFF"
                onClicked: devicesController.openSubpage("gpu")
            }

            SinaxToolCard {
                title: "اللوحة الأم وBIOS"
                description: "الشركة المصنعة للوحة، إصدار الـ BIOS، ونمط UEFI والإقلاع الآمن."
                iconName: "devices"
                iconColor: "#52C41A"
                onClicked: devicesController.openSubpage("motherboard")
            }

            SinaxToolCard {
                title: "الشاشات ومواصفات العرض"
                description: "معلومات لوحات العرض ومعدل التحديث والدقة وبيانات EDID."
                iconName: "devices"
                iconColor: "#FFB900"
                onClicked: devicesController.openSubpage("displays")
            }

            SinaxToolCard {
                title: "USB والأجهزة الملحقة"
                description: "الأجهزة الموصولة عبر USB ومعرفات VID/PID وحالة الاتصال."
                iconName: "devices"
                iconColor: "#A855F7"
                onClicked: devicesController.openSubpage("usb")
            }

            SinaxToolCard {
                title: "التعريفات ومدير الأجهزة"
                description: "شجرة العتاد وحزم التعريفات المثبتة والنسخ الاحتياطي عبر pnputil."
                iconName: "devices"
                iconColor: "#14B8A6"
                onClicked: devicesController.openSubpage("drivers")
            }

            SinaxToolCard {
                title: "الحساسات والحرارة"
                description: "قراءات الحساسات اللحظية لدرجات حرارة الأنوية وسرعة المراوح."
                iconName: "devices"
                iconColor: "#EC4899"
                onClicked: devicesController.openSubpage("sensors")
            }

            SinaxToolCard {
                title: "بيئة Windows والتنشيط"
                description: "بيانات بناء النظام، وقت التشغيل (Uptime)، ومفتاح التنشيط."
                iconName: "devices"
                iconColor: "#38BDF8"
                onClicked: devicesController.openSubpage("windows")
            }

            SinaxToolCard {
                title: "تقارير العتاد ولقطات المقارنة"
                description: "حفظ لقطة العتاد ومقارنتها عند تغيير أي قطعة وتصدير التقارير."
                iconName: "devices"
                iconColor: "#F5222D"
                onClicked: devicesController.openSubpage("reports")
            }
        }
    }
}

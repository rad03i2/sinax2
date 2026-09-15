import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Flickable {
    id: root

    contentWidth: width
    contentHeight: galleryCol.implicitHeight + Theme.spacing2XL
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    ScrollBar.vertical: SinaxScrollBar {}

    ColumnLayout {
        id: galleryCol
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: Theme.spacingL
        }
        spacing: Theme.spacingXL

        // Header
        SinaxPageHeader {
            title: "معرض المكونات التفاعلي (Developer Component Gallery)"
            subtitle: "استعراض حي لكافة عناصر نظام تصميم SINAX QML بالوضعين الداكن والفاتح ودعم RTL الكامل."
            iconName: "tools"
            breadcrumb: "المطور  ›  معرض المكونات"
            primaryActionText: themeController.isDark ? "الوضع الفاتح" : "الوضع الداكن"
            primaryActionIcon: themeController.isDark ? "info" : "settings"
            onPrimaryActionClicked: themeController.toggleTheme()
            secondaryActionText: "معرض الأيقونات (Icon Gallery)"
            secondaryActionIcon: "tools"
            onSecondaryActionClicked: navController.openRoute("icon_gallery")
        }

        // Section 1: Buttons
        SinaxSectionHeader {
            title: "الأزرار التفاعلية (SinaxButton & Variants)"
            description: "أنماط الأزرار الأساسية والثانوية وأزرار الحذف والتحميل"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingM
            layoutDirection: Qt.RightToLeft

            SinaxButton { text: "Primary Button"; variant: "primary" }
            SinaxButton { text: "Secondary Button"; variant: "secondary" }
            SinaxButton { text: "Danger Action"; variant: "danger" }
            SinaxButton { text: "Ghost Button"; variant: "ghost" }
            SinaxButton { text: "Loading State"; variant: "primary"; isLoading: true }
            SinaxButton { text: "Disabled Button"; variant: "primary"; enabled: false }
        }

        // Section 2: Badges & Switches
        SinaxSectionHeader {
            title: "الشارات والمفاتيح (Badges & Switches)"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            SinaxBadge { text: "نجاح (Success)"; variant: "success" }
            SinaxBadge { text: "تحذير (Warning)"; variant: "warning" }
            SinaxBadge { text: "خطأ (Error)"; variant: "error" }
            SinaxBadge { text: "معلومات (Info)"; variant: "info" }
            SinaxBadge { text: "افتراضي (Default)"; variant: "default" }

            SinaxSwitch { text: "مفتاح التفعيل التلقائي"; checked: true }
        }

        // Section 3: Tool Cards & Grid
        SinaxSectionHeader {
            title: "بطاقات الأدوات وشبكة العرض المتجاوبة (Tool Cards & Grid)"
        }

        SinaxToolGrid {
            Layout.fillWidth: true
            minItemWidth: 260
            maxColumns: 3

            SinaxToolCard {
                title: "بطاقة أداة قياسية"
                description: "وصف موجز يوضح وظيفة الأداة وسرعة استجابتها مع حركة تمرير عائمة."
                badgeText: "جاهز"
                iconName: "tools"
            }
            SinaxToolCard {
                title: "أداة مفضلة مع شارة مسؤول"
                description: "تدعم وضع النجمة المفضلة وشارة تتطلب صلاحيات المدير."
                badgeText: "نشط"
                requiresAdmin: true
                favorite: true
                iconName: "security"
            }
            SinaxToolCard {
                title: "ميزة تجريبية جديدة"
                description: "عرض شارة تجريبي للأدوات في مرحلة الاختبار والتحسين."
                badgeText: "جديد"
                beta: true
                iconName: "convert"
            }
        }

        // Section 4: Info Rows (Border-free presentation)
        SinaxSectionHeader {
            title: "صفوف المعلومات النظيفة (SinaxInfoRow)"
            description: "طريقة عرض المفتاح والقيمة دون مربعات باهتة أو خطوط سميكة"
        }

        SinaxCard {
            Layout.fillWidth: true
            implicitHeight: infoRowsCol.implicitHeight + Theme.spacingL * 2

            ColumnLayout {
                id: infoRowsCol
                anchors.fill: parent
                anchors.margins: Theme.spacingL
                spacing: 0

                SinaxInfoRow { label: "اسم الجهاز"; value: "SINAX Workstation Pro"; copyable: true }
                SinaxInfoRow { label: "نظام التشغيل"; value: "Windows 11 Professional (x64)"; isMono: true; copyable: true }
                SinaxInfoRow { label: "عنوان IP المحلي"; value: "192.168.1.105"; isMono: true; isLTR: true; copyable: true }
                SinaxInfoRow { label: "حالة التشفير"; value: "مفعل ومؤمن"; statusText: "محمي"; statusVariant: "success"; showDivider: false }
            }
        }

        // Section 5: Drag & Drop Zone
        SinaxSectionHeader {
            title: "منطقة السحب والإفلات الذكية (SinaxDropZone)"
        }

        SinaxDropZone {
            Layout.fillWidth: true
            promptText: "اسحب أي ملف لتجربة تأثير السحب والإفلات التفاعلي..."
        }

        // Section 6: Empty & Error States
        SinaxSectionHeader {
            title: "حالات الخطأ والشاشات الفارغة (Empty & Error States)"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            layoutDirection: Qt.RightToLeft

            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 220
                SinaxEmptyState {
                    anchors.centerIn: parent
                    title: "لا توجد ملفات محددة"
                    description: "قم باختيار مجلد للبدء في الفحص والمعالجة."
                    actionText: "اختيار مجلد"
                }
            }

            SinaxCard {
                Layout.fillWidth: true
                implicitHeight: 220
                SinaxErrorState {
                    anchors.centerIn: parent
                    title: "فشل الاتصال بالخدمة"
                    message: "يرجى التأكد من تشغيل الخدمة المحلية والمحاولة ثانية."
                    technicalDetails: "ErrCode: 0x80070005 (E_ACCESSDENIED) at WinPnpEnum."
                }
            }
        }

        // Section 7: Before & After Split Slider Viewer
        SinaxSectionHeader {
            title: "عارض المقارنة التفاعلي (BeforeAfterViewer)"
            description: "مكون مقارنة قبل وبعد مع مقبض سحب متحرك وشارات تمييز لعرض نتائج الضغط والتحسين"
        }

        SinaxCard {
            Layout.fillWidth: true
            implicitHeight: 320

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingM
                spacing: Theme.spacingM

                BeforeAfterViewer {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    beforeText: "الأصل (Original - 4.2 MB)"
                    afterText: "المحسن (Optimized - 820 KB)"
                    sliderPosition: 0.5
                }
            }
        }
    }
}

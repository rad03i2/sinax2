import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root
    implicitWidth: 1000
    implicitHeight: 700

    // Filter and Preview state
    property string searchQuery: ""
    property string selectedCategory: "all"
    property int previewSize: Theme.iconLarge // 24px default
    property string previewColorKey: "default" // default, active, hover, danger, disabled
    property string previewVariant: "regular" // regular, filled
    property bool previewRTL: false
    property string copiedIconName: ""

    // Dynamic color resolution
    readonly property color currentPreviewColor: {
        if (previewColorKey === "active") return Theme.iconActive;
        if (previewColorKey === "hover") return Theme.iconHover;
        if (previewColorKey === "danger") return Theme.iconDanger;
        if (previewColorKey === "disabled") return Theme.iconDisabled;
        return Theme.iconDefault;
    }

    // Complete Registry Model
    readonly property var allIcons: [
        // Navigation
        { name: "home", category: "navigation", desc: "الرئيسية", rtl: false, hasFilled: true },
        { name: "folder", category: "navigation", desc: "إدارة الملفات", rtl: false, hasFilled: true },
        { name: "media", category: "navigation", desc: "الوسائط المتعددة", rtl: false, hasFilled: true },
        { name: "storage", category: "navigation", desc: "النظام والتخزين", rtl: false, hasFilled: true },
        { name: "devices", category: "navigation", desc: "الأجهزة والمعلومات", rtl: false, hasFilled: true },
        { name: "apps", category: "navigation", desc: "إدارة البرامج", rtl: false, hasFilled: true },
        { name: "network", category: "navigation", desc: "الشبكة والإنترنت", rtl: false, hasFilled: true },
        { name: "shield", category: "navigation", desc: "الخصوصية والأمان", rtl: false, hasFilled: true },
        { name: "backup", category: "navigation", desc: "النسخ الاحتياطي", rtl: false, hasFilled: true },
        { name: "maintenance", category: "navigation", desc: "مركز الصيانة", rtl: false, hasFilled: false },
        { name: "toolbox", category: "navigation", desc: "الأدوات السريعة", rtl: false, hasFilled: false },
        { name: "history", category: "navigation", desc: "سجل العمليات", rtl: false, hasFilled: false },
        { name: "settings", category: "navigation", desc: "الإعدادات", rtl: false, hasFilled: false },
        { name: "info", category: "navigation", desc: "حول البرنامج", rtl: false, hasFilled: true },

        // Actions
        { name: "add", category: "actions", desc: "إضافة", rtl: false, hasFilled: false },
        { name: "delete", category: "actions", desc: "حذف", rtl: false, hasFilled: false },
        { name: "edit", category: "actions", desc: "تعديل", rtl: false, hasFilled: false },
        { name: "copy", category: "actions", desc: "نسخ", rtl: false, hasFilled: false },
        { name: "cut", category: "actions", desc: "قص", rtl: false, hasFilled: false },
        { name: "paste", category: "actions", desc: "لصق", rtl: false, hasFilled: false },
        { name: "save", category: "actions", desc: "حفظ", rtl: false, hasFilled: false },
        { name: "refresh", category: "actions", desc: "تحديث", rtl: false, hasFilled: false },
        { name: "sync", category: "actions", desc: "مزامنة", rtl: false, hasFilled: false },
        { name: "search", category: "actions", desc: "بحث", rtl: false, hasFilled: false },
        { name: "filter", category: "actions", desc: "تصفية", rtl: false, hasFilled: false },
        { name: "sort", category: "actions", desc: "ترتيب", rtl: false, hasFilled: false },
        { name: "download", category: "actions", desc: "تنزيل", rtl: false, hasFilled: false },
        { name: "upload", category: "actions", desc: "رفع", rtl: false, hasFilled: false },
        { name: "share", category: "actions", desc: "مشاركة", rtl: false, hasFilled: false },
        { name: "dismiss", category: "actions", desc: "إغلاق / إلغاء", rtl: false, hasFilled: false },
        { name: "check", category: "actions", desc: "تم / تأكيد", rtl: false, hasFilled: false },
        { name: "menu", category: "actions", desc: "القائمة الجانبية", rtl: false, hasFilled: false },
        { name: "star", category: "actions", desc: "المفضلة", rtl: false, hasFilled: true },
        { name: "pin", category: "actions", desc: "تثبيت", rtl: false, hasFilled: true },
        { name: "more_horizontal", category: "actions", desc: "المزيد", rtl: false, hasFilled: false },

        // Directionals (RTL Mirrored)
        { name: "back", category: "actions", desc: "رجوع للخلف (RTL)", rtl: true, hasFilled: false },
        { name: "forward", category: "actions", desc: "تقدم للأمام (RTL)", rtl: true, hasFilled: false },
        { name: "chevron_left", category: "actions", desc: "سهم يسار (RTL)", rtl: true, hasFilled: false },
        { name: "chevron_right", category: "actions", desc: "سهم يمين (RTL)", rtl: true, hasFilled: false },
        { name: "chevron_up", category: "actions", desc: "سهم أعلى", rtl: false, hasFilled: false },
        { name: "chevron_down", category: "actions", desc: "سهم أسفل", rtl: false, hasFilled: false },
        { name: "undo", category: "actions", desc: "تراجع (RTL)", rtl: true, hasFilled: false },
        { name: "redo", category: "actions", desc: "إعادة (RTL)", rtl: true, hasFilled: false },

        // Files
        { name: "file", category: "files", desc: "ملف", rtl: false, hasFilled: false },
        { name: "pdf", category: "files", desc: "ملف PDF", rtl: false, hasFilled: false },
        { name: "convert", category: "files", desc: "تحويل التنسيق", rtl: false, hasFilled: false },
        { name: "merge", category: "files", desc: "دمج الملفات", rtl: false, hasFilled: false },
        { name: "split", category: "files", desc: "تقسيم الملفات", rtl: false, hasFilled: false },
        { name: "organize", category: "files", desc: "التنظيم الذكي", rtl: false, hasFilled: false },
        { name: "duplicate", category: "files", desc: "النسخ والتكرار", rtl: false, hasFilled: false },

        // Media
        { name: "image", category: "media", desc: "صورة", rtl: false, hasFilled: false },
        { name: "video", category: "media", desc: "فيديو", rtl: false, hasFilled: false },
        { name: "audio", category: "media", desc: "صوت", rtl: false, hasFilled: false },
        { name: "play", category: "media", desc: "تشغيل", rtl: false, hasFilled: false },
        { name: "pause", category: "media", desc: "إيقاف مؤقت", rtl: false, hasFilled: false },
        { name: "crop", category: "media", desc: "اقتصاص", rtl: false, hasFilled: false },
        { name: "rotate", category: "media", desc: "تدوير", rtl: false, hasFilled: false },

        // System
        { name: "cpu", category: "system", desc: "المعالج", rtl: false, hasFilled: false },
        { name: "performance", category: "system", desc: "مراقبة الأداء", rtl: false, hasFilled: false },
        { name: "clean", category: "system", desc: "التنظيف الآمن", rtl: false, hasFilled: false },
        { name: "startup", category: "system", desc: "بدء التشغيل", rtl: false, hasFilled: false },
        { name: "chart", category: "system", desc: "المخططات البيانية", rtl: false, hasFilled: false },

        // Devices
        { name: "doctor", category: "devices", desc: "طبيب التشخيص", rtl: false, hasFilled: false },
        { name: "ram", category: "devices", desc: "الذاكرة العشوائية", rtl: false, hasFilled: false },

        // Network
        { name: "wifi", category: "network", desc: "الشبكة اللاسلكية", rtl: false, hasFilled: false },

        // Security
        { name: "lock", category: "security", desc: "قفل / تشفير", rtl: false, hasFilled: false },
        { name: "key", category: "security", desc: "كلمات المرور", rtl: false, hasFilled: false },
        { name: "eye", category: "security", desc: "فحص الخصوصية", rtl: false, hasFilled: false },
        { name: "vault", category: "security", desc: "الخزنة المشفرة", rtl: false, hasFilled: false },

        // Tools
        { name: "calculator", category: "tools", desc: "آلة حاسبة", rtl: false, hasFilled: false },
        { name: "code", category: "tools", desc: "أدوات المطور", rtl: false, hasFilled: false },

        // Status
        { name: "success", category: "status", desc: "نجاح أو معتمد", rtl: false, hasFilled: true },
        { name: "warning", category: "status", desc: "تحذير أو انتباه", rtl: false, hasFilled: true },
        { name: "error", category: "status", desc: "خطأ أو فشل", rtl: false, hasFilled: true },
        { name: "question", category: "status", desc: "غير معروف / مساعدة", rtl: false, hasFilled: true }
    ]

    // Filtered items
    readonly property var filteredIcons: {
        var res = [];
        var q = searchQuery.toLowerCase().trim();
        for (var i = 0; i < allIcons.length; i++) {
            var item = allIcons[i];
            if (selectedCategory !== "all" && item.category !== selectedCategory) continue;
            if (q !== "" && item.name.indexOf(q) === -1 && item.desc.indexOf(q) === -1 && item.category.indexOf(q) === -1) continue;
            res.push(item);
        }
        return res;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingL
        spacing: Theme.spacingL

        // Header
        RowLayout {
            Layout.fillWidth: true
            layoutDirection: Qt.RightToLeft
            spacing: Theme.spacingM

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: "معرض الأيقونات للمطورين • SINAX Icon Gallery"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontPageTitle
                    font.bold: true
                    color: Theme.textPrimary
                    horizontalAlignment: Text.AlignRight
                }

                Text {
                    text: "النظام البصري الموحد لتطبيق SINAX مبني على Microsoft Fluent UI System Icons (MIT License)."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    color: Theme.textSecondary
                    horizontalAlignment: Text.AlignRight
                }
            }

            // Stats badge
            Rectangle {
                Layout.preferredHeight: 32
                implicitWidth: statsRow.implicitWidth + 24
                radius: Theme.radiusSmall
                color: Theme.surfaceElevated
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: statsRow
                    anchors.centerIn: parent
                    spacing: Theme.spacingS
                    layoutDirection: Qt.RightToLeft

                    SinaxIcon { iconName: "check"; size: Theme.iconSmall; color: Theme.success }
                    Text {
                        text: "75 أيقونة معتمدة • 0 نواقص • ترخيص MIT"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        color: Theme.textPrimary
                    }
                }
            }
        }

        // Toolbar: Search + Category filter + Size + Theme + RTL switches
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: toolbarCol.implicitHeight + 20
            radius: Theme.radiusMedium
            color: Theme.surface
            border.color: Theme.borderSubtle
            border.width: 1

            ColumnLayout {
                id: toolbarCol
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                // Row 1: Search & Category Chips
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingM
                    layoutDirection: Qt.RightToLeft

                    SinaxSearchBox {
                        Layout.preferredWidth: 260
                        placeholderText: "ابحث بالاسم أو الوصف..."
                        onSearchChanged: function(text) { root.searchQuery = text; }
                        onCleared: { root.searchQuery = ""; }
                    }

                    // Category filters
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        layoutDirection: Qt.RightToLeft

                        Repeater {
                            model: [
                                { id: "all", label: "الكل" },
                                { id: "navigation", label: "التنقل" },
                                { id: "actions", label: "الإجراءات" },
                                { id: "files", label: "الملفات" },
                                { id: "media", label: "الوسائط" },
                                { id: "system", label: "النظام" },
                                { id: "devices", label: "الأجهزة" },
                                { id: "network", label: "الشبكة" },
                                { id: "security", label: "الأمان" },
                                { id: "tools", label: "الأدوات" },
                                { id: "status", label: "الحالات" }
                            ]

                            delegate: Rectangle {
                                Layout.preferredHeight: 28
                                implicitWidth: catText.implicitWidth + 16
                                radius: Theme.radiusSmall
                                color: root.selectedCategory === modelData.id ? Theme.primaryTint : (catMouse.containsMouse ? Theme.surfaceHover : "transparent")
                                border.color: root.selectedCategory === modelData.id ? Theme.primary : Theme.borderSubtle
                                border.width: 1

                                Text {
                                    id: catText
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    color: root.selectedCategory === modelData.id ? Theme.primary : Theme.textPrimary
                                }

                                MouseArea {
                                    id: catMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.selectedCategory = modelData.id
                                }
                            }
                        }
                    }
                }

                // Row 2: Preview Size, Preview Color, Variant, RTL
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingL
                    layoutDirection: Qt.RightToLeft

                    // Size selector
                    RowLayout {
                        spacing: 4
                        layoutDirection: Qt.RightToLeft
                        Text { text: "الحجم:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                        Repeater {
                            model: [
                                { label: "16", size: Theme.iconSmall },
                                { label: "20", size: Theme.iconMedium },
                                { label: "24", size: Theme.iconLarge },
                                { label: "32", size: Theme.iconXL },
                                { label: "48", size: Theme.iconXXL }
                            ]
                            delegate: Rectangle {
                                Layout.preferredHeight: 26
                                implicitWidth: 32
                                radius: Theme.radiusSmall
                                color: root.previewSize === modelData.size ? Theme.primary : "transparent"
                                border.color: Theme.borderSubtle
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: root.previewSize === modelData.size ? "#FFFFFF" : Theme.textSecondary
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.previewSize = modelData.size
                                }
                            }
                        }
                    }

                    // Color Preview
                    RowLayout {
                        spacing: 4
                        layoutDirection: Qt.RightToLeft
                        Text { text: "اللون:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                        Repeater {
                            model: [
                                { id: "default", label: "عادي", color: Theme.iconDefault },
                                { id: "active", label: "نشط", color: Theme.iconActive },
                                { id: "hover", label: "تحويم", color: Theme.iconHover },
                                { id: "danger", label: "خطر", color: Theme.iconDanger },
                                { id: "disabled", label: "معطل", color: Theme.iconDisabled }
                            ]
                            delegate: Rectangle {
                                Layout.preferredHeight: 26
                                implicitWidth: colText.implicitWidth + 12
                                radius: Theme.radiusSmall
                                color: root.previewColorKey === modelData.id ? Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.2) : "transparent"
                                border.color: root.previewColorKey === modelData.id ? modelData.color : Theme.borderSubtle
                                border.width: 1
                                Text {
                                    id: colText
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: modelData.color
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.previewColorKey = modelData.id
                                }
                            }
                        }
                    }

                    // Variant toggle
                    RowLayout {
                        spacing: 4
                        layoutDirection: Qt.RightToLeft
                        Text { text: "النمط:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                        Rectangle {
                            Layout.preferredHeight: 26
                            implicitWidth: 64
                            radius: Theme.radiusSmall
                            color: root.previewVariant === "filled" ? Theme.primary : "transparent"
                            border.color: Theme.borderSubtle
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.previewVariant === "filled" ? "Filled" : "Regular"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                color: root.previewVariant === "filled" ? "#FFFFFF" : Theme.textSecondary
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.previewVariant = (root.previewVariant === "filled" ? "regular" : "filled")
                            }
                        }
                    }

                    // RTL mirror preview
                    RowLayout {
                        spacing: 6
                        layoutDirection: Qt.RightToLeft
                        Text { text: "معاينة RTL:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; color: Theme.textSecondary }
                        SinaxSwitch {
                            checked: root.previewRTL
                            onToggled: function(c) { root.previewRTL = c; }
                        }
                    }
                }
            }
        }

        // Grid of icons
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Flow {
                width: parent.width
                spacing: Theme.spacingM
                layoutDirection: Qt.RightToLeft

                Repeater {
                    model: root.filteredIcons

                    delegate: Rectangle {
                        width: 180
                        height: 140
                        radius: Theme.radiusMedium
                        color: cardMouse.containsMouse ? Theme.surfaceHover : Theme.surface
                        border.color: root.copiedIconName === modelData.name ? Theme.primary : Theme.borderSubtle
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 6

                            // Header row: category badge + RTL tag
                            RowLayout {
                                Layout.fillWidth: true
                                layoutDirection: Qt.RightToLeft

                                SinaxBadge {
                                    text: modelData.category
                                    statusType: "info"
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    visible: modelData.rtl
                                    text: "RTL ⇄"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    color: Theme.warning
                                }
                            }

                            // Icon Center Preview
                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                SinaxIcon {
                                    anchors.centerIn: parent
                                    iconName: modelData.name
                                    variant: (modelData.hasFilled && root.previewVariant === "filled") ? "filled" : "regular"
                                    size: root.previewSize
                                    color: root.currentPreviewColor
                                    mirrored: root.previewRTL && modelData.rtl
                                }
                            }

                            // Semantic name label
                            Text {
                                text: modelData.name
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSmall
                                font.bold: true
                                color: Theme.textPrimary
                                Layout.alignment: Qt.AlignCenter
                                elide: Text.ElideRight
                            }

                            // Copy name button
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 24
                                radius: Theme.radiusSmall
                                color: root.copiedIconName === modelData.name ? Theme.successSurface : (btnMouse.containsMouse ? Theme.surfacePressed : Theme.surfaceElevated)
                                border.color: root.copiedIconName === modelData.name ? Theme.success : Theme.borderSubtle
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: root.copiedIconName === modelData.name ? "تم النسخ" : "نسخ الاسم"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: root.copiedIconName === modelData.name ? Theme.success : Theme.textSecondary
                                }

                                MouseArea {
                                    id: btnMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        navController.copyToClipboard(modelData.name);
                                        root.copiedIconName = modelData.name;
                                        copyTimer.restart();
                                    }
                                }
                            }
                        }

                        MouseArea {
                            id: cardMouse
                            anchors.fill: parent
                            z: -1
                            hoverEnabled: true
                            onClicked: {
                                navController.copyToClipboard(modelData.name);
                                root.copiedIconName = modelData.name;
                                copyTimer.restart();
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        id: copyTimer
        interval: 1800
        onTriggered: root.copiedIconName = ""
    }
}

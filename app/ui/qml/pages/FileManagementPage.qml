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

    // Drop recommendation banner state
    property string recommendedAction: ""
    property string recommendedRoute: ""
    property string recommendedSummary: ""

    Connections {
        target: fileManagementController
        function onDropResolved(actionTitle, recommendedRoute, summaryText) {
            root.recommendedAction = actionTitle;
            root.recommendedRoute = recommendedRoute;
            root.recommendedSummary = summaryText;
        }
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
            title: "مركز إدارة الملفات الذكي"
            subtitle: "أدوات احترافية متقدمة لإعادة التسمية، التحويل الشامل، الدمج، الفرز الذكي، والتحليل بأقصى سرعة وأمان."
            iconName: "folder"
            breadcrumb: "الرئيسية  ›  إدارة الملفات"
            searchVisible: false
        }

        // 2. Smart Drag & Drop Target
        SinaxDropZone {
            Layout.fillWidth: true
            promptText: "اسحب ملفات أو مجلدات وأفلتها هنا للتعرف الذكي على الإجراء المناسب..."
            formatHint: "يدعم المستندات، الصور، الصوت، الفيديو، مجلدات الأرشيف والبيانات"
            onFilesDropped: function(urls) {
                fileManagementController.handleDrop(urls);
            }
        }

        // 3. Smart Action Resolver Recommendation Card (when drop happens)
        Rectangle {
            visible: root.recommendedAction.length > 0
            Layout.fillWidth: true
            implicitHeight: bannerRow.implicitHeight + Theme.spacingL * 2
            radius: Theme.radiusLarge
            color: Theme.infoSurface
            border.color: Theme.primary
            border.width: 1.5

            RowLayout {
                id: bannerRow
                anchors.fill: parent
                anchors.margins: Theme.spacingL
                spacing: Theme.spacingL
                layoutDirection: Qt.RightToLeft

                Image {
                    width: 28
                    height: 28
                    source: "image://sinax/tools/" + encodeURIComponent(Theme.primary) + "/28"
                    fillMode: Image.PreserveAspectFit
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: "إجراء ذكي مقترح: " + root.recommendedAction
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMedium
                        font.bold: true
                        color: Theme.primary
                    }

                    Text {
                        text: root.recommendedSummary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                }

                SinaxButton {
                    text: "فتح في " + root.recommendedAction + "  ←"
                    variant: "primary"
                    onClicked: {
                        fileManagementController.openTool(root.recommendedRoute);
                        root.recommendedAction = "";
                    }
                }

                SinaxIconButton {
                    iconName: "close"
                    iconSize: 14
                    tooltipText: "تجاهل"
                    onClicked: root.recommendedAction = ""
                }
            }
        }

        // 4. Section: Primary File Management Tools
        SinaxSectionHeader {
            title: "أدوات إدارة الملفات الأساسية"
            description: "7 أدوات رئيسية متكاملة مصممة لمعالجة الدفعات الكبيرة بكفاءة وسرعة فائقة"
            badgeText: "7 أدوات جاهزة"
            badgeVariant: "success"
        }

        // 5. Responsive Tools Grid
        SinaxToolGrid {
            Layout.fillWidth: true
            spacing: Theme.spacingL
            minItemWidth: 320
            maxColumns: 3

            // Tool 1: Batch Rename
            SinaxToolCard {
                toolId: "batch_rename"
                title: "1. إعادة تسمية الملفات الجماعية"
                description: "تغيير أسماء مئات أو آلاف الملفات بنقرة واحدة باستخدام أكثر من 160 نمطاً جاهزاً، مع دعم الأرقام العربية، البحث والاستبدال، والمعاينة الحية."
                iconName: "rename"
                iconColor: "#60CDFF"
                badgeText: "نشط وشامل"
                favorite: fileManagementController.isFavorite("batch_rename")
                onClicked: fileManagementController.openTool("batch_rename")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("batch_rename"); }
            }

            // Tool 2: Universal Converter
            SinaxToolCard {
                toolId: "converter"
                title: "2. المحوّل الشامل للملفات"
                description: "تحويل احترافي فوري بين أكثر من 50 صيغة مستندات، صور، صوت، فيديو، جداول وبيانات مع معالجة دفعية فائقة السرعة وخيارات جودة مخصصة."
                iconName: "convert"
                iconColor: "#13C2C2"
                badgeText: "50+ صيغة"
                favorite: fileManagementController.isFavorite("converter")
                onClicked: fileManagementController.openTool("converter")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("converter"); }
            }

            // Tool 3: Merge & Combine
            SinaxToolCard {
                toolId: "merge_files"
                title: "3. دمج وتجميع الملفات"
                description: "دمج ملفات PDF بدقة مع إعادة الترتيب، ودمج مستندات Word، وتجميع جداول Excel في أوراق مستقلة، وضغط الصور والملفات في أرشيف ZIP."
                iconName: "merge"
                iconColor: "#FFB900"
                badgeText: "تجميع ذكي"
                favorite: fileManagementController.isFavorite("merge_files")
                onClicked: fileManagementController.openTool("merge_files")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("merge_files"); }
            }

            // Tool 4: Smart Organize
            SinaxToolCard {
                toolId: "smart_organize"
                title: "4. التنظيم الذكي للملفات"
                description: "ترتيب المجلدات المزدحمة تلقائياً حسب نوع الملفات، الامتداد، السنة، الشهر، الحجم أو حسب تصنيف الكلمات الأكاديمية والمشاريع."
                iconName: "organize"
                iconColor: "#52C41A"
                badgeText: "فرز آلي"
                favorite: fileManagementController.isFavorite("smart_organize")
                onClicked: fileManagementController.openTool("smart_organize")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("smart_organize"); }
            }

            // Tool 5: Search & Analysis
            SinaxToolCard {
                toolId: "search_analysis"
                title: "5. البحث والتحليل المتقدم"
                description: "البحث الذكي داخل المجلدات المتفرعة بدعم التعبيرات النمطية Regex، وفحص أحجام الملفات وتوزيع المساحة مع لوحة إحصائيات متكاملة."
                iconName: "search"
                iconColor: "#9254DE"
                badgeText: "تحليل معمق"
                favorite: fileManagementController.isFavorite("search_analysis")
                onClicked: fileManagementController.openTool("search_analysis")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("search_analysis"); }
            }

            // Tool 6: Duplicate Finder & Safe Copy
            SinaxToolCard {
                toolId: "duplicate_copy"
                title: "6. النسخ والنقل وكشف التكرار"
                description: "نقل ونسخ دفعات الملفات بأمان فائق، مع كشف فوري للملفات المتطابقة عبر خوارزمية SHA-256، وحماية سلة المحذوفات من الضياع."
                iconName: "duplicate"
                iconColor: "#F5222D"
                badgeText: "SHA-256"
                favorite: fileManagementController.isFavorite("duplicate_copy")
                onClicked: fileManagementController.openTool("duplicate_copy")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("duplicate_copy"); }
            }

            // Tool 7: Comprehensive PDF Center
            SinaxToolCard {
                toolId: "pdf_center"
                title: "7. مركز PDF الاحترافي الشامل"
                description: "المركز المتكامل لكافة أدوات PDF: دمج، تقسيم، ضغط، استخراج، تدوير، قص، تحويل إلى ومن صور، علامات مائية، ترقيم، وحماية AES."
                iconName: "pdf"
                iconColor: "#FF4D4F"
                badgeText: "مركز متكامل"
                favorite: fileManagementController.isFavorite("pdf_center")
                onClicked: fileManagementController.openTool("pdf_center")
                onFavoriteToggled: function(fav) { fileManagementController.toggleFavorite("pdf_center"); }
            }
        }

        // 6. Section: Recent Folders
        SinaxSectionHeader {
            visible: fileManagementController.recentFolders.length > 0
            title: "المجلدات المستخدمة مؤخراً"
            description: "الوصول السريع إلى المجلدات التي تمت معالجتها مؤخراً في SINAX"
        }

        Flow {
            visible: fileManagementController.recentFolders.length > 0
            Layout.fillWidth: true
            spacing: Theme.spacingM
            layoutDirection: Qt.RightToLeft

            Repeater {
                model: fileManagementController.recentFolders

                Rectangle {
                    implicitWidth: folderRow.implicitWidth + Theme.spacingL * 2
                    implicitHeight: 38
                    radius: Theme.radiusMedium
                    color: folderMouse.containsMouse ? Theme.surfaceHover : Theme.surface2
                    border.color: Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        id: folderRow
                        anchors.fill: parent
                        anchors.margins: Theme.spacingM
                        spacing: Theme.spacingS
                        layoutDirection: Qt.RightToLeft

                        Image {
                            width: 16
                            height: 16
                            source: "image://sinax/folder/" + encodeURIComponent(Theme.primary) + "/16"
                            fillMode: Image.PreserveAspectFit
                        }

                        Text {
                            text: modelData
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textPrimary
                            elide: Text.ElideMiddle
                            Layout.maximumWidth: 320
                        }
                    }

                    MouseArea {
                        id: folderMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            // Quick launch batch rename targeting this directory
                            fileManagementController.openTool("batch_rename");
                        }
                    }
                }
            }
        }
    }
}

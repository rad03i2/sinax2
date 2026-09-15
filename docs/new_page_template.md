# SINAX New Page Development Template
## القالب المرجعي المعياري لإنشاء صفحات ومراكز جديدة في SINAX

استخدم هذا القالب لإنشاء أي مركز أو أداة جديدة بطريقة قياسية تتبع معايير QML Phase 3 الموحدة.

---

## 1. هيكل الملفات المطلوب (File Layout)

عند إضافة ميزة أو مركز جديد باسم `feature_name`:
```text
app/
├── controllers/
│   └── feature_controller.py         # متحكم بايثون (QObject + Signals + Slots)
├── ui/
│   ├── qml/
│   │   └── pages/
│   │       └── FeatureCenterPage.qml # واجهة المستخدم الحديثة بتقنية QML
│   └── pages/
│       └── feature_page.py           # غلاف التوافق الرجعي (Legacy QWidget Wrapper)
```

---

## 2. قالب متحكم بايثون (`app/controllers/feature_controller.py`)

```python
# -*- coding: utf-8 -*-
"""
SINAX Feature Controller
Python bridge managing backend tasks, state, and properties for the feature center.
"""

from PySide6.QtCore import QObject, Signal, Slot, Property
from app.core.logger import get_logger

logger = get_logger("feature_controller")


class FeatureController(QObject):
    stateChanged = Signal()
    progressChanged = Signal(int, str)
    operationFinished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_busy = False
        self._progress = 0

    @Property(bool, notify=stateChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @Slot(str)
    def executeAction(self, target_path: str):
        """Executes the core action asynchronously."""
        if self._is_busy:
            return
        self._is_busy = True
        self.stateChanged.emit()
        logger.info(f"Executing feature action on: {target_path}")

        # Dispatch background worker here...
        # worker.finished.connect(self._on_worker_finished)


feature_controller = FeatureController()
```

---

## 3. قالب واجهة QML (`app/ui/qml/pages/FeatureCenterPage.qml`)

```qml
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

    ScrollBar.vertical: ScrollBar { active: true }

    ColumnLayout {
        id: contentCol
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: Theme.spacingL
        }
        spacing: Theme.spacingXL

        // 1. ترويسة الصفحة الموحدة
        SinaxPageHeader {
            title: "اسم المركز الجديد"
            subtitle: "شرح تفصيلي وموجز يوضح للمستخدم ما يقدمه هذا المركز."
            iconName: "tools"
            breadcrumb: "الرئيسية  ›  اسم المركز"
            primaryActionText: "بدء المعالجة"
            isPrimaryLoading: featureController.isBusy
            onPrimaryActionClicked: featureController.executeAction("")
        }

        // 2. بطاقة الإحصائيات أو المؤشرات
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingM
            layoutDirection: Qt.RightToLeft

            SinaxStatCard {
                Layout.fillWidth: true
                title: "إجمالي العمليات"
                value: "1,240"
                iconName: "chart"
                accentColor: Theme.accentPrimary
            }

            SinaxStatCard {
                Layout.fillWidth: true
                title: "الحالة العامة"
                value: "مستقر"
                iconName: "shield"
                accentColor: Theme.accentSuccess
            }
        }

        // 3. منطقة الإجراءات أو السحب والإفلات
        SinaxSectionHeader {
            title: "خيارات التشغيل"
            description: "تخصيص المعاملات والبدء السريع"
        }

        SinaxDropZone {
            Layout.fillWidth: true
            promptText: "اسحب الملفات هنا لبدء المعالجة الفورية..."
            onFilesDropped: function(paths) {
                if (paths.length > 0) {
                    featureController.executeAction(paths[0])
                }
            }
        }
    }
}
```

---

## 4. خطوات التسجيل والربط (Registration Checklist)

1. **تسجيل في `app/core/qml_helper.py`**:
   ```python
   from app.controllers.feature_controller import feature_controller
   # داخل configure_qml_engine:
   root_ctx.setContextProperty("featureController", feature_controller)
   ```
2. **تسجيل في `app/ui/main_window.py`**:
   * إضافة المعرف إلى `_ATTR_TO_INDEX`.
   * إضافة مصنع التحميل الكسول في `_setup_page_factories`.
   * ربط المسار والاسم العربي في `page_map` داخل `navigate_to`.
3. **التكامل مع لوحة الأوامر (`Ctrl+K`)**:
   * إضافة المسار باللغتين العربية والإنجليزية داخل `app/controllers/command_palette_controller.py`.

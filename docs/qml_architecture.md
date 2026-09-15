# SINAX QML Architecture Guide
## المعمارية البرمجية الشاملة لمنظومة واجهات QML والربط مع نواة Python

تعتمد منصة **SINAX** معمارية هجينة متطورة تجمع بين كفاءة محركات C++/Python في الخلفية وخفة وجمالية واجهات **Qt Quick / QML** الحديثة عبر **PySide6**.

---

## 1. بنية المنظومة (Architectural Layers)

```text
┌─────────────────────────────────────────────────────────────┐
│                      QML UI Layer                           │
│  (Qt Quick Controls, Fluid Animations, Modern Dark/Light)   │
│  Pages, Components, BeforeAfterViewer, Responsive Grids     │
└──────────────────────────────┬──────────────────────────────┘
                               │  Signals / Slots / Q_PROPERTY
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Python Controllers Layer                    │
│  (Navigation, Jobs, FileManagement, Audio, Video, Apps...)  │
│  QObject Singletons registered in QQmlContext               │
└──────────────────────────────┬──────────────────────────────┘
                               │  Worker Threads (QThread)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Engine & Services Layer                     │
│  (FFmpeg, StorageScanner, Win32 APIs, SQLite, WinGet, WMI)  │
│  100% Asynchronous Non-blocking Operations                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. جسر الربط الهجين (Python ↔ QML Bridge)

يتم ربط كائنات التحكم (Controllers) داخل بيئة محرك `QQmlEngine` مركزياً عبر ملف [`app/core/qml_helper.py`](file:///c:/Users/HP/Desktop/sinax2/app/core/qml_helper.py).

### خصائص السياق العامة (Root Context Properties):
* `navController`: التحكم في التنقل والسجل والتوجيه بين المراكز والصفحات الفرعية.
* `themeController`: إدارة السمات اللونية والتبديل الحي بين الداكن والفاتح ومزامنة التفضيلات.
* `dashboardController`: تغذية لوحة التحكم الرئيسية بالمؤشرات الحية وحالة العتاد.
* `jobController`: إدارة المهام الخلفية المتزامنة والمجدولة ومراقبة التقدم.
* `commandPaletteController`: لوحة الأوامر العالمية السريعة (`Ctrl+K`).
* `pdfController`: عمليات دمج، تقسيم، استخراج، تحويل، وتوقيع ملفات PDF.
* `imageController`: تحويل، ضغط، تغيير حجم، وتصفية الصور ومعاينات المقارنة.
* `videoController`: فحص ضغط الفيديو، كشف المسرعات العتادية (NVENC, QSV, AMF)، وسرعات المعالجة.
* `audioController`: تحويل الصوت، استخراج الصوت من الفيديو، وتوليد الأشكال الموجية.
* `appsController`: جرد البرامج المثبتة، تتبع WinGet، وإلغاء التثبيت الآمن المتسلسل.
* `networkController`: اختبارات سرعة الإنترنت الفعلية، تشخيص الأعطال، ومشاركة الملفات.
* `privacyController`: استخبارات حماية ويندوز، الخزنة المشفرة AES-256، وفحص الملفات.
* `historyController`: سجل العمليات والتراجع بنقرة واحدة وتتبع المسارات.
* `settingsController`: قراءة وتحديث وضبط إعدادات البرنامج ومزامنة التفضيلات.

---

## 3. نماذج البيانات التفاعلية (Data Models & Virtualization)

للتعامل مع آلاف السجلات (مثل جرد البرامج المثبتة أو آلاف العمليات السابقة) بدون أي بطء أو استهلاك زائد للذاكرة:
* تم بناء نماذج معتمدة على `QAbstractListModel`:
  * [`InstalledAppsModel`](file:///c:/Users/HP/Desktop/sinax2/app/controllers/apps_controller.py): فرز وتصفية البرامج حياً حسب الاسم والناشر والحجم والتاريخ.
  * [`HistoryModel`](file:///c:/Users/HP/Desktop/sinax2/app/controllers/history_controller.py): عرض آلاف العمليات مع دعم التراجع الحي وتحديث الحالة فورياً.
* تستخدم واجهة QML مكونات `ListView` مع `clip: true` و `reuseItems: true`، حيث يتم تصيير العناصر المرئية على الشاشة فقط (Virtual Scrolling).

---

## 4. معمارية الخيوط وتفادي التجمد (Threading & Zero Freezing)

1. **حظر العمليات الطويلة في خيط الواجهة**:
   * تُمنع أي عمليات قراءة أقراص، فحص شبكة، استعلامات WMI، أو معالجة وسائط في الخيط الرئيسي (GUI Thread).
   * يتم تفويض كافة العمليات الشاقة إلى `QThread` أو `Worker` منفصل.
2. **كبح وتيرة التحديثات (Update Throttling)**:
   * تقتصر إشارات تحديث التقدم والنسبة المئوية على تردد يتراوح بين **5 إلى 10 هرتز** (كل 100-200 ملي ثانية).
   * هذا يمنع إغراق حلقة أحداث واجهة المستخدم بآلاف الإشارات ويحافظ على سلاسة الرسوم بمعدل 60 إطاراً في الثانية.
3. **أمان الإلغاء (Cancellation Safety)**:
   * كافة العمال مدعومون بأعلام إلغاء (`is_cancelled` / `QAtomicInt`) تضمن إيقاف المهام بشكل آمن وفوري عند طلب المستخدم دون ترك عمليات معلقة.

---

## 5. مرونة التحميل الكسول والتحصين ضد الأعطال (Hardening & Fault Tolerance)

### التحميل الكسول (Lazy Loading Architecture):
* عند بدء التشغيل، يتم إنشاء لوحة التحكم الرئيسية (`DashboardPage`) فقط، بينما تظل باقي المراكز (1 إلى 22) كعناصر خفيفة (`Placeholders`).
* يتم إنشاء كل مركز فقط عند أول زيارة للمستخدم عبر `ensure_page_loaded(idx)`.
* يحقق هذا زمناً استثنائياً للتشغيل الأول للواجهة (**أقل من 65 ملي ثانية**).

### جدار حماية QML (QML Error Boundary):
* يتم تغليف عناصر QML عبر فئة [`QmlErrorBoundaryWidget`](file:///c:/Users/HP/Desktop/sinax2/app/core/qml_helper.py).
* في حال حدوث أي خطأ في التحميل، الصياغة (Syntax Error)، أو خطأ أثناء التشغيل (Runtime Error):
  * لا ينهار البرنامج إطلاقاً.
  * تظهر داخل الصفحة بطاقة خطأ أنيقة (`Fallback Card`) تحتوي على نص الخطأ التفصيلي.
  * يتوفر زر "إعادة تحميل الصفحة" وزر "نسخ تفاصيل الخطأ".
  * تظل كافة أقسام البرنامج الأخرى والقوائم تعمل بكفاءة تامة.

### وضع الإقلاع الآمن واستعادة الانهيارات (Safe UI Mode & Crash Recovery):
* يُمكن تشغيل البرنامج عبر الراية:
  ```bash
  SINAX.exe --safe-ui
  ```
* يقوم كائن [`crash_recovery_manager`](file:///c:/Users/HP/Desktop/sinax2/app/core/crash_recovery.py) بمراقبة موثوقية الإقلاع. في حال رصد انهيارين متتاليين أثناء الإقلاع، يُفعل الوضع الآمن تلقائياً.
* يوفر الوضع الآمن شريطاً علوياً فورياً للوصول السريع إلى سجلات الأخطاء وأداة "الإصلاح الذاتي" لمسح ذاكرة التخزين المؤقت وإعادة ضبط المعلمات.

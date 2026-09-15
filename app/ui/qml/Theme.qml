pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Mode state
    property bool isDark: (typeof themeController !== "undefined") ? themeController.isDark : true

    // Scrollbar tokens
    property color scrollbarThumb: isDark ? "#475569" : "#CBD5E1"
    property color scrollbarTrack: "transparent"

    // Backgrounds & Surfaces (Phase 2 Multi-level)
    property color background: isDark ? "#0D1117" : "#F6F8FA"
    property color surface: isDark ? "#161B22" : "#FFFFFF"
    property color surface1: isDark ? "#161B22" : "#FFFFFF"
    property color surface2: isDark ? "#21262D" : "#F8FAFC"
    property color surface3: isDark ? "#30363D" : "#EDF2F7"
    property color surfaceElevated: isDark ? "#21262D" : "#FFFFFF"
    property color surfaceHover: isDark ? "#2A313C" : "#F3F4F6"
    property color surfacePressed: isDark ? "#30363D" : "#E5E7EB"
    property color sidebar: isDark ? "#13171D" : "#F3F4F6"
    property color sidebarHover: isDark ? "#1C2128" : "#E5E7EB"
    property color overlay: isDark ? "#80000000" : "#60000000"
    property color divider: isDark ? "#21262D" : "#E2E8F0"
    property color focusRing: isDark ? "#38BDF8" : "#0284C7"

    // Primary & Accent Colors (SINAX Modern Blue)
    property color primary: isDark ? "#38BDF8" : "#0284C7"
    property color primaryLight: isDark ? "#60CDFF" : "#38BDF8"
    property color primaryHover: isDark ? "#7DD3FC" : "#0369A1"
    property color primaryPressed: isDark ? "#0284C7" : "#075985"
    property color primaryTint: isDark ? "#152636" : "#E0F2FE"

    // Typography Colors
    property color textPrimary: isDark ? "#F0F6FC" : "#1F2328"
    property color textSecondary: isDark ? "#8B949E" : "#656D76"
    property color textMuted: isDark ? "#484F58" : "#8C959F"
    property color textOnPrimary: "#FFFFFF"

    // Borders & Dividers
    property color borderSubtle: isDark ? "#30363D" : "#D0D7DE"
    property color borderMuted: isDark ? "#21262D" : "#E1E4E8"
    property color borderAccent: isDark ? "#38BDF8" : "#0284C7"

    // Status Colors & Semantic Surfaces
    property color success: "#238636"
    property color successSurface: isDark ? "#0D2818" : "#DCFCE7"
    property color successTint: isDark ? "#0D2818" : "#DCFCE7"
    property color warning: "#D29922"
    property color warningSurface: isDark ? "#2A1F08" : "#FEF9C3"
    property color warningTint: isDark ? "#2A1F08" : "#FEF9C3"
    property color error: "#F85149"
    property color errorSurface: isDark ? "#2E1114" : "#FEE2E2"
    property color errorTint: isDark ? "#2E1114" : "#FEE2E2"
    property color info: "#38BDF8"
    property color infoSurface: isDark ? "#152636" : "#E0F2FE"
    property color infoTint: isDark ? "#152636" : "#E0F2FE"

    // Icon Size Tokens (Standardized Scale - No arbitrary pixel sizes allowed)
    property int iconXS: 12
    property int iconSmall: 16
    property int iconMedium: 20
    property int iconLarge: 24
    property int iconXL: 32
    property int iconXXL: 48
    property int iconHero: 64

    // Icon Color Tokens
    property color iconDefault: textSecondary
    property color iconHover: primary
    property color iconActive: primary
    property color iconSelected: primary
    property color iconDisabled: textMuted
    property color iconMuted: textMuted
    property color iconPrimary: primary
    property color iconSuccess: success
    property color iconWarning: warning
    property color iconDanger: error
    property color iconInfo: info

    // Spacing scale
    property int spacingXS: 4
    property int spacingS: 8
    property int spacingM: 12
    property int spacingL: 16
    property int spacingXL: 24
    property int spacing2XL: 32

    // Border Radii
    property int radiusSmall: 4
    property int radiusMedium: 8
    property int radiusLarge: 12
    property int radiusPill: 999

    // Typography Fonts & Sizes
    property string fontFamily: "Segoe UI"
    property string fontMono: "Cascadia Code, Consolas, Courier New, monospace"
    property int fontSmall: 11
    property int fontCaption: 11
    property int fontBody: 13
    property int fontMedium: 14
    property int fontLarge: 16
    property int fontCardTitle: 15
    property int fontSectionTitle: 16
    property int fontPageTitle: 20
    property int fontTitle: 20
    property int fontDisplay: 24

    // Accessibility
    property bool reducedMotion: false

    // Animations (Windows 11 Fluid Timing)
    property int durationFast: reducedMotion ? 0 : 100
    property int durationNormal: reducedMotion ? 0 : 160
    property int durationSlow: reducedMotion ? 0 : 220

    // Easing Curves
    property int standardEasing: Easing.OutCubic

    function setDarkMode(val) {
        isDark = val;
    }

    Component.onCompleted: {
        if (typeof themeController !== "undefined") {
            isDark = themeController.isDark;
            themeController.themeChanged.connect(function() {
                isDark = themeController.isDark;
            });
        }
    }
}

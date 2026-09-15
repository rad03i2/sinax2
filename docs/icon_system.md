# SINAX Icon System Architecture & Developer Guide

## 1. Overview & Principles

The SINAX Icon System provides a single, high-performance, unified visual symbol architecture across the entire desktop application for both modern QML/Qt Quick views and legacy Python/QWidget components.

### Core Tenets
1. **One Icon Family**: Exclusively based on **Microsoft Fluent UI System Icons** (MIT License). Windows 11 desktop ergonomics, clean 24x24 viewBox vectors, and balanced visual weights. No mixing of foreign icon families.
2. **Zero Emoji Clutter**: Elimination of ad-hoc Unicode emojis (📁, ⚙, 🔒, 🌐, 💾, ⭐, ✓, ✕, ⚠️) from production buttons, badges, navigation, and registries.
3. **Single Source of Truth**: Centralized registry (`app.core.icon_registry.IconRegistry`) mapping semantic names and aliases to SVG assets with explicit category and RTL mirroring metadata.
4. **Theme & State Aware**: Dynamic SVG color substitution (`fill="currentColor"` injected in-memory) matching SINAX theme tokens without requiring duplicate files per color.
5. **Intelligent RTL Directional Mirroring**: Only directional actions (back, forward, chevron navigation, undo, redo) flip horizontally when running under RTL (Arabic). Content and metaphor icons (folder, shield, play, check) remain invariant.
6. **Sub-millisecond LRU Cache**: QPixmap and QIcon renders are cached in-memory with a 300-entry LRU cache, ensuring zero startup lag and instant UI response.

---

## 2. Directory Structure

```text
sinax2/
├── resources/icons/
│   ├── actions/          # add, back, check, copy, cut, delete, dismiss, edit, filter, ...
│   ├── devices/          # cpu, gpu, memory, disk, usb, battery, monitor, ...
│   ├── files/            # file, pdf, convert, merge, split, organize, duplicate, ...
│   ├── media/            # image, video, audio, play, pause, stop, mute, ...
│   ├── navigation/       # home, folder, media, storage, devices, apps, network, shield, ...
│   ├── network/          # wifi, ethernet, cloud, globe, ping, share, ...
│   ├── security/         # lock, unlock, key, certificate, clean, scan, ...
│   ├── status/           # info, success, warning, error, question
│   ├── system/           # settings, info, search, history, optimize, ...
│   └── tools/            # wrench, terminal, hammer, flash, ...
├── app/
│   ├── core/
│   │   └── icon_registry.py       # Canonical registry, aliases, IconService, LRU cache
│   ├── ui/
│   │   ├── qml_icon_provider.py   # QQuickImageProvider ("image://sinax/")
│   │   ├── icons.py               # Legacy bridge delegating to IconService.get_qicon
│   │   └── qml/
│   │       ├── Theme.qml          # Size tokens (iconXS..iconHero) & color tokens
│   │       ├── components/
│   │       │   ├── SinaxIcon.qml       # Core declarative icon component
│   │       │   └── SinaxIconButton.qml # Accessible icon button with tooltips
│   │       └── pages/
│   │           └── DeveloperIconGalleryPage.qml # Interactive developer test gallery
└── tools/
    └── build_icons.py             # CLI validator & icons.qrc resource builder
```

---

## 3. Size & Color Tokens (`Theme.qml`)

### Size Tokens
| Token | Pixel Size | Primary Use Case |
|---|---|---|
| `Theme.iconXS` | 12 px | Micro badges, inline indicators, status dots |
| `Theme.iconSmall` | 16 px | Dense tables, compact toolbars, secondary actions |
| `Theme.iconMedium` | 20 px | Default button icons, sidebar items, standard inputs |
| `Theme.iconLarge` | 24 px | Standard action buttons, cards, headers |
| `Theme.iconXL` | 32 px | Feature cards, category tiles |
| `Theme.iconXXL` | 48 px | Empty state illustrations, dialog headers |
| `Theme.iconHero` | 64 px | Wizard banners, splash screens, hero banners |

### Color Tokens
| Token | Default Dark Value | Semantics |
|---|---|---|
| `Theme.iconDefault` | `#E2E8F0` | Standard icon foreground |
| `Theme.iconHover` | `#FFFFFF` | Interactive hover highlight |
| `Theme.iconActive` | `#6366F1` | Selected / pressed state |
| `Theme.iconDisabled` | `#64748B` | Inactive / disabled elements |
| `Theme.iconMuted` | `#94A3B8` | Subtle auxiliary indicators |
| `Theme.iconPrimary` | `#6366F1` | Primary brand accent |
| `Theme.iconSuccess` | `#10B981` | Success states and verified indicators |
| `Theme.iconWarning` | `#F59E0B` | Cautionary warnings and doctor alerts |
| `Theme.iconDanger` | `#EF4444` | Errors and destructive actions |
| `Theme.iconInfo` | `#38BDF8` | Informational callouts |

---

## 4. QML Usage Guide

### A. Declarative Icon (`SinaxIcon`)
```qml
import QtQuick
import "../components"
import ".."

// 1. Basic Icon
SinaxIcon {
    iconName: "folder"
    size: Theme.iconMedium
}

// 2. State-aware Colored & Filled Variant
SinaxIcon {
    iconName: "star"
    variant: isFavorite ? "filled" : "regular"
    color: isFavorite ? Theme.warning : Theme.iconMuted
    size: Theme.iconLarge
}

// 3. Directional Icon with Automatic RTL Mirroring
SinaxIcon {
    iconName: "chevron_left"
    size: Theme.iconSmall
    // Automatically mirrors horizontally in RTL (Arabic) layout!
}
```

### B. Accessible Icon Button (`SinaxIconButton`)
`SinaxIconButton` enforces accessibility standards with mandatory tooltips and keyboard focus:
```qml
SinaxIconButton {
    iconName: "refresh"
    tooltipText: "تحديث البيانات الآن"
    accessibleName: "زر تحديث البيانات"
    size: Theme.iconMedium
    onClicked: refreshData()
}
```

### C. Direct Image Provider
If binding directly inside custom QML elements or shaders:
```qml
Image {
    source: "image://sinax/settings:regular?color=#6366F1"
    sourceSize.width: 24
    sourceSize.height: 24
}
```

---

## 5. Python & QWidget Usage Guide

Legacy dialogs or QWidget views consume icons directly via `IconService`:

```python
from app.core.icon_registry import IconService

# 1. Fetching a themed QIcon for QPushButton or QAction
button.setIcon(IconService.get_qicon("save", color="#FFFFFF", size=20))

# 2. Status icon with custom color
status_icon = IconService.get_qicon("check", color="#10B981", size=16)

# 3. Explicit RTL mirroring (when building custom painter delegates)
pixmap = IconService.get_pixmap("back", size=24, color="#E2E8F0", mirrored=True)

# 4. Backward-compatible helper bridge (app/ui/icons.py)
from app.ui.icons import get_icon
action_icon = get_icon("folder", size=24, color="#6366F1")
```

---

## 6. RTL Mirroring Rules

In Arabic (RTL) desktop applications, flipping every icon causes severe UX confusion. SINAX implements strict directional filtering:

### Icons That ARE Mirrored (`rtl_mirror = True`):
- `back` / `forward`
- `previous` / `next`
- `chevron_left` / `chevron_right`
- `undo` / `redo`

### Icons That ARE NOT Mirrored (`rtl_mirror = False`):
- Real-world objects: `folder`, `file`, `camera`, `printer`, `usb`, `keyboard`, `display`
- Media controls: `play`, `pause`, `stop`, `volume`, `mute`
- Universal status symbols: `check`, `dismiss`, `warning`, `error`, `info`, `search`
- Brand and security: `shield`, `lock`, `key`

---

## 7. Developer Icon Gallery

Developers can preview, search, and verify all visual symbols interactively:
- Navigate to route: `icon_gallery` (via `NavigationController.navigateTo("icon_gallery")` or the Component Gallery link).
- **Features**:
  - Live search across names, categories, and aliases.
  - Category pill filter tabs (`all`, `navigation`, `actions`, `files`, `media`, `devices`, etc.).
  - Size switcher (16px, 20px, 24px, 32px, 48px).
  - Dynamic color state previews (`Default`, `Hover`, `Primary`, `Success`, `Warning`, `Danger`).
  - Regular / Filled variant toggle.
  - Interactive RTL / LTR layout flip preview.
  - 1-Click icon name copy with clipboard confirmation.

---

## 8. CLI Builder & Quality Assurance (`tools/build_icons.py`)

Run the automated icon build and validation suite at any time:

```bash
# Validate SVG XML syntax, viewBox geometry, and registry consistency:
python tools/build_icons.py --check

# Generate / Update Qt Resource file (app/resources/icons.qrc):
python tools/build_icons.py --qrc

# Run full check + rebuild:
python tools/build_icons.py
```\n
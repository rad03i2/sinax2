# -*- coding: utf-8 -*-
"""Runtime UI reliability fixes for SINAX.

This module intentionally keeps the fixes centralized so they are applied before
MainWindow creates any lazy pages. It restores the proven QWidget catalogs for
PDF / Image / Video / Audio centers, removes the obsolete multimedia placeholder,
protects the universal converter, and improves precision-touchpad two-finger
scrolling without changing a normal 120-step mouse wheel.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QEvent, QPoint, QCoreApplication, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QMessageBox

from app.core.logger import get_logger

logger = get_logger("runtime_ui_fixes")


class TouchpadScrollAccelerator(QObject):
    """Amplify precision-touchpad scrolling while leaving normal mouse wheels alone.

    Depending on the Windows/Qt/driver combination, a precision touchpad may arrive
    as pixelDelta(), as small/high-resolution angleDelta() values, or as wheel events
    carrying a scroll phase. Older SINAX code only accelerated pixelDelta(), so on
    some Windows laptops the two-finger gesture was never detected. This filter
    recognises all three forms and scales the event before the target widget handles
    it. A traditional mouse wheel normally emits +/-120 angle units with no scroll
    phase and is therefore passed through unchanged.
    """

    def __init__(self, parent=None, factor: float = 4.0):
        super().__init__(parent)
        self.factor = max(1.0, float(factor))
        self._reposting = False

    @staticmethod
    def _is_precision_scroll(event: QWheelEvent) -> bool:
        pixel = event.pixelDelta()
        if not pixel.isNull():
            return True

        # Precision touchpads frequently expose ScrollBegin/ScrollUpdate/ScrollEnd
        # even when the Windows backend reports angle deltas instead of pixels.
        try:
            if event.phase() != Qt.ScrollPhase.NoScrollPhase:
                return True
        except Exception:
            pass

        angle = event.angleDelta()
        values = [abs(v) for v in (angle.x(), angle.y()) if v]
        if not values:
            return False

        # A classic wheel notch is 120 units. High-resolution touchpad/wheel events
        # are usually smaller than one notch or are not exact multiples of 120.
        return max(values) < 120 or any((v % 120) != 0 for v in values)

    def eventFilter(self, watched, event):
        if self._reposting or event.type() != QEvent.Wheel:
            return False

        try:
            if not self._is_precision_scroll(event):
                return False

            pixel = event.pixelDelta()
            angle = event.angleDelta()
            scaled_pixel = QPoint(
                int(round(pixel.x() * self.factor)),
                int(round(pixel.y() * self.factor)),
            )
            scaled_angle = QPoint(
                int(round(angle.x() * self.factor)),
                int(round(angle.y() * self.factor)),
            )

            if scaled_pixel == pixel and scaled_angle == angle:
                return False

            accelerated = QWheelEvent(
                event.position(),
                event.globalPosition(),
                scaled_pixel,
                scaled_angle,
                event.buttons(),
                event.modifiers(),
                event.phase(),
                event.inverted(),
            )
            self._reposting = True
            QCoreApplication.sendEvent(watched, accelerated)
            event.accept()
            return True
        except Exception as exc:
            # Scrolling enhancement must never be able to break the application.
            logger.debug("Touchpad acceleration fallback: %s", exc)
            return False
        finally:
            self._reposting = False


def _stable_center_init(self):
    """Initialize a media/PDF center with its reliable QWidget catalog.

    The project already contains complete QWidget catalogs and workspaces for all
    four centers. The newer QML landing pages could load without their tool model
    in packaged builds, producing an empty/non-working center. This initializer
    keeps the modern app shell while using the proven catalog implementation.
    """

    self.stack = QStackedWidget(self)
    outer_layout = QVBoxLayout(self)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.addWidget(self.stack)

    catalog = self.catalog_widget
    self.stack.addWidget(catalog)
    self.stack.setCurrentIndex(0)


def _is_in_workspace(self) -> bool:
    return hasattr(self, "stack") and self.stack.currentIndex() == 1


def _patch_centers() -> None:
    from app.ui.pages.pdf_center_page import PDFCenterPage
    from app.ui.pages.image_center_page import ImageCenterPage
    from app.ui.pages.video_center_page import VideoCenterPage
    from app.ui.pages.audio_center_page import AudioCenterPage

    # Use the already-implemented, fully interactive QWidget catalogs.
    for cls in (PDFCenterPage, ImageCenterPage, VideoCenterPage, AudioCenterPage):
        cls._init_ui = _stable_center_init

    # MainWindow expects these compatibility methods for nested back navigation.
    PDFCenterPage.is_in_workspace = _is_in_workspace
    PDFCenterPage.close_workspace = PDFCenterPage._on_back_to_catalog

    ImageCenterPage.is_in_workspace = _is_in_workspace
    ImageCenterPage.close_workspace = ImageCenterPage._close_workspace

    VideoCenterPage.is_in_workspace = _is_in_workspace
    VideoCenterPage.close_workspace = VideoCenterPage._close_workspace

    if not hasattr(AudioCenterPage, "is_in_workspace"):
        AudioCenterPage.is_in_workspace = _is_in_workspace


def _remove_obsolete_media_placeholder() -> None:
    """Remove 'أدوات الوسائط (قريباً)' from navigation before the sidebar is built."""

    from app.core.navigation_constants import NAVIGATION_SECTIONS

    changed = False
    for section in NAVIGATION_SECTIONS:
        if section.get("id") != "multimedia":
            continue
        children = section.get("children", [])
        filtered = [item for item in children if item.get("id") != "media_tools"]
        if len(filtered) != len(children):
            section["children"] = filtered
            changed = True
        break

    try:
        from app.controllers.navigation_controller import navigation_controller

        navigation_controller.ROUTE_META.pop("media_tools", None)
        if changed and hasattr(navigation_controller, "navModel"):
            navigation_controller.navModel._build_model()
    except Exception as exc:
        logger.warning("Could not rebuild navigation after media placeholder removal: %s", exc)


def _patch_pdf_back_navigation() -> None:
    """Make the global Back button close an open PDF workspace first."""

    from app.ui.main_window import MainWindow

    if getattr(MainWindow, "_sinax_pdf_back_patch", False):
        return

    original_go_back = MainWindow._go_back

    def _go_back_with_pdf_workspace(self):
        try:
            if self.stack.currentIndex() == 10 and self.is_page_loaded(10):
                page = self.pdf_center_page
                if hasattr(page, "is_in_workspace") and page.is_in_workspace():
                    page.close_workspace()
                    return
        except Exception:
            logger.exception("PDF nested back-navigation failed; using normal history.")
        return original_go_back(self)

    MainWindow._go_back = _go_back_with_pdf_workspace
    MainWindow._sinax_pdf_back_patch = True


def _patch_converter_error_boundary() -> None:
    """Prevent one converter backend error from making the whole center appear dead."""

    from app.ui.pages.universal_converter_page import UniversalConverterPage

    if getattr(UniversalConverterPage, "_sinax_converter_patch", False):
        return

    original_open = UniversalConverterPage._open_workspace

    def _safe_open_workspace(self, direction, card_id):
        try:
            return original_open(self, direction, card_id)
        except Exception as exc:
            logger.exception("Failed to open converter workspace %s: %s", card_id, exc)
            try:
                self.status_changed.emit(
                    "تعذر فتح مساحة هذا التحويل. تم إبقاء مركز المحول فعالاً ويمكن تجربة تحويل آخر.",
                    False,
                    True,
                )
            except Exception:
                pass
            QMessageBox.warning(
                self,
                "تعذر فتح التحويل",
                "تعذر تهيئة هذا التحويل تحديداً، لكن مركز المحول لم يتوقف.\n\n"
                f"التفاصيل التقنية: {exc}",
            )
            self.stack.setCurrentIndex(0)
            self.current_workspace = None
            return None

    UniversalConverterPage._open_workspace = _safe_open_workspace
    UniversalConverterPage._sinax_converter_patch = True


def install_runtime_ui_fixes(app) -> TouchpadScrollAccelerator:
    """Install all UI reliability fixes before MainWindow creates lazy pages."""

    _remove_obsolete_media_placeholder()
    _patch_centers()
    _patch_pdf_back_navigation()
    _patch_converter_error_boundary()

    accelerator = TouchpadScrollAccelerator(app, factor=4.0)
    app.installEventFilter(accelerator)
    app._sinax_touchpad_scroll_accelerator = accelerator

    logger.info(
        "Runtime UI fixes installed: stable PDF/media catalogs, converter boundary, "
        "media placeholder removed, precision scroll x%.1f",
        accelerator.factor,
    )
    return accelerator

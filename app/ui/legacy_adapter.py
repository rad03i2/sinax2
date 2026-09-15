# -*- coding: utf-8 -*-
"""
SINAX Legacy Page Adapter
Bridges QML NavigationController routes to legacy Qt Widget stacked pages.
Enables seamless co-existence of QML views and Qt Widget centers.
"""

import time
from typing import Callable, Dict, Optional
from PySide6.QtWidgets import QStackedWidget, QWidget
from app.controllers.navigation_controller import navigation_controller
from app.core.logger import get_logger

logger = get_logger("legacy_adapter")


class LegacyPageAdapter:
    """Manages routing between QML navigation actions and stacked Qt Widget pages."""

    def __init__(self, stack: QStackedWidget, ensure_page_fn: Callable[[int], QWidget]):
        self.stack = stack
        self.ensure_page_fn = ensure_page_fn
        self.route_to_index: Dict[str, int] = {}
        self.index_to_route: Dict[int, str] = {}

    def register_route(self, route_id: str, stack_index: int):
        self.route_to_index[route_id] = stack_index
        self.index_to_route[stack_index] = route_id

    def navigate_route(self, route_id: str) -> bool:
        t0 = time.perf_counter()
        idx = self.route_to_index.get(route_id)
        if idx is None:
            logger.warning(f"Unknown navigation route: {route_id}")
            return False

        # Ensure page is materialized if currently a placeholder
        self.ensure_page_fn(idx)
        self.stack.setCurrentIndex(idx)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(f"[LATENCY] Route '{route_id}' (index {idx}) presented in {elapsed_ms:.1f}ms")
        return True

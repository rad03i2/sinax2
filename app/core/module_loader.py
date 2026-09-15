# -*- coding: utf-8 -*-
"""
SINAX Center Module Loader & Subpage Lazy Registry Architecture
Provides lifecycle management, background service decoupling, and instant page caching
to guarantee zero UI freeze during navigation.
"""

from abc import ABC, abstractmethod
import time
from typing import Any, Callable, Dict, List, Optional
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget

from app.core.logger import get_logger

logger = get_logger("module_loader")


class BaseCenterLoader(ABC):
    """
    Abstract lifecycle loader for SINAX major centers and modules.
    Decouples lightweight UI construction from asynchronous heavy background services.
    """

    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False
        self.is_services_loaded = False
        self._cached_widget: Optional[QWidget] = None

    def initialize(self) -> None:
        """Lightweight configuration and metadata initialization (< 5ms)."""
        self.is_initialized = True

    @abstractmethod
    def load_ui(self) -> QWidget:
        """Constructs and returns the primary UI widget (Catalog or Overview). Must complete in < 150ms."""
        pass

    def load_services(self, on_ready_callback: Optional[Callable[[], None]] = None) -> None:
        """Runs heavy background probes, hardware scans, or database checks asynchronously."""
        self.is_services_loaded = True
        if on_ready_callback:
            on_ready_callback()

    def unload(self) -> None:
        """Releases memory, stops active pollers/threads when memory eviction is triggered."""
        self._cached_widget = None
        self.is_services_loaded = False


class SubpageLazyRegistry:
    """
    Manages lazy instantiation and instant caching of subpages inside major tabbed centers
    (e.g., DevicesPage, SystemStoragePage, BackupSyncPage).
    Eliminates the multi-second UI freeze caused by eagerly creating 10-14 subpages at once.
    """

    def __init__(self, stack: QStackedWidget):
        self._stack = stack
        self._factories: Dict[str, Callable[[], QWidget]] = {}
        self._instances: Dict[str, QWidget] = {}
        self._key_to_index: Dict[str, int] = {}
        self._index_to_key: Dict[int, str] = {}
        self._placeholders: Dict[int, QWidget] = {}

    def register_subpage(self, key: str, index: int, factory: Callable[[], QWidget], eager: bool = False) -> None:
        """Registers a subpage factory with its designated stacked widget index."""
        self._factories[key] = factory
        self._key_to_index[key] = index
        self._index_to_key[index] = key

        if eager:
            # Instantiate immediately (used strictly for page 0: Overview)
            widget = factory()
            self._instances[key] = widget
            if self._stack.count() > index:
                self._stack.removeWidget(self._stack.widget(index))
                self._stack.insertWidget(index, widget)
            else:
                self._stack.addWidget(widget)
        else:
            # Insert a lightweight placeholder widget in the stack to preserve index positions
            placeholder = QWidget()
            placeholder.setObjectName(f"Placeholder_{key}")
            self._placeholders[index] = placeholder
            self._stack.addWidget(placeholder)

    def is_loaded(self, key: str) -> bool:
        """Returns True if the subpage has already been instantiated."""
        return key in self._instances

    def get_or_create(self, key: str) -> Optional[QWidget]:
        """
        Retrieves the cached subpage instance or instantiates it on-demand in < 50ms,
        seamlessly swapping out the placeholder inside QStackedWidget.
        """
        if key in self._instances:
            return self._instances[key]

        factory = self._factories.get(key)
        if not factory:
            logger.warning(f"No factory registered for subpage '{key}'")
            return None

        idx = self._key_to_index.get(key)
        if idx is None:
            return None

        start_time = time.perf_counter()
        logger.info(f"Lazy-loading subpage '{key}' at index {idx}...")
        widget = factory()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(f"Subpage '{key}' instantiated in {elapsed_ms:.1f}ms")

        self._instances[key] = widget

        # Swap placeholder with real widget in stack
        placeholder = self._placeholders.pop(idx, None)
        self._stack.removeWidget(placeholder or self._stack.widget(idx))
        self._stack.insertWidget(idx, widget)

        return widget

    def switch_to(self, key: str) -> Optional[QWidget]:
        """Ensures the target subpage is loaded, switches the stack to its index, and returns the widget."""
        widget = self.get_or_create(key)
        idx = self._key_to_index.get(key)
        if idx is not None and self._stack.currentIndex() != idx:
            self._stack.setCurrentIndex(idx)
        return widget


class PageCacheManager:
    """
    Central Page Cache Manager for MainWindow.
    Ensures that once a center or tool page is visited, it stays resident in memory
    so subsequent visits switch instantaneously in < 15ms.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PageCacheManager, cls).__new__(cls)
            cls._instance._cache = {}
            cls._instance._access_timestamps = {}
        return cls._instance

    def store(self, key: str, widget: QWidget) -> None:
        self._cache[key] = widget
        self._access_timestamps[key] = time.time()

    def get(self, key: str) -> Optional[QWidget]:
        widget = self._cache.get(key)
        if widget:
            self._access_timestamps[key] = time.time()
        return widget

    def contains(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()
        self._access_timestamps.clear()

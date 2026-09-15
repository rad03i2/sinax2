# -*- coding: utf-8 -*-
"""
SINAX System & Storage Services Package
"""

from app.services.system_storage.cleanup_service import CleanupItem, CleanupResult, CleanupService
from app.services.system_storage.device_info_service import DeviceInfoService, SystemSpecs
from app.services.system_storage.disk_health_service import DiskHealthService, LogicalDriveInfo, PhysicalDiskInfo
from app.services.system_storage.performance_service import PerformanceService, PerformanceSnapshot
from app.services.system_storage.process_service import FileLockerInfo, ProcessDetail, ProcessInfo, ProcessService
from app.services.system_storage.recommendation_engine import RecommendationCard, RecommendationEngine
from app.services.system_storage.snapshot_service import SnapshotService
from app.services.system_storage.storage_analyzer import (
    AgeStats,
    CategoryStats,
    DownloadsAnalysis,
    ExtensionStats,
    StorageAnalysisReport,
    StorageAnalyzer,
    SystemReservedInfo,
)
from app.services.system_storage.storage_scanner import FileItem, FolderNode, FastStorageScanner, ScanResult, format_bytes

__all__ = [
    "FastStorageScanner",
    "ScanResult",
    "FileItem",
    "FolderNode",
    "format_bytes",
    "StorageAnalyzer",
    "StorageAnalysisReport",
    "CategoryStats",
    "AgeStats",
    "ExtensionStats",
    "SystemReservedInfo",
    "DownloadsAnalysis",
    "CleanupService",
    "CleanupItem",
    "CleanupResult",
    "DiskHealthService",
    "LogicalDriveInfo",
    "PhysicalDiskInfo",
    "PerformanceService",
    "PerformanceSnapshot",
    "ProcessService",
    "ProcessInfo",
    "ProcessDetail",
    "FileLockerInfo",
    "StartupService",
    "DeviceInfoService",
    "SystemSpecs",
    "SnapshotService",
    "RecommendationEngine",
    "RecommendationCard",
]

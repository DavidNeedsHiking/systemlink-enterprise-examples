"""
SystemLink Enterprise API Client - Core Library

This package provides reusable wrappers for SystemLink REST APIs.

Usage:
    from core.systemlink_client import get_asset_client, get_dataframe_client
    from core.outlier_detection import OutlierDetector
"""

from .systemlink_client import (
    SystemLinkClient,
    AssetClient,
    TestMonitorClient,
    NotificationClient,
    DataFrameClient,
    get_asset_client,
    get_testmonitor_client,
    get_notification_client,
    get_dataframe_client,
)

from .outlier_detection import (
    OutlierDetector,
    detect_outliers_log_sigma,
    detect_outliers_percentile,
    detect_outliers_asymmetric_mad,
)

__all__ = [
    # Client classes
    "SystemLinkClient",
    "AssetClient",
    "TestMonitorClient",
    "NotificationClient",
    "DataFrameClient",
    # Factory functions
    "get_asset_client",
    "get_testmonitor_client",
    "get_notification_client",
    "get_dataframe_client",
    # Outlier detection
    "OutlierDetector",
    "detect_outliers_log_sigma",
    "detect_outliers_percentile",
    "detect_outliers_asymmetric_mad",
]

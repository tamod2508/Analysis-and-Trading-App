# config/__init__.py

"""
Configuration package with automatic hardware adaptation
"""

from .settings import config, AppConfig, configure_logging_from_yaml
from .constants import (
    # Enums
    Exchange,
    Interval,
    InstrumentType,
    Segment,
    CompressionType,

    # Exchange-Segment mappings
    EXCHANGE_TO_SEGMENT,
    SEGMENT_TO_EXCHANGES,

    # Validation limits
    ValidationLimits,
    VALIDATION_LIMITS,
    MIN_PRICE,
    MAX_PRICE,
    MIN_VOLUME,
    MAX_VOLUME,
    MIN_DATE,
    MAX_DATE,

    # File size limits
    MAX_HDF5_FILE_SIZE_GB,
    MAX_BACKUP_SIZE_GB,
    MAX_EXPORT_SIZE_MB,
    MAX_LOG_FILE_SIZE_MB,
    MAX_TOTAL_DATA_SIZE_GB,

    # Application Configuration
    PRIMARY_INTERVALS,
    DERIVED_INTERVALS,

    # Kite API Constants
    INTERVAL_FETCH_LIMITS,
    IST,
    HISTORICAL_DATA_START,
    API_LIMITS,

    # HDF5 Constants
    HDF5_DATASETS,
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    COLUMN_DTYPES,

    # UI Constants
    CHART_TYPES,
    TIME_RANGES,
    EXPORT_FORMATS,

    # Messages
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,

    # Corporate Actions
    CIRCUIT_LIMIT_PERCENT,
    CORPORATE_ACTION_RATIOS,
    CORPORATE_ACTIONS_FILENAME,
    CA_DETECTION_THRESHOLD,
    CA_HIGH_CONFIDENCE_THRESHOLD,
    CA_MEDIUM_CONFIDENCE_THRESHOLD,

    HDF5_STORAGE_CHUNKS,
    CHUNK_SIZES  # Deprecated alias
)
from .optimizer import optimizer, get_system_info, get_detailed_system_info

__all__ = [
    # Core config
    'config',
    'AppConfig',
    'configure_logging_from_yaml',

    # Validation
    'MIN_PRICE',
    'MAX_PRICE',
    'MIN_VOLUME',
    'MAX_VOLUME',
    'MIN_DATE',
    'MAX_DATE',

    # File size limits
    'MAX_HDF5_FILE_SIZE_GB',
    'MAX_BACKUP_SIZE_GB',
    'MAX_EXPORT_SIZE_MB',
    'MAX_LOG_FILE_SIZE_MB',
    'MAX_TOTAL_DATA_SIZE_GB',

    # Optimizer
    'optimizer',
    'get_system_info',
    'get_detailed_system_info',

    # Enums
    'Exchange',
    'Interval',
    'InstrumentType',
    'Segment',
    'CompressionType',

    # Exchange-Segment mappings
    'EXCHANGE_TO_SEGMENT',
    'SEGMENT_TO_EXCHANGES',

    # Validation limits (new)
    'ValidationLimits',
    'VALIDATION_LIMITS',

    # Application Configuration
    'PRIMARY_INTERVALS',
    'DERIVED_INTERVALS',

    # Kite API
    'INTERVAL_FETCH_LIMITS',
    'IST',
    'HISTORICAL_DATA_START',
    'API_LIMITS',

    # HDF5
    'HDF5_DATASETS',
    'REQUIRED_COLUMNS',
    'OPTIONAL_COLUMNS',
    'COLUMN_DTYPES',

    # UI
    'CHART_TYPES',
    'TIME_RANGES',
    'EXPORT_FORMATS',

    # Messages
    'ERROR_MESSAGES',
    'SUCCESS_MESSAGES',

    # Corporate Actions
    'CIRCUIT_LIMIT_PERCENT',
    'CORPORATE_ACTION_RATIOS',
    'CORPORATE_ACTIONS_FILENAME',
    'CA_DETECTION_THRESHOLD',
    'CA_HIGH_CONFIDENCE_THRESHOLD',
    'CA_MEDIUM_CONFIDENCE_THRESHOLD',

    'HDF5_STORAGE_CHUNKS',
    'CHUNK_SIZES'  # Deprecated alias
]
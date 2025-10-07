# config/__init__.py

"""
Configuration package with automatic hardware adaptation
"""

from .settings import config, AppConfig
from .constants import (
    # Enums
    Exchange,
    Interval,
    InstrumentType,
    Segment,

    # Validation limits
    MIN_PRICE,
    MAX_PRICE,
    MIN_VOLUME,
    MAX_VOLUME,
    MIN_DATE,
    MAX_DATE,

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

    CHUNK_SIZES
)
from .optimizer import optimizer, get_system_info, get_detailed_system_info

__all__ = [
    # Core config
    'config',
    'AppConfig',

    # Validation
    'MIN_PRICE',
    'MAX_PRICE',
    'MIN_VOLUME',
    'MAX_VOLUME',
    'MIN_DATE',
    'MAX_DATE',

    # Optimizer
    'optimizer',
    'get_system_info',
    'get_detailed_system_info',

    # Enums
    'Exchange',
    'Interval',
    'InstrumentType',
    'Segment',

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

    'CHUNK_SIZES'
]
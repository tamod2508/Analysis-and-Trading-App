"""
Configuration package with automatic hardware adaptation
"""

from .settings import config, AppConfig
from .constants import (
    Exchange,
    Interval,
    InstrumentType,
    HDF5_DATASETS,
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    COLUMN_DTYPES,
    CHART_TYPES,
    TIME_RANGES,
    EXPORT_FORMATS,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    API_LIMITS,
)
from .optimizer import optimizer, get_system_info, get_detailed_system_info

__all__ = [
    # Core config
    'config',
    'AppConfig',
    
    # Optimizer and system info
    'optimizer',
    'get_system_info',
    'get_detailed_system_info',
    
    # Enums
    'Exchange',
    'Interval',
    'InstrumentType',
    
    # Constants
    'HDF5_DATASETS',
    'REQUIRED_COLUMNS',
    'OPTIONAL_COLUMNS',
    'COLUMN_DTYPES',
    'CHART_TYPES',
    'TIME_RANGES',
    'EXPORT_FORMATS',
    'ERROR_MESSAGES',
    'SUCCESS_MESSAGES',
    'API_LIMITS',
]
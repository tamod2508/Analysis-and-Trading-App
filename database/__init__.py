"""
Database package - HDF5 storage and corporate action handling
"""

from .hdf5_manager import HDF5Manager, MultiSegmentManager
from .schema import (
    EquityOHLCVSchema,
    InstrumentSchema,
    HDF5Structure,
    DatasetAttributes,
    ValidationRules,
    create_empty_ohlcv_array,
    dict_to_ohlcv_array,
    ohlcv_array_to_dict,
)
from .data_validator import DataValidator
from .corporate_action_detector import CorporateActionDetector, detect_and_flag_actions
from .data_adjuster import DataAdjuster, adjust_symbol, check_symbol_consistency

__all__ = [
    # HDF5 Management
    'HDF5Manager',
    'MultiSegmentManager',

    # Schema and Validation
    'EquityOHLCVSchema',
    'InstrumentSchema',
    'HDF5Structure',
    'DatasetAttributes',
    'ValidationRules',
    'create_empty_ohlcv_array',
    'dict_to_ohlcv_array',
    'ohlcv_array_to_dict',
    'DataValidator',

    # Corporate Actions
    'CorporateActionDetector',
    'detect_and_flag_actions',
    'DataAdjuster',
    'adjust_symbol',
    'check_symbol_consistency',
]

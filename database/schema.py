"""
HDF5 Database Schema Definition

Note: Validation logic has been moved to validators.py for better separation of concerns.
This file now contains only schema definitions, data structures, and conversion functions.
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import pytz
from config.constants import (
    Interval,
    Exchange,
)

@dataclass
class EquityOHLCVSchema:
    """
    Schema for Equity OHLCV (candlestick) data
    Used for: Stocks, ETFs, Indices
    """

    # Column definitions with NumPy dtypes
    DTYPE = np.dtype([
        ('timestamp', 'int64'),  # Unix timestamp
        ('open', 'float32'),
        ('high', 'float32'),
        ('low', 'float32'),
        ('close', 'float32'),
        ('volume', 'int64'),
    ])

    REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

@dataclass
class OptionsOHLCVSchema:
    """
    Schema for Options/Futures OHLCV data
    Used for: Options (CE/PE), Futures (FUT)

    Additional field: Open Interest (OI)

    Note: While this schema includes 'oi' field, OI data may not always be
    available from the data source. The validation layer will issue warnings
    if OI is missing but will not fail validation. Missing OI values default to 0.
    """

    # Column definitions with NumPy dtypes
    DTYPE = np.dtype([
        ('timestamp', 'int64'),  # Unix timestamp
        ('open', 'float32'),
        ('high', 'float32'),
        ('low', 'float32'),
        ('close', 'float32'),
        ('volume', 'int64'),
        ('oi', 'int64'),  # Open Interest - key metric for derivatives (may be 0 if unavailable)
    ])

    # Core required columns (oi is in the dtype but not strictly required in source data)
    REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    OPTIONAL_COLUMNS = ['oi']  # Common for derivatives but may not always be available

@dataclass
class InstrumentSchema:
    """
    Schema for equity/index instrument metadata
    """

    DTYPE = np.dtype([
        ('instrument_token', 'int64'),
        ('exchange_token', 'int64'),
        ('tradingsymbol', 'U50'),
        ('name', 'U100'),
        ('last_price', 'float32'),
        ('tick_size', 'float32'),
        ('instrument_type', 'U10'),
        ('segment', 'U10'),
        ('exchange', 'U10'),
    ])

class HDF5Structure:
    """
    Defines the hierarchical structure of HDF5 databases

    Database files by segment:
    - EQUITY.h5: NSE + BSE stocks
    - DERIVATIVES.h5: NFO + BFO options/futures
    - COMMODITY.h5: MCX commodities (Gold, Silver, Crude, etc.)
    - CURRENCY.h5: CDS currency derivatives (USDINR, EURINR, etc.)

    Structure (same for all):
    /
    ├── instruments/
    │   ├── NSE/              (NSE instrument metadata)
    │   ├── BSE/              (BSE instrument metadata)
    │   ├── NFO/              (NFO instrument metadata - F&O)
    │   ├── BFO/              (BFO instrument metadata - BSE F&O)
    │   ├── MCX/              (MCX instrument metadata - Commodities)
    │   └── CDS/              (CDS instrument metadata - Currency)
    │
    └── data/
        ├── NSE/              (NSE equity data)
        │   └── {symbol}/
        │       ├── minute/
        │       ├── 5minute/
        │       ├── 15minute/
        │       ├── 60minute/
        │       └── day/
        ├── BSE/              (BSE equity data)
        │   └── {symbol}/
        │       └── day/
        ├── NFO/              (NFO derivatives data)
        │   └── {symbol}/     (e.g., NIFTY25OCT24950CE)
        │       ├── minute/
        │       ├── 5minute/
        │       ├── 15minute/
        │       ├── 60minute/
        │       └── day/
        ├── BFO/              (BFO derivatives data)
        │   └── {symbol}/
        │       └── day/
        ├── MCX/              (MCX commodity data)
        │   └── {symbol}/     (e.g., GOLDM25OCTFUT, CRUDEOIL25NOVFUT)
        │       ├── minute/
        │       ├── 5minute/
        │       ├── 15minute/
        │       ├── 60minute/
        │       └── day/
        └── CDS/              (CDS currency data)
            └── {symbol}/     (e.g., USDINR25OCTFUT)
                ├── minute/
                ├── 5minute/
                ├── 15minute/
                ├── 60minute/
                └── day/

    Storage Strategy:
    EQUITY:
    - Dual-listed stocks: Store from NSE only (higher liquidity)
    - BSE-only stocks: Store from BSE
    - Schema: EquityOHLCVSchema (no OI)

    DERIVATIVES:
    - Options/Futures: Store from respective exchange (NFO, BFO)
    - Schema: OptionsOHLCVSchema (includes OI)
    - Symbol naming: NIFTY25OCT24950CE, BANKNIFTY25NOV51500PE

    COMMODITY:
    - Commodity futures: Store from MCX
    - Schema: OptionsOHLCVSchema (includes OI)
    - Symbol naming: GOLDM25OCTFUT, CRUDEOIL25NOVFUT, SILVER25DECFUT
    - Commodities: Gold, Silver, Crude Oil, Natural Gas, Copper, etc.

    CURRENCY:
    - Currency futures: Store from CDS (Currency Derivatives Segment)
    - Schema: OptionsOHLCVSchema (includes OI)
    - Symbol naming: USDINR25OCTFUT, EURINR25NOVFUT
    - Pairs: USDINR, EURINR, GBPINR, JPYINR

    Examples:
        EQUITY.h5:
            /instruments/NSE/
            /data/NSE/RELIANCE/day
            /data/BSE/BSE_ONLY_STOCK/day

        DERIVATIVES.h5:
            /instruments/NFO/
            /data/NFO/NIFTY25OCT24950CE/minute
            /data/NFO/BANKNIFTY25NOV51500PE/day

        COMMODITY.h5:
            /instruments/MCX/
            /data/MCX/GOLDM25OCTFUT/minute
            /data/MCX/CRUDEOIL25NOVFUT/day

        CURRENCY.h5:
            /instruments/CDS/
            /data/CDS/USDINR25OCTFUT/minute
            /data/CDS/EURINR25NOVFUT/day
    """

    # Root groups
    ROOT_GROUPS = [
        '/instruments',
        '/data',
        ]


    @staticmethod
    def get_instrument_path(exchange: str) -> str:
        """Get path for instrument metadata"""
        return f'/instruments/{exchange.upper()}'

    @staticmethod
    def get_data_path(exchange: str, symbol: str, interval: str) -> str:
        """
        Get path for historical OHLCV data

        Args:
            exchange: NSE, BSE
            symbol: RELIANCE, TCS, etc.
            interval: 15minute, 60minute, day

        Returns:
            Path like: /data/NSE/RELIANCE/15minute
        """
        exchange = exchange.upper()
        # Clean symbol name
        symbol = symbol.upper().replace('&', '_').replace('-', '_').replace(' ', '_')
        return f'/data/{exchange}/{symbol}/{interval}'

    @staticmethod
    def parse_data_path(path: str) -> Tuple[str, str, str]:
        """
        Parse a historical data path

        Args:
            path: /historical/NSE/RELIANCE/15minute

        Returns:
            (exchange, symbol, interval)
        """
        parts = path.strip('/').split('/')
        if len(parts) >= 4 and parts[0] == 'data':
            return parts[1], parts[2], parts[3]
        raise ValueError(f"Invalid data path: {path}")

class DatasetAttributes:
    """Standard attributes for HDF5 datasets"""

    @staticmethod
    def ohlcv_attributes(
        exchange: str,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        row_count: int,
    ) -> Dict:

        return {
            # Date range
            'start_date': start_date,
            'end_date': end_date,

            # Data quality (CRITICAL for validation)
            'row_count': row_count,

            # Freshness (CRITICAL for live trading)
            'updated_at': datetime.now().isoformat(),

            # Provenance (IMPORTANT for audit)
            'source': 'kite_connect_api',
            'api_version': 'v3',

            # Future-proofing (IMPORTANT for migrations)
            'schema_version': '1.0',
        }

    @staticmethod
    def instrument_attributes(exchange: str, count: int) -> Dict:
        """Attributes for instrument datasets"""
        return {
            'instrument_count': count,
            'updated_at': datetime.now().isoformat(),
            'schema_version': '1.0',
        }

def create_empty_ohlcv_array(size: int = 0) -> np.ndarray:
    """Create an empty equity OHLCV array with correct dtype"""
    return np.zeros(size, dtype=EquityOHLCVSchema.DTYPE)


def create_empty_options_array(size: int = 0) -> np.ndarray:
    """Create an empty options/derivatives OHLCV array with correct dtype (includes OI)"""
    return np.zeros(size, dtype=OptionsOHLCVSchema.DTYPE)


def create_empty_instrument_array(size: int = 0) -> np.ndarray:
    """Create an empty instrument array with correct dtype"""
    return np.zeros(size, dtype=InstrumentSchema.DTYPE)


def dict_to_ohlcv_array(data: List[Dict]) -> np.ndarray:
    """
    Convert list of dicts (from Kite API) to NumPy structured array

    Expected dict format from Kite API:
    {
        'timestamp': int64,
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': int,
    }
    """
    size = len(data)
    arr = create_empty_ohlcv_array(size)

    for i, row in enumerate(data):
        # Handle timezone-aware datetime
        date_val = row['date']
        if isinstance(date_val, pd.Timestamp):
            # Convert to UTC then to Unix timestamp
            if date_val.tz is not None:
                date_val = date_val.tz_convert('UTC')
            timestamp = int(date_val.timestamp())
        elif hasattr(date_val, 'timestamp'):
            # Python datetime object
            timestamp = int(date_val.timestamp())
        else:
            # Already a timestamp or string
            timestamp = int(pd.Timestamp(date_val).timestamp())

        arr[i]['timestamp'] = timestamp
        arr[i]['open'] = row['open']
        arr[i]['high'] = row['high']
        arr[i]['low'] = row['low']
        arr[i]['close'] = row['close']
        arr[i]['volume'] = row['volume']

    return arr


def ohlcv_array_to_dict(data: np.ndarray) -> List[Dict]:
    """Convert NumPy structured array back to list of dicts"""
    result = []

    for row in data:
        result.append({
            'date': row['timestamp'].astype('datetime64[s]').item(),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume']),
        })

    return result


def dict_to_options_array(data: List[Dict]) -> np.ndarray:
    """
    Convert list of dicts (from Kite API) to NumPy structured array for options/derivatives

    Expected dict format from Kite API:
    {
        'timestamp': int64,
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': int,
        'oi': int,  # Open Interest (optional - defaults to 0 if missing)
    }

    Note: 'oi' (Open Interest) is optional. If not present in input data,
    it will be set to 0. This handles cases where OI data is unavailable.
    """
    size = len(data)
    arr = create_empty_options_array(size)

    for i, row in enumerate(data):
        # Handle timezone-aware datetime
        date_val = row['date']
        if isinstance(date_val, pd.Timestamp):
            # Convert to UTC then to Unix timestamp
            if date_val.tz is not None:
                date_val = date_val.tz_convert('UTC')
            timestamp = int(date_val.timestamp())
        elif hasattr(date_val, 'timestamp'):
            # Python datetime object
            timestamp = int(date_val.timestamp())
        else:
            # Already a timestamp or string
            timestamp = int(pd.Timestamp(date_val).timestamp())

        arr[i]['timestamp'] = timestamp
        arr[i]['open'] = row['open']
        arr[i]['high'] = row['high']
        arr[i]['low'] = row['low']
        arr[i]['close'] = row['close']
        arr[i]['volume'] = row['volume']
        arr[i]['oi'] = row.get('oi', 0)  # Default to 0 if missing

    return arr


def options_array_to_dict(data: np.ndarray) -> List[Dict]:
    """Convert options/derivatives NumPy structured array back to list of dicts"""
    result = []

    for row in data:
        result.append({
            'date': row['timestamp'].astype('datetime64[s]').item(),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume']),
            'oi': int(row['oi']),
        })

    return result

# SCHEMA VERSION

SCHEMA_VERSION = '1.0'
COMPATIBLE_VERSIONS = ['1.0']

def is_schema_compatible(version: str) -> bool:
    """Check if schema version is compatible"""
    return version in COMPATIBLE_VERSIONS


# Backward compatibility: Import validation classes from validators.py
# This allows existing code to continue using schema.ValidationRules
from .validators import ValidationRules, OptionsValidationRules

__all__ = [
    'EquityOHLCVSchema',
    'OptionsOHLCVSchema',
    'InstrumentSchema',
    'HDF5Structure',
    'DatasetAttributes',
    'ValidationRules',  # Re-exported for backward compatibility
    'OptionsValidationRules',  # Re-exported for backward compatibility
    'create_empty_ohlcv_array',
    'create_empty_options_array',
    'create_empty_instrument_array',
    'dict_to_ohlcv_array',
    'ohlcv_array_to_dict',
    'dict_to_options_array',
    'options_array_to_dict',
    'SCHEMA_VERSION',
    'COMPATIBLE_VERSIONS',
    'is_schema_compatible',
]
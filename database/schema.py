"""
HDF5 Database Schema Definition
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
    MIN_PRICE,
    MAX_PRICE,
    MIN_VOLUME,
    MAX_VOLUME,
    MIN_DATE,
    MAX_DATE
)

@dataclass
class EquityOHLCVSchema:
    """
    Schema for OHLCV (candlestick) data
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
    Defines the hierarchical structure of the equity HDF5 database

    Database file: EQUITY.h5 (single file for NSE + BSE equity)

    Structure:
    /
    ├── instruments/
    │   ├── NSE/              (NSE instrument metadata)
    │   └── BSE/              (BSE instrument metadata)
    │
    └── data/
        ├── NSE/              (NSE equity data - primary)
        │   └── {symbol}/
        │       ├── 5minute/
        │       ├── 15minute/
        │       ├── 60minute/
        │       └── day/
        └── BSE/              (BSE equity data - fallback for BSE-only stocks)
            └── {symbol}/
                └── day/

    Storage Strategy:
    - Dual-listed stocks (RELIANCE, TCS): Store from NSE only (higher liquidity)
    - BSE-only stocks: Store from BSE
    - Exchange kept in path for data provenance

    Examples:
        /instruments/NSE/RELIANCE
        /data/NSE/RELIANCE/day
        /data/NSE/RELIANCE/5minute
        /data/BSE/BSE_ONLY_STOCK/day
    """

    # Root groups
    ROOT_GROUPS = [
        '/instruments',
        '/data',
        ]


    EXCHANGES = ['NSE', 'BSE', "NFO"]

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

class ValidationRules:
    """Data validation rules for equity OHLCV data"""

    @classmethod
    def validate_ohlcv_row(cls, row: np.ndarray) -> Tuple[bool, List[str]]:
        """Validate a single OHLCV row"""
        errors = []

        # OHLC relationship check
        if not (row['low'] <= row['open'] <= row['high']):
            errors.append("Invalid OHLC: low <= open <= high violated")

        if not (row['low'] <= row['close'] <= row['high']):
            errors.append("Invalid OHLC: low <= close <= high violated")

        # Price range check
        for field in ['open', 'high', 'low', 'close']:
            price = row[field]
            if not (MIN_PRICE <= price <= MAX_PRICE):  # ← Use imported constant
                errors.append(f"{field} price out of range: {price}")

        # Volume check
        if not (MIN_VOLUME <= row['volume'] <= MAX_VOLUME):  # ← Use imported constant
            errors.append(f"Volume out of range: {row['volume']}")

        # Date check
        if not (MIN_DATE <= row['timestamp'] <= MAX_DATE):  # ← Use imported constant
            errors.append(f"Timestamp out of range: {row['timestamp']}")

        return len(errors) == 0, errors

    @classmethod
    def validate_ohlcv_array(cls, data: np.ndarray) -> Tuple[bool, Dict]:
        """
        Validate an array of OHLCV data

        Returns:
            (is_valid, stats_dict)
        """
        total_rows = len(data)
        invalid_rows = []

        for i, row in enumerate(data):
            is_valid, errors = cls.validate_ohlcv_row(row)
            if not is_valid:
                invalid_rows.append((i, errors))
                if len(invalid_rows) >= 10:  # Limit error collection
                    break

        stats = {
            'total_rows': total_rows,
            'valid_rows': total_rows - len(invalid_rows),
            'invalid_rows': len(invalid_rows),
            'invalid_details': invalid_rows,
        }

        return len(invalid_rows) == 0, stats


def create_empty_ohlcv_array(size: int = 0) -> np.ndarray:
    """Create an empty equity OHLCV array with correct dtype"""
    return np.zeros(size, dtype=EquityOHLCVSchema.DTYPE)


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

# SCHEMA VERSION

SCHEMA_VERSION = '1.0'
COMPATIBLE_VERSIONS = ['1.0']

def is_schema_compatible(version: str) -> bool:
    """Check if schema version is compatible"""
    return version in COMPATIBLE_VERSIONS
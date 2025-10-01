"""
HDF5 Database Schema Definition - EQUITY/INDEX ONLY
Optimized for multi-timeframe equity and index data storage
(Options schemas in separate module: database/options_schema.py)
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# INTERVALS ENUM (matches Kite Connect API)
# ============================================================================

class Interval(str, Enum):
    """Candlestick intervals"""
    MINUTE = "minute"
    MINUTE_3 = "3minute"
    MINUTE_5 = "5minute"
    MINUTE_10 = "10minute"
    MINUTE_15 = "15minute"
    MINUTE_30 = "30minute"
    MINUTE_60 = "60minute"
    DAY = "day"


# ============================================================================
# PRIMARY INTERVALS CONFIGURATION
# ============================================================================

# Intervals to fetch by default for equity/index
PRIMARY_INTERVALS = [
    Interval.DAY,           # Long-term analysis
    Interval.MINUTE_60,     # Hourly - swing trading
    Interval.MINUTE_15,     # 15-min - intraday analysis
]

# Per-request limits for each interval (from Kite API)
INTERVAL_FETCH_LIMITS = {
    Interval.MINUTE: 60,        # 60 days per request
    Interval.MINUTE_3: 100,     # 100 days per request
    Interval.MINUTE_5: 100,     # 100 days per request
    Interval.MINUTE_10: 100,    # 100 days per request
    Interval.MINUTE_15: 200,    # 200 days per request
    Interval.MINUTE_30: 200,    # 200 days per request
    Interval.MINUTE_60: 400,    # 400 days per request
    Interval.DAY: 2000,         # 2000 days per request
}

# Historical data availability dates
HISTORICAL_DATA_START = {
    'NSE_intraday': '2015-02-02',   # NSE intraday data starts here
    'BSE_intraday': '2016-03-18',   # BSE intraday data starts here
    'daily': '2005-01-01',          # Daily data goes back much further
}


# ============================================================================
# EQUITY OHLCV SCHEMA (Clean - no options fields)
# ============================================================================

@dataclass
class EquityOHLCVSchema:
    """
    Schema for equity/index OHLCV (candlestick) data
    Pure equity schema - NO options-specific fields
    """
    
    # Column definitions with NumPy dtypes
    DTYPE = np.dtype([
        ('timestamp', 'datetime64[s]'),  # Unix timestamp
        ('open', 'float32'),              # Opening price
        ('high', 'float32'),              # High price
        ('low', 'float32'),               # Low price
        ('close', 'float32'),             # Closing price
        ('volume', 'int64'),              # Trading volume
    ])
    
    REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    @staticmethod
    def validate_ohlc(row: np.ndarray) -> bool:
        """Validate OHLC relationships"""
        return (
            row['high'] >= row['open'] and
            row['high'] >= row['close'] and
            row['high'] >= row['low'] and
            row['low'] <= row['open'] and
            row['low'] <= row['close'] and
            row['volume'] >= 0
        )


@dataclass
class InstrumentSchema:
    """
    Schema for equity/index instrument metadata
    Clean separation - futures/options metadata in options_schema.py
    """
    
    DTYPE = np.dtype([
        ('instrument_token', 'int64'),
        ('exchange_token', 'int64'),
        ('tradingsymbol', 'U50'),      # Trading symbol
        ('name', 'U100'),               # Company/Index name
        ('last_price', 'float32'),      # Last traded price
        ('tick_size', 'float32'),       # Minimum price movement
        ('lot_size', 'int32'),          # Lot size
        ('instrument_type', 'U10'),     # EQ (Equity only for this schema)
        ('segment', 'U10'),             # NSE, BSE
        ('exchange', 'U10'),            # Exchange code
    ])


# ============================================================================
# HDF5 HIERARCHICAL STRUCTURE (Equity/Index)
# ============================================================================

class HDF5Structure:
    """
    Defines the hierarchical structure of the equity HDF5 database
    
    Multi-timeframe structure:
    /
    ├── metadata/
    │   └── (stored as file attributes, not datasets)
    ├── instruments/
    │   ├── NSE/        (equity instruments only)
    │   └── BSE/
    └── historical/
        └── {exchange}/
            └── {symbol}/
                ├── 15minute/  (dataset with start_date, end_date, row_count, updated_at attributes)
                ├── 60minute/  (dataset with start_date, end_date, row_count, updated_at attributes)
                └── day/       (dataset with start_date, end_date, row_count, updated_at attributes)
    
    Metadata stored as HDF5 attributes (not separate datasets):
    - File level: db_version, created_at, last_updated, format
    - Dataset level: start_date, end_date, row_count, updated_at, source, api_version, schema_version
    """
    
    # Root groups
    ROOT_GROUPS = [
        '/instruments',
        '/historical',
    ]
    
    # Exchange groups (equity only)
    EXCHANGES = ['NSE', 'BSE']
    
    @staticmethod
    def get_instrument_path(exchange: str) -> str:
        """Get path for instrument metadata"""
        return f'/instruments/{exchange.upper()}'
    
    @staticmethod
    def get_historical_path(exchange: str, symbol: str, interval: str) -> str:
        """
        Get path for historical OHLCV data
        
        Args:
            exchange: NSE, BSE
            symbol: RELIANCE, TCS, etc.
            interval: 15minute, 60minute, day
        
        Returns:
            Path like: /historical/NSE/RELIANCE/15minute
        """
        exchange = exchange.upper()
        # Clean symbol name
        symbol = symbol.upper().replace('&', '_').replace('-', '_').replace(' ', '_')
        return f'/historical/{exchange}/{symbol}/{interval}'
    
    @staticmethod
    def parse_historical_path(path: str) -> Tuple[str, str, str]:
        """
        Parse a historical data path
        
        Args:
            path: /historical/NSE/RELIANCE/15minute
        
        Returns:
            (exchange, symbol, interval)
        """
        parts = path.strip('/').split('/')
        if len(parts) >= 4 and parts[0] == 'historical':
            return parts[1], parts[2], parts[3]
        raise ValueError(f"Invalid historical path: {path}")
    
    @staticmethod
    def get_metadata_path(key: str) -> str:
        """Get path for metadata entry"""
        return f'/metadata/{key}'


# ============================================================================
# DATASET ATTRIBUTES
# ============================================================================

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
        """Essential metadata for production trading system"""
        return {
            # Date range (CRITICAL for trading)
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

# ============================================================================
# COMPRESSION SETTINGS (M1 Optimized)
# ============================================================================

@dataclass
class CompressionSettings:
    """HDF5 compression configuration optimized for M1"""
    
    # Compression algorithm
    ALGORITHM: str = 'gzip'
    LEVEL: int = 4  # Sweet spot for M1 (balance speed/compression)
    SHUFFLE: bool = True  # Improves compression ratio
    
    # Chunk sizes optimized by interval
    CHUNK_SIZES = {
        Interval.DAY: (5000,),       # Large chunks for daily
        Interval.MINUTE_60: (2000,),  # Medium for hourly
        Interval.MINUTE_15: (1000,),  # Smaller for 15-min
        Interval.MINUTE_5: (1000,),   # Smaller for 5-min
        Interval.MINUTE: (500,),      # Smallest for minute
    }
    
    @classmethod
    def get_settings(cls, interval: str) -> Dict:
        """
        Get optimal compression settings for interval
        
        Args:
            interval: Data interval (15minute, 60minute, day)
        
        Returns:
            Dict with compression, chunks, shuffle settings
        """
        # Convert string to Interval enum if needed
        if isinstance(interval, str):
            try:
                interval_enum = Interval(interval)
            except ValueError:
                interval_enum = Interval.DAY  # Default
        else:
            interval_enum = interval
        
        # Get chunk size for this interval
        chunks = cls.CHUNK_SIZES.get(interval_enum, (1000,))
        
        return {
            'compression': cls.ALGORITHM,
            'compression_opts': cls.LEVEL,
            'shuffle': cls.SHUFFLE,
            'chunks': chunks,
        }


# ============================================================================
# VALIDATION RULES
# ============================================================================

class ValidationRules:
    """Data validation rules for equity OHLCV data"""
    
    # Price validation
    MIN_PRICE = 0.01
    MAX_PRICE = 1_000_000.0
    
    # Volume validation
    MIN_VOLUME = 0
    MAX_VOLUME = 10_000_000_000
    
    # Date validation
    MIN_DATE = np.datetime64('2000-01-01')
    MAX_DATE = np.datetime64('2099-12-31')
    
    @classmethod
    def validate_ohlcv_row(cls, row: np.ndarray) -> Tuple[bool, List[str]]:
        """
        Validate a single OHLCV row
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # OHLC relationship check
        if not (row['low'] <= row['open'] <= row['high']):
            errors.append("Invalid OHLC: low <= open <= high violated")
        
        if not (row['low'] <= row['close'] <= row['high']):
            errors.append("Invalid OHLC: low <= close <= high violated")
        
        # Price range check
        for field in ['open', 'high', 'low', 'close']:
            price = row[field]
            if not (cls.MIN_PRICE <= price <= cls.MAX_PRICE):
                errors.append(f"{field} price out of range: {price}")
        
        # Volume check
        if not (cls.MIN_VOLUME <= row['volume'] <= cls.MAX_VOLUME):
            errors.append(f"Volume out of range: {row['volume']}")
        
        # Date check
        if not (cls.MIN_DATE <= row['timestamp'] <= cls.MAX_DATE):
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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
        'date': datetime,
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
        arr[i]['timestamp'] = np.datetime64(row['date'])
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


# ============================================================================
# MULTI-TIMEFRAME HELPERS
# ============================================================================

def get_expected_candle_count(interval: Interval, days: int) -> int:
    """
    Calculate expected number of candles for a time period
    
    Args:
        interval: Candle interval
        days: Number of trading days
    
    Returns:
        Expected candle count
    """
    # Approximate trading minutes per day: 375 (9:15 AM - 3:30 PM)
    candles_per_day = {
        Interval.DAY: 1,
        Interval.MINUTE_60: 6,      # ~375 / 60
        Interval.MINUTE_30: 12,     # ~375 / 30
        Interval.MINUTE_15: 25,     # ~375 / 15
        Interval.MINUTE_10: 37,     # ~375 / 10
        Interval.MINUTE_5: 75,      # ~375 / 5
        Interval.MINUTE_3: 125,     # ~375 / 3
        Interval.MINUTE: 375,       # All minutes
    }
    
    return candles_per_day.get(interval, 1) * days


# ============================================================================
# SCHEMA VERSION
# ============================================================================

SCHEMA_VERSION = '1.0'
COMPATIBLE_VERSIONS = ['1.0']

def is_schema_compatible(version: str) -> bool:
    """Check if schema version is compatible"""
    return version in COMPATIBLE_VERSIONS
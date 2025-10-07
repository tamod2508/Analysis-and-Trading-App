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
from config.constants import Interval, Exchange

PRIMARY_INTERVALS = [
    Interval.DAY,         
    Interval.MINUTE_60,   
    Interval.MINUTE_15,     
]

# Per-request limits for each interval (from Kite API)
INTERVAL_FETCH_LIMITS = {
    Interval.MINUTE: 60,       
    Interval.MINUTE_3: 100,     
    Interval.MINUTE_5: 100,     
    Interval.MINUTE_10: 100,   
    Interval.MINUTE_15: 200,    
    Interval.MINUTE_30: 200,    
    Interval.MINUTE_60: 400,   
    Interval.DAY: 2000,        
}

# Historical data availability dates
IST = pytz.timezone('Asia/Kolkata')

HISTORICAL_DATA_START = {
    'NSE_intraday': pd.Timestamp('2015-02-02', tz=IST),
    'BSE_intraday': pd.Timestamp('2016-03-18', tz=IST),
    'daily': pd.Timestamp('2005-01-01', tz=IST),
}


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
    
    Multi-timeframe structure:
    /
    ├── metadata/
    │   └── (stored as file attributes, not datasets)
    ├── instruments/
    │   ├── NSE/        (equity instruments only)
    │   └── BSE/
    └── data/
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
        '/data',
    ]
    
    EXCHANGES = ['NSE', 'BSE']
    
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

@dataclass
class CompressionSettings:
    """HDF5 compression configuration optimized for M1"""
    
    # Compression algorithm
    ALGORITHM: str = 'gzip'
    LEVEL: int = 7 
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
    def get_settings(cls, interval: str, data_size: int = None) -> Dict:
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
        default_chunks = cls.CHUNK_SIZES.get(interval_enum, (1000,))
        
        if data_size is not None:
            chunk_size = min(default_chunks[0], max(10, data_size))
            chunks = (chunk_size,)
        else:
            chunks = default_chunks

        return {
            'compression': cls.ALGORITHM,
            'compression_opts': cls.LEVEL,
            'shuffle': cls.SHUFFLE,
            'chunks': chunks
        }


class ValidationRules:
    """Data validation rules for equity OHLCV data"""
    
    # Price validation
    MIN_PRICE = 0.01
    MAX_PRICE = 1_000_000.0
    
    # Volume validation
    MIN_VOLUME = 0
    MAX_VOLUME = 10_000_000_000
    
    # Date validation
    MIN_DATE = int(pd.Timestamp('2000-01-01').timestamp())
    MAX_DATE = int(pd.Timestamp('2099-12-31').timestamp())
    
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
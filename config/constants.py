"""
Constants and enumerations
"""

from enum import Enum
from dataclasses import dataclass
import pytz
import pandas as pd

class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    CDS = "CDS"
    BFO = "BFO"
    MCX = "MCX"

class Interval(str, Enum):
    MINUTE = "minute"
    MINUTE_3 = "3minute"
    MINUTE_5 = "5minute"
    MINUTE_10 = "10minute"
    MINUTE_15 = "15minute"
    MINUTE_30 = "30minute"
    MINUTE_60 = "60minute"
    DAY = "day"

class InstrumentType(str, Enum):  # ← ADD THIS (it's exported but not defined!)
    EQ = "EQ"   # Equity
    FUT = "FUT" # Futures
    CE = "CE"   # Call Option
    PE = "PE"   # Put Option

class Segment(str, Enum):
    EQUITY = "EQUITY"              # Equity stocks (NSE, BSE)
    DERIVATIVES = "DERIVATIVES"    # F&O (NFO, BFO, CDS)
    COMMODITY = "COMMODITY"        # Commodities (MCX)
    CURRENCY = "CURRENCY"          # Currency derivatives (CDS)

class CompressionType(str, Enum):
    """HDF5 compression algorithms"""
    BLOSC_LZ4 = "blosc:lz4"        # Fast compression (recommended)
    BLOSC_ZSTD = "blosc:zstd"      # Better compression ratio
    BLOSC_LZ4HC = "blosc:lz4hc"    # High compression LZ4
    GZIP = "gzip"                  # Standard gzip (slower but compatible)
    LZF = "lzf"                    # Fast, low compression
    NONE = "none"                  # No compression

# Exchange to Segment mapping (single source of truth)
EXCHANGE_TO_SEGMENT = {
    Exchange.NSE: Segment.EQUITY,
    Exchange.BSE: Segment.EQUITY,
    Exchange.NFO: Segment.DERIVATIVES,
    Exchange.BFO: Segment.DERIVATIVES,
    Exchange.MCX: Segment.COMMODITY,
    Exchange.CDS: Segment.CURRENCY,
}

# Reverse mapping: Segment to Exchanges
SEGMENT_TO_EXCHANGES = {
    Segment.EQUITY: [Exchange.NSE, Exchange.BSE],
    Segment.DERIVATIVES: [Exchange.NFO, Exchange.BFO],
    Segment.COMMODITY: [Exchange.MCX],
    Segment.CURRENCY: [Exchange.CDS],
}

# Validation limits dataclass
@dataclass
class ValidationLimits:
    """Validation limits for price and volume data"""
    min_price: float
    max_price: float
    min_volume: int
    max_volume: int
    allow_zero_prices: bool = False  # For derivatives options that can expire worthless

# Segment-specific validation limits
VALIDATION_LIMITS = {
    Segment.EQUITY: ValidationLimits(
        min_price=0.01,              # Equity must have positive price
        max_price=1_000_000.0,       # ₹10 lakh max (sanity check)
        min_volume=0,
        max_volume=10_000_000_000,   # 10 billion shares max
        allow_zero_prices=False
    ),
    Segment.DERIVATIVES: ValidationLimits(
        min_price=0.00,              # Options can expire worthless (₹0)
        max_price=100_000.0,         # ₹1 lakh max for derivatives
        min_volume=0,
        max_volume=10_000_000_000,
        allow_zero_prices=True       # Allow ₹0 for expired options
    ),
    Segment.COMMODITY: ValidationLimits(
        min_price=0.00,              # Commodities can theoretically hit zero
        max_price=100_000.0,
        min_volume=0,
        max_volume=10_000_000_000,
        allow_zero_prices=True
    ),
    Segment.CURRENCY: ValidationLimits(
        min_price=0.00,              # Currency options can expire worthless
        max_price=100_000.0,
        min_volume=0,
        max_volume=10_000_000_000,
        allow_zero_prices=True
    ),
}

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

PRIMARY_INTERVALS = {
    Segment.EQUITY: [Interval.DAY, Interval.MINUTE_60, Interval.MINUTE_15, Interval.MINUTE_5],
    Segment.DERIVATIVES: [Interval.DAY, Interval.MINUTE_60, Interval.MINUTE_15, Interval.MINUTE_5, Interval.MINUTE],
    Segment.COMMODITY: [Interval.DAY, Interval.MINUTE_60, Interval.MINUTE_15, Interval.MINUTE_5, Interval.MINUTE],
    Segment.CURRENCY: [Interval.DAY, Interval.MINUTE_60, Interval.MINUTE_15, Interval.MINUTE_5, Interval.MINUTE],
}

DERIVED_INTERVALS = {
    Interval.MINUTE_10: Interval.MINUTE_5,   # Resample from 5-min
    Interval.MINUTE_30: Interval.MINUTE_15  # Resample from 15-min
}

# Historical data availability dates
IST = pytz.timezone('Asia/Kolkata')

HISTORICAL_DATA_START = {
    'NSE_intraday': pd.Timestamp('2015-02-02', tz=IST),
    'BSE_intraday': pd.Timestamp('2016-03-18', tz=IST),
    'daily': pd.Timestamp('2005-01-01', tz=IST),
}


HDF5_DATASETS = {
    'INSTRUMENTS': '/instruments',
    'DATA': '/data',
}

# Required columns for historical data
REQUIRED_COLUMNS = [
    'timestamp', 'open', 'high', 'low', 'close', 'volume'
]

# Optional columns
OPTIONAL_COLUMNS = [
    'oi',  # Open Interest (for F&O)
]

# Data type mappings
COLUMN_DTYPES = {
    'timestamp': 'int64',
    'open': 'float32',
    'high': 'float32',
    'low': 'float32',
    'close': 'float32',
    'volume': 'int64',
    'oi': 'int64',
}

# Chart types
CHART_TYPES = [
    "Line",
    "Candlestick",
    "Bar",
    "Area",
    "OHLC"
]

# HDF5 Internal Storage Chunks
# These control how HDF5 stores data internally for optimal compression and I/O.
# Smaller values = better for random access queries
# Larger values = better for sequential reads
HDF5_STORAGE_CHUNKS = {
    Interval.DAY: 5000,        # Daily: large chunks (sequential reads common)
    Interval.MINUTE_60: 2000,  # Hourly: medium chunks
    Interval.MINUTE_15: 1000,  # 15-min: smaller chunks (more queries)
    Interval.MINUTE_5: 1000,   # 5-min: smaller chunks
    Interval.MINUTE: 500,      # Minute: smallest chunks (frequent queries)
}

# DEPRECATED: Use HDF5_STORAGE_CHUNKS instead
CHUNK_SIZES = HDF5_STORAGE_CHUNKS  # Backward compatibility alias

# Time ranges for quick selection
TIME_RANGES = {
    "1 Week": 7,
    "1 Month": 30,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
    "2 Years": 730,
    "5 Years": 1825,
    "10 Years": 3650,
    "All Time": None,
}

# DEPRECATED: Use VALIDATION_LIMITS[segment] instead for segment-specific validation
# Kept for backward compatibility only
MIN_PRICE = 0.01          # Minimum valid price (₹0.01) - EQUITY only
MAX_PRICE = 1_000_000.0   # Maximum valid price (₹10 lakh - sanity check) - EQUITY only
MIN_VOLUME = 0                 # Minimum volume (can be zero)
MAX_VOLUME = 10_000_000_000    # Maximum volume (10 billion shares)

# Date validation limits
MIN_DATE = int(pd.Timestamp('2000-01-01').timestamp())  # Earliest valid date
MAX_DATE = int(pd.Timestamp('2099-12-31').timestamp())  # Latest valid date

# File size limits (for warnings and safety checks)
MAX_HDF5_FILE_SIZE_GB: float = 50.0        # Warn if single HDF5 file exceeds 50GB
MAX_BACKUP_SIZE_GB: float = 100.0          # Warn if total backup size exceeds 100GB
MAX_EXPORT_SIZE_MB: float = 500.0          # Warn if single export file exceeds 500MB
MAX_LOG_FILE_SIZE_MB: float = 100.0        # Maximum size per log file (before rotation)
MAX_TOTAL_DATA_SIZE_GB: float = 200.0      # Warn if total data directory exceeds 200GB

# Export formats
EXPORT_FORMATS = [
    "CSV",
    "Excel",
    "JSON",
    "Parquet"
]

ERROR_MESSAGES = {
    'NO_API_KEY': 'API Key not configured. Please add it to .env file.',
    'NO_API_SECRET': 'API Secret not configured. Please add it to .env file.',
    'INVALID_TOKEN': 'Invalid or expired access token. Please login again.',
    'NO_DATA': 'No data available for the selected parameters.',
    'INVALID_DATE_RANGE': 'Invalid date range. Start date must be before end date.',
    'API_ERROR': 'Error communicating with Kite Connect API.',
    'DATABASE_ERROR': 'Error accessing HDF5 database.',
    'VALIDATION_ERROR': 'Data validation failed.',
}

SUCCESS_MESSAGES = {
    'DATA_FETCHED': 'Historical data fetched successfully!',
    'DATA_SAVED': 'Data saved to database successfully!',
    'BACKUP_CREATED': 'Backup created successfully!',
    'EXPORT_COMPLETE': 'Data exported successfully!',
    'LOGIN_SUCCESS': 'Login successful!',
}

API_LIMITS = {
    'MAX_RECORDS_PER_REQUEST': 1000,
    'MAX_INSTRUMENTS_PER_REQUEST': 100,
    'RATE_LIMIT_PER_SECOND': 3,
    'MAX_HISTORICAL_DAYS': 365 * 2,  # 2 years typically
}

# Corporate Action Constants
CIRCUIT_LIMIT_PERCENT = 20.0  # NSE/BSE daily circuit breaker limit

# Common split/bonus ratios and their expected price changes
CORPORATE_ACTION_RATIOS = {
    0.50: {'ratio': '1:1', 'type': 'bonus', 'description': '1:1 Bonus (50% drop)'},
    0.67: {'ratio': '1:2', 'type': 'bonus', 'description': '1:2 Bonus (33% drop)'},
    0.75: {'ratio': '1:3', 'type': 'bonus', 'description': '1:3 Bonus (25% drop)'},
    0.80: {'ratio': '1:5', 'type': 'split', 'description': '1:5 Split (80% drop)'},
    0.90: {'ratio': '1:10', 'type': 'split', 'description': '1:10 Split (90% drop)'},
}

# Corporate action file settings
CORPORATE_ACTIONS_FILENAME = 'corporate_actions.json'

# Corporate action detection thresholds
CA_DETECTION_THRESHOLD = CIRCUIT_LIMIT_PERCENT / 100.0  # 0.20 (20%)
CA_HIGH_CONFIDENCE_THRESHOLD = 0.05  # Within 5% of known ratio
CA_MEDIUM_CONFIDENCE_THRESHOLD = 0.10  # Within 10% of known ratio
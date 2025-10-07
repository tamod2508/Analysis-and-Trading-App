"""
Constants and enumerations
"""

from enum import Enum
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
    # Equity
    EQUITY = "EQUITY"
    # Future: DERIVATIVES, COMMODITY, CURRENCY

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
    # Future: Segment.DERIVATIVES: [...], etc.
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

CHUNK_SIZES = {
    Interval.DAY: 5000,        # Large chunks for daily
    Interval.MINUTE_60: 2000,  # Medium for hourly
    Interval.MINUTE_15: 1000,  # Smaller for 15-min
    Interval.MINUTE_5: 1000,   # Smaller for 5-min
    Interval.MINUTE: 500,      # Smallest for minute
}

# Time ranges for quick selection
TIME_RANGES = {
    "1 Week": 7,
    "1 Month": 30,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
    "2 Years": 730,
    "5 Years": 1825,
    "10 years": 3650,
    "All Time": None,
}

# Price validation limits
MIN_PRICE = 0.01          # Minimum valid price (₹0.01)
MAX_PRICE = 1_000_000.0   # Maximum valid price (₹10 lakh - sanity check)

# Volume validation limits
MIN_VOLUME = 0                 # Minimum volume (can be zero)
MAX_VOLUME = 10_000_000_000    # Maximum volume (10 billion shares)

# Date validation limits
MIN_DATE = int(pd.Timestamp('2000-01-01').timestamp())  # Earliest valid date
MAX_DATE = int(pd.Timestamp('2099-12-31').timestamp())  # Latest valid date

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
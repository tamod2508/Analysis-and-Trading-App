"""
Constants and enumerations
"""

from enum import Enum

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

class InstrumentType(str, Enum):
    EQ = "EQ"  # Equity
    FUT = "FUT"  # Futures
    CE = "CE"  # Call Option
    PE = "PE"  # Put Option


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
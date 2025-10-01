"""
Constants and enumerations for Kite Connect API
"""

from enum import Enum

# ============================================================================
# KITE CONNECT API CONSTANTS
# ============================================================================

class Exchange(str, Enum):
    """Exchange codes"""
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    CDS = "CDS"
    BFO = "BFO"
    MCX = "MCX"

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

class InstrumentType(str, Enum):
    """Instrument types"""
    EQ = "EQ"  # Equity
    FUT = "FUT"  # Futures
    CE = "CE"  # Call Option
    PE = "PE"  # Put Option

# ============================================================================
# HDF5 DATASET NAMES
# ============================================================================

HDF5_DATASETS = {
    'METADATA': '/metadata',
    'INSTRUMENTS': '/instruments',
    'HISTORICAL_DATA': '/historical_data',
    'OHLC_DATA': '/ohlc',
}

# ============================================================================
# DATA VALIDATION CONSTANTS
# ============================================================================

# Required columns for historical data
REQUIRED_COLUMNS = [
    'date', 'open', 'high', 'low', 'close', 'volume'
]

# Optional columns
OPTIONAL_COLUMNS = [
    'oi',  # Open Interest (for F&O)
]

# Data type mappings
COLUMN_DTYPES = {
    'date': 'datetime64[ns]',
    'open': 'float64',
    'high': 'float64',
    'low': 'float64',
    'close': 'float64',
    'volume': 'int64',
    'oi': 'int64',
}

# ============================================================================
# UI CONSTANTS
# ============================================================================

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
    "All Time": None,
}

# Export formats
EXPORT_FORMATS = [
    "CSV",
    "Excel",
    "JSON",
    "Parquet"
]

# ============================================================================
# ERROR MESSAGES
# ============================================================================

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

# ============================================================================
# SUCCESS MESSAGES
# ============================================================================

SUCCESS_MESSAGES = {
    'DATA_FETCHED': 'Historical data fetched successfully!',
    'DATA_SAVED': 'Data saved to database successfully!',
    'BACKUP_CREATED': 'Backup created successfully!',
    'EXPORT_COMPLETE': 'Data exported successfully!',
    'LOGIN_SUCCESS': 'Login successful!',
}

# ============================================================================
# API LIMITS
# ============================================================================

API_LIMITS = {
    'MAX_RECORDS_PER_REQUEST': 1000,
    'MAX_INSTRUMENTS_PER_REQUEST': 100,
    'RATE_LIMIT_PER_SECOND': 3,
    'MAX_HISTORICAL_DAYS': 365 * 2,  # 2 years typically
}
"""
Shared validation constants for both HDF5 (legacy) and QuestDB (current)

These constants are used by validators in both database implementations.
They define the acceptable ranges for OHLCV data validation.

Usage:
    from database.validation_constants import (
        MIN_PRICE, MAX_PRICE,
        MIN_VOLUME, MAX_VOLUME,
        Circuit, CIRCUIT_LIMIT_PCT
    )
"""

# Re-export from main config
from config import (
    Exchange,
    Segment,
    Interval,
    EXCHANGE_TO_SEGMENT,
    SEGMENT_TO_EXCHANGES,
    VALIDATION_LIMITS,
    IST,
)

# Validation constants (shared by HDF5 and QuestDB)

# Price limits - Equity
MIN_PRICE = 0.01  # Equity minimum (₹0.01)
MAX_PRICE = 1_000_000.0  # Equity maximum (₹10 lakh)

# Price limits - Derivatives
MIN_PRICE_DERIVATIVES = 0.0  # Options can expire worthless
MAX_PRICE_DERIVATIVES = 100_000.0  # ₹1 lakh max

# Volume limits
MIN_VOLUME = 0
MAX_VOLUME = 10_000_000_000  # 10 billion shares

# Open Interest limits (derivatives only)
MIN_OI = 0
MAX_OI = 100_000_000  # 100 million contracts

# Date limits
from datetime import datetime
MIN_DATE = datetime(2000, 1, 1)
MAX_DATE = datetime(2099, 12, 31)

# Circuit breaker limits (Indian markets)
CIRCUIT_LIMIT_PCT = 0.20  # 20% daily circuit limit (NSE/BSE)
CIRCUIT_LIMIT_PERCENT = 20.0  # Alternative format

# Volume spike detection
VOLUME_SPIKE_THRESHOLD = 8  # 8x median volume

# Corporate action detection thresholds
CA_DETECTION_THRESHOLD = 0.20  # Detect when price changes >20%
CA_HIGH_CONFIDENCE_THRESHOLD = 0.02  # Within 2% of known ratio
CA_MEDIUM_CONFIDENCE_THRESHOLD = 0.05  # Within 5% of known ratio

# Corporate action ratios (expected price changes)
CORPORATE_ACTION_RATIOS = {
    0.50: {'ratio': '1:1', 'type': 'bonus', 'description': '1:1 bonus (50% price drop)'},
    0.33: {'ratio': '1:2', 'type': 'bonus', 'description': '1:2 bonus (33% price drop)'},
    0.25: {'ratio': '1:3', 'type': 'bonus', 'description': '1:3 bonus (25% price drop)'},
    0.20: {'ratio': '1:4', 'type': 'bonus', 'description': '1:4 bonus (20% price drop)'},
    0.80: {'ratio': '1:5', 'type': 'split', 'description': '1:5 split (80% price drop)'},
    0.75: {'ratio': '1:4', 'type': 'split', 'description': '1:4 split (75% price drop)'},
    0.67: {'ratio': '1:3', 'type': 'split', 'description': '1:3 split (67% price drop)'},
    0.50: {'ratio': '1:2', 'type': 'split', 'description': '1:2 split (50% price drop)'},
}

# Export list
__all__ = [
    # Enums
    'Exchange',
    'Segment',
    'Interval',
    'EXCHANGE_TO_SEGMENT',
    'SEGMENT_TO_EXCHANGES',

    # Validation limits
    'VALIDATION_LIMITS',
    'MIN_PRICE',
    'MAX_PRICE',
    'MIN_PRICE_DERIVATIVES',
    'MAX_PRICE_DERIVATIVES',
    'MIN_VOLUME',
    'MAX_VOLUME',
    'MIN_OI',
    'MAX_OI',
    'MIN_DATE',
    'MAX_DATE',

    # Circuit limits
    'CIRCUIT_LIMIT_PCT',
    'CIRCUIT_LIMIT_PERCENT',
    'VOLUME_SPIKE_THRESHOLD',

    # Corporate actions
    'CA_DETECTION_THRESHOLD',
    'CA_HIGH_CONFIDENCE_THRESHOLD',
    'CA_MEDIUM_CONFIDENCE_THRESHOLD',
    'CORPORATE_ACTION_RATIOS',

    # Timezone
    'IST',
]

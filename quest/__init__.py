"""
QuestDB Integration for Kite Historical Data

Provides high-performance time-series storage with:
- Designated timestamp columns
- ILP (InfluxDB Line Protocol) for fast writes
- Efficient querying with SYMBOL indexing
- Corporate action tracking
"""

from quest.client import QuestDBClient
from quest.config import (
    CONNECTION_CONFIG,
    TableNames,
    Intervals,
    Exchanges,
    DataSource,
)
from quest.writer import (
    QuestDBWriter,
    QuestDBWriteError,
    write_equity_batch,
    write_derivatives_batch,
)
from quest.data_reader import (
    QuestDBReader,
    QuestDBReadError,
    get_equity_data,
    get_latest_candles,
    get_symbol_stats,
    get_available_symbols,
)

# Optional validator import (if module exists)
try:
    from quest.validator import (
        EquityValidator,
        DerivativesValidator,
        ValidationStatsLogger,
        get_validator_for_table,
    )
    _has_validator = True
except ImportError:
    _has_validator = False
    EquityValidator = None
    DerivativesValidator = None
    ValidationStatsLogger = None
    get_validator_for_table = None

__all__ = [
    'QuestDBClient',
    'CONNECTION_CONFIG',
    'TableNames',
    'Intervals',
    'Exchanges',
    'DataSource',
    'QuestDBWriter',
    'QuestDBWriteError',
    'write_equity_batch',
    'write_derivatives_batch',
    'QuestDBReader',
    'QuestDBReadError',
    'get_equity_data',
    'get_latest_candles',
    'get_symbol_stats',
    'get_available_symbols',
]

# Add validator exports if available
if _has_validator:
    __all__.extend([
        'EquityValidator',
        'DerivativesValidator',
        'ValidationStatsLogger',
        'get_validator_for_table',
    ])

__version__ = '1.0.0'

"""
Financial Data Fetcher - EODHD Integration
Fetch fundamental data from EODHD API for NSE/BSE companies
"""

from .eodhd_client import EODHDClient
from .data_parser import FundamentalsParser
from .storage import FundamentalsWriter, FundamentalsSchema

__all__ = [
    'EODHDClient',
    'FundamentalsParser',
    'FundamentalsWriter',
    'FundamentalsSchema'
]

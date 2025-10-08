"""
Kite Connect API module

Exports:
    - KiteClient: Main API client
    - Exception classes for structured error handling
"""

from .kite_client import (
    KiteClient,
    KiteAPIError,
    KiteRateLimitError,
    KiteServerError,
    KiteAuthenticationError,
    create_client,
    fetch_symbol
)

__all__ = [
    'KiteClient',
    'KiteAPIError',
    'KiteRateLimitError',
    'KiteServerError',
    'KiteAuthenticationError',
    'create_client',
    'fetch_symbol'
]

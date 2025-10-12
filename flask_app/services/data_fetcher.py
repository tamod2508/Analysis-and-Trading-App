"""
Flask Data Fetcher Service
Provides Flask-compatible interface to KiteClient for fetching historical data
"""

import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import is_dataclass, asdict

from api.kite_client import KiteClient, KiteAPIError, KiteAuthenticationError
from config.constants import Exchange, Interval, Segment
from database.hdf5_manager import HDF5Manager
from database.instruments_db import InstrumentsDB
from utils.logger import get_logger

logger = get_logger(__name__, 'fetcher.log')


def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert NumPy types and dataclass objects to Python native types for JSON serialization

    Args:
        obj: Object to convert (can be dict, list, numpy type, dataclass, etc.)

    Returns:
        Object with all NumPy types and dataclasses converted to Python native types
    """
    # Handle dataclass objects
    if is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)

    # Handle datetime.date objects
    if isinstance(obj, date):
        return obj.isoformat()

    # Handle dict
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}

    # Handle list
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]

    # Handle tuple
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)

    # Handle NumPy integer types
    elif isinstance(obj, np.integer):
        return int(obj)

    # Handle NumPy float types
    elif isinstance(obj, np.floating):
        return float(obj)

    # Handle NumPy arrays
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())

    # Handle NumPy bool
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)

    # Return as-is for other types
    else:
        return obj


class DataFetcherService:
    """
    Flask service for fetching and managing Kite historical data

    This service wraps KiteClient with Flask-friendly features:
    - Session-based authentication
    - Progress tracking for UI updates
    - Batch operations with status callbacks
    - Error handling with user-friendly messages
    """

    def __init__(self, api_key: str = None, access_token: str = None):
        """
        Initialize data fetcher service

        Args:
            api_key: Kite API key (optional, from config if not provided)
            access_token: Kite access token (optional, from session)
        """
        self.api_key = api_key
        self.access_token = access_token
        self._client = None

    @property
    def client(self) -> KiteClient:
        """Lazy-load KiteClient when needed"""
        if self._client is None:
            if not self.access_token:
                raise KiteAuthenticationError("No access token available. Please authenticate first.")
            self._client = KiteClient(
                api_key=self.api_key,
                access_token=self.access_token
            )
        return self._client

    def is_authenticated(self) -> bool:
        """Check if service has valid authentication"""
        return bool(self.access_token)

    def set_access_token(self, access_token: str):
        """
        Update access token (e.g., from session)

        Args:
            access_token: New access token
        """
        self.access_token = access_token
        self._client = None  # Reset client to use new token

    def get_profile(self) -> Dict:
        """
        Get user profile information

        Returns:
            Dict with user profile data

        Raises:
            KiteAuthenticationError: If not authenticated
        """
        return self.client.get_profile()

    def fetch_equity(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = 'day',
        exchange: Optional[str] = None,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch equity data by symbol

        Args:
            symbol: Trading symbol (e.g., 'RELIANCE', 'TCS')
            from_date: Start date
            to_date: End date
            interval: Timeframe (minute, day, etc.)
            exchange: Specific exchange (NSE/BSE) or None for auto-detect
            validate: Run data validation
            overwrite: Overwrite existing data
            incremental: Only fetch missing data

        Returns:
            Result dict with success status and details
        """
        logger.info(f"Fetching equity data: {symbol} [{interval}] {from_date.date()} to {to_date.date()}")

        try:
            result = self.client.fetch_equity_by_symbol(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                exchange=exchange,
                validate=validate,
                overwrite=overwrite,
                incremental=incremental
            )
            # Convert NumPy types to Python native types for JSON serialization
            return convert_numpy_types(result)

        except KiteAuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'interval': interval,
                'error': 'Authentication failed. Please log in again.',
                'error_type': 'auth'
            }
        except KiteAPIError as e:
            logger.error(f"API error: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'interval': interval,
                'error': f'API error: {str(e)}',
                'error_type': 'api'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                'success': False,
                'symbol': symbol,
                'interval': interval,
                'error': f'Error: {str(e)}',
                'error_type': 'unknown'
            }

    def fetch_derivatives(
        self,
        exchange: str,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = 'day',
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch derivatives (options/futures) data

        Args:
            exchange: Exchange (NFO, BFO)
            symbol: Trading symbol (e.g., 'NIFTY25OCT24950CE')
            from_date: Start date
            to_date: End date
            interval: Timeframe
            validate: Run data validation
            overwrite: Overwrite existing data
            incremental: Only fetch missing data

        Returns:
            Result dict with success status and details
        """
        logger.info(f"Fetching derivatives data: {exchange}/{symbol} [{interval}]")

        try:
            result = self.client.fetch_derivatives_by_symbol(
                exchange=exchange,
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                validate=validate,
                overwrite=overwrite,
                incremental=incremental
            )
            return convert_numpy_types(result)

        except KiteAuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': 'Authentication failed. Please log in again.',
                'error_type': 'auth'
            }
        except KiteAPIError as e:
            logger.error(f"API error: {e}")
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': f'API error: {str(e)}',
                'error_type': 'api'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': f'Error: {str(e)}',
                'error_type': 'unknown'
            }

    def fetch_batch(
        self,
        requests: List[Dict],
        progress_callback=None
    ) -> Dict:
        """
        Fetch data for multiple symbols in batch

        Args:
            requests: List of fetch requests, each with:
                - segment: 'EQUITY' or 'DERIVATIVES'
                - exchange: Exchange name (optional for equity, required for derivatives)
                - symbol: Trading symbol
                - from_date: Start date
                - to_date: End date
                - interval: Timeframe
                - validate: Run validation (default: True)
                - overwrite: Overwrite existing (default: False)
                - incremental: Only fetch missing (default: True)
            progress_callback: Callback function(current, total, symbol, status)

        Returns:
            Summary dict with batch results
        """
        total = len(requests)
        results = []

        logger.info(f"Starting batch fetch: {total} requests")

        for idx, req in enumerate(requests, 1):
            segment = req.get('segment', 'EQUITY').upper()
            symbol = req.get('symbol')
            interval = req.get('interval', 'day')

            if progress_callback:
                progress_callback(idx, total, symbol, 'fetching')

            # Route to appropriate fetcher based on segment
            if segment == 'EQUITY':
                result = self.fetch_equity(
                    symbol=symbol,
                    from_date=req['from_date'],
                    to_date=req['to_date'],
                    interval=interval,
                    exchange=req.get('exchange'),
                    validate=req.get('validate', True),
                    overwrite=req.get('overwrite', False),
                    incremental=req.get('incremental', True)
                )
            elif segment == 'DERIVATIVES':
                result = self.fetch_derivatives(
                    exchange=req['exchange'],
                    symbol=symbol,
                    from_date=req['from_date'],
                    to_date=req['to_date'],
                    interval=interval,
                    validate=req.get('validate', True),
                    overwrite=req.get('overwrite', False),
                    incremental=req.get('incremental', True)
                )
            else:
                result = {
                    'success': False,
                    'symbol': symbol,
                    'interval': interval,
                    'error': f'Invalid segment: {segment}. Must be EQUITY or DERIVATIVES'
                }

            results.append(result)

            if progress_callback:
                status = 'success' if result.get('success') else 'failed'
                progress_callback(idx, total, symbol, status)

        # Calculate summary
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]

        summary = {
            'total': total,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': round(len(successful) / total * 100, 1) if total > 0 else 0,
            'results': results
        }

        logger.info(f"Batch complete: {len(successful)}/{total} successful")
        return convert_numpy_types(summary)

    def get_instruments(
        self,
        exchange: str,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Get list of instruments for exchange

        Args:
            exchange: Exchange name (NSE, BSE, NFO, BFO, )
            use_cache: Use cached data if available
            force_refresh: Force refresh from API

        Returns:
            List of instrument dicts
        """
        try:
            return self.client.get_instruments(
                exchange=exchange,
                use_cache=use_cache,
                force_refresh=force_refresh
            )
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return []

    def lookup_instrument(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[int]:
        """
        Lookup instrument token for symbol

        Args:
            exchange: Exchange name
            symbol: Trading symbol

        Returns:
            Instrument token or None if not found
        """
        try:
            return self.client.lookup_instrument_token(exchange, symbol)
        except Exception as e:
            logger.error(f"Error looking up instrument: {e}")
            return None

    def get_existing_data_range(
        self,
        exchange: str,
        symbol: str,
        interval: str
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Get date range of existing data

        Args:
            exchange: Exchange name
            symbol: Trading symbol
            interval: Timeframe

        Returns:
            Tuple of (start_date, end_date) or None if no data
        """
        try:
            return self.client.get_existing_date_range(exchange, symbol, interval)
        except Exception as e:
            logger.error(f"Error getting existing data range: {e}")
            return None

    def get_database_info(self, segment: str = 'EQUITY') -> Dict:
        """
        Get information about HDF5 database

        Args:
            segment: Database segment (EQUITY, DERIVATIVES, )

        Returns:
            Dict with database statistics
        """
        try:
            db = HDF5Manager(segment=segment)

            # Get file info
            file_path = db.hdf5_file
            file_exists = file_path.exists()
            file_size = file_path.stat().st_size / (1024**2) if file_exists else 0  # MB

            # Get data info
            exchanges = []
            total_datasets = 0

            if file_exists:
                with db._open_file('r') as f:
                    # Count exchanges and datasets
                    if 'data' in f:
                        exchanges = list(f['data'].keys())
                        for exchange in exchanges:
                            exchange_group = f['data'][exchange]
                            for symbol in exchange_group.keys():
                                symbol_group = exchange_group[symbol]
                                total_datasets += len(symbol_group.keys())

            return {
                'segment': segment,
                'file_path': str(file_path),
                'exists': file_exists,
                'size_mb': round(file_size, 2),
                'exchanges': exchanges,
                'total_datasets': total_datasets
            }

        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {
                'segment': segment,
                'error': str(e)
            }


# Convenience function for creating service instance
def create_data_fetcher(api_key: str = None, access_token: str = None) -> DataFetcherService:
    """
    Create and return DataFetcherService instance

    Args:
        api_key: Kite API key (optional, from config)
        access_token: Kite access token (optional, from session)

    Returns:
        DataFetcherService instance
    """
    return DataFetcherService(api_key=api_key, access_token=access_token)

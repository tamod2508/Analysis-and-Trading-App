"""
Kite Connect API Client - Historical Data Fetcher
Handles rate limiting, retries, and data normalization
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from kiteconnect import KiteConnect
import pandas as pd

from config import config
from config.constants import Exchange, Interval, API_LIMITS, Segment
from database.data_validator import DataValidator
from database.hdf5_manager import HDF5Manager
from database.instruments_db import InstrumentsDB
from utils.logger import get_logger

logger = get_logger(__name__, 'fetcher.log')


class KiteAPIError(Exception):
    """Base exception for Kite API errors"""
    pass


class KiteRateLimitError(KiteAPIError):
    """Rate limit exceeded (HTTP 429)"""
    pass


class KiteServerError(KiteAPIError):
    """Server error (HTTP 5xx)"""
    pass


class KiteAuthenticationError(KiteAPIError):
    """Authentication/token error (HTTP 401/403)"""
    pass


class KiteClient:
    """
    Kite Connect API client for fetching historical data
    Handles rate limiting, retries, and data validation
    """
    
    def __init__(self, api_key: str = None, access_token: str = None):
        """
        Initialize Kite client
        
        Args:
            api_key: Kite API key (default: from config)
            access_token: Kite access token (default: from config)
        """
        self.api_key = api_key or config.KITE_API_KEY
        self.access_token = access_token or config.KITE_ACCESS_TOKEN
        
        if not self.api_key:
            raise ValueError("API key not configured")
        
        # Initialize KiteConnect
        self.kite = KiteConnect(api_key=self.api_key)
        
        if self.access_token:
            self.kite.set_access_token(self.access_token)
        
        # Rate limiting
        self.last_request_time = time.time()
        self.min_request_interval = (1.0 / config.API_RATE_LIMIT) + config.API_RATE_SAFETY_MARGIN

        # Validator and database
        self.validator = DataValidator()
        self.db = HDF5Manager()
        self.instruments_db = InstrumentsDB()

        actual_rate = 1.0 / self.min_request_interval
        logger.info(f"KiteClient initialized (rate limit: {config.API_RATE_LIMIT} req/sec with {config.API_RATE_SAFETY_MARGIN*1000:.0f}ms safety margin, actual: {actual_rate:.2f} req/sec, interval: {self.min_request_interval:.3f}s)")
    
    def _rate_limit_wait(self):
        """Enforce rate limiting between API calls"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def _make_api_call(self, func, *args, **kwargs):
        """
        Make API call with rate limiting and retry logic
        
        Args:
            func: API function to call
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            API response
        """
        for attempt in range(config.MAX_RETRIES):
            try:
                self._rate_limit_wait()
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit error
                if "Too many requests" in error_msg or "429" in error_msg:
                    wait_time = config.RETRY_DELAY * (config.RETRY_BACKOFF ** attempt)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt+1}/{config.MAX_RETRIES}")
                    time.sleep(wait_time)
                    continue
                
                # Check if it's a server error (retry)
                elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
                    wait_time = config.RETRY_DELAY * (config.RETRY_BACKOFF ** attempt)
                    logger.warning(f"Server error, retrying in {wait_time}s (attempt {attempt+1}/{config.MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
                
                # Check if it's invalid token (don't retry)
                elif "Invalid" in error_msg and "token" in error_msg.lower():
                    logger.error("Invalid access token - please re-authenticate")
                    raise
                
                # Other errors
                else:
                    if attempt < config.MAX_RETRIES - 1:
                        wait_time = config.RETRY_DELAY * (config.RETRY_BACKOFF ** attempt)
                        logger.warning(f"API error: {error_msg}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"API call failed after {config.MAX_RETRIES} attempts: {error_msg}")
                        raise
        
        raise Exception(f"API call failed after {config.MAX_RETRIES} retries")
    
    def fetch_historical_data(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str,
    ) -> List[Dict]:
        """
        Fetch historical data for a single instrument
        
        Args:
            instrument_token: Kite instrument token
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            interval: Timeframe (minute, 15minute, 60minute, day)
        
        Returns:
            List of OHLCV dicts
        """
        logger.info(f"Fetching {interval} data for token {instrument_token} ({from_date.date()} to {to_date.date()})")
        
        try:
            data = self._make_api_call(
                self.kite.historical_data,
                instrument_token,
                from_date,
                to_date,
                interval,
                continuous=False,
                oi=False
            )
            
            if not data:
                logger.warning(f"No data returned for token {instrument_token}")
                return []
            
            logger.info(f"Fetched {len(data)} records")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise
    
    def fetch_historical_data_chunked(
        self,
        instrument_token: int,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
    ) -> List[Dict]:
        """
        Fetch historical data in chunks (for long date ranges)
        Respects API limits for each interval
        
        Args:
            instrument_token: Kite instrument token
            symbol: Trading symbol (for logging)
            from_date: Start date
            to_date: End date
            interval: Timeframe
        
        Returns:
            Combined list of OHLCV dicts
        """
        # Calculate API fetch chunk size based on interval
        interval_enum = Interval(interval)
        max_days_per_chunk = config.API_FETCH_CHUNK_DAYS
        
        # For intraday data, use smaller chunks
        if interval_enum != Interval.DAY:
            max_days_per_chunk = min(max_days_per_chunk, 60)  # 60 days max for intraday
        
        all_data = []
        current_start = from_date
        
        while current_start <= to_date:
            chunk_end = min(
                current_start + timedelta(days=max_days_per_chunk),
                to_date
            )
            
            logger.info(f"Fetching chunk: {current_start.date()} to {chunk_end.date()}")
            
            chunk_data = self.fetch_historical_data(
                instrument_token,
                current_start,
                chunk_end,
                interval
            )
            
            if chunk_data:
                all_data.extend(chunk_data)
            
            # Move to next chunk
            current_start = chunk_end + timedelta(days=1)
            
            # Pause between chunks
            if current_start <= to_date:
                time.sleep(config.BATCH_PAUSE_SECONDS)
        
        logger.info(f"Total records fetched for {symbol}: {len(all_data)}")
        return all_data
    
    def get_existing_date_range(
        self,
        exchange: str,
        symbol: str,
        interval: str,
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the date range of existing data in the database

        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            interval: Timeframe

        Returns:
            Tuple of (start_date, end_date) if data exists, None otherwise
        """
        try:
            data_info = self.db.get_data_info(exchange, symbol, interval)

            if not data_info or 'start_date' not in data_info:
                return None

            start_str = data_info.get('start_date')
            end_str = data_info.get('end_date')

            if not start_str or not end_str:
                return None

            # Dates are stored as Unix timestamps (strings)
            # Convert to datetime
            start_timestamp = int(start_str)
            end_timestamp = int(end_str)

            start_date = datetime.fromtimestamp(start_timestamp)
            end_date = datetime.fromtimestamp(end_timestamp)

            return (start_date, end_date)

        except Exception as e:
            logger.debug(f"Could not get existing date range for {exchange}:{symbol}: {e}")
            return None

    def calculate_missing_ranges(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        requested_start: datetime,
        requested_end: datetime,
    ) -> List[Tuple[datetime, datetime]]:
        """
        Calculate missing date ranges that need to be fetched

        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            interval: Timeframe
            requested_start: Desired start date
            requested_end: Desired end date

        Returns:
            List of (start, end) tuples representing missing ranges
        """
        existing_range = self.get_existing_date_range(exchange, symbol, interval)

        # No existing data - fetch full range
        if not existing_range:
            logger.info(f"No existing data for {exchange}:{symbol} [{interval}] - will fetch full range")
            return [(requested_start, requested_end)]

        existing_start, existing_end = existing_range
        logger.info(f"Existing data: {existing_start.date()} to {existing_end.date()}")

        missing_ranges = []

        # Only fetch NEW data after the existing end date
        # Don't try to backfill - if data wasn't there before, it won't be there now
        if requested_end > existing_end:
            gap_start = existing_end + timedelta(days=1)
            gap_end = requested_end
            logger.info(f"New data to fetch: {gap_start.date()} to {gap_end.date()}")
            missing_ranges.append((gap_start, gap_end))
        else:
            logger.info(f"All requested data already exists for {exchange}:{symbol} [{interval}]")

        return missing_ranges

    def fetch_and_save(
        self,
        exchange: str,
        symbol: str,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Complete workflow: fetch → validate → save

        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            instrument_token: Kite instrument token
            from_date: Start date
            to_date: End date
            interval: Timeframe
            validate: Run validation before saving
            overwrite: Overwrite existing data
            incremental: Only fetch missing date ranges (default: True)

        Returns:
            Dict with operation summary
        """
        start_time = time.time()

        try:
            # Determine what to fetch
            if overwrite or not incremental:
                # Full fetch
                logger.info(f"Starting {'FULL' if overwrite else 'NON-INCREMENTAL'} fetch for {exchange}:{symbol} [{interval}]")
                ranges_to_fetch = [(from_date, to_date)]
            else:
                # Incremental fetch - only missing ranges
                logger.info(f"Starting INCREMENTAL fetch for {exchange}:{symbol} [{interval}]")
                ranges_to_fetch = self.calculate_missing_ranges(
                    exchange,
                    symbol,
                    interval,
                    from_date,
                    to_date
                )

            # If no ranges to fetch, return success
            if not ranges_to_fetch:
                logger.info(f"✓ All data already exists for {exchange}:{symbol} [{interval}]")
                return {
                    'success': True,
                    'symbol': symbol,
                    'interval': interval,
                    'records': 0,
                    'message': 'All data already exists (incremental update)',
                    'elapsed_seconds': round(time.time() - start_time, 2),
                }

            # Fetch all missing ranges
            all_data = []
            for range_start, range_end in ranges_to_fetch:
                logger.info(f"Fetching range: {range_start.date()} to {range_end.date()}")
                range_data = self.fetch_historical_data_chunked(
                    instrument_token,
                    symbol,
                    range_start,
                    range_end,
                    interval
                )
                if range_data:
                    all_data.extend(range_data)

            data = all_data
            
            if not data:
                return {
                    'success': False,
                    'symbol': symbol,
                    'interval': interval,
                    'error': 'No data returned from API'
                }
            
            # Validate data
            if validate:
                logger.info(f"Validating {len(data)} records...")
                validation_result = self.validator.validate(
                    data,
                    exchange,
                    symbol,
                    interval,
                    expected_start=from_date,
                    expected_end=to_date
                )
                
                if not validation_result.is_valid:
                    logger.error(f"Validation failed:\n{validation_result.summary()}")
                    return {
                        'success': False,
                        'symbol': symbol,
                        'interval': interval,
                        'error': 'Data validation failed',
                        'validation': validation_result
                    }
                
                if validation_result.warnings:
                    logger.warning(f"Validation warnings:\n{validation_result.summary()}")
            
            # Save to database
            logger.info(f"Saving to database...")
            save_success = self.db.save_ohlcv(
                exchange,
                symbol,
                interval,
                data,
                overwrite=overwrite
            )
            
            if not save_success:
                return {
                    'success': False,
                    'symbol': symbol,
                    'interval': interval,
                    'error': 'Failed to save to database'
                }
            
            # Success
            elapsed = time.time() - start_time
            return {
                'success': True,
                'symbol': symbol,
                'interval': interval,
                'records': len(data),
                'date_range': f"{data[0]['date'].date()} to {data[-1]['date'].date()}",
                'elapsed_seconds': round(elapsed, 2),
                'validation': validation_result if validate else None
            }
            
        except Exception as e:
            logger.error(f"Error in fetch_and_save: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'interval': interval,
                'error': str(e)
            }

    def find_exchange_for_symbol(
        self,
        symbol: str,
        preferred_exchange: Optional[str] = None
    ) -> Optional[Tuple[str, int]]:
        """
        Find which exchange(s) a symbol is listed on

        Args:
            symbol: Trading symbol
            preferred_exchange: Preferred exchange (NSE or BSE). If None, returns first found.

        Returns:
            Tuple of (exchange, instrument_token) or None if not found
        """
        # Check preferred exchange first if specified
        if preferred_exchange:
            token = self.lookup_instrument_token(preferred_exchange, symbol)
            if token:
                return (preferred_exchange, token)

        # Check both exchanges
        for exchange in ['NSE', 'BSE']:
            if exchange == preferred_exchange:
                continue  # Already checked above

            token = self.lookup_instrument_token(exchange, symbol)
            if token:
                return (exchange, token)

        return None

    def fetch_equity_by_symbol(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        exchange: Optional[str] = None,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch equity data by symbol name (auto-detects exchange)

        This method:
        1. Looks up the symbol in the instruments database
        2. Auto-detects which exchange it's on (or uses specified exchange)
        3. Fetches data from that exchange

        Args:
            symbol: Trading symbol (e.g., 'RELIANCE', 'TCS')
            from_date: Start date
            to_date: End date
            interval: Timeframe
            exchange: Specific exchange (NSE or BSE). If None, auto-detects.
            validate: Run validation before saving
            overwrite: Overwrite existing data
            incremental: Only fetch missing date ranges (default: True)

        Returns:
            Dict with operation summary
        """
        logger.info(f"Looking up {symbol}" + (f" on {exchange}" if exchange else ""))

        try:
            # Find exchange and token
            result = self.find_exchange_for_symbol(symbol, preferred_exchange=exchange)

            if result is None:
                search_location = exchange if exchange else "NSE or BSE"
                return {
                    'success': False,
                    'symbol': symbol,
                    'interval': interval,
                    'error': f'Symbol {symbol} not found on {search_location}'
                }

            detected_exchange, token = result
            logger.info(f"Found {symbol} on {detected_exchange} (token: {token})")

            # Fetch from the detected exchange
            return self.fetch_and_save(
                exchange=detected_exchange,
                symbol=symbol,
                instrument_token=token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                validate=validate,
                overwrite=overwrite,
                incremental=incremental
            )

        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'interval': interval,
                'error': f'Failed to fetch symbol: {str(e)}'
            }

    def fetch_and_save_derivatives(
        self,
        exchange: str,
        symbol: str,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch derivatives (options/futures) data from NFO/BFO

        Unlike equity, derivatives contracts are unique to each exchange,
        so no fallback logic is needed.

        Args:
            exchange: Exchange name (NFO, BFO)
            symbol: Trading symbol (e.g., 'NIFTY25OCT24950CE', 'BANKNIFTY25NOV51500PE')
            instrument_token: Instrument token
            from_date: Start date
            to_date: End date
            interval: Timeframe
            validate: Run validation before saving
            overwrite: Overwrite existing data
            incremental: Only fetch missing date ranges (default: True)

        Returns:
            Dict with operation summary
        """
        if exchange.upper() not in ['NFO', 'BFO']:
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': f'Invalid derivatives exchange: {exchange}. Must be NFO or BFO'
            }

        try:
            start_time = time.time()
            logger.info(f"Fetching {exchange}/{symbol} [{interval}]")

            # Initialize HDF5Manager with DERIVATIVES segment
            derivatives_db = HDF5Manager(segment='DERIVATIVES')

            # Incremental update: check for existing data and calculate missing ranges
            if incremental and not overwrite:
                missing_ranges = self.calculate_missing_ranges(
                    exchange, symbol, interval, from_date, to_date
                )

                if not missing_ranges:
                    logger.info(f"All data already exists for {exchange}/{symbol} [{interval}]")
                    return {
                        'success': True,
                        'exchange': exchange,
                        'symbol': symbol,
                        'interval': interval,
                        'records': 0,
                        'message': 'All data already exists (incremental mode)',
                        'elapsed_seconds': round(time.time() - start_time, 2)
                    }

                # Fetch only missing ranges
                logger.info(f"Incremental mode: fetching {len(missing_ranges)} missing date range(s)")
                all_data = []

                for range_start, range_end in missing_ranges:
                    logger.info(f"Fetching gap: {range_start.date()} to {range_end.date()}")
                    gap_data = self.fetch_historical_data_chunked(
                        instrument_token,
                        symbol,
                        range_start,
                        range_end,
                        interval
                    )

                    if gap_data:
                        all_data.extend(gap_data)
                        logger.info(f"Fetched {len(gap_data)} records for gap")

                data = all_data
            else:
                # Fetch full range
                data = self.fetch_historical_data_chunked(
                    instrument_token,
                    symbol,
                    from_date,
                    to_date,
                    interval
                )

            if not data:
                return {
                    'success': False,
                    'exchange': exchange,
                    'symbol': symbol,
                    'interval': interval,
                    'error': 'No data returned from API'
                }

            logger.info(f"Received {len(data)} records from API")

            # Validate data if requested
            validation_result = None
            if validate:
                logger.info(f"Validating data...")
                validation_result = self.validator.validate(
                    data,
                    exchange,
                    symbol,
                    interval,
                    expected_start=from_date,
                    expected_end=to_date
                )

                if not validation_result.is_valid:
                    logger.error(f"Validation failed:\n{validation_result.summary()}")
                    return {
                        'success': False,
                        'exchange': exchange,
                        'symbol': symbol,
                        'interval': interval,
                        'error': 'Data validation failed',
                        'validation': validation_result
                    }

                if validation_result.warnings:
                    logger.warning(f"Validation warnings:\n{validation_result.summary()}")

            # Save to database (use derivatives DB)
            logger.info(f"Saving to DERIVATIVES database...")
            save_success = derivatives_db.save_ohlcv(
                exchange,
                symbol,
                interval,
                data,
                overwrite=overwrite
            )

            if not save_success:
                return {
                    'success': False,
                    'exchange': exchange,
                    'symbol': symbol,
                    'interval': interval,
                    'error': 'Failed to save to database'
                }

            # Success
            elapsed = time.time() - start_time
            return {
                'success': True,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'records': len(data),
                'date_range': f"{data[0]['date'].date()} to {data[-1]['date'].date()}",
                'elapsed_seconds': round(elapsed, 2),
                'validation': validation_result if validate else None
            }

        except Exception as e:
            logger.error(f"Error in fetch_and_save_derivatives: {e}")
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': str(e)
            }

    def fetch_derivatives_by_symbol(
        self,
        exchange: str,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch derivatives data by symbol name (auto-lookup instrument token)

        This is a convenience method that:
        1. Looks up the symbol in the specified derivatives exchange
        2. Extracts instrument token
        3. Calls fetch_and_save_derivatives()

        Args:
            exchange: Exchange name (NFO, BFO)
            symbol: Trading symbol (e.g., 'NIFTY25OCT24950CE', 'BANKNIFTY25NOV51500PE')
            from_date: Start date
            to_date: End date
            interval: Timeframe
            validate: Run validation before saving
            overwrite: Overwrite existing data
            incremental: Only fetch missing date ranges (default: True)

        Returns:
            Dict with operation summary
        """
        if exchange.upper() not in ['NFO', 'BFO']:
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': f'Invalid derivatives exchange: {exchange}. Must be NFO or BFO'
            }

        logger.info(f"Looking up instrument token for {exchange}/{symbol}")

        try:
            # Fast lookup using database (auto-refreshes if stale)
            token = self.lookup_instrument_token(exchange, symbol)

            if not token:
                return {
                    'success': False,
                    'exchange': exchange,
                    'symbol': symbol,
                    'interval': interval,
                    'error': f'Symbol {symbol} not found on {exchange}'
                }

            # Fetch the data
            return self.fetch_and_save_derivatives(
                exchange=exchange,
                symbol=symbol,
                instrument_token=token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                validate=validate,
                overwrite=overwrite,
                incremental=incremental
            )

        except Exception as e:
            logger.error(f"Error looking up symbol {symbol} on {exchange}: {e}")
            return {
                'success': False,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'error': f'Failed to lookup symbol: {str(e)}'
            }

    def fetch_multiple_symbols(
        self,
        instruments: List[Dict],
        from_date: datetime,
        to_date: datetime,
        intervals: List[str],
        validate: bool = True,
        overwrite: bool = False,
        progress_callback=None,
    ) -> Dict:
        """
        Fetch data for multiple symbols and intervals
        
        Args:
            instruments: List of dicts with 'exchange', 'symbol', 'instrument_token'
            from_date: Start date
            to_date: End date
            intervals: List of intervals to fetch
            validate: Run validation
            overwrite: Overwrite existing data
            progress_callback: Function to call with progress updates
        
        Returns:
            Dict with summary of all operations
        """
        total_tasks = len(instruments) * len(intervals)
        completed = 0
        results = []
        
        logger.info(f"Starting batch fetch: {len(instruments)} symbols × {len(intervals)} intervals = {total_tasks} tasks")
        
        for instrument in instruments:
            for interval in intervals:
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, total_tasks, instrument['symbol'], interval)
                
                result = self.fetch_and_save(
                    exchange=instrument['exchange'],
                    symbol=instrument['symbol'],
                    instrument_token=instrument['instrument_token'],
                    from_date=from_date,
                    to_date=to_date,
                    interval=interval,
                    validate=validate,
                    overwrite=overwrite
                )
                
                results.append(result)
                
                # Pause between batches
                if completed % config.BATCH_SIZE == 0:
                    logger.info(f"Batch pause ({completed}/{total_tasks})")
                    time.sleep(config.BATCH_PAUSE_SECONDS)
        
        # Summary
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        summary = {
            'total_tasks': total_tasks,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': round(len(successful) / total_tasks * 100, 1),
            'results': results
        }
        
        logger.info(f"Batch complete: {len(successful)}/{total_tasks} successful")
        return summary
    
    def get_instruments(
        self,
        exchange: str = None,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Get list of instruments (with persistent caching)

        This method:
        1. Checks persistent database first (if use_cache=True)
        2. Auto-refreshes if data is stale (older than 7 days)
        3. Falls back to API if database unavailable
        4. Saves fetched data to database for future use

        Args:
            exchange: Filter by exchange (NSE, BSE, NFO, BFO)
            use_cache: Use persistent database cache (default: True)
            force_refresh: Force API fetch even if cache exists (default: False)

        Returns:
            List of instrument dicts
        """
        if exchange is None:
            logger.warning("Exchange not specified - fetching from API without caching")
            use_cache = False

        # Try database first
        if use_cache and not force_refresh:
            df = self.instruments_db.get_instruments(
                exchange,
                refresh_if_stale=True  # Returns None if stale
            )

            if df is not None:
                logger.info(
                    f"✓ Using cached instruments for {exchange} "
                    f"({len(df)} instruments from database)"
                )
                return df.to_dict('records')
            else:
                if self.instruments_db.needs_refresh(exchange):
                    logger.info(
                        f"Instruments for {exchange} are stale or missing - "
                        f"fetching from API"
                    )

        # Fetch from API
        try:
            logger.info(f"Fetching instruments from API: {exchange or 'all exchanges'}")
            instruments = self._make_api_call(self.kite.instruments, exchange)
            logger.info(f"✓ Fetched {len(instruments)} instruments from API")

            # Save to database for future use (only if exchange is specified)
            if exchange and use_cache:
                save_success = self.instruments_db.save_instruments(
                    exchange,
                    instruments,
                    overwrite=True
                )
                if save_success:
                    logger.info(f"✓ Saved instruments to database for future use")

            return instruments

        except Exception as e:
            logger.error(f"Error fetching instruments from API: {e}")
            raise

    def lookup_instrument_token(
        self,
        exchange: str,
        symbol: str,
        use_cache: bool = True
    ) -> Optional[int]:
        """
        Fast lookup: symbol → instrument_token

        This method is optimized for performance:
        1. Tries database first (instant lookup via pandas indexing)
        2. Auto-refreshes if database is stale
        3. Falls back to API fetch if needed

        Args:
            exchange: Exchange name (NSE, BSE, NFO, BFO)
            symbol: Trading symbol
            use_cache: Use persistent database (default: True)

        Returns:
            Instrument token or None if not found
        """
        # Try database first (fast path)
        if use_cache:
            token = self.instruments_db.lookup_token(
                exchange,
                symbol,
                refresh_if_stale=True
            )

            if token is not None:
                return token

            # Database returned None - either symbol not found or data stale
            # Check if we need to refresh the database
            if self.instruments_db.needs_refresh(exchange):
                logger.info(
                    f"Database stale for {exchange} - refreshing before lookup"
                )
                # Fetch and save fresh data
                instruments = self.get_instruments(exchange, use_cache=True, force_refresh=True)

                # Try lookup again
                token = self.instruments_db.lookup_token(exchange, symbol, refresh_if_stale=False)
                if token is not None:
                    return token

        # Fallback: search through API results (slow path)
        logger.info(f"Symbol {symbol} not found in database - searching API results")
        instruments = self.get_instruments(exchange, use_cache=use_cache)

        for inst in instruments:
            if inst.get('tradingsymbol') == symbol:
                return inst.get('instrument_token')

        logger.warning(f"Symbol {symbol} not found on {exchange}")
        return None

    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return bool(self.access_token and self.kite.access_token)
    
    def get_profile(self) -> Dict:
        """Get user profile (to verify authentication)"""
        try:
            profile = self._make_api_call(self.kite.profile)
            return profile
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            raise


# Convenience functions
def create_client(api_key: str = None, access_token: str = None) -> KiteClient:
    """Create and return a KiteClient instance"""
    return KiteClient(api_key, access_token)


def fetch_symbol(
    symbol: str,
    instrument_token: int,
    from_date: datetime,
    to_date: datetime,
    exchange: str = "NSE",
    interval: str = "day",
) -> Dict:
    """
    Quick function to fetch a single symbol
    
    Usage:
        result = fetch_symbol(
            'RELIANCE',
            738561,
            datetime(2023, 1, 1),
            datetime(2024, 1, 1)
        )
    """
    client = create_client()
    return client.fetch_and_save(
        exchange,
        symbol,
        instrument_token,
        from_date,
        to_date,
        interval
    )
"""
Kite Connect API Client - Historical Data Fetcher
Handles rate limiting, retries, and data normalization
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from kiteconnect import KiteConnect
import pandas as pd

from config import config
from config.constants import Exchange, Interval, API_LIMITS, Segment
from database.data_validator import DataValidator
from database.hdf5_manager import HDF5Manager

logger = logging.getLogger(__name__)


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
        self.last_request_time = time.time()  # Initialize to current time
        self.min_request_interval = (1.0 / config.API_RATE_LIMIT) + config.API_RATE_SAFETY_MARGIN

        # Validator and database
        self.validator = DataValidator()
        self.db = HDF5Manager()

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
        # Calculate chunk size based on interval
        interval_enum = Interval(interval)
        max_days_per_chunk = config.HISTORICAL_DATA_CHUNK_DAYS
        
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

    def fetch_and_save_equity(
        self,
        symbol: str,
        nse_instrument_token: Optional[int] = None,
        bse_instrument_token: Optional[int] = None,
        from_date: datetime = None,
        to_date: datetime = None,
        interval: str = None,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch equity data with NSE-first, BSE-fallback logic

        This method implements smart exchange selection:
        1. Try NSE first (higher liquidity, better data quality)
        2. Only fall back to BSE if NSE has NO DATA available
        3. If NSE has data but validation/save fails, don't fall back (data exists)

        Args:
            symbol: Trading symbol (should be same on both exchanges)
            nse_instrument_token: NSE instrument token (optional)
            bse_instrument_token: BSE instrument token (optional)
            from_date: Start date
            to_date: End date
            interval: Timeframe
            validate: Run validation before saving
            overwrite: Overwrite existing data
            incremental: Only fetch missing date ranges (default: True)

        Returns:
            Dict with operation summary (includes which exchange was used)
        """
        if not nse_instrument_token and not bse_instrument_token:
            return {
                'success': False,
                'symbol': symbol,
                'interval': interval,
                'error': 'No instrument tokens provided (need at least NSE or BSE)'
            }

        # Try NSE first
        nse_has_data = False
        nse_result = None

        if nse_instrument_token:
            logger.info(f"Attempting to fetch {symbol} from NSE (preferred)")

            try:
                # Fetch data from NSE
                nse_data = self.fetch_historical_data_chunked(
                    nse_instrument_token,
                    symbol,
                    from_date,
                    to_date,
                    interval
                )

                # Check if we got data
                if nse_data and len(nse_data) > 0:
                    nse_has_data = True
                    logger.info(f"✓ NSE has data for {symbol} ({len(nse_data)} records)")

                    # Now validate and save
                    nse_result = self.fetch_and_save(
                        exchange='NSE',
                        symbol=symbol,
                        instrument_token=nse_instrument_token,
                        from_date=from_date,
                        to_date=to_date,
                        interval=interval,
                        validate=validate,
                        overwrite=overwrite,
                        incremental=incremental
                    )

                    nse_result['exchange_used'] = 'NSE'
                    nse_result['fallback_used'] = False
                    return nse_result
                else:
                    logger.warning(f"NSE returned no data for {symbol}")

            except Exception as e:
                logger.warning(f"NSE fetch failed for {symbol}: {e}")

        # Fallback to BSE only if NSE has no data
        if bse_instrument_token and not nse_has_data:
            if nse_instrument_token:
                logger.info(f"Falling back to BSE for {symbol} (NSE had no data)")
            else:
                logger.info(f"Fetching {symbol} from BSE (no NSE token available)")

            bse_result = self.fetch_and_save(
                exchange='BSE',
                symbol=symbol,
                instrument_token=bse_instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                validate=validate,
                overwrite=overwrite,
                incremental=incremental
            )

            if bse_result['success']:
                logger.info(f"✓ Successfully fetched {symbol} from BSE")
                bse_result['exchange_used'] = 'BSE'
                bse_result['fallback_used'] = bool(nse_instrument_token)
                return bse_result
            else:
                logger.error(f"BSE fetch failed for {symbol}: {bse_result.get('error', 'Unknown error')}")
                return bse_result

        # If NSE had data, return that result (even if it failed validation/save)
        if nse_has_data and nse_result:
            return nse_result

        # No data from either exchange
        return {
            'success': False,
            'symbol': symbol,
            'interval': interval,
            'error': 'No data available from NSE or BSE'
        }

    def fetch_equity_by_symbol(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        validate: bool = True,
        overwrite: bool = False,
        incremental: bool = True,
    ) -> Dict:
        """
        Fetch equity data by symbol name (auto-lookup instrument tokens)

        This is a convenience method that:
        1. Looks up the symbol in both NSE and BSE
        2. Extracts instrument tokens
        3. Calls fetch_and_save_equity() with NSE-first logic

        Args:
            symbol: Trading symbol (e.g., 'RELIANCE', 'TCS')
            from_date: Start date
            to_date: End date
            interval: Timeframe
            validate: Run validation before saving
            overwrite: Overwrite existing data
            incremental: Only fetch missing date ranges (default: True)

        Returns:
            Dict with operation summary
        """
        logger.info(f"Looking up instrument tokens for {symbol}")

        try:
            # Fetch instruments from both exchanges
            nse_instruments = self.get_instruments('NSE')
            bse_instruments = self.get_instruments('BSE')

            # Search for the symbol
            nse_token = None
            bse_token = None

            for inst in nse_instruments:
                if inst.get('tradingsymbol') == symbol:
                    nse_token = inst.get('instrument_token')
                    logger.info(f"Found {symbol} on NSE (token: {nse_token})")
                    break

            for inst in bse_instruments:
                if inst.get('tradingsymbol') == symbol:
                    bse_token = inst.get('instrument_token')
                    logger.info(f"Found {symbol} on BSE (token: {bse_token})")
                    break

            if not nse_token and not bse_token:
                return {
                    'success': False,
                    'symbol': symbol,
                    'interval': interval,
                    'error': f'Symbol {symbol} not found on NSE or BSE'
                }

            # Use the NSE-first logic
            return self.fetch_and_save_equity(
                symbol=symbol,
                nse_instrument_token=nse_token,
                bse_instrument_token=bse_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                validate=validate,
                overwrite=overwrite,
                incremental=incremental
            )

        except Exception as e:
            logger.error(f"Error looking up symbol {symbol}: {e}")
            return {
                'success': False,
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
    
    def get_instruments(self, exchange: str = None) -> List[Dict]:
        """
        Get list of instruments from Kite
        
        Args:
            exchange: Filter by exchange (NSE, BSE)
        
        Returns:
            List of instrument dicts
        """
        try:
            instruments = self._make_api_call(self.kite.instruments, exchange)
            logger.info(f"Fetched {len(instruments)} instruments from {exchange or 'all exchanges'}")
            return instruments
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            raise
    
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
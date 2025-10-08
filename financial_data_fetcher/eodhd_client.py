"""
EODHD API Client
Fetch fundamental data from EODHD API for Indian stock markets (NSE/BSE)
"""

import requests
import time
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class EODHDClient:
    """
    EODHD API Client for fetching fundamental data

    Documentation: https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds
    """

    BASE_URL = 'https://eodhd.com/api'
    RATE_LIMIT_DELAY = 0.075  # 75ms between requests = 800 requests/minute (buffer for 1000/min limit)

    def __init__(self, api_key: str, cache_dir: str = 'data/fundamentals/cache'):
        """
        Initialize EODHD client

        Args:
            api_key: Your EODHD API key
            cache_dir: Directory to cache responses (optional)
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KiteDataManager/1.0'
        })

        logger.info(f"EODHD Client initialized")
        logger.info(f"Cache directory: {self.cache_dir}")

    def get_exchange_symbols(self, exchange: str = 'NSE') -> List[Dict]:
        """
        Get list of all symbols on an exchange

        Args:
            exchange: Exchange code (NSE or BSE)

        Returns:
            List of ticker dicts with code, name, type, etc.
        """
        url = f"{self.BASE_URL}/exchange-symbol-list/{exchange}"
        params = {'api_token': self.api_key, 'fmt': 'json'}

        cache_file = self.cache_dir / f"{exchange}_symbols.json"

        # Check cache (valid for 1 day)
        if cache_file.exists():
            age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
            if age_hours < 24:
                logger.info(f"Using cached symbols for {exchange}")
                with open(cache_file, 'r') as f:
                    return json.load(f)

        logger.info(f"Fetching symbols from {exchange}...")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            symbols = response.json()

            # Cache the result
            with open(cache_file, 'w') as f:
                json.dump(symbols, f)

            logger.info(f"✅ Fetched {len(symbols)} symbols from {exchange}")

            time.sleep(self.RATE_LIMIT_DELAY)

            return symbols

        except Exception as e:
            logger.error(f"Error fetching symbols from {exchange}: {e}")
            raise

    def get_fundamental_data(
        self,
        symbol: str,
        exchange: str = 'NSE',
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Get fundamental data for a symbol

        Args:
            symbol: Company ticker (e.g., 'RELIANCE')
            exchange: Exchange code (NSE or BSE)
            use_cache: Use cached data if available

        Returns:
            Dict with fundamental data or None if not available
        """
        ticker = f"{symbol}.{exchange}"
        url = f"{self.BASE_URL}/fundamentals/{ticker}"
        params = {'api_token': self.api_key, 'fmt': 'json'}

        cache_file = self.cache_dir / f"{ticker}.json"

        # Check cache (valid for 1 week)
        if use_cache and cache_file.exists():
            age_days = (time.time() - cache_file.stat().st_mtime) / 86400
            if age_days < 7:
                logger.debug(f"Using cached data for {ticker}")
                with open(cache_file, 'r') as f:
                    return json.load(f)

        logger.info(f"Fetching fundamental data for {ticker}...")

        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()

            # Check if data is available
            if not data or 'error' in data:
                logger.warning(f"⚠️ No fundamental data for {ticker}")
                return None

            # Cache the result
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"✅ Fetched fundamental data for {ticker}")

            time.sleep(self.RATE_LIMIT_DELAY)

            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"⚠️ Fundamental data not found for {ticker}")
                return None
            else:
                logger.error(f"HTTP error for {ticker}: {e}")
                raise

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            raise

    def bulk_download_fundamentals(
        self,
        symbols: List[Tuple[str, str]],
        start_index: int = 0,
        max_companies: Optional[int] = None,
        skip_errors: bool = True
    ) -> Dict:
        """
        Download fundamentals for multiple companies

        Args:
            symbols: List of (symbol, exchange) tuples
            start_index: Index to start from (for resume capability)
            max_companies: Maximum number to download
            skip_errors: Continue on errors

        Returns:
            Dict with results summary
        """
        symbols_to_process = symbols[start_index:]
        if max_companies:
            symbols_to_process = symbols_to_process[:max_companies]

        total = len(symbols_to_process)
        results = {
            'success': [],
            'not_found': [],
            'errors': [],
            'total': total
        }

        logger.info(f"Starting bulk download for {total} companies")
        logger.info(f"Starting from index {start_index}")

        start_time = time.time()

        for i, (symbol, exchange) in enumerate(symbols_to_process, start=1):
            ticker = f"{symbol}.{exchange}"

            try:
                logger.info(f"[{i}/{total}] Processing {ticker}...")

                data = self.get_fundamental_data(symbol, exchange)

                if data:
                    results['success'].append(ticker)
                else:
                    results['not_found'].append(ticker)

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                results['errors'].append((ticker, str(e)))

                if not skip_errors:
                    raise

            # Progress update every 25 companies
            if i % 25 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total - i) / rate

                logger.info(f"Progress: {i}/{total} ({i/total*100:.1f}%)")
                logger.info(f"Success: {len(results['success'])}, "
                           f"Not Found: {len(results['not_found'])}, "
                           f"Errors: {len(results['errors'])}")
                logger.info(f"Rate: {rate:.1f} companies/sec, "
                           f"ETA: {remaining/60:.1f} minutes")

        # Final summary
        elapsed = time.time() - start_time

        logger.info(f"\n{'='*70}")
        logger.info(f"BULK DOWNLOAD COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Total Companies: {total}")
        logger.info(f"✅ Success: {len(results['success'])}")
        logger.info(f"⚠️ Not Found: {len(results['not_found'])}")
        logger.info(f"❌ Errors: {len(results['errors'])}")
        logger.info(f"Time Elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Average Rate: {total/elapsed:.1f} companies/sec")
        logger.info(f"{'='*70}")

        return results

    def get_coverage_stats(self, exchange: str = 'NSE') -> Dict:
        """
        Get coverage statistics for an exchange

        Args:
            exchange: Exchange code

        Returns:
            Dict with coverage statistics
        """
        symbols = self.get_exchange_symbols(exchange)

        # Sample companies to estimate coverage
        sample_size = min(50, len(symbols))
        sample_symbols = symbols[:sample_size]

        logger.info(f"Checking coverage for {exchange} (sampling {sample_size} companies)...")

        with_data = 0
        without_data = 0

        for ticker_data in sample_symbols:
            symbol = ticker_data['Code']
            try:
                data = self.get_fundamental_data(symbol, exchange)
                if data and 'Financials' in data:
                    with_data += 1
                else:
                    without_data += 1
            except:
                without_data += 1

        coverage_pct = (with_data / sample_size) * 100

        stats = {
            'exchange': exchange,
            'total_tickers': len(symbols),
            'sampled': sample_size,
            'with_data': with_data,
            'without_data': without_data,
            'estimated_coverage_pct': coverage_pct,
            'estimated_companies_with_data': int(len(symbols) * coverage_pct / 100)
        }

        logger.info(f"\n{'='*70}")
        logger.info(f"COVERAGE STATS - {exchange}")
        logger.info(f"{'='*70}")
        logger.info(f"Total Tickers: {stats['total_tickers']}")
        logger.info(f"Sampled: {stats['sampled']}")
        logger.info(f"With Fundamental Data: {stats['with_data']}/{stats['sampled']}")
        logger.info(f"Estimated Coverage: {stats['estimated_coverage_pct']:.1f}%")
        logger.info(f"Estimated Companies with Data: ~{stats['estimated_companies_with_data']}")
        logger.info(f"{'='*70}")

        return stats


if __name__ == '__main__':
    # Test script
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get API key from command line
    if len(sys.argv) < 2:
        print("Usage: python eodhd_client.py YOUR_API_KEY")
        print("\nGet your API key from: https://eodhd.com/")
        sys.exit(1)

    api_key = sys.argv[1]

    # Initialize client
    client = EODHDClient(api_key)

    # Test 1: Get NSE symbols
    print("\n" + "="*70)
    print("TEST 1: Get NSE Symbols")
    print("="*70)
    symbols = client.get_exchange_symbols('NSE')
    print(f"✅ Fetched {len(symbols)} NSE symbols")
    print(f"Sample: {symbols[:3]}")

    # Test 2: Get fundamental data for Reliance
    print("\n" + "="*70)
    print("TEST 2: Get Reliance Industries Fundamental Data")
    print("="*70)
    data = client.get_fundamental_data('RELIANCE', 'NSE')

    if data:
        print(f"✅ Got data for RELIANCE.NSE")
        if 'Highlights' in data:
            highlights = data['Highlights']
            print(f"\nKey Metrics:")
            print(f"  Market Cap: ₹{highlights.get('MarketCapitalization', 'N/A')} M")
            print(f"  Revenue: ₹{highlights.get('RevenueTTM', 'N/A')} M")
            print(f"  EBITDA: ₹{highlights.get('EBITDA', 'N/A')} M")
            print(f"  EPS: ₹{highlights.get('EarningsPerShareTTM', 'N/A')}")

        if 'Financials' in data:
            financials = data['Financials']
            if 'Balance_Sheet' in financials and 'yearly' in financials['Balance_Sheet']:
                years = len(financials['Balance_Sheet']['yearly'])
                print(f"\nFinancial History: {years} years of data")
    else:
        print(f"❌ No data for RELIANCE.NSE")

    # Test 3: Coverage stats
    print("\n" + "="*70)
    print("TEST 3: Check NSE Coverage")
    print("="*70)
    stats = client.get_coverage_stats('NSE')

    print(f"\n✅ All tests completed!")

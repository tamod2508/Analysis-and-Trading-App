#!/usr/bin/env python3
"""
Multi-threaded Bulk Fundamental Data Downloader
Uses ThreadPoolExecutor for parallel downloads - MUCH faster!
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_data_fetcher import EODHDClient, FundamentalsParser
from database.fundamentals_manager import FundamentalsManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/fundamentals/bulk_download_parallel.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ParallelBulkDownloader:
    """
    Multi-threaded bulk downloader for fundamental data

    Features:
    - Parallel downloads using ThreadPoolExecutor
    - Thread-safe statistics tracking
    - Resume capability
    - Progress tracking
    - Respects API rate limits (1000 req/min)
    """

    def __init__(self, api_key: str, max_workers: int = 4):
        """
        Initialize parallel bulk downloader

        Args:
            api_key: EODHD API key
            max_workers: Number of parallel threads (default: 4)
                        Set to 4 to leave CPU cores for other operations
        """
        self.eodhd = EODHDClient(api_key)
        self.manager = FundamentalsManager()
        self.max_workers = max_workers

        # Thread-safe statistics
        self.stats_lock = threading.Lock()
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'no_data': 0,
            'duplicates': 0,  # For ISIN-based deduplication
            'errors': []
        }

        # ISIN map for deduplication (NSE companies)
        self.nse_isins = None

    def download_all(
        self,
        exchange: str = 'NSE',
        start_index: int = 0,
        max_companies: Optional[int] = None,
        skip_existing: bool = True
    ):
        """
        Download fundamentals for all companies on an exchange (parallel)

        Args:
            exchange: NSE or BSE
            start_index: Start from this index (for resume)
            max_companies: Max companies to download (None = all)
            skip_existing: Skip companies already in database
        """
        logger.info("="*70)
        logger.info("PARALLEL BULK DOWNLOAD STARTED")
        logger.info("="*70)
        logger.info(f"Exchange: {exchange}")
        logger.info(f"Max Workers: {self.max_workers} threads")
        logger.info(f"Start Index: {start_index}")
        logger.info(f"Max Companies: {max_companies or 'All'}")
        logger.info(f"Skip Existing: {skip_existing}")

        # Get all symbols
        logger.info(f"\nFetching symbol list from {exchange}...")
        symbols_list = self.eodhd.get_exchange_symbols(exchange)

        if not symbols_list:
            logger.error("❌ Failed to fetch symbols")
            return

        # Filter if max_companies specified
        if max_companies:
            symbols_list = symbols_list[start_index:start_index + max_companies]
        else:
            symbols_list = symbols_list[start_index:]

        self.stats['total'] = len(symbols_list)

        logger.info(f"✅ Found {len(symbols_list)} companies to process")
        logger.info("="*70)

        # Get existing companies if skip_existing
        existing_companies = set()
        if skip_existing:
            existing_companies = set(self.manager.list_companies(exchange))
            logger.info(f"📋 {len(existing_companies)} companies already in database")

        # Build NSE ISIN map for BSE deduplication
        if exchange == 'BSE':
            logger.info("🔍 Building NSE ISIN map for deduplication...")
            self.nse_isins = self._build_nse_isin_map()
            logger.info(f"✅ Found {len(self.nse_isins)} NSE companies with ISIN")

        # Filter out existing companies
        to_download = []
        for symbol_data in symbols_list:
            symbol = symbol_data.get('Code', '')
            if not (skip_existing and symbol in existing_companies):
                to_download.append((exchange, symbol, symbol_data.get('Name', symbol)))
            else:
                with self.stats_lock:
                    self.stats['skipped'] += 1

        logger.info(f"📥 Will download {len(to_download)} companies ({self.stats['skipped']} skipped)")
        logger.info("="*70)
        logger.info(f"🚀 Starting parallel download with {self.max_workers} threads...")
        logger.info("="*70)

        # Process in parallel
        start_time = datetime.now()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self._download_single, exch, sym, name): (exch, sym, name)
                for exch, sym, name in to_download
            }

            # Process completed tasks
            completed = 0
            for future in as_completed(futures):
                completed += 1
                progress = (completed / len(to_download)) * 100

                if completed % 50 == 0 or completed == len(to_download):
                    logger.info(f"\n[{completed}/{len(to_download)}] ({progress:.1f}%) completed")
                    self._print_progress_summary()

        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "="*70)
        logger.info("PARALLEL BULK DOWNLOAD COMPLETE")
        logger.info("="*70)
        logger.info(f"Total Companies: {self.stats['total']}")
        logger.info(f"✅ Success: {self.stats['success']}")
        logger.info(f"⏭️  Skipped: {self.stats['skipped']}")
        logger.info(f"🔄 Duplicates: {self.stats['duplicates']}")
        logger.info(f"⚠️  No Data: {self.stats['no_data']}")
        logger.info(f"❌ Failed: {self.stats['failed']}")
        logger.info(f"⏱️  Duration: {duration/60:.1f} minutes")
        logger.info(f"⚡ Speed: {len(to_download)/(duration/60):.1f} companies/min")

        # Show errors
        if self.stats['errors']:
            logger.info(f"\n❌ Errors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Show first 10
                logger.info(f"  - {error}")

        # Database stats
        db_stats = self.manager.get_statistics()
        logger.info(f"\n📊 Database Statistics:")
        logger.info(f"  Total Companies: {db_stats['total_companies']}")
        logger.info(f"  File Size: {db_stats['file_size_mb']:.2f} MB")

        logger.info("="*70)

    def _build_nse_isin_map(self) -> dict:
        """Build map of ISIN -> Symbol from NSE companies"""
        import h5py

        isin_map = {}
        nse_companies = self.manager.list_companies('NSE')

        with h5py.File(self.manager.db_path, 'r') as f:
            for symbol in nse_companies:
                path = f"/companies/NSE/{symbol}"
                if path in f:
                    isin = f[path].attrs.get('general_isin', '')
                    if isin:
                        isin_map[isin] = symbol

        return isin_map

    def _is_duplicate(self, isin: str) -> Tuple[bool, str]:
        """
        Check if company is duplicate (already exists in NSE)

        Returns:
            (is_duplicate, nse_symbol)
        """
        if not self.nse_isins or not isin:
            return False, ''

        nse_symbol = self.nse_isins.get(isin)
        return nse_symbol is not None, nse_symbol or ''

    def _download_single(self, exchange: str, symbol: str, name: str) -> bool:
        """
        Download and store single company (thread-safe)

        Returns:
            True if successful
        """
        try:
            # Fetch from EODHD
            raw_data = self.eodhd.get_fundamental_data(symbol, exchange)

            if not raw_data:
                with self.stats_lock:
                    self.stats['no_data'] += 1
                return False

            # Check for duplicates (BSE only)
            if exchange == 'BSE' and self.nse_isins:
                general = raw_data.get('General', {})
                isin = general.get('ISIN', '')

                is_dup, nse_symbol = self._is_duplicate(isin)
                if is_dup:
                    with self.stats_lock:
                        self.stats['duplicates'] += 1
                    logger.debug(f"⏭️ {symbol} - Duplicate of NSE:{nse_symbol} (ISIN: {isin})")
                    return False

            # Parse
            parsed = FundamentalsParser.parse_all(raw_data)

            # Validate
            is_valid, warnings = FundamentalsParser.validate_parsed_data(parsed)

            if not is_valid:
                with self.stats_lock:
                    self.stats['no_data'] += 1
                return False

            # Store (thread-safe - HDF5 handles locking)
            success = self.manager.save_company_fundamentals(
                exchange,
                symbol,
                parsed,
                overwrite=True
            )

            if success:
                with self.stats_lock:
                    self.stats['success'] += 1
                logger.debug(f"✅ {symbol} - {name}")
                return True
            else:
                with self.stats_lock:
                    self.stats['failed'] += 1
                    self.stats['errors'].append(f"{symbol}: Storage failed")
                return False

        except Exception as e:
            with self.stats_lock:
                self.stats['failed'] += 1
                self.stats['errors'].append(f"{symbol}: {str(e)}")
            logger.error(f"❌ {symbol}: {e}")
            return False

    def _print_progress_summary(self):
        """Print progress summary (thread-safe)"""
        with self.stats_lock:
            logger.info("\n" + "-"*70)
            logger.info("PROGRESS SUMMARY")
            logger.info(f"  Success: {self.stats['success']}")
            logger.info(f"  Skipped: {self.stats['skipped']}")
            logger.info(f"  Duplicates: {self.stats['duplicates']}")
            logger.info(f"  No Data: {self.stats['no_data']}")
            logger.info(f"  Failed: {self.stats['failed']}")
            logger.info("-"*70)


def main():
    """Main entry point"""

    print("\n" + "="*70)
    print("PARALLEL BULK FUNDAMENTAL DATA DOWNLOADER")
    print("="*70)

    # Load API key
    load_dotenv()
    api_key = os.getenv('EODHD_API_KEY', '').strip()

    if not api_key:
        print("\n❌ No API key found in EODHD_API_KEY environment variable")
        return

    print(f"\n✅ API key loaded: {api_key[:8]}...")

    # Configuration
    exchange = sys.argv[1] if len(sys.argv) > 1 else 'BSE'
    start_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    max_companies = int(sys.argv[3]) if len(sys.argv) > 3 else None
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4  # Default to 4 threads

    print("\n" + "="*70)
    print("CONFIGURATION")
    print("="*70)
    print(f"Exchange: {exchange}")
    print(f"Start Index: {start_index}")
    print(f"Max Companies: {max_companies or 'All'}")
    print(f"Parallel Threads: {max_workers}")
    print("="*70)

    # Start download
    downloader = ParallelBulkDownloader(api_key, max_workers=max_workers)
    downloader.download_all(
        exchange=exchange,
        start_index=start_index,
        max_companies=max_companies,
        skip_existing=True
    )


if __name__ == '__main__':
    main()

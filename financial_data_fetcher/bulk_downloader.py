#!/usr/bin/env python3
"""
Bulk Fundamental Data Downloader
Downloads fundamental data from EODHD API and writes to QuestDB
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_data_fetcher import EODHDClient, FundamentalsParser
from database2.client import QuestDBClient
from financial_data_fetcher.storage import FundamentalsWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/fundamentals/bulk_download.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class BulkDownloader:
    """
    Bulk downloader for fundamental data

    Features:
    - Fetches from EODHD API
    - Writes to QuestDB
    - Resume capability (skip already downloaded companies)
    - Progress tracking
    - Error handling
    - Statistics reporting
    """

    def __init__(self, api_key: str):
        """
        Initialize bulk downloader

        Args:
            api_key: EODHD API key
        """
        self.eodhd = EODHDClient(api_key)
        self.questdb_client = QuestDBClient()
        self.questdb_writer = FundamentalsWriter(self.questdb_client)

        logger.info("✅ QuestDB writer initialized")

        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'no_data': 0,
            'errors': []
        }

    def download_all(
        self,
        exchange: str = 'NSE',
        start_index: int = 0,
        max_companies: Optional[int] = None,
        skip_existing: bool = True
    ):
        """
        Download fundamentals for all companies on an exchange

        Args:
            exchange: NSE or BSE
            start_index: Start from this index (for resume)
            max_companies: Max companies to download (None = all)
            skip_existing: Skip companies already in QuestDB
        """
        logger.info("="*70)
        logger.info("BULK DOWNLOAD STARTED")
        logger.info("="*70)
        logger.info(f"Exchange: {exchange}")
        logger.info(f"Start Index: {start_index}")
        logger.info(f"Max Companies: {max_companies or 'All'}")
        logger.info(f"Skip Existing: {skip_existing}")

        # Get all symbols from EODHD
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
            try:
                result = self.questdb_client.execute_query(
                    f"SELECT DISTINCT symbol FROM fundamentals_balance_sheet WHERE exchange = '{exchange}'"
                )
                existing_companies = {row[0] for row in result}
                logger.info(f"📋 {len(existing_companies)} companies already in QuestDB")
            except Exception as e:
                logger.warning(f"⚠️ Could not check existing companies: {e}")

        # Process each company
        start_time = datetime.now()

        for idx, symbol_data in enumerate(symbols_list, 1):
            symbol = symbol_data.get('Code', '')
            name = symbol_data.get('Name', symbol)

            # Progress
            progress = (idx / len(symbols_list)) * 100
            logger.info(f"\n[{idx}/{len(symbols_list)}] ({progress:.1f}%) Processing {symbol}")

            # Skip if already exists
            if skip_existing and symbol in existing_companies:
                logger.info(f"  ⏭️  Skipped (already in database)")
                self.stats['skipped'] += 1
                continue

            # Download and store
            success = self._download_single(exchange, symbol, name)

            if success:
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1

            # Show progress every 50 companies
            if idx % 50 == 0:
                self._print_progress_summary()

        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "="*70)
        logger.info("BULK DOWNLOAD COMPLETE")
        logger.info("="*70)
        logger.info(f"Total Companies: {self.stats['total']}")
        logger.info(f"✅ Success: {self.stats['success']}")
        logger.info(f"⏭️  Skipped: {self.stats['skipped']}")
        logger.info(f"⚠️  No Data: {self.stats['no_data']}")
        logger.info(f"❌ Failed: {self.stats['failed']}")
        logger.info(f"\n⏱️  Duration: {duration/60:.1f} minutes")
        logger.info(f"⚡ Speed: {self.stats['total']/(duration/60):.1f} companies/min")

        # Show errors
        if self.stats['errors']:
            logger.info(f"\n❌ Errors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Show first 10
                logger.info(f"  - {error}")

        # QuestDB stats
        try:
            result = self.questdb_client.execute_query(
                f"SELECT COUNT(DISTINCT symbol) FROM fundamentals_balance_sheet WHERE exchange = '{exchange}'"
            )
            total_companies = result[0][0] if result else 0
            logger.info(f"\n📊 QuestDB Statistics:")
            logger.info(f"  Total Companies ({exchange}): {total_companies}")
        except Exception as e:
            logger.warning(f"Could not fetch QuestDB stats: {e}")

        logger.info("="*70)

    def _download_single(self, exchange: str, symbol: str, name: str) -> bool:
        """
        Download and store single company

        Returns:
            True if successful
        """
        try:
            # Fetch from EODHD
            raw_data = self.eodhd.get_fundamental_data(symbol, exchange)

            if not raw_data:
                logger.warning(f"  ⚠️  No data available")
                self.stats['no_data'] += 1
                return False

            # Parse
            parsed = FundamentalsParser.parse_all(raw_data)

            # Validate
            is_valid, warnings = FundamentalsParser.validate_parsed_data(parsed)

            if not is_valid:
                logger.warning(f"  ⚠️  Invalid data: {', '.join(warnings)}")
                self.stats['no_data'] += 1
                return False

            # Write to QuestDB
            try:
                questdb_results = self._save_to_questdb(exchange, symbol, parsed)
                success_count = sum(1 for v in questdb_results.values() if v)
                total_count = len(questdb_results)

                if success_count == total_count:
                    logger.info(f"  ✅ Saved to QuestDB ({success_count}/{total_count} datasets)")
                    logger.info(f"  ✅ Saved {name}")
                    return True
                else:
                    failed_datasets = [k for k, v in questdb_results.items() if not v]
                    logger.warning(f"  ⚠️ Partial save ({success_count}/{total_count}, failed: {', '.join(failed_datasets)})")
                    return success_count > 0  # Partial success

            except Exception as e:
                logger.error(f"  ❌ Failed to save to QuestDB: {e}")
                self.stats['errors'].append(f"{symbol}: QuestDB storage failed - {e}")
                return False

        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            self.stats['errors'].append(f"{symbol}: {str(e)}")
            return False

    def _save_to_questdb(self, exchange: str, symbol: str, parsed: Dict) -> Dict[str, bool]:
        """
        Save parsed fundamentals to QuestDB

        Args:
            exchange: NSE or BSE
            symbol: Company symbol
            parsed: Parsed fundamentals data from FundamentalsParser.parse_all()

        Returns:
            Dict with success status for each dataset
        """
        # Convert NumPy arrays to list of dicts for QuestDB
        def numpy_to_dicts(np_array):
            if np_array is None or len(np_array) == 0:
                return []
            result = []
            for row in np_array:
                record = {}
                for field_name in row.dtype.names:
                    value = row[field_name]
                    # Convert bytes to string
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    # Convert NumPy types to Python types
                    elif hasattr(value, 'item'):
                        value = value.item()
                    record[field_name] = value
                result.append(record)
            return result

        # Prepare data for QuestDB
        balance_sheet_yearly = numpy_to_dicts(parsed.get('balance_sheet_yearly'))
        balance_sheet_quarterly = numpy_to_dicts(parsed.get('balance_sheet_quarterly'))
        income_statement_yearly = numpy_to_dicts(parsed.get('income_statement_yearly'))
        income_statement_quarterly = numpy_to_dicts(parsed.get('income_statement_quarterly'))
        cash_flow_yearly = numpy_to_dicts(parsed.get('cash_flow_yearly'))
        cash_flow_quarterly = numpy_to_dicts(parsed.get('cash_flow_quarterly'))
        general_info = parsed.get('general', {})
        highlights = parsed.get('highlights', {})

        # Write to QuestDB
        return self.questdb_writer.insert_all_fundamentals(
            symbol=symbol,
            exchange=exchange,
            balance_sheet_yearly=balance_sheet_yearly,
            balance_sheet_quarterly=balance_sheet_quarterly,
            income_statement_yearly=income_statement_yearly,
            income_statement_quarterly=income_statement_quarterly,
            cash_flow_yearly=cash_flow_yearly,
            cash_flow_quarterly=cash_flow_quarterly,
            general_info=general_info,
            highlights=highlights
        )

    def _print_progress_summary(self):
        """Print progress summary"""
        logger.info("\n" + "-"*70)
        logger.info("PROGRESS SUMMARY")
        logger.info(f"  Success: {self.stats['success']}")
        logger.info(f"  Skipped: {self.stats['skipped']}")
        logger.info(f"  No Data: {self.stats['no_data']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info("-"*70)


def main():
    """Main entry point"""

    print("\n" + "="*70)
    print("BULK FUNDAMENTAL DATA DOWNLOADER (QuestDB)")
    print("="*70)

    # Load API key
    load_dotenv()
    api_key = os.getenv('EODHD_API_KEY', '').strip()

    if not api_key:
        print("\n❌ No API key found in EODHD_API_KEY environment variable")
        return

    print(f"\n✅ API key loaded: {api_key[:8]}...")

    # Configuration
    print("\n" + "="*70)
    print("CONFIGURATION")
    print("="*70)

    exchange = input("\nExchange (NSE/BSE) [NSE]: ").strip().upper() or 'NSE'
    start_index = int(input("Start index (0 for beginning) [0]: ").strip() or "0")
    max_companies_str = input("Max companies (blank for all): ").strip()
    max_companies = int(max_companies_str) if max_companies_str else None
    skip_existing = input("Skip existing companies? (y/n) [y]: ").strip().lower() != 'n'

    print("\n" + "="*70)
    print("STARTING DOWNLOAD")
    print("="*70)
    print(f"Exchange: {exchange}")
    print(f"Start Index: {start_index}")
    print(f"Max Companies: {max_companies or 'All'}")
    print(f"Skip Existing: {skip_existing}")
    print(f"Target Database: QuestDB")
    print("="*70)

    confirm = input("\nProceed? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("Cancelled")
        return

    # Start download
    downloader = BulkDownloader(api_key)
    downloader.download_all(
        exchange=exchange,
        start_index=start_index,
        max_companies=max_companies,
        skip_existing=skip_existing
    )


if __name__ == '__main__':
    main()

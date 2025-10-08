#!/usr/bin/env python3
"""
Test fetch for 10 Nifty 50 stocks
Date range: 2017-01-01 to today
All intervals: day, 60minute, 30minute, 15minute, 10minute, 5minute, 3minute, minute
"""

from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.kite_client import KiteClient
from database.hdf5_manager import HDF5Manager

# 10 Nifty 50 stocks for testing
TEST_STOCKS = [
    'RELIANCE',
    'TCS',
    'HDFCBANK',
    'INFY',
    'ICICIBANK',
    'HINDUNILVR',
    'ITC',
    'SBIN',
    'BHARTIARTL',
    'KOTAKBANK'
]

# All intervals to fetch
INTERVALS = ['day', '60minute', '15minute', '5minute']

# Date range
FROM_DATE = datetime(2017, 1, 1)
TO_DATE = datetime.now()

def main():
    print("=" * 80)
    print("TEST FETCH: 10 Nifty 50 Stocks")
    print("=" * 80)
    print(f"Stocks: {', '.join(TEST_STOCKS)}")
    print(f"Intervals: {', '.join(INTERVALS)}")
    print(f"Date Range: {FROM_DATE.date()} to {TO_DATE.date()}")
    print(f"Total requests: {len(TEST_STOCKS)} stocks × {len(INTERVALS)} intervals = {len(TEST_STOCKS) * len(INTERVALS)}")
    print("=" * 80)
    print()

    # Initialize Kite client
    print("🔧 Initializing Kite client...")
    kite = KiteClient()

    # Statistics
    total_requests = len(TEST_STOCKS) * len(INTERVALS)
    completed = 0
    failed = 0
    total_records = 0

    start_time = datetime.now()

    # Fetch each stock for all intervals
    for stock in TEST_STOCKS:
        print(f"\n📊 Fetching {stock}...")
        print("-" * 80)

        for interval in INTERVALS:
            print(f"  ⏳ {interval:12s} ", end="", flush=True)

            try:
                result = kite.fetch_equity_by_symbol(
                    symbol=stock,
                    from_date=FROM_DATE,
                    to_date=TO_DATE,
                    interval=interval,
                    exchange='NSE',
                    validate=False,
                    incremental=True
                )

                if result['success']:
                    records = result.get('records', 0)
                    total_records += records
                    completed += 1
                    print(f"✅ {records:6d} records")
                else:
                    failed += 1
                    error = result.get('error', 'Unknown error')
                    print(f"❌ {error}")

            except Exception as e:
                failed += 1
                print(f"❌ Error: {str(e)}")

    # Final statistics
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Requests:   {total_requests}")
    print(f"Completed:        {completed} ✅")
    print(f"Failed:           {failed} ❌")
    print(f"Success Rate:     {(completed/total_requests)*100:.1f}%")
    print(f"Total Records:    {total_records:,}")
    print(f"Elapsed Time:     {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Avg per Request:  {elapsed/total_requests:.2f} seconds")
    print("=" * 80)

    # Verify database
    print("\n🔍 Verifying database...")
    mgr = HDF5Manager('EQUITY')
    stats = mgr.get_database_stats()

    print(f"Database Size:    {stats.get('file_size_mb', 0):.2f} MB")
    print(f"Total Symbols:    {stats['total_symbols']}")
    print(f"Total Datasets:   {stats['total_datasets']}")
    print(f"Exchanges:        {', '.join(stats['exchanges'].keys())}")

    for exchange, exchange_stats in stats['exchanges'].items():
        print(f"\n{exchange}:")
        print(f"  Symbols: {exchange_stats['symbols']}")
        print(f"  Datasets: {exchange_stats['datasets']}")

if __name__ == '__main__':
    main()

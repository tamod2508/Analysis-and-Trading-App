#!/usr/bin/env python3
"""
Fetch ALL Nifty 50 stocks - Full historical data
Date range: 2017-01-01 to today
Intervals: day, 60minute, 15minute, 5minute
"""

from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.kite_client import KiteClient
from database.hdf5_manager import HDF5Manager

# Complete Nifty 50 list (as of 2024)
NIFTY_50_STOCKS = [
    'ADANIENT',
    'ADANIPORTS',
    'APOLLOHOSP',
    'ASIANPAINT',
    'AXISBANK',
    'BAJAJ-AUTO',
    'BAJAJFINSV',
    'BAJFINANCE',
    'BHARTIARTL',
    'BPCL',
    'BRITANNIA',
    'CIPLA',
    'COALINDIA',
    'DIVISLAB',
    'DRREDDY',
    'EICHERMOT',
    'GRASIM',
    'HCLTECH',
    'HDFC',
    'HDFCBANK',
    'HDFCLIFE',
    'HEROMOTOCO',
    'HINDALCO',
    'HINDUNILVR',
    'ICICIBANK',
    'INDUSINDBK',
    'INFY',
    'ITC',
    'JSWSTEEL',
    'KOTAKBANK',
    'LT',
    'M&M',
    'MARUTI',
    'NESTLEIND',
    'NTPC',
    'ONGC',
    'POWERGRID',
    'RELIANCE',
    'SBILIFE',
    'SBIN',
    'SHREECEM',
    'SUNPHARMA',
    'TATACONSUM',
    'TATAMOTORS',
    'TATASTEEL',
    'TCS',
    'TECHM',
    'TITAN',
    'ULTRACEMCO',
    'UPL',
    'WIPRO'
]

# Intervals to fetch
INTERVALS = ['day', '60minute', '15minute', '5minute']

# Date range
FROM_DATE = datetime(2017, 1, 1)
TO_DATE = datetime.now()

def main():
    print("=" * 80)
    print("NIFTY 50 COMPLETE FETCH")
    print("=" * 80)
    print(f"Stocks: {len(NIFTY_50_STOCKS)} (Full Nifty 50)")
    print(f"Intervals: {', '.join(INTERVALS)}")
    print(f"Date Range: {FROM_DATE.date()} to {TO_DATE.date()}")
    print(f"Total requests: {len(NIFTY_50_STOCKS)} × {len(INTERVALS)} = {len(NIFTY_50_STOCKS) * len(INTERVALS)}")
    print(f"Estimated time: ~80-90 minutes")
    print("=" * 80)
    print()

    # Initialize Kite client
    print("🔧 Initializing Kite client...")
    kite = KiteClient()

    # Statistics
    total_requests = len(NIFTY_50_STOCKS) * len(INTERVALS)
    completed = 0
    failed = 0
    total_records = 0
    failed_fetches = []

    start_time = datetime.now()

    # Fetch each stock for all intervals
    for idx, stock in enumerate(NIFTY_50_STOCKS, 1):
        print(f"\n📊 [{idx}/{len(NIFTY_50_STOCKS)}] Fetching {stock}...")
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
                    failed_fetches.append(f"{stock} - {interval}: {error}")

            except Exception as e:
                failed += 1
                print(f"❌ Error: {str(e)}")
                failed_fetches.append(f"{stock} - {interval}: {str(e)}")

        # Progress update every 10 stocks
        if idx % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = len(NIFTY_50_STOCKS) - idx
            eta = (elapsed / idx) * remaining if idx > 0 else 0
            print(f"\n  📈 Progress: {idx}/{len(NIFTY_50_STOCKS)} stocks | {elapsed:.1f} min elapsed | ETA: {eta:.1f} min")

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

    if failed_fetches:
        print(f"\n⚠️  Failed Fetches ({len(failed_fetches)}):")
        for fail in failed_fetches[:10]:  # Show first 10
            print(f"  • {fail}")
        if len(failed_fetches) > 10:
            print(f"  ... and {len(failed_fetches) - 10} more")

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

    print("\n✅ Nifty 50 fetch complete!")

if __name__ == '__main__':
    main()

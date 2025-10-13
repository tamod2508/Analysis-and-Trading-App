"""
Test script for QuestDB Data Reader

Tests all major functionality of the data reader module
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quest.data_reader import QuestDBReader
from quest.client import QuestDBClient
import pandas as pd


def test_connection():
    """Test QuestDB connection"""
    print("=" * 60)
    print("Testing QuestDB Connection")
    print("=" * 60)

    reader = QuestDBReader()

    if reader.is_healthy():
        print("✓ Connection successful!")
        return True
    else:
        print("✗ Connection failed!")
        return False


def test_available_symbols(reader):
    """Test getting available symbols"""
    print("\n" + "=" * 60)
    print("Testing Available Symbols")
    print("=" * 60)

    try:
        # Get all symbols with at least 100 rows
        symbols = reader.get_available_symbols('NSE', 'day', min_rows=100)
        print(f"✓ Found {len(symbols)} symbols with data")

        if symbols:
            print(f"Sample symbols: {symbols[:5]}")
            return symbols[0] if symbols else None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_equity_data(reader, symbol):
    """Test getting equity data"""
    print("\n" + "=" * 60)
    print(f"Testing Equity Data for {symbol}")
    print("=" * 60)

    try:
        # Get latest 100 candles
        df = reader.get_latest_candles(symbol, 'NSE', 'day', limit=100)

        if not df.empty:
            print(f"✓ Retrieved {len(df)} candles")
            print(f"\nData shape: {df.shape}")
            print(f"\nColumns: {df.columns.tolist()}")
            print(f"\nFirst row:")
            print(df.head(1))
            print(f"\nLast row:")
            print(df.tail(1))
            return True
        else:
            print("✗ No data returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_date_range_query(reader, symbol):
    """Test date range query"""
    print("\n" + "=" * 60)
    print(f"Testing Date Range Query for {symbol}")
    print("=" * 60)

    try:
        # Get data for last 30 days
        df = reader.get_equity_data(
            symbol=symbol,
            exchange='NSE',
            interval='day',
            from_date='2024-01-01',
            to_date='2024-12-31'
        )

        if not df.empty:
            print(f"✓ Retrieved {len(df)} rows for 2024")
            print(f"\nDate range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"\nPrice range: ₹{df['low'].min():.2f} to ₹{df['high'].max():.2f}")
            print(f"\nAvg volume: {df['volume'].mean():.0f}")
            return True
        else:
            print("✗ No data in date range")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_symbol_stats(reader, symbol):
    """Test symbol statistics"""
    print("\n" + "=" * 60)
    print(f"Testing Symbol Statistics for {symbol}")
    print("=" * 60)

    try:
        stats = reader.get_symbol_stats(symbol, 'NSE', 'day')

        print(f"✓ Statistics retrieved")
        print(f"\nSymbol: {stats['symbol']}")
        print(f"Exchange: {stats['exchange']}")
        print(f"Interval: {stats['interval']}")
        print(f"Total rows: {stats['row_count']}")

        if stats['date_range']['first']:
            print(f"\nDate range:")
            print(f"  First: {stats['date_range']['first']}")
            print(f"  Last: {stats['date_range']['last']}")

        if stats['price_range']['min']:
            print(f"\nPrice range:")
            print(f"  Min: ₹{stats['price_range']['min']:.2f}")
            print(f"  Max: ₹{stats['price_range']['max']:.2f}")
            print(f"  Avg: ₹{stats['price_range']['avg']:.2f}")

        print(f"\nVolume:")
        print(f"  Total: {stats['volume']['total']:,}")
        print(f"  Average: {stats['volume']['avg']:,.0f}")
        print(f"  Max: {stats['volume']['max']:,}")

        print(f"\nAnomalies: {stats['anomaly_count']}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_batch_query(reader):
    """Test batch query for multiple symbols"""
    print("\n" + "=" * 60)
    print("Testing Batch Query")
    print("=" * 60)

    try:
        # Get data for multiple symbols
        symbols = ['RELIANCE', 'TCS', 'INFY']
        df = reader.get_equity_data_batch(
            symbols=symbols,
            exchange='NSE',
            interval='day',
            from_date='2024-01-01',
            exclude_anomalies=True
        )

        if not df.empty:
            print(f"✓ Retrieved {len(df)} rows for {len(symbols)} symbols")
            print(f"\nRows per symbol:")
            for symbol in symbols:
                count = len(df[df['symbol'] == symbol])
                print(f"  {symbol}: {count} rows")
            return True
        else:
            print("✗ No data returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_data_quality_summary(reader):
    """Test data quality summary"""
    print("\n" + "=" * 60)
    print("Testing Data Quality Summary")
    print("=" * 60)

    try:
        df = reader.get_data_quality_summary('NSE', 'day')

        if not df.empty:
            print(f"✓ Quality summary retrieved for {len(df)} symbols")
            print(f"\nTop 5 symbols by row count:")
            top_symbols = df.nlargest(5, 'total_rows')[['symbol', 'total_rows', 'anomaly_count', 'anomaly_pct']]
            print(top_symbols.to_string(index=False))
            return True
        else:
            print("✗ No quality data")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_date_range_lookup(reader, symbol):
    """Test date range lookup"""
    print("\n" + "=" * 60)
    print(f"Testing Date Range Lookup for {symbol}")
    print("=" * 60)

    try:
        date_range = reader.get_date_range_for_symbol(symbol, 'NSE', 'day')

        if date_range:
            first_date, last_date = date_range
            print(f"✓ Date range found")
            print(f"\nFirst date: {first_date}")
            print(f"Last date: {last_date}")
            print(f"Days of data: {(last_date - first_date).days}")
            return True
        else:
            print("✗ No date range found")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_raw_query(reader):
    """Test raw SQL query"""
    print("\n" + "=" * 60)
    print("Testing Raw SQL Query")
    print("=" * 60)

    try:
        sql = """
        SELECT
            exchange,
            COUNT(DISTINCT symbol) as symbol_count,
            COUNT(*) as total_rows
        FROM ohlcv_equity
        WHERE interval = 'day'
        GROUP BY exchange
        ORDER BY total_rows DESC
        """

        df = reader.execute_raw_query(sql)

        if not df.empty:
            print(f"✓ Query executed successfully")
            print(f"\nResults:")
            print(df.to_string(index=False))
            return True
        else:
            print("✗ No results")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("QuestDB Data Reader Test Suite")
    print("=" * 60)

    # Test connection
    if not test_connection():
        print("\n✗ Cannot connect to QuestDB. Make sure it's running!")
        return

    # Create reader
    reader = QuestDBReader()

    try:
        # Get available symbols
        test_symbol = test_available_symbols(reader)

        if test_symbol:
            # Run tests with the first available symbol
            test_equity_data(reader, test_symbol)
            test_date_range_query(reader, test_symbol)
            test_symbol_stats(reader, test_symbol)
            test_date_range_lookup(reader, test_symbol)

        # Run batch tests
        test_batch_query(reader)
        test_data_quality_summary(reader)
        test_raw_query(reader)

        print("\n" + "=" * 60)
        print("Test Suite Complete!")
        print("=" * 60)

    finally:
        reader.close()


if __name__ == '__main__':
    main()

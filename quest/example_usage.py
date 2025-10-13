"""
QuestDB Data Reader - Usage Examples

Demonstrates how to use the data reader with other quest modules
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quest import (
    QuestDBReader,
    QuestDBWriter,
    QuestDBClient,
    get_equity_data,
    get_latest_candles,
    get_symbol_stats,
    get_available_symbols,
)
import pandas as pd


def example_1_simple_queries():
    """Example 1: Simple data queries"""
    print("=" * 60)
    print("Example 1: Simple Data Queries")
    print("=" * 60)

    # Using convenience functions (auto-connect and close)
    print("\n1. Get latest 100 candles:")
    df = get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)
    print(f"   Retrieved {len(df)} candles")

    print("\n2. Get data for date range:")
    df = get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')
    print(f"   Retrieved {len(df)} rows")

    print("\n3. Get symbol statistics:")
    stats = get_symbol_stats('RELIANCE', 'NSE', 'day')
    print(f"   Total rows: {stats['row_count']}")
    print(f"   Price range: ₹{stats['price_range']['min']:.2f} - ₹{stats['price_range']['max']:.2f}")

    print("\n4. Get available symbols:")
    symbols = get_available_symbols('NSE', 'day', min_rows=200)
    print(f"   Found {len(symbols)} symbols")


def example_2_context_manager():
    """Example 2: Using context manager for multiple queries"""
    print("\n" + "=" * 60)
    print("Example 2: Context Manager (Reusable Connection)")
    print("=" * 60)

    with QuestDBReader() as reader:
        # Multiple queries using same connection
        print("\n1. Check connection health:")
        is_healthy = reader.is_healthy()
        print(f"   Connection healthy: {is_healthy}")

        print("\n2. Get available symbols:")
        symbols = reader.get_available_symbols('NSE', 'day', min_rows=100)
        print(f"   Found {len(symbols)} symbols")

        if symbols:
            symbol = symbols[0]

            print(f"\n3. Get data for {symbol}:")
            df = reader.get_equity_data(symbol, 'NSE', 'day', limit=50)
            print(f"   Retrieved {len(df)} rows")

            print(f"\n4. Get statistics for {symbol}:")
            stats = reader.get_symbol_stats(symbol, 'NSE', 'day')
            print(f"   Total rows: {stats['row_count']}")

            print(f"\n5. Get date range for {symbol}:")
            date_range = reader.get_date_range_for_symbol(symbol, 'NSE', 'day')
            if date_range:
                first, last = date_range
                print(f"   First date: {first}")
                print(f"   Last date: {last}")


def example_3_batch_operations():
    """Example 3: Batch operations for multiple symbols"""
    print("\n" + "=" * 60)
    print("Example 3: Batch Operations")
    print("=" * 60)

    reader = QuestDBReader()

    try:
        # Get data for multiple symbols at once
        symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']

        print(f"\n1. Batch query for {len(symbols)} symbols:")
        df = reader.get_equity_data_batch(
            symbols=symbols,
            exchange='NSE',
            interval='day',
            from_date='2024-01-01',
            exclude_anomalies=True
        )

        print(f"   Total rows: {len(df)}")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        print("\n2. Rows per symbol:")
        for symbol in symbols:
            count = len(df[df['symbol'] == symbol])
            print(f"   {symbol}: {count} rows")

        # Calculate correlations
        print("\n3. Calculate price correlations:")
        pivot = df.pivot_table(index='timestamp', columns='symbol', values='close')
        corr_matrix = pivot.corr()
        print(corr_matrix)

    finally:
        reader.close()


def example_4_filtering_and_analytics():
    """Example 4: Advanced filtering and analytics"""
    print("\n" + "=" * 60)
    print("Example 4: Filtering and Analytics")
    print("=" * 60)

    with QuestDBReader() as reader:
        symbol = 'RELIANCE'

        # Get data with various filters
        print(f"\n1. Get adjusted data only:")
        df = reader.get_equity_data(
            symbol=symbol,
            exchange='NSE',
            interval='day',
            adjusted=True,
            exclude_anomalies=True
        )
        print(f"   Adjusted rows: {len(df)}")

        # Calculate returns
        if not df.empty and len(df) > 1:
            df['returns'] = df['close'].pct_change()
            df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1

            print(f"\n2. Returns analysis:")
            print(f"   Daily return: {df['returns'].iloc[-1]*100:.2f}%")
            print(f"   Avg daily return: {df['returns'].mean()*100:.4f}%")
            print(f"   Volatility (std): {df['returns'].std()*100:.2f}%")
            print(f"   Cumulative return: {df['cumulative_returns'].iloc[-1]*100:.2f}%")

            print(f"\n3. Volume analysis:")
            print(f"   Avg volume: {df['volume'].mean():,.0f}")
            print(f"   Max volume: {df['volume'].max():,}")
            print(f"   Volume trend (20-day SMA): {df['volume'].tail(20).mean():,.0f}")


def example_5_data_quality():
    """Example 5: Data quality checks"""
    print("\n" + "=" * 60)
    print("Example 5: Data Quality Checks")
    print("=" * 60)

    with QuestDBReader() as reader:
        print("\n1. Get data quality summary:")
        quality_df = reader.get_data_quality_summary('NSE', 'day')

        if not quality_df.empty:
            print(f"   Total symbols: {len(quality_df)}")

            print("\n2. Top 5 symbols by data completeness:")
            top_5 = quality_df.nlargest(5, 'total_rows')[
                ['symbol', 'total_rows', 'anomaly_count', 'anomaly_pct']
            ]
            print(top_5.to_string(index=False))

            print("\n3. Symbols with high anomaly rates (>5%):")
            high_anomalies = quality_df[quality_df['anomaly_pct'] > 5.0]
            if not high_anomalies.empty:
                print(high_anomalies[['symbol', 'total_rows', 'anomaly_pct']].to_string(index=False))
            else:
                print("   No symbols with high anomaly rates!")


def example_6_corporate_actions():
    """Example 6: Corporate actions"""
    print("\n" + "=" * 60)
    print("Example 6: Corporate Actions")
    print("=" * 60)

    with QuestDBReader() as reader:
        print("\n1. Get all corporate actions for symbol:")
        df = reader.get_corporate_actions(
            symbol='RELIANCE',
            exchange='NSE',
            from_date='2023-01-01'
        )

        if not df.empty:
            print(f"   Found {len(df)} corporate actions")
            print(df[['timestamp', 'suspected_type', 'suspected_ratio', 'confidence', 'status']].head())
        else:
            print("   No corporate actions found")

        print("\n2. Get all pending corporate actions:")
        pending = reader.get_corporate_actions(status='pending')
        print(f"   Found {len(pending)} pending actions")


def example_7_raw_sql_queries():
    """Example 7: Custom SQL queries"""
    print("\n" + "=" * 60)
    print("Example 7: Custom SQL Queries")
    print("=" * 60)

    with QuestDBReader() as reader:
        print("\n1. Top 10 most active stocks by volume:")
        sql = """
        SELECT
            symbol,
            SUM(volume) as total_volume,
            AVG(volume) as avg_volume,
            COUNT(*) as trading_days
        FROM ohlcv_equity
        WHERE exchange = 'NSE'
            AND interval = 'day'
            AND timestamp > dateadd('d', -30, now())
        GROUP BY symbol
        ORDER BY total_volume DESC
        LIMIT 10
        """
        df = reader.execute_raw_query(sql)
        print(df.to_string(index=False))

        print("\n2. Daily market summary (last 5 days):")
        sql = """
        SELECT
            timestamp,
            COUNT(DISTINCT symbol) as symbols_traded,
            SUM(volume) as total_volume,
            AVG(close) as avg_close
        FROM ohlcv_equity
        WHERE exchange = 'NSE'
            AND interval = 'day'
            AND timestamp > dateadd('d', -5, now())
        GROUP BY timestamp
        ORDER BY timestamp DESC
        """
        df = reader.execute_raw_query(sql)
        print(df.to_string(index=False))


def example_8_integration_with_writer():
    """Example 8: Integration with writer"""
    print("\n" + "=" * 60)
    print("Example 8: Reader + Writer Integration")
    print("=" * 60)

    # Read data
    print("\n1. Read existing data:")
    reader = QuestDBReader()
    df = reader.get_equity_data('RELIANCE', 'NSE', 'day', limit=10)
    print(f"   Retrieved {len(df)} rows")
    reader.close()

    # Transform data (example: calculate indicators)
    if not df.empty:
        print("\n2. Transform data (calculate SMA):")
        df['sma_5'] = df['close'].rolling(window=5).mean()
        print(f"   Added SMA column")

        # You could write transformed data back or to another table
        print("\n3. Data ready for further processing or writing")
        print(df[['timestamp', 'symbol', 'close', 'sma_5']].tail())


def example_9_fundamental_data():
    """Example 9: Fundamental data queries"""
    print("\n" + "=" * 60)
    print("Example 9: Fundamental Data")
    print("=" * 60)

    with QuestDBReader() as reader:
        print("\n1. Get fundamental data:")
        df = reader.get_fundamental_data(
            symbol='RELIANCE',
            exchange='NSE',
            period_type='yearly',
            limit=5
        )

        if not df.empty:
            print(f"   Found {len(df)} records")
            print(f"   Columns: {len(df.columns)} financial metrics")
        else:
            print("   No fundamental data available yet")

        print("\n2. Get company info:")
        info = reader.get_company_info('RELIANCE', 'NSE')

        if info:
            print(f"   Company: {info.get('company_name', 'N/A')}")
            print(f"   Sector: {info.get('sector', 'N/A')}")
            print(f"   Market Cap: ₹{info.get('market_cap_mln', 0):,.0f}M")
        else:
            print("   No company info available yet")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("QuestDB Data Reader - Usage Examples")
    print("=" * 60)

    try:
        example_1_simple_queries()
        example_2_context_manager()
        example_3_batch_operations()
        example_4_filtering_and_analytics()
        example_5_data_quality()
        example_6_corporate_actions()
        example_7_raw_sql_queries()
        example_8_integration_with_writer()
        example_9_fundamental_data()

        print("\n" + "=" * 60)
        print("All Examples Complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

# QuestDB Data Reader

High-performance SQL-based data reader for QuestDB with seamless integration into the quest module ecosystem.

## Features

- **SQL-based querying** via HTTP API
- **Automatic DataFrame conversion** for easy analysis
- **Date range filtering** with flexible date input formats
- **Batch operations** for multiple symbols
- **Analytics and aggregations** (stats, correlations, trends)
- **Connection pooling** and query optimization
- **Corporate actions** and fundamental data queries
- **Data quality** summaries and anomaly detection
- **Raw SQL execution** for custom queries

## Installation

The data reader is part of the `quest` module. No separate installation required.

```python
from quest import QuestDBReader
```

## Quick Start

### Simple Queries

```python
from quest import get_equity_data, get_latest_candles

# Get latest 100 daily candles
df = get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)

# Get data for date range
df = get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')
```

### Using the Reader Class

```python
from quest import QuestDBReader

# Create reader instance
reader = QuestDBReader()

# Get equity data
df = reader.get_equity_data(
    symbol='RELIANCE',
    exchange='NSE',
    interval='day',
    from_date='2024-01-01',
    to_date='2024-12-31',
    exclude_anomalies=True
)

# Get statistics
stats = reader.get_symbol_stats('RELIANCE', 'NSE', 'day')
print(f"Total rows: {stats['row_count']}")
print(f"Price range: ₹{stats['price_range']['min']:.2f} - ₹{stats['price_range']['max']:.2f}")

# Close connection
reader.close()
```

### Context Manager (Recommended)

```python
from quest import QuestDBReader

# Auto-connect and close
with QuestDBReader() as reader:
    # Multiple queries using same connection
    symbols = reader.get_available_symbols('NSE', 'day')

    for symbol in symbols[:5]:
        df = reader.get_latest_candles(symbol, 'NSE', 'day', limit=50)
        print(f"{symbol}: {len(df)} candles")
```

## API Reference

### QuestDBReader Class

#### Core Methods

**`get_equity_data(symbol, exchange, interval, from_date=None, to_date=None, limit=None, adjusted=None, exclude_anomalies=False)`**

Get equity OHLCV data for a single symbol.

```python
df = reader.get_equity_data(
    symbol='RELIANCE',
    exchange='NSE',
    interval='day',
    from_date='2024-01-01',
    exclude_anomalies=True
)
```

**`get_equity_data_batch(symbols, exchange, interval, from_date=None, to_date=None, exclude_anomalies=False)`**

Get equity data for multiple symbols in one query.

```python
df = reader.get_equity_data_batch(
    symbols=['RELIANCE', 'TCS', 'INFY'],
    exchange='NSE',
    interval='day',
    from_date='2024-01-01'
)
```

**`get_latest_candles(symbol, exchange, interval, limit=100)`**

Get the most recent N candles for a symbol.

```python
df = reader.get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)
```

**`get_derivatives_data(symbol, exchange, interval, from_date=None, to_date=None, limit=None, exclude_anomalies=False)`**

Get derivatives OHLCV data (includes Open Interest).

```python
df = reader.get_derivatives_data(
    symbol='NIFTY24JANFUT',
    exchange='NFO',
    interval='15minute',
    from_date='2024-01-01'
)
```

#### Analytics Methods

**`get_symbol_stats(symbol, exchange, interval, from_date=None, to_date=None)`**

Get comprehensive statistics for a symbol.

```python
stats = reader.get_symbol_stats('RELIANCE', 'NSE', 'day')
# Returns: row_count, date_range, price_range, volume stats, anomaly_count
```

**`get_available_symbols(exchange=None, interval=None, min_rows=100)`**

Get list of symbols with available data.

```python
symbols = reader.get_available_symbols('NSE', 'day', min_rows=200)
```

**`get_date_range_for_symbol(symbol, exchange, interval)`**

Get the first and last date available for a symbol.

```python
date_range = reader.get_date_range_for_symbol('RELIANCE', 'NSE', 'day')
first_date, last_date = date_range
```

**`get_data_quality_summary(exchange=None, interval=None)`**

Get data quality metrics for all symbols.

```python
df = reader.get_data_quality_summary('NSE', 'day')
# Returns DataFrame with: symbol, total_rows, anomaly_count, anomaly_pct, etc.
```

#### Corporate Actions & Fundamentals

**`get_corporate_actions(symbol=None, exchange=None, from_date=None, to_date=None, action_type=None, status=None)`**

Query corporate actions data.

```python
df = reader.get_corporate_actions(
    symbol='RELIANCE',
    exchange='NSE',
    from_date='2023-01-01',
    status='verified'
)
```

**`get_fundamental_data(symbol, exchange, period_type=None, fiscal_year=None, limit=None)`**

Get fundamental data (balance sheet, income statement, cash flow).

```python
df = reader.get_fundamental_data(
    symbol='RELIANCE',
    exchange='NSE',
    period_type='yearly',
    fiscal_year=2024
)
```

**`get_company_info(symbol, exchange)`**

Get company information and metrics.

```python
info = reader.get_company_info('RELIANCE', 'NSE')
print(f"Company: {info['company_name']}")
print(f"Sector: {info['sector']}")
```

#### Utility Methods

**`execute_raw_query(sql)`**

Execute custom SQL query and return DataFrame.

```python
sql = """
SELECT symbol, COUNT(*) as count, AVG(close) as avg_price
FROM ohlcv_equity
WHERE exchange = 'NSE' AND interval = 'day'
GROUP BY symbol
ORDER BY count DESC
LIMIT 10
"""
df = reader.execute_raw_query(sql)
```

**`is_healthy()`**

Check if QuestDB connection is working.

```python
if reader.is_healthy():
    print("Connected!")
```

**`get_table_summary(table_name)`**

Get metadata about a table.

```python
info = reader.get_table_summary('ohlcv_equity')
```

### Convenience Functions

Quick access functions that auto-connect and close:

```python
from quest import (
    get_equity_data,
    get_latest_candles,
    get_symbol_stats,
    get_available_symbols
)

# One-liner queries
df = get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')
df = get_latest_candles('TCS', 'NSE', 'day', limit=100)
stats = get_symbol_stats('INFY', 'NSE', 'day')
symbols = get_available_symbols('NSE', 'day', min_rows=200)
```

## Usage Examples

### Example 1: Calculate Returns

```python
with QuestDBReader() as reader:
    df = reader.get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')

    # Calculate daily returns
    df['returns'] = df['close'].pct_change()
    df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1

    print(f"Daily return: {df['returns'].iloc[-1]*100:.2f}%")
    print(f"Total return: {df['cumulative_returns'].iloc[-1]*100:.2f}%")
    print(f"Volatility: {df['returns'].std()*100:.2f}%")
```

### Example 2: Multi-Symbol Analysis

```python
with QuestDBReader() as reader:
    # Get data for multiple stocks
    symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK']
    df = reader.get_equity_data_batch(
        symbols=symbols,
        exchange='NSE',
        interval='day',
        from_date='2024-01-01'
    )

    # Calculate correlation matrix
    pivot = df.pivot_table(index='timestamp', columns='symbol', values='close')
    corr_matrix = pivot.corr()
    print(corr_matrix)
```

### Example 3: Find High-Volume Days

```python
with QuestDBReader() as reader:
    # Custom SQL query
    sql = """
    SELECT timestamp, symbol, volume, close
    FROM ohlcv_equity
    WHERE exchange = 'NSE'
        AND interval = 'day'
        AND volume > (
            SELECT AVG(volume) * 2
            FROM ohlcv_equity
            WHERE symbol = 'RELIANCE'
        )
        AND symbol = 'RELIANCE'
    ORDER BY volume DESC
    LIMIT 10
    """

    high_volume_days = reader.execute_raw_query(sql)
    print(high_volume_days)
```

### Example 4: Data Quality Check

```python
with QuestDBReader() as reader:
    # Get quality summary
    quality = reader.get_data_quality_summary('NSE', 'day')

    # Find symbols with anomalies
    high_anomalies = quality[quality['anomaly_pct'] > 5.0]
    print(f"Symbols with >5% anomalies: {len(high_anomalies)}")

    # Check specific symbol
    stats = reader.get_symbol_stats('RELIANCE', 'NSE', 'day')
    print(f"Anomaly count: {stats['anomaly_count']}")
```

### Example 5: Integration with Writer

```python
from quest import QuestDBReader, QuestDBWriter

# Read data
with QuestDBReader() as reader:
    df = reader.get_equity_data('RELIANCE', 'NSE', 'day', limit=100)

# Transform data
df['sma_20'] = df['close'].rolling(window=20).mean()
df['signal'] = df['close'] > df['sma_20']

# Write back transformed data (to another table or system)
print(f"Generated {len(df)} signals")
```

## Date Handling

The reader accepts flexible date formats:

```python
# String dates (ISO format)
df = reader.get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')

# datetime objects
from datetime import datetime
df = reader.get_equity_data('RELIANCE', 'NSE', 'day', from_date=datetime(2024, 1, 1))

# date objects
from datetime import date
df = reader.get_equity_data('RELIANCE', 'NSE', 'day', from_date=date(2024, 1, 1))
```

All timestamps are automatically converted to UTC and returned as pandas datetime objects.

## Integration with Other Modules

### With Writer

```python
from quest import QuestDBReader, QuestDBWriter

reader = QuestDBReader()
writer = QuestDBWriter()

# Read, transform, write
df = reader.get_equity_data('RELIANCE', 'NSE', 'day')
# ... transform df ...
writer.write_equity_data(df)
```

### With Client

```python
from quest import QuestDBReader, QuestDBClient

# Reader uses client internally
reader = QuestDBReader()

# Or pass custom client
custom_client = QuestDBClient()
reader = QuestDBReader(config=custom_client.config)
```

### With Config

```python
from quest import QuestDBReader, CONNECTION_CONFIG, QuestDBConnectionConfig

# Use default config
reader = QuestDBReader()

# Or custom config
custom_config = QuestDBConnectionConfig(
    http_host='remote-host',
    http_port=9000,
    http_timeout=60
)
reader = QuestDBReader(config=custom_config)
```

## Performance Tips

1. **Use context managers** to reuse connections for multiple queries
2. **Use batch queries** (`get_equity_data_batch`) instead of multiple single queries
3. **Apply filters** at the database level (use `from_date`, `to_date`, `exclude_anomalies`)
4. **Limit results** with `limit` parameter when you don't need all data
5. **Use raw SQL** for complex aggregations instead of post-processing in pandas

## Error Handling

```python
from quest import QuestDBReader, QuestDBReadError

with QuestDBReader() as reader:
    try:
        df = reader.get_equity_data('RELIANCE', 'NSE', 'day')
    except QuestDBReadError as e:
        print(f"Query failed: {e}")
```

## Testing

Run the test suite:

```bash
python3 quest/test_reader.py
```

Run examples:

```bash
python3 quest/example_usage.py
```

## Architecture

```
QuestDBReader (data_reader.py)
    ↓
QuestDBClient (client.py) - HTTP API
    ↓
QuestDB HTTP Endpoint (localhost:9000)
```

The reader uses the HTTP API for queries (read-only operations). For writes, use `QuestDBWriter` which uses ILP protocol for high-performance inserts.

## Module Structure

```
quest/
├── __init__.py           # Package exports
├── client.py             # HTTP client (used by reader)
├── config.py             # Configuration and schemas
├── writer.py             # ILP writer (fast writes)
├── data_reader.py        # SQL reader (THIS MODULE)
├── table_functions.py    # Schema management
├── test_reader.py        # Test suite
├── example_usage.py      # Usage examples
└── README_DATA_READER.md # This file
```

## FAQ

**Q: Should I use the reader or client directly?**

A: Use `QuestDBReader` for data queries - it provides high-level methods with DataFrame output. Use `QuestDBClient` only for low-level operations or custom queries.

**Q: How do I handle large result sets?**

A: Use pagination with `LIMIT` and `OFFSET` in raw SQL queries, or use `from_date`/`to_date` filters to query data in chunks.

**Q: Can I query derivatives data?**

A: Yes! Use `get_derivatives_data()` which includes Open Interest (OI) column.

**Q: How are timestamps handled?**

A: All timestamps are stored in UTC (nanoseconds) and returned as pandas datetime objects in UTC timezone.

**Q: What if QuestDB is not running?**

A: Check connection with `reader.is_healthy()`. The reader will raise `QuestDBReadError` if queries fail.

## See Also

- [quest/writer.py](writer.py) - Fast ILP-based data writer
- [quest/client.py](client.py) - Low-level HTTP client
- [quest/config.py](config.py) - Configuration and schemas
- [quest/example_usage.py](example_usage.py) - Complete usage examples

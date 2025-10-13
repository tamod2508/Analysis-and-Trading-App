"""
QuestDB Data Reader - SQL-based querying for OHLCV and fundamental data

High-performance data reader using SQL queries:
- Equity and derivatives OHLCV data
- Corporate actions and fundamental data
- Advanced filtering (date ranges, symbols, intervals)
- Aggregations and time-series analytics
- Pandas DataFrame output for easy analysis
- Connection pooling and query optimization

Usage:
    reader = QuestDBReader()

    # Simple queries
    df = reader.get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')

    # Multiple symbols
    df = reader.get_equity_data_batch(['RELIANCE', 'TCS'], 'NSE', 'day')

    # Latest N candles
    df = reader.get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)

    # Date range analytics
    stats = reader.get_symbol_stats('RELIANCE', 'NSE', 'day', from_date='2024-01-01')

    # Check data availability
    available = reader.get_available_symbols('NSE', 'day')
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Union, Tuple
from datetime import datetime, date, timedelta
import pytz

from quest.config import (
    CONNECTION_CONFIG,
    TableNames,
    Exchanges,
    Intervals,
    QuestDBConnectionConfig,
)
from quest.client import QuestDBClient, QuestDBQueryError
from utils.logger import get_logger

logger = get_logger(__name__, 'questdb.log')


class QuestDBReadError(Exception):
    """Raised when read operation fails"""
    pass


class QuestDBReader:
    """
    High-level QuestDB reader for OHLCV and fundamental data

    Features:
    - SQL-based querying via HTTP API
    - Automatic DataFrame conversion
    - Date range filtering
    - Symbol and interval filtering
    - Aggregations and analytics
    - Connection pooling
    - Query optimization

    Usage:
        reader = QuestDBReader()

        # Get equity data
        df = reader.get_equity_data(
            symbol='RELIANCE',
            exchange='NSE',
            interval='day',
            from_date='2024-01-01',
            to_date='2024-12-31'
        )

        # Get derivatives data
        df = reader.get_derivatives_data(
            symbol='NIFTY24JANFUT',
            exchange='NFO',
            interval='15minute'
        )

        # Get latest candles
        df = reader.get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)

        # Get symbol statistics
        stats = reader.get_symbol_stats('RELIANCE', 'NSE', 'day')
    """

    def __init__(self, config: Optional[QuestDBConnectionConfig] = None):
        """
        Initialize QuestDB reader

        Args:
            config: Optional connection config (defaults to CONNECTION_CONFIG)
        """
        self.config = config or CONNECTION_CONFIG
        self.client = QuestDBClient(self.config)
        self._cache: Dict[str, pd.DataFrame] = {}

        logger.info("QuestDBReader initialized")

    def get_equity_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[Union[str, datetime, date]] = None,
        to_date: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = None,
        adjusted: Optional[bool] = None,
        exclude_anomalies: bool = False
    ) -> pd.DataFrame:
        """
        Get equity OHLCV data for a single symbol

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
            exchange: Exchange ('NSE' or 'BSE')
            interval: Time interval ('day', '15minute', etc.)
            from_date: Start date (inclusive) - str, datetime, or date
            to_date: End date (inclusive) - str, datetime, or date
            limit: Max number of rows to return (default: None - all rows)
            adjusted: Filter by adjusted data (True/False/None for all)
            exclude_anomalies: Exclude rows marked as anomalies

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, etc.

        Example:
            df = reader.get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')
        """
        table = TableNames.OHLCV_EQUITY

        # Build WHERE clause
        where_clauses = [
            f"symbol = '{self._escape_sql_string(symbol)}'",
            f"exchange = '{self._escape_sql_string(exchange)}'",
            f"interval = '{self._escape_sql_string(interval)}'"
        ]

        # Date filters
        if from_date:
            from_ts = self._parse_date_to_timestamp(from_date)
            where_clauses.append(f"timestamp >= {from_ts}")

        if to_date:
            to_ts = self._parse_date_to_timestamp(to_date, end_of_day=True)
            where_clauses.append(f"timestamp <= {to_ts}")

        # Additional filters
        if adjusted is not None:
            where_clauses.append(f"adjusted = {str(adjusted).lower()}")

        if exclude_anomalies:
            where_clauses.append("is_anomaly = false")

        where_sql = " AND ".join(where_clauses)

        # Build query
        sql = f"""
        SELECT
            timestamp,
            exchange,
            symbol,
            interval,
            open,
            high,
            low,
            close,
            volume,
            is_anomaly,
            adjusted,
            data_source
        FROM {table}
        WHERE {where_sql}
        ORDER BY timestamp ASC
        """

        if limit:
            sql += f" LIMIT {limit}"

        return self._execute_query_to_dataframe(sql)

    def get_equity_data_batch(
        self,
        symbols: List[str],
        exchange: str,
        interval: str,
        from_date: Optional[Union[str, datetime, date]] = None,
        to_date: Optional[Union[str, datetime, date]] = None,
        exclude_anomalies: bool = False
    ) -> pd.DataFrame:
        """
        Get equity OHLCV data for multiple symbols

        Args:
            symbols: List of symbols (e.g., ['RELIANCE', 'TCS', 'INFY'])
            exchange: Exchange ('NSE' or 'BSE')
            interval: Time interval
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            exclude_anomalies: Exclude anomalies

        Returns:
            DataFrame with data for all symbols

        Example:
            df = reader.get_equity_data_batch(['RELIANCE', 'TCS'], 'NSE', 'day')
        """
        table = TableNames.OHLCV_EQUITY

        if not symbols:
            # no symbols requested -> return empty dataframe (or raise ValueError)
            return pd.DataFrame()

        # Build symbol list for IN clause (escape each symbol)
        symbols_list = "', '".join([self._escape_sql_string(s) for s in symbols])

        where_clauses = [
            f"symbol IN ('{symbols_list}')",
            f"exchange = '{self._escape_sql_string(exchange)}'",
            f"interval = '{self._escape_sql_string(interval)}'"
        ]

        # Date filters
        if from_date:
            from_ts = self._parse_date_to_timestamp(from_date)
            where_clauses.append(f"timestamp >= {from_ts}")

        if to_date:
            to_ts = self._parse_date_to_timestamp(to_date, end_of_day=True)
            where_clauses.append(f"timestamp <= {to_ts}")

        if exclude_anomalies:
            where_clauses.append("is_anomaly = false")

        where_sql = " AND ".join(where_clauses)

        sql = f"""
        SELECT
            timestamp,
            exchange,
            symbol,
            interval,
            open,
            high,
            low,
            close,
            volume,
            is_anomaly,
            adjusted,
            data_source
        FROM {table}
        WHERE {where_sql}
        ORDER BY symbol, timestamp ASC
        """

        return self._execute_query_to_dataframe(sql)

    def get_latest_candles(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get the latest N candles for a symbol

        Args:
            symbol: Stock symbol
            exchange: Exchange
            interval: Time interval
            limit: Number of latest candles to retrieve (default: 100)

        Returns:
            DataFrame with latest candles (sorted oldest to newest)

        Example:
            # Get last 100 daily candles
            df = reader.get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)
        """
        table = TableNames.OHLCV_EQUITY

        sql = f"""
        SELECT
            timestamp,
            exchange,
            symbol,
            interval,
            open,
            high,
            low,
            close,
            volume,
            is_anomaly,
            adjusted
        FROM {table}
        WHERE symbol = '{self._escape_sql_string(symbol)}'
            AND exchange = '{self._escape_sql_string(exchange)}'
            AND interval = '{self._escape_sql_string(interval)}'
        ORDER BY timestamp DESC
        LIMIT {limit}
        """

        # Get data and reverse order (oldest to newest)
        df = self._execute_query_to_dataframe(sql)

        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)

        return df

    # =========================================================================
    # DERIVATIVES DATA QUERIES
    # =========================================================================

    def get_derivatives_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[Union[str, datetime, date]] = None,
        to_date: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = None,
        exclude_anomalies: bool = False
    ) -> pd.DataFrame:
        """
        Get derivatives OHLCV data (includes Open Interest)

        Args:
            symbol: Contract symbol (e.g., 'NIFTY24JANFUT')
            exchange: Exchange ('NFO' or 'BFO')
            interval: Time interval
            from_date: Start date
            to_date: End date
            limit: Max rows
            exclude_anomalies: Exclude anomalies

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, oi, etc.
        """
        table = TableNames.OHLCV_DERIVATIVES

        where_clauses = [
            f"symbol = '{self._escape_sql_string(symbol)}'",
            f"exchange = '{self._escape_sql_string(exchange)}'",
            f"interval = '{self._escape_sql_string(interval)}'"
        ]

        if from_date:
            from_ts = self._parse_date_to_timestamp(from_date)
            where_clauses.append(f"timestamp >= {from_ts}")

        if to_date:
            to_ts = self._parse_date_to_timestamp(to_date, end_of_day=True)
            where_clauses.append(f"timestamp <= {to_ts}")

        if exclude_anomalies:
            where_clauses.append("is_anomaly = false")

        where_sql = " AND ".join(where_clauses)

        sql = f"""
        SELECT
            timestamp,
            exchange,
            symbol,
            interval,
            open,
            high,
            low,
            close,
            volume,
            oi,
            is_anomaly,
            adjusted,
            data_source
        FROM {table}
        WHERE {where_sql}
        ORDER BY timestamp ASC
        """

        if limit:
            sql += f" LIMIT {limit}"

        return self._execute_query_to_dataframe(sql)

    # =========================================================================
    # ANALYTICS AND AGGREGATIONS
    # =========================================================================

    def get_symbol_stats(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: Optional[Union[str, datetime, date]] = None,
        to_date: Optional[Union[str, datetime, date]] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a symbol (count, min, max, avg, etc.)

        Args:
            symbol: Stock symbol
            exchange: Exchange
            interval: Time interval
            from_date: Start date
            to_date: End date

        Returns:
            Dict with statistics:
            {
                'symbol': str,
                'exchange': str,
                'interval': str,
                'row_count': int,
                'date_range': {'first': datetime, 'last': datetime},
                'price_range': {'min': float, 'max': float, 'avg': float},
                'volume': {'total': int, 'avg': int, 'max': int},
                'anomaly_count': int
            }
        """
        table = TableNames.OHLCV_EQUITY

        where_clauses = [
            f"symbol = '{self._escape_sql_string(symbol)}'",
            f"exchange = '{self._escape_sql_string(exchange)}'",
            f"interval = '{self._escape_sql_string(interval)}'"
        ]

        if from_date:
            from_ts = self._parse_date_to_timestamp(from_date)
            where_clauses.append(f"timestamp >= {from_ts}")

        if to_date:
            to_ts = self._parse_date_to_timestamp(to_date, end_of_day=True)
            where_clauses.append(f"timestamp <= {to_ts}")

        where_sql = " AND ".join(where_clauses)

        sql = f"""
        SELECT
            COUNT(*) as row_count,
            MIN(timestamp) as first_date,
            MAX(timestamp) as last_date,
            MIN(low) as min_price,
            MAX(high) as max_price,
            AVG(close) as avg_price,
            SUM(volume) as total_volume,
            AVG(volume) as avg_volume,
            MAX(volume) as max_volume,
            SUM(CAST(is_anomaly AS INT)) as anomaly_count
        FROM {table}
        WHERE {where_sql}
        """

        result = self.client.query(sql)

        if not result.get('dataset') or len(result['dataset']) == 0:
            return {
                'symbol': symbol,
                'exchange': exchange,
                'interval': interval,
                'row_count': 0,
                'error': 'No data found'
            }

        row = result['dataset'][0]
        columns = [col['name'] for col in result['columns']]

        # Map columns to values
        data = dict(zip(columns, row))

        stats = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'row_count': data.get('row_count', 0),
            'date_range': {
                'first': self._parse_timestamp(data.get('first_date')),
                'last': self._parse_timestamp(data.get('last_date'))
            },
            'price_range': {
                'min': data.get('min_price'),
                'max': data.get('max_price'),
                'avg': data.get('avg_price')
            },
            'volume': {
                'total': data.get('total_volume'),
                'avg': data.get('avg_volume'),
                'max': data.get('max_volume')
            },
            'anomaly_count': data.get('anomaly_count', 0)
        }

        return stats

    def get_available_symbols(
        self,
        exchange: Optional[str] = None,
        interval: Optional[str] = None,
        min_rows: int = 100
    ) -> List[str]:
        """
        Get list of available symbols with data

        Args:
            exchange: Filter by exchange (None for all)
            interval: Filter by interval (None for all)
            min_rows: Minimum number of rows required (default: 100)

        Returns:
            List of symbols

        Example:
            symbols = reader.get_available_symbols('NSE', 'day', min_rows=200)
        """
        table = TableNames.OHLCV_EQUITY

        where_clauses = []

        if exchange:
            where_clauses.append(f"exchange = '{self._escape_sql_string(exchange)}'")

        if interval:
            where_clauses.append(f"interval = '{self._escape_sql_string(interval)}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        sql = f"""
        SELECT symbol, COUNT(*) as row_count
        FROM {table}
        {where_sql}
        GROUP BY symbol
        HAVING COUNT(*) >= {min_rows}
        ORDER BY symbol
        """

        result = self.client.query(sql)
        symbols = [row[0] for row in result.get('dataset', [])]

        logger.info(f"Found {len(symbols)} symbols with at least {min_rows} rows")
        return symbols

    def get_date_range_for_symbol(
        self,
        symbol: str,
        exchange: str,
        interval: str
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the date range (first and last timestamp) for a symbol

        Args:
            symbol: Stock symbol
            exchange: Exchange
            interval: Time interval

        Returns:
            Tuple of (first_date, last_date) or None if no data
        """
        table = TableNames.OHLCV_EQUITY

        sql = f"""
        SELECT
            MIN(timestamp) as first_date,
            MAX(timestamp) as last_date
        FROM {table}
        WHERE symbol = '{self._escape_sql_string(symbol)}'
            AND exchange = '{self._escape_sql_string(exchange)}'
            AND interval = '{self._escape_sql_string(interval)}'
        """

        result = self.client.query(sql)

        if not result.get('dataset') or len(result['dataset']) == 0:
            return None

        row = result['dataset'][0]
        first_date = self._parse_timestamp(row[0])
        last_date = self._parse_timestamp(row[1])

        if first_date and last_date:
            return (first_date, last_date)

        return None

    # =========================================================================
    # CORPORATE ACTIONS
    # =========================================================================

    def get_corporate_actions(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        from_date: Optional[Union[str, datetime, date]] = None,
        to_date: Optional[Union[str, datetime, date]] = None,
        action_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get corporate actions data

        Args:
            symbol: Filter by symbol (None for all)
            exchange: Filter by exchange
            from_date: Start date
            to_date: End date
            action_type: Filter by action type ('split', 'bonus', 'dividend')
            status: Filter by status ('pending', 'verified', 'rejected')

        Returns:
            DataFrame with corporate actions
        """
        table = TableNames.CORPORATE_ACTIONS

        where_clauses = []

        if symbol:
            where_clauses.append(f"symbol = '{self._escape_sql_string(symbol)}'")

        if exchange:
            where_clauses.append(f"exchange = '{self._escape_sql_string(exchange)}'")

        if from_date:
            from_ts = self._parse_date_to_timestamp(from_date)
            where_clauses.append(f"timestamp >= {from_ts}")

        if to_date:
            to_ts = self._parse_date_to_timestamp(to_date, end_of_day=True)
            where_clauses.append(f"timestamp <= {to_ts}")

        if action_type:
            where_clauses.append(f"suspected_type = '{self._escape_sql_string(action_type)}'")

        if status:
            where_clauses.append(f"status = '{self._escape_sql_string(status)}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        sql = f"""
        SELECT *
        FROM {table}
        {where_sql}
        ORDER BY timestamp DESC
        """

        return self._execute_query_to_dataframe(sql)

    # =========================================================================
    # DATA VALIDATION & QUALITY
    # =========================================================================

    def get_data_quality_summary(
        self,
        exchange: Optional[str] = None,
        interval: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get data quality summary (anomaly counts, validation status)

        Args:
            exchange: Filter by exchange
            interval: Filter by interval

        Returns:
            DataFrame with quality metrics per symbol
        """
        table = TableNames.OHLCV_EQUITY

        where_clauses = []

        if exchange:
            where_clauses.append(f"exchange = '{self._escape_sql_string(exchange)}'")

        if interval:
            where_clauses.append(f"interval = '{self._escape_sql_string(interval)}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        sql = f"""
        SELECT
            symbol,
            exchange,
            interval,
            COUNT(*) as total_rows,
            SUM(CAST(is_anomaly AS INT)) as anomaly_count,
            (SUM(CAST(is_anomaly AS INT)) * 100.0 / COUNT(*)) as anomaly_pct,
            SUM(CAST(adjusted AS INT)) as adjusted_count,
            MIN(timestamp) as first_date,
            MAX(timestamp) as last_date
        FROM {table}
        {where_sql}
        GROUP BY symbol, exchange, interval
        ORDER BY symbol
        """

        return self._execute_query_to_dataframe(sql)

    # =========================================================================
    # FUNDAMENTAL DATA QUERIES
    # =========================================================================

    def get_fundamental_data(
        self,
        symbol: str,
        exchange: str,
        period_type: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get fundamental data (balance sheet, income statement, cash flow)

        Args:
            symbol: Stock symbol
            exchange: Exchange
            period_type: Filter by period type ('yearly', 'quarterly', None for all)
            fiscal_year: Filter by fiscal year (e.g., 2024)
            limit: Max rows to return

        Returns:
            DataFrame with fundamental data
        """
        table = TableNames.FUNDAMENTAL_DATA

        where_clauses = [
            f"symbol = '{self._escape_sql_string(symbol)}'",
            f"exchange = '{self._escape_sql_string(exchange)}'"
        ]

        if period_type:
            where_clauses.append(f"period_type = '{self._escape_sql_string(period_type)}'")

        if fiscal_year:
            where_clauses.append(f"fiscal_year = {fiscal_year}")

        where_sql = " AND ".join(where_clauses)

        sql = f"""
        SELECT *
        FROM {table}
        WHERE {where_sql}
        ORDER BY timestamp DESC
        """

        if limit:
            sql += f" LIMIT {limit}"

        return self._execute_query_to_dataframe(sql)

    def get_company_info(
        self,
        symbol: str,
        exchange: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get company information

        Args:
            symbol: Stock symbol
            exchange: Exchange

        Returns:
            Dict with company info or None if not found
        """
        table = TableNames.COMPANY_INFO

        sql = f"""
        SELECT *
        FROM {table}
        WHERE symbol = '{self._escape_sql_string(symbol)}'
            AND exchange = '{self._escape_sql_string(exchange)}'
        ORDER BY timestamp DESC
        LIMIT 1
        """

        df = self._execute_query_to_dataframe(sql)

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _execute_query_to_dataframe(self, sql: str) -> pd.DataFrame:
        """
        Execute SQL query and convert result to DataFrame

        Args:
            sql: SQL query string

        Returns:
            pandas DataFrame
        """
        try:
            result = self.client.query(sql)

            if not result.get('dataset'):
                return pd.DataFrame()

            # Get column names
            columns = [col['name'] for col in result['columns']]

            # Create DataFrame
            df = pd.DataFrame(result['dataset'], columns=columns)

            # Convert timestamp columns to datetime
            for col in df.columns:
                if 'timestamp' in col.lower() or col in ['timestamp', 'date']:
                    try:
                        df[col] = pd.to_datetime(df[col], unit='ns', utc=True)
                    except Exception:
                        pass  # Skip if conversion fails

            logger.debug(f"Query returned {len(df)} rows")
            return df

        except QuestDBQueryError as e:
            logger.error(f"Query failed: {e}")
            raise QuestDBReadError(f"Query failed: {e}")

    def _parse_date_to_timestamp(
        self,
        date_input: Union[str, datetime, date],
        end_of_day: bool = False
    ) -> int:
        """
        Parse date input to nanosecond timestamp (UTC)

        Args:
            date_input: Date as string, datetime, or date object
            end_of_day: If True, set time to 23:59:59.999999

        Returns:
            Timestamp in nanoseconds (UTC)
        """
        if isinstance(date_input, str):
            dt = pd.to_datetime(date_input)
        elif isinstance(date_input, datetime):
            dt = date_input
        elif isinstance(date_input, date):
            dt = datetime.combine(date_input, datetime.min.time())
        else:
            raise ValueError(f"Invalid date type: {type(date_input)}")

        # Ensure timezone-aware (default to UTC if naive)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        else:
            dt = dt.astimezone(pytz.UTC)

        # Set to end of day if requested
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Convert to nanoseconds
        timestamp_ns = int(dt.timestamp() * 1_000_000_000)
        return timestamp_ns

    def _parse_timestamp(self, timestamp_ns: Optional[int]) -> Optional[datetime]:
        """
        Parse nanosecond timestamp to datetime (UTC)

        Args:
            timestamp_ns: Timestamp in nanoseconds

        Returns:
            datetime object (UTC) or None
        """
        if timestamp_ns is None:
            return None

        try:
            dt = pd.to_datetime(timestamp_ns, unit='ns', utc=True)
            return dt.to_pydatetime()
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp_ns}: {e}")
            return None

    def _escape_sql_string(self, value: Optional[str]) -> str:
        """
        Escape string for safe SQL usage (prevents SQL injection).
        - Returns the escaped string (does NOT add surrounding single quotes).
        - Example: "O'REILLY" -> "O''REILLY"
        """
        if value is None:
            raise ValueError("None passed to _escape_sql_string; caller must handle NULLs explicitly")
        return str(value).replace("'", "''")

    def execute_raw_query(self, sql: str) -> pd.DataFrame:
        """
        Execute raw SQL query and return DataFrame

        Args:
            sql: Raw SQL query string

        Returns:
            DataFrame with query results

        Example:
            df = reader.execute_raw_query(
                "SELECT symbol, COUNT(*) as count FROM ohlcv_equity GROUP BY symbol"
            )
        """
        return self._execute_query_to_dataframe(sql)

    def get_table_summary(self, table_name: str) -> Dict[str, Any]:
        """
        Get summary information for a table

        Args:
            table_name: Name of table

        Returns:
            Dict with table info
        """
        return self.client.get_table_info(table_name)

    def is_healthy(self) -> bool:
        """
        Check if QuestDB connection is healthy

        Returns:
            True if connected and responding
        """
        return self.client.is_healthy()

    def close(self):
        """Close the connection"""
        self.client.close()
        logger.debug("QuestDBReader closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def get_equity_data(
    symbol: str,
    exchange: str,
    interval: str,
    from_date: Optional[Union[str, datetime, date]] = None,
    to_date: Optional[Union[str, datetime, date]] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience function to get equity data in one call

    Args:
        symbol: Stock symbol
        exchange: Exchange
        interval: Time interval
        from_date: Start date
        to_date: End date
        limit: Max rows

    Returns:
        DataFrame with equity data

    Example:
        df = get_equity_data('RELIANCE', 'NSE', 'day', from_date='2024-01-01')
    """
    with QuestDBReader() as reader:
        return reader.get_equity_data(symbol, exchange, interval, from_date, to_date, limit)


def get_latest_candles(
    symbol: str,
    exchange: str,
    interval: str,
    limit: int = 100
) -> pd.DataFrame:
    """
    Convenience function to get latest candles

    Args:
        symbol: Stock symbol
        exchange: Exchange
        interval: Time interval
        limit: Number of candles

    Returns:
        DataFrame with latest candles

    Example:
        df = get_latest_candles('RELIANCE', 'NSE', 'day', limit=100)
    """
    with QuestDBReader() as reader:
        return reader.get_latest_candles(symbol, exchange, interval, limit)


def get_symbol_stats(
    symbol: str,
    exchange: str,
    interval: str,
    from_date: Optional[Union[str, datetime, date]] = None,
    to_date: Optional[Union[str, datetime, date]] = None
) -> Dict[str, Any]:
    """
    Convenience function to get symbol statistics

    Args:
        symbol: Stock symbol
        exchange: Exchange
        interval: Time interval
        from_date: Start date
        to_date: End date

    Returns:
        Dict with statistics

    Example:
        stats = get_symbol_stats('RELIANCE', 'NSE', 'day')
    """
    with QuestDBReader() as reader:
        return reader.get_symbol_stats(symbol, exchange, interval, from_date, to_date)


def get_available_symbols(
    exchange: Optional[str] = None,
    interval: Optional[str] = None,
    min_rows: int = 100
) -> List[str]:
    """
    Convenience function to get available symbols

    Args:
        exchange: Filter by exchange
        interval: Filter by interval
        min_rows: Minimum rows required

    Returns:
        List of symbols

    Example:
        symbols = get_available_symbols('NSE', 'day', min_rows=200)
    """
    with QuestDBReader() as reader:
        return reader.get_available_symbols(exchange, interval, min_rows)


__all__ = [
    'QuestDBReader',
    'QuestDBReadError',
    'get_equity_data',
    'get_latest_candles',
    'get_symbol_stats',
    'get_available_symbols',
]

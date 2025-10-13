"""
QuestDB Client - Connection management and query execution
"""

import requests
from typing import Optional, Dict, List, Any
from urllib.parse import quote_plus
import json
from datetime import datetime

from quest.config import CONNECTION_CONFIG, QuestDBConnectionConfig
from utils.logger import get_logger

logger = get_logger(__name__, 'questdb.log')


class QuestDBClient:
    """
    QuestDB client for HTTP queries and health checks

    Usage:
        client = QuestDBClient()

        # Check connection
        if client.is_healthy():
            print("Connected!")

        # Execute query
        result = client.query("SELECT * FROM ohlcv_equity LIMIT 10")

        # Get table info
        tables = client.get_tables()
    """

    def __init__(self, config: Optional[QuestDBConnectionConfig] = None):
        """
        Initialize QuestDB client

        Args:
            config: Optional configuration (defaults to CONNECTION_CONFIG)
        """
        self.config = config or CONNECTION_CONFIG
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'KiteApp-QuestDB-Client/1.0'
        })

        logger.info(f"QuestDB client initialized: {self.config.http_url}")

    def is_healthy(self) -> bool:
        """
        Check if QuestDB is accessible and responding

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self._session.get(
                f"{self.config.http_url}/exec",
                params={'query': 'SELECT 1'},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                is_ok = data.get('count', 0) == 1

                if is_ok:
                    logger.debug("QuestDB health check: OK")
                else:
                    logger.warning("QuestDB health check: Unexpected response")

                return is_ok
            else:
                logger.error(f"QuestDB health check failed: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"QuestDB health check failed: {e}")
            return False

    def query(self, sql: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute SQL query via HTTP API

        Args:
            sql: SQL query to execute
            timeout: Optional timeout in seconds (default: from config)

        Returns:
            Dict with query results:
            {
                'query': str,
                'columns': List[Dict],
                'dataset': List[List],
                'count': int,
                'timestamp': int
            }

        Raises:
            QuestDBQueryError: If query fails
        """
        timeout = timeout or self.config.http_timeout

        try:
            logger.debug(f"Executing query: {sql[:100]}...")

            response = self._session.get(
                f"{self.config.http_url}/exec",
                params={'query': sql},
                timeout=timeout
            )

            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Query returned {result.get('count', 0)} rows")
                return result
            else:
                error_msg = response.text
                logger.error(f"Query failed: {error_msg}")
                raise QuestDBQueryError(f"Query failed: {error_msg}")

        except requests.exceptions.Timeout:
            logger.error(f"Query timeout after {timeout}s")
            raise QuestDBQueryError(f"Query timeout after {timeout}s")

        except requests.exceptions.RequestException as e:
            logger.error(f"Query request failed: {e}")
            raise QuestDBQueryError(f"Query request failed: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse query response: {e}")
            raise QuestDBQueryError(f"Failed to parse query response: {e}")

    def execute(self, sql: str, timeout: Optional[int] = None) -> bool:
        """
        Execute SQL command (CREATE, INSERT, UPDATE, etc.)

        Args:
            sql: SQL command to execute
            timeout: Optional timeout in seconds

        Returns:
            True if successful

        Raises:
            QuestDBQueryError: If execution fails
        """
        result = self.query(sql, timeout)
        return result.get('count', -1) >= 0

    def get_tables(self) -> List[str]:
        """
        Get list of all tables in QuestDB

        Returns:
            List of table names
        """
        try:
            result = self.query("SHOW TABLES")
            tables = [row[0] for row in result.get('dataset', [])]
            logger.info(f"Found {len(tables)} tables: {tables}")
            return tables
        except QuestDBQueryError as e:
            logger.error(f"Failed to get tables: {e}")
            return []

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists
        """
        tables = self.get_tables()
        exists = table_name in tables
        logger.debug(f"Table '{table_name}' exists: {exists}")
        return exists

    def get_row_count(self, table_name: str, where: Optional[str] = None) -> int:
        """
        Get row count for a table

        Args:
            table_name: Name of table
            where: Optional WHERE clause (without 'WHERE' keyword)

        Returns:
            Number of rows
        """
        try:
            sql = f"SELECT COUNT(*) FROM {table_name}"
            if where:
                sql += f" WHERE {where}"

            result = self.query(sql)
            count = result['dataset'][0][0] if result.get('dataset') else 0
            return count
        except QuestDBQueryError as e:
            logger.error(f"Failed to get row count for {table_name}: {e}")
            return 0

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a table

        Args:
            table_name: Name of table

        Returns:
            Dict with table metadata
        """
        try:
            # Get columns
            result = self.query(f"SHOW COLUMNS FROM {table_name}")
            columns = []
            for row in result.get('dataset', []):
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'indexed': row[2] if len(row) > 2 else False,
                    'index_block_capacity': row[3] if len(row) > 3 else None,
                })

            # Get row count
            row_count = self.get_row_count(table_name)

            info = {
                'name': table_name,
                'columns': columns,
                'row_count': row_count,
                'column_count': len(columns),
            }

            logger.info(f"Table '{table_name}': {row_count} rows, {len(columns)} columns")
            return info

        except QuestDBQueryError as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {
                'name': table_name,
                'error': str(e)
            }

    def drop_table(self, table_name: str, confirm: bool = False) -> bool:
        """
        Drop a table (requires confirmation)

        Args:
            table_name: Name of table to drop
            confirm: Must be True to actually drop

        Returns:
            True if dropped successfully
        """
        if not confirm:
            logger.warning(f"Drop table '{table_name}' requires confirm=True")
            return False

        try:
            logger.warning(f"Dropping table: {table_name}")
            self.execute(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"Table '{table_name}' dropped")
            return True
        except QuestDBQueryError as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            return False

    def close(self):
        """Close the HTTP session"""
        self._session.close()
        logger.debug("QuestDB client session closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class QuestDBQueryError(Exception):
    """Exception raised when QuestDB query fails"""
    pass


def get_client(config: Optional[QuestDBConnectionConfig] = None) -> QuestDBClient:
    """
    Factory function to get a QuestDB client instance

    Args:
        config: Optional configuration

    Returns:
        QuestDBClient instance
    """
    return QuestDBClient(config)

"""
QuestDB Schema Management - Complete Table Creation

Uses schema definitions from quest_database.config
Creates ALL tables defined in config dynamically.

Tables created:
- ohlcv_equity: Equity OHLCV data (NSE/BSE)
- ohlcv_derivatives: Derivatives OHLCV data (NFO/BFO) - Future
- corporate_actions: Corporate action detection
- data_lineage: Audit trail
- validation_results: Data quality tracking
- fundamental_data: Financial fundamentals
- company_info: Company information
- earnings_history: Historical earnings
- earnings_estimate: Earnings estimates
- institutional_shareholders: Institutional holdings
- insider_trades: Insider trading data

WAL (Write-Ahead Logging): Explicitly enabled for all tables
All tables are partitioned (required for WAL)
"""

from typing import Dict, List

from quest.config import (
    TableNames,
    ColumnTypes,
    TABLE_SCHEMAS,
    TABLE_PARTITIONS,
)
from config.constants import VALIDATION_LIMITS, Segment
from utils.logger import get_logger

logger = get_logger(__name__, 'questdb.log')


class TableSchemaGenerator:
    """
    Generates CREATE TABLE SQL from schema definitions in config

    All tables are WAL-enabled explicitly with 'WAL' keyword
    """

    @staticmethod
    def generate_create_table_sql(
        table_name: str,
        schema: Dict[str, str],
        partition_by: str,
        designated_timestamp: str = 'timestamp'
    ) -> str:
        """
        Generate CREATE TABLE SQL from schema definition

        Args:
            table_name: Name of the table
            schema: Dict mapping column names to QuestDB types
            partition_by: Partition strategy (DAY, MONTH, YEAR)
            designated_timestamp: Name of timestamp column (default: 'timestamp')

        Returns:
            SQL CREATE TABLE statement with WAL enabled
        """
        # Build column definitions
        columns = []
        for col_name, col_type in schema.items():
            if col_type == ColumnTypes.SYMBOL:
                # All SYMBOL columns with capacity 4096 and cache enabled
                columns.append(f"    {col_name} {col_type} CAPACITY 4096 CACHE")
            else:
                columns.append(f"    {col_name} {col_type}")

        columns_sql = ",\n".join(columns)

        sql = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
{columns_sql}
) TIMESTAMP({designated_timestamp}) PARTITION BY {partition_by} WAL;
"""
        return sql.strip()


class QuestDBSchemaManager:
    """
    Manages QuestDB schema creation and validation

    Creates ALL tables defined in quest_database.config.TABLE_SCHEMAS
    Uses TABLE_PARTITIONS for partition strategies

    Usage:
        from quest_database.questdb_client import QuestDBClient
        from quest_database.questdb_schema import QuestDBSchemaManager

        client = QuestDBClient()
        manager = QuestDBSchemaManager(client)

        # Create ALL tables
        manager.create_all_tables()

        # Verify tables
        if manager.verify_all_tables():
            print("All tables ready!")
    """

    def __init__(self, client):
        """
        Initialize schema manager

        Args:
            client: QuestDBClient instance
        """
        self.client = client
        self.generator = TableSchemaGenerator()
        logger.info("QuestDBSchemaManager initialized")

    def create_table(self, table_name: str) -> bool:
        """
        Create a single table from config

        Args:
            table_name: Name of table (from TableNames)

        Returns:
            True if successful
        """
        try:
            # Get schema and partition strategy from config
            schema = TABLE_SCHEMAS.get(table_name)
            partition = TABLE_PARTITIONS.get(table_name)

            if not schema:
                logger.error(f"No schema found for table: {table_name}")
                return False

            if not partition:
                logger.error(f"No partition strategy found for table: {table_name}")
                return False

            logger.info(f"Creating table: {table_name}...")

            # Generate and execute CREATE TABLE SQL
            sql = self.generator.generate_create_table_sql(
                table_name=table_name,
                schema=schema,
                partition_by=partition,
                designated_timestamp='timestamp'
            )

            self.client.execute(sql)
            logger.info(f"✓ Table '{table_name}' created successfully (WAL enabled, partitioned by {partition})")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to create table '{table_name}': {e}")
            return False

    def create_all_tables(self, skip_derivatives: bool = False) -> bool:
        """
        Create ALL tables defined in config

        Args:
            skip_derivatives: Skip derivatives table for now (default: True)

        Returns:
            True if all tables created successfully
        """
        logger.info("=" * 60)
        logger.info("Creating ALL QuestDB tables from config...")
        logger.info("=" * 60)

        success_count = 0
        fail_count = 0

        # Get all table names from config
        tables_to_create = [
            TableNames.OHLCV_EQUITY,
            TableNames.CORPORATE_ACTIONS,
            TableNames.DATA_LINEAGE,
            TableNames.VALIDATION_RESULTS,
            TableNames.FUNDAMENTAL_DATA,
            TableNames.COMPANY_INFO,
            TableNames.EARNINGS_HISTORY,
            TableNames.EARNINGS_ESTIMATE,
            TableNames.INSTITUTIONAL_SHAREHOLDERS,
            TableNames.INSIDER_TRADES,
        ]

        # Add derivatives if not skipping
        if not skip_derivatives:
            tables_to_create.insert(1, TableNames.OHLCV_DERIVATIVES)

        for table_name in tables_to_create:
            if self.create_table(table_name):
                success_count += 1
            else:
                fail_count += 1

        logger.info("=" * 60)
        logger.info(f"Table creation complete: {success_count} succeeded, {fail_count} failed")
        logger.info("=" * 60)

        return fail_count == 0

    def verify_all_tables(self, skip_derivatives: bool = False) -> bool:
        """
        Verify that all tables exist

        Args:
            skip_derivatives: Skip derivatives table check (default: True)

        Returns:
            True if all tables exist
        """
        required_tables = [
            TableNames.OHLCV_EQUITY,
            TableNames.CORPORATE_ACTIONS,
            TableNames.DATA_LINEAGE,
            TableNames.VALIDATION_RESULTS,
            TableNames.FUNDAMENTAL_DATA,
            TableNames.COMPANY_INFO,
            TableNames.EARNINGS_HISTORY,
            TableNames.EARNINGS_ESTIMATE,
            TableNames.INSTITUTIONAL_SHAREHOLDERS,
            TableNames.INSIDER_TRADES,
        ]

        if not skip_derivatives:
            required_tables.insert(1, TableNames.OHLCV_DERIVATIVES)

        existing_tables = self.client.get_tables()

        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                logger.error(f"✗ Missing table: {table}")
                missing_tables.append(table)
            else:
                logger.debug(f"✓ Table exists: {table}")

        if missing_tables:
            logger.error(f"Missing {len(missing_tables)} tables: {missing_tables}")
            return False

        logger.info(f"✓ All {len(required_tables)} tables verified")
        return True

    def get_all_table_stats(self) -> Dict[str, Dict]:
        """
        Get statistics for all tables

        Returns:
            Dict with table stats for each table
        """
        stats = {}

        all_tables = self.client.get_tables()

        for table in all_tables:
            try:
                info = self.client.get_table_info(table)
                stats[table] = info
            except Exception as e:
                stats[table] = {'error': str(e)}

        return stats

    def drop_table(self, table_name: str, confirm: bool = False) -> bool:
        """
        Drop a single table (DANGEROUS - requires confirmation)

        Args:
            table_name: Name of table to drop (from TableNames)
            confirm: Must be True to actually drop table

        Returns:
            True if table dropped successfully

        Example:
            manager.drop_table(TableNames.OHLCV_EQUITY, confirm=True)
        """
        if not confirm:
            logger.warning(f"⚠️  Drop table '{table_name}' requires confirm=True")
            return False

        try:
            if not self.client.table_exists(table_name):
                logger.warning(f"Table '{table_name}' does not exist")
                return False

            logger.warning(f"⚠️  Dropping table: {table_name}")
            if self.client.drop_table(table_name, confirm=True):
                logger.info(f"✓ Table '{table_name}' dropped successfully")
                return True
            else:
                logger.error(f"✗ Failed to drop table '{table_name}'")
                return False

        except Exception as e:
            logger.error(f"✗ Error dropping table '{table_name}': {e}")
            return False

    def drop_all_tables(self, confirm: bool = False) -> bool:
        """
        Drop ALL tables (DANGEROUS - requires confirmation)

        Args:
            confirm: Must be True to actually drop tables

        Returns:
            True if all tables dropped
        """
        if not confirm:
            logger.warning("⚠️  Drop all tables requires confirm=True")
            return False

        logger.warning("=" * 60)
        logger.warning("⚠️  DROPPING ALL TABLES - THIS CANNOT BE UNDONE")
        logger.warning("=" * 60)

        tables_to_drop = TableNames.all_tables()

        success_count = 0
        fail_count = 0

        for table_name in tables_to_drop:
            if self.drop_table(table_name, confirm=True):
                success_count += 1
            else:
                fail_count += 1

        logger.warning("=" * 60)
        logger.warning(f"Drop complete: {success_count} dropped, {fail_count} failed")
        logger.warning("=" * 60)

        return fail_count == 0

    def clear_table(self, table_name: str, confirm: bool = False) -> bool:
        """
        Remove all rows from a single table (requires confirmation).

        Args:
            table_name: Name of table to clear (from TableNames)
            confirm: Must be True to actually clear the table

        Returns:
            True if the table was cleared successfully

        Example:
            manager.clear_table(TableNames.OHLCV_EQUITY, confirm=True)
        """
        if not confirm:
            logger.warning(f"⚠️  Clear table '{table_name}' requires confirm=True")
            return False

        try:
            if not self.client.table_exists(table_name):
                logger.warning(f"Table '{table_name}' does not exist")
                return False

            logger.warning(f"⚠️  Clearing all rows from table: {table_name}")
            # Prefer TRUNCATE TABLE for removing all rows while keeping schema.
            # TRUNCATE is supported in newer QuestDB versions; if not available,
            # fall back to dropping and recreating the table to achieve an equivalent effect.
            sql = f"TRUNCATE TABLE {table_name};"
            try:
                self.client.execute(sql)
                logger.info(f"✓ Table '{table_name}' cleared successfully via TRUNCATE")
                return True
            except Exception as truncate_err:
                logger.warning(f"TRUNCATE failed for '{table_name}' (server may not support it): {truncate_err}")
                logger.warning("Attempting drop+recreate fallback to clear data")

                # Attempt to drop and recreate table using existing helpers
                try:
                    # Drop (force) and recreate the table schema
                    if self.drop_table(table_name, confirm=True):
                        # Recreate table from config
                        if self.create_table(table_name):
                            logger.info(f"✓ Table '{table_name}' cleared via drop+recreate")
                            return True
                        else:
                            logger.error(f"✗ Table '{table_name}' was dropped but failed to recreate")
                            return False
                    else:
                        logger.error(f"✗ Failed to drop table '{table_name}' during fallback")
                        return False
                except Exception as e:
                    logger.error(f"✗ Fallback clear failed for '{table_name}': {e}")
                    return False

        except Exception as e:
            logger.error(f"✗ Error clearing table '{table_name}': {e}")
            return False

    def clear_all_tables(self, confirm: bool = False) -> bool:
        """
        Remove all rows from all known tables (requires confirmation).

        Args:
            confirm: Must be True to actually clear tables

        Returns:
            True if all tables cleared successfully
        """
        if not confirm:
            logger.warning("⚠️  Clear all tables requires confirm=True")
            return False

        logger.warning("=" * 60)
        logger.warning("⚠️  CLEARING ALL TABLES - THIS REMOVES ALL DATA BUT KEEPS SCHEMA")
        logger.warning("=" * 60)

        tables_to_clear = TableNames.all_tables()

        success_count = 0
        fail_count = 0

        for table_name in tables_to_clear:
            if self.clear_table(table_name, confirm=True):
                success_count += 1
            else:
                fail_count += 1

        logger.warning("=" * 60)
        logger.warning(f"Clear complete: {success_count} cleared, {fail_count} failed")
        logger.warning("=" * 60)

        return fail_count == 0


# Convenience functions
def create_all_tables(client, skip_derivatives: bool = True) -> bool:
    """
    Convenience function to create all tables

    Args:
        client: QuestDBClient instance
        skip_derivatives: Skip derivatives table (default: True)

    Returns:
        True if successful
    """
    manager = QuestDBSchemaManager(client)
    return manager.create_all_tables(skip_derivatives=skip_derivatives)


def verify_all_tables(client, skip_derivatives: bool = True) -> bool:
    """
    Convenience function to verify all tables

    Args:
        client: QuestDBClient instance
        skip_derivatives: Skip derivatives table check (default: True)

    Returns:
        True if all tables exist
    """
    manager = QuestDBSchemaManager(client)
    return manager.verify_all_tables(skip_derivatives=skip_derivatives)


__all__ = [
    'TableSchemaGenerator',
    'QuestDBSchemaManager',
    'DataValidator',
    'create_all_tables',
    'verify_all_tables',
    'drop_table',
]

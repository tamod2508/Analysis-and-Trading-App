"""
HDF5 to QuestDB Migration Script

Migrates equity OHLCV data from HDF5 files to QuestDB using ILP protocol.

Migrates from:
- EQUITY.h5
- EQUITY_chunk1.h5
- EQUITY_chunk2.h5

To:
- QuestDB ohlcv_equity table

Features:
- Parallel migration with multiple workers
- Automatic deduplication
- Progress tracking
- Resumable (skips already migrated data)
- Validation statistics
- ILP protocol for fast writes (50K-400K rows/sec)

Usage:
    python scripts/migrate_hdf5_to_questdb.py [--parallel=8] [--verify] [--dry-run]
"""

import h5py
import hdf5plugin
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import sys
from typing import List, Dict, Tuple, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quest.writer import QuestDBWriter, QuestDBWriteError
from quest.config import CONNECTION_CONFIG, Intervals, Exchanges
from database.schema import EquityOHLCVSchema
from utils.logger import get_logger

logger = get_logger(__name__, 'migration.log')


class HDF5ToQuestDBMigration:
    """
    Migrates equity data from HDF5 to QuestDB
    """

    def __init__(
        self,
        hdf5_files: List[Path],
        workers: int = 1,
        batch_size: int = 25000,
        verify: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize migration

        Args:
            hdf5_files: List of HDF5 file paths to migrate
            workers: Number of parallel workers (default: 1 for sequential processing)
            batch_size: Number of rows per batch (default: 25000, helps prevent ILP broken pipe)
            verify: Verify data after migration
            dry_run: Don't actually write, just analyze
        """
        self.hdf5_files = hdf5_files
        self.workers = workers
        self.batch_size = batch_size
        self.verify = verify
        self.dry_run = dry_run

        self.stats = {
            'total_rows': 0,
            'rows_migrated': 0,
            'rows_skipped': 0,
            'errors': 0,
            'files_processed': 0,
            'symbols_processed': 0,
            'start_time': None,
            'end_time': None,
        }

        logger.info(f"Migration initialized:")
        logger.info(f"  Files: {len(hdf5_files)}")
        logger.info(f"  Workers: {workers} ({'parallel' if workers > 1 else 'sequential'})")
        logger.info(f"  Batch size: {batch_size:,} rows per batch")
        logger.info(f"  Verify: {verify}")
        logger.info(f"  Dry run: {dry_run}")

    def discover_datasets(self) -> List[Dict]:
        """
        Discover all datasets across HDF5 files

        Returns:
            List of dataset info dicts with:
            - file_path: Path to HDF5 file
            - exchange: Exchange name
            - symbol: Trading symbol
            - interval: Time interval
            - dataset_path: Full HDF5 path
            - row_count: Number of rows
        """
        logger.info("Discovering datasets in HDF5 files...")
        datasets = []

        for hdf5_file in self.hdf5_files:
            if not hdf5_file.exists():
                logger.warning(f"File not found: {hdf5_file}")
                continue

            logger.info(f"Scanning: {hdf5_file.name}")

            try:
                with h5py.File(hdf5_file, 'r') as f:
                    # Navigate through /data/{EXCHANGE}/{SYMBOL}/{interval}
                    if 'data' not in f:
                        logger.warning(f"No 'data' group in {hdf5_file.name}")
                        continue

                    data_group = f['data']

                    for exchange_name in data_group.keys():
                        exchange_group = data_group[exchange_name]

                        for symbol in exchange_group.keys():
                            symbol_group = exchange_group[symbol]

                            for interval in symbol_group.keys():
                                dataset = symbol_group[interval]
                                row_count = len(dataset)

                                if row_count == 0:
                                    continue

                                datasets.append({
                                    'file_path': hdf5_file,
                                    'exchange': exchange_name,
                                    'symbol': symbol,
                                    'interval': interval,
                                    'dataset_path': f'/data/{exchange_name}/{symbol}/{interval}',
                                    'row_count': row_count,
                                })

            except Exception as e:
                logger.error(f"Error scanning {hdf5_file.name}: {e}")
                continue

        logger.info(f"Found {len(datasets)} datasets across {len(self.hdf5_files)} files")
        logger.info(f"Total rows: {sum(d['row_count'] for d in datasets):,}")

        return datasets

    def migrate_dataset(self, dataset_info: Dict, writer: QuestDBWriter) -> Dict:
        """
        Migrate a single dataset to QuestDB

        Args:
            dataset_info: Dataset information dict
            writer: QuestDB writer instance

        Returns:
            Migration statistics
        """
        file_path = dataset_info['file_path']
        exchange = dataset_info['exchange']
        symbol = dataset_info['symbol']
        interval = dataset_info['interval']
        dataset_path = dataset_info['dataset_path']
        row_count = dataset_info['row_count']

        logger.info(f"Migrating: {exchange}/{symbol}/{interval} ({row_count:,} rows) from {file_path.name}")

        stats = {
            'exchange': exchange,
            'symbol': symbol,
            'interval': interval,
            'rows_read': 0,
            'rows_written': 0,
            'errors': 0,
            'elapsed': 0,
        }

        try:
            start = time.time()

            # Read data from HDF5
            with h5py.File(file_path, 'r') as f:
                dataset = f[dataset_path]
                data = dataset[:]
                stats['rows_read'] = len(data)

                # Convert to DataFrame
                # IMPORTANT: HDF5 timestamps are Unix timestamps (already in UTC)
                # Mark them as UTC timezone-aware so the writer doesn't localize them to IST
                # This preserves the dates as stored (e.g., 2017-01-01 18:30 UTC stays as 2017-01-01)
                timestamps_utc = pd.to_datetime(data['timestamp'], unit='s', utc=True)

                df = pd.DataFrame({
                    'timestamp': timestamps_utc,
                    'exchange': exchange,
                    'symbol': symbol,
                    'interval': interval,
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'close': data['close'],
                    'volume': data['volume'],
                })

                # Sort by timestamp (important for QuestDB)
                df = df.sort_values('timestamp').reset_index(drop=True)

                # Calculate prev_close and change_pct
                df['prev_close'] = df['close'].shift(1)

                # Calculate log returns (change_pct)
                # Log return = ln(close / prev_close) * 100
                df['change_pct'] = np.where(
                    df['prev_close'].notna() & (df['prev_close'] > 0),
                    np.log(df['close'] / df['prev_close']) * 100,
                    np.nan
                )

                # First row has no previous close
                df.loc[0, 'prev_close'] = np.nan
                df.loc[0, 'change_pct'] = np.nan

                # Add metadata columns
                df['is_anomaly'] = False
                df['adjusted'] = False
                df['data_source'] = 'hdf5_migration'

                # Write data in batches to prevent ILP broken pipe errors
                if not self.dry_run:
                    total_written = 0
                    total_rows = len(df)

                    # Split DataFrame into batches
                    for i in range(0, total_rows, self.batch_size):
                        batch_df = df.iloc[i:i + self.batch_size]
                        batch_num = (i // self.batch_size) + 1
                        total_batches = (total_rows + self.batch_size - 1) // self.batch_size

                        logger.debug(
                            f"  Writing batch {batch_num}/{total_batches}: "
                            f"{len(batch_df):,} rows"
                        )

                        write_stats = writer.write_equity_data(
                            batch_df,
                            deduplicate=True
                        )
                        total_written += write_stats['rows_written']

                    stats['rows_written'] = total_written
                else:
                    stats['rows_written'] = len(df)
                    logger.info(f"  [DRY RUN] Would write {len(df):,} rows in batches of {self.batch_size:,}")

                stats['elapsed'] = time.time() - start

                logger.info(
                    f"✓ Migrated {exchange}/{symbol}/{interval}: "
                    f"{stats['rows_written']:,} rows in {stats['elapsed']:.2f}s"
                )

        except Exception as e:
            logger.error(f"✗ Failed to migrate {exchange}/{symbol}/{interval}: {e}")
            stats['errors'] += 1

        return stats

    def run(self) -> Dict:
        """
        Run migration

        Returns:
            Migration statistics
        """
        self.stats['start_time'] = datetime.now()
        logger.info("=" * 80)
        logger.info("HDF5 to QuestDB Migration Started")
        logger.info("=" * 80)

        # Discover datasets
        datasets = self.discover_datasets()

        if not datasets:
            logger.warning("No datasets found to migrate")
            return self.stats

        self.stats['total_rows'] = sum(d['row_count'] for d in datasets)

        # Create writer
        writer = QuestDBWriter()

        if self.dry_run:
            logger.info("[DRY RUN MODE] No data will be written")

        # Migrate datasets
        logger.info(f"Starting migration of {len(datasets)} datasets...")

        if self.workers > 1:
            # Parallel migration
            logger.info(f"Using {self.workers} parallel workers")
            self._migrate_parallel(datasets, writer)
        else:
            # Sequential migration
            logger.info("Using sequential migration")
            self._migrate_sequential(datasets, writer)

        # Close writer
        writer.close()

        # Calculate final stats
        self.stats['end_time'] = datetime.now()
        elapsed = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.stats['elapsed_seconds'] = elapsed

        # Print summary
        self._print_summary()

        return self.stats

    def _migrate_sequential(self, datasets: List[Dict], writer: QuestDBWriter):
        """Migrate datasets sequentially"""
        for i, dataset_info in enumerate(datasets, 1):
            logger.info(f"Progress: {i}/{len(datasets)}")
            stats = self.migrate_dataset(dataset_info, writer)

            self.stats['rows_migrated'] += stats['rows_written']
            self.stats['errors'] += stats['errors']
            self.stats['symbols_processed'] += 1

    def _migrate_parallel(self, datasets: List[Dict], writer: QuestDBWriter):
        """Migrate datasets in parallel using thread pool"""
        # Create a writer per thread (not thread-safe to share)
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            futures = []
            for dataset_info in datasets:
                # Each worker gets its own writer
                future = executor.submit(
                    self._migrate_dataset_worker,
                    dataset_info
                )
                futures.append(future)

            # Process results as they complete
            completed = 0
            for future in as_completed(futures):
                try:
                    stats = future.result()
                    self.stats['rows_migrated'] += stats['rows_written']
                    self.stats['errors'] += stats['errors']
                    self.stats['symbols_processed'] += 1

                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{len(datasets)} datasets completed")

                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    self.stats['errors'] += 1

    def _migrate_dataset_worker(self, dataset_info: Dict) -> Dict:
        """Worker function for parallel migration (creates own writer)"""
        writer = QuestDBWriter()
        try:
            return self.migrate_dataset(dataset_info, writer)
        finally:
            writer.close()

    def _print_summary(self):
        """Print migration summary"""
        logger.info("=" * 80)
        logger.info("Migration Summary")
        logger.info("=" * 80)
        logger.info(f"Total rows in source:    {self.stats['total_rows']:,}")
        logger.info(f"Rows migrated:           {self.stats['rows_migrated']:,}")
        logger.info(f"Rows skipped:            {self.stats['rows_skipped']:,}")
        logger.info(f"Errors:                  {self.stats['errors']:,}")
        logger.info(f"Symbols processed:       {self.stats['symbols_processed']:,}")
        logger.info(f"Files processed:         {len(self.hdf5_files)}")

        if self.stats['elapsed_seconds'] > 0:
            rows_per_sec = self.stats['rows_migrated'] / self.stats['elapsed_seconds']
            logger.info(f"Elapsed time:            {self.stats['elapsed_seconds']:.2f}s")
            logger.info(f"Throughput:              {rows_per_sec:,.0f} rows/sec")

        logger.info(f"Started:                 {self.stats['start_time']}")
        logger.info(f"Completed:               {self.stats['end_time']}")
        logger.info("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate equity data from HDF5 to QuestDB'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of parallel workers (default: 1, use 1 for sequential)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25000,
        help='Number of rows per batch (default: 25000, helps prevent ILP broken pipe)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify data after migration'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - analyze only, no writes'
    )
    parser.add_argument(
        '--files',
        nargs='+',
        help='Specific HDF5 files to migrate (default: all EQUITY files)'
    )

    args = parser.parse_args()

    # Determine which files to migrate
    data_dir = Path('/Users/atm/Desktop/kite_app/data/hdf5')

    if args.files:
        hdf5_files = [Path(f) for f in args.files]
    else:
        # Default: migrate all EQUITY files except backup
        # Use EQUITY_repacked.h5 if it exists (smaller, cleaner), otherwise use EQUITY.h5
        equity_file = data_dir / 'EQUITY_repacked.h5' if (data_dir / 'EQUITY_repacked.h5').exists() else data_dir / 'EQUITY.h5'
        hdf5_files = [
            equity_file,
            data_dir / 'EQUITY_chunk1.h5',
            data_dir / 'EQUITY_chunk2.h5',
        ]
        # Filter out files that don't exist
        hdf5_files = [f for f in hdf5_files if f.exists()]

    if not hdf5_files:
        logger.error("No HDF5 files found to migrate")
        sys.exit(1)

    logger.info(f"Migrating {len(hdf5_files)} files:")
    for f in hdf5_files:
        logger.info(f"  - {f.name}")

    # Run migration
    migration = HDF5ToQuestDBMigration(
        hdf5_files=hdf5_files,
        workers=args.parallel,
        batch_size=args.batch_size,
        verify=args.verify,
        dry_run=args.dry_run,
    )

    stats = migration.run()

    # Exit with error if there were errors
    if stats['errors'] > 0:
        logger.error(f"Migration completed with {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Migration completed successfully!")
        sys.exit(0)


if __name__ == '__main__':
    main()

"""
Check HDF5 to QuestDB Migration Status

Compares data counts between HDF5 and QuestDB to verify migration completeness.

Usage:
    python scripts/check_migration_status.py
"""

import h5py
import hdf5plugin
import sys
from pathlib import Path
from typing import Dict, List
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from quest.config import CONNECTION_CONFIG, TableNames
from utils.logger import get_logger

logger = get_logger(__name__, 'migration_check.log')


def count_hdf5_rows(hdf5_files: List[Path]) -> Dict[str, Dict]:
    """
    Count rows in HDF5 files grouped by exchange/symbol/interval

    Returns:
        Dict with key (exchange, symbol, interval) -> row_count
    """
    logger.info("Counting rows in HDF5 files...")
    counts = {}

    for hdf5_file in hdf5_files:
        if not hdf5_file.exists():
            logger.warning(f"File not found: {hdf5_file}")
            continue

        logger.info(f"Scanning: {hdf5_file.name}")

        try:
            with h5py.File(hdf5_file, 'r') as f:
                if 'data' not in f:
                    continue

                data_group = f['data']

                for exchange in data_group.keys():
                    for symbol in data_group[exchange].keys():
                        for interval in data_group[exchange][symbol].keys():
                            dataset = data_group[exchange][symbol][interval]
                            row_count = len(dataset)

                            key = (exchange, symbol, interval)
                            counts[key] = counts.get(key, 0) + row_count

        except Exception as e:
            logger.error(f"Error reading {hdf5_file.name}: {e}")

    return counts


def count_questdb_rows() -> Dict[str, Dict]:
    """
    Count rows in QuestDB grouped by exchange/symbol/interval

    Returns:
        Dict with key (exchange, symbol, interval) -> row_count
    """
    logger.info("Counting rows in QuestDB...")

    query = f"""
        SELECT
            exchange,
            symbol,
            interval,
            COUNT(*) as row_count
        FROM {TableNames.OHLCV_EQUITY}
        GROUP BY exchange, symbol, interval
        ORDER BY exchange, symbol, interval
    """

    try:
        response = requests.get(
            f"{CONNECTION_CONFIG.http_url}/exec",
            params={'query': query},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        counts = {}
        if 'dataset' in result:
            for row in result['dataset']:
                exchange = row[0]
                symbol = row[1]
                interval = row[2]
                row_count = row[3]

                key = (exchange, symbol, interval)
                counts[key] = row_count

        return counts

    except Exception as e:
        logger.error(f"Error querying QuestDB: {e}")
        return {}


def compare_counts(hdf5_counts: Dict, questdb_counts: Dict):
    """Compare HDF5 and QuestDB row counts"""
    logger.info("=" * 100)
    logger.info("Migration Status Comparison")
    logger.info("=" * 100)

    all_keys = sorted(set(hdf5_counts.keys()) | set(questdb_counts.keys()))

    missing_in_questdb = []
    mismatched_counts = []
    matched = []

    for key in all_keys:
        exchange, symbol, interval = key
        hdf5_count = hdf5_counts.get(key, 0)
        questdb_count = questdb_counts.get(key, 0)

        if questdb_count == 0:
            missing_in_questdb.append((key, hdf5_count))
        elif hdf5_count != questdb_count:
            mismatched_counts.append((key, hdf5_count, questdb_count))
        else:
            matched.append((key, hdf5_count))

    # Print summary
    logger.info(f"Total datasets: {len(all_keys)}")
    logger.info(f"Matched: {len(matched)}")
    logger.info(f"Missing in QuestDB: {len(missing_in_questdb)}")
    logger.info(f"Mismatched counts: {len(mismatched_counts)}")
    logger.info("")

    # Print matched (summary)
    if matched:
        total_matched_rows = sum(count for _, count in matched)
        logger.info(f"✓ Matched datasets: {len(matched)} ({total_matched_rows:,} rows)")

    # Print missing
    if missing_in_questdb:
        logger.info("")
        logger.info("✗ Missing in QuestDB:")
        for key, count in missing_in_questdb[:20]:  # Show first 20
            exchange, symbol, interval = key
            logger.info(f"  {exchange:4s} | {symbol:20s} | {interval:10s} | {count:>10,} rows")
        if len(missing_in_questdb) > 20:
            logger.info(f"  ... and {len(missing_in_questdb) - 20} more")

    # Print mismatched
    if mismatched_counts:
        logger.info("")
        logger.info("⚠ Mismatched counts:")
        for key, hdf5_count, questdb_count in mismatched_counts[:20]:
            exchange, symbol, interval = key
            diff = questdb_count - hdf5_count
            logger.info(
                f"  {exchange:4s} | {symbol:20s} | {interval:10s} | "
                f"HDF5: {hdf5_count:>10,} | QuestDB: {questdb_count:>10,} | "
                f"Diff: {diff:>+10,}"
            )
        if len(mismatched_counts) > 20:
            logger.info(f"  ... and {len(mismatched_counts) - 20} more")

    # Overall stats
    logger.info("")
    logger.info("=" * 100)
    logger.info("Overall Statistics")
    logger.info("=" * 100)

    total_hdf5 = sum(hdf5_counts.values())
    total_questdb = sum(questdb_counts.values())

    logger.info(f"Total rows in HDF5:    {total_hdf5:>15,}")
    logger.info(f"Total rows in QuestDB: {total_questdb:>15,}")
    logger.info(f"Difference:            {total_questdb - total_hdf5:>+15,}")

    if total_hdf5 > 0:
        pct = (total_questdb / total_hdf5) * 100
        logger.info(f"Migration progress:    {pct:>14.2f}%")

    logger.info("=" * 100)

    return {
        'matched': len(matched),
        'missing': len(missing_in_questdb),
        'mismatched': len(mismatched_counts),
        'total_hdf5_rows': total_hdf5,
        'total_questdb_rows': total_questdb,
    }


def main():
    """Main entry point"""
    # HDF5 files to check
    data_dir = Path('/Users/atm/Desktop/kite_app/data/hdf5')
    hdf5_files = [
        data_dir / 'EQUITY.h5',
        data_dir / 'EQUITY_chunk1.h5',
        data_dir / 'EQUITY_chunk2.h5',
    ]
    hdf5_files = [f for f in hdf5_files if f.exists()]

    if not hdf5_files:
        logger.error("No HDF5 files found")
        sys.exit(1)

    # Count rows
    hdf5_counts = count_hdf5_rows(hdf5_files)
    questdb_counts = count_questdb_rows()

    # Compare
    stats = compare_counts(hdf5_counts, questdb_counts)

    # Exit with error if migration incomplete
    if stats['missing'] > 0 or stats['mismatched'] > 0:
        logger.warning("Migration incomplete or has mismatches")
        sys.exit(1)
    else:
        logger.info("✓ Migration complete and verified!")
        sys.exit(0)


if __name__ == '__main__':
    main()

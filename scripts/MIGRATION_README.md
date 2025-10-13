# HDF5 to QuestDB Migration Guide

This guide covers migrating equity OHLCV data from HDF5 files to QuestDB.

## Overview

**Source Files:**
- `EQUITY.h5` (7.3 GB)
- `EQUITY_chunk1.h5` (683 MB)
- `EQUITY_chunk2.h5` (646 MB)

**Destination:**
- QuestDB `ohlcv_equity` table

**Migration Method:**
- ILP (InfluxDB Line Protocol) for maximum speed
- Parallel processing with configurable workers
- Automatic deduplication
- Resumable (can restart if interrupted)

## Prerequisites

1. **QuestDB running:**
   ```bash
   # Check if QuestDB is running
   curl -s "http://localhost:9000/exec?query=SELECT+1"
   ```

2. **Python dependencies installed:**
   ```bash
   pip install h5py hdf5plugin pandas numpy requests pytz
   ```

## Migration Steps

### Step 1: Dry Run (Recommended)

First, run in dry-run mode to analyze the data without writing:

```bash
python scripts/migrate_hdf5_to_questdb.py --dry-run
```

This will:
- Scan all HDF5 files
- Count rows and datasets
- Show what would be migrated
- Estimate time needed

### Step 2: Run Migration

Run the actual migration with parallel workers:

```bash
# Default: 8 workers, 50K batch size
python scripts/migrate_hdf5_to_questdb.py

# Custom settings
python scripts/migrate_hdf5_to_questdb.py --parallel=12 --batch-size=100000
```

**Options:**
- `--parallel=N` - Number of parallel workers (default: 8)
- `--batch-size=N` - Rows per batch (default: 50000)
- `--verify` - Verify data after migration
- `--dry-run` - Analyze only, no writes
- `--files FILE1 FILE2` - Migrate specific files only

**Expected Performance:**
- Throughput: 50,000 - 400,000 rows/sec (depends on system)
- Total time: ~10-30 minutes for ~8.7 GB of data

### Step 3: Verify Migration

Check migration completeness:

```bash
python scripts/check_migration_status.py
```

This will:
- Count rows in HDF5 files
- Count rows in QuestDB
- Compare counts by exchange/symbol/interval
- Report any missing or mismatched data

## Migration Strategy

### Parallel Processing

The script uses thread-based parallelism:
- Each worker processes a different dataset (exchange/symbol/interval)
- Workers create their own QuestDB writer instances
- Progress is logged in real-time

**Recommended worker counts:**
- 8 workers: Good for most systems
- 12-16 workers: For high-performance systems
- 4 workers: For resource-constrained systems

### Deduplication

The writer automatically deduplicates rows based on:
- `(timestamp, exchange, symbol, interval)` - unique key

This handles:
- Overlapping data between chunk files
- Duplicate rows within the same file
- Re-running migration (idempotent)

### Resumability

The migration is **idempotent** - you can safely re-run it:
- QuestDB deduplicates on write (keeps latest)
- Partial migrations can be resumed
- No need to clear existing data first

## Monitoring

### Real-time Progress

The script logs:
- Datasets discovered
- Progress: X/Y datasets completed
- Per-dataset statistics (rows/sec)
- Overall throughput

### Check QuestDB Stats

While migration is running:

```bash
# Count rows in QuestDB
curl -s "http://localhost:9000/exec?query=SELECT+COUNT(*)+FROM+ohlcv_equity"

# Count unique symbols
curl -s "http://localhost:9000/exec?query=SELECT+COUNT(DISTINCT+symbol)+FROM+ohlcv_equity"

# Check recent writes
curl -s "http://localhost:9000/exec?query=SELECT+*+FROM+ohlcv_equity+LIMIT+10"
```

## Troubleshooting

### Connection Refused

If you see "Connection refused" errors:

```bash
# Check if QuestDB is running
curl -s "http://localhost:9000/exec?query=SELECT+1"

# Start QuestDB if not running
brew services start questdb
# OR
questdb start
```

### Out of Memory

If migration fails with OOM:

1. Reduce batch size:
   ```bash
   python scripts/migrate_hdf5_to_questdb.py --batch-size=25000
   ```

2. Reduce workers:
   ```bash
   python scripts/migrate_hdf5_to_questdb.py --parallel=4
   ```

### Slow Performance

If migration is slow (<10K rows/sec):

1. Check QuestDB write performance:
   - Ensure QuestDB has enough disk I/O
   - Check QuestDB logs for errors

2. Increase workers (if CPU is low):
   ```bash
   python scripts/migrate_hdf5_to_questdb.py --parallel=16
   ```

3. Check network latency (if QuestDB is remote)

### Mismatched Counts

If verification shows mismatched counts:

1. Check for duplicates in HDF5:
   - HDF5 may have duplicate timestamps
   - QuestDB deduplicates automatically

2. Check QuestDB deduplication:
   ```sql
   SELECT timestamp, exchange, symbol, interval, COUNT(*)
   FROM ohlcv_equity
   GROUP BY timestamp, exchange, symbol, interval
   HAVING COUNT(*) > 1
   ```

## Post-Migration

### Validate Data Quality

Run validation checks:

```python
from quest.validator import QuestDBValidator

validator = QuestDBValidator()
results = validator.validate_equity_data(
    exchange='NSE',
    symbol='RELIANCE',
    interval='day'
)
```

### Create Indexes (Optional)

QuestDB automatically indexes:
- `timestamp` (designated timestamp)
- `exchange`, `symbol`, `interval` (SYMBOL type)

No additional indexes needed for most queries.

### Backup

Create a backup after successful migration:

```bash
# Stop QuestDB
brew services stop questdb

# Backup data directory
cp -r /opt/homebrew/var/questdb/db /path/to/backup/

# Restart QuestDB
brew services start questdb
```

## Examples

### Migrate Only One File

```bash
python scripts/migrate_hdf5_to_questdb.py \
    --files /Users/atm/Desktop/kite_app/data/hdf5/EQUITY.h5
```

### Fast Migration (High-Performance System)

```bash
python scripts/migrate_hdf5_to_questdb.py \
    --parallel=16 \
    --batch-size=100000
```

### Careful Migration (Low Resources)

```bash
python scripts/migrate_hdf5_to_questdb.py \
    --parallel=2 \
    --batch-size=10000
```

### Verify Only

```bash
python scripts/check_migration_status.py
```

## Data Mapping

### HDF5 Schema → QuestDB Schema

| HDF5 Column | QuestDB Column | Type | Notes |
|-------------|----------------|------|-------|
| `timestamp` | `timestamp` | TIMESTAMP | Unix epoch → QuestDB timestamp |
| `open` | `open` | DOUBLE | |
| `high` | `high` | DOUBLE | |
| `low` | `low` | DOUBLE | |
| `close` | `close` | DOUBLE | |
| `volume` | `volume` | LONG | |
| N/A | `exchange` | SYMBOL | From HDF5 path |
| N/A | `symbol` | SYMBOL | From HDF5 path |
| N/A | `interval` | SYMBOL | From HDF5 path |
| N/A | `is_anomaly` | BOOLEAN | Default: false |
| N/A | `adjusted` | BOOLEAN | Default: false |
| N/A | `data_source` | SYMBOL | 'hdf5_migration' |

### Timezone Handling

- **HDF5**: Timestamps are Unix epoch (UTC)
- **QuestDB**: Timestamps stored as UTC
- **IST Conversion**: Done automatically by writer for intraday data

## FAQ

**Q: Can I run multiple migrations in parallel?**
A: No, run one migration at a time to avoid conflicts.

**Q: What happens if I stop migration mid-way?**
A: You can safely restart - it will continue from where it left off (idempotent).

**Q: Will this delete existing QuestDB data?**
A: No, it only adds/updates data. Duplicates are handled automatically.

**Q: How long will it take?**
A: Typically 10-30 minutes for ~8.7 GB (277M rows) at 50K-400K rows/sec.

**Q: Can I migrate while the app is running?**
A: Yes, QuestDB supports concurrent reads/writes.

## Support

For issues or questions:
1. Check logs: `logs/migration.log`
2. Check QuestDB logs: `/opt/homebrew/var/questdb/log/`
3. Run in dry-run mode to debug
4. Check this README's troubleshooting section

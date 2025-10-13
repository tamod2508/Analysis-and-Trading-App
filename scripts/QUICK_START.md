# Quick Start: HDF5 to QuestDB Migration

## TL;DR

Migrate 233.5M rows from 3 HDF5 files to QuestDB in ~15-30 minutes.

## Run Migration

```bash
cd /Users/atm/Desktop/kite_app

# 1. Make sure QuestDB is running
curl -s "http://localhost:9000/exec?query=SELECT+1"

# 2. Run migration with 8 parallel workers
python3 scripts/migrate_hdf5_to_questdb.py

# 3. Verify after completion
python3 scripts/check_migration_status.py
```

## What It Does

**Migrates:**
- `EQUITY.h5` (7.3 GB)
- `EQUITY_chunk1.h5` (683 MB)
- `EQUITY_chunk2.h5` (646 MB)

**To:**
- QuestDB `ohlcv_equity` table

**Stats:**
- 5,380 datasets (exchange/symbol/interval combinations)
- 233,478,666 rows
- Expected throughput: 50K-400K rows/sec
- Expected time: 15-30 minutes

## Features

✅ **Fast:** Uses ILP protocol for maximum write speed
✅ **Parallel:** 8 workers by default (configurable)
✅ **Idempotent:** Can safely re-run (automatic deduplication)
✅ **Resumable:** Interruptions? Just restart
✅ **Safe:** Dry-run mode available to preview
✅ **Monitored:** Real-time progress logs

## Command Options

```bash
# Default (8 workers, 50K batch)
python3 scripts/migrate_hdf5_to_questdb.py

# Fast mode (16 workers, 100K batch)
python3 scripts/migrate_hdf5_to_questdb.py --parallel=16 --batch-size=100000

# Careful mode (4 workers, 25K batch)
python3 scripts/migrate_hdf5_to_questdb.py --parallel=4 --batch-size=25000

# Dry run (preview only)
python3 scripts/migrate_hdf5_to_questdb.py --dry-run

# Specific file only
python3 scripts/migrate_hdf5_to_questdb.py --files data/hdf5/EQUITY.h5
```

## Monitor Progress

### While Running

```bash
# Check row count in QuestDB
curl -s "http://localhost:9000/exec?query=SELECT+COUNT(*)+as+total+FROM+ohlcv_equity"

# Check unique symbols
curl -s "http://localhost:9000/exec?query=SELECT+COUNT(DISTINCT+symbol)+as+symbols+FROM+ohlcv_equity"

# Check progress by exchange
curl -s "http://localhost:9000/exec" \
  --data-urlencode "query=SELECT exchange, COUNT(*) as rows FROM ohlcv_equity GROUP BY exchange"
```

### Check Logs

```bash
# Real-time logs
tail -f logs/migration.log

# Search for errors
grep ERROR logs/migration.log
```

## After Migration

### Verify

```bash
python3 scripts/check_migration_status.py
```

This compares HDF5 row counts vs QuestDB row counts and reports:
- ✓ Matched datasets
- ✗ Missing datasets
- ⚠ Mismatched counts

### Query Data

```bash
# Sample query
curl -s "http://localhost:9000/exec" \
  --data-urlencode "query=SELECT * FROM ohlcv_equity WHERE symbol='RELIANCE' AND interval='day' LIMIT 10"
```

## Troubleshooting

### QuestDB Not Running

```bash
brew services start questdb
# OR
questdb start
```

### Migration Too Slow

```bash
# Increase workers
python3 scripts/migrate_hdf5_to_questdb.py --parallel=16
```

### Out of Memory

```bash
# Reduce batch size and workers
python3 scripts/migrate_hdf5_to_questdb.py --parallel=4 --batch-size=25000
```

### Migration Interrupted

Just re-run the same command - it's idempotent and will resume automatically.

## Files Created

- `scripts/migrate_hdf5_to_questdb.py` - Main migration script
- `scripts/check_migration_status.py` - Verification script
- `scripts/MIGRATION_README.md` - Detailed documentation
- `scripts/QUICK_START.md` - This file

## Next Steps

After successful migration:

1. **Validate data quality:**
   ```python
   from quest.validator import QuestDBValidator
   validator = QuestDBValidator()
   ```

2. **Update application to use QuestDB:**
   - Use `quest.data_reader` for queries
   - Use `quest.writer` for new data

3. **Set up backups:**
   ```bash
   cp -r /opt/homebrew/var/questdb/db /path/to/backup/
   ```

4. **Archive HDF5 files:**
   ```bash
   # After verification, you can archive HDF5 files
   mv data/hdf5/*.h5 data/hdf5/archive/
   ```

## Support

- Detailed docs: `scripts/MIGRATION_README.md`
- Logs: `logs/migration.log`
- QuestDB logs: `/opt/homebrew/var/questdb/log/`

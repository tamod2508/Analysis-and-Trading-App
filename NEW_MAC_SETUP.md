# Setup Instructions for New MacBook

## Quick Start

### 1. Clone Repository
```bash
cd ~/Desktop
git clone <your-repo-url> kite_app
cd kite_app
```

### 2. Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# If Apple Silicon (M1/M2/M3/M4), add to PATH:
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 3. Install Dependencies
```bash
# Install QuestDB and Python
brew install questdb python@3.11

# Install Python packages
pip3 install pandas numpy h5py hdf5plugin requests psycopg2-binary tqdm
```

### 4. Configure QuestDB Memory
```bash
# Find QuestDB version
QUESTDB_VERSION=$(ls /opt/homebrew/Cellar/questdb/)

# Edit env.sh
nano /opt/homebrew/Cellar/questdb/$QUESTDB_VERSION/libexec/env.sh

# Add this line at the end:
export JVM_PREPEND="-Xms4g -Xmx16g"

# Save and exit (Ctrl+X, Y, Enter)
```

### 5. Start QuestDB
```bash
brew services start questdb

# Wait for startup
sleep 5

# Verify it's running with correct heap
ps aux | grep java | grep questdb | grep Xmx16g

# Open web console
open http://localhost:9000
```

### 6. Copy HDF5 Data Files
Copy these 3 files from old Mac (via external drive, AirDrop, or cloud):
- `EQUITY_repacked.h5` (1.35 GB)
- `EQUITY_chunk1.h5`
- `EQUITY_chunk2.h5`

Place them in: `~/Desktop/kite_app/data/hdf5/`

### 7. Create QuestDB Table
```bash
cd ~/Desktop/kite_app

python3 << 'EOF'
from quest.client import QuestDBClient
from quest.table_functions import QuestDBSchemaManager
from quest.config import TableNames

client = QuestDBClient()
manager = QuestDBSchemaManager(client)

print("Creating ohlcv_equity table...")
manager.create_table(TableNames.OHLCV_EQUITY)
print("✓ Table created successfully!")

client.close()
EOF
```

### 8. Run Migration
```bash
# Run migration with 25K batch size
python3 scripts/migrate_hdf5_to_questdb.py --batch-size=25000

# Or use the helper script
bash scripts/run_migration.sh
```

### 9. Monitor Progress
```bash
# In another terminal, watch progress
watch -n 30 'curl -s "http://localhost:9000/exec?query=SELECT+COUNT(*)+as+cnt+FROM+ohlcv_equity"'

# Or use the monitoring script
bash scripts/monitor_migration.sh
```

---

## Migration Details

**Data to migrate:**
- Total rows: 233,478,666
- Files: 3 HDF5 files
- Datasets: 5,380 symbol/interval combinations
- Symbols: ~1,230 unique symbols
- Intervals: day, 60minute, 15minute, 5minute, 3minute, minute

**Known Issues:**
- QuestDB ILP TCP sometimes gets "broken pipe" errors during high-throughput writes
- Solution: Increased heap size to 16GB + batch size of 25K rows
- Migration will take several hours but will complete eventually

**Expected Performance:**
- Throughput: 50K-150K rows/sec (when working)
- Success rate: ~50-70% (some batches fail and retry)
- Total time: 4-8 hours for full migration

---

## Directory Structure

```
kite_app/
├── api/                  # Kite Connect API client
├── config/              # Configuration and constants
├── database/            # HDF5 storage layer
├── quest/               # QuestDB client and writer (NEW)
│   ├── client.py       # HTTP client for queries
│   ├── writer.py       # ILP writer for fast writes
│   ├── config.py       # QuestDB configuration
│   └── table_functions.py  # Table creation/management
├── scripts/            # Migration scripts (NEW)
│   ├── migrate_hdf5_to_questdb.py  # Main migration script
│   ├── validate_questdb_data.py    # Validation script
│   └── run_migration.sh            # Helper script
├── flask_app/          # Flask web interface
├── utils/              # Utilities
├── data/hdf5/          # HDF5 data files (NOT in git)
│   ├── EQUITY_repacked.h5  ← Copy this file
│   ├── EQUITY_chunk1.h5    ← Copy this file
│   └── EQUITY_chunk2.h5    ← Copy this file
└── logs/               # Log files
```

---

## Troubleshooting

### QuestDB won't start
```bash
# Check logs
tail -f /opt/homebrew/var/questdb/log/stdout-*.txt

# Restart
brew services restart questdb
```

### Import errors
```bash
# Reinstall packages
pip3 install --upgrade pandas numpy h5py hdf5plugin requests psycopg2-binary
```

### Migration failing
```bash
# Check QuestDB is running
curl http://localhost:9000/

# Check table exists
curl -G "http://localhost:9000/exec" --data-urlencode "query=SHOW TABLES"

# Check logs
tail -f logs/migration.log
```

### Out of memory errors
```bash
# Increase heap size (edit env.sh)
nano /opt/homebrew/Cellar/questdb/*/libexec/env.sh

# Change to:
export JVM_PREPEND="-Xms8g -Xmx32g"

# Restart QuestDB
brew services restart questdb
```

---

## What's New (QuestDB Migration)

This version adds QuestDB support for faster queries and better scalability:

1. **New `quest/` module:**
   - QuestDB client for HTTP queries
   - ILP writer for fast bulk inserts (50K-400K rows/sec)
   - Table schema management
   - Configuration management

2. **New migration scripts:**
   - `migrate_hdf5_to_questdb.py` - Migrates HDF5 → QuestDB
   - `validate_questdb_data.py` - Validates against Kite API
   - Helper scripts for monitoring

3. **Features:**
   - Parallel migration support
   - Automatic deduplication
   - Resume capability
   - Progress tracking
   - Error handling with retries

4. **HDF5 still works:**
   - All existing HDF5 code is untouched
   - Can use both HDF5 and QuestDB
   - QuestDB is optional

---

## Next Steps Tomorrow

1. ✅ Complete setup steps above
2. ✅ Copy HDF5 files
3. ✅ Run migration
4. 🔄 Write improved migration script (optional - if current one has issues)

Sleep well! 🌙

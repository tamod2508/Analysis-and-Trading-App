# Migration Plan: HDF5 → QuestDB

## Current Status
- **QuestDB:** 1,263 symbols, 282.7M rows (still loading from WAL)
- **HDF5 files:** 691 symbols in EQUITY.h5 (7.3GB)
- **Migration:** Completed using ILP protocol, but HDF5 code still active in 15+ files

## Architecture Analysis

### Existing QuestDB Infrastructure (database2/)
✅ **Already exists and working:**
- `writer.py` - ILP-based high-speed writer
- `reader.py` - Query interface for OHLCV data
- `client.py` - QuestDB connection manager
- `validator.py` - Data validation
- `schema.py` - Table definitions
- `fetch_to_questdb.py` - Direct Kite → QuestDB fetching

### Files Using HDF5 (need migration)
**Core Application:**
1. `api/kite_client.py` - Fetches from Kite API, saves to HDF5
2. `flask_app/services/data_fetcher.py` - Flask wrapper for KiteClient
3. `flask_app/services/data_service.py` - Dashboard statistics
4. `flask_app/routes/dashboard.py` - Dashboard views
5. `flask_app/routes/auth.py` - DB checks during auth

**Database Layer:**
6. `database/hdf5_manager.py` - Core HDF5 functionality (1,200+ lines)
7. `database/data_adjuster.py` - Price adjustments

## Phase 1: Create QuestDB Adapters (SAFE - No Breaking Changes)

### 1.1 Create QuestDB Manager Wrapper
**New file:** `database2/questdb_manager.py`

Purpose: Mirror HDF5Manager API for drop-in replacement

**Key Methods to Implement:**
```python
class QuestDBManager:
    def __init__(self, segment: str = 'EQUITY'):
        """Initialize with segment (EQUITY/DERIVATIVES)"""

    def save_ohlcv(self, exchange: str, symbol: str, interval: str,
                   data: np.ndarray) -> bool:
        """Save OHLCV data - mirrors HDF5Manager.save_ohlcv()"""

    def get_ohlcv(self, exchange: str, symbol: str, interval: str,
                  start_date=None, end_date=None, as_dataframe=True):
        """Query OHLCV data - mirrors HDF5Manager.get_ohlcv()"""

    def list_symbols(self, exchange: str = None) -> List[str]:
        """List all symbols - mirrors HDF5Manager.list_symbols()"""

    def get_database_stats(self) -> Dict:
        """Get database statistics - mirrors HDF5Manager.get_database_stats()"""

    def delete_data(self, exchange: str, symbol: str, interval: str = None):
        """Delete symbol data - mirrors HDF5Manager.delete_data()"""
```

**Implementation Notes:**
- Wraps existing `QuestDBReader` and `QuestDBWriter`
- Maintains same return types as HDF5Manager
- Handles timezone conversions (IST ↔ UTC)
- Supports both equity and derivatives (OI field)

**Benefits:**
- Drop-in replacement - minimal code changes
- Can swap backends with single line change
- Enables A/B testing between HDF5 and QuestDB
- Gradual migration without breaking existing code

### 1.2 Create Dual-Write Mode
**Update:** `api/kite_client.py`

Add configuration flag for parallel writes:
```python
class KiteClient:
    def __init__(self, api_key=None, access_token=None, use_questdb=False):
        self.use_questdb = use_questdb

        # Initialize both managers
        self.hdf5_db = HDF5Manager()
        if use_questdb:
            from database2.questdb_manager import QuestDBManager
            self.questdb = QuestDBManager()

    def _save_data(self, exchange, symbol, interval, data):
        """Save to HDF5 and optionally QuestDB"""
        # Always write to HDF5 (primary)
        self.hdf5_db.save_ohlcv(exchange, symbol, interval, data)

        # Optionally write to QuestDB (for testing)
        if self.use_questdb:
            try:
                self.questdb.save_ohlcv(exchange, symbol, interval, data)
            except Exception as e:
                logger.warning(f"QuestDB write failed (non-critical): {e}")
```

**Configuration:**
```python
# config/constants.py or .env
USE_QUESTDB = False  # Set to True to enable dual-write
```

**Testing Strategy:**
1. Enable dual-write for 1 week
2. Compare data integrity daily
3. Verify query results match
4. Monitor performance metrics

## Phase 2: Update Flask Application (READ Operations First)

### 2.1 Update Data Service
**Update:** `flask_app/services/data_service.py`

```python
from database2.questdb_manager import QuestDBManager
from database.hdf5_manager import HDF5Manager

# Configuration flag
USE_QUESTDB_READS = False  # Toggle to switch

def get_database_manager(segment: str):
    """Factory function to get database manager"""
    if USE_QUESTDB_READS:
        return QuestDBManager(segment)
    else:
        return HDF5Manager(segment)

def get_all_database_stats() -> Dict:
    """Get statistics using configured backend"""
    segments = ['EQUITY', 'DERIVATIVES', 'FUNDAMENTALS']

    all_stats = {}
    for segment in segments:
        try:
            mgr = get_database_manager(segment)
            stats = mgr.get_database_stats()
            all_stats[segment] = stats
        except Exception as e:
            logger.error(f"Error getting stats for {segment}: {e}")

    return all_stats
```

**Migration Steps:**
1. Add `get_database_manager()` factory function
2. Replace all `HDF5Manager()` calls with factory
3. Test with `USE_QUESTDB_READS = False` (existing behavior)
4. Switch to `USE_QUESTDB_READS = True` to use QuestDB
5. Monitor for errors, performance issues

### 2.2 Update Dashboard
**Update:** `flask_app/routes/dashboard.py`

```python
from flask_app.services.data_service import get_database_manager

@dashboard_bp.route('/')
@login_required
def home():
    try:
        # Use factory instead of direct HDF5Manager
        manager = get_database_manager('EQUITY')

        # Get symbols (works with both backends)
        symbols = manager.list_symbols('NSE')

        # Get statistics
        stats = manager.get_database_stats()

        return render_template('dashboard/home.html',
                             symbols=symbols,
                             stats=stats)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('error.html', error=str(e))
```

**Changes:**
- Replace `HDF5Manager()` with `get_database_manager()`
- No other logic changes needed
- Queries work identically with both backends

### 2.3 Update Data Fetcher Service
**Update:** `flask_app/services/data_fetcher.py`

```python
from flask_app.services.data_service import get_database_manager

class DataFetcherService:
    def query_data(self, exchange: str, symbol: str, interval: str,
                   start_date=None, end_date=None):
        """Query OHLCV data using configured backend"""

        # Determine segment
        segment = 'DERIVATIVES' if exchange in ['NFO', 'BFO'] else 'EQUITY'

        # Get appropriate manager
        mgr = get_database_manager(segment)

        # Query data (works with both HDF5 and QuestDB)
        data = mgr.get_ohlcv(exchange, symbol, interval,
                            start_date, end_date,
                            as_dataframe=True)

        return data
```

**Testing:**
1. Query data with HDF5 backend → save results
2. Switch to QuestDB backend → compare results
3. Verify data matches exactly
4. Check query performance

## Phase 3: Update Write Operations

### 3.1 Update KiteClient
**Update:** `api/kite_client.py`

**Step 1: Make backend configurable**
```python
from config import config

class KiteClient:
    def __init__(self, api_key=None, access_token=None):
        # ... existing init code ...

        # Choose backend based on config
        if config.USE_QUESTDB_PRIMARY:
            from database2.questdb_manager import QuestDBManager
            self.db = QuestDBManager()
        else:
            from database.hdf5_manager import HDF5Manager
            self.db = HDF5Manager()
```

**Step 2: Test write operations**
1. Set `USE_QUESTDB_PRIMARY = True`
2. Fetch new data for 5-10 symbols
3. Verify data written to QuestDB
4. Query data back and verify integrity
5. Check dashboard displays correctly

**Step 3: Migrate completely**
Once confident:
```python
# Remove HDF5, use only QuestDB
from database2.questdb_manager import QuestDBManager

class KiteClient:
    def __init__(self, api_key=None, access_token=None):
        # ... existing init code ...
        self.db = QuestDBManager()
```

### 3.2 Test Data Flow End-to-End

**Test Scenario:**
1. **Fetch** new data via KiteClient → QuestDB
2. **Verify** data in QuestDB (count, dates, OHLCV values)
3. **Query** via Flask routes → confirm displays correctly
4. **Dashboard** statistics → verify counts match
5. **Charts** → verify visualization works

**Validation:**
```python
# Compare data before/after migration
import pandas as pd
from database.hdf5_manager import HDF5Manager
from database2.questdb_manager import QuestDBManager

symbol = 'RELIANCE'
exchange = 'NSE'
interval = 'day'

# Get from HDF5
hdf5_mgr = HDF5Manager('EQUITY')
hdf5_data = hdf5_mgr.get_ohlcv(exchange, symbol, interval)

# Get from QuestDB
qdb_mgr = QuestDBManager('EQUITY')
qdb_data = qdb_mgr.get_ohlcv(exchange, symbol, interval)

# Compare
assert len(hdf5_data) == len(qdb_data), "Row count mismatch"
pd.testing.assert_frame_equal(hdf5_data, qdb_data, check_exact=False, atol=0.01)
print("✅ Data matches!")
```

## Phase 4: Clean Up HDF5 Code

### 4.1 Remove HDF5 Dependencies

**Delete:**
```bash
# Core HDF5 functionality (archive first!)
git mv database/hdf5_manager.py database/_archived/hdf5_manager.py
git mv database/data_adjuster.py database/_archived/data_adjuster.py

# Migration scripts (keep for reference)
git mv scripts/migrate_hdf5_to_questdb*.py scripts/_archived/

# Old fetch scripts (keep for reference)
git mv scripts/fetch_*.py scripts/_archived/
```

**Archive HDF5 files:**
```bash
# Create archive directory
mkdir -p data/hdf5_archive/

# Move HDF5 databases (keep as backup for 30 days)
mv data/hdf5/EQUITY.h5 data/hdf5_archive/EQUITY_$(date +%Y%m%d).h5
mv data/hdf5/DERIVATIVES.h5 data/hdf5_archive/DERIVATIVES_$(date +%Y%m%d).h5
```

### 4.2 Update Imports

**Files to update (15 files):**
```python
# OLD
from database.hdf5_manager import HDF5Manager
manager = HDF5Manager('EQUITY')

# NEW
from database2.questdb_manager import QuestDBManager
manager = QuestDBManager('EQUITY')
```

**Use find-replace:**
```bash
# Find all imports
grep -r "from database.hdf5_manager" --include="*.py"

# Replace in each file
sed -i '' 's/from database.hdf5_manager import HDF5Manager/from database2.questdb_manager import QuestDBManager/g' file.py
sed -i '' 's/HDF5Manager/QuestDBManager/g' file.py
```

**Files to update:**
1. api/kite_client.py
2. flask_app/services/data_fetcher.py
3. flask_app/services/data_service.py
4. flask_app/routes/dashboard.py
5. flask_app/routes/auth.py
6. database/data_adjuster.py (if kept)
7. scripts/*.py (any remaining scripts)

### 4.3 Remove HDF5 Packages

**Update:** `requirements.txt`

**Remove:**
```
h5py==3.9.0
hdf5plugin==4.1.3
tables==3.8.0
```

**Keep:**
```
questdb==1.1.0
psycopg2-binary==2.9.9
```

**Test after removal:**
```bash
# Create new virtual environment
python3 -m venv venv_test
source venv_test/bin/activate

# Install updated requirements
pip install -r requirements.txt

# Run application
python wsgi.py

# Verify:
# - No import errors
# - Flask starts successfully
# - Can fetch new data
# - Dashboard works
# - Queries return data
```

### 4.4 Update Documentation

**Update:** `.claude/CLAUDE.md`

Remove HDF5 sections, update with QuestDB info:

```markdown
## Data Storage Strategy

- **Primary Database:** QuestDB (time-series optimized)
- **Table Structure:** `ohlcv_equity`, `ohlcv_derivatives`, `fundamentals`
- **Protocol:** InfluxDB Line Protocol (ILP) for writes
- **Query:** PostgreSQL wire protocol for reads
- **Partitioning:** By DAY on timestamp column
- **Performance:** 50K+ rows/sec write throughput

## Previous System (Archived)
- HDF5 files archived in `data/hdf5_archive/`
- Migration completed: [date]
- HDF5 code available in `database/_archived/` for reference
```

## Phase 5: Keep HDF5 for Backups (Optional)

### 5.1 Export Utility
**New file:** `scripts/export_questdb_to_hdf5.py`

```python
"""
Export QuestDB data to HDF5 format for archival/backup
Run monthly for portable backups
"""

import h5py
import pandas as pd
from datetime import datetime
from database2.client import QuestDBClient
from pathlib import Path

def export_to_hdf5(output_dir: str = 'data/hdf5_archive'):
    """
    Export all QuestDB data to HDF5 format

    Use cases:
    - Monthly backups
    - Portable archives
    - Offline analysis
    - Sharing data without QuestDB
    """
    client = QuestDBClient()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get all symbols
    symbols_query = "SELECT DISTINCT symbol FROM ohlcv_equity ORDER BY symbol"
    symbols = client.execute_query(symbols_query)

    # Create HDF5 file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    h5_file = output_path / f'equity_archive_{timestamp}.h5'

    with h5py.File(h5_file, 'w') as f:
        for symbol in symbols:
            # Query data from QuestDB
            query = f"""
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv_equity
                WHERE symbol = '{symbol}'
                ORDER BY timestamp
            """
            df = client.query_to_dataframe(query)

            # Save to HDF5
            grp = f.create_group(f'NSE/{symbol}')
            for interval in ['day', '60minute', '15minute']:
                # Filter by interval and save
                interval_data = df[df['interval'] == interval]
                grp.create_dataset(interval, data=interval_data.to_records())

            print(f"✅ Exported {symbol}")

    print(f"\n✅ Archive created: {h5_file}")
    print(f"   Size: {h5_file.stat().st_size / (1024**2):.1f} MB")
    return h5_file

if __name__ == '__main__':
    export_to_hdf5()
```

**Schedule monthly:**
```bash
# Add to crontab
0 0 1 * * /Users/atm/Desktop/kite_app/venv/bin/python /Users/atm/Desktop/kite_app/scripts/export_questdb_to_hdf5.py
```

## Rollback Plan

**If issues occur during migration:**

### Immediate Rollback (Phase 1-2)
```python
# In config/constants.py
USE_QUESTDB_READS = False    # Switch back to HDF5 reads
USE_QUESTDB_PRIMARY = False  # Switch back to HDF5 writes
```

**Result:** Application uses HDF5 immediately, no code changes needed

### Emergency Rollback (Phase 3)
```bash
# Restore archived HDF5Manager
git checkout HEAD~1 database/hdf5_manager.py

# Revert kite_client changes
git checkout HEAD~1 api/kite_client.py

# Restart application
python wsgi.py
```

**Result:** Back to 100% HDF5, QuestDB untouched

### Data Recovery
```python
# If QuestDB data is corrupted, restore from HDF5
from database.hdf5_manager import HDF5Manager
from database2.writer import QuestDBWriter

hdf5 = HDF5Manager('EQUITY')
writer = QuestDBWriter()

# Re-migrate from HDF5
symbols = hdf5.list_symbols('NSE')
for symbol in symbols:
    data = hdf5.get_ohlcv('NSE', symbol, 'day')
    writer.insert_ohlcv_batch('ohlcv_equity', 'NSE', symbol, 'day', data)
```

## Risk Mitigation

### Phase 1 (LOW RISK)
**Risk:** QuestDB manager has bugs
**Mitigation:**
- All writes go to HDF5 (primary)
- QuestDB writes are optional/dual
- Can disable QuestDB at any time
- Zero impact on production

### Phase 2 (LOW RISK)
**Risk:** QuestDB queries return wrong data
**Mitigation:**
- Read-only operations
- HDF5 still receives all writes
- Can toggle back instantly via config flag
- A/B test results before committing

### Phase 3 (MEDIUM RISK)
**Risk:** New data writes fail
**Mitigation:**
- Dual-write initially (both HDF5 + QuestDB)
- Monitor write success rates
- HDF5 remains backup for 30 days
- Can restore from HDF5 if needed

### Phase 4 (HIGH RISK)
**Risk:** Delete HDF5 code prematurely
**Mitigation:**
- Archive instead of delete
- Keep HDF5 files for 30+ days
- Test thoroughly before removing
- Document rollback procedure
- Maintain monthly HDF5 exports

## Success Criteria

Before proceeding to next phase:

**Phase 1 Complete:**
- ✅ QuestDBManager created with all HDF5Manager methods
- ✅ Dual-write tested with 100+ symbols
- ✅ Data integrity verified (HDF5 vs QuestDB match)
- ✅ No errors in QuestDB writes

**Phase 2 Complete:**
- ✅ All Flask routes work with QuestDB backend
- ✅ Dashboard displays correct statistics
- ✅ Queries return same results as HDF5
- ✅ Performance equal or better than HDF5
- ✅ No errors in production logs (7 days)

**Phase 3 Complete:**
- ✅ New data fetches write to QuestDB
- ✅ No HDF5 writes for 7 days (QuestDB only)
- ✅ All features work (fetch, query, dashboard, charts)
- ✅ Data integrity maintained
- ✅ Zero data loss

**Phase 4 Complete:**
- ✅ No HDF5 imports in active code
- ✅ HDF5 packages removed from requirements.txt
- ✅ All tests pass without HDF5
- ✅ Application runs without h5py installed
- ✅ Documentation updated

## Timeline Estimate

**Phase 1: QuestDB Adapters**
- Wrapper creation: 2 hours
- Dual-write implementation: 1 hour
- Testing: 2 hours
- **Total: 5 hours**

**Phase 2: Flask Updates (Reads)**
- Data service updates: 1 hour
- Dashboard updates: 1 hour
- Route updates: 1 hour
- Testing: 2 hours
- **Total: 5 hours**

**Phase 3: Write Operations**
- KiteClient updates: 1 hour
- End-to-end testing: 2 hours
- Production monitoring: 1 week
- **Total: 3 hours + 1 week monitoring**

**Phase 4: Cleanup**
- Remove HDF5 code: 1 hour
- Update imports: 1 hour
- Testing: 2 hours
- Documentation: 1 hour
- **Total: 5 hours**

**Overall Timeline:**
- **Development:** ~18 hours
- **Testing/Monitoring:** 2-3 weeks
- **Total:** 1 month for safe migration

## Performance Comparison

### HDF5 (Current)
- **Write:** ~10K rows/sec (compressed)
- **Read:** Fast for single symbol queries
- **Queries:** Limited to Python/pandas operations
- **Concurrency:** File locks limit concurrent writes
- **Storage:** 7.3GB for 691 symbols (compressed)

### QuestDB (Target)
- **Write:** 50K+ rows/sec (ILP protocol)
- **Read:** Sub-second for large date ranges
- **Queries:** Full SQL with time-series functions
- **Concurrency:** Multiple writers, readers no problem
- **Storage:** Similar or better (columnar compression)

### Migration Performance
- **ILP migration:** 54,269 rows/sec
- **Total migrated:** 277M rows in 35 minutes
- **Success rate:** 100% (zero errors)

## Conclusion

**Recommended Approach:**
1. **Start conservative** - Phase 1 with dual-write
2. **Validate thoroughly** - Test each phase before proceeding
3. **Keep escape hatches** - Always able to rollback
4. **Move gradually** - 1 phase per week minimum
5. **Monitor closely** - Watch logs, metrics, errors

**Benefits After Migration:**
- ✅ Better query performance (SQL + time-series functions)
- ✅ Higher write throughput (ILP protocol)
- ✅ Better concurrency (no file locks)
- ✅ Easier scaling (separate server)
- ✅ Industry-standard time-series DB

**Safety Net:**
- HDF5 code archived, not deleted
- HDF5 files kept for 30+ days
- Can rollback at any point
- Monthly HDF5 exports for backup

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Migration Status:** Planning Phase
**Next Step:** Phase 1 - Create QuestDBManager wrapper

# Kite Connect Historical Data Manager - Project Structure

**Last Updated:** January 2025
**Version:** 1.0
**Database Version:** 1.0

---

## Table of Contents

1. [Directory Overview](#directory-overview)
2. [Core Modules](#core-modules)
3. [Configuration System](#configuration-system)
4. [Database Architecture](#database-architecture)
5. [Validation System](#validation-system)
6. [Performance & Monitoring](#performance--monitoring)
7. [Recent Improvements](#recent-improvements)

---

## Directory Overview

```
kite_app/
├── api/                          # Kite API integration
│   ├── auth_handler.py          # OAuth authentication
│   └── kite_client.py           # API client with rate limiting
│
├── config/                       # Configuration and constants
│   ├── __init__.py              # Exports all configs
│   ├── constants.py             # Enums, limits, mappings
│   ├── settings.py              # Environment configs (Dev/Test/Prod)
│   ├── optimizer.py             # M1/M4 hardware optimization
│   └── logging_config.yaml      # YAML logging configuration
│
├── database/                     # HDF5 storage layer
│   ├── schema.py                # Schema definitions (OHLCV, Instruments)
│   ├── validators.py            # Validation logic (BaseValidationRules)
│   ├── hdf5_manager.py          # Database operations + migrations
│   ├── instruments_db.py        # Instrument metadata management
│   ├── data_validator.py        # Data quality checks
│   ├── data_adjuster.py         # Corporate action adjustments
│   └── corporate_action_detector.py  # Detect splits/dividends
│
├── ui/                           # Streamlit interface
│   ├── pages/                   # UI pages
│   └── components/              # Reusable UI components
│
├── utils/                        # Utilities
│   ├── metrics.py               # Performance metrics collection
│   └── [other utilities]        # Date, file, logging helpers
│
├── tests/                        # Unit tests
│   ├── test_improvements.py     # Tests for improvements 1-10
│   └── test_improvements_12_22.py  # Tests for improvements 12-22
│
├── docs/                         # Documentation
│   ├── api_reference.md
│   ├── setup_guide.md
│   ├── MARKET_SEGMENTS_IMPLEMENTATION.md
│   ├── DERIVATIVES_OI_HANDLING.md
│   ├── INSTRUMENTS_DATABASE.md
│   └── PROJECT_STRUCTURE.md     # This file
│
├── data/                         # Data directory (gitignored)
│   ├── hdf5/                    # HDF5 database files
│   │   ├── EQUITY.h5           # NSE + BSE stocks
│   │   ├── DERIVATIVES.h5      # NFO + BFO options/futures
│   └── backups/                 # Database backups
│
├── exports/                      # Exported data
│   ├── csv/
│   ├── reports/
│   └── charts/
│
├── logs/                         # Application logs
│   ├── app.log
│   ├── error.log
│   ├── database.log
│   └── api.log
│
├── .env                          # Environment variables
├── main.py                       # Streamlit entry point
└── .claude/CLAUDE.md             # Project instructions
```

---

## Core Modules

### 1. API Layer (`api/`)

**Purpose:** Interface with Zerodha's Kite Connect API

#### `auth_handler.py`
- OAuth 2.0 authentication flow
- Token management and refresh
- Session persistence

#### `kite_client.py`
- Historical data fetching
- Rate limiting (3 requests/second)
- Exponential backoff retry
- Batch processing
- API fetch chunking (1095 days per chunk)

**Key Constants:**
- `KITE_API_RATE_LIMIT_PER_SECOND = 3`
- `API_RATE_SAFETY_MARGIN_SECONDS = 0.05`
- `API_TIMEOUT_SECONDS = 60`
- `RETRY_BACKOFF_MULTIPLIER = 1.3`

---

### 2. Configuration System (`config/`)

**Purpose:** Centralized configuration with environment-specific profiles

#### `constants.py`
**Enums:**
- `Interval` - minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute, day
- `CompressionType` - BLOSC_LZ4, BLOSC_ZSTD, GZIP, LZF, NONE
- `InstrumentType` - EQ, FUT, CE, PE

**Mappings:**
```python
EXCHANGE_TO_SEGMENT = {
    Exchange.NSE: Segment.EQUITY,
    Exchange.BSE: Segment.EQUITY,
    Exchange.NFO: Segment.DERIVATIVES,
    Exchange.BFO: Segment.DERIVATIVES,
}
```

**Validation Limits:**
```python
VALIDATION_LIMITS = {
    Segment.EQUITY: ValidationLimits(
        min_price=0.01,
        max_price=1_000_000.0,
        allow_zero_prices=False
    ),
    Segment.DERIVATIVES: ValidationLimits(
        min_price=0.00,  # Options can expire worthless
        max_price=100_000.0,
        allow_zero_prices=True
    ),
}
```

**File Size Limits:**
- `MAX_HDF5_FILE_SIZE_GB = 50.0`
- `MAX_BACKUP_SIZE_GB = 100.0`
- `MAX_EXPORT_SIZE_MB = 500.0`
- `MAX_LOG_FILE_SIZE_MB = 100.0`
- `MAX_TOTAL_DATA_SIZE_GB = 200.0`

**HDF5 Storage Chunks:**
```python
HDF5_STORAGE_CHUNKS = {
    Interval.DAY: 5000,
    Interval.MINUTE_60: 2000,
    Interval.MINUTE_15: 1000,
    Interval.MINUTE_5: 1000,
    Interval.MINUTE: 500,
}
```

#### `settings.py`
**Environment-Specific Configs:**

```python
class BaseConfig:
    """Shared settings across all environments"""
    # Paths, API credentials, rate limits, etc.

class DevelopmentConfig(BaseConfig):
    LOG_LEVEL = "DEBUG"
    HDF5_RDCC_NBYTES = 314572800  # 300MB cache
    MAX_RETRIES = 3

class ProductionConfig(BaseConfig):
    LOG_LEVEL = "INFO"
    HDF5_RDCC_NBYTES = 2147483648  # 2GB cache
    MAX_RETRIES = 7

class TestingConfig(BaseConfig):
    LOG_LEVEL = "WARNING"
    AUTO_BACKUP = False
    HDF5_RDCC_NBYTES = 104857600  # 100MB cache
```

**Auto-Configuration:**
- Detects M1/M4 chips for hardware-specific optimization
- Auto-detects optimal thread count (75% of CPU cores)
- Configures BLAS/LAPACK backend (Accelerate on macOS)

#### `optimizer.py`
- M1/M4 chip detection
- Hardware-specific memory/thread optimization
- No side effects (explicit `optimize_config()` method)

#### `logging_config.yaml`
- YAML-based logging configuration
- Multiple handlers (console, file, error_file, database_file, api_file)
- Different formatters (simple, detailed, verbose)
- Configurable log levels per module

---

### 3. Database Layer (`database/`)

**Purpose:** HDF5-based time-series data storage with integrity checks

#### Database Files

**Separate file per segment:**
- `EQUITY.h5` - NSE + BSE stocks (6-field schema)
- `DERIVATIVES.h5` - NFO + BFO options/futures (7-field schema with OI)

**Internal Structure:**
```
/{SEGMENT}.h5
├── /instruments/{EXCHANGE}/    # Instrument metadata
│   └── dataset with instrument info
└── /data/{EXCHANGE}/{SYMBOL}/{INTERVAL}/
    └── dataset with OHLCV data + attributes
```

#### Schemas (`schema.py`)

**Equity OHLCV Schema:**
```python
DTYPE = np.dtype([
    ('timestamp', 'int64'),
    ('open', 'float32'),
    ('high', 'float32'),
    ('low', 'float32'),
    ('close', 'float32'),
    ('volume', 'int64'),
])
```

**Options/Derivatives Schema:**
```python
DTYPE = np.dtype([
    ('timestamp', 'int64'),
    ('open', 'float32'),
    ('high', 'float32'),
    ('low', 'float32'),
    ('close', 'float32'),
    ('volume', 'int64'),
    ('oi', 'int64'),  # Open Interest
])
```

#### Validation System (`validators.py`)

**Base Class:**
```python
class BaseValidationRules:
    """Common validation methods"""
    - validate_ohlc_relationship()
    - validate_price_range()
    - validate_volume()
    - validate_timestamp()
```

**Subclasses:**
```python
class ValidationRules(BaseValidationRules):
    """Equity validation"""
    MIN_PRICE_LIMIT = 0.01
    MAX_PRICE_LIMIT = 1_000_000.0

class OptionsValidationRules(BaseValidationRules):
    """Options/Derivatives validation"""
    MIN_PRICE_LIMIT = 0.00  # Allow ₹0
    MAX_PRICE_LIMIT = 100_000.0
    validate_open_interest()  # Additional method
```

#### HDF5 Manager (`hdf5_manager.py`)

**Key Features:**
- Context manager for safe file operations
- Automatic compression (Blosc:LZ4)
- Interval-specific chunk sizes
- Input validation (exchange/symbol/interval)
- Data integrity checks:
  - File corruption detection
  - SHA-256 checksums
  - Automatic recovery

**Database Migrations:**
```python
CURRENT_DB_VERSION = '1.0'
COMPATIBLE_DB_VERSIONS = ['1.0']

# Auto-migration on database open
def _check_and_migrate_version()
def _migrate_database(from_version, to_version)
def _migrate_0_0_to_1_0()  # Example migration
```

**Dataset Attributes:**
- `start_date`, `end_date`
- `row_count`
- `updated_at`
- `source` (kite_connect_api)
- `schema_version`
- `checksum` (SHA-256)
- `checksum_algorithm`

---

## Performance & Monitoring

### Performance Metrics (`utils/metrics.py`)

**Usage:**
```python
from utils.metrics import PerformanceMetrics, global_metrics

metrics = PerformanceMetrics()

# Method 1: Context manager
with metrics.measure('save_ohlcv', log=True):
    manager.save_ohlcv(...)

# Method 2: Decorator
@metrics.tracked('fetch_data', log=True)
def fetch_data():
    ...

# Get statistics
stats = metrics.get_stats('save_ohlcv')
# Returns: count, success_count, error_count, success_rate,
#          avg_time, median_time, min_time, max_time, stddev_time

summary = metrics.get_summary()  # Human-readable summary
```

**Features:**
- Context manager and decorator support
- Success/error tracking
- Statistical analysis (avg, median, min, max, stddev)
- Last execution timestamp
- Enable/disable globally
- Reset individual or all metrics

### Optimization Settings

**HDF5 Performance:**
- Read cache: 2GB (prod) / 300MB (dev) / 100MB (test)
- Compression: Blosc:LZ4 level 5
- Driver: sec2 (optimized for sequential access)
- Sieve buffer: 512KB
- Meta block size: 2MB

**Parallel Processing:**
- Auto thread count: 75% of CPU cores
- Batch size: 500 records
- Batch pause: 0.5 seconds
- GC interval: 200 operations
- Memory check interval: 120 seconds

**Memory Thresholds:**
- Max usage: 87% of RAM
- Warning: 93% of RAM
- Critical: 97% of RAM

---

## Recent Improvements

### High Priority (1-10) ✅

1. **Exchange-to-Segment Mapping**
   - Centralized `EXCHANGE_TO_SEGMENT` dict
   - Reverse mapping `SEGMENT_TO_EXCHANGES`

2. **Segment-Specific Validation**
   - `VALIDATION_LIMITS` dict by segment
   - Allows ₹0 for derivatives/options

3. **Environment-Specific Configs**
   - DevelopmentConfig, ProductionConfig, TestingConfig
   - Different cache sizes, retry counts, logging

4. **Input Validation**
   - Validate exchange/symbol/interval before operations
   - Clear error messages

5. **Auto-Detect Thread Counts**
   - Uses 75% of CPU cores automatically
   - Configures BLAS/LAPACK

6. **Fixed Bare Except Clauses**
   - All exceptions now specific
   - Better error logging

7. **File Corruption Detection**
   - Checks on database open
   - Auto-recovery (moves to .corrupt, re-initialize)

8. **Optimizer No Side Effects**
   - Explicit `optimize_config()` method
   - No global state modification on import

9. **Data Checksums**
   - SHA-256 checksums for all datasets
   - Automatic verification on read
   - Recalculate on append

10. **Type Hints**
    - Added to all critical methods
    - Better IDE support

### Medium Priority (12-22) ✅

12. **Logging Configuration File**
    - YAML-based (`logging_config.yaml`)
    - Multiple handlers and formatters

13. **Compression Type Enum**
    - Type-safe compression selection
    - BLOSC_LZ4, BLOSC_ZSTD, GZIP, LZF, NONE

14. **Magic Numbers Documented**
    - `KITE_API_RATE_LIMIT_PER_SECOND = 3`
    - Clear inline comments

15. **File Size Limits**
    - Constants for warnings
    - 5 different limit types

16. **Separated Validation from Schema**
    - New `validators.py` module
    - Backward compatibility maintained

17. **Database Migration Support**
    - Version tracking (v1.0)
    - Auto-migration with backup
    - `_migrate_0_0_to_1_0()` example

18. **Data Checksums** (covered in #9)

19. **Pathlib Consistency** (verified)

20. **Subprocess Timeouts** (verified - all have timeout=5)

21. **Base Validator Class**
    - `BaseValidationRules` eliminates duplication
    - Equity and Options inherit from base

22. **Performance Metrics**
    - Complete metrics collection system
    - Context manager + decorator support

### Testing ✅

- **32 tests passing**
  - `test_improvements.py` - 12 tests (improvements 1-10)
  - `test_improvements_12_22.py` - 20 tests (improvements 12-22)
- 100% backward compatibility
- No breaking changes

---

## Usage Examples

### Fetching Data

```python
from api.kite_client import KiteClient
from database.hdf5_manager import HDF5Manager

# Initialize
client = KiteClient(api_key, api_secret, access_token)
manager = HDF5Manager(segment='EQUITY')

# Fetch equity data
client.fetch_equity_by_symbol('RELIANCE', start_date, end_date, 'day')

# Fetch derivatives data
manager_derivatives = HDF5Manager(segment='DERIVATIVES')
client.fetch_derivatives_by_symbol('NFO', 'NIFTY25OCT24950CE',
                                   start_date, end_date, '5minute')
```

### Performance Monitoring

```python
from utils.metrics import global_metrics

# Track operations
with global_metrics.measure('data_fetch', log=True):
    data = fetch_historical_data()

# Get statistics
stats = global_metrics.get_stats('data_fetch')
print(f"Average time: {stats['avg_time']:.4f}s")
print(f"Success rate: {stats['success_rate']}%")
```

### Environment-Specific Behavior

```bash
# Development
export KITE_ENV=development
python main.py  # Uses DevelopmentConfig (DEBUG, 300MB cache)

# Production
export KITE_ENV=production
python main.py  # Uses ProductionConfig (INFO, 2GB cache)

# Testing
export KITE_ENV=testing
pytest  # Uses TestingConfig (WARNING, 100MB cache, no backup)
```

---

## Best Practices

1. **Always use segment-specific managers:**
   ```python
   equity_manager = HDF5Manager(segment='EQUITY')
   derivatives_manager = HDF5Manager(segment='DERIVATIVES')
   ```

2. **Use enums for constants:**
   ```python
   from config import Exchange, Interval, Segment
   manager.save_ohlcv(Exchange.NSE.value, symbol, Interval.DAY.value, data)
   ```

3. **Track performance for critical operations:**
   ```python
   @global_metrics.tracked('expensive_operation', log=True)
   def expensive_operation():
       ...
   ```

4. **Leverage environment configs:**
   - Development: Fast iteration, debug logging
   - Production: Optimized caching, error logging
   - Testing: Minimal overhead, no side effects

5. **Check data integrity:**
   ```python
   # Automatic on read - will raise ValueError if checksum mismatch
   data = manager.get_ohlcv('NSE', 'RELIANCE', 'day')
   ```

---

## Version History

**v1.0 (January 2025)**
- Initial stable release
- All 22 improvements implemented
- 32 tests passing
- Database migrations support
- Performance metrics collection
- Comprehensive documentation

---

## Contributing

When adding new features:
1. Update `constants.py` with new enums/limits
2. Add type hints to all methods
3. Write tests in `tests/`
4. Update this documentation
5. Follow existing patterns (dataclasses, enums, validators)

---

## References

- [Kite Connect API Documentation](https://kite.trade/docs/connect/v3/)
- [HDF5 Documentation](https://docs.h5py.org/)
- [Market Segments Implementation](./MARKET_SEGMENTS_IMPLEMENTATION.md)
- [Derivatives OI Handling](./DERIVATIVES_OI_HANDLING.md)

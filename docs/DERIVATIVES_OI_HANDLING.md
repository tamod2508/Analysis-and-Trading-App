# Derivatives Data - Open Interest (OI) Handling

## Overview

This document explains how the system handles derivatives data with or without Open Interest (OI) field.

## Background

**Your Question:** "Derivatives includes options as well as futures but futures has no oi, how do we account for that?"

**Reality:** Both futures and options contracts typically have Open Interest data. However, OI data may not always be available due to:
- Data source limitations
- API response variations
- Missing or incomplete data
- Different derivative instrument types

## Solution

The system now treats OI as **optional but recommended** for derivatives data.

---

## Schema Design

### OptionsOHLCVSchema Structure

```python
DTYPE = np.dtype([
    ('timestamp', 'int64'),
    ('open', 'float32'),
    ('high', 'float32'),
    ('low', 'float32'),
    ('close', 'float32'),
    ('volume', 'int64'),
    ('oi', 'int64'),  # Always present in array, defaults to 0 if missing
])

REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
OPTIONAL_COLUMNS = ['oi']  # Common but not required
```

**Key Points:**
- Schema includes 'oi' field (7 fields total)
- 'oi' is NOT in REQUIRED_COLUMNS
- Missing OI data defaults to 0

---

## Data Flow

### 1. Data Conversion (`dict_to_options_array`)

**Input:** List of dicts from Kite API
```python
{
    'date': datetime,
    'open': float,
    'high': float,
    'low': float,
    'close': float,
    'volume': int,
    'oi': int,  # ← MAY BE MISSING
}
```

**Handling:**
```python
arr[i]['oi'] = row.get('oi', 0)  # Default to 0 if missing
```

**Output:** NumPy array with 'oi' field (0 if missing)

### 2. Validation (`DataValidator.validate`)

**Structure Check:**
- Only validates: `['open', 'high', 'low', 'close', 'volume']`
- Does NOT require 'oi' field

**OI Validation:**
- IF 'oi' column exists → Validate OI values
- IF 'oi' column missing → Issue **warning** (not error)

**Result:**
- Data with missing OI: ✅ **VALID** (with warning)
- Data with OI present: ✅ **VALID** (if OI values valid)

**Stats Returned:**
```python
stats['has_oi'] = True   # OI field present
stats['has_oi'] = False  # OI field missing
```

### 3. Database Storage (`HDF5Manager.save_ohlcv`)

**Storage:**
- Always creates array with 'oi' field
- Missing OI stored as 0
- No errors or failures

### 4. Data Retrieval (`HDF5Manager.get_ohlcv`)

**Returns:**
- DataFrame with 'oi' column
- 'oi' values are 0 if data was missing OI originally

---

## Validation Behavior

### With OI Data

```python
data = [
    {'date': ..., 'open': 100, ..., 'oi': 25000000},
    {'date': ..., 'open': 101, ..., 'oi': 25100000},
]

result = validator.validate(data, 'NFO', 'NIFTY25OCT24950CE', '5minute')
# ✅ VALID
# has_oi: True
# Warnings: 0
```

### Without OI Data

```python
data = [
    {'date': ..., 'open': 100, ..., 'volume': 1000000},  # No 'oi'
    {'date': ..., 'open': 101, ..., 'volume': 1100000},  # No 'oi'
]

result = validator.validate(data, 'NFO', 'NIFTY25OCT24950FUT', '5minute')
# ✅ VALID
# has_oi: False
# Warnings: 1 ("Missing 'oi' column for derivatives data...")
```

---

## Changes Made

### 1. `database/data_validator.py`

**Changed:**
- `_validate_structure()`: Removed 'oi' from required columns
- `validate()`: Added conditional OI validation
- `_validate_open_interest()`: Made defensive (checks for column existence)
- `_check_missing_values()`: Only checks OI if present
- `quick_validate()`: Gracefully handles missing OI
- `sanitize_data()`: Only fills OI if column exists

**Added:**
- Warning message when OI is missing for derivatives
- `stats['has_oi']` flag to indicate OI presence

### 2. `database/schema.py`

**Changed:**
- `OptionsOHLCVSchema.REQUIRED_COLUMNS`: Removed 'oi'
- `OptionsOHLCVSchema`: Added `OPTIONAL_COLUMNS = ['oi']`
- `dict_to_options_array()`: Already had `.get('oi', 0)` default
- Updated docstrings to clarify OI is optional

**No Breaking Changes:**
- Schema still has 7 fields (including 'oi')
- All existing code continues to work

### 3. `tests/test_derivatives_no_oi.py`

**Created:**
- New test for derivatives without OI field
- Verifies: conversion, validation, storage, retrieval
- Confirms: OI defaults to 0, validation warns but succeeds

---

## Test Results

### All Tests Passing ✅

```
✅ test_options_schema.py          (6/6 tests)
✅ test_derivatives_integration.py (with OI)
✅ test_derivatives_no_oi.py       (without OI)
```

### Test Coverage

1. **With OI data:**
   - Conversion works ✓
   - Validation passes ✓
   - Storage succeeds ✓
   - Retrieval correct ✓

2. **Without OI data:**
   - OI defaults to 0 ✓
   - Validation warns but passes ✓
   - Storage succeeds ✓
   - Retrieval shows OI=0 ✓

---

## Usage Examples

### Example 1: Fetching Options with OI

```python
client = KiteClient()
result = client.fetch_derivatives_by_symbol(
    exchange='NFO',
    symbol='NIFTY25OCT24950CE',
    from_date=start_date,
    to_date=end_date,
    interval='5minute'
)
# Will save with OI if available from API
```

### Example 2: Fetching Futures without OI

```python
# If Kite API doesn't return OI for futures
result = client.fetch_derivatives_by_symbol(
    exchange='NFO',
    symbol='NIFTY25OCTFUT',
    from_date=start_date,
    to_date=end_date,
    interval='day'
)
# Will still succeed, OI stored as 0
# Validation result will have warning
```

### Example 3: Manual Data with Missing OI

```python
data = [
    {'date': datetime.now(), 'open': 100, 'high': 102,
     'low': 99, 'close': 101, 'volume': 1000000}
]

db = HDF5Manager(segment='DERIVATIVES')
success = db.save_ohlcv('NFO', 'NIFTY25OCTFUT', 'day', data)
# ✓ Succeeds, OI stored as 0
```

---

## Benefits

1. **Flexibility:** Handles both complete and incomplete derivatives data
2. **No Data Loss:** Missing OI doesn't prevent storage
3. **Clear Feedback:** Warnings indicate when OI is missing
4. **Backward Compatible:** Existing code with OI continues to work
5. **Forward Compatible:** Can handle future derivative types

---

## Recommendations

### For Production Use

1. **Always check validation warnings:**
   ```python
   if result['validation'].warnings:
       for warning in result['validation'].warnings:
           logger.warning(warning)
   ```

2. **Check has_oi flag:**
   ```python
   if not result['validation'].stats.get('has_oi'):
       logger.info("OI data not available for this instrument")
   ```

3. **Filter by OI when analyzing:**
   ```python
   df = db.get_ohlcv('NFO', symbol, 'day')
   if (df['oi'] == 0).all():
       logger.warning(f"No OI data available for {symbol}")
   ```

### For Data Quality

1. Monitor OI availability across different instruments
2. Log when OI is missing to identify patterns
3. Consider separate handling for instruments without OI

---

## Summary

**Answer to Original Question:**

> "Derivatives includes options as well as futures but futures has no oi, how do we account for that?"

**Solution:**
- OI is **always present in the schema** (7-field array)
- OI is **optional in source data** (defaults to 0)
- Validation **warns but doesn't fail** when OI is missing
- System **gracefully handles both cases** (with/without OI)

This approach ensures maximum flexibility while maintaining data integrity.

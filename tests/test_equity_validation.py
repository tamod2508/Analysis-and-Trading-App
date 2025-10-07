"""
Test script for EQUITY data validation and HDF5 storage

This script:
1. Generates sample OHLCV data for NSE/BSE equities
2. Tests data validation (valid and invalid cases)
3. Tests HDF5 storage operations (save, read, append, delete)
4. Verifies data integrity
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

from config import config, Interval
from database.data_validator import DataValidator
from database.hdf5_manager import HDF5Manager
from database.schema import dict_to_ohlcv_array

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SampleDataGenerator:
    """Generate realistic sample OHLCV data for testing"""

    @staticmethod
    def generate_valid_daily_data(
        symbol: str = "RELIANCE",
        start_date: str = "2023-01-01",
        days: int = 100,
        base_price: float = 2500.0,
        volatility: float = 0.02
    ):
        """Generate valid daily OHLCV data"""
        dates = pd.date_range(start=start_date, periods=days, freq='D')
        data = []

        current_price = base_price

        for date in dates:
            # Random price movement
            change = np.random.randn() * volatility * current_price

            open_price = current_price
            close_price = current_price + change

            # Generate high and low
            high_price = max(open_price, close_price) * (1 + abs(np.random.randn()) * 0.01)
            low_price = min(open_price, close_price) * (1 - abs(np.random.randn()) * 0.01)

            # Ensure OHLC relationships
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            # Generate volume
            volume = int(np.random.uniform(1_000_000, 10_000_000))

            data.append({
                'date': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

            current_price = close_price

        return data

    @staticmethod
    def generate_valid_intraday_data(
        symbol: str = "RELIANCE",
        date: str = "2023-01-02",
        interval: str = "5minute",
        candles: int = 75,  # ~6.5 hours of trading
        base_price: float = 2500.0
    ):
        """Generate valid intraday OHLCV data"""
        start_time = pd.Timestamp(date) + pd.Timedelta(hours=9, minutes=15)

        if interval == "5minute":
            freq = '5T'
        elif interval == "15minute":
            freq = '15T'
        elif interval == "60minute":
            freq = '60T'
        else:
            freq = '5T'

        times = pd.date_range(start=start_time, periods=candles, freq=freq, tz='Asia/Kolkata')
        data = []

        current_price = base_price

        for timestamp in times:
            change = np.random.randn() * 0.005 * current_price

            open_price = current_price
            close_price = current_price + change

            high_price = max(open_price, close_price) * (1 + abs(np.random.randn()) * 0.003)
            low_price = min(open_price, close_price) * (1 - abs(np.random.randn()) * 0.003)

            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            volume = int(np.random.uniform(50_000, 500_000))

            data.append({
                'date': timestamp,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

            current_price = close_price

        return data

    @staticmethod
    def generate_invalid_data_cases():
        """Generate various invalid data cases for testing"""
        base_date = pd.Timestamp('2023-01-01')

        cases = {
            'invalid_ohlc_high_too_low': {
                'date': base_date,
                'open': 100.0,
                'high': 95.0,  # High < Open (INVALID)
                'low': 90.0,
                'close': 98.0,
                'volume': 100000
            },
            'invalid_ohlc_low_too_high': {
                'date': base_date + timedelta(days=1),
                'open': 100.0,
                'high': 105.0,
                'low': 102.0,  # Low > Open (INVALID)
                'close': 103.0,
                'volume': 100000
            },
            'negative_price': {
                'date': base_date + timedelta(days=2),
                'open': -100.0,  # Negative price (INVALID)
                'high': -95.0,
                'low': -105.0,
                'close': -98.0,
                'volume': 100000
            },
            'zero_price': {
                'date': base_date + timedelta(days=3),
                'open': 0.0,  # Zero price (INVALID)
                'high': 0.0,
                'low': 0.0,
                'close': 0.0,
                'volume': 100000
            },
            'negative_volume': {
                'date': base_date + timedelta(days=4),
                'open': 100.0,
                'high': 105.0,
                'low': 98.0,
                'close': 103.0,
                'volume': -100000  # Negative volume (INVALID)
            },
            'excessive_price': {
                'date': base_date + timedelta(days=5),
                'open': 2_000_000.0,  # Price > MAX_PRICE (INVALID)
                'high': 2_100_000.0,
                'low': 1_900_000.0,
                'close': 2_050_000.0,
                'volume': 100000
            },
            'missing_values': {
                'date': base_date + timedelta(days=6),
                'open': np.nan,  # Missing value (INVALID)
                'high': 105.0,
                'low': 98.0,
                'close': 103.0,
                'volume': 100000
            },
        }

        return cases


def test_data_validation():
    """Test data validation with various scenarios"""
    print("\n" + "="*80)
    print("TEST 1: DATA VALIDATION")
    print("="*80)

    validator = DataValidator()
    generator = SampleDataGenerator()

    # Test 1: Valid daily data
    print("\n--- Test 1.1: Valid Daily Data ---")
    valid_data = generator.generate_valid_daily_data("RELIANCE", days=30)
    result = validator.validate(
        data=valid_data,
        exchange="NSE",
        symbol="RELIANCE",
        interval="day"
    )
    print(result.summary())
    assert result.is_valid, "Valid data should pass validation"

    # Test 2: Valid intraday data
    print("\n--- Test 1.2: Valid Intraday Data (5minute) ---")
    intraday_data = generator.generate_valid_intraday_data("TCS", interval="5minute")
    result = validator.validate(
        data=intraday_data,
        exchange="NSE",
        symbol="TCS",
        interval="5minute"
    )
    print(result.summary())
    assert result.is_valid, "Valid intraday data should pass validation"

    # Test 3: Invalid data cases
    print("\n--- Test 1.3: Invalid Data Cases ---")
    invalid_cases = generator.generate_invalid_data_cases()

    for case_name, case_data in invalid_cases.items():
        print(f"\nTesting: {case_name}")
        result = validator.validate(
            data=[case_data],
            exchange="NSE",
            symbol="TEST",
            interval="day"
        )
        print(f"  Valid: {result.is_valid}")
        if result.errors:
            print(f"  Errors: {result.errors[0]}")
        # Invalid cases should fail validation
        assert not result.is_valid, f"{case_name} should fail validation"

    # Test 4: Duplicate timestamps
    print("\n--- Test 1.4: Duplicate Timestamps ---")
    dup_data = generator.generate_valid_daily_data(days=10)
    dup_data.append(dup_data[5])  # Add duplicate
    result = validator.validate(
        data=dup_data,
        exchange="NSE",
        symbol="RELIANCE",
        interval="day"
    )
    print(result.summary())
    assert not result.is_valid, "Duplicate timestamps should fail validation"

    print("\n✅ All validation tests passed!")


def test_hdf5_operations():
    """Test HDF5 storage operations"""
    print("\n" + "="*80)
    print("TEST 2: HDF5 STORAGE OPERATIONS")
    print("="*80)

    # Use test database
    test_db_path = config.HDF5_DIR / "TEST_EQUITY.h5"
    if test_db_path.exists():
        test_db_path.unlink()
        print(f"Removed existing test database: {test_db_path}")

    # Create manager for EQUITY segment
    manager = HDF5Manager(segment='EQUITY')
    # Override with test path
    manager.db_path = test_db_path
    if test_db_path.exists():
        test_db_path.unlink()
    manager._initialize_database()

    generator = SampleDataGenerator()

    # Test 1: Save daily data
    print("\n--- Test 2.1: Save Daily Data ---")
    daily_data = generator.generate_valid_daily_data("RELIANCE", days=100)
    success = manager.save_ohlcv(
        exchange="NSE",
        symbol="RELIANCE",
        interval=Interval.DAY,
        data=daily_data,
        overwrite=False
    )
    assert success, "Failed to save daily data"
    print(f"✅ Saved {len(daily_data)} daily records for RELIANCE")

    # Test 2: Save intraday data (multiple intervals)
    print("\n--- Test 2.2: Save Intraday Data (Multiple Intervals) ---")
    for interval in ["5minute", "15minute", "60minute"]:
        intraday_data = generator.generate_valid_intraday_data(
            "RELIANCE",
            interval=interval,
            candles=75
        )
        success = manager.save_ohlcv(
            exchange="NSE",
            symbol="RELIANCE",
            interval=interval,
            data=intraday_data
        )
        assert success, f"Failed to save {interval} data"
        print(f"✅ Saved {len(intraday_data)} {interval} records for RELIANCE")

    # Test 3: Save data for multiple symbols
    print("\n--- Test 2.3: Save Data for Multiple Symbols ---")
    symbols = ["TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    for symbol in symbols:
        data = generator.generate_valid_daily_data(symbol, days=50)
        manager.save_ohlcv("NSE", symbol, "day", data)
    print(f"✅ Saved data for {len(symbols)} symbols")

    # Test 4: Read data
    print("\n--- Test 2.4: Read Data ---")
    df = manager.get_ohlcv("NSE", "RELIANCE", Interval.DAY)
    assert df is not None, "Failed to read data"
    assert len(df) == 100, f"Expected 100 rows, got {len(df)}"
    print(f"✅ Read {len(df)} records")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"   Columns: {list(df.columns)}")
    print(f"\n   First 3 rows:")
    print(df.head(3))

    # Test 5: Read with date filter
    print("\n--- Test 2.5: Read with Date Filter ---")
    df_filtered = manager.get_ohlcv(
        "NSE",
        "RELIANCE",
        Interval.DAY,
        start_date=datetime(2023, 2, 1),
        end_date=datetime(2023, 3, 1)
    )
    print(f"✅ Read {len(df_filtered)} filtered records")

    # Test 6: Append data
    print("\n--- Test 2.6: Append New Data ---")
    new_data = generator.generate_valid_daily_data("RELIANCE", start_date="2023-04-11", days=30)
    success = manager.save_ohlcv("NSE", "RELIANCE", "day", new_data, overwrite=False)
    assert success, "Failed to append data"

    df_after = manager.get_ohlcv("NSE", "RELIANCE", "day")
    print(f"✅ Appended data. Total records: {len(df_after)}")

    # Test 7: Get data info
    print("\n--- Test 2.7: Get Dataset Info ---")
    info = manager.get_data_info("NSE", "RELIANCE", "day")
    print(f"Dataset info:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Test 8: List operations
    print("\n--- Test 2.8: List Operations ---")
    symbols = manager.list_symbols("NSE")
    print(f"✅ Symbols in database: {symbols}")

    intervals = manager.list_intervals("NSE", "RELIANCE")
    print(f"✅ Intervals for RELIANCE: {intervals}")

    # Test 9: Get database stats
    print("\n--- Test 2.9: Database Statistics ---")
    stats = manager.get_database_stats()
    print(f"Database statistics:")
    print(f"  File size: {stats['file_size_mb']} MB")
    print(f"  Segment: {stats['segment']}")
    print(f"  Total symbols: {stats['total_symbols']}")
    print(f"  Total datasets: {stats['total_datasets']}")
    print(f"  Total rows: {stats['total_rows']}")
    print(f"  Compression: {stats['compression']}")
    for exchange, exch_stats in stats['exchanges'].items():
        print(f"  {exchange}: {exch_stats['symbols']} symbols, {exch_stats['datasets']} datasets")

    # Test 10: BSE data
    print("\n--- Test 2.10: BSE Exchange Data ---")
    bse_data = generator.generate_valid_daily_data("BSE_STOCK", days=30)
    manager.save_ohlcv("BSE", "BSE_STOCK", "day", bse_data)
    df_bse = manager.get_ohlcv("BSE", "BSE_STOCK", "day")
    assert df_bse is not None and len(df_bse) == 30
    print(f"✅ Saved and read {len(df_bse)} BSE records")

    # Test 11: Delete data
    print("\n--- Test 2.11: Delete Operations ---")
    manager.delete_ohlcv("NSE", "TCS", "day")
    print(f"✅ Deleted TCS daily data")

    # Verify the interval is deleted
    tcs_intervals = manager.list_intervals("NSE", "TCS")
    assert "day" not in tcs_intervals, "TCS daily interval should be deleted"
    print(f"   TCS intervals after delete: {tcs_intervals}")

    # Delete all TCS data
    manager.delete_ohlcv("NSE", "INFY")  # Delete all intervals for INFY
    symbols_after = manager.list_symbols("NSE")
    assert "INFY" not in symbols_after, "INFY should be completely deleted"
    print(f"   Symbols after complete delete: {symbols_after}")

    print("\n✅ All HDF5 operations tests passed!")

    # Cleanup
    print(f"\n--- Cleanup ---")
    print(f"Test database location: {test_db_path}")
    print(f"File size: {test_db_path.stat().st_size / (1024**2):.2f} MB")

    # Auto-cleanup test database
    test_db_path.unlink()
    print("✅ Test database deleted")


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n" + "="*80)
    print("TEST 3: EDGE CASES")
    print("="*80)

    validator = DataValidator()
    generator = SampleDataGenerator()

    # Test 1: Empty data
    print("\n--- Test 3.1: Empty Data ---")
    result = validator.validate([], "NSE", "TEST", "day")
    print(f"  Valid: {result.is_valid}")
    assert not result.is_valid, "Empty data should fail"

    # Test 2: Single candle
    print("\n--- Test 3.2: Single Candle ---")
    single_data = generator.generate_valid_daily_data(days=1)
    result = validator.validate(single_data, "NSE", "TEST", "day")
    print(f"  Valid: {result.is_valid}")
    assert result.is_valid, "Single candle should be valid"

    # Test 3: Large dataset
    print("\n--- Test 3.3: Large Dataset (1000 days) ---")
    large_data = generator.generate_valid_daily_data(days=1000)
    result = validator.validate(large_data, "NSE", "TEST", "day")
    print(f"  Valid: {result.is_valid}")
    print(f"  Rows: {result.stats['total_rows']}")
    assert result.is_valid, "Large dataset should be valid"

    # Test 4: Zero volume (warning, not error)
    print("\n--- Test 3.4: Zero Volume ---")
    zero_vol_data = [{
        'date': pd.Timestamp('2023-01-01'),
        'open': 100.0,
        'high': 105.0,
        'low': 98.0,
        'close': 103.0,
        'volume': 0  # Zero volume
    }]
    result = validator.validate(zero_vol_data, "NSE", "TEST", "day")
    print(f"  Valid: {result.is_valid}")
    print(f"  Warnings: {len(result.warnings)}")
    if result.warnings:
        print(f"    {result.warnings[0]}")

    # Test 5: Circuit limit price spike
    print("\n--- Test 3.5: Circuit Limit Price Spike (20%) ---")
    spike_data = [
        {'date': pd.Timestamp('2023-01-01'), 'open': 100, 'high': 105, 'low': 98, 'close': 103, 'volume': 100000},
        {'date': pd.Timestamp('2023-01-02'), 'open': 103, 'high': 124, 'low': 103, 'close': 123.6, 'volume': 200000},  # 20% up
    ]
    result = validator.validate(spike_data, "NSE", "TEST", "day")
    print(f"  Valid: {result.is_valid}")
    print(f"  Warnings: {len(result.warnings)}")
    print(f"  Anomalies: {len(result.anomalies)}")

    print("\n✅ All edge case tests passed!")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("EQUITY DATA VALIDATION & STORAGE TEST SUITE")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Run tests
        test_data_validation()
        test_hdf5_operations()
        test_edge_cases()

        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_all_tests()

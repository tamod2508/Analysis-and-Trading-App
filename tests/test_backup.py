"""
Comprehensive test suite for HDF5 database backup functionality
Tests backup creation, cleanup, and recovery
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import h5py
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.hdf5_manager import HDF5Manager
from database.schema import dict_to_ohlcv_array
from config import config


def print_header(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_subheader(title):
    """Print a formatted subsection header"""
    print(f"\n🔹 {title}")
    print("-" * 70)


def setup_test_data():
    """Create test data for backup testing"""
    print_subheader("Setting up test data")

    # Create a manager with test segment
    manager = HDF5Manager(segment='TEST')

    # Sample OHLCV data - need at least 10 records for HDF5 chunk size
    test_data = []
    base_price = 100.0

    for i in range(20):  # Create 20 records to be safe
        date = datetime(2024, 1, 1) + timedelta(days=i)
        price_variation = np.random.uniform(-2, 2)
        open_price = base_price + price_variation
        close_price = open_price + np.random.uniform(-1, 1)
        high_price = max(open_price, close_price) + np.random.uniform(0, 1)
        low_price = min(open_price, close_price) - np.random.uniform(0, 1)
        volume = int(np.random.uniform(10000, 20000))

        test_data.append({
            'date': date,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

        base_price = close_price  # Carry forward price

    # Save test data
    manager.save_ohlcv(
        exchange='NSE',
        symbol='TESTSTOCK',
        interval='day',
        data=test_data,
        overwrite=True
    )

    print(f"✅ Created test data: NSE/TESTSTOCK with {len(test_data)} records")
    return manager


def cleanup_test_data(manager):
    """Clean up test data and backups"""
    print_subheader("Cleaning up test data")

    try:
        # Remove test database
        if manager.db_path.exists():
            manager.db_path.unlink()
            print(f"✅ Removed test database: {manager.db_path.name}")

        # Remove test backups
        test_backups = list(config.BACKUP_DIR.glob('TEST_backup_*.h5'))
        for backup in test_backups:
            backup.unlink()
            print(f"✅ Removed test backup: {backup.name}")

        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


def test_backup_creation():
    """Test basic backup creation"""
    print_header("TEST 1: Backup Creation")

    manager = setup_test_data()

    try:
        # Create backup
        backup_path = manager.create_backup()

        # Verify backup exists
        if not backup_path.exists():
            print("❌ Backup file was not created")
            return False

        print(f"✅ Backup created: {backup_path.name}")

        # Check file size
        original_size = manager.db_path.stat().st_size
        backup_size = backup_path.stat().st_size

        print(f"   Original size: {original_size:,} bytes")
        print(f"   Backup size: {backup_size:,} bytes")

        if backup_size != original_size:
            print("❌ Backup size doesn't match original")
            return False

        print("✅ Backup size matches original")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data(manager)


def test_backup_integrity():
    """Test backup file integrity and data verification"""
    print_header("TEST 2: Backup Integrity")

    manager = setup_test_data()

    try:
        # Create backup
        backup_path = manager.create_backup()

        # Read data from original
        original_data = manager.get_ohlcv('NSE', 'TESTSTOCK', 'day')

        # Read data from backup
        with h5py.File(backup_path, 'r') as backup_file:
            dataset_path = 'data/NSE/TESTSTOCK/day'

            if dataset_path not in backup_file:
                print(f"❌ Dataset not found in backup: {dataset_path}")
                return False

            backup_dataset = backup_file[dataset_path]

            # Convert to structured array
            backup_data = backup_dataset[:]

            # Compare lengths
            if len(original_data) != len(backup_data):
                print(f"❌ Data length mismatch: {len(original_data)} vs {len(backup_data)}")
                return False

            print(f"✅ Data length matches: {len(backup_data)} records")

            # Compare values (sample first record)
            original_first = original_data.iloc[0]
            backup_first = backup_data[0]

            print(f"\n   First record comparison:")
            print(f"   Original close: {original_first['close']:.2f}")
            print(f"   Backup close: {backup_first['close']:.2f}")

            if not np.isclose(original_first['close'], backup_first['close']):
                print("❌ Data values don't match")
                return False

            print("✅ Backup data integrity verified")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data(manager)


def test_backup_cleanup():
    """Test automatic cleanup of old backups"""
    print_header("TEST 3: Backup Cleanup (MAX_BACKUPS)")

    manager = setup_test_data()

    try:
        # Get MAX_BACKUPS setting
        max_backups = config.MAX_BACKUPS
        print(f"   MAX_BACKUPS setting: {max_backups}")

        # Create more backups than MAX_BACKUPS
        num_backups_to_create = max_backups + 2
        created_backups = []

        print(f"\n   Creating {num_backups_to_create} backups...")

        for i in range(num_backups_to_create):
            # Create backup with custom path to control timing
            import time
            time.sleep(0.1)  # Ensure different timestamps

            backup_path = manager.create_backup()
            created_backups.append(backup_path)
            print(f"   • Created backup {i+1}: {backup_path.name}")

        # Count remaining backups
        remaining_backups = list(config.BACKUP_DIR.glob('TEST_backup_*.h5'))
        num_remaining = len(remaining_backups)

        print(f"\n   Backups remaining: {num_remaining}")
        print(f"   Expected: {max_backups} (MAX_BACKUPS)")

        if num_remaining > max_backups:
            print(f"❌ Too many backups remaining: {num_remaining} > {max_backups}")
            return False

        # Check that the newest backups are kept
        remaining_names = [b.name for b in remaining_backups]
        newest_backups = created_backups[-max_backups:]

        for backup in newest_backups:
            if backup.name not in remaining_names:
                print(f"❌ Newest backup was deleted: {backup.name}")
                return False

        print(f"✅ Cleanup working correctly: kept {num_remaining} newest backups")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data(manager)


def test_backup_recovery():
    """Test recovery from backup"""
    print_header("TEST 4: Backup Recovery")

    manager = setup_test_data()

    try:
        # Create backup
        backup_path = manager.create_backup()
        print(f"✅ Created backup: {backup_path.name}")

        # Read original data
        original_data = manager.get_ohlcv('NSE', 'TESTSTOCK', 'day')
        original_count = len(original_data)

        # Simulate data corruption/deletion
        manager.delete_ohlcv('NSE', 'TESTSTOCK')
        print("   Deleted original data (simulating corruption)")

        # Verify data is gone
        deleted_data = manager.get_ohlcv('NSE', 'TESTSTOCK', 'day')
        if deleted_data is not None:
            print("❌ Data still exists after deletion")
            return False

        print("✅ Data successfully deleted")

        # Restore from backup
        print(f"\n   Restoring from backup...")

        # Close current file handles
        import gc
        gc.collect()

        # Copy backup over original
        shutil.copy2(backup_path, manager.db_path)

        # Verify recovery
        recovered_data = manager.get_ohlcv('NSE', 'TESTSTOCK', 'day')

        if recovered_data is None:
            print("❌ Recovery failed: no data found")
            return False

        recovered_count = len(recovered_data)

        print(f"   Original records: {original_count}")
        print(f"   Recovered records: {recovered_count}")

        if recovered_count != original_count:
            print("❌ Recovery incomplete: record count mismatch")
            return False

        # Compare values
        if not np.allclose(original_data['close'].values, recovered_data['close'].values):
            print("❌ Recovered data doesn't match original")
            return False

        print("✅ Data successfully recovered from backup")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_data(manager)


def test_custom_backup_path():
    """Test backup with custom path"""
    print_header("TEST 5: Custom Backup Path")

    manager = setup_test_data()

    try:
        # Create custom backup path
        custom_path = config.BACKUP_DIR / "custom_test_backup.h5"

        # Create backup with custom path
        backup_path = manager.create_backup(backup_path=custom_path)

        if backup_path != custom_path:
            print(f"❌ Backup path mismatch: {backup_path} != {custom_path}")
            return False

        if not custom_path.exists():
            print("❌ Custom backup not created")
            return False

        print(f"✅ Custom backup created: {custom_path.name}")

        # Cleanup custom backup
        custom_path.unlink()

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data(manager)


def test_backup_metadata():
    """Test backup preserves metadata"""
    print_header("TEST 6: Backup Metadata Preservation")

    manager = setup_test_data()

    try:
        # Create backup
        backup_path = manager.create_backup()

        # Read metadata from original
        with manager.open_file('r') as original_file:
            original_version = original_file.attrs.get('db_version', 'unknown')
            original_created = original_file.attrs.get('created_at', 'unknown')

        # Read metadata from backup
        with h5py.File(backup_path, 'r') as backup_file:
            backup_version = backup_file.attrs.get('db_version', 'unknown')
            backup_created = backup_file.attrs.get('created_at', 'unknown')

        print(f"   Original DB Version: {original_version}")
        print(f"   Backup DB Version: {backup_version}")

        if original_version != backup_version:
            print("❌ Metadata mismatch: db_version")
            return False

        print("✅ Metadata preserved in backup")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data(manager)


def test_auto_backup_setting():
    """Test AUTO_BACKUP configuration"""
    print_header("TEST 7: AUTO_BACKUP Configuration")

    print(f"   AUTO_BACKUP: {config.AUTO_BACKUP}")
    print(f"   MAX_BACKUPS: {config.MAX_BACKUPS}")
    print(f"   BACKUP_DIR: {config.BACKUP_DIR}")

    # Verify backup directory exists
    if not config.BACKUP_DIR.exists():
        print("❌ Backup directory doesn't exist")
        return False

    print(f"✅ Backup directory exists: {config.BACKUP_DIR}")

    # Check if it's writable
    test_file = config.BACKUP_DIR / ".test_write"
    try:
        test_file.touch()
        test_file.unlink()
        print("✅ Backup directory is writable")
        return True
    except Exception as e:
        print(f"❌ Backup directory not writable: {e}")
        return False


def run_all_tests():
    """Run all backup tests and report results"""
    print("\n" + "="*70)
    print("  🧪 HDF5 BACKUP - COMPREHENSIVE TEST SUITE")
    print("="*70)

    tests = [
        ("AUTO_BACKUP Configuration", test_auto_backup_setting),
        ("Backup Creation", test_backup_creation),
        ("Backup Integrity", test_backup_integrity),
        ("Backup Cleanup", test_backup_cleanup),
        ("Backup Recovery", test_backup_recovery),
        ("Custom Backup Path", test_custom_backup_path),
        ("Metadata Preservation", test_backup_metadata),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} FAILED with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed\n")

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")

    print("\n" + "="*70)

    if passed == total:
        print("  ✅ ALL TESTS PASSED - BACKUP SYSTEM READY!")
    else:
        print(f"  ⚠️  {total - passed} TEST(S) FAILED - REVIEW REQUIRED")

    print("="*70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

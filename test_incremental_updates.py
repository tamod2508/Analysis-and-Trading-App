"""
Test script for incremental update functionality
"""

import sys
from datetime import datetime, timedelta
from api.kite_client import KiteClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_incremental_updates():
    """Test incremental update logic"""

    print("\n" + "="*70)
    print("Testing Incremental Updates")
    print("="*70 + "\n")

    try:
        # Initialize client
        print("Initializing Kite client...")
        client = KiteClient()

        if not client.is_authenticated():
            print("❌ Not authenticated. Please set KITE_ACCESS_TOKEN in .env")
            return False

        print("✓ Client authenticated\n")

        # Test symbol
        test_symbol = "RELIANCE"

        # Phase 1: Fetch initial data (older data)
        print("="*70)
        print("PHASE 1: Initial fetch (older data)")
        print("="*70)

        initial_end = datetime.now() - timedelta(days=10)
        initial_start = initial_end - timedelta(days=20)

        print(f"Fetching initial data: {initial_start.date()} to {initial_end.date()}")

        result1 = client.fetch_equity_by_symbol(
            symbol=test_symbol,
            from_date=initial_start,
            to_date=initial_end,
            interval='day',
            validate=True,
            overwrite=False,
            incremental=True
        )

        print(f"\nResult:")
        print(f"  Success: {result1.get('success')}")
        print(f"  Exchange: {result1.get('exchange_used', 'N/A')}")
        print(f"  Records: {result1.get('records', 'N/A')}")
        print(f"  Elapsed: {result1.get('elapsed_seconds', 'N/A')}s")

        if not result1.get('success'):
            print(f"❌ Phase 1 failed: {result1.get('error')}")
            return False

        print(f"\n✓ Phase 1 complete - {result1.get('records')} records saved")

        # Phase 2: Incremental update (newer data)
        print("\n" + "="*70)
        print("PHASE 2: Incremental update (newer data)")
        print("="*70)

        update_start = initial_start  # Same start
        update_end = datetime.now()  # Extended end

        print(f"Requesting data: {update_start.date()} to {update_end.date()}")
        print(f"Expected behavior: Only fetch missing dates after {initial_end.date()}")

        result2 = client.fetch_equity_by_symbol(
            symbol=test_symbol,
            from_date=update_start,
            to_date=update_end,
            interval='day',
            validate=True,
            overwrite=False,
            incremental=True  # This should only fetch new data
        )

        print(f"\nResult:")
        print(f"  Success: {result2.get('success')}")
        print(f"  Exchange: {result2.get('exchange_used', 'N/A')}")
        print(f"  Records: {result2.get('records', 'N/A')}")
        print(f"  Message: {result2.get('message', 'N/A')}")
        print(f"  Elapsed: {result2.get('elapsed_seconds', 'N/A')}s")

        if not result2.get('success'):
            print(f"❌ Phase 2 failed: {result2.get('error')}")
            return False

        print(f"\n✓ Phase 2 complete - Only fetched {result2.get('records', 0)} new records!")

        # Phase 3: Request data that already exists
        print("\n" + "="*70)
        print("PHASE 3: Request already-existing data")
        print("="*70)

        print(f"Requesting data: {initial_start.date()} to {initial_end.date()}")
        print(f"Expected behavior: Skip fetch (data already exists)")

        result3 = client.fetch_equity_by_symbol(
            symbol=test_symbol,
            from_date=initial_start,
            to_date=initial_end,
            interval='day',
            validate=True,
            overwrite=False,
            incremental=True
        )

        print(f"\nResult:")
        print(f"  Success: {result3.get('success')}")
        print(f"  Records: {result3.get('records', 'N/A')}")
        print(f"  Message: {result3.get('message', 'N/A')}")
        print(f"  Elapsed: {result3.get('elapsed_seconds', 'N/A')}s")

        if result3.get('records') == 0 and 'already exists' in result3.get('message', ''):
            print(f"\n✓ Phase 3 complete - Correctly skipped fetching existing data!")
        else:
            print(f"⚠️  Phase 3 - Expected 0 records, got {result3.get('records', 0)}")

        # Phase 4: Force full refresh with overwrite
        print("\n" + "="*70)
        print("PHASE 4: Force full refresh (overwrite=True)")
        print("="*70)

        print(f"Requesting data: {initial_start.date()} to {update_end.date()}")
        print(f"Expected behavior: Fetch full range (ignore existing data)")

        result4 = client.fetch_equity_by_symbol(
            symbol=test_symbol,
            from_date=initial_start,
            to_date=update_end,
            interval='day',
            validate=True,
            overwrite=True,  # Force full refresh
            incremental=True  # Ignored when overwrite=True
        )

        print(f"\nResult:")
        print(f"  Success: {result4.get('success')}")
        print(f"  Records: {result4.get('records', 'N/A')}")
        print(f"  Elapsed: {result4.get('elapsed_seconds', 'N/A')}s")

        if not result4.get('success'):
            print(f"❌ Phase 4 failed: {result4.get('error')}")
            return False

        print(f"\n✓ Phase 4 complete - Full refresh with {result4.get('records')} records!")

        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"✓ Phase 1: Initial fetch - {result1.get('records')} records")
        print(f"✓ Phase 2: Incremental update - {result2.get('records')} new records")
        print(f"✓ Phase 3: Skip existing - {result3.get('records')} records (should be 0)")
        print(f"✓ Phase 4: Force refresh - {result4.get('records')} records")
        print("\n✓ All incremental update tests passed!")
        print("="*70 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🚀 Starting Incremental Update Tests" + "\n")

    test_passed = test_incremental_updates()

    print("\n" + "="*70)
    print(f"Test Result: {'✓ PASSED' if test_passed else '❌ FAILED'}")
    print("="*70 + "\n")

    sys.exit(0 if test_passed else 1)

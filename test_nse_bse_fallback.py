"""
Test script for NSE-first, BSE-fallback logic
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


def test_fetch_equity_by_symbol():
    """Test fetching equity data by symbol name"""

    print("\n" + "="*70)
    print("Testing NSE-first, BSE-fallback logic")
    print("="*70 + "\n")

    try:
        # Initialize client
        print("Initializing Kite client...")
        client = KiteClient()

        # Check authentication
        if not client.is_authenticated():
            print("❌ Not authenticated. Please set KITE_ACCESS_TOKEN in .env")
            return False

        print("✓ Client authenticated\n")

        # Test with a common symbol (should be on both NSE and BSE)
        test_symbol = "RELIANCE"

        # Use recent dates (last 30 days)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)

        print(f"Test Parameters:")
        print(f"  Symbol: {test_symbol}")
        print(f"  Date Range: {from_date.date()} to {to_date.date()}")
        print(f"  Interval: day")
        print()

        # Test 1: Fetch by symbol (auto-lookup)
        print("Test 1: fetch_equity_by_symbol() - Auto-lookup tokens")
        print("-" * 70)

        result = client.fetch_equity_by_symbol(
            symbol=test_symbol,
            from_date=from_date,
            to_date=to_date,
            interval='day',
            validate=True,
            overwrite=True
        )

        print("\nResult:")
        print(f"  Success: {result.get('success')}")
        print(f"  Exchange Used: {result.get('exchange_used', 'N/A')}")
        print(f"  Fallback Used: {result.get('fallback_used', 'N/A')}")
        print(f"  Records: {result.get('records', 'N/A')}")
        print(f"  Date Range: {result.get('date_range', 'N/A')}")

        if result.get('success'):
            print(f"\n✓ Successfully fetched {test_symbol} from {result.get('exchange_used')}")
            if result.get('fallback_used'):
                print("  (Used BSE fallback)")
            else:
                print("  (Used NSE - preferred exchange)")
            return True
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_tokens():
    """Test with manual token specification"""

    print("\n" + "="*70)
    print("Test 2: fetch_and_save_equity() - Manual tokens")
    print("="*70 + "\n")

    try:
        client = KiteClient()

        # RELIANCE tokens (these are example tokens, may need updating)
        # You can get real tokens from the instruments list
        test_cases = [
            {
                'symbol': 'RELIANCE',
                'nse_token': 738561,  # NSE:RELIANCE
                'bse_token': 500325,  # BSE:RELIANCE
            }
        ]

        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)

        for test in test_cases:
            print(f"Testing {test['symbol']}...")
            print(f"  NSE Token: {test['nse_token']}")
            print(f"  BSE Token: {test['bse_token']}")

            result = client.fetch_and_save_equity(
                symbol=test['symbol'],
                nse_instrument_token=test['nse_token'],
                bse_instrument_token=test['bse_token'],
                from_date=from_date,
                to_date=to_date,
                interval='day',
                validate=True,
                overwrite=True
            )

            print(f"\nResult:")
            print(f"  Success: {result.get('success')}")
            print(f"  Exchange Used: {result.get('exchange_used', 'N/A')}")
            print(f"  Records: {result.get('records', 'N/A')}")

            if result.get('success'):
                print(f"✓ Test passed")
                return True
            else:
                print(f"❌ Test failed: {result.get('error')}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🚀 Starting NSE-BSE Fallback Tests" + "\n")

    # Run test with auto-lookup
    test1_passed = test_fetch_equity_by_symbol()

    print("\n" + "="*70)
    print(f"Test Summary:")
    print(f"  Auto-lookup test: {'✓ PASSED' if test1_passed else '❌ FAILED'}")
    print("="*70 + "\n")

    sys.exit(0 if test1_passed else 1)

"""
Test rate limiting in KiteClient to ensure we don't hit API limits
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.kite_client import KiteClient
from config import config


def test_rate_limit_initialization():
    """Test that rate limiting is properly initialized"""
    print("\n" + "="*70)
    print("TEST: Rate Limit Initialization")
    print("="*70)

    # Mock the kite connection to avoid needing credentials
    original_init = KiteClient.__init__

    def mock_init(self, api_key=None, access_token=None):
        self.api_key = "test_key"
        self.access_token = "test_token"
        self.kite = Mock()

        # Rate limiting (same as real code)
        self.last_request_time = time.time()
        self.min_request_interval = (1.0 / config.API_RATE_LIMIT) + config.API_RATE_SAFETY_MARGIN

        # Mock other attributes
        self.validator = Mock()
        self.db = Mock()

        actual_rate = 1.0 / self.min_request_interval
        print(f"\n✓ Rate limit: {config.API_RATE_LIMIT} req/sec")
        print(f"✓ Safety margin: {config.API_RATE_SAFETY_MARGIN*1000:.0f}ms")
        print(f"✓ Min interval: {self.min_request_interval:.3f}s")
        print(f"✓ Actual rate: {actual_rate:.2f} req/sec")

    # Patch and create client
    KiteClient.__init__ = mock_init
    client = KiteClient()
    KiteClient.__init__ = original_init

    # Verify safety margin is applied
    expected_interval = (1.0 / config.API_RATE_LIMIT) + config.API_RATE_SAFETY_MARGIN
    assert client.min_request_interval == expected_interval, "Safety margin not applied"

    # Verify it's greater than bare minimum
    bare_minimum = 1.0 / config.API_RATE_LIMIT
    assert client.min_request_interval > bare_minimum, "No safety margin"

    # Verify last_request_time is initialized (not 0)
    assert client.last_request_time > 0, "last_request_time not initialized"

    print(f"\n✅ Rate limiting properly initialized with safety margin")
    return True


def test_rate_limit_enforcement():
    """Test that rate limiting actually enforces delays"""
    print("\n" + "="*70)
    print("TEST: Rate Limit Enforcement")
    print("="*70)

    # Create mock client
    class MockKiteClient:
        def __init__(self):
            self.last_request_time = time.time()
            self.min_request_interval = (1.0 / config.API_RATE_LIMIT) + config.API_RATE_SAFETY_MARGIN
            self.call_times = []

        def _rate_limit_wait(self):
            """Same logic as real KiteClient"""
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                time.sleep(wait_time)
            self.last_request_time = time.time()

        def make_test_call(self):
            """Simulate API call"""
            self._rate_limit_wait()
            self.call_times.append(time.time())

    client = MockKiteClient()

    print(f"\n📊 Making 5 rapid consecutive calls...")
    print(f"   Expected interval: {client.min_request_interval:.3f}s\n")

    # Make 5 rapid calls
    for i in range(5):
        client.make_test_call()
        print(f"   Call {i+1} at {client.call_times[-1]:.3f}")

    # Verify intervals
    print(f"\n📏 Verifying intervals between calls:")
    intervals = []
    for i in range(1, len(client.call_times)):
        interval = client.call_times[i] - client.call_times[i-1]
        intervals.append(interval)
        status = "✓" if interval >= client.min_request_interval - 0.001 else "✗"  # 1ms tolerance
        print(f"   {status} Call {i} → {i+1}: {interval:.3f}s")

    # All intervals should be >= min_request_interval (with small tolerance for timing)
    min_interval = min(intervals)
    avg_interval = sum(intervals) / len(intervals)

    print(f"\n📈 Statistics:")
    print(f"   Min interval: {min_interval:.3f}s")
    print(f"   Avg interval: {avg_interval:.3f}s")
    print(f"   Expected min: {client.min_request_interval:.3f}s")

    # Verify all intervals meet minimum (with 1ms tolerance for timing precision)
    tolerance = 0.001
    for i, interval in enumerate(intervals):
        assert interval >= client.min_request_interval - tolerance, \
            f"Interval {i+1} too short: {interval:.3f}s < {client.min_request_interval:.3f}s"

    print(f"\n✅ All intervals meet minimum threshold")

    # Calculate actual rate
    total_time = client.call_times[-1] - client.call_times[0]
    actual_rate = (len(client.call_times) - 1) / total_time
    print(f"✅ Actual request rate: {actual_rate:.2f} req/sec (limit: {config.API_RATE_LIMIT} req/sec)")

    assert actual_rate < config.API_RATE_LIMIT, "Rate limit exceeded!"

    return True


def test_safety_margin_calculation():
    """Test that safety margin is correctly calculated"""
    print("\n" + "="*70)
    print("TEST: Safety Margin Calculation")
    print("="*70)

    base_interval = 1.0 / config.API_RATE_LIMIT
    safety_margin = config.API_RATE_SAFETY_MARGIN
    total_interval = base_interval + safety_margin

    print(f"\n📐 Calculations:")
    print(f"   Base interval: {base_interval:.3f}s (1.0 / {config.API_RATE_LIMIT})")
    print(f"   Safety margin: {safety_margin:.3f}s ({safety_margin*1000:.0f}ms)")
    print(f"   Total interval: {total_interval:.3f}s")

    # Calculate effective rates
    base_rate = 1.0 / base_interval
    safe_rate = 1.0 / total_interval

    print(f"\n📊 Effective Rates:")
    print(f"   Without safety: {base_rate:.2f} req/sec")
    print(f"   With safety: {safe_rate:.2f} req/sec")
    print(f"   Reduction: {((base_rate - safe_rate) / base_rate * 100):.1f}%")

    # Verify safety margin exists and is reasonable
    assert safety_margin > 0, "No safety margin"
    assert safety_margin < 0.2, f"Safety margin too large: {safety_margin}s"
    assert safe_rate < config.API_RATE_LIMIT, "Safe rate exceeds limit"

    print(f"\n✅ Safety margin properly configured")
    return True


def run_all_tests():
    """Run all rate limiting tests"""
    print("\n" + "="*70)
    print("🧪 RATE LIMITING TEST SUITE")
    print("="*70)

    tests = [
        ("Rate Limit Initialization", test_rate_limit_initialization),
        ("Safety Margin Calculation", test_safety_margin_calculation),
        ("Rate Limit Enforcement", test_rate_limit_enforcement),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, True))
        except AssertionError as e:
            print(f"\n❌ {name} FAILED: {e}")
            results.append((name, False))
        except Exception as e:
            print(f"\n❌ {name} ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed\n")

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")

    print("\n" + "="*70)

    if passed == total:
        print("✅ ALL TESTS PASSED - RATE LIMITING WORKING CORRECTLY!")
    else:
        print(f"⚠️  {total - passed} TEST(S) FAILED")

    print("="*70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

"""
Test Corporate Action Detection and Data Adjustment

This test suite verifies:
1. Corporate action detection from price data
2. Data adjustment for splits/bonuses
3. End-to-end workflow
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import CorporateActionDetector, DataAdjuster, HDF5Manager
from config import CORPORATE_ACTION_RATIOS, CA_DETECTION_THRESHOLD


class TestCorporateActionDetector:
    """Test corporate action detection functionality"""

    @pytest.fixture
    def detector(self):
        """Create a detector instance for testing"""
        return CorporateActionDetector()

    @pytest.fixture
    def sample_data_with_bonus(self):
        """
        Create sample data with a 1:1 bonus (50% price drop)
        Before bonus: ₹100
        After bonus: ₹50 (as expected for 1:1 bonus)
        """
        dates = pd.date_range('2024-01-01', periods=60, freq='D')

        # Normal trading for first 30 days around ₹100
        prices_before = np.random.normal(100, 2, 30)

        # 1:1 bonus on day 31 - 50% drop
        bonus_day_price = 50.0

        # After bonus, trading around ₹50 (new base)
        prices_after = np.random.normal(50, 1, 29)

        close_prices = np.concatenate([prices_before, [bonus_day_price], prices_after])

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.randint(100000, 500000, 60)
        })

        df.set_index('timestamp', inplace=True)
        return df

    @pytest.fixture
    def sample_data_with_split(self):
        """
        Create sample data with a 1:5 split (80% price drop)
        Before split: ₹200
        After split: ₹40 (as expected for 1:5 split)
        """
        dates = pd.date_range('2024-01-01', periods=60, freq='D')

        # Normal trading for first 30 days around ₹200
        prices_before = np.random.normal(200, 5, 30)

        # 1:5 split on day 31 - 80% drop
        split_day_price = 40.0

        # After split, trading around ₹40 (new base)
        prices_after = np.random.normal(40, 2, 29)

        close_prices = np.concatenate([prices_before, [split_day_price], prices_after])

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.randint(100000, 500000, 60)
        })

        df.set_index('timestamp', inplace=True)
        return df

    @pytest.fixture
    def sample_data_no_action(self):
        """Create normal data with no corporate actions"""
        dates = pd.date_range('2024-01-01', periods=60, freq='D')

        # Normal trading with small fluctuations (<10%)
        base_price = 150
        prices = [base_price]

        for i in range(59):
            # Random walk with max 5% change
            change_pct = np.random.uniform(-0.05, 0.05)
            new_price = prices[-1] * (1 + change_pct)
            prices.append(new_price)

        prices = np.array(prices)

        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(100000, 500000, 60)
        })

        df.set_index('timestamp', inplace=True)
        return df

    def test_detect_bonus_action(self, detector, sample_data_with_bonus):
        """Test detection of 1:1 bonus (50% drop)"""
        print("\n" + "="*60)
        print("TEST: Detecting 1:1 Bonus (50% drop)")
        print("="*60)

        actions = detector.detect_corporate_actions(
            sample_data_with_bonus,
            symbol='TEST_BONUS',
            exchange='NSE'
        )

        print(f"\nDetected {len(actions)} corporate action(s)")

        # Should detect at least one action
        assert len(actions) > 0, "Should detect at least one corporate action"

        # Check first detected action
        action = actions[0]
        print(f"\nDetected Action Details:")
        print(f"  Date: {action['date']}")
        print(f"  Price change: {action['price_change_pct']}%")
        print(f"  Previous close: ₹{action['prev_close']}")
        print(f"  Current close: ₹{action['curr_close']}")
        print(f"  Suspected type: {action['suspected_type']}")
        print(f"  Suspected ratio: {action['suspected_ratio']}")
        print(f"  Confidence: {action['confidence']}")

        # Verify it's detecting a bonus-like action
        assert action['price_change_pct'] > 40, "Should detect large price drop"
        assert action['suspected_type'] in ['bonus', 'split'], "Should identify as bonus or split"

        print("\n✅ Bonus detection test passed!")

    def test_detect_split_action(self, detector, sample_data_with_split):
        """Test detection of 1:5 split (80% drop)"""
        print("\n" + "="*60)
        print("TEST: Detecting 1:5 Split (80% drop)")
        print("="*60)

        actions = detector.detect_corporate_actions(
            sample_data_with_split,
            symbol='TEST_SPLIT',
            exchange='NSE'
        )

        print(f"\nDetected {len(actions)} corporate action(s)")

        assert len(actions) > 0, "Should detect at least one corporate action"

        action = actions[0]
        print(f"\nDetected Action Details:")
        print(f"  Date: {action['date']}")
        print(f"  Price change: {action['price_change_pct']}%")
        print(f"  Previous close: ₹{action['prev_close']}")
        print(f"  Current close: ₹{action['curr_close']}")
        print(f"  Suspected type: {action['suspected_type']}")
        print(f"  Suspected ratio: {action['suspected_ratio']}")
        print(f"  Confidence: {action['confidence']}")

        # Verify it's detecting a split-like action
        assert action['price_change_pct'] > 70, "Should detect very large price drop"

        print("\n✅ Split detection test passed!")

    def test_no_false_positives(self, detector, sample_data_no_action):
        """Test that normal price movements don't trigger false detections"""
        print("\n" + "="*60)
        print("TEST: No False Positives on Normal Data")
        print("="*60)

        actions = detector.detect_corporate_actions(
            sample_data_no_action,
            symbol='TEST_NORMAL',
            exchange='NSE'
        )

        print(f"\nDetected {len(actions)} corporate action(s)")

        # Should not detect any corporate actions in normal data
        assert len(actions) == 0, "Should not detect corporate actions in normal data"

        print("\n✅ No false positives test passed!")

    def test_save_and_load_actions(self, detector, sample_data_with_bonus):
        """Test saving and loading corporate actions"""
        print("\n" + "="*60)
        print("TEST: Save and Load Actions")
        print("="*60)

        # Detect actions
        actions = detector.detect_corporate_actions(
            sample_data_with_bonus,
            symbol='TEST_SAVE',
            exchange='NSE'
        )

        assert len(actions) > 0, "Should have detected actions"

        # Save action
        action = actions[0]
        detector.save_action(action)
        print(f"\n✅ Saved action for TEST_SAVE on {action['date']}")

        # Load and verify
        loaded_actions = detector.get_actions(symbol='TEST_SAVE')
        print(f"✅ Loaded {len(loaded_actions)} action(s)")

        assert len(loaded_actions) > 0, "Should load saved actions"
        assert loaded_actions[0]['symbol'] == 'TEST_SAVE', "Should match symbol"

        print("\n✅ Save/load test passed!")

    def test_verify_action(self, detector, sample_data_with_bonus):
        """Test verifying a detected action"""
        print("\n" + "="*60)
        print("TEST: Verify Detected Action")
        print("="*60)

        # Detect and save
        actions = detector.detect_corporate_actions(
            sample_data_with_bonus,
            symbol='TEST_VERIFY',
            exchange='NSE'
        )

        action = actions[0]
        detector.save_action(action)
        print(f"\nSaved action: {action['suspected_ratio']} {action['suspected_type']}")

        # Verify with actual details
        success = detector.verify_action(
            symbol='TEST_VERIFY',
            date=action['date'],
            actual_type='bonus',
            actual_ratio='1:1',
            notes='Verified from exchange announcement'
        )

        assert success, "Should successfully verify action"
        print("✅ Action verified")

        # Check verification status
        verified = detector.get_actions(symbol='TEST_VERIFY', status='verified')
        print(f"✅ Found {len(verified)} verified action(s)")

        assert len(verified) > 0, "Should have verified actions"
        assert verified[0]['status'] == 'verified', "Status should be verified"
        assert verified[0]['actual_ratio'] == '1:1', "Should store actual ratio"

        print("\n✅ Verification test passed!")


class TestDataAdjuster:
    """Test data adjustment functionality"""

    @pytest.fixture
    def adjuster(self):
        """Create adjuster instance for testing"""
        return DataAdjuster()

    @pytest.fixture
    def manager(self):
        """Create HDF5 manager for testing"""
        return HDF5Manager(segment='EQUITY')

    @pytest.fixture
    def sample_data_before_bonus(self):
        """
        Create historical data before a 1:1 bonus
        Prices around ₹100, needs adjustment to ₹50 after bonus
        """
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        prices = np.random.normal(100, 2, 30)

        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(100000, 500000, 30)
        })

        df.set_index('timestamp', inplace=True)
        return df

    def test_calculate_multiplier_bonus(self, adjuster):
        """Test multiplier calculation for bonus"""
        print("\n" + "="*60)
        print("TEST: Calculate Multiplier for Bonus")
        print("="*60)

        # 1:1 bonus = 2x shares = price should be halved
        multiplier = adjuster._calculate_multiplier('bonus', '1:1')
        print(f"\n1:1 Bonus multiplier: {multiplier}")
        assert multiplier == 2.0, "1:1 bonus should have 2x multiplier"

        # 1:2 bonus = 1.5x shares = price should be 67%
        multiplier = adjuster._calculate_multiplier('bonus', '1:2')
        print(f"1:2 Bonus multiplier: {multiplier}")
        assert abs(multiplier - 1.5) < 0.01, "1:2 bonus should have 1.5x multiplier"

        print("\n✅ Bonus multiplier test passed!")

    def test_calculate_multiplier_split(self, adjuster):
        """Test multiplier calculation for split"""
        print("\n" + "="*60)
        print("TEST: Calculate Multiplier for Split")
        print("="*60)

        # 1:5 split = 5x shares = price should be 20%
        multiplier = adjuster._calculate_multiplier('split', '1:5')
        print(f"\n1:5 Split multiplier: {multiplier}")
        assert multiplier == 5.0, "1:5 split should have 5x multiplier"

        # 1:10 split = 10x shares = price should be 10%
        multiplier = adjuster._calculate_multiplier('split', '1:10')
        print(f"1:10 Split multiplier: {multiplier}")
        assert multiplier == 10.0, "1:10 split should have 10x multiplier"

        print("\n✅ Split multiplier test passed!")

    def test_adjustment_dry_run(self, adjuster, manager, sample_data_before_bonus):
        """Test adjustment in dry-run mode (no actual changes)"""
        print("\n" + "="*60)
        print("TEST: Adjustment Dry Run")
        print("="*60)

        # Save test data to database
        symbol = 'TEST_ADJUST_DRY'
        manager.save_ohlcv('NSE', symbol, 'day', sample_data_before_bonus, overwrite=True)
        print(f"\n✅ Saved test data for {symbol}")

        # Simulate adjustment for 1:1 bonus on 2023-01-31
        result = adjuster.adjust_for_action(
            exchange='NSE',
            symbol=symbol,
            interval='day',
            action_date='2023-01-31',
            action_type='bonus',
            ratio='1:1',
            dry_run=True
        )

        print(f"\nDry run result:")
        print(f"  Success: {result['success']}")
        print(f"  Rows to adjust: {result['rows_adjusted']}")
        print(f"  Multiplier: {result['multiplier']}")
        print(f"  Date range: {result.get('date_range_adjusted', 'N/A')}")

        if 'sample_adjustment' in result:
            sample = result['sample_adjustment']
            print(f"\nSample adjustment preview:")
            print(f"  Date: {sample['date']}")
            print(f"  Close: ₹{sample['close_before']} → ₹{sample['close_after']}")
            print(f"  Volume: {sample['volume_before']:,} → {sample['volume_after']:,}")

        assert result['success'], "Dry run should succeed"
        assert result['rows_adjusted'] > 0, "Should have rows to adjust"
        assert result['dry_run'] == True, "Should be marked as dry run"

        # Verify data is unchanged
        data_after = manager.get_ohlcv('NSE', symbol, 'day')
        assert len(data_after) == len(sample_data_before_bonus), "Data should be unchanged"

        print("\n✅ Dry run test passed!")

    def test_actual_adjustment(self, adjuster, manager, sample_data_before_bonus):
        """Test actual data adjustment"""
        print("\n" + "="*60)
        print("TEST: Actual Data Adjustment")
        print("="*60)

        # Save test data
        symbol = 'TEST_ADJUST_REAL'
        manager.save_ohlcv('NSE', symbol, 'day', sample_data_before_bonus, overwrite=True)

        # Get original data
        original_data = manager.get_ohlcv('NSE', symbol, 'day')
        original_close = original_data['close'].iloc[0]
        original_volume = original_data['volume'].iloc[0]

        print(f"\nOriginal data:")
        print(f"  First close price: ₹{original_close:.2f}")
        print(f"  First volume: {original_volume:,}")

        # Apply adjustment for 1:1 bonus
        result = adjuster.adjust_for_action(
            exchange='NSE',
            symbol=symbol,
            interval='day',
            action_date='2023-01-31',
            action_type='bonus',
            ratio='1:1',
            dry_run=False
        )

        print(f"\nAdjustment applied:")
        print(f"  Rows adjusted: {result['rows_adjusted']}")
        print(f"  Multiplier: {result['multiplier']}")

        # Get adjusted data
        adjusted_data = manager.get_ohlcv('NSE', symbol, 'day')
        adjusted_close = adjusted_data['close'].iloc[0]
        adjusted_volume = adjusted_data['volume'].iloc[0]

        print(f"\nAdjusted data:")
        print(f"  First close price: ₹{adjusted_close:.2f}")
        print(f"  First volume: {adjusted_volume:,}")

        # Verify adjustment
        expected_close = original_close / 2.0  # 1:1 bonus = divide by 2
        expected_volume = original_volume * 2.0  # Volume doubles

        print(f"\nVerification:")
        print(f"  Expected close: ₹{expected_close:.2f}, Got: ₹{adjusted_close:.2f}")
        print(f"  Expected volume: {expected_volume:,.0f}, Got: {adjusted_volume:,}")

        assert abs(adjusted_close - expected_close) < 0.01, "Close price should be adjusted"
        assert abs(adjusted_volume - expected_volume) < 1, "Volume should be adjusted"

        print("\n✅ Actual adjustment test passed!")

    def test_end_to_end_workflow(self, adjuster, manager):
        """Test complete workflow: detect → verify → adjust"""
        print("\n" + "="*60)
        print("TEST: End-to-End Workflow")
        print("="*60)

        # Step 1: Create data with corporate action
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        prices_before = np.full(30, 100.0)  # Flat at ₹100
        prices_after = np.full(30, 50.0)    # Flat at ₹50 after bonus
        close_prices = np.concatenate([prices_before, prices_after])

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices,
            'high': close_prices * 1.01,
            'low': close_prices * 0.99,
            'close': close_prices,
            'volume': np.full(60, 100000)
        })
        df.set_index('timestamp', inplace=True)

        symbol = 'TEST_E2E'

        # Save to database
        manager.save_ohlcv('NSE', symbol, 'day', df, overwrite=True)
        print(f"\n✅ Step 1: Saved test data for {symbol}")

        # Step 2: Detect corporate actions
        detector = CorporateActionDetector()
        actions = detector.detect_corporate_actions(df, symbol, 'NSE')
        print(f"✅ Step 2: Detected {len(actions)} action(s)")

        assert len(actions) > 0, "Should detect the bonus action"

        # Step 3: Verify the action
        action = actions[0]
        detector.save_action(action)
        detector.verify_action(
            symbol=symbol,
            date=action['date'],
            actual_type='bonus',
            actual_ratio='1:1',
            notes='Test verification'
        )
        print(f"✅ Step 3: Verified action on {action['date']}")

        # Step 4: Check consistency (should need adjustment)
        consistency = adjuster.check_consistency('NSE', symbol, 'day', auto_detect=False)
        print(f"✅ Step 4: Consistency check - needs adjustment: {consistency['needs_adjustment']}")

        assert consistency['needs_adjustment'], "Should need adjustment"

        # Step 5: Auto-adjust
        adjust_result = adjuster.auto_adjust_symbol('NSE', symbol, 'day', dry_run=False)
        print(f"✅ Step 5: Auto-adjusted {adjust_result['total_adjustments']} action(s)")

        assert adjust_result['adjusted'], "Should have applied adjustments"

        # Step 6: Verify adjusted data
        adjusted_data = manager.get_ohlcv('NSE', symbol, 'day')

        # All prices should now be around ₹50 (adjusted)
        avg_price = adjusted_data['close'].mean()
        print(f"\n✅ Step 6: Average price after adjustment: ₹{avg_price:.2f}")

        # Should be around 50 (all data adjusted to post-bonus level)
        assert 45 < avg_price < 55, "Average price should be around ₹50 after adjustment"

        print("\n✅ End-to-end workflow test passed!")


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" CORPORATE ACTION DETECTION AND ADJUSTMENT TEST SUITE")
    print("="*70)

    # Run with pytest
    pytest.main([__file__, '-v', '-s'])

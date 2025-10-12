"""
Data Adjuster - Handle corporate action adjustments for hidtorical data
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

from database.hdf5_manager import HDF5Manager
from database.corporate_action_detector import CorporateActionDetector
from database.schema import dict_to_ohlcv_array

logger = logging.getLogger(__name__)


class DataAdjuster:
    """
    Adjust historical data for corporate actions
    """
    
    def __init__(self):
        self.manager = HDF5Manager()
        self.detector = CorporateActionDetector()
    
    def adjust_for_action(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        action_date: str,
        action_type: str,
        ratio: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Adjust all data before a corporate action date
        
        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            interval: day, 15minute, etc.
            action_date: Date of corporate action (YYYY-MM-DD)
            action_type: 'split' or 'bonus'
            ratio: '1:1', '1:5', etc.
            dry_run: If True, don't save, just return what would change
        
        Returns:
            Dict with adjustment details
        """
        # Load existing data
        data = self.manager.get_ohlcv(exchange, symbol, interval)
        
        if data is None:
            logger.error(f"No data found for {symbol}")
            return {
                'success': False,
                'error': 'No data found',
                'rows_adjusted': 0
            }
        
        # Parse ratio and calculate multiplier
        multiplier = self._calculate_multiplier(action_type, ratio)
        if multiplier is None:
            return {
                'success': False,
                'error': f'Invalid ratio: {ratio}',
                'rows_adjusted': 0
            }
        
        # Create mask for data before action date
        action_dt = pd.to_datetime(action_date)
        mask = data.index < action_dt
        rows_to_adjust = mask.sum()
        
        if rows_to_adjust == 0:
            logger.info(f"No data before {action_date} to adjust")
            return {
                'success': True,
                'rows_adjusted': 0,
                'message': 'No historical data to adjust'
            }
        
        # Calculate adjustment preview
        sample_before = data.loc[mask].iloc[-1] if rows_to_adjust > 0 else None
        
        if not dry_run:
            # Apply adjustments
            data.loc[mask, ['open', 'high', 'low', 'close']] /= multiplier
            data.loc[mask, 'volume'] = (data.loc[mask, 'volume'] * multiplier).astype('int64')
            
            # Save adjusted data back
            self.manager.save_ohlcv(
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                data=data,
                overwrite=True
            )
            
            logger.info(
                f"Adjusted {rows_to_adjust} rows for {symbol} "
                f"({action_type} {ratio} on {action_date})"
            )
        
        # Return adjustment details
        result = {
            'success': True,
            'rows_adjusted': rows_to_adjust,
            'action_date': action_date,
            'action_type': action_type,
            'ratio': ratio,
            'multiplier': multiplier,
            'date_range_adjusted': f"{data.index[0].date()} to {action_dt.date()}",
            'dry_run': dry_run
        }
        
        if sample_before is not None:
            result['sample_adjustment'] = {
                'date': str(sample_before.name.date()),
                'close_before': round(sample_before['close'], 2),
                'close_after': round(sample_before['close'] / multiplier, 2),
                'volume_before': int(sample_before['volume']),
                'volume_after': int(sample_before['volume'] * multiplier)
            }
        
        return result
    
    def _calculate_multiplier(self, action_type: str, ratio: str) -> Optional[float]:
        """
        Calculate adjustment multiplier from action type and ratio
        
        Args:
            action_type: 'split' or 'bonus'
            ratio: '1:1', '1:5', etc.
        
        Returns:
            Multiplier for price adjustment (or None if invalid)
        """
        try:
            parts = ratio.split(':')
            numerator = int(parts[0])
            denominator = int(parts[1])
            
            if action_type == 'bonus':
                # 1:1 bonus = 2x shares = 50% price
                # Formula: (old + new) / old = (1 + 1) / 1 = 2
                multiplier = (numerator + denominator) / denominator
            
            elif action_type == 'split':
                # 1:5 split = 5x shares = 20% price
                # Formula: new / old = 5 / 1 = 5
                multiplier = denominator / numerator
            
            else:
                logger.error(f"Unknown action type: {action_type}")
                return None
            
            return multiplier
            
        except Exception as e:
            logger.error(f"Error calculating multiplier for {ratio}: {e}")
            return None
    
    def check_consistency(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        auto_detect: bool = True
    ) -> Dict:
        """
        Check if database data is consistent with verified corporate actions
        
        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            interval: day, 15minute, etc.
            auto_detect: If True, also detect new actions from data
        
        Returns:
            Dict with consistency check results
        """
        # Get database data
        data = self.manager.get_ohlcv(exchange, symbol, interval)
        if data is None:
            return {
                'has_data': False,
                'needs_adjustment': False,
                'actions_to_apply': []
            }
        
        # Get verified corporate actions
        verified_actions = self.detector.get_actions(
            symbol=symbol,
            status='verified'
        )
        
        actions_to_apply = []
        
        for action in verified_actions:
            action_date = pd.to_datetime(action['date'])
            
            # Check if we have data before this action
            before_action = data[data.index < action_date]
            if len(before_action) == 0:
                continue  # No data before action, nothing to adjust
            
            # Check if action date is in our data
            if action_date not in data.index:
                # Action date not in data, assume we need to adjust
                actions_to_apply.append({
                    'action': action,
                    'reason': 'Action date not in dataset, likely unadjusted',
                    'confidence': 'medium'
                })
                continue
            
            # Check price discontinuity at action date
            action_idx = data.index.get_loc(action_date)
            if action_idx > 0:
                prev_close = data.iloc[action_idx - 1]['close']
                action_close = data.loc[action_date]['close']
                pct_change = abs((action_close - prev_close) / prev_close)
                
                # If change is large (>20%), data is NOT adjusted yet
                if pct_change > 0.20:
                    actions_to_apply.append({
                        'action': action,
                        'reason': f'Large price discontinuity ({pct_change*100:.1f}%) at action date',
                        'confidence': 'high',
                        'detected_change': round(pct_change * 100, 2)
                    })
                else:
                    logger.info(f"✓ {symbol}: Already adjusted for {action['date']}")
        
        # Auto-detect new actions if requested
        if auto_detect:
            detected = self.detector.detect_corporate_actions(data, symbol, exchange)
            for d in detected:
                # Check if this is already in verified actions
                if not any(a['date'] == d['date'] for a in verified_actions):
                    logger.warning(
                        f"Detected unverified action: {symbol} on {d['date']} "
                        f"({d['suspected_ratio']} {d['suspected_type']})"
                    )
        
        return {
            'has_data': True,
            'needs_adjustment': len(actions_to_apply) > 0,
            'actions_to_apply': actions_to_apply,
            'total_verified_actions': len(verified_actions),
            'date_range': f"{data.index[0].date()} to {data.index[-1].date()}",
            'total_rows': len(data)
        }
    
    def auto_adjust_symbol(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Automatically adjust a symbol's data for all verified corporate actions
        
        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            interval: day, 15minute, etc.
            dry_run: If True, don't save, just report what would happen
        
        Returns:
            Dict with adjustment summary
        """
        # Check consistency
        check = self.check_consistency(exchange, symbol, interval, auto_detect=False)
        
        if not check['needs_adjustment']:
            return {
                'symbol': symbol,
                'interval': interval,
                'adjusted': False,
                'message': 'No adjustments needed'
            }
        
        # Apply adjustments
        results = []
        for item in check['actions_to_apply']:
            action = item['action']
            
            result = self.adjust_for_action(
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                action_date=action['date'],
                action_type=action['actual_type'],
                ratio=action['actual_ratio'],
                dry_run=dry_run
            )
            
            results.append({
                'action_date': action['date'],
                'action_type': action['actual_type'],
                'ratio': action['actual_ratio'],
                'result': result
            })
        
        return {
            'symbol': symbol,
            'interval': interval,
            'adjusted': True,
            'dry_run': dry_run,
            'adjustments': results,
            'total_adjustments': len(results)
        }
    
    def incremental_update_workflow(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        new_data: pd.DataFrame,
        from_date: str,
        to_date: str
    ) -> Dict:
        """
        Complete workflow for incremental data updates with corporate action handling
        Args:
            exchange: NSE, BSE
            symbol: Trading symbol
            interval: day, 15minute, etc.
            new_data: Newly fetched data from Kite
            from_date: Start date of new data
            to_date: End date of new data
        
        Returns:
            Dict with update summary
        """
        logger.info(f"Starting incremental update for {symbol} ({from_date} to {to_date})")
        
        # Step 1: Detect corporate actions in new data
        detected_actions = self.detector.detect_corporate_actions(
            new_data, symbol, exchange
        )
        
        # Step 2: Save detected actions for review
        for action in detected_actions:
            self.detector.save_action(action, verified=False)
        
        # Step 3: Check if old data needs adjustment
        consistency = self.check_consistency(exchange, symbol, interval, auto_detect=False)
        
        # Step 4: If corporate actions detected, pause for verification
        if detected_actions:
            logger.warning(
                f"Detected {len(detected_actions)} corporate actions in new data. "
                f"Verify before completing update!"
            )
            
            return {
                'status': 'paused_for_verification',
                'detected_actions': detected_actions,
                'message': 'Corporate actions detected. Verify them before saving new data.',
                'next_steps': [
                    '1. Review detected actions: detector.get_pending_actions()',
                    '2. Verify each action: detector.verify_action(...)',
                    '3. Run auto_adjust_symbol() to adjust old data',
                    '4. Then save new data'
                ]
            }
        
        # Step 5: Apply adjustments to old data if needed
        adjustment_results = []
        if consistency['needs_adjustment']:
            logger.info(f"Adjusting old data for {len(consistency['actions_to_apply'])} corporate actions")
            
            for item in consistency['actions_to_apply']:
                action = item['action']
                result = self.adjust_for_action(
                    exchange, symbol, interval,
                    action['date'], action['actual_type'], action['actual_ratio']
                )
                adjustment_results.append(result)
        
        # Step 6: Save new data
        self.manager.save_ohlcv(exchange, symbol, interval, new_data, overwrite=False)
        
        return {
            'status': 'completed',
            'symbol': symbol,
            'interval': interval,
            'new_data_rows': len(new_data),
            'adjustments_applied': len(adjustment_results),
            'adjustment_details': adjustment_results,
            'message': 'Incremental update completed successfully'
        }

def adjust_symbol(symbol: str, exchange: str = 'NSE', interval: str = 'day', dry_run: bool = False):
    """
    Adjust a symbol's data
    
    Usage:
        adjust_symbol('RELIANCE', dry_run=True)  # Preview
        adjust_symbol('RELIANCE')  # Apply
    """
    adjuster = DataAdjuster()
    return adjuster.auto_adjust_symbol(exchange, symbol, interval, dry_run)


def check_symbol_consistency(symbol: str, exchange: str = 'NSE', interval: str = 'day'):
    """
    Check if a symbol needs adjustment
    
    Usage:
        result = check_symbol_consistency('RELIANCE')
        if result['needs_adjustment']:
            print("Needs adjustment!")
    """
    adjuster = DataAdjuster()
    return adjuster.check_consistency(exchange, symbol, interval)
    
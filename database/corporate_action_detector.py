"""
Corporate Action Detector
Detects stock splits, bonus issues based on circuit breaker violations
Since NSE/BSE have 20% daily limits, >20% changes might indicate corporate actions
"""
from datetime import datetime
from typing import List, Dict, Optional
import json
import pandas as pd

from config import (
    config,
    CIRCUIT_LIMIT_PERCENT,
    CORPORATE_ACTION_RATIOS,
    CORPORATE_ACTIONS_FILENAME,
    CA_DETECTION_THRESHOLD,
    CA_HIGH_CONFIDENCE_THRESHOLD,
    CA_MEDIUM_CONFIDENCE_THRESHOLD,
)
from utils.logger import get_logger

logger = get_logger(__name__, 'database.log')


class CorporateActionDetector:
    """
    Detects corporate actions by analyzing price movements
    Uses 20% circuit breaker rule (NSE/BSE standard)
    """

    def __init__(self):
        self.actions_file = config.DATA_DIR / CORPORATE_ACTIONS_FILENAME
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.actions_file.exists():
            self.actions_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_actions([])

    def detect_corporate_actions(
        self,
        data: pd.DataFrame,
        symbol: str,
        exchange: str = 'NSE',
        threshold: float = None
    ) -> List[Dict]:
        """
        Detect potential corporate actions based on price movements

        Args:
            data: DataFrame with OHLCV data (DatetimeIndex)
            symbol: Trading symbol
            exchange: Exchange name
            threshold: Custom threshold (default: CIRCUIT_LIMIT_PERCENT)

        Returns:
            List of detected corporate action events
        """
        if threshold is None:
            threshold = CA_DETECTION_THRESHOLD

        detected_actions = []

        pct_change = data['close'].pct_change().abs()

        # Find changes exceeding circuit limit
        violations = data[pct_change > threshold]

        for idx in violations.index:
            change = pct_change.loc[idx]
            prev_close = data['close'].shift(1).loc[idx]
            curr_close = data['close'].loc[idx]

            # Determine if price went up or down
            direction = 'up' if curr_close > prev_close else 'down'

            # Only corporate actions cause downward moves >20%
            if direction == 'down':
                # Try to match to known ratio
                ratio_info = self._match_ratio(change)

                action = {
                    'symbol': symbol,
                    'exchange': exchange,
                    'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                    'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                    'price_change_pct': round(change * 100, 2),
                    'prev_close': round(prev_close, 2),
                    'curr_close': round(curr_close, 2),
                    'suspected_type': ratio_info['type'],
                    'suspected_ratio': ratio_info['ratio'],
                    'description': ratio_info['description'],
                    'confidence': ratio_info['confidence'],
                    'status': 'pending_verification',
                    'detected_at': datetime.now().isoformat(),
                }

                detected_actions.append(action)

                logger.warning(
                    f"Detected corporate action: {symbol} on {idx.date()} - "
                    f"{change*100:.1f}% drop (suspected {ratio_info['ratio']} {ratio_info['type']})"
                )

        return detected_actions

    def _match_ratio(self, change: float) -> Dict:
        """
        Match price change to known corporate action ratios

        Args:
            change: Absolute percentage change (e.g., 0.50 for 50%)

        Returns:
            Dict with ratio info and confidence
        """
        # Find closest known ratio
        closest_ratio = None
        min_diff = float('inf')

        for known_change, info in CORPORATE_ACTION_RATIOS.items():
            diff = abs(change - known_change)
            if diff < min_diff:
                min_diff = diff
                closest_ratio = info.copy()

        # Calculate confidence based on how close to known ratio
        if min_diff < CA_HIGH_CONFIDENCE_THRESHOLD:
            confidence = 'high'
        elif min_diff < CA_MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = 'medium'
        else:
            confidence = 'low'
            # Unknown ratio
            closest_ratio = {
                'ratio': 'unknown',
                'type': 'unknown',
                'description': f'Unknown corporate action ({change*100:.1f}% drop)'
            }

        closest_ratio['confidence'] = confidence
        closest_ratio['deviation_pct'] = round(min_diff * 100, 2)

        return closest_ratio


    def save_action(self, action: Dict, verified: bool = False):
        """
        Save a corporate action to the database

        Args:
            action: Action dictionary from detect_corporate_actions()
            verified: If True, mark as verified (user confirmed)
        """
        actions = self.load_actions()

        # Update status
        action['status'] = 'verified' if verified else 'pending_verification'
        action['verified_at'] = datetime.now().isoformat() if verified else None

        # Check for duplicates
        existing = self._find_action(
            actions,
            action['symbol'],
            action['date']
        )

        if existing:
            # Update existing
            actions[actions.index(existing)] = action
            logger.info(f"Updated corporate action: {action['symbol']} on {action['date']}")
        else:
            # Add new
            actions.append(action)
            logger.info(f"Saved corporate action: {action['symbol']} on {action['date']}")

        self._save_actions(actions)

    def verify_action(
        self,
        symbol: str,
        date: str,
        actual_type: str,
        actual_ratio: str,
        notes: str = ""
    ):
        """
        Verify a detected corporate action with actual details

        Args:
            symbol: Trading symbol
            date: Date of action (YYYY-MM-DD)
            actual_type: Actual type ('split', 'bonus', etc.)
            actual_ratio: Actual ratio (e.g., '1:1')
            notes: Additional notes
        """
        actions = self.load_actions()
        action = self._find_action(actions, symbol, date)

        if not action:
            logger.error(f"No action found for {symbol} on {date}")
            return False

        # Update with verified info
        action['status'] = 'verified'
        action['actual_type'] = actual_type
        action['actual_ratio'] = actual_ratio
        action['notes'] = notes
        action['verified_at'] = datetime.now().isoformat()

        # Update in list
        idx = actions.index(self._find_action(actions, symbol, date))
        actions[idx] = action

        self._save_actions(actions)
        logger.info(f"Verified corporate action: {symbol} on {date} as {actual_ratio} {actual_type}")
        return True

    def reject_action(self, symbol: str, date: str, reason: str = ""):
        """Mark a detected action as false positive"""
        actions = self.load_actions()
        action = self._find_action(actions, symbol, date)

        if not action:
            logger.error(f"No action found for {symbol} on {date}")
            return False

        action['status'] = 'rejected'
        action['rejection_reason'] = reason
        action['rejected_at'] = datetime.now().isoformat()

        idx = actions.index(self._find_action(actions, symbol, date))
        actions[idx] = action

        self._save_actions(actions)
        logger.info(f"Rejected corporate action: {symbol} on {date}")
        return True

    def get_actions(
        self,
        symbol: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get corporate actions with filters

        Args:
            symbol: Filter by symbol
            from_date: Filter from date (YYYY-MM-DD)
            to_date: Filter to date (YYYY-MM-DD)
            status: Filter by status ('verified', 'pending_verification', 'rejected')

        Returns:
            List of matching actions
        """
        actions = self.load_actions()

        # Apply filters
        if symbol:
            actions = [a for a in actions if a['symbol'] == symbol]

        if from_date:
            actions = [a for a in actions if a['date'] >= from_date]

        if to_date:
            actions = [a for a in actions if a['date'] <= to_date]

        if status:
            actions = [a for a in actions if a['status'] == status]

        return sorted(actions, key=lambda x: x['date'], reverse=True)

    def get_pending_actions(self) -> List[Dict]:
        """Get all actions pending verification"""
        return self.get_actions(status='pending_verification')

    def load_actions(self) -> List[Dict]:
        """Load all corporate actions from file"""
        try:
            with open(self.actions_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_actions(self, actions: List[Dict]):
        """Save corporate actions to file"""
        with open(self.actions_file, 'w') as f:
            json.dump(actions, f, indent=2)

    def _find_action(self, actions: List[Dict], symbol: str, date: str) -> Optional[Dict]:
        """Find action by symbol and date"""
        for action in actions:
            if action['symbol'] == symbol and action['date'] == date:
                return action
        return None

    # ========================================================================
    # REPORTING
    # ========================================================================

    def generate_report(self, symbol: Optional[str] = None) -> str:
        """Generate a text report of corporate actions"""
        actions = self.get_actions(symbol=symbol)

        if not actions:
            return "No corporate actions recorded."

        lines = [
            "=" * 80,
            f"CORPORATE ACTIONS REPORT" + (f" - {symbol}" if symbol else ""),
            "=" * 80,
            ""
        ]

        # Group by status
        by_status = {}
        for action in actions:
            status = action['status']
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(action)

        for status, acts in by_status.items():
            lines.append(f"\n{status.upper().replace('_', ' ')} ({len(acts)}):")
            lines.append("-" * 80)

            for action in acts:
                lines.append(f"\n{action['symbol']} - {action['date']}")
                lines.append(f"  Price Change: {action['price_change_pct']}%")
                lines.append(f"  {action['prev_close']} → {action['curr_close']}")

                if action['status'] == 'verified':
                    lines.append(f"  Action: {action['actual_ratio']} {action['actual_type']}")
                else:
                    lines.append(f"  Suspected: {action['suspected_ratio']} {action['suspected_type']} "
                               f"(confidence: {action['confidence']})")

                if action.get('notes'):
                    lines.append(f"  Notes: {action['notes']}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

def detect_and_flag_actions(data: pd.DataFrame, symbol: str, exchange: str = 'NSE') -> List[Dict]:
    """
    Convenience function to detect corporate actions

    Usage:
        actions = detect_and_flag_actions(df, 'RELIANCE')
        if actions:
            print(f"Found {len(actions)} potential corporate actions")
    """
    detector = CorporateActionDetector()
    return detector.detect_corporate_actions(data, symbol, exchange)
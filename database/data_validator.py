"""
Validates OHLCV data quality before storage
"""
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging
import numpy as np
import pandas as pd

from config.settings import config
from database.schema import (
    EquityOHLCVSchema,
    ValidationRules,
    Interval,
    HISTORICAL_DATA_START,
)

logger = logging.getLogger(__name__)
logger.setLevel(config.LOG_LEVEL)

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]              # Critical issues (corrupt data)
    warnings: List[str]             # Potential issues (review needed)
    anomalies: List[Dict]           # Detected anomalies (informational only)
    stats: Dict
    
    def __str__(self) -> str:
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return f"{status} | Errors: {len(self.errors)} | Warnings: {len(self.warnings)} | Anomalies: {len(self.anomalies)}"
    
    def summary(self) -> str:
        """Get detailed validation summary"""
        lines = [
            "=" * 70,
            f"VALIDATION RESULT: {self.__str__()}",
            "=" * 70,
        ]
        
        if self.errors:
            lines.append("\n❌ ERRORS (Data Corruption - Must Fix):")
            for err in self.errors:
                lines.append(f"  • {err}")
        
        if self.warnings:
            lines.append("\n⚠️  WARNINGS (Data Quality Issues):")
            for warn in self.warnings:
                lines.append(f"  • {warn}")
        
        if self.anomalies:
            lines.append(f"\n📊 ANOMALIES DETECTED ({len(self.anomalies)}):")
            lines.append("  (These may be legitimate market events - review recommended)")
            for anom in self.anomalies[:5]:  # Show first 5
                lines.append(f"  • {anom.get('type')}: {anom.get('description')}")
            if len(self.anomalies) > 5:
                lines.append(f"  ... and {len(self.anomalies) - 5} more")
        
        if self.stats:
            lines.append("\n📈 STATISTICS:")
            for key, value in self.stats.items():
                lines.append(f"  • {key}: {value}")
        
        lines.append("=" * 70)
        return "\n".join(lines)

class DataValidator:
    """
    Validates OHLCV data before storage
    
    Checks:
    - Data format and structure
    - OHLC relationships
    - Price ranges
    - Volume validity
    - Date ranges and gaps
    - Duplicates
    - Missing values
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: If True, warnings also fail validation
        """
        self.strict_mode = strict_mode
        self.rules = ValidationRules()
        
        # Log configuration
        if config.LOG_PERFORMANCE:
            logger.info(f"DataValidator initialized (strict_mode={strict_mode})")
    
    # ========================================================================
    # MAIN VALIDATION METHOD
    # ========================================================================
    
    def validate(
        self,
        data: Union[List[Dict], np.ndarray, pd.DataFrame],
        exchange: str,
        symbol: str,
        interval: Union[str, Interval],
        expected_start: Optional[datetime] = None,
        expected_end: Optional[datetime] = None,
        detect_anomalies: bool = True,  # New parameter
    ) -> ValidationResult:
        """
        Comprehensive validation of OHLCV data
        
        Args:
            data: OHLCV data (list of dicts, numpy array, or DataFrame)
            exchange: Exchange name (NSE, BSE)
            symbol: Trading symbol
            interval: Timeframe (15minute, 60minute, day)
            expected_start: Expected start date (optional)
            expected_end: Expected end date (optional)
            detect_anomalies: If True, detect and report anomalies (default: True)
        
        Returns:
            ValidationResult with details
        """
        errors = []
        warnings = []
        anomalies = []  # New: separate anomaly tracking
        stats = {}
        
        try:
            # Convert to DataFrame for easier validation
            df = self._to_dataframe(data)
            
            if df is None or len(df) == 0:
                errors.append("Empty dataset")
                return ValidationResult(False, errors, warnings, anomalies, stats)
            
            # Convert interval to string if enum
            if isinstance(interval, Interval):
                interval = interval.value
            
            # Log validation start
            if config.LOG_PERFORMANCE:
                logger.debug(
                    f"Validating {len(df)} rows for {exchange}/{symbol} [{interval}]"
                )
            
            # Basic stats
            stats['total_rows'] = len(df)
            stats['date_range'] = f"{df.index[0]} to {df.index[-1]}"
            stats['exchange'] = exchange
            stats['symbol'] = symbol
            stats['interval'] = interval
            
            # 1. Structure validation
            struct_errors = self._validate_structure(df)
            errors.extend(struct_errors)
            
            # 2. OHLC relationship validation
            ohlc_errors, ohlc_stats = self._validate_ohlc_relationships(df)
            errors.extend(ohlc_errors)
            stats.update(ohlc_stats)
            
            # 3. Price range validation
            price_errors, price_warnings = self._validate_price_ranges(df)
            errors.extend(price_errors)
            warnings.extend(price_warnings)
            
            # 4. Volume validation
            vol_errors, vol_warnings = self._validate_volume(df)
            errors.extend(vol_errors)
            warnings.extend(vol_warnings)
            
            # 5. Date validation
            date_errors, date_warnings, date_stats = self._validate_dates(
                df, interval, expected_start, expected_end
            )
            errors.extend(date_errors)
            warnings.extend(date_warnings)
            stats.update(date_stats)
            
            # 6. Duplicate check
            dup_errors, dup_stats = self._check_duplicates(df)
            errors.extend(dup_errors)
            stats.update(dup_stats)
            
            # 7. Missing values check
            missing_errors = self._check_missing_values(df)
            errors.extend(missing_errors)
            
            # 8. Data availability check
            avail_warnings = self._check_data_availability(
                df, exchange, interval
            )
            warnings.extend(avail_warnings)
            
            # Determine if valid
            is_valid = len(errors) == 0
            if self.strict_mode and len(warnings) > 0:
                is_valid = False
            
            # Log result
            if config.LOG_PERFORMANCE:
                status = "✅ VALID" if is_valid else "❌ INVALID"
                logger.info(
                    f"Validation {status}: {symbol} [{interval}] - "
                    f"Errors: {len(errors)}, Warnings: {len(warnings)}"
                )
            
            return ValidationResult(is_valid, errors, warnings, anomalies, stats)
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            errors.append(f"Validation exception: {str(e)}")
            return ValidationResult(False, errors, warnings, anomalies, stats)
    
    # ========================================================================
    # SPECIFIC VALIDATION METHODS
    # ========================================================================
    
    def _validate_structure(self, df: pd.DataFrame) -> List[str]:
        """Validate DataFrame structure"""
        errors = []
        
        required = EquityOHLCVSchema.REQUIRED_COLUMNS
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            errors.append(f"Missing required columns: {missing}")
        
        return errors
    
    def _validate_ohlc_relationships(
        self, df: pd.DataFrame
    ) -> Tuple[List[str], Dict]:
        """Validate OHLC price relationships"""
        errors = []
        stats = {}
        
        # High >= Open, Close, Low
        invalid_high = (
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['high'] < df['low'])
        )
        
        # Low <= Open, Close, High
        invalid_low = (
            (df['low'] > df['open']) |
            (df['low'] > df['close']) |
            (df['low'] > df['high'])
        )
        
        invalid_count = invalid_high.sum() + invalid_low.sum()
        
        if invalid_count > 0:
            errors.append(
                f"Invalid OHLC relationships in {invalid_count} rows "
                f"({invalid_count/len(df)*100:.1f}%)"
            )
            
            # Show first few examples
            invalid_rows = df[invalid_high | invalid_low].head(5)
            for idx, row in invalid_rows.iterrows():
                errors.append(
                    f"  Row {idx}: O={row['open']:.2f} H={row['high']:.2f} "
                    f"L={row['low']:.2f} C={row['close']:.2f}"
                )
        
        stats['valid_ohlc_rows'] = len(df) - invalid_count
        stats['invalid_ohlc_rows'] = invalid_count
        
        return errors, stats
    
    def _validate_price_ranges(
        self, df: pd.DataFrame
    ) -> Tuple[List[str], List[str]]:
        """Validate price ranges"""
        errors = []
        warnings = []
        
        for col in ['open', 'high', 'low', 'close']:
            # Check minimum
            too_low = df[col] < self.rules.MIN_PRICE
            if too_low.any():
                errors.append(
                    f"{col.upper()} has {too_low.sum()} values below "
                    f"minimum ({self.rules.MIN_PRICE})"
                )
            
            # Check maximum
            too_high = df[col] > self.rules.MAX_PRICE
            if too_high.any():
                errors.append(
                    f"{col.upper()} has {too_high.sum()} values above "
                    f"maximum ({self.rules.MAX_PRICE})"
                )
            
            # Check for zero prices (critical error)
            zero_prices = df[col] == 0
            if zero_prices.any():
                errors.append(f"{col.upper()} has {zero_prices.sum()} zero values")
        
        # Check for suspicious price spikes
        for col in ['open', 'high', 'low', 'close']:
            pct_change = df[col].pct_change().abs()
            spikes = pct_change > 0.25  # 25% move in one candle
            
            if spikes.any():
                spike_count = spikes.sum()
                max_spike = pct_change.max() * 100
                warnings.append(
                    f"{col.upper()} has {spike_count} suspicious spikes "
                    f"(max: {max_spike:.1f}% change)"
                )
        
        return errors, warnings
    
    def _validate_volume(
        self, df: pd.DataFrame
    ) -> Tuple[List[str], List[str]]:
        """Validate volume data"""
        errors = []
        warnings = []
        
        # Check negative volumes
        negative = df['volume'] < 0
        if negative.any():
            errors.append(f"Negative volume in {negative.sum()} rows")
        
        # Check excessive volumes
        excessive = df['volume'] > self.rules.MAX_VOLUME
        if excessive.any():
            errors.append(
                f"Excessive volume (>{self.rules.MAX_VOLUME}) in "
                f"{excessive.sum()} rows"
            )
        
        # Check for zero volume (warning, not error)
        zero_vol = df['volume'] == 0
        if zero_vol.any():
            warnings.append(
                f"Zero volume in {zero_vol.sum()} rows "
                f"({zero_vol.sum()/len(df)*100:.1f}%)"
            )
        
        return errors, warnings
    
    def _validate_dates(
        self,
        df: pd.DataFrame,
        interval: str,
        expected_start: Optional[datetime],
        expected_end: Optional[datetime],
    ) -> Tuple[List[str], List[str], Dict]:
        """Validate date range and continuity"""
        errors = []
        warnings = []
        stats = {}
        
        # Check date range
        actual_start = df.index[0]
        actual_end = df.index[-1]
        
        stats['actual_start'] = str(actual_start)
        stats['actual_end'] = str(actual_end)
        
        # Check if dates are in order
        if not df.index.is_monotonic_increasing:
            errors.append("Timestamps are not in ascending order")
        
        # Check expected vs actual dates
        if expected_start:
            if actual_start > expected_start:
                warnings.append(
                    f"Data starts later than expected: "
                    f"{actual_start} vs {expected_start}"
                )
        
        if expected_end:
            if actual_end < expected_end:
                warnings.append(
                    f"Data ends earlier than expected: "
                    f"{actual_end} vs {expected_end}"
                )
        
        # Check for gaps
        gap_warnings, gap_stats = self._check_date_gaps(df, interval)
        warnings.extend(gap_warnings)
        stats.update(gap_stats)
        
        return errors, warnings, stats
    
    def _check_date_gaps(
        self, df: pd.DataFrame, interval: str
    ) -> Tuple[List[str], Dict]:
        """Check for gaps in date sequence"""
        warnings = []
        stats = {}
        
        # Calculate expected frequency
        if interval == 'day':
            expected_freq = 'D'
            tolerance = pd.Timedelta(days=5)  # Allow for weekends/holidays
        elif interval == '60minute':
            expected_freq = '60T'
            tolerance = pd.Timedelta(hours=2)
        elif interval == '15minute':
            expected_freq = '15T'
            tolerance = pd.Timedelta(minutes=30)
        else:
            # For other intervals, skip gap detection
            return warnings, stats
        
        # Check gaps
        time_diff = df.index.to_series().diff()
        large_gaps = time_diff > tolerance
        
        gap_count = large_gaps.sum()
        if gap_count > 0:
            warnings.append(
                f"Found {gap_count} gaps larger than {tolerance} in data"
            )
            
            # Show first few gaps
            gap_indices = df.index[large_gaps][:3]
            for idx in gap_indices:
                warnings.append(f"  Gap near: {idx}")
        
        stats['gaps_detected'] = gap_count
        
        return warnings, stats
    
    def _check_duplicates(self, df: pd.DataFrame) -> Tuple[List[str], Dict]:
        """Check for duplicate timestamps"""
        errors = []
        stats = {}
        
        duplicates = df.index.duplicated()
        dup_count = duplicates.sum()
        
        if dup_count > 0:
            errors.append(f"Found {dup_count} duplicate timestamps")
            
            # Show examples
            dup_dates = df.index[duplicates].unique()[:5]
            for date in dup_dates:
                errors.append(f"  Duplicate: {date}")
        
        stats['duplicate_count'] = dup_count
        stats['unique_timestamps'] = len(df.index.unique())
        
        return errors, stats
    
    def _detect_anomalies(
        self,
        df: pd.DataFrame,
        exchange: str,
        symbol: str,
        interval: str,
    ) -> List[Dict]:
        """
        Detect anomalies - these are NOT errors, just notable events
        Returns list of anomaly dictionaries with metadata
        """
        anomalies = []
        
        # 1. Price spikes (potential: stock splits, bonuses, major news)
        for col in ['open', 'high', 'low', 'close']:
            pct_change = df[col].pct_change().abs()
            spikes = df[pct_change > 0.25]  # 25% moves
            
            for idx in spikes.index[:10]:  # Limit to 10
                anomalies.append({
                    'type': 'price_spike',
                    'date': str(idx),
                    'field': col,
                    'change_pct': round(pct_change.loc[idx] * 100, 2),
                    'description': f"{col.upper()} changed {pct_change.loc[idx]*100:.1f}% on {idx.date()}",
                    'severity': 'info',
                    'possible_causes': ['Stock split', 'Bonus issue', 'Major news', 'Corporate action']
                })
        
        # 2. Volume anomalies (potential: buybacks, block deals, earnings)
        median_volume = df['volume'].median()
        if median_volume > 0:
            volume_ratio = df['volume'] / median_volume
            volume_spikes = df[volume_ratio > 10]  # 10x normal
            
            for idx in volume_spikes.index[:10]:
                anomalies.append({
                    'type': 'volume_spike',
                    'date': str(idx),
                    'volume': int(df.loc[idx, 'volume']),
                    'ratio': round(volume_ratio.loc[idx], 1),
                    'description': f"Volume {volume_ratio.loc[idx]:.1f}x normal on {idx.date()}",
                    'severity': 'info',
                    'possible_causes': ['Block deal', 'Buyback', 'Earnings', 'Index inclusion/exclusion']
                })
        
        # 3. Data gaps (potential: trading halts, holidays, suspensions)
        gap_info = self._analyze_gaps(df, interval)
        for gap in gap_info:
            anomalies.append({
                'type': 'data_gap',
                'date': gap['start_date'],
                'gap_days': gap['gap_size'],
                'description': f"{gap['gap_size']}-day gap starting {gap['start_date']}",
                'severity': 'low' if gap['gap_size'] <= 5 else 'medium',
                'possible_causes': ['Market holiday', 'Trading halt', 'Weekend', 'Suspension']
            })
        
        # 4. Zero volume days (potential: circuit limits, no trading interest)
        zero_vol_days = df[df['volume'] == 0]
        if len(zero_vol_days) > 0:
            for idx in zero_vol_days.index[:5]:
                anomalies.append({
                    'type': 'zero_volume',
                    'date': str(idx),
                    'description': f"Zero trading volume on {idx.date()}",
                    'severity': 'low',
                    'possible_causes': ['Circuit limit', 'Trading halt', 'Low liquidity']
                })
        
        return anomalies
    
    def _analyze_gaps(self, df: pd.DataFrame, interval: str) -> List[Dict]:
        """Analyze gaps in data"""
        gaps = []
        
        if interval == 'day':
            expected_freq = pd.Timedelta(days=1)
            max_normal_gap = pd.Timedelta(days=3)  # Weekend
        elif interval == '60minute':
            expected_freq = pd.Timedelta(hours=1)
            max_normal_gap = pd.Timedelta(hours=18)  # Overnight
        elif interval == '15minute':
            expected_freq = pd.Timedelta(minutes=15)
            max_normal_gap = pd.Timedelta(hours=18)  # Overnight
        else:
            return gaps  # Skip gap analysis for other intervals
        
        time_diff = df.index.to_series().diff()
        large_gaps = time_diff > max_normal_gap
        
        for idx in df.index[large_gaps]:
            gap_size_days = (time_diff.loc[idx].total_seconds() / 86400)
            gaps.append({
                'start_date': str(idx),
                'gap_size': int(gap_size_days)
            })
        
        return gaps[:10]  # Limit to 10 gaps
        """Check for missing/NaN values"""
        errors = []
        
        for col in EquityOHLCVSchema.REQUIRED_COLUMNS:
            if col == 'timestamp':
                continue
            
            if col not in df.columns:
                continue
            
            missing = df[col].isna().sum()
            if missing > 0:
                errors.append(
                    f"Missing values in {col}: {missing} rows "
                    f"({missing/len(df)*100:.1f}%)"
                )
        
        return errors
    
    def _check_data_availability(
        self,
        df: pd.DataFrame,
        exchange: str,
        interval: str,
    ) -> List[str]:
        """Check if data is within expected availability window"""
        warnings = []
        
        actual_start = df.index[0]
        
        # Check against known data availability dates
        if interval != 'day':  # Intraday data
            key = f"{exchange}_intraday"
            if key in HISTORICAL_DATA_START:
                expected_start = pd.to_datetime(HISTORICAL_DATA_START[key])
                
                if actual_start < expected_start:
                    warnings.append(
                        f"Data starts before expected availability: "
                        f"{actual_start} < {expected_start}"
                    )
        
        return warnings
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _to_dataframe(
        self, data: Union[List[Dict], np.ndarray, pd.DataFrame]
    ) -> Optional[pd.DataFrame]:
        """Convert input data to DataFrame with DatetimeIndex"""
        try:
            if isinstance(data, pd.DataFrame):
                df = data.copy()
                
                # Ensure datetime index
                if not isinstance(df.index, pd.DatetimeIndex):
                    if 'timestamp' in df.columns:
                        df = df.set_index('timestamp')
                    elif 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.set_index('date')
                
                return df
            
            elif isinstance(data, np.ndarray):
                # Structured array from schema
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
                return df
            
            elif isinstance(data, list):
                # List of dicts from Kite API
                df = pd.DataFrame(data)
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                elif 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.set_index('timestamp')
                
                return df
            
            else:
                logger.error(f"Unsupported data type: {type(data)}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting data to DataFrame: {e}")
            return None
    
    # ========================================================================
    # QUICK VALIDATION METHODS
    # ========================================================================
    
    @staticmethod
    def quick_validate(data: pd.DataFrame) -> bool:
        """
        Quick validation check (for performance-critical paths)
        Returns True if basic checks pass
        """
        if data is None or len(data) == 0:
            return False
        
        # Check required columns exist
        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required):
            return False
        
        # Check for NaN values
        if data[required].isna().any().any():
            return False
        
        # Basic OHLC check
        valid_ohlc = (
            (data['high'] >= data['open']) &
            (data['high'] >= data['close']) &
            (data['high'] >= data['low']) &
            (data['low'] <= data['open']) &
            (data['low'] <= data['close'])
        ).all()
        
        return valid_ohlc
    
    @staticmethod
    def sanitize_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Attempt to clean/fix common data issues
        Returns sanitized DataFrame
        """
        df = df.copy()
        
        # Remove duplicates (keep first)
        df = df[~df.index.duplicated(keep='first')]
        
        # Sort by date
        df = df.sort_index()
        
        # Fill missing volumes with 0
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0)
        
        # Remove rows with NaN prices
        price_cols = ['open', 'high', 'low', 'close']
        df = df.dropna(subset=price_cols)
        
        # Remove rows with zero prices
        for col in price_cols:
            df = df[df[col] > 0]
        
        return df


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def validate_kite_response(
    data: List[Dict],
    exchange: str,
    symbol: str,
    interval: str,
) -> ValidationResult:
    """
    Validate data from Kite Connect API response
    
    Convenience function for common use case
    """
    validator = DataValidator(strict_mode=False)
    return validator.validate(data, exchange, symbol, interval)


def is_data_valid(data: Union[List[Dict], pd.DataFrame]) -> bool:
    """Quick check if data is valid"""
    if isinstance(data, list):
        if len(data) == 0:
            return False
        df = pd.DataFrame(data)
    else:
        df = data
    
    return DataValidator.quick_validate(df)
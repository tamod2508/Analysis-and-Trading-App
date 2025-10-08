"""
Data validation rules for OHLCV data
Separated from schema definitions for Single Responsibility Principle
"""

import numpy as np
from typing import List, Tuple, Dict
from config.constants import (
    MIN_PRICE,
    MAX_PRICE,
    MIN_VOLUME,
    MAX_VOLUME,
    MIN_DATE,
    MAX_DATE
)


class BaseValidationRules:
    """
    Base class for OHLCV data validation
    Provides common validation logic shared across all instrument types
    """

    # Override these in subclasses
    MIN_PRICE_LIMIT = MIN_PRICE
    MAX_PRICE_LIMIT = MAX_PRICE

    @classmethod
    def validate_ohlc_relationship(cls, row: np.ndarray) -> List[str]:
        """
        Validate OHLC relationships (common for all instruments)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not (row['low'] <= row['open'] <= row['high']):
            errors.append("Invalid OHLC: low <= open <= high violated")

        if not (row['low'] <= row['close'] <= row['high']):
            errors.append("Invalid OHLC: low <= close <= high violated")

        return errors

    @classmethod
    def validate_price_range(cls, row: np.ndarray) -> List[str]:
        """
        Validate price ranges

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        for field in ['open', 'high', 'low', 'close']:
            price = row[field]
            if not (cls.MIN_PRICE_LIMIT <= price <= cls.MAX_PRICE_LIMIT):
                errors.append(f"{field} price out of range: {price}")

        return errors

    @classmethod
    def validate_volume(cls, row: np.ndarray) -> List[str]:
        """
        Validate volume (common for all instruments)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not (MIN_VOLUME <= row['volume'] <= MAX_VOLUME):
            errors.append(f"Volume out of range: {row['volume']}")

        return errors

    @classmethod
    def validate_timestamp(cls, row: np.ndarray) -> List[str]:
        """
        Validate timestamp (common for all instruments)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not (MIN_DATE <= row['timestamp'] <= MAX_DATE):
            errors.append(f"Timestamp out of range: {row['timestamp']}")

        return errors


class ValidationRules(BaseValidationRules):
    """Data validation rules for equity OHLCV data"""

    # Equity-specific price limits
    MIN_PRICE_LIMIT = MIN_PRICE  # 0.01
    MAX_PRICE_LIMIT = MAX_PRICE  # 1,000,000

    @classmethod
    def validate_ohlcv_row(cls, row: np.ndarray) -> Tuple[bool, List[str]]:
        """Validate a single OHLCV row"""
        errors = []

        # Use base class methods for common validation
        errors.extend(cls.validate_ohlc_relationship(row))
        errors.extend(cls.validate_price_range(row))
        errors.extend(cls.validate_volume(row))
        errors.extend(cls.validate_timestamp(row))

        return len(errors) == 0, errors

    @classmethod
    def validate_ohlcv_array(cls, data: np.ndarray) -> Tuple[bool, Dict]:
        """
        Validate an array of OHLCV data

        Returns:
            (is_valid, stats_dict)
        """
        total_rows = len(data)
        invalid_rows = []

        for i, row in enumerate(data):
            is_valid, errors = cls.validate_ohlcv_row(row)
            if not is_valid:
                invalid_rows.append((i, errors))
                if len(invalid_rows) >= 10:  # Limit error collection
                    break

        stats = {
            'total_rows': total_rows,
            'valid_rows': total_rows - len(invalid_rows),
            'invalid_rows': len(invalid_rows),
            'invalid_details': invalid_rows,
        }

        return len(invalid_rows) == 0, stats


class OptionsValidationRules(BaseValidationRules):
    """Data validation rules for options/derivatives OHLCV data"""

    # Options-specific limits (options can go to ₹0)
    MIN_PRICE_LIMIT = 0.0  # Options can expire worthless
    MAX_PRICE_LIMIT = 100_000.0  # Max option price (sanity check)
    MIN_OI = 0  # Minimum open interest
    MAX_OI = 100_000_000  # Max open interest (100M contracts)

    @classmethod
    def validate_open_interest(cls, row: np.ndarray) -> List[str]:
        """
        Validate open interest (options-specific)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not (cls.MIN_OI <= row['oi'] <= cls.MAX_OI):
            errors.append(f"Open Interest out of range: {row['oi']}")

        return errors

    @classmethod
    def validate_options_row(cls, row: np.ndarray) -> Tuple[bool, List[str]]:
        """Validate a single options OHLCV row"""
        errors = []

        # Use base class methods for common validation
        errors.extend(cls.validate_ohlc_relationship(row))
        errors.extend(cls.validate_price_range(row))
        errors.extend(cls.validate_volume(row))
        errors.extend(cls.validate_timestamp(row))

        # Options-specific validation
        errors.extend(cls.validate_open_interest(row))

        return len(errors) == 0, errors

    @classmethod
    def validate_options_array(cls, data: np.ndarray) -> Tuple[bool, Dict]:
        """
        Validate an array of options OHLCV data

        Returns:
            (is_valid, stats_dict)
        """
        total_rows = len(data)
        invalid_rows = []

        for i, row in enumerate(data):
            is_valid, errors = cls.validate_options_row(row)
            if not is_valid:
                invalid_rows.append((i, errors))
                if len(invalid_rows) >= 10:  # Limit error collection
                    break

        stats = {
            'total_rows': total_rows,
            'valid_rows': total_rows - len(invalid_rows),
            'invalid_rows': len(invalid_rows),
            'invalid_details': invalid_rows,
        }

        return len(invalid_rows) == 0, stats

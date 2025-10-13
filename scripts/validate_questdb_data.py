"""
QuestDB Data Validation Script

Fetches random data from Kite API and compares with QuestDB to validate migration.

Usage:
    python scripts/validate_questdb_data.py --symbols=10 --dates=10
"""

import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.kite_client import KiteClient
from quest.config import CONNECTION_CONFIG, TableNames
from utils.logger import get_logger

logger = get_logger(__name__, 'validation.log')


class DataValidator:
    """Validates QuestDB data against fresh Kite API data"""

    def __init__(self):
        self.kite_client = KiteClient()
        self.questdb_url = CONNECTION_CONFIG.http_url
        self.validation_results = []
        self.total_dates_checked = 0
        self.dates_passed = 0
        self.dates_failed = 0

    def get_random_symbols(self, n_symbols: int = 10) -> list:
        """Get random symbols from QuestDB"""
        logger.info(f"Selecting {n_symbols} random symbols from QuestDB...")

        query = f"SELECT DISTINCT symbol, exchange FROM {TableNames.OHLCV_EQUITY} WHERE interval = 'day'"

        try:
            response = requests.get(f"{self.questdb_url}/exec", params={'query': query}, timeout=30)
            response.raise_for_status()
            result = response.json()

            if 'dataset' not in result or len(result['dataset']) == 0:
                logger.error("No data found in QuestDB")
                return []

            symbols = [(row[0], row[1]) for row in result['dataset']]
            selected = random.sample(symbols, min(n_symbols, len(symbols)))

            logger.info(f"Selected {len(selected)} symbols for validation")
            return selected

        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []

    def get_random_dates_for_symbol(self, symbol: str, exchange: str, n_dates: int = 10) -> list:
        """Get random dates for a symbol from QuestDB"""
        query = f"""
            SELECT timestamp
            FROM {TableNames.OHLCV_EQUITY}
            WHERE symbol = '{symbol}' AND exchange = '{exchange}' AND interval = 'day'
            ORDER BY timestamp
        """

        try:
            response = requests.get(f"{self.questdb_url}/exec", params={'query': query}, timeout=30)
            response.raise_for_status()
            result = response.json()

            if 'dataset' not in result or len(result['dataset']) == 0:
                return []

            all_dates = [datetime.fromisoformat(row[0].replace('Z', '+00:00')) for row in result['dataset']]
            selected_dates = random.sample(all_dates, min(n_dates, len(all_dates)))

            return selected_dates

        except Exception as e:
            logger.error(f"Error getting dates for {symbol}: {e}")
            return []

    def validate_date(self, symbol: str, exchange: str, date: datetime) -> dict:
        """Validate single date for a symbol"""
        result = {
            'symbol': symbol,
            'exchange': exchange,
            'date': date.date(),
            'status': 'PASS',
            'issues': []
        }

        try:
            # Fetch from QuestDB
            query = f"""
                SELECT open, high, low, close, volume
                FROM {TableNames.OHLCV_EQUITY}
                WHERE symbol = '{symbol}'
                    AND exchange = '{exchange}'
                    AND interval = 'day'
                    AND timestamp = '{date.strftime("%Y-%m-%dT%H:%M:%S")}.000000Z'
            """

            resp = requests.get(f"{self.questdb_url}/exec", params={'query': query}, timeout=30)
            resp.raise_for_status()
            qdb_result = resp.json()

            if 'dataset' not in qdb_result or len(qdb_result['dataset']) == 0:
                result['status'] = 'FAIL'
                result['issues'].append("Data not found in QuestDB")
                return result

            qdb_data = qdb_result['dataset'][0]
            qdb_ohlcv = {
                'open': qdb_data[0],
                'high': qdb_data[1],
                'low': qdb_data[2],
                'close': qdb_data[3],
                'volume': qdb_data[4]
            }

            # Fetch from Kite API
            instrument_token = self.kite_client.lookup_instrument_token(exchange, symbol)
            if not instrument_token:
                result['status'] = 'SKIP'
                result['issues'].append("Instrument token not found")
                return result

            # Fetch 3-day window to ensure we get the date
            from_date = date - timedelta(days=1)
            to_date = date + timedelta(days=1)

            kite_data = self.kite_client.fetch_historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval='day'
            )

            if not kite_data:
                result['status'] = 'SKIP'
                result['issues'].append("No data from Kite API")
                return result

            # Find matching date
            kite_row = None
            for row in kite_data:
                row_date = pd.to_datetime(row['date']).date()
                if row_date == date.date():
                    kite_row = row
                    break

            if not kite_row:
                result['status'] = 'SKIP'
                result['issues'].append("Date not found in Kite data")
                return result

            # Compare values
            tolerance = 0.01  # 1 paisa

            for field in ['open', 'high', 'low', 'close']:
                kite_val = kite_row[field]
                qdb_val = qdb_ohlcv[field]
                diff = abs(kite_val - qdb_val)

                if diff > tolerance:
                    result['status'] = 'FAIL'
                    result['issues'].append(
                        f"{field}: Kite={kite_val:.2f}, QDB={qdb_val:.2f}, diff={diff:.4f}"
                    )

            # Check volume
            if kite_row['volume'] != qdb_ohlcv['volume']:
                result['status'] = 'WARN'
                result['issues'].append(
                    f"volume: Kite={kite_row['volume']}, QDB={qdb_ohlcv['volume']}"
                )

        except Exception as e:
            result['status'] = 'ERROR'
            result['issues'].append(f"Exception: {str(e)}")

        return result

    def validate_symbol(self, symbol: str, exchange: str, n_dates: int = 10):
        """Validate random dates for a symbol"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Validating: {exchange}:{symbol}")
        logger.info(f"{'='*80}")

        # Get random dates
        dates = self.get_random_dates_for_symbol(symbol, exchange, n_dates)
        if not dates:
            logger.warning(f"No dates found for {exchange}:{symbol}")
            return

        logger.info(f"Validating {len(dates)} random dates...")

        # Validate each date
        for i, date in enumerate(dates, 1):
            result = self.validate_date(symbol, exchange, date)
            self.validation_results.append(result)
            self.total_dates_checked += 1

            if result['status'] == 'PASS':
                self.dates_passed += 1
                logger.info(f"  [{i}/{len(dates)}] {date.date()}: ✓ PASS")
            elif result['status'] == 'SKIP':
                logger.info(f"  [{i}/{len(dates)}] {date.date()}: ⊘ SKIP - {result['issues'][0]}")
            elif result['status'] == 'WARN':
                logger.warning(f"  [{i}/{len(dates)}] {date.date()}: ⚠ WARN - {', '.join(result['issues'])}")
            elif result['status'] == 'FAIL':
                self.dates_failed += 1
                logger.error(f"  [{i}/{len(dates)}] {date.date()}: ✗ FAIL - {', '.join(result['issues'])}")
            elif result['status'] == 'ERROR':
                self.dates_failed += 1
                logger.error(f"  [{i}/{len(dates)}] {date.date()}: ✗ ERROR - {', '.join(result['issues'])}")

    def run_validation(self, n_symbols: int = 10, n_dates: int = 10):
        """Run validation"""
        logger.info("=" * 80)
        logger.info("QuestDB Data Validation")
        logger.info("=" * 80)

        # Get random symbols
        symbols = self.get_random_symbols(n_symbols)
        if not symbols:
            logger.error("No symbols to validate")
            return

        logger.info(f"Will validate {len(symbols)} symbols × {n_dates} dates = {len(symbols) * n_dates} total checks")

        # Validate each symbol
        for i, (symbol, exchange) in enumerate(symbols, 1):
            logger.info(f"\n[Symbol {i}/{len(symbols)}]")
            self.validate_symbol(symbol, exchange, n_dates)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print validation summary"""
        logger.info("\n" + "=" * 80)
        logger.info("Validation Summary")
        logger.info("=" * 80)

        passed = sum(1 for r in self.validation_results if r['status'] == 'PASS')
        warned = sum(1 for r in self.validation_results if r['status'] == 'WARN')
        failed = sum(1 for r in self.validation_results if r['status'] == 'FAIL')
        skipped = sum(1 for r in self.validation_results if r['status'] == 'SKIP')
        errors = sum(1 for r in self.validation_results if r['status'] == 'ERROR')

        logger.info(f"Total checks: {len(self.validation_results)}")
        logger.info(f"✓ Passed: {passed}")
        logger.info(f"⚠ Warnings: {warned}")
        logger.info(f"✗ Failed: {failed}")
        logger.info(f"⊘ Skipped: {skipped}")
        logger.info(f"✗ Errors: {errors}")

        if passed > 0:
            accuracy = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
            logger.info(f"\nAccuracy: {accuracy:.2f}% ({passed}/{passed + failed} validated successfully)")

        logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate QuestDB data against Kite API')
    parser.add_argument('--symbols', type=int, default=10, help='Number of symbols to validate')
    parser.add_argument('--dates', type=int, default=10, help='Number of dates per symbol to validate')

    args = parser.parse_args()

    validator = DataValidator()
    validator.run_validation(n_symbols=args.symbols, n_dates=args.dates)


if __name__ == '__main__':
    main()

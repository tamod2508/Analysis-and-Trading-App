"""
Script to add more equity symbols to the EQUITY database
This will test the dynamic update feature of the UI
"""

from api.kite_client import KiteClient
from database.hdf5_manager import HDF5Manager
from database.instruments_db import InstrumentsDB
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_equity_symbols():
    """Fetch and store data for popular NSE stocks"""

    # Popular NSE stocks with their instrument tokens
    # Note: These are real tokens - in production, fetch from instruments DB
    symbols_with_tokens = [
        ('RELIANCE', 738561),   # Reliance Industries
        ('TCS', 2953217),       # Tata Consultancy Services
        ('INFY', 408065),       # Infosys
        ('HDFCBANK', 341249),   # HDFC Bank
        ('ICICIBANK', 1270529)  # ICICI Bank
    ]

    exchange = 'NSE'
    interval = 'day'

    # Fetch last 30 days of data
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)

    # Initialize clients
    kite_client = KiteClient()
    manager = HDF5Manager(segment='EQUITY')

    success_count = 0

    for symbol, instrument_token in symbols_with_tokens:
        try:
            logger.info(f"Fetching data for {symbol} (token: {instrument_token})...")

            # Fetch historical data
            data = kite_client.fetch_historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )

            if data and len(data) > 0:
                # Store in database
                success = manager.save_ohlcv(
                    exchange=exchange,
                    symbol=symbol,
                    interval=interval,
                    data=data,
                    overwrite=False
                )

                if success:
                    logger.info(f"✓ Successfully added {symbol}: {len(data)} records")
                    success_count += 1
                else:
                    logger.warning(f"✗ Failed to save {symbol} to database")
            else:
                logger.warning(f"✗ No data received for {symbol}")

        except Exception as e:
            logger.error(f"✗ Failed to add {symbol}: {e}")

    logger.info(f"\n{'='*60}")
    logger.info(f"Summary: Successfully added {success_count}/{len(symbols_with_tokens)} symbols")
    logger.info(f"{'='*60}\n")

    # Show updated database stats
    stats = manager.get_database_stats()
    logger.info("Updated EQUITY Database Stats:")
    logger.info(f"  - File Size: {stats['file_size_mb']} MB")
    logger.info(f"  - Total Symbols: {stats['total_symbols']}")
    logger.info(f"  - Total Datasets: {stats['total_datasets']}")

    for exchange, exch_stats in stats['exchanges'].items():
        logger.info(f"  - {exchange}: {exch_stats['symbols']} symbols, {exch_stats['datasets']} datasets")


if __name__ == '__main__':
    print("Adding more equity symbols to EQUITY database...")
    print("This will fetch last 30 days of daily data for popular NSE stocks\n")
    add_equity_symbols()

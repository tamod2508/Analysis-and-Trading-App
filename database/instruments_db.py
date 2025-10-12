"""
Instruments Database Manager
Stores instrument master data (symbols, tokens, metadata) in HDF5 for fast lookups
Eliminates need to fetch instruments from API on every call
"""

import h5py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import config
from utils.logger import get_logger

logger = get_logger(__name__, 'instruments.log')


class InstrumentsDB:
    """
    Manages persistent storage of instrument master data

    Features:
    - Stores instruments per exchange in HDF5 format
    - Fast symbol → token lookups via pandas indexing
    - Auto-refresh if data is stale (configurable TTL)
    - Export to CSV/Excel for human inspection
    - Compressed storage with blosc

    Storage Structure:
    instruments.h5
    ├── /NSE/
    │   ├── instruments (dataset)  # Full instrument data
    │   ├── metadata (attrs)       # Last updated, record count
    ├── /BSE/
    │   ├── instruments
    │   ├── metadata
    ├── /NFO/
    └── /BFO/
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ttl_days: int = 7,  # Refresh if older than 7 days
    ):
        """
        Initialize Instruments Database

        Args:
            db_path: Path to instruments.h5 file (default: data/instruments.h5)
            ttl_days: Auto-refresh if data older than this many days
        """
        self.db_path = db_path or config.DATA_DIR / 'instruments.h5'
        self.ttl_days = ttl_days

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache for current session
        self._cache: Dict[str, pd.DataFrame] = {}

        logger.info(f"InstrumentsDB initialized: {self.db_path}")

    def save_instruments(
        self,
        exchange: str,
        instruments: List[Dict],
        overwrite: bool = True
    ) -> bool:
        """
        Save instruments to database

        Args:
            exchange: Exchange name (NSE, BSE, NFO, BFO)
            instruments: List of instrument dicts from Kite API
            overwrite: Overwrite existing data (default: True)

        Returns:
            Success status
        """
        if not instruments:
            logger.warning(f"No instruments to save for {exchange}")
            return False

        try:
            # Convert to DataFrame
            df = pd.DataFrame(instruments)

            # Ensure required columns exist
            required_cols = ['instrument_token', 'tradingsymbol']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns in instruments data")
                return False

            # Save to HDF5
            with h5py.File(self.db_path, 'a') as f:
                group_path = f'/{exchange}'

                # Delete existing group if overwriting
                if overwrite and group_path in f:
                    del f[group_path]

                # Create group
                grp = f.require_group(group_path)

                # Save metadata
                grp.attrs['last_updated'] = datetime.now().isoformat()
                grp.attrs['record_count'] = len(df)
                grp.attrs['exchange'] = exchange

                # Save DataFrame as dataset (using pandas HDF5 store would be cleaner but we want consistency)
                # Convert DataFrame to structured array for HDF5 storage

                # Store as CSV string (simple and flexible)
                csv_data = df.to_csv(index=False)

                # Create dataset with compression
                if 'data' in grp:
                    del grp['data']

                grp.create_dataset(
                    'data',
                    data=np.frombuffer(csv_data.encode(), dtype='S1'),
                    compression='gzip',
                    compression_opts=9
                )

            logger.info(f"✓ Saved {len(df)} instruments for {exchange} to {self.db_path}")

            # Update cache
            self._cache[exchange] = df

            return True

        except Exception as e:
            logger.error(f"Failed to save instruments for {exchange}: {e}")
            return False

    def get_instruments(
        self,
        exchange: str,
        refresh_if_stale: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get instruments for an exchange

        Args:
            exchange: Exchange name
            refresh_if_stale: If True and data is stale, return None (caller should refresh)

        Returns:
            DataFrame with instruments, or None if not found/stale
        """
        # Check memory cache first
        if exchange in self._cache:
            logger.debug(f"Using cached instruments for {exchange}")
            return self._cache[exchange]

        # Check if file exists
        if not self.db_path.exists():
            logger.info(f"Instruments database not found: {self.db_path}")
            return None

        try:
            with h5py.File(self.db_path, 'r') as f:
                group_path = f'/{exchange}'

                # Check if exchange exists
                if group_path not in f:
                    logger.info(f"No instruments found for {exchange} in database")
                    return None

                grp = f[group_path]

                # Check if data is stale
                if refresh_if_stale:
                    last_updated_str = grp.attrs.get('last_updated')
                    if last_updated_str:
                        last_updated = datetime.fromisoformat(last_updated_str)
                        age_days = (datetime.now() - last_updated).days

                        if age_days > self.ttl_days:
                            logger.warning(
                                f"Instruments for {exchange} are {age_days} days old "
                                f"(TTL: {self.ttl_days} days). Refresh recommended."
                            )
                            return None

                # Load data
                csv_bytes = grp['data'][()].tobytes()
                csv_string = csv_bytes.decode('utf-8')

                # Parse CSV
                from io import StringIO
                df = pd.read_csv(StringIO(csv_string))

                logger.info(f"Loaded {len(df)} instruments for {exchange} from database")

                # Cache it
                self._cache[exchange] = df

                return df

        except Exception as e:
            logger.error(f"Failed to load instruments for {exchange}: {e}")
            return None

    def lookup_token(
        self,
        exchange: str,
        symbol: str,
        refresh_if_stale: bool = True
    ) -> Optional[int]:
        """
        Fast lookup: symbol → instrument_token

        Args:
            exchange: Exchange name
            symbol: Trading symbol
            refresh_if_stale: Return None if data is stale

        Returns:
            Instrument token or None if not found
        """
        df = self.get_instruments(exchange, refresh_if_stale)

        if df is None:
            return None

        # Lookup symbol
        matches = df[df['tradingsymbol'] == symbol]

        if len(matches) == 0:
            logger.debug(f"Symbol {symbol} not found on {exchange}")
            return None

        token = int(matches.iloc[0]['instrument_token'])
        logger.debug(f"Found {symbol} on {exchange}: token={token}")
        return token

    def lookup_instrument(
        self,
        exchange: str,
        symbol: str,
        refresh_if_stale: bool = True
    ) -> Optional[Dict]:
        """
        Lookup full instrument details

        Args:
            exchange: Exchange name
            symbol: Trading symbol
            refresh_if_stale: Return None if data is stale

        Returns:
            Instrument dict or None if not found
        """
        df = self.get_instruments(exchange, refresh_if_stale)

        if df is None:
            return None

        matches = df[df['tradingsymbol'] == symbol]

        if len(matches) == 0:
            return None

        return matches.iloc[0].to_dict()

    def search_symbols(
        self,
        exchange: str,
        pattern: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for symbols matching a pattern

        Args:
            exchange: Exchange name
            pattern: Search pattern (case-insensitive substring match)
            limit: Max results to return

        Returns:
            List of matching instruments
        """
        df = self.get_instruments(exchange, refresh_if_stale=False)

        if df is None:
            return []

        # Case-insensitive search
        matches = df[
            df['tradingsymbol'].str.contains(pattern, case=False, na=False)
        ]

        # Limit results
        matches = matches.head(limit)

        return matches.to_dict('records')

    def get_metadata(self, exchange: str) -> Optional[Dict]:
        """
        Get metadata for an exchange (last updated, record count, etc.)

        Args:
            exchange: Exchange name

        Returns:
            Metadata dict or None if not found
        """
        if not self.db_path.exists():
            return None

        try:
            with h5py.File(self.db_path, 'r') as f:
                group_path = f'/{exchange}'

                if group_path not in f:
                    return None

                grp = f[group_path]

                metadata = {
                    'exchange': grp.attrs.get('exchange'),
                    'last_updated': grp.attrs.get('last_updated'),
                    'record_count': grp.attrs.get('record_count'),
                }

                # Calculate age
                if metadata['last_updated']:
                    last_updated = datetime.fromisoformat(metadata['last_updated'])
                    metadata['age_days'] = (datetime.now() - last_updated).days
                    metadata['is_stale'] = metadata['age_days'] > self.ttl_days

                return metadata

        except Exception as e:
            logger.error(f"Failed to get metadata for {exchange}: {e}")
            return None

    def get_all_metadata(self) -> Dict[str, Dict]:
        """
        Get metadata for all exchanges in the database

        Returns:
            Dict mapping exchange → metadata
        """
        if not self.db_path.exists():
            return {}

        metadata_map = {}

        try:
            with h5py.File(self.db_path, 'r') as f:
                for exchange in f.keys():
                    meta = self.get_metadata(exchange)
                    if meta:
                        metadata_map[exchange] = meta

        except Exception as e:
            logger.error(f"Failed to get all metadata: {e}")

        return metadata_map

    def export_to_csv(
        self,
        exchange: str,
        output_path: Optional[Path] = None
    ) -> bool:
        """
        Export instruments to CSV (for Excel)

        Args:
            exchange: Exchange name
            output_path: Output CSV path (default: exports/{exchange}_instruments.csv)

        Returns:
            Success status
        """
        df = self.get_instruments(exchange, refresh_if_stale=False)

        if df is None:
            logger.error(f"No instruments to export for {exchange}")
            return False

        # Default output path
        if output_path is None:
            output_path = config.EXPORTS_DIR / f'{exchange}_instruments.csv'

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            df.to_csv(output_path, index=False)
            logger.info(f"✓ Exported {len(df)} instruments to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export instruments: {e}")
            return False

    def export_all_to_excel(
        self,
        output_path: Optional[Path] = None
    ) -> bool:
        """
        Export all exchanges to a single Excel file (multiple sheets)

        Args:
            output_path: Output Excel path (default: exports/all_instruments.xlsx)

        Returns:
            Success status
        """
        if output_path is None:
            output_path = config.EXPORTS_DIR / 'all_instruments.xlsx'

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Get all exchanges
                exchanges = self.get_all_exchanges()

                if not exchanges:
                    logger.warning("No exchanges found in database")
                    return False

                for exchange in exchanges:
                    df = self.get_instruments(exchange, refresh_if_stale=False)
                    if df is not None:
                        df.to_excel(writer, sheet_name=exchange, index=False)
                        logger.info(f"✓ Added {exchange} sheet ({len(df)} instruments)")

            logger.info(f"✓ Exported all instruments to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            return False

    def get_all_exchanges(self) -> List[str]:
        """
        Get list of all exchanges in the database

        Returns:
            List of exchange names
        """
        if not self.db_path.exists():
            return []

        try:
            with h5py.File(self.db_path, 'r') as f:
                return list(f.keys())
        except Exception as e:
            logger.error(f"Failed to get exchanges: {e}")
            return []

    def clear_cache(self):
        """Clear in-memory cache"""
        self._cache.clear()
        logger.info("Cleared instruments cache")

    def needs_refresh(self, exchange: str) -> bool:
        """
        Check if exchange data needs refresh (is stale or missing)

        Args:
            exchange: Exchange name

        Returns:
            True if refresh needed
        """
        metadata = self.get_metadata(exchange)

        if metadata is None:
            return True  # No data

        return metadata.get('is_stale', True)

    def get_database_stats(self) -> Dict:
        """
        Get overall database statistics

        Returns:
            Dict with database stats
        """
        if not self.db_path.exists():
            return {
                'exists': False,
                'file_size': 0,
                'exchanges': [],
                'total_instruments': 0,
                'db_path': str(self.db_path)
            }

        exchanges = self.get_all_exchanges()
        all_metadata = self.get_all_metadata()

        total_instruments = sum(
            meta.get('record_count', 0)
            for meta in all_metadata.values()
        )

        return {
            'exists': True,
            'file_size': self.db_path.stat().st_size,
            'file_size_mb': round(self.db_path.stat().st_size / 1024 / 1024, 2),
            'exchanges': exchanges,
            'total_instruments': total_instruments,
            'metadata': all_metadata,
            'db_path': str(self.db_path)
        }

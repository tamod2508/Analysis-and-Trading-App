"""
Fundamentals HDF5 Manager
Handles storage and retrieval of fundamental data in FUNDAMENTALS.h5
"""

import h5py
import hdf5plugin  # Register blosc and other compression filters
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from config import config
from database.fundamentals_schema import (
    FundamentalsHDF5Structure,
    BalanceSheetSchema,
    IncomeStatementSchema,
    CashFlowSchema,
    CompanyGeneralInfo,
    CompanyHighlights,
    get_schema_for_dataset,
)
from utils.logger import get_logger

logger = get_logger(__name__, 'fundamentals.log')


class FundamentalsManager:
    """
    Manages fundamental data storage in HDF5 format

    File: FUNDAMENTALS.h5
    Location: data/hdf5/FUNDAMENTALS.h5

    Usage:
        manager = FundamentalsManager()
        manager.save_company_fundamentals('NSE', 'RELIANCE', parsed_data)
        data = manager.get_company_fundamentals('NSE', 'RELIANCE')
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize FundamentalsManager

        Args:
            db_path: Path to FUNDAMENTALS.h5 (defaults to config.HDF5_DIR/FUNDAMENTALS.h5)
        """
        if db_path is None:
            self.db_path = config.HDF5_DIR / 'FUNDAMENTALS.h5'
        else:
            self.db_path = Path(db_path)

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Get HDF5 file options from config
        self.hdf5_options = config.get_hdf5_options()

        # Initialize database if it doesn't exist
        if not self.db_path.exists():
            self._initialize_database()

        logger.info(f"FundamentalsManager initialized: {self.db_path}")

    def _get_compression_settings(self, data_size: int = None) -> dict:
        """
        Get compression settings for HDF5 datasets

        Returns:
            Dict with hdf5plugin.Blosc filter and chunks for create_dataset()
        """
        # Get base settings from config (using 'day' interval as baseline)
        settings = config.get_hdf5_creation_settings('day', data_size)

        # Create blosc filter object
        blosc_filter = hdf5plugin.Blosc(
            cname='lz4',
            clevel=config.HDF5_COMPRESSION_LEVEL,
            shuffle=hdf5plugin.Blosc.SHUFFLE,
        )

        return {
            **blosc_filter,
            'chunks': settings['chunks']
        }

    def _initialize_database(self):
        """Create new FUNDAMENTALS.h5 with proper structure"""
        logger.info("Creating new FUNDAMENTALS.h5...")

        with h5py.File(self.db_path, 'w', **self.hdf5_options) as f:
            # Create root groups
            for group in FundamentalsHDF5Structure.ROOT_GROUPS:
                f.create_group(group)

            # Create exchange groups
            for group in FundamentalsHDF5Structure.EXCHANGE_GROUPS:
                f.create_group(group)

            # Add metadata
            metadata_group = f['/metadata']
            metadata_group.attrs['created_at'] = datetime.now().isoformat()
            metadata_group.attrs['version'] = '1.0'
            metadata_group.attrs['description'] = 'Fundamental data from EODHD API'

        logger.info("✅ FUNDAMENTALS.h5 created successfully")

    def save_company_fundamentals(
        self,
        exchange: str,
        symbol: str,
        parsed_data: Dict,
        overwrite: bool = True
    ) -> bool:
        """
        Save fundamental data for a company

        Args:
            exchange: NSE or BSE
            symbol: Company symbol (e.g., RELIANCE)
            parsed_data: Dict from FundamentalsParser.parse_all()
            overwrite: If True, replace existing data

        Returns:
            True if saved successfully
        """
        try:
            company_path = FundamentalsHDF5Structure.get_company_group_path(exchange, symbol)

            with h5py.File(self.db_path, 'a', **self.hdf5_options) as f:
                # Create or get company group
                if company_path in f:
                    if overwrite:
                        del f[company_path]
                    else:
                        logger.warning(f"Data already exists for {symbol}, use overwrite=True to replace")
                        return False

                company_group = f.create_group(company_path)

                # Save general info as attributes
                if parsed_data.get('general'):
                    for field in CompanyGeneralInfo.FIELDS:
                        value = parsed_data['general'].get(field, '')
                        company_group.attrs[f'general_{field}'] = str(value)

                # Save highlights as attributes
                if parsed_data.get('highlights'):
                    for field in CompanyHighlights.FIELDS:
                        value = parsed_data['highlights'].get(field, 0.0)
                        company_group.attrs[f'highlight_{field}'] = float(value)

                # Save financial statement datasets
                dataset_map = {
                    'balance_sheet_yearly': parsed_data.get('balance_sheet_yearly'),
                    'balance_sheet_quarterly': parsed_data.get('balance_sheet_quarterly'),
                    'income_statement_yearly': parsed_data.get('income_statement_yearly'),
                    'income_statement_quarterly': parsed_data.get('income_statement_quarterly'),
                    'cash_flow_yearly': parsed_data.get('cash_flow_yearly'),
                    'cash_flow_quarterly': parsed_data.get('cash_flow_quarterly'),
                }

                for dataset_name, data_array in dataset_map.items():
                    if data_array is not None and len(data_array) > 0:
                        # Get compression settings from config with proper blosc filter
                        comp_settings = self._get_compression_settings(len(data_array))

                        # Create dataset with config-based compression
                        company_group.create_dataset(
                            dataset_name,
                            data=data_array,
                            **comp_settings
                        )
                        logger.debug(f"Saved {dataset_name}: {len(data_array)} periods")

                # Add update timestamp
                company_group.attrs['last_updated'] = datetime.now().isoformat()
                company_group.attrs['source'] = 'EODHD'

            logger.info(f"✅ Saved fundamentals for {exchange}:{symbol}")
            return True

        except Exception as e:
            logger.error(f"Error saving fundamentals for {symbol}: {e}")
            return False

    def get_company_fundamentals(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        Retrieve fundamental data for a company

        Args:
            exchange: NSE or BSE
            symbol: Company symbol

        Returns:
            Dict with:
                - general: Company info dict
                - highlights: Metrics dict
                - balance_sheet_yearly: NumPy array
                - balance_sheet_quarterly: NumPy array
                - income_statement_yearly: NumPy array
                - income_statement_quarterly: NumPy array
                - cash_flow_yearly: NumPy array
                - cash_flow_quarterly: NumPy array
                - metadata: Dict with last_updated, source
        """
        try:
            company_path = FundamentalsHDF5Structure.get_company_group_path(exchange, symbol)

            with h5py.File(self.db_path, 'r', **self.hdf5_options) as f:
                if company_path not in f:
                    logger.warning(f"No data found for {exchange}:{symbol}")
                    return None

                company_group = f[company_path]

                # Extract general info from attributes
                general = {}
                for field in CompanyGeneralInfo.FIELDS:
                    key = f'general_{field}'
                    if key in company_group.attrs:
                        general[field] = company_group.attrs[key]

                # Extract highlights from attributes
                highlights = {}
                for field in CompanyHighlights.FIELDS:
                    key = f'highlight_{field}'
                    if key in company_group.attrs:
                        highlights[field] = float(company_group.attrs[key])

                # Extract datasets
                result = {
                    'general': general,
                    'highlights': highlights,
                    'balance_sheet_yearly': None,
                    'balance_sheet_quarterly': None,
                    'income_statement_yearly': None,
                    'income_statement_quarterly': None,
                    'cash_flow_yearly': None,
                    'cash_flow_quarterly': None,
                    'metadata': {
                        'last_updated': company_group.attrs.get('last_updated', ''),
                        'source': company_group.attrs.get('source', ''),
                    }
                }

                for dataset_name in FundamentalsHDF5Structure.DATASETS:
                    if dataset_name in company_group:
                        result[dataset_name] = company_group[dataset_name][:]

            logger.info(f"Retrieved fundamentals for {exchange}:{symbol}")
            return result

        except Exception as e:
            logger.error(f"Error retrieving fundamentals for {symbol}: {e}")
            return None

    def list_companies(self, exchange: Optional[str] = None) -> List[str]:
        """
        List all companies with fundamental data

        Args:
            exchange: Filter by exchange (NSE or BSE), or None for all

        Returns:
            List of symbols
        """
        try:
            symbols = []

            with h5py.File(self.db_path, 'r', **self.hdf5_options) as f:
                exchanges = [exchange] if exchange else ['NSE', 'BSE']

                for exch in exchanges:
                    exch_path = f"/companies/{exch}"
                    if exch_path in f:
                        symbols.extend(list(f[exch_path].keys()))

            return sorted(symbols)

        except Exception as e:
            logger.error(f"Error listing companies: {e}")
            return []

    def get_statistics(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dict with:
                - total_companies: Total count
                - nse_companies: NSE count
                - bse_companies: BSE count
                - file_size_mb: Database file size
                - last_modified: File modification time
        """
        try:
            stats = {
                'total_companies': 0,
                'nse_companies': 0,
                'bse_companies': 0,
                'file_size_mb': 0.0,
                'last_modified': '',
            }

            if not self.db_path.exists():
                return stats

            # File stats
            file_stats = self.db_path.stat()
            stats['file_size_mb'] = file_stats.st_size / (1024 * 1024)
            stats['last_modified'] = datetime.fromtimestamp(file_stats.st_mtime).isoformat()

            # Company counts
            with h5py.File(self.db_path, 'r', **self.hdf5_options) as f:
                if '/companies/NSE' in f:
                    stats['nse_companies'] = len(f['/companies/NSE'].keys())
                if '/companies/BSE' in f:
                    stats['bse_companies'] = len(f['/companies/BSE'].keys())

            stats['total_companies'] = stats['nse_companies'] + stats['bse_companies']

            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def delete_company(self, exchange: str, symbol: str) -> bool:
        """
        Delete fundamental data for a company

        Args:
            exchange: NSE or BSE
            symbol: Company symbol

        Returns:
            True if deleted successfully
        """
        try:
            company_path = FundamentalsHDF5Structure.get_company_group_path(exchange, symbol)

            with h5py.File(self.db_path, 'a', **self.hdf5_options) as f:
                if company_path in f:
                    del f[company_path]
                    logger.info(f"Deleted fundamentals for {exchange}:{symbol}")
                    return True
                else:
                    logger.warning(f"No data found for {exchange}:{symbol}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting fundamentals for {symbol}: {e}")
            return False

    def update_metadata(self, key: str, value: str):
        """
        Update database metadata

        Args:
            key: Metadata key
            value: Metadata value
        """
        try:
            with h5py.File(self.db_path, 'a', **self.hdf5_options) as f:
                f['/metadata'].attrs[key] = value
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")

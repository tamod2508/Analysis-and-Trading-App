"""
HDF5 Database Manager - EQUITY/INDEX ONLY
"""

import h5py
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Union
from contextlib import contextmanager
import shutil
import gc
import logging

from config.settings import config
from database.schema import (
    Interval,
    PRIMARY_INTERVALS,
    EquityOHLCVSchema,
    InstrumentSchema,
    HDF5Structure,
    DatasetAttributes,
    CompressionSettings,
    ValidationRules,
    create_empty_ohlcv_array,
    dict_to_ohlcv_array,
    ohlcv_array_to_dict,
)

logger = logging.getLogger(__name__)


class HDF5Manager:
    """
    HDF5 Database Manager for multi-timeframe equity/index data
    Thread-safe, memory-efficient operations optimized for M1
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize HDF5 Manager
        
        Args:
            db_path: Path to HDF5 file (default: from config)
        """
        self.db_path = Path(db_path) if db_path else config.HDF5_FILE
        self.structure = HDF5Structure()
        self.compression = CompressionSettings()
        
        # Ensure database exists
        if not self.db_path.exists():
            self._initialize_database()
        
        logger.info(f"HDF5Manager initialized: {self.db_path}")
    
    # ========================================================================
    # CONTEXT MANAGERS
    # ========================================================================
    
    @contextmanager
    def open_file(self, mode: str = 'r'):
        """
        Context manager for safe file operations
        
        Args:
            mode: 'r' (read), 'r+' (read/write), 'a' (append)
        
        Usage:
            with manager.open_file('r+') as f:
                # Use f as h5py.File object
        """
        f = None
        try:
            f = h5py.File(
                self.db_path,
                mode,
                rdcc_nbytes=config.HDF5_RDCC_NBYTES,
                rdcc_nslots=config.HDF5_RDCC_NSLOTS,
                rdcc_w0=config.HDF5_RDCC_W0,
            )
            yield f
        except Exception as e:
            logger.error(f"HDF5 file operation error: {e}")
            raise
        finally:
            if f is not None:
                f.close()
    
    # ========================================================================
    # DATABASE INITIALIZATION
    # ========================================================================
    
    def _initialize_database(self):
        """Create new HDF5 database with structure"""
        logger.info(f"Creating new database: {self.db_path}")
        
        with self.open_file('w') as f:
            # Create root groups
            for group_path in self.structure.ROOT_GROUPS:
                f.create_group(group_path)
            
            # Create exchange groups
            for exchange in self.structure.EXCHANGES:
                f.create_group(f'/instruments/{exchange}')
                f.create_group(f'/data/{exchange}')
            
            # Set database metadata
            f.attrs['db_version'] = '1.0'
            f.attrs['created_at'] = datetime.now().isoformat()
            f.attrs['last_updated'] = datetime.now().isoformat()
            f.attrs['format'] = 'kite_equity_v1'
        
        logger.info("Database initialized successfully")
    
    # ========================================================================
    # METADATA OPERATIONS
    # ========================================================================
    
    def set_metadata(self, key: str, value: str):
        """Set database metadata (stored as file attributes)"""
        with self.open_file('a') as f:
            f.attrs[key] = value
            f.attrs['last_updated'] = datetime.now().isoformat()
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get database metadata"""
        with self.open_file('r') as f:
            return f.attrs.get(key)
    
    def get_all_metadata(self) -> Dict:
        """Get all database metadata"""
        with self.open_file('r') as f:
            return dict(f.attrs)
    
    # ========================================================================
    # MULTI-TIMEFRAME OHLCV OPERATIONS
    # ========================================================================
    
    def save_ohlcv(
        self,
        exchange: str,
        symbol: str,
        interval: Union[str, Interval],
        data: Union[List[Dict], np.ndarray, pd.DataFrame],
        overwrite: bool = False,
    ) -> bool:
        """
        Save OHLCV data to database for a specific timeframe
        
        Args:
            exchange: Exchange name (NSE, BSE)
            symbol: Trading symbol
            interval: Timeframe (15minute, 60minute, day)
            data: OHLCV data (list of dicts, numpy array, or DataFrame)
            overwrite: If True, replace existing data
        
        Returns:
            True if successful
        """
        try:
            # Convert interval to string if Enum
            if isinstance(interval, Interval):
                interval = interval.value
            
            # Convert data to numpy array
            if isinstance(data, list):
                arr = dict_to_ohlcv_array(data)
            elif isinstance(data, pd.DataFrame):
                arr = self._dataframe_to_array(data)
            elif isinstance(data, np.ndarray):
                arr = data
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")
            
            if len(arr) == 0:
                logger.warning(f"Empty data array for {symbol} {interval}, nothing to save")
                return False
            
            # Validate data
            is_valid, stats = ValidationRules.validate_ohlcv_array(arr)
            if not is_valid:
                logger.error(f"Data validation failed for {symbol} {interval}: {stats}")
                raise ValueError(f"Invalid OHLCV data: {stats['invalid_rows']} invalid rows")
            
            # Sort by timestamp
            arr = np.sort(arr, order='timestamp')
            
            # Get dataset path
            path = self.structure.get_data_path(exchange, symbol, interval)
            
            # Get compression settings for this interval
            comp_settings = self.compression.get_settings(interval, data_size=len(arr))
            
            # Save to database
            with self.open_file('a') as f:
                # Create parent groups if needed
                self._ensure_groups_exist(f, path)
                
                if path in f:
                    if overwrite:
                        del f[path]
                        logger.info(f"Overwriting existing dataset: {path}")
                    else:
                        # Append to existing data
                        return self._append_ohlcv(f, path, arr)
                
                # Create new dataset
                dset = f.create_dataset(
                    path,
                    data=arr,
                    dtype=EquityOHLCVSchema.DTYPE,
                    **comp_settings,
                )
                
                # Set attributes (lean metadata)
                attrs = DatasetAttributes.ohlcv_attributes(
                    exchange=exchange,
                    symbol=symbol,
                    interval=interval,
                    start_date=str(arr[0]['timestamp']),
                    end_date=str(arr[-1]['timestamp']),
                    row_count=len(arr),
                )
                for k, v in attrs.items():
                    dset.attrs[k] = v
                
                # Update file-level last_updated
                f.attrs['last_updated'] = datetime.now().isoformat()
            
            logger.info(f"✅ Saved {len(arr)} records to {path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving OHLCV data for {symbol} {interval}: {e}")
            raise
    
    def _append_ohlcv(self, f: h5py.File, path: str, new_data: np.ndarray) -> bool:
        """Append data to existing dataset (deduplicates by timestamp)"""
        try:
            dset = f[path]
            existing_data = dset[:]
            
            # Merge and deduplicate by timestamp
            combined = np.concatenate([existing_data, new_data])
            # Use unique on structured array
            _, unique_indices = np.unique(combined['timestamp'], return_index=True)
            combined = combined[unique_indices]
            combined = np.sort(combined, order='timestamp')
            
            # Replace dataset
            compression = dset.compression
            chunks = dset.chunks
            attrs_backup = dict(dset.attrs)
            
            del f[path]
            new_dset = f.create_dataset(
                path,
                data=combined,
                dtype=EquityOHLCVSchema.DTYPE,
                compression=compression,
                chunks=chunks,
            )
            
            # Restore and update attributes
            for k, v in attrs_backup.items():
                new_dset.attrs[k] = v
            
            new_dset.attrs['start_date'] = str(combined[0]['timestamp'])
            new_dset.attrs['end_date'] = str(combined[-1]['timestamp'])
            new_dset.attrs['row_count'] = len(combined)
            new_dset.attrs['updated_at'] = datetime.now().isoformat()
            
            # Update file-level last_updated
            f.attrs['last_updated'] = datetime.now().isoformat()
            
            added = len(combined) - len(existing_data)
            logger.info(f"✅ Appended {added} new records to {path} (total: {len(combined)})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error appending data: {e}")
            raise
    
    def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        interval: Union[str, Interval],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        columns: Optional[List[str]] = None,
        as_dataframe: bool = True,
    ) -> Union[pd.DataFrame, np.ndarray, None]:
        """
        Retrieve OHLCV data from database for a specific timeframe
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            interval: Timeframe (15minute, 60minute, day)
            start_date: Filter start date (inclusive)
            end_date: Filter end date (inclusive)
            columns: Columns to retrieve (None = all)
            as_dataframe: Return as DataFrame (True) or numpy array (False)
        
        Returns:
            DataFrame, numpy array, or None if not found
        """
        try:
            # Convert interval to string if Enum
            if isinstance(interval, Interval):
                interval = interval.value
            
            path = self.structure.get_data_path(exchange, symbol, interval)
            
            with self.open_file('r') as f:
                if path not in f:
                    logger.warning(f"Dataset not found: {path}")
                    return None
                
                dset = f[path]
                
                # Read data (memory-mapped for efficiency)
                data = dset[:]
                
                # Filter by date range
                if start_date or end_date:
                    mask = np.ones(len(data), dtype=bool)
                    
                    if start_date:
                        start_ts = np.datetime64(start_date)
                        mask &= (data['timestamp'] >= start_ts)
                    
                    if end_date:
                        end_ts = np.datetime64(end_date)
                        mask &= (data['timestamp'] <= end_ts)
                    
                    data = data[mask]
                
                # Select columns
                if columns:
                    data = data[columns]
                
                # Convert to DataFrame if requested
                if as_dataframe:
                    df = pd.DataFrame(data)
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit ='s')
                        df = df.set_index('timestamp')
                    return df
                
                return data
                
        except Exception as e:
            logger.error(f"❌ Error retrieving OHLCV data for {symbol} {interval}: {e}")
            return None
    
    def delete_ohlcv(
        self,
        exchange: str,
        symbol: str,
        interval: Optional[Union[str, Interval]] = None
    ) -> bool:
        """
        Delete OHLCV dataset(s)
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            interval: Specific timeframe to delete (None = delete all timeframes)
        
        Returns:
            True if successful
        """
        try:
            if interval:
                # Delete specific interval
                if isinstance(interval, Interval):
                    interval = interval.value
                
                path = self.structure.get_data_path(exchange, symbol, interval)
                
                with self.open_file('a') as f:
                    if path in f:
                        del f[path]
                        f.attrs['last_updated'] = datetime.now().isoformat()
                        logger.info(f"✅ Deleted dataset: {path}")
                        return True
                    else:
                        logger.warning(f"Dataset not found: {path}")
                        return False
            else:
                # Delete all intervals for this symbol
                symbol_path = f'/data/{exchange.upper()}/{symbol.upper()}'
                
                with self.open_file('a') as f:
                    if symbol_path in f:
                        del f[symbol_path]
                        f.attrs['last_updated'] = datetime.now().isoformat()
                        logger.info(f"✅ Deleted all data for: {symbol_path}")
                        return True
                    else:
                        logger.warning(f"Symbol path not found: {symbol_path}")
                        return False
                    
        except Exception as e:
            logger.error(f"❌ Error deleting dataset: {e}")
            return False
    
    # ========================================================================
    # MULTI-TIMEFRAME QUERY & SEARCH
    # ========================================================================
    
    def list_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """List all symbols in database"""
        symbols = []
        
        with self.open_file('r') as f:
            data_group = f['/data']
            
            if exchange:
                exchanges = [exchange.upper()]
            else:
                exchanges = list(data_group.keys())
            
            for exch in exchanges:
                if exch in data_group:
                    exch_group = data_group[exch]
                    symbols.extend(list(exch_group.keys()))
        
        return sorted(set(symbols))
    
    def list_intervals(self, exchange: str, symbol: str) -> List[str]:
        """List available intervals for a symbol"""
        intervals = []
        
        with self.open_file('r') as f:
            base_path = f'/data/{exchange.upper()}/{symbol.upper()}'
            
            if base_path in f:
                group = f[base_path]
                intervals = list(group.keys())
        
        return intervals
    
    def get_data_info(self, exchange: str, symbol: str, interval: Union[str, Interval]) -> Dict:
        """Get information about a dataset"""
        if isinstance(interval, Interval):
            interval = interval.value
        
        path = self.structure.get_data_path(exchange, symbol, interval)
        
        with self.open_file('r') as f:
            if path not in f:
                return {}
            
            dset = f[path]
            
            return {
                'path': path,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval,
                'rows': dset.shape[0],
                'size_mb': round(dset.nbytes / (1024**2), 2),
                'compression': dset.compression,
                'start_date': dset.attrs.get('start_date'),
                'end_date': dset.attrs.get('end_date'),
                'row_count': dset.attrs.get('row_count'),
                'updated_at': dset.attrs.get('updated_at'),
                'source': dset.attrs.get('source'),
                'api_version': dset.attrs.get('api_version'),
            }
    
    def get_symbol_summary(self, exchange: str, symbol: str) -> Dict:
        """
        Get summary of all timeframes for a symbol
        
        Returns:
            Dict with info for each available interval
        """
        intervals = self.list_intervals(exchange, symbol)
        
        summary = {
            'symbol': symbol,
            'exchange': exchange,
            'intervals': {},
            'total_size_mb': 0,
            'total_rows': 0,
        }
        
        for interval in intervals:
            info = self.get_data_info(exchange, symbol, interval)
            if info:
                summary['intervals'][interval] = info
                summary['total_size_mb'] += info['size_mb']
                summary['total_rows'] += info['rows']
        
        summary['total_size_mb'] = round(summary['total_size_mb'], 2)
        return summary
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        stats = {
            'file_size_mb': round(self.db_path.stat().st_size / (1024**2), 2),
            'exchanges': {},
            'total_symbols': 0,
            'total_datasets': 0,
            'total_rows': 0,
            'intervals_summary': {},
            'db_version': self.get_metadata('db_version'),
            'created_at': self.get_metadata('created_at'),
            'last_updated': self.get_metadata('last_updated'),
        }
        
        with self.open_file('r') as f:
            data_group = f['/data']
            
            for exchange in data_group.keys():
                exch_group = data_group[exchange]
                symbols = list(exch_group.keys())
                
                datasets_by_interval = {}
                total_datasets = 0
                total_rows = 0
                
                for symbol in symbols:
                    sym_group = exch_group[symbol]
                    for interval in sym_group.keys():
                        dset = sym_group[interval]
                        datasets_by_interval[interval] = datasets_by_interval.get(interval, 0) + 1
                        total_datasets += 1
                        total_rows += dset.shape[0]
                
                stats['exchanges'][exchange] = {
                    'symbols': len(symbols),
                    'datasets': total_datasets,
                    'rows': total_rows,
                    'intervals': datasets_by_interval,
                }
                stats['total_symbols'] += len(symbols)
                stats['total_datasets'] += total_datasets
                stats['total_rows'] += total_rows
                
                # Update global intervals summary
                for interval, count in datasets_by_interval.items():
                    stats['intervals_summary'][interval] = stats['intervals_summary'].get(interval, 0) + count
        
        return stats
    
    # ========================================================================
    # BACKUP & MAINTENANCE
    # ========================================================================
    
    def create_backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create backup of database
        
        Args:
            backup_path: Custom backup path (default: auto-generated)
        
        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = config.BACKUP_DIR / f"kite_data_backup_{timestamp}.h5"
        
        try:
            # Close any open handles
            gc.collect()
            
            # Copy file
            logger.info(f"Creating backup: {backup_path}")
            shutil.copy2(self.db_path, backup_path)
            
            # Verify backup
            with h5py.File(backup_path, 'r') as f:
                f.attrs.get('db_version')  # Simple read check
            
            size_mb = round(backup_path.stat().st_size / (1024**2), 2)
            logger.info(f"✅ Backup created: {backup_path} ({size_mb} MB)")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def optimize_database(self):
        """Optimize database (repack to reduce size)"""
        logger.info("Optimizing database (this may take a while)...")
        
        # Create temporary file
        temp_path = self.db_path.with_suffix('.tmp.h5')
        
        try:
            # Copy to temp file with repacking
            with h5py.File(self.db_path, 'r') as src:
                with h5py.File(temp_path, 'w') as dst:
                    # Recursively copy all data
                    def copy_item(name, obj):
                        if isinstance(obj, h5py.Dataset):
                            # Copy dataset with same compression
                            src.copy(obj, dst, name=name)
                        elif isinstance(obj, h5py.Group):
                            if name != '/':
                                dst.create_group(name)
                    
                    src.visititems(copy_item)
                    
                    # Copy metadata
                    for k, v in src.attrs.items():
                        dst.attrs[k] = v
                    
                    dst.attrs['last_optimized'] = datetime.now().isoformat()
            
            # Get file sizes
            old_size = self.db_path.stat().st_size / (1024**2)
            new_size = temp_path.stat().st_size / (1024**2)
            savings = old_size - new_size
            
            # Replace original with optimized version
            self.db_path.unlink()
            temp_path.rename(self.db_path)
            
            logger.info(f"✅ Database optimized: {old_size:.2f} MB → {new_size:.2f} MB (saved {savings:.2f} MB)")
            
        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _ensure_groups_exist(self, f: h5py.File, path: str):
        """Ensure all parent groups exist for a path"""
        parts = path.strip('/').split('/')
        current = ''
        
        for part in parts[:-1]:  # Exclude last part (dataset name)
            current += '/' + part
            if current not in f:
                f.create_group(current)
    
    def _dataframe_to_array(self, df: pd.DataFrame) -> np.ndarray:
        """Convert pandas DataFrame to structured numpy array"""
        size = len(df)
        arr = create_empty_ohlcv_array(size)
        
        # Map DataFrame columns to array fields
        if 'date' in df.columns:
            arr['timestamp'] = pd.to_datetime(df['date']).astype('int64') // 10**9
        elif 'timestamp' in df.columns:
            arr['timestamp'] = pd.to_datetime(df['timestamp']).astype('int64') // 10**9
        elif isinstance(df.index, pd.DatetimeIndex):
            arr['timestamp'] = df.index.astype('int64') // 10**9
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                arr[col] = df[col].values
        
        return arr
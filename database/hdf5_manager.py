"""
HDF5 Database Manager
"""

import h5py
import hdf5plugin
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Union
from contextlib import contextmanager
import shutil
import gc
import logging

from config import (
    config,
    Interval,
    Segment,
    Exchange,
    CHUNK_SIZES,
    MIN_PRICE,
    MAX_PRICE,
    MIN_VOLUME,
    MAX_VOLUME,
    MIN_DATE,
    MAX_DATE,
    IST,
)
from database.schema import (
    EquityOHLCVSchema,
    InstrumentSchema,
    HDF5Structure,
    DatasetAttributes,
    ValidationRules,
    create_empty_ohlcv_array,
    dict_to_ohlcv_array,
    ohlcv_array_to_dict,
)

logger = logging.getLogger(__name__)


class HDF5Manager:
    """
    HDF5 Database Manager 
    """
    
    def __init__(self, segment: str = 'EQUITY'):
        """
        Initialize HDF5 Manager for a specific segment
        
        Args:
            segment: Market segment (EQUITY, DERIVATIVES, COMMODITY, CURRENCY)
        """
        self.segment = segment.upper()
        self.db_path = config.get_hdf5_path(self.segment)
        self.structure = HDF5Structure()
        
        # Ensure HDF5 directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if needed
        if not self.db_path.exists():
            self._initialize_database()
        
        logger.info(f"HDF5Manager initialized: {self.db_path} (Segment: {self.segment})")
        logger.info(f"Compression: {config.HDF5_COMPRESSION} (level {config.HDF5_COMPRESSION_LEVEL})")
    
    @contextmanager
    def open_file(self, mode: str = 'r'):
        """
        Context manager for safe file operations with optimized settings
        
        Args:
            mode: 'r' (read), 'r+' (read/write), 'a' (append)
        
        Usage:
            with manager.open_file('r+') as f:
                # Use f as h5py.File object
        """
        f = None
        try:
            # Get optimized HDF5 options from config
            hdf5_opts = config.get_hdf5_options()
            
            f = h5py.File(
                self.db_path,
                mode,
                **hdf5_opts,
            )
            yield f
            
        except Exception as e:
            logger.error(f"HDF5 file operation error [{self.segment}]: {e}")
            raise
            
        finally:
            if f is not None:
                f.close()
                
                # Periodic garbage collection for memory efficiency
                if mode in ['a', 'r+'] and config.ENABLE_AGGRESSIVE_GC:
                    gc.collect()
    
    def _get_compression_settings(self, interval: Union[str, Interval], data_size: int = None) -> Dict:
        """
        Get compression settings from config
        
        Returns:
            Dict with hdf5plugin.Blosc filter and chunks ready for create_dataset()
        """
        settings = config.get_hdf5_creation_settings(interval, data_size)
        
        # Create blosc filter directly
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
        """Create new HDF5 database with proper structure"""
        logger.info(f"Creating new database: {self.db_path}")
        
        with self.open_file('w') as f:
            # Create root groups
            for group_path in self.structure.ROOT_GROUPS:
                f.create_group(group_path)
            
            # Create exchange groups (segment-specific)
            exchanges = self._get_segment_exchanges()
            for exchange in exchanges:
                f.create_group(f'/instruments/{exchange}')
                f.create_group(f'/data/{exchange}')
            
            # Set database metadata
            f.attrs['db_version'] = '1.0'
            f.attrs['segment'] = self.segment
            f.attrs['created_at'] = datetime.now().isoformat()
            f.attrs['last_updated'] = datetime.now().isoformat()
            f.attrs['format'] = f'kite_{self.segment.lower()}_v1'
            f.attrs['compression'] = config.HDF5_COMPRESSION
            f.attrs['compression_level'] = config.HDF5_COMPRESSION_LEVEL
            f.attrs['hdf5_cache_size'] = config.HDF5_RDCC_NBYTES
        
        logger.info(f"✅ Database initialized: {self.segment}")
    
    def _get_segment_exchanges(self) -> List[str]:
        """Get list of exchanges for current segment"""
        segment_exchange_map = {
            'EQUITY': [Exchange.NSE.value, Exchange.BSE.value],
            'DERIVATIVES': [Exchange.NFO.value, Exchange.BFO.value],
            'COMMODITY': [Exchange.MCX.value],
            'CURRENCY': [Exchange.CDS.value],
        }
        return segment_exchange_map.get(self.segment, [Exchange.NSE.value])
    
    def set_metadata(self, key: str, value: str):
        """Set database metadata"""
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
            exchange: Exchange name (NSE, BSE, NFO, etc.)
            symbol: Trading symbol
            interval: Timeframe (5minute, 15minute, 60minute, day)
            data: OHLCV data (list of dicts, numpy array, or DataFrame)
            overwrite: If True, replace existing data
            validate: If True, validate data before saving
        
        Returns:
            True if successful
        """
        try:
            # Convert interval to string if Enum
            if isinstance(interval, Interval):
                interval_str = interval.value
            else:
                interval_str = interval
            
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
                logger.warning(f"Empty data array for {symbol} {interval_str}, nothing to save")
                return False
            
            # Validate data if requested
            is_valid, stats = ValidationRules.validate_ohlcv_array(arr)
            if not is_valid:
                logger.error(f"Data validation failed for {symbol} {interval_str}: {stats}")
                logger.error(f"Invalid rows: {stats['invalid_details'][:3]}")
                raise ValueError(f"Invalid OHLCV data: {stats['invalid_rows']} invalid rows")
            
            # Sort by timestamp
            arr = np.sort(arr, order='timestamp')
            
            # Get dataset path
            path = self.structure.get_data_path(exchange, symbol, interval_str)
            
            # Get compression filter and chunk size
            comp_settings = self._get_compression_settings(interval_str, len(arr))
            
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
                        return self._append_ohlcv(f, path, arr, interval_str)
                
                # Create new dataset with blosc compression
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
                    interval=interval_str,
                    start_date=str(arr[0]['timestamp']),
                    end_date=str(arr[-1]['timestamp']),
                    row_count=len(arr),
                )
                for k, v in attrs.items():
                    dset.attrs[k] = v
                
                # Update file-level last_updated
                f.attrs['last_updated'] = datetime.now().isoformat()
            
            logger.info(f"✅ Saved {len(arr)} records to {path} [{config.HDF5_COMPRESSION}]")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving OHLCV data for {symbol} {interval_str}: {e}")
            raise
    
    def _append_ohlcv(
        self,
        f: h5py.File,
        path: str,
        new_data: np.ndarray,
        interval: str,
    ) -> bool:
        """
        Append data to existing dataset (deduplicates by timestamp)
        
        Args:
            f: Open HDF5 file handle
            path: Dataset path
            new_data: New data to append
            interval: Data interval (for compression settings)
        
        Returns:
            True if successful
        """
        try:
            dset = f[path]
            existing_data = dset[:]
            
            # Merge and deduplicate by timestamp
            combined = np.concatenate([existing_data, new_data])
            
            # Get unique timestamps (keeps first occurrence)
            _, unique_indices = np.unique(combined['timestamp'], return_index=True)
            combined = combined[unique_indices]
            combined = np.sort(combined, order='timestamp')
            
            # Backup settings
            attrs_backup = dict(dset.attrs)
            
            # Delete old dataset
            del f[path]
            
            # Get compression settings for recreation
            comp_settings = self._get_compression_settings(interval, len(combined))

            new_dset = f.create_dataset(
                path,
                data=combined,
                dtype=EquityOHLCVSchema.DTYPE,
                **comp_settings,
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
            interval: Timeframe (5minute, 15minute, 60minute, day)
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
                interval_str = interval.value
            else:
                interval_str = interval
            
            path = self.structure.get_data_path(exchange, symbol, interval_str)
            
            with self.open_file('r') as f:
                if path not in f:
                    logger.warning(f"Dataset not found: {path}")
                    return None
                
                dset = f[path]
                
                # Read data efficiently
                if config.ENABLE_MMAP and dset.nbytes > config.MMAP_THRESHOLD_MB * 1024**2:
                    # Use memory mapping for large datasets
                    data = dset[:]
                else:
                    # Direct read for smaller datasets
                    data = dset[:]
                
                # Filter by date range
                if start_date or end_date:
                    mask = np.ones(len(data), dtype=bool)
                    
                    if start_date:
                        start_ts = int(pd.Timestamp(start_date).timestamp())
                        mask &= (data['timestamp'] >= start_ts)
                    
                    if end_date:
                        end_ts = int(pd.Timestamp(end_date).timestamp())
                        mask &= (data['timestamp'] <= end_ts)
                    
                    data = data[mask]
                
                # Select columns if specified
                if columns:
                    data = data[columns]
                
                # Convert to DataFrame if requested
                if as_dataframe:
                    df = pd.DataFrame(data)
                    
                    if 'timestamp' in df.columns:
                        # Convert Unix timestamp to datetime (UTC)
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                        
                        # Timezone handling based on interval
                        if interval_str != 'day':
                            # Intraday: convert to IST
                            df['timestamp'] = df['timestamp'].dt.tz_convert(IST)
                        else:
                            # Daily: remove timezone (date only)
                            df['timestamp'] = df['timestamp'].dt.tz_localize(None)
                        
                        # Set timestamp as index
                        df = df.set_index('timestamp')
                    
                    return df
                else:
                    return data
                    
        except Exception as e:
            logger.error(f"❌ Error retrieving OHLCV data for {symbol} {interval_str}: {e}")
            return None
    
    def delete_ohlcv(
        self,
        exchange: str,
        symbol: str,
        interval: Optional[Union[str, Interval]] = None,
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
                    interval_str = interval.value
                else:
                    interval_str = interval
                
                path = self.structure.get_data_path(exchange, symbol, interval_str)
                
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
    
    def get_data_info(
        self,
        exchange: str,
        symbol: str,
        interval: Union[str, Interval],
    ) -> Dict:
        """Get information about a dataset"""
        if isinstance(interval, Interval):
            interval_str = interval.value
        else:
            interval_str = interval
        
        path = self.structure.get_data_path(exchange, symbol, interval_str)
        
        with self.open_file('r') as f:
            if path not in f:
                return {}
            
            dset = f[path]
            
            # Get compression info
            if hasattr(dset, 'compression'):
                compression_info = dset.compression
            else:
                compression_info = 'unknown'
            
            return {
                'path': path,
                'exchange': exchange,
                'symbol': symbol,
                'interval': interval_str,
                'rows': dset.shape[0],
                'size_mb': round(dset.nbytes / (1024**2), 2),
                'compression': compression_info,
                'chunks': dset.chunks,
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
            'segment': self.segment,
            'exchanges': {},
            'total_symbols': 0,
            'total_datasets': 0,
            'total_rows': 0,
            'intervals_summary': {},
            'db_version': self.get_metadata('db_version'),
            'created_at': self.get_metadata('created_at'),
            'last_updated': self.get_metadata('last_updated'),
            'compression': self.get_metadata('compression'),
            'compression_level': self.get_metadata('compression_level'),
        }
        
        with self.open_file('r') as f:
            data_group = f['/data']
            
            for exchange in data_group.keys():
                exch_group = data_group[exchange]
                symbols = list(exch_group.keys())
                
                datasets_by_interval = {}
                total_datasets = 0
                total_rows = 0
                total_size_mb = 0
                
                for symbol in symbols:
                    sym_group = exch_group[symbol]
                    for interval in sym_group.keys():
                        dset = sym_group[interval]
                        datasets_by_interval[interval] = datasets_by_interval.get(interval, 0) + 1
                        total_datasets += 1
                        total_rows += dset.shape[0]
                        total_size_mb += dset.nbytes / (1024**2)
                
                stats['exchanges'][exchange] = {
                    'symbols': len(symbols),
                    'datasets': total_datasets,
                    'rows': total_rows,
                    'size_mb': round(total_size_mb, 2),
                    'intervals': datasets_by_interval,
                }
                
                stats['total_symbols'] += len(symbols)
                stats['total_datasets'] += total_datasets
                stats['total_rows'] += total_rows
                
                # Update global intervals summary
                for interval, count in datasets_by_interval.items():
                    stats['intervals_summary'][interval] = stats['intervals_summary'].get(interval, 0) + count
        
        return stats
    
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
            backup_path = config.BACKUP_DIR / f"{self.segment}_backup_{timestamp}.h5"
        
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
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def _cleanup_old_backups(self):
        """Remove old backups beyond MAX_BACKUPS limit"""
        if not config.AUTO_BACKUP:
            return
        
        try:
            # Find all backups for this segment
            pattern = f"{self.segment}_backup_*.h5"
            backups = sorted(config.BACKUP_DIR.glob(pattern), key=lambda p: p.stat().st_mtime)
            
            # Remove oldest backups
            while len(backups) > config.MAX_BACKUPS:
                oldest = backups.pop(0)
                oldest.unlink()
                logger.info(f"Removed old backup: {oldest.name}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def optimize_database(self):
        """
        Repack database to reclaim space from deleted datasets.
        
        Use this after:
        - Deleting multiple symbols or intervals
        - Database has grown due to accumulated deletes
        
        Note: 
        - This does NOT improve compression (already optimal with blosc:lz4)
        - Rewrites the entire file (can take time for large databases)
        - HDF5 doesn't free space immediately on delete - this reclaims it
        
        Example:
            manager.delete_ohlcv('NSE', 'OLDSTOCK')  # Space not freed yet
            manager.delete_ohlcv('NSE', 'OLDSTOCK2')
            # ... delete many more
            manager.optimize_database()  # Now space is reclaimed
        """
        logger.info(f"Repacking database to reclaim deleted space: {self.db_path} (this may take a while)...")
        
        # Create temporary file
        temp_path = self.db_path.with_suffix('.tmp.h5')
        
        try:
            # Copy to temp file with repacking
            with self.open_file('r') as src:
                with h5py.File(temp_path, 'w', **config.get_hdf5_options()) as dst:
                    # Copy all groups and datasets
                    def copy_item(name, obj):
                        if isinstance(obj, h5py.Dataset):
                            # Get interval from path for optimal chunking
                            try:
                                _, _, _, interval = name.strip('/').split('/')
                            except:
                                interval = 'day'
                            
                            # Get compression settings
                            comp_settings = self._get_compression_settings(interval, obj.shape[0])

                            new_dset = dst.create_dataset(
                                name,
                                data=obj[:],
                                dtype=obj.dtype,
                                **comp_settings,
                            )
                            
                            # Copy attributes
                            for k, v in obj.attrs.items():
                                new_dset.attrs[k] = v
                                
                        elif isinstance(obj, h5py.Group):
                            if name != '/':
                                dst.create_group(name)
                    
                    src.visititems(copy_item)
                    
                    # Copy file-level metadata
                    for k, v in src.attrs.items():
                        dst.attrs[k] = v
                    
                    dst.attrs['last_optimized'] = datetime.now().isoformat()
            
            # Get file sizes
            old_size = self.db_path.stat().st_size / (1024**2)
            new_size = temp_path.stat().st_size / (1024**2)
            savings = old_size - new_size
            savings_pct = (savings / old_size * 100) if old_size > 0 else 0
            
            # Replace original with optimized version
            self.db_path.unlink()
            temp_path.rename(self.db_path)
            
            logger.info(f"✅ Database optimized: {old_size:.2f} MB → {new_size:.2f} MB")
            logger.info(f"   Saved {savings:.2f} MB ({savings_pct:.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
    
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
        
        # Handle timestamp/date column
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
            if dates.dt.tz is not None:
                dates = dates.dt.tz_convert('UTC')
            arr['timestamp'] = dates.astype('int64') // 10**9
            
        elif 'timestamp' in df.columns:
            dates = pd.to_datetime(df['timestamp'])
            if dates.dt.tz is not None:
                dates = dates.dt.tz_convert('UTC')
            arr['timestamp'] = dates.astype('int64') // 10**9
            
        elif isinstance(df.index, pd.DatetimeIndex):
            dates = df.index
            if dates.tz is not None:
                dates = dates.tz_convert('UTC')
            arr['timestamp'] = dates.astype('int64') // 10**9
        
        # Copy OHLCV columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                arr[col] = df[col].values
        
        return arr


# ========================================================================
# MULTI-SEGMENT MANAGER
# ========================================================================

class MultiSegmentManager:
    """
    Manager for multiple HDF5 databases (one per segment)
    
    Usage:
        manager = MultiSegmentManager()
        
        # Access specific segment
        equity_mgr = manager.get_manager('EQUITY')
        equity_mgr.save_ohlcv(...)
        
        # Or use directly
        manager.save_ohlcv('EQUITY', 'NSE', 'RELIANCE', 'day', data)
    """
    
    def __init__(self):
        self._managers: Dict[str, HDF5Manager] = {}
    
    def get_manager(self, segment: str) -> HDF5Manager:
        """Get or create manager for specific segment"""
        segment = segment.upper()
        
        if segment not in self._managers:
            self._managers[segment] = HDF5Manager(segment)
        
        return self._managers[segment]
    
    def save_ohlcv(self, segment: str, *args, **kwargs) -> bool:
        """Save OHLCV data to specific segment"""
        mgr = self.get_manager(segment)
        return mgr.save_ohlcv(*args, **kwargs)
    
    def get_ohlcv(self, segment: str, *args, **kwargs):
        """Get OHLCV data from specific segment"""
        mgr = self.get_manager(segment)
        return mgr.get_ohlcv(*args, **kwargs)
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all segments"""
        stats = {}
        
        for segment in ['EQUITY', 'DERIVATIVES', 'COMMODITY', 'CURRENCY']:
            db_path = config.get_hdf5_path(segment)
            if db_path.exists():
                mgr = self.get_manager(segment)
                stats[segment] = mgr.get_database_stats()
        
        return stats
    
    def close_all(self):
        """Close all managers and clear cache"""
        self._managers.clear()
        gc.collect()
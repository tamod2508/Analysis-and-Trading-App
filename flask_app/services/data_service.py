"""
Data Service
Business logic for data management and statistics
"""

import logging
from pathlib import Path
from typing import Dict
import os

# Import existing database manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.hdf5_manager import HDF5Manager

logger = logging.getLogger(__name__)


def get_all_database_stats() -> Dict:
    """
    Get statistics for all database segments
    Returns a dict with stats for each segment

    Returns:
        Dict containing statistics for each segment plus summary
    """
    segments = {
        'EQUITY': 'Stock market equities and shares',
        'DERIVATIVES': 'Futures & Options contracts',
    }

    # Get database directory path
    base_dir = Path(__file__).parent.parent.parent
    db_dir = base_dir / 'data' / 'hdf5'

    all_stats = {}

    total_size_mb = 0
    total_symbols = 0
    total_datasets = 0
    all_exchanges = set()
    active_count = 0

    for segment, description in segments.items():
        db_path = db_dir / f'{segment}.h5'

        if db_path.exists():
            try:
                size_mb = os.path.getsize(db_path) / (1024**2)

                # Get HDF5 stats
                mgr = HDF5Manager(segment)
                stats = mgr.get_database_stats()

                is_active = stats['total_symbols'] > 0

                all_stats[segment] = {
                    'description': description,
                    'size_mb': size_mb,
                    'total_symbols': stats['total_symbols'],
                    'total_datasets': stats['total_datasets'],
                    'exchanges': list(stats['exchanges'].keys()),
                    'exchange_details': stats['exchanges'],
                    'is_active': is_active,
                    'status': 'Active' if is_active else 'Empty'
                }

                total_size_mb += size_mb
                total_symbols += stats['total_symbols']
                total_datasets += stats['total_datasets']
                all_exchanges.update(stats['exchanges'].keys())
                if is_active:
                    active_count += 1

            except Exception as e:
                logger.error(f"Error loading stats for {segment}: {e}")
                all_stats[segment] = {
                    'description': description,
                    'size_mb': 0,
                    'total_symbols': 0,
                    'total_datasets': 0,
                    'exchanges': [],
                    'exchange_details': {},
                    'is_active': False,
                    'status': 'Error'
                }
        else:
            all_stats[segment] = {
                'description': description,
                'size_mb': 0,
                'total_symbols': 0,
                'total_datasets': 0,
                'exchanges': [],
                'exchange_details': {},
                'is_active': False,
                'status': 'Not Found'
            }

    # Add summary stats
    all_stats['_summary'] = {
        'total_size_mb': round(total_size_mb, 2),
        'total_symbols': total_symbols,
        'total_datasets': total_datasets,
        'all_exchanges': sorted(list(all_exchanges)),
        'active_count': active_count,
        'total_segments': len(segments)
    }

    return all_stats


def get_segment_stats(segment: str) -> Dict:
    """
    Get statistics for a specific segment

    Args:
        segment: Segment name (EQUITY, DERIVATIVES, etc.)

    Returns:
        Dict containing segment statistics
    """
    try:
        mgr = HDF5Manager(segment)
        stats = mgr.get_database_stats()

        # Get file size
        base_dir = Path(__file__).parent.parent.parent
        db_path = base_dir / 'data' / 'hdf5' / f'{segment}.h5'

        size_mb = 0
        if db_path.exists():
            size_mb = os.path.getsize(db_path) / (1024**2)

        return {
            'segment': segment,
            'size_mb': size_mb,
            'total_symbols': stats['total_symbols'],
            'total_datasets': stats['total_datasets'],
            'exchanges': stats['exchanges']
        }

    except Exception as e:
        logger.error(f"Error getting stats for {segment}: {e}")
        return {
            'segment': segment,
            'size_mb': 0,
            'total_symbols': 0,
            'total_datasets': 0,
            'exchanges': {}
        }

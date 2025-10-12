"""
Dashboard Routes
Main dashboard and home page
"""

from datetime import datetime
from flask import Blueprint, render_template, current_app, jsonify, flash, redirect, url_for, request
from flask_login import login_required
from utils.logger import get_logger

logger = get_logger(__name__, 'flask.log')

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def home():
    """
    Home page / dashboard

    Shows welcome screen for non-authenticated users
    Shows database overview for authenticated users
    """
    from ..services.data_service import get_all_database_stats

    # Get database statistics
    db_stats = get_all_database_stats()

    return render_template('dashboard/home.html', db_stats=db_stats)


# Alias for backwards compatibility
index = home


@dashboard_bp.route('/refresh-data', methods=['POST'])
@login_required
def refresh_data():
    """
    Refresh the analysis backup file with latest data from main database

    This endpoint is called when user clicks "Refresh Data" button.
    It copies the main EQUITY.h5 to EQUITY_backup.h5 so analysis uses latest data.
    """
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from database.hdf5_manager import HDF5Manager

        # Create backup for EQUITY segment
        manager = HDF5Manager('EQUITY')
        backup_path = manager.create_analysis_backup()

        # Get backup file info
        size_mb = round(backup_path.stat().st_size / (1024**2), 2)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"Analysis data refreshed by user: {backup_path} ({size_mb} MB)")
        flash(f'Analysis data refreshed! ({size_mb} MB updated at {timestamp})', 'success')

        # Redirect back to where the user came from (or analysis page by default)
        referrer = request.referrer
        if referrer and '/data/analysis' in referrer:
            return redirect(url_for('data.analysis'))
        return redirect(url_for('dashboard.home'))

    except Exception as e:
        logger.error(f"Error refreshing analysis data: {e}", exc_info=True)
        flash(f'Failed to refresh data: {str(e)}', 'error')

        # Redirect back to where the user came from (or home by default)
        referrer = request.referrer
        if referrer and '/data/analysis' in referrer:
            return redirect(url_for('data.analysis'))
        return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/api/backup-info')
def backup_info():
    """
    Get backup file information (for displaying on dashboard)

    Returns JSON with backup file stats and timestamp
    """
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from config import config

        backup_path = config.HDF5_DIR / 'EQUITY_backup.h5'

        if not backup_path.exists():
            return jsonify({
                'exists': False,
                'message': 'No backup file found. Login to create one.'
            })

        # Get file stats
        stat = backup_path.stat()
        size_mb = round(stat.st_size / (1024**2), 2)
        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'exists': True,
            'path': str(backup_path),
            'size_mb': size_mb,
            'last_updated': modified
        })

    except Exception as e:
        logger.error(f"Error getting backup info: {e}")
        return jsonify({
            'exists': False,
            'error': str(e)
        }), 500

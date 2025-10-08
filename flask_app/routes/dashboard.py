"""
Dashboard Routes
Main dashboard and home page
"""

import logging
from flask import Blueprint, render_template, current_app
from flask_login import login_required

logger = logging.getLogger(__name__)

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

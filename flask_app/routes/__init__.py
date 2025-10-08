"""
Flask Routes
URL routing and view handlers
"""

from .auth import auth_bp
from .dashboard import dashboard_bp
from .data_api import data_api_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'data_api_bp',
]

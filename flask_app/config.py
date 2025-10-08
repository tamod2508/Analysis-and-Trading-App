"""
Flask Configuration
Environment-specific settings for the Flask app
"""

import os
from pathlib import Path
from datetime import timedelta


class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

    # Session configuration
    SESSION_COOKIE_NAME = 'kite_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Don't expire CSRF tokens

    # Application paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    HDF5_DIR = DATA_DIR / 'hdf5'
    EXPORTS_DIR = BASE_DIR / 'exports'
    LOGS_DIR = BASE_DIR / 'logs'

    # Kite API settings (from existing config)
    KITE_API_KEY = os.getenv('KITE_API_KEY')
    KITE_API_SECRET = os.getenv('KITE_API_SECRET')
    KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN')

    # OAuth redirect URI
    KITE_REDIRECT_URI = os.getenv('KITE_REDIRECT_URI', 'http://127.0.0.1:5000/auth/callback')

    # Flask-Login
    LOGIN_VIEW = 'auth.login'
    LOGIN_MESSAGE = 'Please log in to access this page.'
    LOGIN_MESSAGE_CATEGORY = 'info'

    # Database settings
    SEGMENTS = ['EQUITY', 'DERIVATIVES']


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # Development-specific settings
    ENV = 'development'

    # Session
    SESSION_COOKIE_SECURE = False  # Allow HTTP in dev

    # Templates auto-reload
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Production-specific settings
    ENV = 'production'

    # Enforce HTTPS
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

    # Stronger secret key - will be validated at app startup
    # (Don't validate here during import to avoid errors in dev)


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True

    # Test-specific settings
    ENV = 'testing'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Session
    SESSION_COOKIE_SECURE = False


# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Get configuration object by name

    Args:
        config_name: 'development', 'production', or 'testing'
        If None, uses FLASK_ENV environment variable

    Returns:
        Config class
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    return config_by_name.get(config_name, DevelopmentConfig)

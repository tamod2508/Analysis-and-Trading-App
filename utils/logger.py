"""
Logging utility for Kite Data Manager
Provides module-specific loggers with separate log files
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Log file configurations
LOG_FILES = {
    'fetcher': 'fetcher.log',
    'flask': 'flask.log',
    'file_manager': 'file_manager.log',
    'authentication': 'authentication.log',
    'database': 'database.log',
    'api': 'api.log',
    'hdf5': 'hdf5.log',
    'validator': 'validator.log',
    'instruments': 'instruments.log',
    'fundamentals': 'fundamentals.log',
}

# Formatter configurations
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
SIMPLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# File handler settings
MAX_BYTES = 100 * 1024 * 1024  # 100MB
BACKUP_COUNT = 10


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    console: bool = True,
    file_logging: bool = True
) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (typically module name)
        log_file: Log file name (without path). If None, uses module-based mapping
        level: Logging level (default: DEBUG)
        console: Enable console output (default: True)
        file_logging: Enable file output (default: True)

    Returns:
        Configured logger instance

    Examples:
        # In api/kite_client.py
        logger = get_logger(__name__, 'fetcher.log')

        # In flask_app/__init__.py
        logger = get_logger(__name__, 'flask.log')

        # Auto-mapped based on module name
        logger = get_logger('api.kite_client')  # -> fetcher.log
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Determine log file based on module name if not specified
    if log_file is None:
        log_file = _get_log_file_for_module(name)

    # Create formatters
    detailed_formatter = logging.Formatter(DETAILED_FORMAT, DATE_FORMAT)
    simple_formatter = logging.Formatter(SIMPLE_FORMAT, DATE_FORMAT)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    # File handler
    if file_logging and log_file:
        file_path = LOGS_DIR / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    # Error file handler (all errors go to error.log)
    error_file = LOGS_DIR / 'error.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
        encoding='utf8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)

    return logger


def _get_log_file_for_module(module_name: str) -> str:
    """
    Map module name to appropriate log file

    Args:
        module_name: Python module name (e.g., 'api.kite_client')

    Returns:
        Log file name
    """
    # Module to log file mapping
    module_mapping = {
        'api.kite_client': 'fetcher.log',
        'api.auth_handler': 'authentication.log',
        'flask_app': 'flask.log',
        'flask_app.routes': 'flask.log',
        'flask_app.services.auth_service': 'authentication.log',
        'flask_app.services.data_fetcher': 'fetcher.log',
        'flask_app.services.data_service': 'database.log',
        'flask_app.services.fundamentals_service': 'fundamentals.log',
        'database.hdf5_manager': 'file_manager.log',
        'database.validators': 'validator.log',
        'database.data_validator': 'validator.log',
        'database.instruments_db': 'instruments.log',
        'database.fundamentals_manager': 'fundamentals.log',
        'database': 'database.log',
    }

    # Check exact match
    if module_name in module_mapping:
        return module_mapping[module_name]

    # Check prefix match
    for prefix, log_file in module_mapping.items():
        if module_name.startswith(prefix):
            return log_file

    # Default to app.log
    return 'app.log'


def setup_root_logger(level: int = logging.INFO):
    """
    Setup root logger with basic configuration
    Should be called once at application startup

    Args:
        level: Root logging level
    """
    root_logger = logging.getLogger()

    # Avoid duplicate configuration
    if root_logger.handlers:
        return

    root_logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(SIMPLE_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Root file handler
    file_path = LOGS_DIR / 'app.log'
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf8'
    )
    file_handler.setLevel(logging.DEBUG)
    detailed_formatter = logging.Formatter(DETAILED_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_file = LOGS_DIR / 'error.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=5,
        encoding='utf8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)


def cleanup_old_logs(days: int = 30):
    """
    Clean up log files older than specified days

    Args:
        days: Number of days to retain logs
    """
    import time

    cutoff_time = time.time() - (days * 24 * 60 * 60)

    for log_file in LOGS_DIR.glob('*.log*'):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                print(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                print(f"Failed to delete {log_file.name}: {e}")


# Quick access functions for common loggers
def get_fetcher_logger() -> logging.Logger:
    """Get logger for data fetching operations"""
    return get_logger('fetcher', 'fetcher.log')


def get_flask_logger() -> logging.Logger:
    """Get logger for Flask application"""
    return get_logger('flask', 'flask.log')


def get_file_manager_logger() -> logging.Logger:
    """Get logger for file management operations"""
    return get_logger('file_manager', 'file_manager.log')


def get_auth_logger() -> logging.Logger:
    """Get logger for authentication operations"""
    return get_logger('authentication', 'authentication.log')


def get_database_logger() -> logging.Logger:
    """Get logger for database operations"""
    return get_logger('database', 'database.log')


def get_validator_logger() -> logging.Logger:
    """Get logger for validation operations"""
    return get_logger('validator', 'validator.log')


def get_instruments_logger() -> logging.Logger:
    """Get logger for instruments database"""
    return get_logger('instruments', 'instruments.log')


def get_fundamentals_logger() -> logging.Logger:
    """Get logger for fundamentals data"""
    return get_logger('fundamentals', 'fundamentals.log')


if __name__ == '__main__':
    # Test logging setup
    setup_root_logger()

    # Test various loggers
    fetcher_log = get_fetcher_logger()
    fetcher_log.info("Fetcher logger test")

    flask_log = get_flask_logger()
    flask_log.info("Flask logger test")

    db_log = get_database_logger()
    db_log.info("Database logger test")

    print(f"\nLog files created in: {LOGS_DIR}")
    print("Available log files:")
    for name, filename in LOG_FILES.items():
        print(f"  - {filename}")

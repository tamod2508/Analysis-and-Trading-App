"""
Flask Services
Business logic and data access layer for the Flask app
"""

from .auth_service import (
    AuthService,
    User,
    load_user,
    save_user,
    get_auth_service
)
from .data_service import (
    get_all_database_stats,
    get_segment_stats
)

# data_fetcher will be created in Phase 2
# from .data_fetcher import (
#     DataFetcherService,
#     create_data_fetcher
# )

__all__ = [
    # Auth
    'AuthService',
    'User',
    'load_user',
    'save_user',
    'get_auth_service',
    # Data service
    'get_all_database_stats',
    'get_segment_stats',
    # Data fetcher (Phase 2)
    # 'DataFetcherService',
    # 'create_data_fetcher',
]

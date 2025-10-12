"""
Flask Authentication Service
Handles Kite Connect OAuth authentication and session management
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from flask_login import UserMixin
from kiteconnect import KiteConnect
from utils.logger import get_logger

logger = get_logger(__name__, 'authentication.log')


class User(UserMixin):
    """
    Simple user model for Flask-Login

    In this app, users are identified by their Kite user_id
    """

    def __init__(self, user_id: str, user_name: str = None, email: str = None, expiry_string: str = None):
        """
        Initialize user

        Args:
            user_id: Kite user ID
            user_name: User's name (optional)
            email: User's email (optional)
            expiry_string: Token expiry display string (optional)
        """
        self.id = user_id  # Flask-Login requires 'id' attribute
        self.user_id = user_id
        self.user_name = user_name
        self.email = email
        self.expiry_string = expiry_string

    def get_id(self) -> str:
        """Get user ID (required by Flask-Login)"""
        return str(self.user_id)

    def __repr__(self) -> str:
        return f"<User {self.user_id}>"


class AuthService:
    """
    Authentication service for Kite Connect OAuth

    Handles:
    - Login URL generation
    - OAuth callback processing
    - Session management
    - User profile retrieval
    """

    def __init__(self, api_key: str, api_secret: str, redirect_uri: str):
        """
        Initialize auth service

        Args:
            api_key: Kite API key
            api_secret: Kite API secret
            redirect_uri: OAuth callback URL
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.kite = KiteConnect(api_key=api_key)

    def get_login_url(self) -> str:
        """
        Generate Kite Connect login URL

        Returns:
            OAuth login URL to redirect user to
        """
        login_url = self.kite.login_url()
        logger.info(f"Generated login URL")
        return login_url

    def generate_session(self, request_token: str) -> Dict:
        """
        Generate access token from request token

        Args:
            request_token: OAuth request token from callback

        Returns:
            Dict with session data (access_token, user details)

        Raises:
            Exception: If token generation fails
        """
        try:
            # Generate session
            session_data = self.kite.generate_session(
                request_token=request_token,
                api_secret=self.api_secret
            )

            logger.info(f"Session generated for user: {session_data.get('user_id')}")
            return session_data

        except Exception as e:
            logger.error(f"Error generating session: {e}")
            raise

    def get_profile(self, access_token: str) -> Dict:
        """
        Get user profile using access token

        Args:
            access_token: Kite access token

        Returns:
            Dict with user profile data

        Raises:
            Exception: If profile fetch fails
        """
        try:
            # Set access token
            self.kite.set_access_token(access_token)

            # Get profile
            profile = self.kite.profile()
            logger.info(f"Fetched profile for user: {profile.get('user_id')}")
            return profile

        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            raise

    def create_user(self, session_data: Dict, profile: Dict = None) -> User:
        """
        Create User object from session data

        Args:
            session_data: Session data from generate_session()
            profile: Optional profile data

        Returns:
            User object
        """
        user_id = session_data.get('user_id')
        user_name = session_data.get('user_name')
        email = session_data.get('email')

        # Use profile data if available
        if profile:
            user_name = profile.get('user_name', user_name)
            email = profile.get('email', email)

        return User(
            user_id=user_id,
            user_name=user_name,
            email=email
        )


# Global user storage (in production, use a proper database)
# For this app, we only need to track the current user per session
_users = {}


def load_user(user_id: str) -> Optional[User]:
    """
    Load user by ID (required by Flask-Login)

    Also checks for existing authentication from .env file

    Args:
        user_id: User ID

    Returns:
        User object or None if not found
    """
    # Check in-memory cache first
    if user_id in _users:
        return _users[user_id]

    # Try to load from existing .env token
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from api.auth_handler import verify_authentication, get_user_profile, get_token_expiry_info

        if verify_authentication():
            profile = get_user_profile()
            if profile and str(profile.get('user_id')) == str(user_id):
                # Get token expiry info
                expiry_string = None
                expiry_info = get_token_expiry_info()
                if expiry_info:
                    expiry_string = expiry_info.get('expiry_string')

                # Create and cache user
                user = User(
                    user_id=profile['user_id'],
                    user_name=profile.get('user_name'),
                    email=profile.get('email'),
                    expiry_string=expiry_string
                )
                _users[user_id] = user
                return user
    except Exception as e:
        logger.error(f"Error loading user from token: {e}")

    return None


def save_user(user: User, access_token: str = None):
    """
    Save user to storage and optionally update .env with access token

    Args:
        user: User object
        access_token: Access token to save to .env (optional)
    """
    _users[user.id] = user

    # Save access token to .env file if provided
    if access_token:
        try:
            env_path = Path(__file__).parent.parent.parent / '.env'

            if env_path.exists():
                # Read existing .env content
                with open(env_path, 'r') as f:
                    lines = f.readlines()

                # Update or add KITE_ACCESS_TOKEN
                token_updated = False
                timestamp_updated = False
                new_lines = []

                for line in lines:
                    if line.startswith('KITE_ACCESS_TOKEN='):
                        new_lines.append(f'KITE_ACCESS_TOKEN={access_token}\n')
                        token_updated = True
                    elif line.startswith('KITE_ACCESS_TOKEN_CREATED_AT='):
                        new_lines.append(f'KITE_ACCESS_TOKEN_CREATED_AT={datetime.now().isoformat()}\n')
                        timestamp_updated = True
                    else:
                        new_lines.append(line)

                # Add if not found
                if not token_updated:
                    new_lines.append(f'KITE_ACCESS_TOKEN={access_token}\n')
                if not timestamp_updated:
                    new_lines.append(f'KITE_ACCESS_TOKEN_CREATED_AT={datetime.now().isoformat()}\n')

                # Write back to .env
                with open(env_path, 'w') as f:
                    f.writelines(new_lines)

                logger.info(f"Access token saved to .env file for user {user.id}")
            else:
                logger.warning(f".env file not found at {env_path}")

        except Exception as e:
            logger.error(f"Error saving access token to .env: {e}")


def get_auth_service(api_key: str, api_secret: str, redirect_uri: str) -> AuthService:
    """
    Create and return AuthService instance

    Args:
        api_key: Kite API key
        api_secret: Kite API secret
        redirect_uri: OAuth callback URL

    Returns:
        AuthService instance
    """
    return AuthService(
        api_key=api_key,
        api_secret=api_secret,
        redirect_uri=redirect_uri
    )

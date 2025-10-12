"""
Kite Connect Authentication Handler
Manages OAuth2 login flow and token persistence
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

from config import config
from config.constants import IST
from utils.logger import get_logger

logger = get_logger(__name__, 'authentication.log')


class AuthHandler:
    """
    Handles Kite Connect authentication and token management
    
    OAuth2 Flow:
    1. Generate login URL
    2. User logs in via browser
    3. Kite redirects with request_token
    4. Exchange request_token for access_token
    5. Save access_token to .env
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize auth handler
        """
        self.api_key = api_key or config.KITE_API_KEY
        self.api_secret = api_secret or config.KITE_API_SECRET

        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be configured in .env file")

        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = None
        self.token_created_at = None  # Timestamp when token was created

        logger.info("AuthHandler initialized")
    
    def get_login_url(self) -> str:
        """
        Generate Kite login URL
        
        Returns:
            URL to redirect user for login
        """
        login_url = self.kite.login_url()
        logger.info(f"Login URL generated")
        return login_url
    
    def generate_session(self, request_token: str) -> Dict:
        """
        Exchange request token for access token
        
        Args:
            request_token: Token received after user login
        
        Returns:
            Session data with access_token
        """
        try:
            # Generate session
            session_data = self.kite.generate_session(
                request_token,
                api_secret=self.api_secret
            )
            
            self.access_token = session_data['access_token']
            self.kite.set_access_token(self.access_token)
            
            logger.info(f"Session generated successfully")
            logger.info(f"User ID: {session_data['user_id']}")
            logger.info(f"User Name: {session_data['user_name']}")
            
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to generate session: {e}")
            raise
    
    def save_access_token(self, access_token: str = None) -> bool:
        """
        Save access token and creation timestamp to .env file

        Args:
            access_token: Token to save (default: current session token)

        Returns:
            True if successful
        """
        token_to_save = access_token or self.access_token

        if not token_to_save:
            logger.error("No access token to save")
            return False

        try:
            env_path = config.BASE_DIR / '.env'

            # Read existing .env content
            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []

            # Get current IST timestamp
            created_at = datetime.now(IST)
            timestamp_str = created_at.isoformat()

            # Update or add KITE_ACCESS_TOKEN
            token_line = f"KITE_ACCESS_TOKEN={token_to_save}\n"
            timestamp_line = f"KITE_ACCESS_TOKEN_CREATED_AT={timestamp_str}\n"

            token_found = False
            timestamp_found = False

            for i, line in enumerate(lines):
                if line.startswith('KITE_ACCESS_TOKEN=') and not line.startswith('KITE_ACCESS_TOKEN_CREATED_AT='):
                    lines[i] = token_line
                    token_found = True
                elif line.startswith('KITE_ACCESS_TOKEN_CREATED_AT='):
                    lines[i] = timestamp_line
                    timestamp_found = True

            if not token_found:
                lines.append(token_line)
            if not timestamp_found:
                lines.append(timestamp_line)

            # Write back to .env
            with open(env_path, 'w') as f:
                f.writelines(lines)

            # Store timestamp in instance
            self.token_created_at = created_at

            logger.info(f"Access token and timestamp saved to {env_path}")
            logger.info(f"Token created at: {timestamp_str}")
            return True

        except Exception as e:
            logger.error(f"Failed to save access token: {e}")
            return False
    
    def load_access_token(self) -> Optional[str]:
        """
        Load access token and creation timestamp from .env file

        Returns:
            Access token or None
        """
        # Read directly from .env file to get latest token and timestamp
        # (config.KITE_ACCESS_TOKEN is only loaded once at app startup)
        env_path = config.BASE_DIR / '.env'
        token = None
        timestamp_str = None

        if env_path.exists():
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('KITE_ACCESS_TOKEN=') and not line.startswith('KITE_ACCESS_TOKEN_CREATED_AT='):
                            token = line.split('=', 1)[1].strip()
                        elif line.startswith('KITE_ACCESS_TOKEN_CREATED_AT='):
                            timestamp_str = line.split('=', 1)[1].strip()
            except Exception as e:
                logger.error(f"Failed to read .env file: {e}")

        if token:
            self.access_token = token
            self.kite.set_access_token(token)

            # Parse timestamp if available
            if timestamp_str:
                try:
                    self.token_created_at = datetime.fromisoformat(timestamp_str)
                    logger.info(f"Access token loaded from .env file (created: {timestamp_str})")
                except ValueError as e:
                    logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
                    self.token_created_at = None
                    logger.info("Access token loaded from .env file (no valid timestamp)")
            else:
                self.token_created_at = None
                logger.info("Access token loaded from .env file (no timestamp)")

            return token

        logger.warning("No access token found in .env file")
        return None

    def get_token_expiry_time(self) -> Optional[datetime]:
        """
        Calculate when the access token will expire (6 AM IST next day)

        Returns:
            Datetime of expiry in IST, or None if no timestamp available
        """
        if not self.token_created_at:
            return None

        # Ensure created_at is in IST
        created_at_ist = self.token_created_at.astimezone(IST)

        # Calculate 6 AM IST of the next day
        # If created after 6 AM today, expires at 6 AM tomorrow
        # If created before 6 AM today, still expires at 6 AM tomorrow (edge case)
        next_day = created_at_ist.date() + timedelta(days=1)
        expiry_time = IST.localize(datetime.combine(next_day, datetime.min.time().replace(hour=6)))

        return expiry_time

    def is_token_expired_by_time(self) -> bool:
        """
        Check if token is expired based on timestamp (without API call)

        Returns:
            True if definitely expired, False if might still be valid
        """
        expiry_time = self.get_token_expiry_time()

        if not expiry_time:
            # No timestamp available, can't determine from time alone
            return False

        # Get current IST time
        now_ist = datetime.now(IST)

        # Token is expired if current time is past expiry time
        is_expired = now_ist >= expiry_time

        if is_expired:
            logger.info(f"Token expired by timestamp: now={now_ist}, expiry={expiry_time}")
        else:
            time_remaining = expiry_time - now_ist
            logger.debug(f"Token valid by timestamp: {time_remaining} remaining until {expiry_time}")

        return is_expired

    def get_time_until_expiry(self) -> Optional[timedelta]:
        """
        Get time remaining until token expiry

        Returns:
            Timedelta until expiry, or None if no timestamp available
        """
        expiry_time = self.get_token_expiry_time()

        if not expiry_time:
            return None

        now_ist = datetime.now(IST)
        time_remaining = expiry_time - now_ist

        # Return timedelta (can be negative if expired)
        return time_remaining

    def verify_token(self) -> bool:
        """
        Verify if current access token is valid
        Uses hybrid approach: timestamp-based fast path + API verification

        Returns:
            True if token is valid
        """
        if not self.access_token:
            logger.warning("No access token to verify")
            return False

        # FAST PATH: Check if token is definitely expired by timestamp
        # This avoids unnecessary API calls for expired tokens
        if self.is_token_expired_by_time():
            logger.info("Token verification skipped - definitely expired by timestamp (fast path)")
            return False

        # VERIFICATION PATH: Token might be valid by timestamp, verify with API
        # This catches early invalidations (e.g., login to Kite Web, manual logout)
        try:
            # Try to get profile (lightweight API call)
            profile = self.kite.profile()
            logger.info(f"Token verified via API - User: {profile['user_name']} ({profile['email']})")

            # Log expiry info if timestamp available
            expiry_time = self.get_token_expiry_time()
            if expiry_time:
                time_remaining = self.get_time_until_expiry()
                logger.info(f"Token valid until: {expiry_time.strftime('%Y-%m-%d %H:%M:%S %Z')} ({time_remaining})")

            return True

        except Exception as e:
            logger.error(f"Token verification failed via API: {e}")
            return False
    
    def complete_login_flow(self, request_token: str) -> bool:
        """
        Complete full login flow: generate session + save token
        
        Args:
            request_token: Token from Kite redirect
        
        Returns:
            True if successful
        """
        try:
            # Generate session
            session_data = self.generate_session(request_token)
            
            # Save token
            save_success = self.save_access_token(session_data['access_token'])
            
            if save_success:
                logger.info("✅ Login flow completed successfully")
                return True
            else:
                logger.error("Failed to save access token")
                return False
                
        except Exception as e:
            logger.error(f"Login flow failed: {e}")
            return False
    
    def get_profile(self) -> Optional[Dict]:
        """
        Get user profile (requires valid token)
        
        Returns:
            Profile dict or None
        """
        if not self.access_token:
            logger.warning("No access token available")
            return None
        
        try:
            profile = self.kite.profile()
            return profile
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return None
    
    def logout(self) -> bool:
        """
        Invalidate current session
        
        Returns:
            True if successful
        """
        try:
            if self.access_token:
                # Note: Kite doesn't provide a logout endpoint
                # We just clear local token
                self.access_token = None
                logger.info("Session cleared locally")
            
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        if not self.access_token:
            return False
        return self.verify_token()


# Convenience functions
def get_login_url() -> str:
    """Quick function to get login URL"""
    handler = AuthHandler()
    return handler.get_login_url()


def login_with_request_token(request_token: str) -> bool:
    """
    Quick function to complete login
    
    Usage:
        # After user logs in and you get request_token from redirect URL
        success = login_with_request_token(request_token)
    """
    handler = AuthHandler()
    return handler.complete_login_flow(request_token)


def verify_authentication() -> bool:
    """
    Quick function to verify if authenticated
    
    Returns:
        True if valid token exists
    """
    handler = AuthHandler()
    handler.load_access_token()
    return handler.verify_token()


def get_user_profile() -> Optional[Dict]:
    """
    Get current user profile

    Returns:
        Profile dict or None
    """
    handler = AuthHandler()
    handler.load_access_token()
    return handler.get_profile()


def get_token_expiry_info() -> Optional[Dict]:
    """
    Get token expiry information for UI display

    Returns:
        Dict with expiry_time, time_remaining, expiry_string, or None
    """
    handler = AuthHandler()
    handler.load_access_token()

    expiry_time = handler.get_token_expiry_time()
    if not expiry_time:
        return None

    time_remaining = handler.get_time_until_expiry()

    # Format expiry string for display
    if time_remaining:
        total_seconds = int(time_remaining.total_seconds())

        if total_seconds <= 0:
            expiry_string = "Expired"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = total_seconds // 60
            expiry_string = f"{minutes}m remaining"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            expiry_string = f"{hours}h {minutes}m remaining"
        else:
            expiry_string = "Valid until 6:00 AM IST"
    else:
        expiry_string = "Valid until 6:00 AM IST"

    return {
        'expiry_time': expiry_time,
        'time_remaining': time_remaining,
        'expiry_string': expiry_string,
        'is_expired': time_remaining.total_seconds() <= 0 if time_remaining else False,
    }


# Interactive login helper
def interactive_login():
    """
    Interactive CLI login helper
    
    Usage:
        from api.auth_handler import interactive_login
        interactive_login()
    """
    print("\n" + "="*70)
    print("KITE CONNECT - INTERACTIVE LOGIN")
    print("="*70)
    
    handler = AuthHandler()
    
    # Step 1: Get login URL
    login_url = handler.get_login_url()
    print(f"\n1. Open this URL in your browser:\n   {login_url}\n")
    
    # Step 2: Get request token
    print("2. After logging in, Kite will redirect to:")
    print(f"   {config.REDIRECT_URL}?request_token=XXXXX&action=login&status=success\n")
    
    request_token = input("3. Paste the 'request_token' from the URL here: ").strip()
    
    if not request_token:
        print("\n❌ No request token provided")
        return False
    
    # Step 3: Complete login
    print("\n4. Generating session...")
    success = handler.complete_login_flow(request_token)
    
    if success:
        profile = handler.get_profile()
        print("\n" + "="*70)
        print("✅ LOGIN SUCCESSFUL!")
        print("="*70)
        if profile:
            print(f"User: {profile['user_name']}")
            print(f"Email: {profile['email']}")
            print(f"User ID: {profile['user_id']}")
        print("\nAccess token saved to .env file")
        print("You can now use the API client to fetch data")
        print("="*70 + "\n")
        return True
    else:
        print("\n❌ Login failed")
        return False


if __name__ == "__main__":
    # Run interactive login if executed directly
    interactive_login()
"""
Kite Connect Authentication Handler
Manages OAuth2 login flow and token persistence
"""

import os
import logging
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path
from kiteconnect import KiteConnect

from config.settings import config

logger = logging.getLogger(__name__)


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
        
        Args:
            api_key: Kite API key (default: from config)
            api_secret: Kite API secret (default: from config)
        """
        self.api_key = api_key or config.KITE_API_KEY
        self.api_secret = api_secret or config.KITE_API_SECRET
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be configured in .env file")
        
        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = None
        
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
        Save access token to .env file
        
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
            
            # Update or add KITE_ACCESS_TOKEN
            token_line = f"KITE_ACCESS_TOKEN={token_to_save}\n"
            token_found = False
            
            for i, line in enumerate(lines):
                if line.startswith('KITE_ACCESS_TOKEN='):
                    lines[i] = token_line
                    token_found = True
                    break
            
            if not token_found:
                lines.append(token_line)
            
            # Write back to .env
            with open(env_path, 'w') as f:
                f.writelines(lines)
            
            logger.info(f"Access token saved to {env_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save access token: {e}")
            return False
    
    def load_access_token(self) -> Optional[str]:
        """
        Load access token from .env file
        
        Returns:
            Access token or None
        """
        token = config.KITE_ACCESS_TOKEN
        
        if token:
            self.access_token = token
            self.kite.set_access_token(token)
            logger.info("Access token loaded from config")
            return token
        
        logger.warning("No access token found in config")
        return None
    
    def verify_token(self) -> bool:
        """
        Verify if current access token is valid
        
        Returns:
            True if token is valid
        """
        if not self.access_token:
            logger.warning("No access token to verify")
            return False
        
        try:
            # Try to get profile (lightweight API call)
            profile = self.kite.profile()
            logger.info(f"Token verified - User: {profile['user_name']} ({profile['email']})")
            return True
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
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
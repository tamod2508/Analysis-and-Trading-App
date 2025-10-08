"""
Test persistent authentication across app restarts
"""

import os
from pathlib import Path
from api.auth_handler import AuthHandler, verify_authentication, get_user_profile


def test_load_token_from_env():
    """Test that access token is loaded from .env file"""
    handler = AuthHandler()
    token = handler.load_access_token()

    assert token is not None, "No token loaded from .env"
    assert len(token) > 0, "Token is empty"
    print(f"✓ Token loaded: {token[:10]}...")


def test_verify_authentication():
    """Test that verify_authentication() reads from .env"""
    is_authenticated = verify_authentication()

    assert is_authenticated, "Authentication failed"
    print(f"✓ Authentication verified")


def test_get_user_profile():
    """Test that user profile can be fetched"""
    profile = get_user_profile()

    assert profile is not None, "No profile returned"
    assert 'user_id' in profile, "Profile missing user_id"
    assert 'user_name' in profile, "Profile missing user_name"

    print(f"✓ Profile loaded: {profile.get('user_name')} ({profile.get('email')})")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING PERSISTENT AUTHENTICATION")
    print("="*70 + "\n")

    try:
        test_load_token_from_env()
        test_verify_authentication()
        test_get_user_profile()

        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - Persistent auth is working!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        exit(1)

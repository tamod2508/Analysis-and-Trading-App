"""
Authentication Component for Kite Connect
Handles login/logout UI and session management
"""

import streamlit as st
from typing import Optional, Dict
import logging

from api.auth_handler import AuthHandler, verify_authentication, get_user_profile, get_token_expiry_info

logger = logging.getLogger(__name__)


def initialize_auth_state():
    """Initialize authentication state in session"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'auth_checked' not in st.session_state:
        st.session_state.auth_checked = False


def check_existing_auth():
    """Check if user already has valid token in .env"""
    if not st.session_state.auth_checked:
        try:
            is_authenticated = verify_authentication()
            if is_authenticated:
                profile = get_user_profile()
                st.session_state.authenticated = True
                st.session_state.user_profile = profile
                logger.info("Existing authentication verified")
            st.session_state.auth_checked = True
        except Exception as e:
            logger.error(f"Auth check failed: {e}")
            st.session_state.auth_checked = True


def handle_login():
    """Handle login flow via text input for request token"""
    st.markdown("### Login to Kite Connect")

    handler = AuthHandler()
    login_url = handler.get_login_url()

    # Check if request_token is in URL query params (from redirect)
    query_params = st.query_params
    url_request_token = query_params.get("request_token", None)

    if url_request_token and not st.session_state.authenticated:
        # Auto-login with token from URL
        with st.spinner("Auto-authenticating from redirect..."):
            try:
                # Generate session
                session_data = handler.generate_session(url_request_token)

                # Save token
                save_success = handler.save_access_token(session_data['access_token'])

                if save_success:
                    # Get profile
                    profile = handler.get_profile()

                    # Update session state
                    st.session_state.authenticated = True
                    st.session_state.user_profile = profile

                    # Clear URL params
                    st.query_params.clear()

                    st.success("Login successful!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to save access token")
                    st.query_params.clear()

            except Exception as e:
                st.error(f"Auto-login failed: {str(e)}")
                logger.error(f"Auto-login error: {e}")
                st.query_params.clear()
        return

    # Show login instructions
    st.markdown("""
    <div class='info-box'>
        <p><strong>Step 1:</strong> Click the button below to open Kite login page</p>
        <p><strong>Step 2:</strong> Login with your Zerodha credentials</p>
        <p><strong>Step 3:</strong> You'll be automatically logged in on redirect!</p>
        <p style='color: #94A3B8; font-size: 0.9rem; margin-top: 0.5rem;'>
            <em>Note: If auto-login doesn't work, you can manually paste the request_token below</em>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Login URL button
    st.markdown(f"""
    <div style='margin: 1rem 0;'>
        <a href='{login_url}' target='_blank' style='
            display: inline-block;
            background-color: #D4AF37;
            color: #0A0E27;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
        '>
            Open Kite Login Page
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Request token input
    with st.form("login_form"):
        request_token = st.text_input(
            "Request Token",
            placeholder="Paste request_token from URL here",
            help="After logging in, Kite will redirect to a URL containing request_token=XXXXX"
        )

        submit = st.form_submit_button("Complete Login", use_container_width=True)

        if submit:
            if not request_token:
                st.error("Please enter the request token")
                return

            with st.spinner("Authenticating..."):
                try:
                    # Generate session
                    session_data = handler.generate_session(request_token.strip())

                    # Save token
                    save_success = handler.save_access_token(session_data['access_token'])

                    if save_success:
                        # Get profile
                        profile = handler.get_profile()

                        # Update session state
                        st.session_state.authenticated = True
                        st.session_state.user_profile = profile

                        st.success("Login successful!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to save access token")

                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
                    logger.error(f"Login error: {e}")


def show_user_profile(profile: Dict):
    """Display user profile card"""
    # Get token expiry info
    expiry_info = get_token_expiry_info()

    expiry_html = ""
    if expiry_info:
        expiry_string = expiry_info['expiry_string']
        is_expired = expiry_info['is_expired']

        if is_expired:
            expiry_color = '#EF4444'  # Red
        else:
            time_remaining = expiry_info['time_remaining']
            if time_remaining and time_remaining.total_seconds() < 3600:
                expiry_color = '#F59E0B'  # Orange/yellow for < 1 hour
            else:
                expiry_color = '#10B981'  # Green

        expiry_html = f"<div class='profile-detail' style='color: {expiry_color};'><strong>Token Status:</strong> {expiry_string}</div>"

    st.markdown(f"""
    <div class='profile-card fade-in'>
        <h3>Authenticated</h3>
        <div class='profile-detail'><strong>Name:</strong> {profile.get('user_name', 'N/A')}</div>
        <div class='profile-detail'><strong>Email:</strong> {profile.get('email', 'N/A')}</div>
        <div class='profile-detail'><strong>User ID:</strong> {profile.get('user_id', 'N/A')}</div>
        <div class='profile-detail'><strong>Broker:</strong> {profile.get('broker', 'Zerodha')}</div>
        {expiry_html}
    </div>
    """, unsafe_allow_html=True)


def handle_logout():
    """Handle logout"""
    if st.button("Logout", use_container_width=True):
        try:
            handler = AuthHandler()
            handler.load_access_token()
            handler.logout()

            # Clear session state
            st.session_state.authenticated = False
            st.session_state.user_profile = None
            st.session_state.auth_checked = False

            st.success("Logged out successfully")
            st.rerun()

        except Exception as e:
            st.error(f"Logout failed: {str(e)}")
            logger.error(f"Logout error: {e}")


def show_auth_component():
    """
    Main authentication component
    Shows login form if not authenticated, profile if authenticated
    """
    # Initialize state
    initialize_auth_state()

    # Check for existing authentication
    check_existing_auth()

    # Show appropriate UI
    if st.session_state.authenticated and st.session_state.user_profile:
        # Show profile and logout
        show_user_profile(st.session_state.user_profile)
        handle_logout()
    else:
        # Show login form
        handle_login()


def show_auth_status_badge():
    """
    Show compact authentication status badge (for sidebar)
    """
    initialize_auth_state()
    check_existing_auth()

    if st.session_state.authenticated and st.session_state.user_profile:
        profile = st.session_state.user_profile

        # Get token expiry info
        expiry_info = get_token_expiry_info()
        expiry_text = ""

        if expiry_info:
            expiry_string = expiry_info['expiry_string']
            expiry_text = f"<div style='font-size: 0.75rem; color: #94A3B8; margin-top: 0.3rem;'>{expiry_string}</div>"

        st.markdown(f"""
        <div class='auth-badge authenticated'>
            <span class='status-indicator status-online'></span>
            {profile.get('user_name', 'User')}
            {expiry_text}
        </div>
        """, unsafe_allow_html=True)
        return True
    else:
        st.markdown("""
        <div class='auth-badge not-authenticated'>
            <span class='status-indicator status-offline'></span>
            Not Authenticated
        </div>
        """, unsafe_allow_html=True)
        return False


def require_authentication():
    """
    Decorator/helper to require authentication for a page
    Returns True if authenticated, shows login form otherwise
    """
    initialize_auth_state()
    check_existing_auth()

    if not st.session_state.authenticated:
        st.warning("Please login to access this feature")
        show_auth_component()
        return False

    return True

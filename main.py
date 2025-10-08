"""
Kite Connect Historical Data Manager
Main Streamlit Application Entry Point
"""

import streamlit as st
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import UI components
from ui.styles import apply_custom_css
from ui.components import show_auth_component, show_auth_status_badge

# Configure Streamlit page
st.set_page_config(
    page_title="Kite Data Manager",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Kite Connect Historical Data Manager - Built with Streamlit"
    }
)

# Apply custom styling
apply_custom_css()


def show_header():
    """Display auth status and logout button in Streamlit header bar"""
    from ui.components import initialize_auth_state, check_existing_auth

    # Initialize auth
    initialize_auth_state()
    check_existing_auth()

    # Get auth status
    is_authenticated = st.session_state.get('authenticated', False)
    user_profile = st.session_state.get('user_profile', None)

    # Create HTML for header injection with auth badge and logout button side-by-side
    if is_authenticated and user_profile:
        user_name = user_profile.get('user_name', 'User')
        auth_html = f"""
        <div id="custom-header-auth" style="
            position: fixed;
            top: 0.75rem;
            right: 5rem;
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        ">
            <div style="
                display: flex;
                align-items: center;
                background-color: rgba(16, 185, 129, 0.2);
                color: #10B981;
                border: 1px solid #10B981;
                padding: 0.4rem 0.8rem;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
            ">
                <span style="
                    display: inline-block;
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background-color: #10B981;
                    box-shadow: 0 0 8px #10B981;
                    margin-right: 8px;
                "></span>
                {user_name}
            </div>
            <button onclick="logoutUser()" style="
                background-color: #D4AF37;
                color: #0A0E27;
                border: none;
                border-radius: 6px;
                padding: 0.4rem 1rem;
                font-weight: 600;
                font-size: 0.85rem;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(212, 175, 55, 0.2);
            " onmouseover="this.style.backgroundColor='#C9A961'" onmouseout="this.style.backgroundColor='#D4AF37'">
                Logout
            </button>
        </div>
        <script>
        function logoutUser() {{
            window.location.href = window.location.origin + '?logout=true';
        }}
        </script>
        """
    else:
        auth_html = f"""
        <div id="custom-header-auth" style="
            position: fixed;
            top: 0.75rem;
            right: 5rem;
            z-index: 999999;
            display: flex;
            align-items: center;
        ">
            <div style="
                display: flex;
                align-items: center;
                background-color: rgba(220, 38, 38, 0.2);
                color: #DC2626;
                border: 1px solid #DC2626;
                padding: 0.4rem 0.8rem;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
            ">
                <span style="
                    display: inline-block;
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background-color: #DC2626;
                    margin-right: 8px;
                "></span>
                Not Authenticated
            </div>
        </div>
        """

    st.markdown(auth_html, unsafe_allow_html=True)

    # Handle logout via query parameter
    if is_authenticated:
        query_params = st.query_params
        if query_params.get("logout") == "true":
            from api.auth_handler import AuthHandler
            try:
                handler = AuthHandler()
                handler.load_access_token()
                handler.logout()

                # Clear session state
                st.session_state.authenticated = False
                st.session_state.user_profile = None
                st.session_state.auth_checked = False

                # Clear query params
                st.query_params.clear()
                st.success("Logged out successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Logout failed: {str(e)}")
                logging.error(f"Logout error: {e}")


def show_welcome_page():
    """Display welcome/home page"""

    # Check authentication status for conditional rendering
    from ui.components import require_authentication

    # If not authenticated, show login in center
    if not st.session_state.get('authenticated', False):
        # Center the login card
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("<div style='margin-top: 5rem;'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h1 style='border: none; margin: 0;'>Kite Data Manager</h1>
                <p class='secondary-text' style='font-size: 1.1rem; margin-top: 0.5rem;'>
                    Historical Data Platform for Zerodha Kite Connect
                </p>
            </div>
            """, unsafe_allow_html=True)

            show_auth_component()
    else:
        # Show dashboard for authenticated users
        st.markdown("""
        <div class='fade-in' style='text-align: center; margin: 3rem 0;'>
            <h1 style='border: none;'>Welcome to Kite Data Manager</h1>
            <p class='secondary-text' style='font-size: 1.2rem; margin-top: 1rem;'>
                Select a page from the sidebar to get started
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Quick stats cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Database", "8.0 MB", delta="3 symbols")

        with col2:
            st.metric("Exchanges", "2", delta="NSE, BSE")

        with col3:
            st.metric("Status", "Ready", delta=None)

        with col4:
            st.metric("Pages", "Coming Soon", delta=None)


def show_sidebar():
    """Configure sidebar with navigation"""

    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; margin: 1rem 0 2rem 0;'>
            <h2 style='margin: 0; color: #D4AF37;'>Kite Manager</h2>
            <p style='margin: 0.5rem 0 0 0; color: #94A3B8; font-size: 0.85rem;'>
                Historical Data Platform
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation
        st.markdown("### Navigation")

        if st.button("Home", use_container_width=True):
            st.rerun()

        st.markdown("**Coming Soon:**")
        st.markdown("- Data Management")
        st.markdown("- Analysis Dashboard")
        st.markdown("- Database Explorer")

        st.markdown("---")

        # Quick stats (only show if authenticated)
        if st.session_state.get('authenticated', False):
            st.markdown("### Quick Stats")
            st.metric("Symbols", "3")
            st.metric("Database", "8.0 MB")

        # Help section (moved up to avoid overlap with logout)
        st.markdown("---")
        with st.expander("Help"):
            st.markdown("""
            **Getting Started:**

            1. Login with Kite credentials
            2. Navigate using sidebar
            3. More features coming soon!

            **Support:** Report issues on GitHub
            """)


def main():
    """Main application logic"""

    # Show custom header with auth status
    show_header()

    # Show sidebar
    show_sidebar()

    # Show main content
    show_welcome_page()


if __name__ == "__main__":
    main()

"""
Kite Connect Historical Data Manager
Main Streamlit Application Entry Point
"""

import streamlit as st
import streamlit.components.v1 as components
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


def get_all_database_stats():
    """
    Get statistics for all database segments
    Returns a dict with stats for each segment
    """
    from database.hdf5_manager import HDF5Manager
    from pathlib import Path
    import os

    segments = {
        'EQUITY': 'Stock market equities and shares',
        'DERIVATIVES': 'Futures & Options contracts',
        'COMMODITY': 'Commodity futures (MCX)',
        'CURRENCY': 'Currency derivatives (CDS)'
    }

    db_dir = Path('/Users/atm/Desktop/kite_app/data/hdf5')
    all_stats = {}

    total_size_mb = 0
    total_symbols = 0
    total_datasets = 0
    all_exchanges = set()
    active_count = 0

    for segment, description in segments.items():
        db_path = db_dir / f'{segment}.h5'

        if db_path.exists():
            try:
                size_mb = os.path.getsize(db_path) / (1024**2)
                mgr = HDF5Manager(segment)
                stats = mgr.get_database_stats()

                is_active = stats['total_symbols'] > 0

                all_stats[segment] = {
                    'description': description,
                    'size_mb': size_mb,
                    'total_symbols': stats['total_symbols'],
                    'total_datasets': stats['total_datasets'],
                    'exchanges': list(stats['exchanges'].keys()),
                    'exchange_details': stats['exchanges'],
                    'is_active': is_active,
                    'status': 'Active' if is_active else 'Empty'
                }

                total_size_mb += size_mb
                total_symbols += stats['total_symbols']
                total_datasets += stats['total_datasets']
                all_exchanges.update(stats['exchanges'].keys())
                if is_active:
                    active_count += 1

            except Exception as e:
                logging.error(f"Error loading stats for {segment}: {e}")
                all_stats[segment] = {
                    'description': description,
                    'size_mb': 0,
                    'total_symbols': 0,
                    'total_datasets': 0,
                    'exchanges': [],
                    'exchange_details': {},
                    'is_active': False,
                    'status': 'Error'
                }
        else:
            all_stats[segment] = {
                'description': description,
                'size_mb': 0,
                'total_symbols': 0,
                'total_datasets': 0,
                'exchanges': [],
                'exchange_details': {},
                'is_active': False,
                'status': 'Not Found'
            }

    # Add summary stats
    all_stats['_summary'] = {
        'total_size_mb': round(total_size_mb, 2),
        'total_symbols': total_symbols,
        'total_datasets': total_datasets,
        'all_exchanges': sorted(list(all_exchanges)),
        'active_count': active_count,
        'total_segments': len(segments)
    }

    return all_stats


def show_header():
    """Display top navigation bar with links, auth status, and logout"""
    from ui.components import initialize_auth_state, check_existing_auth
    from api.auth_handler import get_token_expiry_info

    # Initialize auth
    initialize_auth_state()
    check_existing_auth()

    # Get auth status
    is_authenticated = st.session_state.get('authenticated', False)
    user_profile = st.session_state.get('user_profile', None)

    # Build auth section HTML
    if is_authenticated and user_profile:
        user_name = user_profile.get('user_name', 'User')

        # Get token expiry info
        expiry_info = get_token_expiry_info()
        expiry_text = ""
        if expiry_info:
            expiry_string = expiry_info['expiry_string']
            expiry_text = f" • {expiry_string}"

        auth_section = f"""
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="
                    display: flex;
                    align-items: center;
                    background-color: rgba(16, 185, 129, 0.2);
                    color: #10B981;
                    border: 1px solid #10B981;
                    padding: 0.4rem 0.8rem;
                    border-radius: 16px;
                    font-size: 0.85rem;
                    font-weight: 600;
                ">
                    <span style="
                        display: inline-block;
                        width: 6px;
                        height: 6px;
                        border-radius: 50%;
                        background-color: #10B981;
                        box-shadow: 0 0 6px #10B981;
                        margin-right: 6px;
                    "></span>
                    {user_name}{expiry_text}
                </div>
                <button onclick="logoutUser()" style="
                    background-color: #E6B865;
                    color: #0A0B14;
                    border: none;
                    border-radius: 6px;
                    padding: 0.4rem 1rem;
                    font-weight: 600;
                    font-size: 0.85rem;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(230, 184, 101, 0.2);
                " onmouseover="this.style.backgroundColor='#D4A655'" onmouseout="this.style.backgroundColor='#E6B865'">
                    Logout
                </button>
            </div>
        """
    else:
        auth_section = f"""
            <div style="
                display: flex;
                align-items: center;
                background-color: rgba(239, 68, 68, 0.2);
                color: #EF4444;
                border: 1px solid #EF4444;
                padding: 0.4rem 0.8rem;
                border-radius: 16px;
                font-size: 0.85rem;
                font-weight: 600;
            ">
                <span style="
                    display: inline-block;
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background-color: #EF4444;
                    margin-right: 6px;
                "></span>
                Not Authenticated
            </div>
        """

    # Complete navbar HTML
    navbar_html = f"""
    <div id="custom-navbar" style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        width: 100vw;
        height: 70px;
        background-color: #1A1D2E;
        border-bottom: 2px solid #E6B865;
        z-index: 999999;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    ">
        <!-- Left section: Brand + Navigation -->
        <div style="
            position: absolute;
            left: 2rem;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            align-items: center;
            gap: 2.5rem;
        ">
            <!-- Brand/Logo -->
            <h2 style="margin: 0; color: #E6B865; font-size: 1.3rem; font-weight: 700; border: none; padding: 0;">
                Kite Data Manager
            </h2>

            <!-- Navigation Links -->
            <div style="display: flex; align-items: center; gap: 2rem; white-space: nowrap;">
                <a href="/" style="
                    color: #E5E7EB;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 0.2s ease;
                " onmouseover="this.style.color='#E6B865'" onmouseout="this.style.color='#E5E7EB'">
                    Home
                </a>

                <div class="nav-dropdown" style="position: relative;">
                    <span style="color: #E5E7EB; font-weight: 600; font-size: 0.95rem; cursor: pointer; transition: color 0.2s ease;"
                          onmouseover="this.style.color='#E6B865'" onmouseout="this.style.color='#E5E7EB'">
                        Data ▾
                    </span>
                    <div class="dropdown-content" style="
                        display: none;
                        position: absolute;
                        top: calc(100% + 0.5rem);
                        left: 0;
                        background-color: #1E2139;
                        border: 1px solid #E6B865;
                        border-radius: 4px;
                        min-width: 150px;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
                        z-index: 1000;
                    ">
                        <a href="/data/equity" style="display: block; padding: 0.75rem 1rem; color: #E5E7EB; text-decoration: none; transition: background-color 0.2s;"
                           onmouseover="this.style.backgroundColor='rgba(230, 184, 101, 0.2)'" onmouseout="this.style.backgroundColor='transparent'">Equity</a>
                        <a href="/data/futures" style="display: block; padding: 0.75rem 1rem; color: #E5E7EB; text-decoration: none; transition: background-color 0.2s;"
                           onmouseover="this.style.backgroundColor='rgba(230, 184, 101, 0.2)'" onmouseout="this.style.backgroundColor='transparent'">Futures</a>
                        <a href="/data/options" style="display: block; padding: 0.75rem 1rem; color: #E5E7EB; text-decoration: none; transition: background-color 0.2s;"
                           onmouseover="this.style.backgroundColor='rgba(230, 184, 101, 0.2)'" onmouseout="this.style.backgroundColor='transparent'">Options</a>
                    </div>
                </div>

                <div class="nav-dropdown" style="position: relative;">
                    <span style="color: #E5E7EB; font-weight: 600; font-size: 0.95rem; cursor: pointer; transition: color 0.2s ease;"
                          onmouseover="this.style.color='#E6B865'" onmouseout="this.style.color='#E5E7EB'">
                        Analytics ▾
                    </span>
                    <div class="dropdown-content" style="
                        display: none;
                        position: absolute;
                        top: calc(100% + 0.5rem);
                        left: 0;
                        background-color: #1E2139;
                        border: 1px solid #E6B865;
                        border-radius: 4px;
                        min-width: 150px;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
                        z-index: 1000;
                    ">
                        <a href="/analytics/equity" style="display: block; padding: 0.75rem 1rem; color: #E5E7EB; text-decoration: none; transition: background-color 0.2s;"
                           onmouseover="this.style.backgroundColor='rgba(230, 184, 101, 0.2)'" onmouseout="this.style.backgroundColor='transparent'">Equity</a>
                        <a href="/analytics/futures" style="display: block; padding: 0.75rem 1rem; color: #E5E7EB; text-decoration: none; transition: background-color 0.2s;"
                           onmouseover="this.style.backgroundColor='rgba(230, 184, 101, 0.2)'" onmouseout="this.style.backgroundColor='transparent'">Futures</a>
                        <a href="/analytics/options" style="display: block; padding: 0.75rem 1rem; color: #E5E7EB; text-decoration: none; transition: background-color 0.2s;"
                           onmouseover="this.style.backgroundColor='rgba(230, 184, 101, 0.2)'" onmouseout="this.style.backgroundColor='transparent'">Options</a>
                    </div>
                </div>

                <a href="/financials" style="
                    color: #E5E7EB;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 0.2s ease;
                " onmouseover="this.style.color='#E6B865'" onmouseout="this.style.color='#E5E7EB'">
                    Financials
                </a>

                <a href="/backtesting" style="
                    color: #E5E7EB;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 0.2s ease;
                " onmouseover="this.style.color='#E6B865'" onmouseout="this.style.color='#E5E7EB'">
                    Backtesting
                </a>

                <a href="/ai-models" style="
                    color: #E5E7EB;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 0.2s ease;
                " onmouseover="this.style.color='#E6B865'" onmouseout="this.style.color='#E5E7EB'">
                    AI Models
                </a>
            </div>
        </div>

        <!-- Auth Section -->
        <div style="
            position: absolute;
            right: 2rem;
            top: 50%;
            transform: translateY(-50%);
        ">
            {auth_section}
        </div>
    </div>

    <script>
    function logoutUser() {{
        window.location.href = window.location.origin + '?logout=true';
    }}

    // Dropdown functionality
    document.addEventListener('DOMContentLoaded', function() {{
        const dropdowns = document.querySelectorAll('.nav-dropdown');
        dropdowns.forEach(dropdown => {{
            dropdown.addEventListener('mouseenter', function() {{
                const content = this.querySelector('.dropdown-content');
                if (content) {{
                    content.style.display = 'block';
                }}
            }});
            dropdown.addEventListener('mouseleave', function() {{
                const content = this.querySelector('.dropdown-content');
                if (content) {{
                    content.style.display = 'none';
                }}
            }});
        }});
    }});
    </script>

    <!-- Spacer to push content below navbar -->
    <div style="height: 90px;"></div>
    """

    # Use components.html to inject navbar (avoids container clipping)
    components.html(f"""
        {navbar_html}
        <script>
        // Move navbar to parent window's body and set up event listeners
        (function() {{
            const navbar = document.getElementById('custom-navbar');
            if (navbar && window.parent && window.parent.document) {{
                // Remove any existing navbar in parent
                const existingNav = window.parent.document.getElementById('custom-navbar');
                if (existingNav) {{
                    existingNav.remove();
                }}
                // Append to parent document body
                window.parent.document.body.insertBefore(navbar, window.parent.document.body.firstChild);

                // Set up dropdown functionality in parent context with delay
                const dropdowns = window.parent.document.querySelectorAll('.nav-dropdown');
                dropdowns.forEach(dropdown => {{
                    let hideTimeout;

                    dropdown.addEventListener('mouseenter', function() {{
                        // Clear any pending hide timeout
                        if (hideTimeout) {{
                            clearTimeout(hideTimeout);
                        }}
                        const content = this.querySelector('.dropdown-content');
                        if (content) {{
                            content.style.display = 'block';
                        }}
                    }});

                    dropdown.addEventListener('mouseleave', function() {{
                        const content = this.querySelector('.dropdown-content');
                        if (content) {{
                            // Add delay before hiding
                            hideTimeout = setTimeout(() => {{
                                content.style.display = 'none';
                            }}, 200); // 200ms delay
                        }}
                    }});
                }});
            }}
        }})();
        </script>
    """, height=0)

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
                More features coming soon!
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Get real database statistics
        db_stats = get_all_database_stats()
        summary = db_stats['_summary']

        # Find active databases names
        active_names = [name.capitalize() for name, data in db_stats.items()
                       if name != '_summary' and data['is_active']]
        active_label = ', '.join(active_names) if active_names else 'None'

        # Combined database statistics cards with real data
        st.markdown(f"""
        <div style='display: flex; gap: 2rem; justify-content: center; margin-top: 3rem; flex-wrap: wrap;'>
            <div style='background-color: #1A1D2E; border: 1px solid #2D3142; border-radius: 8px; padding: 1.5rem; min-width: 200px; text-align: center;'>
                <div style='color: #9CA3AF; font-size: 0.875rem; margin-bottom: 0.5rem;'>Total Database Size</div>
                <div style='color: #E5E7EB; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>{summary['total_size_mb']} MB</div>
                <div style='color: #10B981; font-size: 0.875rem;'>All Segments</div>
            </div>
            <div style='background-color: #1A1D2E; border: 1px solid #2D3142; border-radius: 8px; padding: 1.5rem; min-width: 200px; text-align: center;'>
                <div style='color: #9CA3AF; font-size: 0.875rem; margin-bottom: 0.5rem;'>Active Databases</div>
                <div style='color: #E5E7EB; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>{summary['active_count']} / {summary['total_segments']}</div>
                <div style='color: #10B981; font-size: 0.875rem;'>{active_label}</div>
            </div>
            <div style='background-color: #1A1D2E; border: 1px solid #2D3142; border-radius: 8px; padding: 1.5rem; min-width: 200px; text-align: center;'>
                <div style='color: #9CA3AF; font-size: 0.875rem; margin-bottom: 0.5rem;'>Total Instruments</div>
                <div style='color: #E5E7EB; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>{summary['total_symbols']}</div>
                <div style='color: #10B981; font-size: 0.875rem;'>Across All Segments</div>
            </div>
            <div style='background-color: #1A1D2E; border: 1px solid #2D3142; border-radius: 8px; padding: 1.5rem; min-width: 200px; text-align: center;'>
                <div style='color: #9CA3AF; font-size: 0.875rem; margin-bottom: 0.5rem;'>Total Exchanges</div>
                <div style='color: #E5E7EB; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;'>{len(summary['all_exchanges'])}</div>
                <div style='color: #10B981; font-size: 0.875rem;'>{', '.join(summary['all_exchanges'])}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Database segments overview - Dashboard Layout
        st.markdown("<div style='margin-top: 4rem;'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #E6B865; border-bottom: 2px solid #E6B865; padding-bottom: 1rem; margin-bottom: 2rem;'>Database Overview</h2>", unsafe_allow_html=True)

        # Initialize selected database in session state
        if 'selected_database' not in st.session_state:
            # Default to first active database
            for seg in ['EQUITY', 'DERIVATIVES', 'COMMODITY', 'CURRENCY']:
                if db_stats.get(seg, {}).get('is_active', False):
                    st.session_state.selected_database = seg
                    break
            else:
                st.session_state.selected_database = 'EQUITY'

        # Create two columns for master-detail layout
        col_left, col_right = st.columns([1, 2.5])

        with col_left:
            # Left sidebar - Database list with clickable cards
            # Header
            st.markdown("""
<div style='color: #E6B865; font-size: 1rem; font-weight: 600; margin-bottom: 1rem; border-bottom: 1px solid #2D3142; padding-bottom: 0.5rem;'>DATABASES</div>
            """, unsafe_allow_html=True)

            # Create clickable cards for each database
            for segment_name in ['EQUITY', 'DERIVATIVES', 'COMMODITY', 'CURRENCY']:
                data = db_stats.get(segment_name, {})
                is_active = data.get('is_active', False)
                size_mb = data.get('size_mb', 0)
                status = data.get('status', 'Empty')

                # Check if this is the selected database
                is_selected = st.session_state.selected_database == segment_name

                # Different styling for selected, active, and inactive
                if is_selected:
                    bg_color = '#2D3848'
                    border_color = '#E6B865'
                    indicator = '●'
                    size_color = '#E5E7EB'
                    status_color = '#E6B865'
                    opacity = '1'
                elif is_active:
                    bg_color = '#252839'
                    border_color = '#10B981'
                    indicator = '●'
                    size_color = '#9CA3AF'
                    status_color = '#10B981'
                    opacity = '1'
                else:
                    bg_color = 'rgba(37, 40, 57, 0.5)'
                    border_color = '#2D3142'
                    indicator = '○'
                    size_color = '#6B7280'
                    status_color = '#6B7280'
                    opacity = '0.7'

                # Create clickable button
                if st.button(
                    f"{indicator} {segment_name.capitalize()}",
                    key=f"db_btn_{segment_name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_database = segment_name
                    st.rerun()

                # Display card with size and status
                st.markdown(f"""
<div style='padding: 0.75rem 1rem; margin-bottom: 1.5rem; margin-top: -1rem; background-color: {bg_color}; border-left: 3px solid {border_color}; border-radius: 0 0 4px 4px; opacity: {opacity};'>
    <div style='color: {size_color}; font-size: 0.875rem; font-weight: 500;'>{size_mb:.2f} MB</div>
    <div style='color: {status_color}; font-size: 0.75rem;'>{status}</div>
</div>
                """, unsafe_allow_html=True)

        with col_right:
            # Right panel - Display selected database details

            # Get the selected database from session state
            selected_segment = st.session_state.selected_database

            # Check if the selected database has data
            if db_stats.get(selected_segment, {}).get('is_active', False):
                seg_data = db_stats[selected_segment]

                # Prepare display data
                title = f"{selected_segment} DATABASE"
                description = seg_data['description']
                size_mb = seg_data['size_mb']
                total_symbols = seg_data['total_symbols']
                total_datasets = seg_data['total_datasets']
                exchanges = ', '.join(seg_data['exchanges']) if seg_data['exchanges'] else 'None'

                # Determine label for instruments based on segment
                if selected_segment == 'EQUITY':
                    instrument_label = 'No. of Stocks'
                elif selected_segment == 'DERIVATIVES':
                    instrument_label = 'No. of Contracts'
                elif selected_segment == 'COMMODITY':
                    instrument_label = 'No. of Commodities'
                else:
                    instrument_label = 'No. of Instruments'

                st.markdown(f"""
<div style='background-color: #1A1D2E; border: 1px solid #2D3142; border-radius: 8px; padding: 2rem; min-height: 500px;'>
    <div style='margin-bottom: 2rem;'>
        <div style='display: flex; align-items: center; justify-content: space-between;'>
            <h3 style='color: #E6B865; margin: 0; border: none;'>{title}</h3>
            <span style='background-color: rgba(16, 185, 129, 0.2); color: #10B981; padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.875rem; font-weight: 600;'>● Active</span>
        </div>
        <div style='color: #9CA3AF; font-size: 0.875rem; margin-top: 0.5rem;'>{description}</div>
    </div>
    <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; margin-bottom: 2rem;'>
        <div style='background-color: #252839; border: 1px solid #2D3142; border-radius: 6px; padding: 1.25rem;'>
            <div style='color: #9CA3AF; font-size: 0.75rem; margin-bottom: 0.5rem; text-transform: uppercase;'>Database Size</div>
            <div style='color: #E5E7EB; font-size: 1.75rem; font-weight: 700;'>{size_mb:.2f} MB</div>
        </div>
        <div style='background-color: #252839; border: 1px solid #2D3142; border-radius: 6px; padding: 1.25rem;'>
            <div style='color: #9CA3AF; font-size: 0.75rem; margin-bottom: 0.5rem; text-transform: uppercase;'>{instrument_label}</div>
            <div style='color: #E5E7EB; font-size: 1.75rem; font-weight: 700;'>{total_symbols}</div>
        </div>
        <div style='background-color: #252839; border: 1px solid #2D3142; border-radius: 6px; padding: 1.25rem;'>
            <div style='color: #9CA3AF; font-size: 0.75rem; margin-bottom: 0.5rem; text-transform: uppercase;'>Exchanges</div>
            <div style='color: #E5E7EB; font-size: 1.25rem; font-weight: 600; margin-top: 0.5rem;'>{exchanges}</div>
        </div>
        <div style='background-color: #252839; border: 1px solid #2D3142; border-radius: 6px; padding: 1.25rem;'>
            <div style='color: #9CA3AF; font-size: 0.75rem; margin-bottom: 0.5rem; text-transform: uppercase;'>Total Datasets</div>
            <div style='color: #E5E7EB; font-size: 1.75rem; font-weight: 700;'>{total_datasets}</div>
        </div>
    </div>
    <div style='background-color: rgba(230, 184, 101, 0.1); border: 1px solid rgba(230, 184, 101, 0.3); border-radius: 6px; padding: 1rem; margin-top: 2rem;'>
        <div style='color: #E6B865; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>ℹ Database Information</div>
        <div style='color: #9CA3AF; font-size: 0.875rem; line-height: 1.6;'>
            This database contains historical OHLCV data for {description.lower()}. Data is stored in HDF5 format with multiple timeframe intervals (minute, 5min, 15min, 60min, day).
        </div>
    </div>
</div>
                """, unsafe_allow_html=True)
            else:
                # Selected database has no data - show placeholder with database info
                seg_data = db_stats.get(selected_segment, {})
                title = f"{selected_segment} DATABASE"
                description = seg_data.get('description', 'No description available')

                st.markdown(f"""
<div style='background-color: #1A1D2E; border: 1px solid #2D3142; border-radius: 8px; padding: 2rem; min-height: 500px;'>
    <div style='margin-bottom: 2rem;'>
        <div style='display: flex; align-items: center; justify-content: space-between;'>
            <h3 style='color: #E6B865; margin: 0; border: none;'>{title}</h3>
            <span style='background-color: rgba(239, 68, 68, 0.2); color: #EF4444; padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.875rem; font-weight: 600;'>○ Empty</span>
        </div>
        <div style='color: #9CA3AF; font-size: 0.875rem; margin-top: 0.5rem;'>{description}</div>
    </div>
    <div style='background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 2rem; text-align: center;'>
        <div style='color: #9CA3AF; font-size: 1.25rem; margin-bottom: 1rem;'>No Data Available</div>
        <div style='color: #6B7280; font-size: 0.875rem;'>Import data to populate this database</div>
    </div>
</div>
                """, unsafe_allow_html=True)


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

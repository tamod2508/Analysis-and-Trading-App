"""
Custom CSS styling for Kite Data Manager
Navy/Gold professional theme
"""

# Color palette
COLORS = {
    'primary': '#0A0E27',        # Deep navy - almost black
    'accent': '#D4AF37',         # Muted gold
    'accent_alt': '#C9A961',     # Champagne gold
    'secondary': '#1A1F3A',      # Charcoal navy
    'text_primary': '#F8FAFC',   # Off-white
    'text_secondary': '#94A3B8', # Cool gray
    'success': '#10B981',        # Emerald green
    'alert': '#DC2626',          # Deep red
    'borders': '#334155',        # Subtle slate
}


def get_custom_css() -> str:
    """
    Generate custom CSS for Streamlit app
    Returns CSS string to inject via st.markdown()
    """
    return f"""
    <style>
    /* ==================== Global Styles ==================== */

    /* Main background */
    .stApp {{
        background-color: {COLORS['primary']};
        color: {COLORS['text_primary']};
    }}

    /* Header/Toolbar (Deploy button area) */
    [data-testid="stHeader"] {{
        background-color: {COLORS['secondary']};
        border-bottom: 1px solid {COLORS['borders']};
    }}

    header[data-testid="stHeader"] {{
        background-color: {COLORS['secondary']} !important;
    }}

    /* Toolbar buttons */
    [data-testid="stToolbar"] {{
        background-color: {COLORS['secondary']};
        color: {COLORS['text_primary']};
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['secondary']};
        border-right: 1px solid {COLORS['borders']};
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
        color: {COLORS['text_primary']};
    }}

    /* ==================== Typography ==================== */

    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS['text_primary']} !important;
        font-weight: 600;
    }}

    h1 {{
        border-bottom: 2px solid {COLORS['accent']};
        padding-bottom: 0.7rem;
        margin-bottom: 1rem;
    }}

    p, span, div {{
        color: {COLORS['text_primary']};
    }}

    .stMarkdown {{
        color: {COLORS['text_primary']};
    }}

    /* Secondary text */
    .secondary-text {{
        color: {COLORS['text_secondary']};
        font-size: 0.9rem;
    }}

    /* ==================== Buttons ==================== */

    /* Primary button (gold) */
    .stButton > button {{
        background-color: {COLORS['accent']};
        color: {COLORS['primary']};
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(212, 175, 55, 0.2);
    }}

    .stButton > button:hover {{
        background-color: {COLORS['accent_alt']};
        box-shadow: 0 4px 8px rgba(212, 175, 55, 0.3);
        transform: translateY(-1px);
    }}

    .stButton > button:active {{
        transform: translateY(0);
    }}

    /* Success button */
    .success-button > button {{
        background-color: {COLORS['success']} !important;
        color: white !important;
    }}

    .success-button > button:hover {{
        background-color: #059669 !important;
    }}

    /* Danger button */
    .danger-button > button {{
        background-color: {COLORS['alert']} !important;
        color: white !important;
    }}

    .danger-button > button:hover {{
        background-color: #B91C1C !important;
    }}

    /* ==================== Cards & Containers ==================== */

    /* Card container */
    .card {{
        background-color: {COLORS['secondary']};
        border: 1px solid {COLORS['borders']};
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }}

    .card-title {{
        color: {COLORS['accent']};
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border-bottom: 1px solid {COLORS['borders']};
        padding-bottom: 0.5rem;
    }}

    /* Info box */
    .info-box {{
        background-color: {COLORS['secondary']};
        border-left: 4px solid {COLORS['accent']};
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }}

    /* Success box */
    .success-box {{
        background-color: rgba(16, 185, 129, 0.1);
        border-left: 4px solid {COLORS['success']};
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
        color: {COLORS['success']};
    }}

    /* Alert box */
    .alert-box {{
        background-color: rgba(220, 38, 38, 0.1);
        border-left: 4px solid {COLORS['alert']};
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
        color: {COLORS['alert']};
    }}

    /* ==================== Inputs & Forms ==================== */

    /* Text inputs */
    .stTextInput > div > div > input {{
        background-color: {COLORS['secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['borders']};
        border-radius: 6px;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: {COLORS['accent']};
        box-shadow: 0 0 0 1px {COLORS['accent']};
    }}

    /* Select boxes */
    .stSelectbox > div > div > div {{
        background-color: {COLORS['secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['borders']};
    }}

    /* Date inputs */
    .stDateInput > div > div > input {{
        background-color: {COLORS['secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['borders']};
    }}

    /* ==================== Tables ==================== */

    .stDataFrame {{
        background-color: {COLORS['secondary']};
    }}

    .stDataFrame thead tr th {{
        background-color: {COLORS['accent']} !important;
        color: {COLORS['primary']} !important;
        font-weight: 600;
    }}

    .stDataFrame tbody tr:hover {{
        background-color: rgba(212, 175, 55, 0.1);
    }}

    /* ==================== Status Indicators ==================== */

    .status-indicator {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }}

    .status-online {{
        background-color: {COLORS['success']};
        box-shadow: 0 0 8px {COLORS['success']};
    }}

    .status-offline {{
        background-color: {COLORS['alert']};
    }}

    /* ==================== Metrics ==================== */

    [data-testid="stMetricValue"] {{
        color: {COLORS['text_primary']};
    }}

    [data-testid="stMetricDelta"] {{
        color: {COLORS['success']};
    }}

    /* ==================== Expanders ==================== */

    .streamlit-expanderHeader {{
        background-color: {COLORS['secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['borders']};
        border-radius: 6px;
    }}

    .streamlit-expanderHeader:hover {{
        border-color: {COLORS['accent']};
    }}

    /* ==================== Tabs ==================== */

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {COLORS['secondary']};
        padding: 0.5rem;
        border-radius: 6px;
    }}

    .stTabs [data-baseweb="tab"] {{
        color: {COLORS['text_secondary']};
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: {COLORS['accent']};
        color: {COLORS['primary']};
    }}

    /* ==================== Progress Bars ==================== */

    .stProgress > div > div > div > div {{
        background-color: {COLORS['accent']};
    }}

    /* ==================== Dividers ==================== */

    hr {{
        border-color: {COLORS['borders']};
        margin: 2rem 0;
    }}

    /* ==================== Scrollbars ==================== */

    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}

    ::-webkit-scrollbar-track {{
        background: {COLORS['primary']};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {COLORS['borders']};
        border-radius: 5px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['accent']};
    }}

    /* ==================== Custom Classes ==================== */

    /* Profile card */
    .profile-card {{
        background: linear-gradient(135deg, {COLORS['secondary']} 0%, {COLORS['primary']} 100%);
        border: 1px solid {COLORS['borders']};
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }}

    .profile-card h3 {{
        color: {COLORS['accent']};
        margin: 0 0 0.5rem 0;
    }}

    .profile-detail {{
        color: {COLORS['text_secondary']};
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }}

    .profile-detail strong {{
        color: {COLORS['text_primary']};
    }}

    /* Auth status badge */
    .auth-badge {{
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.5rem 0;
    }}

    .auth-badge.authenticated {{
        background-color: rgba(16, 185, 129, 0.2);
        color: {COLORS['success']};
        border: 1px solid {COLORS['success']};
    }}

    .auth-badge.not-authenticated {{
        background-color: rgba(220, 38, 38, 0.2);
        color: {COLORS['alert']};
        border: 1px solid {COLORS['alert']};
    }}

    /* Gold accent text */
    .gold-text {{
        color: {COLORS['accent']};
        font-weight: 600;
    }}

    /* ==================== Animations ==================== */

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(-10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .fade-in {{
        animation: fadeIn 0.5s ease-in-out;
    }}

    /* ==================== Responsive ==================== */

    @media (max-width: 768px) {{
        .card {{
            padding: 1rem;
        }}

        .profile-card {{
            padding: 1rem;
        }}
    }}

    </style>
    """


def apply_custom_css():
    """
    Apply custom CSS to Streamlit app
    Call this in main.py or at the start of each page
    """
    import streamlit as st
    st.markdown(get_custom_css(), unsafe_allow_html=True)

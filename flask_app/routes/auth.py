"""
Authentication Routes
Handles Kite Connect OAuth login
"""

from flask import Blueprint, request, redirect, url_for, session, flash, current_app
from flask_login import login_user, current_user

from ..services.auth_service import get_auth_service, save_user
from utils.logger import get_logger

logger = get_logger(__name__, 'flask.log')

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login')
def login():
    """
    Redirect user to Kite Connect login page
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    # Get auth service
    auth_service = get_auth_service(
        api_key=current_app.config['KITE_API_KEY'],
        api_secret=current_app.config['KITE_API_SECRET'],
        redirect_uri=current_app.config['KITE_REDIRECT_URI']
    )

    # Generate login URL
    login_url = auth_service.get_login_url()

    # Redirect to Kite
    return redirect(login_url)


@auth_bp.route('/callback')
def callback():
    """
    OAuth callback handler
    Receives request token from Kite and generates access token
    """
    # Get request token from query params
    request_token = request.args.get('request_token')
    status = request.args.get('status')

    # Check if user denied access
    if status == 'error' or not request_token:
        flash('Login failed or was cancelled.', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Get auth service
        auth_service = get_auth_service(
            api_key=current_app.config['KITE_API_KEY'],
            api_secret=current_app.config['KITE_API_SECRET'],
            redirect_uri=current_app.config['KITE_REDIRECT_URI']
        )

        # Generate session (exchange request token for access token)
        session_data = auth_service.generate_session(request_token)

        # Get access token
        access_token = session_data.get('access_token')

        # Get user profile
        profile = auth_service.get_profile(access_token)

        # Create user object
        user = auth_service.create_user(session_data, profile)

        # Save user and access token to .env
        save_user(user, access_token=access_token)

        # Store access token in session
        session['access_token'] = access_token
        session['user_id'] = user.id
        session.permanent = True

        # Log in user (Flask-Login)
        login_user(user, remember=True)

        logger.info(f"User logged in: {user.id}")

        # Create analysis backup for this session (protects data + allows concurrent access)
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from database.hdf5_manager import HDF5Manager

            # Create backup for EQUITY segment (main data)
            manager = HDF5Manager('EQUITY')
            backup_path = manager.create_analysis_backup()
            logger.info(f"Session backup created: {backup_path}")
            flash(f'Welcome, {user.user_name or user.user_id}! Analysis backup created.', 'success')
        except Exception as e:
            logger.warning(f"Failed to create session backup: {e}")
            flash(f'Welcome, {user.user_name or user.user_id}!', 'success')

        # Redirect to dashboard
        return redirect(url_for('dashboard.home'))

    except Exception as e:
        logger.error(f"Error during authentication: {e}", exc_info=True)
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

"""
Kite Data Manager - Flask Application Factory
Creates and configures the Flask app with all extensions and routes
"""

import logging
from pathlib import Path
from flask import Flask
from flask_login import LoginManager

from .config import get_config
from utils.logger import get_logger, setup_root_logger

logger = get_logger(__name__, 'flask.log')


# Initialize Flask-Login
login_manager = LoginManager()


def create_app(config_name: str = None) -> Flask:
    """
    Application factory pattern
    Creates and configures Flask app instance

    Args:
        config_name: 'development', 'production', or 'testing'

    Returns:
        Configured Flask app
    """
    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Validate production config
    if app.config['ENV'] == 'production':
        secret = app.config.get('SECRET_KEY')
        if not secret or secret == 'dev-secret-key-change-in-production':
            raise ValueError("Must set FLASK_SECRET_KEY environment variable in production")

    # Ensure required directories exist
    _create_directories(app)

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Configure logging
    _configure_logging(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register template filters and context processors
    _register_template_helpers(app)

    # Register request hooks
    _register_request_hooks(app)

    app.logger.info(f"Flask app initialized in {app.config['ENV']} mode")

    return app


def _create_directories(app: Flask):
    """Ensure required directories exist"""
    directories = [
        app.config['DATA_DIR'],
        app.config['HDF5_DIR'],
        app.config['EXPORTS_DIR'],
        app.config['LOGS_DIR'],
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def _init_extensions(app: Flask):
    """Initialize Flask extensions"""

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = app.config['LOGIN_VIEW']
    login_manager.login_message = app.config['LOGIN_MESSAGE']
    login_manager.login_message_category = app.config['LOGIN_MESSAGE_CATEGORY']

    # User loader for Flask-Login
    from .services.auth_service import load_user
    login_manager.user_loader(load_user)


def _register_blueprints(app: Flask):
    """Register Flask blueprints (routes)"""

    # Import blueprints
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.data import data_bp
    from .routes.data_api import data_api_bp
    from .routes.fundamentals import fundamentals_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(data_api_bp)
    app.register_blueprint(fundamentals_bp)

    app.logger.info("Blueprints registered")


def _configure_logging(app: Flask):
    """Configure application logging"""

    if app.config['ENV'] == 'production':
        # Production logging to file
        log_file = app.config['LOGS_DIR'] / 'flask_app.log'

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
    else:
        # Development logging to console
        app.logger.setLevel(logging.DEBUG)


def _register_error_handlers(app: Flask):
    """Register custom error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403


def _register_template_helpers(app: Flask):
    """Register custom template filters and context processors"""

    @app.template_filter('format_number')
    def format_number(value):
        """Format numbers with commas"""
        if value is None:
            return '0'
        return f'{value:,}'

    @app.template_filter('format_size')
    def format_size(size_mb):
        """Format file size in MB/GB"""
        if size_mb < 1024:
            return f'{size_mb:.2f} MB'
        else:
            return f'{size_mb / 1024:.2f} GB'

    @app.context_processor
    def inject_globals():
        """Inject global variables into templates"""
        return {
            'app_name': 'Kite Data Manager',
            'segments': app.config['SEGMENTS']
        }


def _register_request_hooks(app: Flask):
    """Register before_request hooks for auto-login"""
    from flask import session
    from flask_login import login_user, current_user
    import sys
    from pathlib import Path

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    @app.before_request
    def auto_login_from_token():
        """Automatically log in user if they have a valid token in .env"""
        # Skip if already authenticated
        if current_user.is_authenticated:
            return

        # Skip for auth routes to avoid loops
        from flask import request
        if request.endpoint and request.endpoint.startswith('auth.'):
            return

        try:
            from api.auth_handler import verify_authentication, get_user_profile, get_token_expiry_info
            from .services.auth_service import User, save_user

            # Check if token exists and is valid
            if verify_authentication():
                profile = get_user_profile()
                if profile:
                    # Get token expiry info
                    expiry_string = None
                    expiry_info = get_token_expiry_info()
                    if expiry_info:
                        expiry_string = expiry_info.get('expiry_string')

                    # Create user
                    user = User(
                        user_id=profile['user_id'],
                        user_name=profile.get('user_name'),
                        email=profile.get('email'),
                        expiry_string=expiry_string
                    )

                    # Save and login
                    save_user(user)
                    login_user(user, remember=True)

                    # Store in session
                    session['user_id'] = user.user_id
                    session.permanent = True

                    app.logger.info(f"Auto-logged in user from .env token: {user.user_name}")

        except Exception as e:
            app.logger.debug(f"Auto-login failed: {e}")

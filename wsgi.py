"""
WSGI Entry Point
Production server entry point for Gunicorn
"""

import os
from flask_app import create_app
from utils.logger import setup_root_logger

# Initialize logging system first
setup_root_logger()

# Get environment from env variable (defaults to development)
env = os.getenv('FLASK_ENV', 'development')

# Create Flask app
app = create_app(config_name=env)

if __name__ == '__main__':
    # For development only - use gunicorn in production
    port = int(os.getenv('FLASK_PORT', 5001))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=(env == 'development')
    )

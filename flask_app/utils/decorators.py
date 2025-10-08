"""
Flask Utility Decorators
Custom decorators for route protection and functionality
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def login_required(f):
    """
    Decorator to require authentication for a route
    Redirects to login page if not authenticated

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "Protected content"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def anonymous_required(f):
    """
    Decorator to require user to be logged out
    Redirects to home if already authenticated
    Useful for login/register pages

    Usage:
        @app.route('/login')
        @anonymous_required
        def login():
            return render_template('login.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            flash('You are already logged in.', 'info')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated_function

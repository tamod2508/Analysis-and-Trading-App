# Flask Architecture Guide - Your Kite App

Deep dive into your Kite Data Manager's Flask architecture, design patterns, and best practices.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Application Factory Pattern](#application-factory-pattern)
3. [Blueprints Structure](#blueprints-structure)
4. [Services Layer](#services-layer)
5. [Configuration Management](#configuration-management)
6. [Authentication Flow](#authentication-flow)
7. [Data Flow](#data-flow)
8. [Template Inheritance](#template-inheritance)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)

---

## Architecture Overview

Your Kite app follows a **layered architecture** with clear separation of concerns:

```
┌────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Templates   │  │    Static    │  │   Routes     │ │
│  │  (Jinja2)    │  │  (CSS/JS)    │  │ (Blueprints) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
├────────────────────────────────────────────────────────┤
│                     BUSINESS LOGIC LAYER                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │    Auth      │  │    Data      │  │   Other      │ │
│  │   Service    │  │   Fetcher    │  │  Services    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
├────────────────────────────────────────────────────────┤
│                     DATA ACCESS LAYER                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ KiteClient   │  │  HDF5        │  │ Instruments  │ │
│  │     API      │  │  Manager     │  │   Database   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────────────────────────────────────┘
```

### Layers Explained

1. **Presentation Layer** - User interface and HTTP handling
   - Templates render HTML
   - Static files provide styling/interactivity
   - Routes handle HTTP requests/responses

2. **Business Logic Layer** - Core application logic
   - Services contain business rules
   - No HTTP knowledge (reusable)
   - Can be used by multiple routes

3. **Data Access Layer** - Database and external APIs
   - Abstracts data storage/retrieval
   - Handles API communication
   - Manages data integrity

### Benefits

✅ **Separation of Concerns** - Each layer has one responsibility
✅ **Testability** - Easy to test each layer independently
✅ **Maintainability** - Changes isolated to specific layers
✅ **Reusability** - Services can be used across routes
✅ **Scalability** - Easy to add new features

---

## Application Factory Pattern

Your app uses the **Application Factory Pattern** instead of creating the Flask app globally.

### Traditional Approach (NOT used)

```python
# ❌ Traditional - app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello"

if __name__ == '__main__':
    app.run()
```

**Problems:**
- Hard to test (app created on import)
- Can't have multiple app instances
- Configuration locked at import time
- Circular import issues

### Application Factory (Your approach)

```python
# ✅ Application Factory - flask_app/__init__.py
from flask import Flask

def create_app(config_name=None):
    """Create and configure Flask application"""
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Configure logging
    _configure_logging(app)

    # Error handlers
    _register_error_handlers(app)

    # Template helpers
    _register_template_helpers(app)

    return app
```

### Benefits

✅ **Multiple Configurations** - Dev, test, production
✅ **Testability** - Create fresh app for each test
✅ **No Circular Imports** - Import blueprint functions separately
✅ **Delayed Configuration** - Configure at runtime
✅ **Extension Initialization** - Extensions bound after creation

### How Your App Uses It

**Development:**
```python
# run.py
from flask_app import create_app

app = create_app('development')
app.run(debug=True)
```

**Production:**
```python
# wsgi.py
from flask_app import create_app

app = create_app('production')
```

**Testing:**
```python
# tests/test_api.py
import pytest
from flask_app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    return app
```

---

## Blueprints Structure

Blueprints organize your app into modular components.

### Your App's Blueprints

```
flask_app/routes/
├── auth.py          # Authentication blueprint
├── dashboard.py     # Dashboard blueprint
└── data_api.py      # Data API blueprint
```

### 1. Auth Blueprint

**Purpose:** User authentication (login/logout)

```python
# routes/auth.py
from flask import Blueprint

# Create blueprint with URL prefix
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login')
def login():
    """Redirect to Kite Connect login"""
    pass

@auth_bp.route('/callback')
def callback():
    """OAuth callback handler"""
    pass

@auth_bp.route('/logout')
def logout():
    """Log out user"""
    pass
```

**URLs:**
- `/auth/login` - Start login flow
- `/auth/callback` - OAuth return URL
- `/auth/logout` - Log out

### 2. Dashboard Blueprint

**Purpose:** Main application dashboard

```python
# routes/dashboard.py
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    return render_template('dashboard/index.html')
```

**URLs:**
- `/dashboard` - Main dashboard

### 3. Data API Blueprint

**Purpose:** RESTful API for data operations

```python
# routes/data_api.py
data_api_bp = Blueprint('data_api', __name__, url_prefix='/api/data')

@data_api_bp.route('/fetch-equity', methods=['POST'])
@login_required
def fetch_equity():
    """Fetch equity data"""
    return jsonify({"success": True})

@data_api_bp.route('/instruments/<exchange>')
@login_required
def get_instruments(exchange):
    """Get instruments list"""
    return jsonify({"instruments": []})
```

**URLs:**
- `/api/data/fetch-equity` - POST endpoint
- `/api/data/fetch-derivatives` - POST endpoint
- `/api/data/instruments/NSE` - GET endpoint
- `/api/data/lookup/NSE/RELIANCE` - GET endpoint

### Blueprint Registration

```python
# flask_app/__init__.py
def _register_blueprints(app):
    """Register all blueprints"""
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.data_api import data_api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(data_api_bp)
```

### Blueprint Benefits

✅ **Organization** - Group related routes
✅ **URL Prefixes** - `/api/data/*` automatically
✅ **Templates** - Can have blueprint-specific templates
✅ **Static Files** - Can have blueprint-specific static files
✅ **Error Handlers** - Blueprint-specific error handling

---

## Services Layer

Services contain your **business logic**, separate from HTTP concerns.

### Why Services?

**Without Services (❌ Bad):**
```python
@app.route('/api/data/fetch-equity', methods=['POST'])
def fetch_equity():
    # All logic mixed in route handler!
    data = request.get_json()
    symbol = data['symbol']

    # Kite API logic
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(session['access_token'])
    token = kite.instruments('NSE').find(lambda x: x['symbol'] == symbol)
    historical_data = kite.historical_data(token, ...)

    # Validation logic
    if not validate_data(historical_data):
        return jsonify({"error": "Invalid data"}), 400

    # Database logic
    db = HDF5Manager()
    db.save_ohlcv('NSE', symbol, 'day', historical_data)

    return jsonify({"success": True})
```

**Problems:**
- Route handler does too much
- Can't reuse logic elsewhere
- Hard to test
- Business logic mixed with HTTP

**With Services (✅ Good):**
```python
# routes/data_api.py
@data_api_bp.route('/api/data/fetch-equity', methods=['POST'])
@login_required
def fetch_equity():
    """HTTP handler - thin layer"""
    data = request.get_json()

    # Get service
    data_fetcher = create_data_fetcher(
        access_token=session['access_token']
    )

    # Call service method
    result = data_fetcher.fetch_equity(
        symbol=data['symbol'],
        from_date=parse_date(data['from_date']),
        to_date=parse_date(data['to_date']),
        interval=data.get('interval', 'day')
    )

    return jsonify(result)
```

```python
# services/data_fetcher.py
class DataFetcherService:
    """Business logic for data fetching"""

    def fetch_equity(self, symbol, from_date, to_date, interval):
        """Fetch equity data - no HTTP knowledge"""
        try:
            # Use KiteClient
            result = self.client.fetch_equity_by_symbol(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )

            return result

        except KiteAuthenticationError as e:
            return {
                'success': False,
                'error': 'Authentication failed',
                'error_type': 'auth'
            }
```

### Your App's Services

#### 1. DataFetcherService

**Location:** `services/data_fetcher.py`

**Purpose:** Fetch and manage historical market data

**Key Methods:**
```python
class DataFetcherService:
    def __init__(self, api_key, access_token):
        """Initialize with credentials"""

    def fetch_equity(self, symbol, from_date, to_date, interval, ...):
        """Fetch equity data from NSE/BSE"""

    def fetch_derivatives(self, exchange, symbol, from_date, to_date, ...):
        """Fetch options/futures data"""

    def fetch_batch(self, requests, progress_callback=None):
        """Batch fetch multiple symbols"""

    def get_instruments(self, exchange, use_cache=True):
        """Get instruments list"""

    def lookup_instrument(self, exchange, symbol):
        """Lookup instrument token"""

    def get_database_info(self, segment='EQUITY'):
        """Get database statistics"""
```

**Usage in Routes:**
```python
# Create service instance
data_fetcher = create_data_fetcher(
    api_key=current_app.config['KITE_API_KEY'],
    access_token=session.get('access_token')
)

# Use service methods
result = data_fetcher.fetch_equity(...)
instruments = data_fetcher.get_instruments('NSE')
db_info = data_fetcher.get_database_info('EQUITY')
```

#### 2. AuthService

**Location:** `services/auth_service.py`

**Purpose:** Handle Kite Connect OAuth authentication

**Key Methods:**
```python
class AuthService:
    def __init__(self, api_key, api_secret, redirect_uri):
        """Initialize with OAuth credentials"""

    def get_login_url(self):
        """Generate Kite Connect login URL"""

    def generate_session(self, request_token):
        """Exchange request token for access token"""

    def get_profile(self, access_token):
        """Get user profile from Kite"""

    def create_user(self, session_data, profile=None):
        """Create User object from session data"""
```

**Usage in Routes:**
```python
# Create service
auth_service = get_auth_service(
    api_key=current_app.config['KITE_API_KEY'],
    api_secret=current_app.config['KITE_API_SECRET'],
    redirect_uri=current_app.config['KITE_REDIRECT_URI']
)

# Generate login URL
login_url = auth_service.get_login_url()

# Process callback
session_data = auth_service.generate_session(request_token)
profile = auth_service.get_profile(access_token)
user = auth_service.create_user(session_data, profile)
```

### Service Benefits

✅ **Reusability** - Use in multiple routes
✅ **Testability** - Test without HTTP
✅ **Separation** - Business logic separate from HTTP
✅ **Maintainability** - Change logic in one place

---

## Configuration Management

Your app supports multiple configurations (dev, test, prod).

### Configuration Classes

```python
# config.py

class Config:
    """Base configuration - shared settings"""
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret')
    KITE_API_KEY = os.getenv('KITE_API_KEY')
    SEGMENTS = ['EQUITY', 'DERIVATIVES']

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'
    SESSION_COOKIE_SECURE = False
    TEMPLATES_AUTO_RELOAD = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True  # Require HTTPS
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
```

### Loading Configuration

```python
# __init__.py
def create_app(config_name=None):
    app = Flask(__name__)

    # Get configuration
    config = get_config(config_name)
    app.config.from_object(config)

    return app
```

### Using Configuration

```python
# In routes
api_key = current_app.config['KITE_API_KEY']
segments = current_app.config['SEGMENTS']

# In templates
{{ config.ENV }}
{{ config.SEGMENTS }}
```

### Environment Variables

```bash
# .env file
FLASK_ENV=development  # or production, testing
FLASK_SECRET_KEY=your-secret-key
KITE_API_KEY=your-api-key
KITE_API_SECRET=your-secret
KITE_REDIRECT_URI=http://127.0.0.1:5000/auth/callback
```

---

## Authentication Flow

Your app uses **Flask-Login** for session management and **Kite Connect OAuth** for authentication.

### Complete Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOW                       │
└─────────────────────────────────────────────────────────────┘

1. User clicks "Login"
   ↓
2. Browser → GET /auth/login
   ↓
3. Flask redirects to Kite Connect OAuth page
   Browser → https://kite.zerodha.com/connect/login?api_key=...
   ↓
4. User logs in on Kite website
   ↓
5. Kite redirects back with request_token
   Browser → GET /auth/callback?request_token=abc123&status=success
   ↓
6. Flask exchanges request_token for access_token
   Flask → POST https://api.kite.trade/session/token
   ← Response: { "access_token": "xyz789", "user_id": "AB1234" }
   ↓
7. Flask stores access_token in session
   session['access_token'] = 'xyz789'
   session['user_id'] = 'AB1234'
   ↓
8. Flask creates User object and logs in with Flask-Login
   login_user(user, remember=True)
   ↓
9. Flask redirects to dashboard
   Browser → GET /dashboard
   ↓
10. User is now authenticated!
```

### Code Implementation

```python
# routes/auth.py

@auth_bp.route('/login')
def login():
    """Step 1-3: Redirect to Kite OAuth"""
    auth_service = get_auth_service(...)
    login_url = auth_service.get_login_url()
    return redirect(login_url)

@auth_bp.route('/callback')
def callback():
    """Step 5-9: Process OAuth callback"""
    request_token = request.args.get('request_token')

    # Step 6: Exchange for access token
    auth_service = get_auth_service(...)
    session_data = auth_service.generate_session(request_token)
    access_token = session_data['access_token']

    # Step 7: Store in session
    session['access_token'] = access_token
    session['user_id'] = session_data['user_id']

    # Step 8: Create user and login
    user = auth_service.create_user(session_data)
    save_user(user)
    login_user(user, remember=True)

    # Step 9: Redirect to dashboard
    return redirect(url_for('dashboard.index'))
```

### Protecting Routes

```python
from flask_login import login_required

@data_api_bp.route('/fetch-equity', methods=['POST'])
@login_required  # User must be logged in
def fetch_equity():
    # Get access token from session
    access_token = session.get('access_token')

    # Use access token
    data_fetcher = create_data_fetcher(access_token=access_token)
    result = data_fetcher.fetch_equity(...)

    return jsonify(result)
```

### Flask-Login Setup

```python
# __init__.py
from flask_login import LoginManager

login_manager = LoginManager()

def _init_extensions(app):
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Redirect here if not logged in

    # User loader - required by Flask-Login
    from .services.auth_service import load_user
    login_manager.user_loader(load_user)
```

```python
# services/auth_service.py
class User(UserMixin):
    """User model for Flask-Login"""
    def __init__(self, user_id, user_name=None, email=None):
        self.id = user_id
        self.user_id = user_id
        self.user_name = user_name
        self.email = email

def load_user(user_id):
    """Load user by ID (called by Flask-Login)"""
    return _users.get(user_id)
```

---

## Data Flow

How data moves through your application.

### Fetch Equity Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       DATA FLOW                              │
└─────────────────────────────────────────────────────────────┘

1. Browser sends POST request
   POST /api/data/fetch-equity
   {
     "symbol": "RELIANCE",
     "from_date": "2024-01-01",
     "to_date": "2024-12-31",
     "interval": "day"
   }
   ↓
2. Flask routes to data_api_bp.fetch_equity()
   ↓
3. Route handler extracts JSON data
   data = request.get_json()
   symbol = data['symbol']
   ↓
4. Creates DataFetcherService instance
   data_fetcher = create_data_fetcher(access_token=session['access_token'])
   ↓
5. Calls service method
   result = data_fetcher.fetch_equity(symbol, from_date, to_date, interval)
   ↓
6. Service uses KiteClient (api/kite_client.py)
   self.client.fetch_equity_by_symbol(...)
   ↓
7. KiteClient calls Kite API
   GET https://api.kite.trade/instruments/historical/...
   ↓
8. API returns OHLCV data
   [
     {"date": "2024-01-01", "open": 2800, "high": 2850, ...},
     ...
   ]
   ↓
9. KiteClient validates data
   validation_result = self.validator.validate(data)
   ↓
10. KiteClient saves to HDF5
    self.db.save_ohlcv('NSE', 'RELIANCE', 'day', data)
    ↓
11. Service returns result dict
    {
      "success": true,
      "symbol": "RELIANCE",
      "records": 248,
      "elapsed_seconds": 3.45
    }
    ↓
12. Route handler returns JSON response
    return jsonify(result)
    ↓
13. Browser receives response
    { "success": true, "records": 248 }
```

### Layer Responsibilities

| Layer | Responsibility | Example |
|-------|----------------|---------|
| **Route** | HTTP handling | Parse JSON, return response |
| **Service** | Business logic | Coordinate fetching, error handling |
| **Client** | API communication | Call Kite API, retry on errors |
| **Database** | Data persistence | Save to HDF5, read from HDF5 |

---

## Template Inheritance

Templates use **inheritance** to avoid duplication.

### Base Template

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>

    <!-- CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    {% include 'components/navbar.html' %}

    <!-- Flash messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <!-- Main content -->
    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    {% include 'components/footer.html' %}

    <!-- JavaScript -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### Child Template

```html
<!-- templates/dashboard/index.html -->
{% extends "base.html" %}

{% block title %}Dashboard - {{ app_name }}{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
{% endblock %}

{% block content %}
<h1>Dashboard</h1>

<div class="stats-grid">
    {% for segment in segments %}
    <div class="stat-card">
        <h3>{{ segment }}</h3>
        <p>{{ db_info[segment].total_datasets }} datasets</p>
        <p>{{ db_info[segment].size_mb | format_size }}</p>
    </div>
    {% endfor %}
</div>

<div class="fetch-form">
    <h2>Fetch Data</h2>
    <!-- Form here -->
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
{% endblock %}
```

### Template Hierarchy

```
base.html                    ← Base template (header, footer, structure)
├── dashboard/
│   └── index.html           ← Extends base (adds dashboard content)
├── auth/
│   └── login.html           ← Extends base (adds login form)
└── data/
    └── fetch.html           ← Extends base (adds fetch UI)
```

### Benefits

✅ **DRY** - Don't repeat header/footer
✅ **Consistency** - Same structure across pages
✅ **Maintainability** - Change header once, affects all pages
✅ **Organization** - Clear parent-child relationships

---

## Error Handling

Graceful error handling improves user experience.

### Error Handlers

```python
# __init__.py
def _register_error_handlers(app):
    """Register custom error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
```

### API Error Responses

```python
# routes/data_api.py
@data_api_bp.route('/fetch-equity', methods=['POST'])
def fetch_equity():
    try:
        data = request.get_json()

        # Validate required fields
        required = ['symbol', 'from_date', 'to_date']
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400

        # Process request
        result = data_fetcher.fetch_equity(...)
        return jsonify(result)

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400

    except Exception as e:
        logger.error(f'Error: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Error Templates

```html
<!-- templates/errors/404.html -->
{% extends "base.html" %}

{% block title %}404 - Page Not Found{% endblock %}

{% block content %}
<div class="error-page">
    <h1>404</h1>
    <h2>Page Not Found</h2>
    <p>The page you're looking for doesn't exist.</p>
    <a href="{{ url_for('dashboard.index') }}" class="btn btn-primary">
        Go to Dashboard
    </a>
</div>
{% endblock %}
```

---

## Best Practices

### 1. Keep Routes Thin

**❌ Bad:**
```python
@app.route('/api/data/fetch-equity', methods=['POST'])
def fetch_equity():
    # 200 lines of business logic here...
    pass
```

**✅ Good:**
```python
@app.route('/api/data/fetch-equity', methods=['POST'])
def fetch_equity():
    # Extract data
    data = request.get_json()

    # Call service
    result = data_fetcher.fetch_equity(...)

    # Return response
    return jsonify(result)
```

### 2. Use Services for Business Logic

**✅ Do:**
- Put business logic in services
- Make services reusable
- Test services independently

**❌ Don't:**
- Put business logic in routes
- Mix HTTP concerns with business logic

### 3. Handle Errors Gracefully

**✅ Do:**
```python
try:
    result = risky_operation()
    return jsonify(result)
except SpecificError as e:
    logger.error(f'Specific error: {e}')
    return jsonify({'error': 'User-friendly message'}), 400
except Exception as e:
    logger.error(f'Unexpected error: {e}', exc_info=True)
    return jsonify({'error': 'Something went wrong'}), 500
```

### 4. Use Type Hints

**✅ Do:**
```python
def fetch_equity(
    self,
    symbol: str,
    from_date: datetime,
    to_date: datetime,
    interval: str = 'day'
) -> Dict:
    """Fetch equity data"""
    pass
```

### 5. Validate Input

**✅ Do:**
```python
# Validate required fields
required = ['symbol', 'from_date', 'to_date']
missing = [f for f in required if f not in data]
if missing:
    return jsonify({'error': f'Missing: {missing}'}), 400

# Validate types
try:
    from_date = datetime.strptime(data['from_date'], '%Y-%m-%d')
except ValueError:
    return jsonify({'error': 'Invalid date format'}), 400
```

### 6. Use Configuration

**✅ Do:**
```python
api_key = current_app.config['KITE_API_KEY']
segments = current_app.config['SEGMENTS']
```

**❌ Don't:**
```python
api_key = 'hardcoded-key'  # Never hardcode secrets!
```

### 7. Log Important Events

**✅ Do:**
```python
logger.info(f"User {user_id} fetched data for {symbol}")
logger.error(f"API error: {e}", exc_info=True)
logger.warning(f"Rate limit hit for user {user_id}")
```

### 8. Use Context Managers

**✅ Do:**
```python
with db._open_file('r') as f:
    data = f['data']['NSE']['RELIANCE']['day'][:]
```

### 9. Return Consistent Responses

**✅ Do:**
```python
# Success
return jsonify({
    'success': True,
    'data': result,
    'message': 'Data fetched successfully'
})

# Error
return jsonify({
    'success': False,
    'error': 'Error message',
    'error_type': 'validation'
}), 400
```

---

## Summary

Your Kite app architecture:

1. **Application Factory** - Create app with different configs
2. **Blueprints** - Organize routes into modules
3. **Services Layer** - Separate business logic from HTTP
4. **Configuration** - Environment-specific settings
5. **Authentication** - OAuth + Flask-Login
6. **Template Inheritance** - DRY templates
7. **Error Handling** - Graceful error responses

**Result:** Scalable, maintainable, testable Flask application! 🚀

---

## Next Steps

1. Read [FLASK_BASICS.md](FLASK_BASICS.md) for Flask fundamentals
2. Read [FLASK_QUICKSTART.md](FLASK_QUICKSTART.md) for hands-on tutorial
3. Read [DATA_FETCHER_README.md](DATA_FETCHER_README.md) for API docs

---

**Happy architecting!** 🏗️

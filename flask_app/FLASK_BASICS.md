# Flask Basics - Complete Beginner's Guide

A comprehensive introduction to Flask web framework, tailored for your Kite Data Manager project.

---

## Table of Contents

1. [What is Flask?](#what-is-flask)
2. [How Web Applications Work](#how-web-applications-work)
3. [Flask Core Concepts](#flask-core-concepts)
4. [Your First Flask App](#your-first-flask-app)
5. [Routing & URL Patterns](#routing--url-patterns)
6. [Templates (Jinja2)](#templates-jinja2)
7. [Static Files (CSS/JS)](#static-files-cssjs)
8. [Request & Response](#request--response)
9. [Sessions & Cookies](#sessions--cookies)
10. [Blueprints (Modular Apps)](#blueprints-modular-apps)
11. [Database Integration](#database-integration)
12. [Error Handling](#error-handling)
13. [Your Kite App Architecture](#your-kite-app-architecture)

---

## What is Flask?

**Flask** is a lightweight Python web framework that helps you build web applications quickly and easily.

### Think of it like this:

```
┌─────────────────────────────────────────────────────────┐
│  Flask is like a restaurant's order-taking system       │
├─────────────────────────────────────────────────────────┤
│  Customer (Browser)  →  Orders (HTTP Request)           │
│         ↓                                                │
│  Waiter (Flask)  →  Takes order to kitchen              │
│         ↓                                                │
│  Chef (Your Code)  →  Prepares the meal                 │
│         ↓                                                │
│  Waiter (Flask)  →  Serves the meal (HTTP Response)     │
│         ↓                                                │
│  Customer (Browser)  →  Enjoys the meal (Displays page) │
└─────────────────────────────────────────────────────────┘
```

### Why Flask?

- **Simple** - Easy to learn, minimal boilerplate
- **Flexible** - Not opinionated, you choose your tools
- **Lightweight** - Core is small, add what you need
- **Python** - Write web apps in familiar Python
- **Popular** - Large community, lots of extensions

### Flask vs Streamlit (What you already know)

| Feature | Streamlit | Flask |
|---------|-----------|-------|
| **Purpose** | Data apps, dashboards | General web apps, APIs |
| **UI** | Auto-generated | You build HTML/CSS/JS |
| **Routing** | Automatic | Manual (you define routes) |
| **Interactivity** | Built-in widgets | You build forms/AJAX |
| **Control** | Less control, simpler | Full control, more work |
| **Best for** | Quick prototypes, ML demos | Production apps, APIs |

**Good news:** Your Kite app can use **both**! Streamlit for dashboards, Flask for API and user management.

---

## How Web Applications Work

Before diving into Flask, let's understand how web apps work.

### The Request-Response Cycle

```
┌──────────────┐                    ┌──────────────┐
│   Browser    │                    │  Web Server  │
│  (Client)    │                    │   (Flask)    │
└──────────────┘                    └──────────────┘
       │                                   │
       │  1. HTTP Request                  │
       │  GET /api/data/fetch-equity       │
       │ ─────────────────────────────────>│
       │                                   │
       │                       2. Process  │
       │                       - Route to  │
       │                         handler   │
       │                       - Run code  │
       │                       - Query DB  │
       │                                   │
       │  3. HTTP Response                 │
       │  { "success": true, ... }         │
       │ <─────────────────────────────────│
       │                                   │
       │  4. Render UI                     │
       │  (Show data to user)              │
       │                                   │
```

### HTTP Methods (Verbs)

- **GET** - Retrieve data (reading)
  - Example: `GET /api/data/instruments/NSE`
  - Like asking "Show me the menu"

- **POST** - Send data (creating/updating)
  - Example: `POST /api/data/fetch-equity`
  - Like ordering "Give me RELIANCE data"

- **PUT** - Update existing data
- **DELETE** - Remove data

### URLs and Routes

A **URL** is the address:
```
https://example.com/api/data/fetch-equity
│       │          │    │    │
scheme  host      path  └─── route
```

A **route** tells Flask what code to run for each URL.

---

## Flask Core Concepts

### 1. The Flask App

```python
from flask import Flask

# Create the Flask application
app = Flask(__name__)

# __name__ tells Flask where to find templates/static files
```

**What's happening:**
- `Flask(__name__)` creates your web application
- `__name__` is a Python variable that equals `'__main__'` when you run the file
- Flask uses this to locate your templates and static files

### 2. Routes (URL Endpoints)

```python
@app.route('/')
def home():
    return "Hello, World!"

@app.route('/about')
def about():
    return "About page"
```

**What's happening:**
- `@app.route('/')` is a **decorator** that registers the URL path
- When someone visits `http://localhost:5000/`, Flask calls `home()`
- The function returns what to show to the user

### 3. Dynamic Routes

```python
@app.route('/user/<username>')
def show_user(username):
    return f"Hello, {username}!"

# Visit: /user/john → "Hello, john!"
```

### 4. HTTP Methods

```python
@app.route('/api/data', methods=['GET', 'POST'])
def handle_data():
    if request.method == 'POST':
        # Handle POST request
        return jsonify({"message": "Data received"})
    else:
        # Handle GET request
        return jsonify({"message": "Send me data"})
```

---

## Your First Flask App

Let's build a simple app step by step.

### Step 1: Install Flask

```bash
pip install flask
```

### Step 2: Create `hello.py`

```python
from flask import Flask

# Create Flask app
app = Flask(__name__)

# Define a route
@app.route('/')
def home():
    return "Welcome to Kite Data Manager!"

@app.route('/greet/<name>')
def greet(name):
    return f"Hello, {name}! 👋"

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
```

### Step 3: Run the app

```bash
python hello.py
```

Output:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Step 4: Visit in browser

- `http://localhost:5000/` → "Welcome to Kite Data Manager!"
- `http://localhost:5000/greet/Alice` → "Hello, Alice! 👋"

**🎉 Congratulations!** You just built your first Flask app!

---

## Routing & URL Patterns

Routes connect URLs to Python functions.

### Basic Routes

```python
@app.route('/')
def index():
    return "Home Page"

@app.route('/about')
def about():
    return "About Page"
```

### Dynamic Routes (URL Parameters)

```python
# Single parameter
@app.route('/user/<username>')
def show_user(username):
    return f"User: {username}"

# Multiple parameters
@app.route('/stock/<exchange>/<symbol>')
def show_stock(exchange, symbol):
    return f"Fetching {symbol} from {exchange}"

# Visit: /stock/NSE/RELIANCE
# Output: "Fetching RELIANCE from NSE"
```

### Type Converters

```python
# String (default)
@app.route('/user/<username>')

# Integer
@app.route('/post/<int:post_id>')
def show_post(post_id):
    return f"Post #{post_id}"

# Float
@app.route('/price/<float:amount>')

# Path (accepts slashes)
@app.route('/path/<path:subpath>')
```

### HTTP Methods

```python
# GET only (default)
@app.route('/data')
def get_data():
    return "Getting data..."

# POST only
@app.route('/data', methods=['POST'])
def post_data():
    return "Posting data..."

# Multiple methods
@app.route('/data', methods=['GET', 'POST'])
def handle_data():
    if request.method == 'POST':
        return "Creating new data"
    return "Showing data"
```

### Example: Your Kite App

```python
# From your data_api.py
@app.route('/api/data/fetch-equity', methods=['POST'])
def fetch_equity():
    # Handle POST request to fetch equity data
    data = request.get_json()  # Get JSON from request body
    symbol = data['symbol']
    # ... fetch data ...
    return jsonify({"success": True, "records": 248})
```

---

## Templates (Jinja2)

Templates let you generate dynamic HTML.

### Why Templates?

Instead of:
```python
@app.route('/user/<name>')
def user(name):
    return f"<html><body><h1>Hello {name}</h1></body></html>"
```

Use templates:
```python
@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)
```

### Template Syntax (Jinja2)

Flask uses **Jinja2** templating engine.

#### 1. Variables

```html
<!-- templates/user.html -->
<h1>Hello {{ name }}!</h1>
<p>Your user ID is {{ user_id }}</p>
```

```python
# Python code
return render_template('user.html', name='Alice', user_id=123)
```

Output:
```html
<h1>Hello Alice!</h1>
<p>Your user ID is 123</p>
```

#### 2. Control Flow

**If statements:**
```html
{% if user.is_authenticated %}
  <p>Welcome back, {{ user.name }}!</p>
{% else %}
  <p>Please log in</p>
{% endif %}
```

**For loops:**
```html
<ul>
{% for stock in stocks %}
  <li>{{ stock.symbol }}: ₹{{ stock.price }}</li>
{% endfor %}
</ul>
```

**With Python:**
```python
stocks = [
    {'symbol': 'RELIANCE', 'price': 2890},
    {'symbol': 'TCS', 'price': 4250}
]
return render_template('stocks.html', stocks=stocks)
```

#### 3. Template Inheritance

**Base template** (`base.html`):
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Kite Data Manager{% endblock %}</title>
</head>
<body>
    <nav><!-- Navigation bar --></nav>

    {% block content %}
    <!-- Page content goes here -->
    {% endblock %}

    <footer><!-- Footer --></footer>
</body>
</html>
```

**Child template** (`dashboard.html`):
```html
{% extends "base.html" %}

{% block title %}Dashboard - Kite Data Manager{% endblock %}

{% block content %}
<h1>Dashboard</h1>
<p>Welcome to your dashboard!</p>
{% endblock %}
```

**Result:** Child template inherits header/footer from base, replaces content block.

#### 4. Filters

```html
<!-- Format numbers -->
{{ 1234567 | format_number }}  → 1,234,567

<!-- Format size -->
{{ 142.35 | format_size }}  → 142.35 MB

<!-- Date formatting -->
{{ date | date_format('%Y-%m-%d') }}

<!-- Upper/lower case -->
{{ "hello" | upper }}  → HELLO
{{ "HELLO" | lower }}  → hello

<!-- Default value -->
{{ missing_value | default('N/A') }}
```

### Your Kite App Templates

Your app already has a base template:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar">
        <!-- Navigation -->
    </nav>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>
```

---

## Static Files (CSS/JS)

Static files are CSS, JavaScript, images that don't change.

### Folder Structure

```
flask_app/
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── img/
│       └── logo.png
└── templates/
    └── index.html
```

### Linking Static Files

**In templates:**
```html
<!-- CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

<!-- JavaScript -->
<script src="{{ url_for('static', filename='js/main.js') }}"></script>

<!-- Images -->
<img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo">
```

**Why `url_for()`?**
- Generates correct URLs automatically
- Works in different environments (dev, production)
- Updates if you move files

### Example CSS (Your Color Palette)

```css
/* static/css/style.css */
:root {
    /* Your color palette */
    --primary: #0A0E27;        /* Deep navy */
    --accent: #D4AF37;         /* Gold */
    --secondary: #1A1F3A;      /* Charcoal navy */
    --text-primary: #F8FAFC;   /* Off-white */
    --success: #10B981;        /* Green */
    --error: #DC2626;          /* Red */
}

body {
    background: var(--primary);
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}

.btn-primary {
    background: var(--accent);
    color: var(--primary);
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}

.success {
    color: var(--success);
}
```

### Example JavaScript

```javascript
// static/js/main.js

// Fetch equity data
async function fetchEquityData(symbol) {
    try {
        const response = await fetch('/api/data/fetch-equity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                from_date: '2024-01-01',
                to_date: '2024-12-31',
                interval: 'day'
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`Fetched ${result.records} records`);
            showSuccess(`Successfully fetched data for ${symbol}`);
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

function showSuccess(message) {
    const alert = document.createElement('div');
    alert.className = 'alert success';
    alert.textContent = message;
    document.body.appendChild(alert);
}
```

---

## Request & Response

### Getting Request Data

```python
from flask import request

@app.route('/search')
def search():
    # Query parameters: /search?q=RELIANCE&exchange=NSE
    query = request.args.get('q')          # 'RELIANCE'
    exchange = request.args.get('exchange') # 'NSE'

    return f"Searching {query} on {exchange}"

@app.route('/api/data', methods=['POST'])
def receive_data():
    # JSON data from request body
    data = request.get_json()
    symbol = data['symbol']
    from_date = data['from_date']

    # Form data (from HTML form)
    # symbol = request.form['symbol']

    return jsonify({"received": symbol})
```

### Request Object Properties

```python
request.method          # 'GET', 'POST', etc.
request.args            # Query parameters (?key=value)
request.form            # Form data (POST)
request.get_json()      # JSON data
request.headers         # HTTP headers
request.cookies         # Cookies
request.files           # Uploaded files
```

### Returning Responses

```python
from flask import jsonify, redirect, url_for, render_template

# Return HTML
@app.route('/')
def home():
    return render_template('home.html')

# Return JSON (for APIs)
@app.route('/api/user')
def get_user():
    return jsonify({
        'name': 'Alice',
        'user_id': 123
    })

# Redirect to another page
@app.route('/old-page')
def old_page():
    return redirect(url_for('new_page'))

# Return with status code
@app.route('/not-found')
def not_found():
    return "Page not found", 404

# Return with headers
@app.route('/download')
def download():
    return response, 200, {
        'Content-Type': 'application/csv',
        'Content-Disposition': 'attachment; filename=data.csv'
    }
```

---

## Sessions & Cookies

Sessions store data **per user** across requests.

### What's a Session?

```
┌─────────────────────────────────────────┐
│  User visits website → Flask creates    │
│  a session (like a shopping cart)       │
│                                          │
│  User adds items → Stored in session    │
│  User logs in → Stored in session       │
│  User navigates pages → Session follows │
└─────────────────────────────────────────┘
```

### Using Sessions

```python
from flask import session

# Set secret key (required for sessions)
app.secret_key = 'your-secret-key-here'

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']

    # Store in session
    session['user_id'] = 123
    session['username'] = username
    session['logged_in'] = True

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Read from session
    if 'logged_in' in session:
        username = session['username']
        return f"Welcome back, {username}!"
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # Clear session
    session.clear()
    return redirect(url_for('home'))
```

### Your Kite App Sessions

```python
# When user logs in (auth.py)
session['access_token'] = access_token
session['user_id'] = user.id
session.permanent = True  # Session lasts 24 hours

# When fetching data (data_api.py)
access_token = session.get('access_token')
data_fetcher = create_data_fetcher(access_token=access_token)
```

---

## Blueprints (Modular Apps)

Blueprints let you organize your app into modules.

### Why Blueprints?

**Without blueprints** (everything in one file):
```python
# app.py (1000+ lines!)
@app.route('/auth/login')
@app.route('/auth/logout')
@app.route('/dashboard')
@app.route('/api/data/fetch-equity')
@app.route('/api/data/fetch-derivatives')
# ... 50+ more routes ...
```

**With blueprints** (organized):
```python
# routes/auth.py
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login')
def login():
    pass

# routes/data_api.py
data_api_bp = Blueprint('data_api', __name__, url_prefix='/api/data')

@data_api_bp.route('/fetch-equity', methods=['POST'])
def fetch_equity():
    pass
```

### Creating a Blueprint

```python
# routes/data_api.py
from flask import Blueprint, jsonify, request

# Create blueprint
data_api_bp = Blueprint('data_api', __name__, url_prefix='/api/data')

@data_api_bp.route('/fetch-equity', methods=['POST'])
def fetch_equity():
    data = request.get_json()
    return jsonify({"success": True})

@data_api_bp.route('/instruments/<exchange>')
def get_instruments(exchange):
    return jsonify({"exchange": exchange})
```

### Registering Blueprints

```python
# __init__.py (app factory)
from flask import Flask

def create_app():
    app = Flask(__name__)

    # Import blueprints
    from .routes.auth import auth_bp
    from .routes.data_api import data_api_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(data_api_bp)

    return app
```

### Your Kite App Blueprints

```
flask_app/
├── routes/
│   ├── auth.py          # Blueprint: auth_bp
│   │   └── /auth/login, /auth/logout, /auth/callback
│   ├── dashboard.py     # Blueprint: dashboard_bp
│   │   └── /dashboard, /dashboard/...
│   └── data_api.py      # Blueprint: data_api_bp
│       └── /api/data/fetch-equity, /api/data/instruments/<exchange>
```

**URLs:**
- Auth blueprint: `http://localhost:5000/auth/login`
- Data API blueprint: `http://localhost:5000/api/data/fetch-equity`

---

## Database Integration

Flask doesn't include a database, but integrates easily.

### Your Kite App Uses HDF5

```python
# services/data_fetcher.py
from database.hdf5_manager import HDF5Manager

class DataFetcherService:
    def fetch_equity(self, symbol, ...):
        # Fetch from Kite API
        data = self.client.fetch_equity_by_symbol(...)

        # Save to HDF5
        db = HDF5Manager(segment='EQUITY')
        db.save_ohlcv(exchange, symbol, interval, data)

        return result
```

### Example: SQLite Database

```python
import sqlite3
from flask import g

# Get database connection
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('database.db')
        g.db.row_factory = sqlite3.Row
    return g.db

# Close connection after request
@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Use in routes
@app.route('/users')
def list_users():
    db = get_db()
    users = db.execute('SELECT * FROM users').fetchall()
    return render_template('users.html', users=users)
```

---

## Error Handling

Handle errors gracefully.

### Error Handlers

```python
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403
```

### Try-Except in Routes

```python
@app.route('/api/data/fetch-equity', methods=['POST'])
def fetch_equity():
    try:
        data = request.get_json()
        symbol = data['symbol']

        # Fetch data
        result = data_fetcher.fetch_equity(symbol, ...)

        return jsonify(result)

    except KeyError as e:
        return jsonify({
            'success': False,
            'error': f'Missing field: {e}'
        }), 400

    except Exception as e:
        logger.error(f'Error: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## Your Kite App Architecture

Let's connect everything to your actual project!

### Project Structure

```
kite_app/
├── flask_app/
│   ├── __init__.py          # App factory (create_app)
│   ├── config.py            # Configuration classes
│   │
│   ├── routes/              # Blueprints (URL handlers)
│   │   ├── auth.py          # /auth/* routes
│   │   ├── dashboard.py     # /dashboard/* routes
│   │   └── data_api.py      # /api/data/* routes
│   │
│   ├── services/            # Business logic
│   │   ├── auth_service.py  # Authentication logic
│   │   └── data_fetcher.py  # Data fetching logic
│   │
│   ├── templates/           # HTML templates
│   │   ├── base.html        # Base template
│   │   ├── auth/            # Auth templates
│   │   ├── dashboard/       # Dashboard templates
│   │   └── errors/          # Error pages
│   │
│   └── static/              # CSS, JS, images
│       ├── css/
│       ├── js/
│       └── img/
│
├── api/                     # Kite API client
├── database/                # HDF5 database
└── config/                  # App configuration
```

### How It Works

```
1. User visits /api/data/fetch-equity
              ↓
2. Flask receives HTTP request
              ↓
3. Routes request to data_api_bp blueprint
              ↓
4. Calls fetch_equity() function
              ↓
5. Function uses DataFetcherService
              ↓
6. Service calls KiteClient (api/kite_client.py)
              ↓
7. KiteClient fetches from Kite API
              ↓
8. Data saved to HDF5Manager (database/hdf5_manager.py)
              ↓
9. Returns JSON response to user
```

### Application Factory Pattern

**Why?**
- Create app with different configs (dev, test, prod)
- Better for testing
- Modular and organized

```python
# flask_app/__init__.py
def create_app(config_name='development'):
    app = Flask(__name__)

    # Load config
    config = get_config(config_name)
    app.config.from_object(config)

    # Setup extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    return app
```

**Usage:**
```python
# Development
app = create_app('development')

# Production
app = create_app('production')

# Testing
app = create_app('testing')
```

---

## Next Steps

Now that you understand Flask basics, check out:

1. **[FLASK_ARCHITECTURE_GUIDE.md](FLASK_ARCHITECTURE_GUIDE.md)** - Deep dive into your app's architecture
2. **[FLASK_QUICKSTART.md](FLASK_QUICKSTART.md)** - Build features step-by-step
3. **[DATA_FETCHER_README.md](DATA_FETCHER_README.md)** - API documentation

---

## Quick Reference

### Common Patterns

```python
# Import Flask essentials
from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for, session
)

# Create app
app = Flask(__name__)
app.secret_key = 'secret'

# Basic route
@app.route('/')
def home():
    return render_template('home.html')

# Route with parameter
@app.route('/user/<username>')
def user(username):
    return render_template('user.html', name=username)

# API endpoint (POST)
@app.route('/api/data', methods=['POST'])
def api_endpoint():
    data = request.get_json()
    return jsonify({"success": True})

# Session usage
session['key'] = 'value'
value = session.get('key')

# Run app
if __name__ == '__main__':
    app.run(debug=True)
```

### Jinja2 Template Syntax

```html
<!-- Variable -->
{{ variable }}

<!-- If statement -->
{% if condition %}
    <p>True</p>
{% else %}
    <p>False</p>
{% endif %}

<!-- For loop -->
{% for item in items %}
    <li>{{ item }}</li>
{% endfor %}

<!-- Extends base -->
{% extends "base.html" %}

{% block content %}
    <!-- Your content -->
{% endblock %}

<!-- Include partial -->
{% include "components/navbar.html" %}

<!-- URL generation -->
<a href="{{ url_for('function_name') }}">Link</a>

<!-- Static file -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

---

## Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **Jinja2 Documentation:** https://jinja.palletsprojects.com/
- **Flask Mega-Tutorial:** https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world

---

**Happy coding!** 🚀 You're now ready to build with Flask!

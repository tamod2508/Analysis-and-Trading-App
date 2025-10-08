# Kite Data Manager - Flask Application

A Flask-based web application for fetching, storing, and analyzing historical market data from Zerodha's Kite Connect API.

---

## 🚀 Quick Start

### For Complete Flask Beginners

**Start here:** [FLASK_LEARNING_INDEX.md](FLASK_LEARNING_INDEX.md)

This is your complete learning path with guides for:
- Flask fundamentals
- Visual understanding of concepts
- Your app's architecture
- Building features hands-on
- API documentation

**Recommended order:**
1. [FLASK_BASICS.md](FLASK_BASICS.md) - Learn Flask fundamentals (40 min)
2. [FLASK_VISUAL_GUIDE.md](FLASK_VISUAL_GUIDE.md) - See visual diagrams (20 min)
3. [FLASK_ARCHITECTURE_GUIDE.md](FLASK_ARCHITECTURE_GUIDE.md) - Understand the architecture (30 min)
4. [FLASK_QUICKSTART.md](FLASK_QUICKSTART.md) - Build features (1-2 hours hands-on)
5. [DATA_FETCHER_README.md](DATA_FETCHER_README.md) - API reference (20 min)

---

## 📚 Documentation

### Learning Guides

| Guide | Description | Time | Best For |
|-------|-------------|------|----------|
| [FLASK_LEARNING_INDEX](FLASK_LEARNING_INDEX.md) | **Start here!** Complete learning path | 10 min | Everyone |
| [FLASK_BASICS](FLASK_BASICS.md) | Flask fundamentals and concepts | 40 min | Beginners |
| [FLASK_VISUAL_GUIDE](FLASK_VISUAL_GUIDE.md) | Visual diagrams and flow charts | 20 min | Visual learners |
| [FLASK_ARCHITECTURE_GUIDE](FLASK_ARCHITECTURE_GUIDE.md) | Deep dive into app architecture | 30 min | Understanding structure |
| [FLASK_QUICKSTART](FLASK_QUICKSTART.md) | Hands-on feature building | 1-2 hours | Learning by doing |
| [DATA_FETCHER_README](DATA_FETCHER_README.md) | API documentation and examples | 20 min | API reference |

### Quick Links

- **New to Flask?** → [FLASK_LEARNING_INDEX.md](FLASK_LEARNING_INDEX.md)
- **Need API docs?** → [DATA_FETCHER_README.md](DATA_FETCHER_README.md)
- **Want to build features?** → [FLASK_QUICKSTART.md](FLASK_QUICKSTART.md)
- **Understanding architecture?** → [FLASK_ARCHITECTURE_GUIDE.md](FLASK_ARCHITECTURE_GUIDE.md)

---

## 🏗️ Project Structure

```
flask_app/
├── README.md                          # This file
├── FLASK_LEARNING_INDEX.md            # Learning path (START HERE)
├── FLASK_BASICS.md                    # Flask fundamentals
├── FLASK_VISUAL_GUIDE.md              # Visual diagrams
├── FLASK_ARCHITECTURE_GUIDE.md        # Architecture deep dive
├── FLASK_QUICKSTART.md                # Hands-on tutorial
├── DATA_FETCHER_README.md             # API documentation
│
├── __init__.py                        # Application factory
├── config.py                          # Configuration
│
├── routes/                            # URL handlers (Blueprints)
│   ├── __init__.py
│   ├── auth.py                        # Authentication routes (/auth/*)
│   ├── dashboard.py                   # Dashboard routes (/dashboard/*)
│   └── data_api.py                    # API routes (/api/data/*)
│
├── services/                          # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py                # Authentication logic
│   └── data_fetcher.py                # Data fetching logic
│
├── templates/                         # HTML templates (Jinja2)
│   ├── base.html                      # Base template
│   ├── auth/                          # Auth pages
│   ├── dashboard/                     # Dashboard pages
│   ├── data/                          # Data pages
│   ├── components/                    # Reusable components
│   └── errors/                        # Error pages
│
├── static/                            # Static files
│   ├── css/                           # Stylesheets
│   ├── js/                            # JavaScript
│   └── img/                           # Images
│
└── utils/                             # Utility functions
```

---

## ⚙️ Setup & Installation

### 1. Install Dependencies

```bash
cd /Users/atm/Desktop/kite_app
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_SECRET_KEY=your-secret-key-here

# Kite API Credentials
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_secret
KITE_ACCESS_TOKEN=your_token
KITE_REDIRECT_URI=http://127.0.0.1:5000/auth/callback
```

### 3. Run the Application

```bash
# Method 1: Using Python
python -c "from flask_app import create_app; app = create_app('development'); app.run(debug=True)"

# Method 2: Create run.py
cat > run.py << 'EOF'
from flask_app import create_app

app = create_app('development')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
EOF

python run.py

# Method 3: Using Flask CLI
export FLASK_APP=flask_app
flask run
```

### 4. Visit the App

Open browser: http://localhost:5000

---

## 🎯 Features

### Data Fetching
- ✅ Fetch equity data (NSE/BSE)
- ✅ Fetch derivatives (NFO/BFO options/futures)
- ✅ Batch fetching multiple symbols
- ✅ Incremental updates (only fetch missing data)
- ✅ Data validation before storage
- ✅ Rate limiting with Kite API

### Data Management
- ✅ Store in HDF5 databases by segment
- ✅ View database statistics
- ✅ Check existing data ranges
- ✅ Instrument lookup and caching

### Authentication
- ✅ Kite Connect OAuth integration
- ✅ Session-based authentication
- ✅ Protected routes

### User Interface
- ✅ Clean, modern design
- ✅ Your custom color palette
- ✅ Responsive layout
- ✅ Real-time progress indicators
- ✅ Error handling and feedback

---

## 🔌 API Endpoints

### Authentication
- `GET /auth/login` - Start Kite OAuth login
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/logout` - Log out user

### Data Fetching
- `POST /api/data/fetch-equity` - Fetch equity data
- `POST /api/data/fetch-derivatives` - Fetch derivatives data
- `POST /api/data/fetch-batch` - Batch fetch multiple symbols

### Data Retrieval
- `GET /api/data/instruments/<exchange>` - Get instruments list
- `GET /api/data/lookup/<exchange>/<symbol>` - Lookup instrument token
- `GET /api/data/database-info/<segment>` - Get database statistics
- `GET /api/data/existing-range/<exchange>/<symbol>/<interval>` - Check existing data

### Dashboard
- `GET /dashboard` - Main dashboard
- `GET /dashboard/fetch` - Data fetching UI
- `GET /dashboard/stats` - Database statistics

**Full API documentation:** [DATA_FETCHER_README.md](DATA_FETCHER_README.md)

---

## 🏛️ Architecture

### Application Layers

```
┌─────────────────────────────────────────────────┐
│          PRESENTATION LAYER                     │
│  Templates (Jinja2) + Static (CSS/JS)           │
│  Routes (Blueprints)                            │
├─────────────────────────────────────────────────┤
│          BUSINESS LOGIC LAYER                   │
│  Services (AuthService, DataFetcherService)     │
├─────────────────────────────────────────────────┤
│          DATA ACCESS LAYER                      │
│  KiteClient + HDF5Manager + InstrumentsDB      │
└─────────────────────────────────────────────────┘
```

### Key Design Patterns

1. **Application Factory** - Create app with different configs
2. **Blueprints** - Modular route organization
3. **Services Layer** - Business logic separation
4. **Repository Pattern** - Data access abstraction

**Learn more:** [FLASK_ARCHITECTURE_GUIDE.md](FLASK_ARCHITECTURE_GUIDE.md)

---

## 🎨 Color Palette

Your app uses a carefully designed color scheme:

```css
/* Primary Colors */
--primary: #0A0E27;        /* Deep navy */
--accent: #D4AF37;         /* Muted gold */
--secondary: #1A1F3A;      /* Charcoal navy */

/* Text Colors */
--text-primary: #F8FAFC;   /* Off-white */
--text-secondary: #94A3B8; /* Cool gray */

/* Status Colors */
--success: #10B981;        /* Emerald green */
--error: #DC2626;          /* Deep red */

/* UI Elements */
--border: #334155;         /* Subtle slate */
```

---

## 🧪 Testing

### Manual Testing

```bash
# Start the app
python run.py

# Visit in browser
open http://localhost:5000
```

### API Testing (cURL)

```bash
# Get instruments
curl http://localhost:5000/api/data/instruments/NSE?limit=10

# Lookup symbol
curl http://localhost:5000/api/data/lookup/NSE/RELIANCE

# Fetch equity data (requires authentication)
curl -X POST http://localhost:5000/api/data/fetch-equity \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "interval": "day"
  }'
```

### Python Testing

```python
import pytest
from flask_app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home(client):
    response = client.get('/')
    assert response.status_code == 200
```

---

## 📖 Usage Examples

### Fetch Equity Data

```javascript
// JavaScript (Fetch API)
async function fetchEquityData() {
    const response = await fetch('/api/data/fetch-equity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            symbol: 'RELIANCE',
            from_date: '2024-01-01',
            to_date: '2024-12-31',
            interval: 'day'
        })
    });

    const result = await response.json();
    console.log(`Fetched ${result.records} records`);
}
```

```python
# Python (requests)
import requests

response = requests.post(
    'http://localhost:5000/api/data/fetch-equity',
    json={
        'symbol': 'RELIANCE',
        'from_date': '2024-01-01',
        'to_date': '2024-12-31',
        'interval': 'day'
    }
)

result = response.json()
print(f"Fetched {result['records']} records")
```

**More examples:** [DATA_FETCHER_README.md](DATA_FETCHER_README.md)

---

## 🔧 Configuration

### Development
```python
# config.py - DevelopmentConfig
DEBUG = True
ENV = 'development'
SESSION_COOKIE_SECURE = False
TEMPLATES_AUTO_RELOAD = True
```

### Production
```python
# config.py - ProductionConfig
DEBUG = False
ENV = 'production'
SESSION_COOKIE_SECURE = True  # Require HTTPS
PREFERRED_URL_SCHEME = 'https'
```

### Testing
```python
# config.py - TestingConfig
TESTING = True
WTF_CSRF_ENABLED = False  # Disable CSRF for testing
```

---

## 🚦 Common Tasks

### Add a New Route

```python
# routes/data_api.py
@data_api_bp.route('/your-endpoint', methods=['GET'])
@login_required
def your_function():
    return jsonify({"message": "Hello!"})
```

### Create a New Page

```html
<!-- templates/your_page.html -->
{% extends "base.html" %}
{% block content %}
<h1>Your Page</h1>
{% endblock %}
```

```python
# routes/dashboard.py
@dashboard_bp.route('/your-page')
@login_required
def your_page():
    return render_template('your_page.html')
```

### Add a New Service

```python
# services/your_service.py
class YourService:
    def __init__(self):
        pass

    def your_method(self):
        # Business logic here
        pass
```

**Learn more:** [FLASK_QUICKSTART.md](FLASK_QUICKSTART.md)

---

## 🤝 Integration with Existing Code

The Flask app integrates seamlessly with your existing Kite application:

- **Same KiteClient** - Uses `api/kite_client.py` for API calls
- **Same HDF5 Storage** - Uses `database/hdf5_manager.py` for data
- **Same Configuration** - Shares `config/` settings
- **Same Validation** - Uses `database/data_validator.py`

**You can run both Streamlit UI and Flask API simultaneously!**

---

## 📚 Learning Resources

### In This Project
- [FLASK_LEARNING_INDEX.md](FLASK_LEARNING_INDEX.md) - Complete learning path
- [FLASK_BASICS.md](FLASK_BASICS.md) - Flask fundamentals
- [FLASK_QUICKSTART.md](FLASK_QUICKSTART.md) - Hands-on tutorial

### External Resources
- **Flask Docs:** https://flask.palletsprojects.com/
- **Flask Mega-Tutorial:** https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world
- **Real Python Flask:** https://realpython.com/tutorials/flask/

---

## 🐛 Troubleshooting

### App won't start

**Check:**
- Python 3.9+ installed
- Dependencies installed: `pip install -r requirements.txt`
- `.env` file exists with required variables
- No other app running on port 5000

### "Template not found" error

**Check:**
- Template exists in `templates/` folder
- Template path is correct in `render_template()`
- Template extends correct base template

### API returns 401 Unauthorized

**Check:**
- User is logged in
- Access token in session
- Route has `@login_required` decorator

### Data fetch fails

**Check:**
- Kite API credentials are correct
- Access token is valid (not expired)
- Symbol exists on exchange
- Date range is valid

---

## 📝 TODO

- [ ] Add data export endpoints (CSV, Excel, Parquet)
- [ ] Create visualization dashboards
- [ ] Add WebSocket support for real-time progress
- [ ] Implement background job processing
- [ ] Add user preferences and settings
- [ ] Create admin panel
- [ ] Add API rate limiting
- [ ] Implement caching layer
- [ ] Add unit tests
- [ ] Create deployment scripts

---

## 📄 License

This project is part of the Kite Data Manager application.

---

## 🙏 Acknowledgments

- **Flask** - Web framework
- **Zerodha Kite Connect** - Market data API
- **HDF5** - Data storage
- **All contributors** to the open-source libraries used

---

## 📞 Support

- **Documentation:** See guides in `flask_app/` folder
- **Project Docs:** See `docs/` folder
- **Flask Help:** https://flask.palletsprojects.com/
- **Kite API Docs:** https://kite.trade/docs/connect/v3/

---

**Version:** 1.0
**Last Updated:** January 2025
**Status:** Active Development

---

## 🎉 You're All Set!

You now have:
- ✅ Complete Flask learning materials
- ✅ Working data fetcher API
- ✅ Beautiful UI templates
- ✅ Comprehensive documentation
- ✅ Hands-on tutorials

**Start your Flask journey:** [FLASK_LEARNING_INDEX.md](FLASK_LEARNING_INDEX.md)

**Happy coding!** 🚀

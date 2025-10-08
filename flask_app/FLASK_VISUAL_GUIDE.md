# Flask Visual Guide - Understanding with Diagrams

Visual explanations of Flask concepts with ASCII diagrams and analogies.

---

## The Restaurant Analogy

Think of Flask as a restaurant's order-taking system:

```
┌────────────────────────────────────────────────────────────┐
│                      THE RESTAURANT                         │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Customer             Waiter              Kitchen           │
│  (Browser)            (Flask)             (Your Code)       │
│      │                   │                    │             │
│      │  1. Order food    │                    │             │
│      │ ─────────────────>│                    │             │
│      │   "GET /menu"     │                    │             │
│      │                   │  2. Check menu     │             │
│      │                   │ ──────────────────>│             │
│      │                   │                    │             │
│      │                   │  3. Menu items     │             │
│      │                   │ <──────────────────│             │
│      │  4. Serve menu    │                    │             │
│      │ <─────────────────│                    │             │
│      │                   │                    │             │
│      │  5. Place order   │                    │             │
│      │ ─────────────────>│  6. Prepare food   │             │
│      │   "POST /order"   │ ──────────────────>│             │
│      │                   │                    │             │
│      │                   │  7. Food ready     │             │
│      │  8. Serve food    │ <──────────────────│             │
│      │ <─────────────────│                    │             │
│      │                   │                    │             │
└────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Customer (Browser)** makes requests
- **Waiter (Flask)** handles requests/responses
- **Kitchen (Your Code)** does the actual work
- **Menu (Routes)** defines what's available

---

## How Flask Works - The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FLASK APPLICATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    1. INCOMING REQUEST                    │  │
│  │                                                            │  │
│  │   Browser → HTTP Request → "GET /api/data/instruments"    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    2. ROUTING LAYER                       │  │
│  │                                                            │  │
│  │   Flask looks at URL and finds matching route:            │  │
│  │   @app.route('/api/data/instruments/<exchange>')          │  │
│  │                                                            │  │
│  │   Finds function: get_instruments(exchange='NSE')         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   3. MIDDLEWARE/CHECKS                    │  │
│  │                                                            │  │
│  │   - Is user authenticated? (@login_required)              │  │
│  │   - Parse request data                                     │  │
│  │   - Check permissions                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 4. EXECUTE FUNCTION                       │  │
│  │                                                            │  │
│  │   def get_instruments(exchange):                          │  │
│  │       data_fetcher = create_data_fetcher(...)             │  │
│  │       instruments = data_fetcher.get_instruments(...)     │  │
│  │       return jsonify(instruments)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    5. BUSINESS LOGIC                      │  │
│  │                                                            │  │
│  │   Service Layer (data_fetcher.py):                        │  │
│  │   - Check cache                                            │  │
│  │   - Call KiteClient API                                    │  │
│  │   - Process data                                           │  │
│  │   - Save to database                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    6. GENERATE RESPONSE                   │  │
│  │                                                            │  │
│  │   Flask converts return value to HTTP response:           │  │
│  │   - JSON: jsonify(data)                                    │  │
│  │   - HTML: render_template('page.html')                    │  │
│  │   - Redirect: redirect('/dashboard')                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   7. SEND TO BROWSER                      │  │
│  │                                                            │  │
│  │   HTTP Response → Browser receives and displays           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Your Kite App Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         KITE DATA MANAGER                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Browser)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   HTML      │  │     CSS     │  │  JavaScript │            │
│  │  Templates  │  │   Styles    │  │   fetch()   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                 │                  │                   │
│         └─────────────────┴──────────────────┘                  │
│                          │                                       │
│                    Renders UI                                    │
│                          │                                       │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                    HTTP Requests
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK APP (Backend)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    ROUTES (Blueprints)                   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  auth_bp               data_api_bp         dashboard_bp │   │
│  │  /auth/login           /api/data/*         /dashboard   │   │
│  │  /auth/callback        /fetch-equity       /stats       │   │
│  │  /auth/logout          /instruments        /fetch       │   │
│  │                                                          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                    Calls Services                                │
│                           │                                      │
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                SERVICES (Business Logic)                 │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  AuthService           DataFetcherService                │   │
│  │  - get_login_url()     - fetch_equity()                  │   │
│  │  - generate_session()  - fetch_derivatives()             │   │
│  │  - create_user()       - fetch_batch()                   │   │
│  │                        - get_instruments()               │   │
│  │                        - lookup_instrument()             │   │
│  │                                                          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                    Uses Data Layer                               │
│                           │                                      │
│                           ↓                                      │
└───────────────────────────┼──────────────────────────────────────┘
                           │
┌───────────────────────────┼──────────────────────────────────────┐
│                    DATA LAYER                                    │
├───────────────────────────┼──────────────────────────────────────┤
│                           │                                      │
│                           ↓                                      │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   KiteClient    │  │  HDF5Manager │  │ InstrumentsDB   │   │
│  │                 │  │              │  │                 │   │
│  │ - Call Kite API │  │ - Save data  │  │ - Cache tokens  │   │
│  │ - Rate limiting │  │ - Read data  │  │ - Lookup fast   │   │
│  │ - Retry logic   │  │ - Validate   │  │                 │   │
│  └────────┬────────┘  └──────┬───────┘  └────────┬────────┘   │
│           │                  │                     │             │
│           ↓                  ↓                     ↓             │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  Kite API       │  │  EQUITY.h5   │  │ instruments.h5  │   │
│  │  (External)     │  │  DERIV.h5    │  │                 │   │
│  └─────────────────┘  │  COMM.h5     │  └─────────────────┘   │
│                       │  CURR.h5     │                          │
│                       └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Example

Let's trace a real request through your app:

**User clicks "Fetch RELIANCE data"**

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Browser → Flask                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Browser:                                                        │
│    POST /api/data/fetch-equity                                  │
│    Content-Type: application/json                               │
│    Cookie: session=abc123                                       │
│    Body: {                                                       │
│      "symbol": "RELIANCE",                                       │
│      "from_date": "2024-01-01",                                  │
│      "to_date": "2024-12-31",                                    │
│      "interval": "day"                                           │
│    }                                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Flask Routing                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Flask matches URL to route:                                    │
│    @data_api_bp.route('/fetch-equity', methods=['POST'])        │
│    def fetch_equity():                                           │
│                                                                  │
│  Checks decorators:                                              │
│    @login_required ✓ (session has access_token)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Route Handler                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  def fetch_equity():                                             │
│      # Parse JSON                                                │
│      data = request.get_json()                                   │
│      symbol = data['symbol']  # 'RELIANCE'                       │
│                                                                  │
│      # Parse dates                                               │
│      from_date = datetime.strptime(data['from_date'], '%Y-%m-%d')│
│      to_date = datetime.strptime(data['to_date'], '%Y-%m-%d')   │
│                                                                  │
│      # Get access token from session                             │
│      access_token = session.get('access_token')                  │
│                                                                  │
│      # Create service                                            │
│      data_fetcher = create_data_fetcher(                         │
│          access_token=access_token                               │
│      )                                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Service Layer                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DataFetcherService.fetch_equity():                              │
│                                                                  │
│      # Use KiteClient                                            │
│      result = self.client.fetch_equity_by_symbol(                │
│          symbol='RELIANCE',                                      │
│          from_date=datetime(2024, 1, 1),                         │
│          to_date=datetime(2024, 12, 31),                         │
│          interval='day'                                          │
│      )                                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: KiteClient (API Layer)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  KiteClient.fetch_equity_by_symbol():                            │
│                                                                  │
│      # 1. Lookup instrument token                               │
│      token = self.lookup_instrument_token('NSE', 'RELIANCE')     │
│      # Result: 738561                                            │
│                                                                  │
│      # 2. Calculate missing date ranges                          │
│      existing_range = self.get_existing_date_range(...)          │
│      missing_ranges = self.calculate_missing_ranges(...)         │
│                                                                  │
│      # 3. Fetch data from Kite API                              │
│      data = self.fetch_historical_data_chunked(                  │
│          instrument_token=738561,                                │
│          symbol='RELIANCE',                                      │
│          from_date=...,                                          │
│          to_date=...                                             │
│      )                                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: External API Call                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Kite API:                                                       │
│    GET https://api.kite.trade/instruments/historical/...         │
│                                                                  │
│  Response: [                                                     │
│    {                                                             │
│      "date": "2024-01-01T09:15:00+0530",                         │
│      "open": 2800.50,                                            │
│      "high": 2850.00,                                            │
│      "low": 2795.00,                                             │
│      "close": 2840.75,                                           │
│      "volume": 1234567                                           │
│    },                                                            │
│    ... 247 more records ...                                     │
│  ]                                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Data Validation                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DataValidator.validate():                                       │
│                                                                  │
│      ✓ Check price ranges (₹0.01 - ₹1M for equity)              │
│      ✓ Verify OHLC relationships (low ≤ open/close ≤ high)      │
│      ✓ Validate volumes (0 - 10B)                               │
│      ✓ Check date consistency                                   │
│                                                                  │
│  Result: VALID ✓                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: Save to Database                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HDF5Manager.save_ohlcv():                                       │
│                                                                  │
│      # Convert to NumPy array                                   │
│      array = dict_to_ohlcv_array(data)                          │
│                                                                  │
│      # Save to HDF5                                             │
│      Path: /data/NSE/RELIANCE/day                               │
│      File: EQUITY.h5                                            │
│      Compression: Blosc:LZ4                                     │
│      Checksum: SHA-256                                          │
│                                                                  │
│      Records saved: 248                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: Return Result                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  result = {                                                      │
│      'success': True,                                            │
│      'symbol': 'RELIANCE',                                       │
│      'interval': 'day',                                          │
│      'records': 248,                                             │
│      'date_range': '2024-01-01 to 2024-12-31',                   │
│      'elapsed_seconds': 3.45                                     │
│  }                                                               │
│                                                                  │
│  return jsonify(result)                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 10: Flask → Browser                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HTTP Response:                                                  │
│    Status: 200 OK                                                │
│    Content-Type: application/json                               │
│    Body: {                                                       │
│      "success": true,                                            │
│      "symbol": "RELIANCE",                                       │
│      "records": 248,                                             │
│      "elapsed_seconds": 3.45                                     │
│    }                                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 11: JavaScript Displays Result                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  fetch('/api/data/fetch-equity')                                 │
│    .then(response => response.json())                            │
│    .then(result => {                                             │
│        if (result.success) {                                     │
│            showSuccess(result);  // Display green checkmark      │
│        }                                                         │
│    });                                                           │
│                                                                  │
│  User sees: ✓ Fetched 248 records for RELIANCE                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Total time: 3.45 seconds** ⚡

---

## Blueprints Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                         FLASK APP                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  app = create_app()                                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                    BLUEPRINT: auth_bp                   │    │
│  │                    Prefix: /auth                        │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │                                                         │    │
│  │  @auth_bp.route('/login')                              │    │
│  │  URL: /auth/login                                       │    │
│  │  Function: login()                                      │    │
│  │                                                         │    │
│  │  @auth_bp.route('/callback')                           │    │
│  │  URL: /auth/callback                                    │    │
│  │  Function: callback()                                   │    │
│  │                                                         │    │
│  │  @auth_bp.route('/logout')                             │    │
│  │  URL: /auth/logout                                      │    │
│  │  Function: logout()                                     │    │
│  │                                                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                 BLUEPRINT: data_api_bp                  │    │
│  │                 Prefix: /api/data                       │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │                                                         │    │
│  │  @data_api_bp.route('/fetch-equity', methods=['POST']) │    │
│  │  URL: /api/data/fetch-equity                            │    │
│  │  Function: fetch_equity()                               │    │
│  │                                                         │    │
│  │  @data_api_bp.route('/instruments/<exchange>')         │    │
│  │  URL: /api/data/instruments/NSE                         │    │
│  │  Function: get_instruments(exchange='NSE')              │    │
│  │                                                         │    │
│  │  @data_api_bp.route('/lookup/<exchange>/<symbol>')     │    │
│  │  URL: /api/data/lookup/NSE/RELIANCE                     │    │
│  │  Function: lookup_instrument(...)                       │    │
│  │                                                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                BLUEPRINT: dashboard_bp                  │    │
│  │                Prefix: /dashboard                       │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │                                                         │    │
│  │  @dashboard_bp.route('/')                              │    │
│  │  URL: /dashboard                                        │    │
│  │  Function: index()                                      │    │
│  │                                                         │    │
│  │  @dashboard_bp.route('/fetch')                         │    │
│  │  URL: /dashboard/fetch                                  │    │
│  │  Function: fetch_page()                                 │    │
│  │                                                         │    │
│  │  @dashboard_bp.route('/stats')                         │    │
│  │  URL: /dashboard/stats                                  │    │
│  │  Function: stats()                                      │    │
│  │                                                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Benefits:
✓ Organized by feature
✓ Easy to find routes
✓ Clean URL structure
✓ Reusable modules
```

---

## Session Management

```
┌─────────────────────────────────────────────────────────────────┐
│                      SESSION LIFECYCLE                           │
└─────────────────────────────────────────────────────────────────┘

STEP 1: User Visits Site (Not Logged In)
┌────────────────────────────────────────┐
│  Browser                   Flask       │
│  ┌──────────┐              ┌────────┐ │
│  │ No cookie│ ───GET /──>  │ Create │ │
│  └──────────┘              │ session│ │
│       ↑                    └────────┘ │
│       │                         │      │
│       │    Set-Cookie:          │      │
│       │    session=abc123       │      │
│       └─────────────────────────┘      │
│                                         │
│  session = {}  (empty)                 │
└────────────────────────────────────────┘

STEP 2: User Logs In
┌────────────────────────────────────────┐
│  Browser                   Flask       │
│  ┌──────────┐              ┌────────┐ │
│  │  Click   │              │  OAuth │ │
│  │  Login   │ ───────────> │ Process│ │
│  └──────────┘              └────────┘ │
│                                 │      │
│                          Store in      │
│                          session:      │
│                                        │
│  session = {                           │
│      'access_token': 'xyz789',         │
│      'user_id': 'AB1234',              │
│      'logged_in': True                 │
│  }                                     │
└────────────────────────────────────────┘

STEP 3: User Makes API Call
┌────────────────────────────────────────┐
│  Browser                   Flask       │
│  ┌──────────┐              ┌────────┐ │
│  │ POST     │              │ Check  │ │
│  │ fetch-   │ ───────────> │ session│ │
│  │ equity   │              │        │ │
│  └──────────┘              └────────┘ │
│  Cookie:                        │      │
│  session=abc123                 │      │
│                                 ↓      │
│                          Read session: │
│                                        │
│  access_token = session['access_token']│
│  # Use token for API call              │
└────────────────────────────────────────┘

STEP 4: User Logs Out
┌────────────────────────────────────────┐
│  Browser                   Flask       │
│  ┌──────────┐              ┌────────┐ │
│  │  Click   │              │ Clear  │ │
│  │  Logout  │ ───────────> │ session│ │
│  └──────────┘              └────────┘ │
│       ↑                         │      │
│       │    Delete cookie        │      │
│       └─────────────────────────┘      │
│                                         │
│  session = {}  (cleared)               │
└────────────────────────────────────────┘
```

---

## Template Inheritance

```
┌─────────────────────────────────────────────────────────────────┐
│                      TEMPLATE HIERARCHY                          │
└─────────────────────────────────────────────────────────────────┘

                        base.html
                   (Master Template)
                           │
            ┌──────────────┼──────────────┐
            │              │              │
       dashboard/     dashboard/      auth/
       index.html     stats.html      login.html
     (Child pages extend base)


┌─────────────────────────────────────────────────────────────────┐
│ base.html (Parent)                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  <!DOCTYPE html>                                                 │
│  <html>                                                          │
│  <head>                                                          │
│      <title>{% block title %}App{% endblock %}</title>          │
│      <link rel="stylesheet" href="...">                          │
│      {% block extra_css %}{% endblock %}  ← Child can add CSS   │
│  </head>                                                         │
│  <body>                                                          │
│      <nav><!-- Navbar --></nav>                                  │
│                                                                  │
│      {% block content %}                                         │
│      <!-- Child content goes here -->                            │
│      {% endblock %}                                              │
│                                                                  │
│      <footer><!-- Footer --></footer>                            │
│      <script src="..."></script>                                 │
│      {% block extra_js %}{% endblock %}  ← Child can add JS     │
│  </body>                                                         │
│  </html>                                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓ extends
┌─────────────────────────────────────────────────────────────────┐
│ dashboard/index.html (Child)                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  {% extends "base.html" %}  ← Inherit from parent               │
│                                                                  │
│  {% block title %}Dashboard - App{% endblock %}  ← Override     │
│                                                                  │
│  {% block extra_css %}                                           │
│  <link rel="stylesheet" href="dashboard.css">  ← Add more CSS   │
│  {% endblock %}                                                  │
│                                                                  │
│  {% block content %}  ← Replace content block                    │
│  <h1>Dashboard</h1>                                              │
│  <p>Welcome!</p>                                                 │
│  <!-- Dashboard specific content -->                             │
│  {% endblock %}                                                  │
│                                                                  │
│  {% block extra_js %}                                            │
│  <script src="dashboard.js"></script>  ← Add more JS            │
│  {% endblock %}                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓ renders as
┌─────────────────────────────────────────────────────────────────┐
│ Final HTML (What browser receives)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  <!DOCTYPE html>                                                 │
│  <html>                                                          │
│  <head>                                                          │
│      <title>Dashboard - App</title>  ← From child               │
│      <link rel="stylesheet" href="...">  ← From parent          │
│      <link rel="stylesheet" href="dashboard.css">  ← From child │
│  </head>                                                         │
│  <body>                                                          │
│      <nav><!-- Navbar --></nav>  ← From parent                   │
│                                                                  │
│      <h1>Dashboard</h1>  ← From child                            │
│      <p>Welcome!</p>                                             │
│                                                                  │
│      <footer><!-- Footer --></footer>  ← From parent             │
│      <script src="..."></script>  ← From parent                  │
│      <script src="dashboard.js"></script>  ← From child         │
│  </body>                                                         │
│  </html>                                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Application Factory Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│              APPLICATION FACTORY PATTERN                         │
└─────────────────────────────────────────────────────────────────┘

Traditional (❌ Bad):
───────────────────────
app.py:
    app = Flask(__name__)  ← Created at import time
    app.config['DEBUG'] = True
    @app.route('/')
    ...

Problems:
    - Can't create multiple app instances
    - Hard to test
    - Configuration locked at import
    - Circular imports

Application Factory (✅ Good):
────────────────────────────────
flask_app/__init__.py:

    def create_app(config_name='development'):
        """Factory function to create app"""

        ┌──────────────────────────────────────┐
        │  1. Create Flask app                 │
        │     app = Flask(__name__)            │
        └──────────────────────────────────────┘
                      ↓
        ┌──────────────────────────────────────┐
        │  2. Load configuration               │
        │     config = get_config(config_name) │
        │     app.config.from_object(config)   │
        └──────────────────────────────────────┘
                      ↓
        ┌──────────────────────────────────────┐
        │  3. Initialize extensions            │
        │     login_manager.init_app(app)      │
        └──────────────────────────────────────┘
                      ↓
        ┌──────────────────────────────────────┐
        │  4. Register blueprints              │
        │     app.register_blueprint(auth_bp)  │
        │     app.register_blueprint(data_bp)  │
        └──────────────────────────────────────┘
                      ↓
        ┌──────────────────────────────────────┐
        │  5. Configure logging                │
        │     setup_logging(app)               │
        └──────────────────────────────────────┘
                      ↓
        ┌──────────────────────────────────────┐
        │  6. Error handlers                   │
        │     @app.errorhandler(404)           │
        └──────────────────────────────────────┘
                      ↓
        ┌──────────────────────────────────────┐
        │  7. Return configured app            │
        │     return app                       │
        └──────────────────────────────────────┘

Usage:
──────
# Development
app = create_app('development')

# Production
app = create_app('production')

# Testing
app = create_app('testing')

# Each creates a separate app instance!
```

---

## Summary Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK QUICK REFERENCE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ROUTING                                                         │
│  ────────                                                        │
│  @app.route('/path')                    Basic route              │
│  @app.route('/user/<name>')             Dynamic route            │
│  @app.route('/api', methods=['POST'])   POST endpoint            │
│                                                                  │
│  REQUEST/RESPONSE                                                │
│  ─────────────────                                               │
│  request.args.get('key')                Query params             │
│  request.form['key']                    Form data                │
│  request.get_json()                     JSON data                │
│  return jsonify(data)                   Return JSON              │
│  return render_template('page.html')    Return HTML              │
│  return redirect(url_for('function'))   Redirect                 │
│                                                                  │
│  TEMPLATES                                                       │
│  ──────────                                                      │
│  {{ variable }}                         Print variable           │
│  {% if condition %}...{% endif %}       Conditional              │
│  {% for item in items %}...{% endfor %} Loop                     │
│  {% extends "base.html" %}              Inherit template         │
│  {% block content %}...{% endblock %}   Define block             │
│  {{ url_for('function') }}              Generate URL             │
│                                                                  │
│  SESSION                                                         │
│  ────────                                                        │
│  session['key'] = value                 Store in session         │
│  value = session.get('key')             Read from session        │
│  session.clear()                        Clear session            │
│                                                                  │
│  BLUEPRINTS                                                      │
│  ───────────                                                     │
│  bp = Blueprint('name', __name__,       Create blueprint         │
│                 url_prefix='/prefix')                            │
│  @bp.route('/path')                     Add route                │
│  app.register_blueprint(bp)             Register blueprint       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**You now have a complete visual understanding of Flask!** 🎨

For more details:
- [FLASK_BASICS.md](FLASK_BASICS.md) - Learn Flask fundamentals
- [FLASK_ARCHITECTURE_GUIDE.md](FLASK_ARCHITECTURE_GUIDE.md) - Understand the architecture
- [FLASK_QUICKSTART.md](FLASK_QUICKSTART.md) - Build features hands-on

# Flask Quickstart - Build Your First Feature

Hands-on tutorial to build features in your Kite Data Manager Flask app.

---

## Table of Contents

1. [Setup & Run](#setup--run)
2. [Build a Data Fetch UI](#build-a-data-fetch-ui)
3. [Add a New API Endpoint](#add-a-new-api-endpoint)
4. [Create a New Page](#create-a-new-page)
5. [Add Real-Time Progress](#add-real-time-progress)
6. [Style with Your Color Palette](#style-with-your-color-palette)
7. [Testing Your Code](#testing-your-code)

---

## Setup & Run

### 1. Install Dependencies

```bash
cd /Users/atm/Desktop/kite_app
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create `.env` file:
```bash
# .env
FLASK_ENV=development
FLASK_SECRET_KEY=dev-secret-key-change-in-production
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_secret
KITE_ACCESS_TOKEN=your_token
KITE_REDIRECT_URI=http://127.0.0.1:5000/auth/callback
```

### 3. Run the App

```bash
# Method 1: Using flask run
export FLASK_APP=flask_app
flask run

# Method 2: Using Python
python -c "from flask_app import create_app; app = create_app('development'); app.run(debug=True)"

# Method 3: Create run.py
cat > run.py << 'EOF'
from flask_app import create_app

app = create_app('development')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
EOF

python run.py
```

### 4. Visit the App

Open browser: `http://localhost:5000`

You should see the app running!

---

## Build a Data Fetch UI

Let's build a complete data fetching interface from scratch.

### Step 1: Create the HTML Template

Create `templates/data/fetch.html`:

```html
{% extends "base.html" %}

{% block title %}Fetch Data - {{ app_name }}{% endblock %}

{% block content %}
<div class="fetch-page">
    <div class="page-header">
        <h1>Fetch Historical Data</h1>
        <p>Fetch OHLCV data from Kite Connect</p>
    </div>

    <!-- Fetch Form -->
    <div class="fetch-form card">
        <h2>Fetch Equity Data</h2>

        <form id="fetch-equity-form">
            <!-- Symbol -->
            <div class="form-group">
                <label for="symbol">Symbol</label>
                <input type="text" id="symbol" name="symbol"
                       placeholder="RELIANCE" required>
                <small>Enter NSE/BSE stock symbol</small>
            </div>

            <!-- Exchange (optional) -->
            <div class="form-group">
                <label for="exchange">Exchange (optional)</label>
                <select id="exchange" name="exchange">
                    <option value="">Auto-detect</option>
                    <option value="NSE">NSE</option>
                    <option value="BSE">BSE</option>
                </select>
            </div>

            <!-- Date Range -->
            <div class="form-row">
                <div class="form-group">
                    <label for="from_date">From Date</label>
                    <input type="date" id="from_date" name="from_date"
                           value="2024-01-01" required>
                </div>
                <div class="form-group">
                    <label for="to_date">To Date</label>
                    <input type="date" id="to_date" name="to_date"
                           value="2024-12-31" required>
                </div>
            </div>

            <!-- Interval -->
            <div class="form-group">
                <label for="interval">Interval</label>
                <select id="interval" name="interval">
                    <option value="day">Daily</option>
                    <option value="60minute">60 Minute</option>
                    <option value="30minute">30 Minute</option>
                    <option value="15minute">15 Minute</option>
                    <option value="5minute">5 Minute</option>
                    <option value="minute">1 Minute</option>
                </select>
            </div>

            <!-- Options -->
            <div class="form-group">
                <label class="checkbox">
                    <input type="checkbox" id="validate" name="validate" checked>
                    Validate data before saving
                </label>
                <label class="checkbox">
                    <input type="checkbox" id="incremental" name="incremental" checked>
                    Incremental update (only fetch missing data)
                </label>
            </div>

            <!-- Submit Button -->
            <button type="submit" class="btn btn-primary">
                <span class="btn-text">Fetch Data</span>
                <span class="btn-loading" style="display: none;">
                    <span class="spinner"></span> Fetching...
                </span>
            </button>
        </form>
    </div>

    <!-- Result Display -->
    <div id="result" class="result-display" style="display: none;">
        <div class="card">
            <h3>Result</h3>
            <div id="result-content"></div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/fetch.js') }}"></script>
{% endblock %}
```

### Step 2: Create the JavaScript

Create `static/js/fetch.js`:

```javascript
// Handle form submission
document.getElementById('fetch-equity-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = {
        symbol: document.getElementById('symbol').value.toUpperCase(),
        from_date: document.getElementById('from_date').value,
        to_date: document.getElementById('to_date').value,
        interval: document.getElementById('interval').value,
        validate: document.getElementById('validate').checked,
        incremental: document.getElementById('incremental').checked
    };

    // Optional exchange
    const exchange = document.getElementById('exchange').value;
    if (exchange) {
        formData.exchange = exchange;
    }

    // Show loading state
    showLoading(true);
    hideResult();

    try {
        // Send POST request
        const response = await fetch('/api/data/fetch-equity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        // Hide loading
        showLoading(false);

        // Show result
        if (result.success) {
            showSuccess(result);
        } else {
            showError(result.error);
        }

    } catch (error) {
        showLoading(false);
        showError('Network error: ' + error.message);
    }
});

function showLoading(show) {
    const btnText = document.querySelector('.btn-text');
    const btnLoading = document.querySelector('.btn-loading');
    const submitBtn = document.querySelector('button[type="submit"]');

    if (show) {
        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-block';
        submitBtn.disabled = true;
    } else {
        btnText.style.display = 'inline-block';
        btnLoading.style.display = 'none';
        submitBtn.disabled = false;
    }
}

function showSuccess(result) {
    const resultDiv = document.getElementById('result');
    const contentDiv = document.getElementById('result-content');

    contentDiv.innerHTML = `
        <div class="success-message">
            <div class="success-icon">✓</div>
            <h4>Data fetched successfully!</h4>
            <div class="result-stats">
                <div class="stat">
                    <span class="stat-label">Symbol:</span>
                    <span class="stat-value">${result.symbol}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Records:</span>
                    <span class="stat-value">${result.records.toLocaleString()}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Date Range:</span>
                    <span class="stat-value">${result.date_range}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Time:</span>
                    <span class="stat-value">${result.elapsed_seconds}s</span>
                </div>
            </div>
        </div>
    `;

    resultDiv.style.display = 'block';
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showError(error) {
    const resultDiv = document.getElementById('result');
    const contentDiv = document.getElementById('result-content');

    contentDiv.innerHTML = `
        <div class="error-message">
            <div class="error-icon">✗</div>
            <h4>Error fetching data</h4>
            <p class="error-text">${error}</p>
        </div>
    `;

    resultDiv.style.display = 'block';
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideResult() {
    document.getElementById('result').style.display = 'none';
}
```

### Step 3: Create the CSS

Create `static/css/fetch.css`:

```css
/* Fetch Page Styles */
.fetch-page {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
}

.page-header {
    margin-bottom: 2rem;
}

.page-header h1 {
    color: var(--accent);
    margin-bottom: 0.5rem;
}

.page-header p {
    color: var(--text-secondary);
}

/* Card */
.card {
    background: var(--secondary);
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

/* Form Styles */
.form-group {
    margin-bottom: 1.5rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
    font-weight: 500;
}

.form-group input,
.form-group select {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--primary);
    color: var(--text-primary);
    font-size: 1rem;
}

.form-group input:focus,
.form-group select:focus {
    outline: none;
    border-color: var(--accent);
}

.form-group small {
    display: block;
    margin-top: 0.25rem;
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.checkbox {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
    cursor: pointer;
}

.checkbox input {
    width: auto;
    margin-right: 0.5rem;
}

/* Button */
.btn {
    padding: 0.75rem 2rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-primary {
    background: var(--accent);
    color: var(--primary);
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(212, 175, 55, 0.3);
}

.btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

/* Spinner */
.spinner {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    border: 2px solid var(--primary);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Result Display */
.result-display {
    margin-top: 2rem;
}

.success-message,
.error-message {
    text-align: center;
    padding: 2rem;
}

.success-icon,
.error-icon {
    width: 60px;
    height: 60px;
    margin: 0 auto 1rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    font-weight: bold;
}

.success-icon {
    background: var(--success);
    color: white;
}

.error-icon {
    background: var(--error);
    color: white;
}

.result-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-top: 1.5rem;
    text-align: left;
}

.stat {
    padding: 1rem;
    background: var(--primary);
    border-radius: 8px;
}

.stat-label {
    display: block;
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-bottom: 0.25rem;
}

.stat-value {
    display: block;
    color: var(--accent);
    font-size: 1.25rem;
    font-weight: 600;
}

.error-text {
    color: var(--error);
    margin-top: 1rem;
}
```

### Step 4: Add Route

Add to `routes/dashboard.py`:

```python
@dashboard_bp.route('/fetch')
@login_required
def fetch_page():
    """Data fetching page"""
    return render_template('data/fetch.html')
```

### Step 5: Test It!

1. Run the app: `python run.py`
2. Visit: `http://localhost:5000/dashboard/fetch`
3. Fill in the form:
   - Symbol: `RELIANCE`
   - From: `2024-01-01`
   - To: `2024-12-31`
4. Click "Fetch Data"
5. See the results!

**🎉 Congratulations!** You just built a complete data fetching UI!

---

## Add a New API Endpoint

Let's add an endpoint to check existing data range.

### Step 1: Add Route Handler

In `routes/data_api.py`, add:

```python
@data_api_bp.route('/check-data/<exchange>/<symbol>/<interval>')
@login_required
def check_existing_data(exchange: str, symbol: str, interval: str):
    """
    Check if data exists and return date range

    Example: GET /api/data/check-data/NSE/RELIANCE/day
    """
    try:
        # Get access token
        access_token = session.get('access_token')

        # Create service
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Check existing range
        date_range = data_fetcher.get_existing_data_range(
            exchange=exchange.upper(),
            symbol=symbol.upper(),
            interval=interval
        )

        if date_range:
            start_date, end_date = date_range
            return jsonify({
                'success': True,
                'exists': True,
                'exchange': exchange.upper(),
                'symbol': symbol.upper(),
                'interval': interval,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_days': (end_date - start_date).days
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'exchange': exchange.upper(),
                'symbol': symbol.upper(),
                'interval': interval,
                'message': 'No data found'
            })

    except Exception as e:
        logger.error(f'Error checking data: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Step 2: Test the Endpoint

```bash
# Using cURL
curl http://localhost:5000/api/data/check-data/NSE/RELIANCE/day

# Response
{
  "success": true,
  "exists": true,
  "exchange": "NSE",
  "symbol": "RELIANCE",
  "interval": "day",
  "start_date": "2020-01-01",
  "end_date": "2024-10-07",
  "total_days": 1741
}
```

### Step 3: Use in Frontend

Add to `fetch.js`:

```javascript
// Check existing data before fetching
async function checkExistingData(exchange, symbol, interval) {
    try {
        const url = `/api/data/check-data/${exchange}/${symbol}/${interval}`;
        const response = await fetch(url);
        const result = await response.json();

        if (result.success && result.exists) {
            showInfo(`
                Data exists from ${result.start_date} to ${result.end_date}.
                Incremental fetch will only get new data.
            `);
        } else {
            showInfo('No existing data found. Full fetch will be performed.');
        }

    } catch (error) {
        console.error('Error checking data:', error);
    }
}

// Call when symbol is entered
document.getElementById('symbol').addEventListener('blur', () => {
    const symbol = document.getElementById('symbol').value;
    const exchange = document.getElementById('exchange').value || 'NSE';
    const interval = document.getElementById('interval').value;

    if (symbol) {
        checkExistingData(exchange, symbol, interval);
    }
});
```

**🎉 You added a new API endpoint!**

---

## Create a New Page

Let's create a database statistics page.

### Step 1: Create Template

Create `templates/dashboard/stats.html`:

```html
{% extends "base.html" %}

{% block title %}Database Statistics - {{ app_name }}{% endblock %}

{% block content %}
<div class="stats-page">
    <div class="page-header">
        <h1>Database Statistics</h1>
        <p>View storage and data statistics</p>
    </div>

    <!-- Segment Grid -->
    <div class="segments-grid">
        {% for segment in segments %}
        <div class="segment-card card">
            <h2>{{ segment }}</h2>

            {% if segment in db_info and not db_info[segment].get('error') %}
            <div class="segment-stats">
                <div class="stat-item">
                    <span class="stat-icon">📊</span>
                    <div class="stat-info">
                        <span class="stat-label">Datasets</span>
                        <span class="stat-value">{{ db_info[segment].total_datasets }}</span>
                    </div>
                </div>

                <div class="stat-item">
                    <span class="stat-icon">💾</span>
                    <div class="stat-info">
                        <span class="stat-label">Size</span>
                        <span class="stat-value">{{ db_info[segment].size_mb | format_size }}</span>
                    </div>
                </div>

                <div class="stat-item">
                    <span class="stat-icon">🏢</span>
                    <div class="stat-info">
                        <span class="stat-label">Exchanges</span>
                        <span class="stat-value">{{ db_info[segment].exchanges | join(', ') }}</span>
                    </div>
                </div>
            </div>

            <div class="segment-actions">
                <a href="{{ url_for('dashboard.browse_segment', segment=segment) }}"
                   class="btn btn-sm">Browse Data</a>
            </div>
            {% else %}
            <p class="empty-state">No data available</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

### Step 2: Add Route

In `routes/dashboard.py`:

```python
@dashboard_bp.route('/stats')
@login_required
def stats():
    """Database statistics page"""
    # Get access token
    access_token = session.get('access_token')

    # Create data fetcher
    data_fetcher = create_data_fetcher(
        api_key=current_app.config['KITE_API_KEY'],
        access_token=access_token
    )

    # Get database info for all segments
    db_info = {}
    for segment in current_app.config['SEGMENTS']:
        db_info[segment] = data_fetcher.get_database_info(segment)

    return render_template('dashboard/stats.html', db_info=db_info)
```

### Step 3: Add CSS

In `static/css/dashboard.css`:

```css
.stats-page {
    padding: 2rem;
}

.segments-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.segment-card {
    background: var(--secondary);
    border-radius: 12px;
    padding: 2rem;
}

.segment-card h2 {
    color: var(--accent);
    margin-bottom: 1.5rem;
}

.segment-stats {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.stat-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: var(--primary);
    border-radius: 8px;
}

.stat-icon {
    font-size: 2rem;
}

.stat-info {
    display: flex;
    flex-direction: column;
}

.stat-label {
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.stat-value {
    color: var(--text-primary);
    font-size: 1.25rem;
    font-weight: 600;
}

.segment-actions {
    margin-top: 1.5rem;
    display: flex;
    gap: 1rem;
}

.btn-sm {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
}

.empty-state {
    color: var(--text-secondary);
    text-align: center;
    padding: 2rem;
}
```

### Step 4: Add Navigation Link

In `templates/components/navbar.html`:

```html
<nav class="navbar">
    <a href="{{ url_for('dashboard.index') }}">Dashboard</a>
    <a href="{{ url_for('dashboard.fetch_page') }}">Fetch Data</a>
    <a href="{{ url_for('dashboard.stats') }}">Statistics</a>
    <a href="{{ url_for('auth.logout') }}">Logout</a>
</nav>
```

**🎉 You created a new page!**

---

## Add Real-Time Progress

Let's add a progress indicator for batch fetching.

### Step 1: Update Template

Add progress bar to `fetch.html`:

```html
<!-- Progress Display -->
<div id="progress-section" style="display: none;">
    <div class="card progress-card">
        <h3>Fetching Data...</h3>
        <div class="progress-bar">
            <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
        </div>
        <p id="progress-text">Processing...</p>
    </div>
</div>
```

### Step 2: Update JavaScript

Add to `fetch.js`:

```javascript
async function fetchBatch(requests) {
    // Show progress
    showProgress(true);
    updateProgress(0, requests.length, 'Starting batch fetch...');

    try {
        const response = await fetch('/api/data/fetch-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ requests })
        });

        const result = await response.json();

        // Update progress for each request
        result.results.forEach((r, idx) => {
            updateProgress(idx + 1, requests.length,
                `Fetched ${r.symbol} (${r.success ? 'Success' : 'Failed'})`);
        });

        // Hide progress
        showProgress(false);

        // Show summary
        showBatchSummary(result);

    } catch (error) {
        showProgress(false);
        showError('Batch fetch error: ' + error.message);
    }
}

function showProgress(show) {
    const progressSection = document.getElementById('progress-section');
    progressSection.style.display = show ? 'block' : 'none';
}

function updateProgress(current, total, message) {
    const percentage = (current / total) * 100;
    document.getElementById('progress-fill').style.width = percentage + '%';
    document.getElementById('progress-text').textContent =
        `${current}/${total} - ${message}`;
}

function showBatchSummary(result) {
    const html = `
        <div class="batch-summary">
            <h3>Batch Complete</h3>
            <div class="summary-stats">
                <div class="summary-stat success">
                    <span class="stat-number">${result.successful}</span>
                    <span class="stat-label">Successful</span>
                </div>
                <div class="summary-stat failed">
                    <span class="stat-number">${result.failed}</span>
                    <span class="stat-label">Failed</span>
                </div>
                <div class="summary-stat rate">
                    <span class="stat-number">${result.success_rate}%</span>
                    <span class="stat-label">Success Rate</span>
                </div>
            </div>
        </div>
    `;

    document.getElementById('result-content').innerHTML = html;
    document.getElementById('result').style.display = 'block';
}
```

### Step 3: Add CSS

```css
.progress-card {
    margin-top: 2rem;
}

.progress-bar {
    width: 100%;
    height: 30px;
    background: var(--primary);
    border-radius: 15px;
    overflow: hidden;
    margin: 1rem 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--success));
    transition: width 0.3s ease;
}

#progress-text {
    text-align: center;
    color: var(--text-secondary);
}

.batch-summary {
    text-align: center;
    padding: 2rem;
}

.summary-stats {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 2rem;
}

.summary-stat {
    padding: 1.5rem;
    border-radius: 12px;
    min-width: 120px;
}

.summary-stat.success {
    background: rgba(16, 185, 129, 0.1);
}

.summary-stat.failed {
    background: rgba(220, 38, 38, 0.1);
}

.summary-stat.rate {
    background: rgba(212, 175, 55, 0.1);
}

.stat-number {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
}

.stat-label {
    display: block;
    margin-top: 0.5rem;
    color: var(--text-secondary);
    font-size: 0.875rem;
}
```

**🎉 You added real-time progress tracking!**

---

## Style with Your Color Palette

Your app has a beautiful color palette defined. Let's use it!

### Your Colors (from CLAUDE.md)

```css
/* static/css/variables.css */
:root {
    /* Primary Colors */
    --primary: #0A0E27;        /* Deep navy - almost black */
    --accent: #D4AF37;         /* Muted gold */
    --accent-alt: #C9A961;     /* Champagne gold */
    --secondary: #1A1F3A;      /* Charcoal navy */

    /* Text Colors */
    --text-primary: #F8FAFC;   /* Off-white */
    --text-secondary: #94A3B8; /* Cool gray */

    /* Status Colors */
    --success: #10B981;        /* Emerald green - wealth signal */
    --error: #DC2626;          /* Deep red */
    --warning: #F59E0B;        /* Amber */
    --info: #3B82F6;           /* Blue */

    /* UI Elements */
    --border: #334155;         /* Subtle slate */
    --border-light: #475569;   /* Lighter slate */

    /* Shadows */
    --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.4);

    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;

    /* Border Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
}
```

### Global Styles

```css
/* static/css/global.css */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    background: var(--primary);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.6;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-md);
}

h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
h3 { font-size: 1.5rem; }

p {
    margin-bottom: var(--spacing-md);
}

a {
    color: var(--accent);
    text-decoration: none;
    transition: color 0.3s;
}

a:hover {
    color: var(--accent-alt);
}

/* Container */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--spacing-lg);
}

/* Buttons */
.btn {
    display: inline-block;
    padding: var(--spacing-sm) var(--spacing-lg);
    border: none;
    border-radius: var(--radius-md);
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-primary {
    background: var(--accent);
    color: var(--primary);
}

.btn-primary:hover {
    background: var(--accent-alt);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.btn-success {
    background: var(--success);
    color: white;
}

.btn-error {
    background: var(--error);
    color: white;
}

/* Cards */
.card {
    background: var(--secondary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border);
}

/* Alerts */
.alert {
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
}

.alert-success {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid var(--success);
    color: var(--success);
}

.alert-error {
    background: rgba(220, 38, 38, 0.1);
    border: 1px solid var(--error);
    color: var(--error);
}

.alert-info {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid var(--info);
    color: var(--info);
}
```

---

## Testing Your Code

### 1. Manual Testing

```bash
# Start the app
python run.py

# Test in browser
open http://localhost:5000
```

### 2. API Testing with cURL

```bash
# Test fetch equity
curl -X POST http://localhost:5000/api/data/fetch-equity \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "interval": "day"
  }'

# Test get instruments
curl http://localhost:5000/api/data/instruments/NSE?limit=10

# Test lookup
curl http://localhost:5000/api/data/lookup/NSE/RELIANCE
```

### 3. Python Testing

```python
# tests/test_data_api.py
import pytest
from flask_app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_fetch_equity(client):
    """Test fetch equity endpoint"""
    response = client.post('/api/data/fetch-equity', json={
        'symbol': 'RELIANCE',
        'from_date': '2024-01-01',
        'to_date': '2024-12-31',
        'interval': 'day'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert 'success' in data

def test_get_instruments(client):
    """Test get instruments endpoint"""
    response = client.get('/api/data/instruments/NSE')
    assert response.status_code == 200
    data = response.get_json()
    assert 'instruments' in data
```

Run tests:
```bash
pytest tests/test_data_api.py -v
```

---

## Summary

You've learned how to:

✅ **Build a complete UI** - Forms, results, styling
✅ **Add API endpoints** - RESTful routes with validation
✅ **Create new pages** - Templates, routes, navigation
✅ **Add real-time features** - Progress bars, live updates
✅ **Style with your palette** - Consistent, beautiful design
✅ **Test your code** - Manual and automated testing

---

## Next Steps

1. **Add more features:**
   - Data export (CSV, Excel, Parquet)
   - Chart visualization
   - Batch symbol upload
   - Scheduled fetching

2. **Improve UX:**
   - Auto-complete for symbols
   - Date range presets (Last 1Y, YTD, etc.)
   - Keyboard shortcuts
   - Dark/light mode toggle

3. **Optimize performance:**
   - Caching
   - Background jobs
   - WebSocket for real-time updates

4. **Deploy:**
   - Production configuration
   - HTTPS setup
   - Gunicorn + Nginx
   - Docker containerization

---

**You're now a Flask developer!** 🚀 Happy coding!

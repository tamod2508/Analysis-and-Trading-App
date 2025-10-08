# Flask Data Fetcher

A Flask-based REST API for fetching historical market data from Zerodha Kite Connect.

## Architecture

### Services Layer

#### `DataFetcherService` ([services/data_fetcher.py](services/data_fetcher.py))

Flask-compatible wrapper around the KiteClient that provides:

- **Session-based authentication** - Uses Flask session to manage access tokens
- **Error handling** - Returns user-friendly error messages
- **Multi-segment support** - Fetches equity and derivatives data
- **Batch operations** - Process multiple fetch requests in one call
- **Database integration** - Automatic storage in segment-specific HDF5 databases

**Key Methods:**

```python
# Fetch equity data (NSE/BSE)
fetch_equity(symbol, from_date, to_date, interval='day', exchange=None, ...)

# Fetch derivatives (NFO/BFO)
fetch_derivatives(exchange, symbol, from_date, to_date, interval='day', ...)

# Batch fetch
fetch_batch(requests, progress_callback=None)

# Get instruments list
get_instruments(exchange, use_cache=True, force_refresh=False)

# Lookup instrument token
lookup_instrument(exchange, symbol)

# Get existing data range
get_existing_data_range(exchange, symbol, interval)

# Get database info
get_database_info(segment='EQUITY')
```

### API Layer

#### Data API Routes ([routes/data_api.py](routes/data_api.py))

RESTful endpoints for data fetching operations.

**Base URL:** `/api/data`

---

## API Endpoints

### 1. Fetch Equity Data

**POST** `/api/data/fetch-equity`

Fetch historical equity data from NSE/BSE.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "exchange": "NSE",      // optional - auto-detects if not provided
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "interval": "day",       // minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute, day
  "validate": true,        // optional - default: true
  "overwrite": false,      // optional - default: false
  "incremental": true      // optional - default: true (only fetch missing data)
}
```

**Response:**
```json
{
  "success": true,
  "symbol": "RELIANCE",
  "interval": "day",
  "records": 248,
  "date_range": "2024-01-01 to 2024-12-31",
  "elapsed_seconds": 3.45
}
```

---

### 2. Fetch Derivatives Data

**POST** `/api/data/fetch-derivatives`

Fetch options/futures data from NFO/BFO.

**Request Body:**
```json
{
  "exchange": "NFO",
  "symbol": "NIFTY25OCT24950CE",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "interval": "day",
  "validate": true,
  "overwrite": false,
  "incremental": true
}
```

**Response:**
```json
{
  "success": true,
  "exchange": "NFO",
  "symbol": "NIFTY25OCT24950CE",
  "interval": "day",
  "records": 185,
  "date_range": "2024-01-01 to 2024-12-31",
  "elapsed_seconds": 2.78
}
```

---

### 3. Batch Fetch

**POST** `/api/data/fetch-batch`

Fetch multiple symbols in one request.

**Request Body:**
```json
{
  "requests": [
    {
      "segment": "EQUITY",
      "symbol": "RELIANCE",
      "from_date": "2024-01-01",
      "to_date": "2024-12-31",
      "interval": "day"
    },
    {
      "segment": "EQUITY",
      "symbol": "TCS",
      "from_date": "2024-01-01",
      "to_date": "2024-12-31",
      "interval": "day"
    },
    {
      "segment": "DERIVATIVES",
      "exchange": "NFO",
      "symbol": "NIFTY25OCT24950CE",
      "from_date": "2024-01-01",
      "to_date": "2024-12-31",
      "interval": "day"
    }
  ]
}
```

**Response:**
```json
{
  "total": 3,
  "successful": 3,
  "failed": 0,
  "success_rate": 100.0,
  "results": [
    {
      "success": true,
      "symbol": "RELIANCE",
      "interval": "day",
      "records": 248,
      "date_range": "2024-01-01 to 2024-12-31",
      "elapsed_seconds": 3.45
    },
    // ... more results
  ]
}
```

---

### 4. Get Instruments

**GET** `/api/data/instruments/<exchange>`

Get list of tradeable instruments for an exchange.

**Parameters:**
- `exchange` (path): NSE, BSE, NFO, or BFO
- `force_refresh` (query, optional): Force API refresh (default: false)
- `limit` (query, optional): Limit number of results

**Example:**
```bash
GET /api/data/instruments/NSE?limit=10
```

**Response:**
```json
{
  "success": true,
  "exchange": "NSE",
  "count": 10,
  "instruments": [
    {
      "instrument_token": 738561,
      "exchange_token": 2885,
      "tradingsymbol": "RELIANCE",
      "name": "RELIANCE INDUSTRIES LIMITED",
      "last_price": 2890.50,
      "expiry": "",
      "strike": 0,
      "tick_size": 0.05,
      "lot_size": 1,
      "instrument_type": "EQ",
      "segment": "NSE",
      "exchange": "NSE"
    },
    // ... more instruments
  ]
}
```

---

### 5. Lookup Instrument

**GET** `/api/data/lookup/<exchange>/<symbol>`

Get instrument token for a symbol.

**Example:**
```bash
GET /api/data/lookup/NSE/RELIANCE
```

**Response:**
```json
{
  "success": true,
  "exchange": "NSE",
  "symbol": "RELIANCE",
  "instrument_token": 738561
}
```

---

### 6. Get Database Info

**GET** `/api/data/database-info/<segment>`

Get statistics about HDF5 database.

**Parameters:**
- `segment` (path): EQUITY or DERIVATIVES

**Example:**
```bash
GET /api/data/database-info/EQUITY
```

**Response:**
```json
{
  "success": true,
  "segment": "EQUITY",
  "file_path": "/Users/atm/Desktop/kite_app/data/hdf5/EQUITY.h5",
  "exists": true,
  "size_mb": 142.35,
  "exchanges": ["NSE", "BSE"],
  "total_datasets": 1248
}
```

---

### 7. Get Existing Data Range

**GET** `/api/data/existing-range/<exchange>/<symbol>/<interval>`

Check what data already exists in the database.

**Example:**
```bash
GET /api/data/existing-range/NSE/RELIANCE/day
```

**Response:**
```json
{
  "success": true,
  "exchange": "NSE",
  "symbol": "RELIANCE",
  "interval": "day",
  "start_date": "2020-01-01",
  "end_date": "2024-10-07"
}
```

If no data exists:
```json
{
  "success": true,
  "exchange": "NSE",
  "symbol": "RELIANCE",
  "interval": "day",
  "start_date": null,
  "end_date": null,
  "message": "No existing data found"
}
```

---

## Usage Examples

### Using cURL

```bash
# Fetch equity data
curl -X POST http://localhost:5000/api/data/fetch-equity \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "interval": "day"
  }'

# Lookup instrument
curl http://localhost:5000/api/data/lookup/NSE/RELIANCE

# Get instruments
curl http://localhost:5000/api/data/instruments/NSE?limit=10

# Check existing data
curl http://localhost:5000/api/data/existing-range/NSE/RELIANCE/day
```

### Using Python `requests`

```python
import requests
from datetime import datetime

BASE_URL = "http://localhost:5000/api/data"

# Fetch equity data
response = requests.post(
    f"{BASE_URL}/fetch-equity",
    json={
        "symbol": "RELIANCE",
        "from_date": "2024-01-01",
        "to_date": "2024-12-31",
        "interval": "day"
    }
)
result = response.json()
print(f"Fetched {result['records']} records")

# Batch fetch
response = requests.post(
    f"{BASE_URL}/fetch-batch",
    json={
        "requests": [
            {
                "segment": "EQUITY",
                "symbol": "RELIANCE",
                "from_date": "2024-01-01",
                "to_date": "2024-12-31",
                "interval": "day"
            },
            {
                "segment": "EQUITY",
                "symbol": "TCS",
                "from_date": "2024-01-01",
                "to_date": "2024-12-31",
                "interval": "day"
            }
        ]
    }
)
summary = response.json()
print(f"Success rate: {summary['success_rate']}%")
```

### Using JavaScript (Fetch API)

```javascript
// Fetch equity data
async function fetchEquityData(symbol, fromDate, toDate) {
  const response = await fetch('/api/data/fetch-equity', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      symbol: symbol,
      from_date: fromDate,
      to_date: toDate,
      interval: 'day'
    })
  });

  const result = await response.json();

  if (result.success) {
    console.log(`Fetched ${result.records} records for ${symbol}`);
  } else {
    console.error(`Error: ${result.error}`);
  }

  return result;
}

// Lookup instrument
async function lookupInstrument(exchange, symbol) {
  const response = await fetch(`/api/data/lookup/${exchange}/${symbol}`);
  const result = await response.json();

  if (result.success) {
    console.log(`${symbol} token: ${result.instrument_token}`);
  }

  return result;
}

// Usage
fetchEquityData('RELIANCE', '2024-01-01', '2024-12-31');
lookupInstrument('NSE', 'RELIANCE');
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message here",
  "error_type": "auth"  // auth, api, or unknown
}
```

**Common HTTP Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Not authenticated
- `404 Not Found` - Symbol/resource not found
- `500 Internal Server Error` - Server error

---

## Features

### Incremental Updates

By default, the fetcher only retrieves missing data:

```json
{
  "symbol": "RELIANCE",
  "from_date": "2020-01-01",
  "to_date": "2024-12-31",
  "incremental": true  // Only fetch data after last stored date
}
```

If data exists from 2020-01-01 to 2024-10-07, it will only fetch from 2024-10-08 to 2024-12-31.

### Data Validation

All fetched data is validated before storage:
- Price range validation (segment-specific)
- OHLC relationship checks (low ≤ open/close ≤ high)
- Volume validation
- Date validation

Disable validation if needed:
```json
{
  "symbol": "RELIANCE",
  "validate": false
}
```

### Rate Limiting

The service automatically handles Kite API rate limits:
- 3 requests/second with safety margin
- Exponential backoff on errors
- Automatic retries

### Multi-Segment Support

Data is automatically stored in the correct segment database:
- **EQUITY.h5** - NSE & BSE stocks
- **DERIVATIVES.h5** - NFO & BFO options/futures

---

## Configuration

### Environment Variables

```bash
# .env file
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_secret
KITE_ACCESS_TOKEN=your_token

# Flask
FLASK_ENV=development  # or production
FLASK_SECRET_KEY=your_secret_key
```

### Flask Config

See [flask_app/config.py](config.py) for configuration options.

---

## Directory Structure

```
flask_app/
├── __init__.py           # Flask app factory
├── config.py             # Configuration
├── services/
│   ├── __init__.py
│   ├── data_fetcher.py   # Data fetcher service
│   └── auth_service.py   # Authentication service
├── routes/
│   ├── __init__.py
│   ├── auth.py           # Auth routes
│   ├── dashboard.py      # Dashboard routes
│   └── data_api.py       # Data API routes (REST)
└── templates/
    └── ...
```

---

## Running the Flask App

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_APP=flask_app
export FLASK_ENV=development

# Run the app
flask run

# Or use Python directly
python -m flask_app.app
```

---

## Integration with Existing Code

The Flask data fetcher integrates seamlessly with the existing Kite app:

- **Uses same KiteClient** - All existing features (rate limiting, retries, validation)
- **Same HDF5 storage** - Compatible with existing databases
- **Same configuration** - Uses shared config from `config/`
- **Same validation** - Uses DataValidator and schema definitions

You can use both Streamlit UI and Flask API simultaneously - they share the same data layer.

---

## Next Steps

1. **Add authentication UI** - Build login/logout pages
2. **Create dashboard** - Display database stats, recent fetches
3. **Add real-time progress** - WebSocket-based progress updates for batch operations
4. **Build visualization** - Charts and analysis dashboards
5. **Add export endpoints** - REST API for exporting data (CSV, Excel, Parquet)

---

## Support

For issues or questions, see:
- Main project docs: [../docs/](../docs/)
- Project structure: [../docs/PROJECT_STRUCTURE.md](../docs/PROJECT_STRUCTURE.md)
- API client docs: [../api/kite_client.py](../api/kite_client.py)

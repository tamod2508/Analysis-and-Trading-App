"""
Data Fetching API Routes
RESTful endpoints for fetching historical market data
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_required

from ..services.data_fetcher import create_data_fetcher
from utils.logger import get_logger

logger = get_logger(__name__, 'flask.log')

# Create blueprint
data_api_bp = Blueprint('data_api', __name__, url_prefix='/api/data')


@data_api_bp.route('/fetch-equity', methods=['POST'])
@login_required
def fetch_equity():
    """
    Fetch equity data endpoint

    Expected JSON payload:
    {
        "symbol": "RELIANCE",
        "exchange": "NSE",  // optional
        "from_date": "2024-01-01",
        "to_date": "2024-12-31",
        "interval": "day",
        "validate": true,
        "overwrite": false,
        "incremental": true
    }

    Returns:
        JSON response with fetch results
    """
    try:
        # Get request data
        data = request.get_json()

        # Debug: log request
        logger.info(f"Equity fetch: incremental={data.get('incremental')}, validate={data.get('validate')}")

        # Validate required fields
        required = ['symbol', 'from_date', 'to_date']
        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400

        # Parse dates
        from_date = datetime.strptime(data['from_date'], '%Y-%m-%d')
        to_date = datetime.strptime(data['to_date'], '%Y-%m-%d')

        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Get incremental flag (default to False if not provided)
        incremental = data.get('incremental', False)
        # If not incremental, enable overwrite to refetch existing data
        overwrite = data.get('overwrite', not incremental)

        # Fetch data
        result = data_fetcher.fetch_equity(
            symbol=data['symbol'].upper(),
            from_date=from_date,
            to_date=to_date,
            interval=data.get('interval', 'day'),
            exchange=data.get('exchange'),
            validate=data.get('validate', False),
            overwrite=overwrite,
            incremental=incremental
        )

        # Debug: log result types
        logger.info(f"Result keys: {result.keys()}")
        for key, value in result.items():
            logger.info(f"  {key}: {type(value)} = {value}")

        return jsonify(result)

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400

    except Exception as e:
        logger.error(f"Error fetching equity data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/fetch-derivatives', methods=['POST'])
@login_required
def fetch_derivatives():
    """
    Fetch derivatives data endpoint

    Expected JSON payload:
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

    Returns:
        JSON response with fetch results
    """
    try:
        # Get request data
        data = request.get_json()

        # Validate required fields
        required = ['exchange', 'symbol', 'from_date', 'to_date']
        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400

        # Parse dates
        from_date = datetime.strptime(data['from_date'], '%Y-%m-%d')
        to_date = datetime.strptime(data['to_date'], '%Y-%m-%d')

        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Fetch data
        result = data_fetcher.fetch_derivatives(
            exchange=data['exchange'].upper(),
            symbol=data['symbol'].upper(),
            from_date=from_date,
            to_date=to_date,
            interval=data.get('interval', 'day'),
            validate=data.get('validate', True),
            overwrite=data.get('overwrite', False),
            incremental=data.get('incremental', True)
        )

        return jsonify(result)

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400

    except Exception as e:
        logger.error(f"Error fetching derivatives data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/fetch-batch', methods=['POST'])
@login_required
def fetch_batch():
    """
    Fetch multiple symbols in batch

    Expected JSON payload:
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
                "segment": "DERIVATIVES",
                "exchange": "NFO",
                "symbol": "NIFTY25OCT24950CE",
                "from_date": "2024-01-01",
                "to_date": "2024-12-31",
                "interval": "day"
            }
        ]
    }

    Returns:
        JSON response with batch summary
    """
    try:
        # Get request data
        data = request.get_json()

        # Validate
        if 'requests' not in data or not isinstance(data['requests'], list):
            return jsonify({
                'success': False,
                'error': 'Invalid request format. Expected "requests" array'
            }), 400

        if len(data['requests']) == 0:
            return jsonify({
                'success': False,
                'error': 'No requests provided'
            }), 400

        # Parse dates in all requests
        requests = []
        for idx, req in enumerate(data['requests']):
            try:
                req_copy = req.copy()
                req_copy['from_date'] = datetime.strptime(req['from_date'], '%Y-%m-%d')
                req_copy['to_date'] = datetime.strptime(req['to_date'], '%Y-%m-%d')
                requests.append(req_copy)
            except (KeyError, ValueError) as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid request at index {idx}: {str(e)}'
                }), 400

        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Fetch batch
        summary = data_fetcher.fetch_batch(requests)

        return jsonify(summary)

    except Exception as e:
        logger.error(f"Error in batch fetch: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/instruments/<exchange>')
@login_required
def get_instruments(exchange: str):
    """
    Get list of instruments for exchange

    Query params:
        - force_refresh: Force refresh from API (default: false)
        - limit: Limit number of results (default: no limit)

    Returns:
        JSON response with instruments list
    """
    try:
        # Get query params
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        limit = request.args.get('limit', type=int)

        # Validate exchange
        valid_exchanges = ['NSE', 'BSE', 'NFO', 'BFO']
        if exchange.upper() not in valid_exchanges:
            return jsonify({
                'success': False,
                'error': f'Invalid exchange. Must be one of: {", ".join(valid_exchanges)}'
            }), 400

        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Get instruments
        instruments = data_fetcher.get_instruments(
            exchange=exchange.upper(),
            use_cache=True,
            force_refresh=force_refresh
        )

        # Apply limit if specified
        if limit and limit > 0:
            instruments = instruments[:limit]

        return jsonify({
            'success': True,
            'exchange': exchange.upper(),
            'count': len(instruments),
            'instruments': instruments
        })

    except Exception as e:
        logger.error(f"Error fetching instruments: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/lookup/<exchange>/<symbol>')
@login_required
def lookup_instrument(exchange: str, symbol: str):
    """
    Lookup instrument token for symbol

    Returns:
        JSON response with instrument token
    """
    try:
        # Validate exchange
        valid_exchanges = ['NSE', 'BSE', 'NFO', 'BFO']
        if exchange.upper() not in valid_exchanges:
            return jsonify({
                'success': False,
                'error': f'Invalid exchange. Must be one of: {", ".join(valid_exchanges)}'
            }), 400

        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Lookup instrument
        token = data_fetcher.lookup_instrument(
            exchange=exchange.upper(),
            symbol=symbol.upper()
        )

        if token:
            return jsonify({
                'success': True,
                'exchange': exchange.upper(),
                'symbol': symbol.upper(),
                'instrument_token': token
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Symbol {symbol} not found on {exchange}'
            }), 404

    except Exception as e:
        logger.error(f"Error looking up instrument: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/database-info/<segment>')
@login_required
def get_database_info(segment: str):
    """
    Get information about HDF5 database for a segment

    Returns:
        JSON response with database statistics
    """
    try:
        # Validate segment
        valid_segments = ['EQUITY', 'DERIVATIVES']
        if segment.upper() not in valid_segments:
            return jsonify({
                'success': False,
                'error': f'Invalid segment. Must be one of: {", ".join(valid_segments)}'
            }), 400

        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Get database info
        db_info = data_fetcher.get_database_info(segment.upper())

        return jsonify({
            'success': True,
            **db_info
        })

    except Exception as e:
        logger.error(f"Error getting database info: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/existing-range/<exchange>/<symbol>/<interval>')
@login_required
def get_existing_range(exchange: str, symbol: str, interval: str):
    """
    Get date range of existing data

    Returns:
        JSON response with date range or null if no data exists
    """
    try:
        # Get access token from session
        access_token = session.get('access_token')

        # Create data fetcher
        data_fetcher = create_data_fetcher(
            api_key=current_app.config['KITE_API_KEY'],
            access_token=access_token
        )

        # Get existing range
        date_range = data_fetcher.get_existing_data_range(
            exchange=exchange.upper(),
            symbol=symbol.upper(),
            interval=interval
        )

        if date_range:
            start_date, end_date = date_range
            return jsonify({
                'success': True,
                'exchange': exchange.upper(),
                'symbol': symbol.upper(),
                'interval': interval,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            })
        else:
            return jsonify({
                'success': True,
                'exchange': exchange.upper(),
                'symbol': symbol.upper(),
                'interval': interval,
                'start_date': None,
                'end_date': None,
                'message': 'No existing data found'
            })

    except Exception as e:
        logger.error(f"Error getting existing range: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_api_bp.route('/search-instruments', methods=['GET'])
@login_required
def search_instruments():
    """
    Search for instruments by name or trading symbol

    Query params:
        q: Search query (name or symbol)
        exchange: Filter by exchange (NSE, BSE, NFO, BFO)
        limit: Max results (default: 20)

    Returns:
        JSON list of matching instruments
    """
    try:
        from database.instruments_db import InstrumentsDB

        query = request.args.get('q', '').strip()
        exchange = request.args.get('exchange', '').strip().upper()
        limit = int(request.args.get('limit', 20))

        if not query or len(query) < 2:
            return jsonify([])

        db = InstrumentsDB()

        # Get instruments for the exchange (or all if not specified)
        if exchange:
            df = db.get_instruments(exchange)
        else:
            # Search across NSE and BSE for equity
            import pandas as pd
            nse_df = db.get_instruments('NSE')
            bse_df = db.get_instruments('BSE')
            df = pd.concat([nse_df, bse_df], ignore_index=True)

        if df.empty:
            return jsonify([])

        # Exclude indices (segment column contains 'NSE', 'BSE', 'INDICES')
        df = df[df['segment'] != 'INDICES']

        # Filter equity instruments only (instrument_type = 'EQ')
        # This excludes futures, options, etc.
        df = df[df['instrument_type'] == 'EQ']

        # Exclude bonds (Gold Bonds, Government Securities, T-Bills, etc.)
        # Bonds typically have -GB, -GS suffixes or contain bond keywords
        bond_patterns = (
            df['tradingsymbol'].str.contains('-GB|-GS|GSEC|TBILL', case=False, na=False) |
            df['name'].str.contains('GOLDBOND|GOI LOAN|G\.SEC|GOVT SEC|TREASURY|T-BILL|GOLD BONDS', case=False, na=False)
        )
        df = df[~bond_patterns]

        # Search by name or trading symbol (case-insensitive)
        query_lower = query.lower()
        mask = (
            df['name'].str.lower().str.contains(query_lower, na=False) |
            df['tradingsymbol'].str.lower().str.contains(query_lower, na=False)
        )

        results = df[mask].head(limit)

        # Format results
        instruments = []
        for _, row in results.iterrows():
            instruments.append({
                'symbol': row['tradingsymbol'],
                'name': row['name'],
                'exchange': row['exchange'],
                'label': f"{row['name']} ({row['tradingsymbol']}) - {row['exchange']}"
            })

        return jsonify(instruments)

    except Exception as e:
        logger.error(f"Error searching instruments: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

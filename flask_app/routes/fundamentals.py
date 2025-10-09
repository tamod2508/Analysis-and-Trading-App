"""
Fundamentals Routes
Routes for viewing company fundamental data
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from utils.logger import get_logger

logger = get_logger(__name__, 'flask.log')

# Create blueprint
fundamentals_bp = Blueprint('fundamentals', __name__, url_prefix='/fundamentals')


@fundamentals_bp.route('/')
def index():
    """
    Fundamentals home page - overview and stats
    """
    from ..services.fundamentals_service import get_fundamentals_stats, get_sector_summary

    stats = get_fundamentals_stats()
    sectors = get_sector_summary('NSE')

    return render_template('fundamentals/index.html', stats=stats, sectors=sectors)


@fundamentals_bp.route('/browse')
def browse():
    """
    Browse companies with filtering and sorting
    """
    from ..services.fundamentals_service import get_top_companies

    # Get query parameters
    exchange = request.args.get('exchange', 'NSE')
    limit = int(request.args.get('limit', 100))

    companies = get_top_companies(exchange, limit)

    return render_template('fundamentals/browse.html', companies=companies, exchange=exchange)


@fundamentals_bp.route('/company/<exchange>/<symbol>')
def view_company(exchange: str, symbol: str):
    """
    View detailed fundamental data for a specific company

    Args:
        exchange: Exchange name (NSE/BSE)
        symbol: Company symbol
    """
    from ..services.fundamentals_service import get_company_fundamentals

    data = get_company_fundamentals(exchange, symbol)

    if not data:
        return render_template('errors/404.html',
                             message=f"Company {symbol} not found on {exchange}"), 404

    return render_template('fundamentals/company.html',
                         company=data,
                         symbol=symbol,
                         exchange=exchange)


@fundamentals_bp.route('/api/search')
def search():
    """
    API endpoint for searching companies
    Returns JSON list of matching companies
    """
    from ..services.fundamentals_service import search_companies

    query = request.args.get('q', '')
    exchange = request.args.get('exchange', 'NSE')
    limit = int(request.args.get('limit', 20))

    if not query or len(query) < 2:
        return jsonify([])

    results = search_companies(query, exchange, limit)
    return jsonify(results)


@fundamentals_bp.route('/api/company/<exchange>/<symbol>/statement/<statement_type>')
def get_statement(exchange: str, symbol: str, statement_type: str):
    """
    API endpoint to get specific financial statement as JSON

    Args:
        exchange: Exchange name
        symbol: Company symbol
        statement_type: balance_sheet, income_statement, or cash_flow
    """
    from ..services.fundamentals_service import get_company_fundamentals

    period = request.args.get('period', 'yearly')  # yearly or quarterly

    data = get_company_fundamentals(exchange, symbol)

    if not data:
        return jsonify({'error': 'Company not found'}), 404

    key = f"{statement_type}_{period}"
    if key not in data or data[key] is None:
        return jsonify({'error': 'Statement not available'}), 404

    # Convert DataFrame to dict for JSON serialization
    df = data[key]
    result = {
        'dates': df['date'].tolist() if 'date' in df.columns else [],
        'data': df.to_dict('records')
    }

    return jsonify(result)

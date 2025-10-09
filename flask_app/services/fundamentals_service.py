"""
Fundamentals Service
Business logic for fundamental data management
"""

from pathlib import Path
from typing import Dict, List, Optional
import os
import pandas as pd

# Import fundamentals manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.fundamentals_manager import FundamentalsManager
from utils.logger import get_logger

logger = get_logger(__name__, 'fundamentals.log')


def get_fundamentals_stats() -> Dict:
    """
    Get statistics for fundamentals database

    Returns:
        Dict containing database statistics
    """
    try:
        manager = FundamentalsManager()
        stats = manager.get_statistics()

        # Get database file path and size
        base_dir = Path(__file__).parent.parent.parent
        db_path = base_dir / 'data' / 'hdf5' / 'FUNDAMENTALS.h5'

        size_mb = 0
        is_active = False

        if db_path.exists():
            size_mb = os.path.getsize(db_path) / (1024**2)
            is_active = stats.get('total_companies', 0) > 0

        return {
            'description': 'Company Fundamental Data',
            'size_mb': size_mb,
            'total_companies': stats.get('total_companies', 0),
            'nse_companies': stats.get('nse_companies', 0),
            'bse_companies': stats.get('bse_companies', 0),
            'is_active': is_active,
            'status': 'Active' if is_active else 'Empty',
            'database_version': stats.get('version', 'Unknown'),
        }
    except Exception as e:
        logger.error(f"Error getting fundamentals stats: {e}")
        return {
            'description': 'Company Fundamental Data',
            'size_mb': 0,
            'total_companies': 0,
            'nse_companies': 0,
            'bse_companies': 0,
            'is_active': False,
            'status': 'Error',
            'database_version': 'Unknown',
        }


def get_company_list(exchange: str = 'NSE', limit: Optional[int] = None) -> List[str]:
    """
    Get list of companies in database

    Args:
        exchange: Exchange name (NSE or BSE)
        limit: Optional limit on number of companies

    Returns:
        List of company symbols
    """
    try:
        manager = FundamentalsManager()
        companies = manager.list_companies(exchange)

        if limit:
            companies = companies[:limit]

        return companies
    except Exception as e:
        logger.error(f"Error getting company list for {exchange}: {e}")
        return []


def get_company_fundamentals(exchange: str, symbol: str) -> Optional[Dict]:
    """
    Get fundamental data for a specific company

    Args:
        exchange: Exchange name (NSE or BSE)
        symbol: Company symbol

    Returns:
        Dict containing company fundamentals or None if not found
    """
    try:
        manager = FundamentalsManager()
        data = manager.get_company_fundamentals(exchange, symbol)

        if not data:
            return None

        # Convert NumPy arrays to list of dicts for JSON serialization
        result = {
            'general': data['general'],
            'highlights': data['highlights'],
        }

        # Convert financial statement arrays to list of dicts
        for stmt_type in ['balance_sheet', 'income_statement', 'cash_flow']:
            for period in ['yearly', 'quarterly']:
                key = f"{stmt_type}_{period}"
                if key in data and data[key] is not None:
                    # Convert structured NumPy array to list of dicts
                    arr = data[key]
                    if len(arr) > 0:
                        # Get field names from dtype
                        fields = arr.dtype.names
                        # Convert to list of dicts
                        result[key] = []
                        for row in arr:
                            row_dict = {}
                            for field in fields:
                                value = row[field]
                                # Convert bytes to string
                                if isinstance(value, bytes):
                                    value = value.decode('utf-8')
                                # Convert numpy types to Python types
                                elif hasattr(value, 'item'):
                                    value = value.item()
                                row_dict[field] = value
                            result[key].append(row_dict)
                    else:
                        result[key] = []
                else:
                    result[key] = []

        return result

    except Exception as e:
        logger.error(f"Error getting fundamentals for {exchange}:{symbol}: {e}")
        return None


def search_companies(query: str, exchange: str = 'NSE', limit: int = 50) -> List[Dict]:
    """
    Search for companies by symbol or name

    Args:
        query: Search query (symbol or name)
        exchange: Exchange to search in
        limit: Maximum results to return

    Returns:
        List of matching companies with basic info
    """
    try:
        manager = FundamentalsManager()
        companies = manager.list_companies(exchange)

        # Filter by query (case-insensitive symbol match)
        query_upper = query.upper()
        matches = []

        for symbol in companies:
            if query_upper in symbol.upper():
                try:
                    data = manager.get_company_fundamentals(exchange, symbol)
                    if data:
                        matches.append({
                            'symbol': symbol,
                            'name': data['general'].get('name', symbol),
                            'sector': data['general'].get('sector', 'N/A'),
                            'industry': data['general'].get('industry', 'N/A'),
                            'market_cap': data['highlights'].get('market_cap', 0),
                        })
                except Exception as e:
                    logger.debug(f"Error loading {symbol}: {e}")
                    continue

            if len(matches) >= limit:
                break

        return matches

    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        return []


def get_sector_summary(exchange: str = 'NSE') -> Dict[str, int]:
    """
    Get summary of companies by sector

    Args:
        exchange: Exchange name

    Returns:
        Dict mapping sector names to company counts
    """
    try:
        manager = FundamentalsManager()
        companies = manager.list_companies(exchange)

        sectors = {}

        for symbol in companies:
            try:
                data = manager.get_company_fundamentals(exchange, symbol)
                if data:
                    sector = data['general'].get('sector', 'Unknown')
                    sectors[sector] = sectors.get(sector, 0) + 1
            except Exception as e:
                logger.debug(f"Error loading sector for {symbol}: {e}")
                continue

        return dict(sorted(sectors.items(), key=lambda x: x[1], reverse=True))

    except Exception as e:
        logger.error(f"Error getting sector summary: {e}")
        return {}


def get_top_companies(exchange: str = 'NSE', limit: int = 100) -> List[Dict]:
    """
    Get top companies with basic metrics

    Args:
        exchange: Exchange name
        limit: Number of companies to return

    Returns:
        List of companies with basic info
    """
    try:
        manager = FundamentalsManager()
        companies = manager.list_companies(exchange)

        company_list = []

        for symbol in companies[:limit]:
            try:
                data = manager.get_company_fundamentals(exchange, symbol)
                if data:
                    company_list.append({
                        'symbol': symbol,
                        'name': data['general'].get('name', symbol),
                        'sector': data['general'].get('sector', 'N/A'),
                        'industry': data['general'].get('industry', 'N/A'),
                        'market_cap': data['highlights'].get('market_cap', 0),
                        'pe_ratio': data['highlights'].get('pe_ratio', 0),
                        'dividend_yield': data['highlights'].get('dividend_yield', 0),
                    })
            except Exception as e:
                logger.debug(f"Error loading {symbol}: {e}")
                continue

        # Sort by market cap (descending)
        company_list.sort(key=lambda x: x.get('market_cap', 0), reverse=True)

        return company_list

    except Exception as e:
        logger.error(f"Error getting top companies: {e}")
        return []

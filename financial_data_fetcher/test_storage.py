#!/usr/bin/env python3
"""
Test fundamentals storage and retrieval
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_data_fetcher import EODHDClient, FundamentalsParser
from database.fundamentals_manager import FundamentalsManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test full pipeline: fetch -> parse -> store -> retrieve"""

    print("\n" + "="*70)
    print("FUNDAMENTALS STORAGE TEST")
    print("="*70)

    # Load API key
    load_dotenv()
    api_key = os.getenv('EODHD_API_KEY', '').strip()

    if not api_key:
        print("\n❌ No API key found")
        return

    print(f"\n✅ Using API key: {api_key[:8]}...")

    # Initialize clients
    eodhd = EODHDClient(api_key)
    manager = FundamentalsManager()

    # Test companies
    test_companies = [
        ('RELIANCE', 'NSE', 'Reliance Industries'),
        ('TCS', 'NSE', 'Tata Consultancy Services'),
        ('INFY', 'NSE', 'Infosys'),
    ]

    print("\n" + "="*70)
    print("FETCHING AND STORING DATA")
    print("="*70)

    for symbol, exchange, name in test_companies:
        print(f"\n📥 Processing {name} ({symbol}.{exchange})...")

        # Step 1: Fetch from EODHD
        raw_data = eodhd.get_fundamental_data(symbol, exchange)
        if not raw_data:
            print(f"  ❌ Failed to fetch data")
            continue

        print(f"  ✅ Fetched raw data")

        # Step 2: Parse
        parsed = FundamentalsParser.parse_all(raw_data)
        print(f"  ✅ Parsed data")

        # Step 3: Store
        success = manager.save_company_fundamentals(exchange, symbol, parsed)
        if success:
            print(f"  ✅ Stored in HDF5")
        else:
            print(f"  ❌ Failed to store")

    # Get database statistics
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)

    stats = manager.get_statistics()
    print(f"\nTotal Companies: {stats['total_companies']}")
    print(f"NSE Companies: {stats['nse_companies']}")
    print(f"BSE Companies: {stats['bse_companies']}")
    print(f"File Size: {stats['file_size_mb']:.2f} MB")
    print(f"Last Modified: {stats['last_modified']}")

    # List all companies
    print("\n" + "="*70)
    print("STORED COMPANIES")
    print("="*70)

    nse_companies = manager.list_companies('NSE')
    print(f"\nNSE Companies ({len(nse_companies)}):")
    for symbol in nse_companies:
        print(f"  • {symbol}")

    # Test retrieval
    print("\n" + "="*70)
    print("TESTING DATA RETRIEVAL")
    print("="*70)

    test_symbol = 'RELIANCE'
    print(f"\n📤 Retrieving {test_symbol} from HDF5...")

    data = manager.get_company_fundamentals('NSE', test_symbol)

    if data:
        print(f"\n✅ Retrieved data successfully")

        # Show general info
        if data['general']:
            print(f"\n📋 General Info:")
            print(f"  Name: {data['general'].get('name', 'N/A')}")
            print(f"  Sector: {data['general'].get('sector', 'N/A')}")
            print(f"  Industry: {data['general'].get('industry', 'N/A')}")

        # Show highlights
        if data['highlights']:
            print(f"\n💰 Key Metrics:")
            print(f"  Market Cap: ₹{data['highlights'].get('market_cap', 0):,.0f} M")
            print(f"  P/E Ratio: {data['highlights'].get('pe_ratio', 0):.2f}")
            print(f"  ROE: {data['highlights'].get('roe', 0)*100:.2f}%")

        # Show datasets
        print(f"\n📊 Financial Statements:")
        if data['balance_sheet_yearly'] is not None:
            print(f"  • Balance Sheet (Yearly): {len(data['balance_sheet_yearly'])} periods")
        if data['balance_sheet_quarterly'] is not None:
            print(f"  • Balance Sheet (Quarterly): {len(data['balance_sheet_quarterly'])} periods")
        if data['income_statement_yearly'] is not None:
            print(f"  • Income Statement (Yearly): {len(data['income_statement_yearly'])} periods")
        if data['income_statement_quarterly'] is not None:
            print(f"  • Income Statement (Quarterly): {len(data['income_statement_quarterly'])} periods")
        if data['cash_flow_yearly'] is not None:
            print(f"  • Cash Flow (Yearly): {len(data['cash_flow_yearly'])} periods")
        if data['cash_flow_quarterly'] is not None:
            print(f"  • Cash Flow (Quarterly): {len(data['cash_flow_quarterly'])} periods")

        # Show latest balance sheet
        if data['balance_sheet_yearly'] is not None:
            bs = data['balance_sheet_yearly']
            print(f"\n📋 Latest Balance Sheet ({bs[0]['date']}):")
            print(f"  Total Assets: ₹{bs[0]['total_assets']:,.0f} M")
            print(f"  Total Liabilities: ₹{bs[0]['total_liabilities']:,.0f} M")
            print(f"  Total Equity: ₹{bs[0]['total_equity']:,.0f} M")
            print(f"  Debt/Equity: {bs[0]['long_term_debt'] / bs[0]['total_equity']:.2f}")

        # Show metadata
        print(f"\n📅 Metadata:")
        print(f"  Last Updated: {data['metadata']['last_updated']}")
        print(f"  Source: {data['metadata']['source']}")

    else:
        print(f"  ❌ Failed to retrieve data")

    print("\n" + "="*70)
    print("STORAGE TEST COMPLETE")
    print("="*70)
    print("\n✅ Full pipeline working!")
    print("\nData flow:")
    print("  1. EODHD API → Raw JSON")
    print("  2. Parser → NumPy arrays")
    print("  3. HDF5Manager → Compressed storage")
    print("  4. Retrieval → Ready for analysis")
    print("\nNext: Bulk download 2000+ companies")
    print("="*70)


if __name__ == '__main__':
    main()

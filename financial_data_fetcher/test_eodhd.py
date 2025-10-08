#!/usr/bin/env python3
"""
Test EODHD API Integration
Run this to verify your API key and check coverage
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_data_fetcher.eodhd_client import EODHDClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test EODHD API with your key"""

    print("\n" + "="*70)
    print("EODHD API TEST")
    print("="*70)

    # Try to get API key from environment first
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('EODHD_API_KEY', '').strip()

    if not api_key:
        # Fall back to interactive input
        try:
            api_key = input("\nEnter your EODHD API key: ").strip()
        except EOFError:
            print("\n❌ No API key found in EODHD_API_KEY environment variable")
            print("Please add to .env file: EODHD_API_KEY=your_key_here")
            print("Or run: python3 setup_eodhd.py")
            return
    else:
        print(f"\n✅ Using API key from environment: {api_key[:8]}...")

    if not api_key:
        print("❌ API key required")
        return

    # Initialize client
    try:
        client = EODHDClient(api_key)
        print("✅ Client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return

    # Test 1: Get NSE symbols
    print("\n" + "="*70)
    print("TEST 1: Fetch NSE Symbols List")
    print("="*70)

    try:
        symbols = client.get_exchange_symbols('NSE')
        print(f"✅ Found {len(symbols)} NSE tickers")
        print(f"\nSample companies:")
        for ticker in symbols[:5]:
            print(f"  • {ticker['Code']}: {ticker['Name']}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return

    # Test 2: Get fundamental data for major companies
    print("\n" + "="*70)
    print("TEST 2: Fetch Fundamental Data (Sample Companies)")
    print("="*70)

    test_companies = [
        ('RELIANCE', 'NSE', 'Reliance Industries'),
        ('TCS', 'NSE', 'Tata Consultancy Services'),
        ('INFY', 'NSE', 'Infosys'),
    ]

    results = []

    for symbol, exchange, name in test_companies:
        print(f"\nTesting {name} ({symbol}.{exchange})...")

        try:
            data = client.get_fundamental_data(symbol, exchange)

            if data:
                # Check what data is available
                has_financials = 'Financials' in data
                has_highlights = 'Highlights' in data

                result = {
                    'symbol': f"{symbol}.{exchange}",
                    'name': name,
                    'has_data': True,
                    'has_financials': has_financials,
                    'has_highlights': has_highlights
                }

                if has_highlights:
                    highlights = data['Highlights']
                    result['market_cap'] = highlights.get('MarketCapitalization')
                    result['revenue'] = highlights.get('RevenueTTM')
                    result['ebitda'] = highlights.get('EBITDA')
                    result['eps'] = highlights.get('EarningsPerShareTTM')

                if has_financials:
                    financials = data['Financials']
                    if 'Balance_Sheet' in financials and 'yearly' in financials['Balance_Sheet']:
                        result['years_of_data'] = len(financials['Balance_Sheet']['yearly'])

                results.append(result)

                print(f"  ✅ Data available")
                if 'years_of_data' in result:
                    print(f"  📊 {result['years_of_data']} years of financial history")
                if 'market_cap' in result:
                    print(f"  💰 Market Cap: ₹{result['market_cap']} M")
                if 'revenue' in result:
                    print(f"  📈 Revenue: ₹{result['revenue']} M")

            else:
                results.append({
                    'symbol': f"{symbol}.{exchange}",
                    'name': name,
                    'has_data': False
                })
                print(f"  ⚠️ No fundamental data available")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'symbol': f"{symbol}.{exchange}",
                'name': name,
                'error': str(e)
            })

    # Test 3: Coverage estimation
    print("\n" + "="*70)
    print("TEST 3: Estimate NSE Coverage")
    print("="*70)

    try:
        stats = client.get_coverage_stats('NSE')
        print(f"\n✅ Coverage estimation complete")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    success_count = sum(1 for r in results if r.get('has_data', False))
    total_tested = len(results)

    print(f"\nCompanies Tested: {total_tested}")
    print(f"With Fundamental Data: {success_count}/{total_tested}")

    if success_count == total_tested:
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"\nYour EODHD API is working correctly!")
        print(f"\nNext steps:")
        print(f"  1. Download fundamentals for all companies")
        print(f"  2. Parse and store in HDF5")
        print(f"  3. Calculate financial ratios")
        print(f"  4. Start training ML models!")
    elif success_count > 0:
        print(f"\n⚠️ PARTIAL SUCCESS")
        print(f"Some companies have data, but not all.")
    else:
        print(f"\n❌ TESTS FAILED")
        print(f"No fundamental data available. Check your API key or subscription.")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()

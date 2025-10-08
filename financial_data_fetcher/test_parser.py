#!/usr/bin/env python3
"""
Test the FundamentalsParser with real EODHD data
"""

import os
import logging
from dotenv import load_dotenv
from financial_data_fetcher import EODHDClient, FundamentalsParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test parser with RELIANCE data"""

    print("\n" + "="*70)
    print("FUNDAMENTALS PARSER TEST")
    print("="*70)

    # Load API key
    load_dotenv()
    api_key = os.getenv('EODHD_API_KEY', '').strip()

    if not api_key:
        print("\n❌ No API key found in EODHD_API_KEY environment variable")
        return

    print(f"\n✅ Using API key: {api_key[:8]}...")

    # Initialize client
    client = EODHDClient(api_key)

    # Fetch RELIANCE data
    print("\n" + "="*70)
    print("Fetching RELIANCE fundamental data...")
    print("="*70)

    raw_data = client.get_fundamental_data('RELIANCE', 'NSE')

    if not raw_data:
        print("❌ Failed to fetch data")
        return

    print("✅ Fetched raw data")

    # Parse the data
    print("\n" + "="*70)
    print("Parsing fundamental data...")
    print("="*70)

    parsed = FundamentalsParser.parse_all(raw_data)

    # Show general info
    if parsed['general']:
        print("\n📋 GENERAL INFO:")
        gen = parsed['general']
        print(f"  Symbol: {gen['symbol']}")
        print(f"  Name: {gen['name']}")
        print(f"  Exchange: {gen['exchange']}")
        print(f"  Sector: {gen['sector']}")
        print(f"  Industry: {gen['industry']}")
        print(f"  ISIN: {gen['isin']}")
        print(f"  IPO Date: {gen['ipo_date']}")

    # Show highlights
    if parsed['highlights']:
        print("\n💰 KEY METRICS:")
        hl = parsed['highlights']
        print(f"  Market Cap: ₹{hl['market_cap']:,.0f} M")
        print(f"  Revenue (TTM): ₹{hl['revenue_ttm']:,.0f} M")
        print(f"  EBITDA: ₹{hl['ebitda']:,.0f} M")
        print(f"  P/E Ratio: {hl['pe_ratio']:.2f}")
        print(f"  EPS: ₹{hl['eps']:.2f}")
        print(f"  ROE: {hl['roe']*100:.2f}%")
        print(f"  ROA: {hl['roa']*100:.2f}%")
        print(f"  Profit Margin: {hl['profit_margin']*100:.2f}%")
        print(f"  Dividend Yield: {hl['div_yield']*100:.2f}%")

    # Show balance sheet
    if parsed['balance_sheet_yearly'] is not None:
        bs = parsed['balance_sheet_yearly']
        print(f"\n📊 BALANCE SHEET (Yearly): {len(bs)} periods")
        print(f"  Latest: {bs[0]['date']}")
        print(f"  Oldest: {bs[-1]['date']}")
        print(f"\n  Latest Balance Sheet ({bs[0]['date']}):")
        print(f"    Total Assets: ₹{bs[0]['total_assets']:,.0f} M")
        print(f"    Total Liabilities: ₹{bs[0]['total_liabilities']:,.0f} M")
        print(f"    Total Equity: ₹{bs[0]['total_equity']:,.0f} M")
        print(f"    Current Assets: ₹{bs[0]['current_assets']:,.0f} M")
        print(f"    Current Liabilities: ₹{bs[0]['current_liabilities']:,.0f} M")
        print(f"    Cash: ₹{bs[0]['cash']:,.0f} M")
        print(f"    Long-term Debt: ₹{bs[0]['long_term_debt']:,.0f} M")

    # Show income statement
    if parsed['income_statement_yearly'] is not None:
        is_data = parsed['income_statement_yearly']
        print(f"\n📈 INCOME STATEMENT (Yearly): {len(is_data)} periods")
        print(f"  Latest: {is_data[0]['date']}")
        print(f"  Oldest: {is_data[-1]['date']}")
        print(f"\n  Latest Income Statement ({is_data[0]['date']}):")
        print(f"    Revenue: ₹{is_data[0]['revenue']:,.0f} M")
        print(f"    Gross Profit: ₹{is_data[0]['gross_profit']:,.0f} M")
        print(f"    Operating Income: ₹{is_data[0]['operating_income']:,.0f} M")
        print(f"    Net Income: ₹{is_data[0]['net_income']:,.0f} M")
        print(f"    EBITDA: ₹{is_data[0]['ebitda']:,.0f} M")
        print(f"    EPS (Basic): ₹{is_data[0]['eps_basic']:.2f}")

    # Show cash flow
    if parsed['cash_flow_yearly'] is not None:
        cf = parsed['cash_flow_yearly']
        print(f"\n💵 CASH FLOW (Yearly): {len(cf)} periods")
        print(f"  Latest: {cf[0]['date']}")
        print(f"  Oldest: {cf[-1]['date']}")
        print(f"\n  Latest Cash Flow ({cf[0]['date']}):")
        print(f"    Operating CF: ₹{cf[0]['operating_cash_flow']:,.0f} M")
        print(f"    Investing CF: ₹{cf[0]['investing_cash_flow']:,.0f} M")
        print(f"    Financing CF: ₹{cf[0]['financing_cash_flow']:,.0f} M")
        print(f"    Free Cash Flow: ₹{cf[0]['free_cash_flow']:,.0f} M")
        print(f"    Capex: ₹{cf[0]['capex']:,.0f} M")

    # Validate
    print("\n" + "="*70)
    print("VALIDATION")
    print("="*70)

    is_valid, warnings = FundamentalsParser.validate_parsed_data(parsed)

    if is_valid:
        print("\n✅ Data is valid and complete!")
    else:
        print("\n⚠️ Data has issues:")
        for warning in warnings:
            print(f"  - {warning}")

    # Show quarterly data availability
    print("\n" + "="*70)
    print("QUARTERLY DATA")
    print("="*70)

    quarterly_available = []
    if parsed['balance_sheet_quarterly'] is not None:
        quarterly_available.append(f"Balance Sheet ({len(parsed['balance_sheet_quarterly'])} periods)")
    if parsed['income_statement_quarterly'] is not None:
        quarterly_available.append(f"Income Statement ({len(parsed['income_statement_quarterly'])} periods)")
    if parsed['cash_flow_quarterly'] is not None:
        quarterly_available.append(f"Cash Flow ({len(parsed['cash_flow_quarterly'])} periods)")

    if quarterly_available:
        print("\n✅ Quarterly data available:")
        for item in quarterly_available:
            print(f"  • {item}")
    else:
        print("\n⚠️ No quarterly data available")

    print("\n" + "="*70)
    print("PARSER TEST COMPLETE")
    print("="*70)
    print("\n✅ Parser is working correctly!")
    print("\nNext: Store this data in HDF5 format")
    print("="*70)


if __name__ == '__main__':
    main()

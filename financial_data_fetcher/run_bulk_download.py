#!/usr/bin/env python3
"""
Non-interactive bulk downloader
Run in background: python3 run_bulk_download.py NSE 0 2000
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_data_fetcher.bulk_downloader import BulkDownloader


def main():
    """Run bulk download with command-line arguments"""

    # Load API key
    load_dotenv()
    api_key = os.getenv('EODHD_API_KEY', '').strip()

    if not api_key:
        print("❌ No API key found")
        sys.exit(1)

    # Parse arguments
    exchange = sys.argv[1] if len(sys.argv) > 1 else 'NSE'
    start_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    max_companies = int(sys.argv[3]) if len(sys.argv) > 3 else None

    print(f"\n{'='*70}")
    print("BULK DOWNLOAD - NON-INTERACTIVE MODE")
    print(f"{'='*70}")
    print(f"Exchange: {exchange}")
    print(f"Start Index: {start_index}")
    print(f"Max Companies: {max_companies or 'All (~2000)'}")
    print(f"{'='*70}\n")

    # Run download
    downloader = BulkDownloader(api_key)
    downloader.download_all(
        exchange=exchange,
        start_index=start_index,
        max_companies=max_companies,
        skip_existing=True
    )


if __name__ == '__main__':
    main()

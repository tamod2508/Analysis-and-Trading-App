#!/usr/bin/env python3
"""
Quick setup script for EODHD API integration
Adds your API key to .env file and runs initial tests
"""

import os
from pathlib import Path


def main():
    print("\n" + "="*70)
    print("EODHD API SETUP")
    print("="*70)

    env_file = Path("/Users/atm/Desktop/kite_app/.env")

    # Check if key already exists
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if 'EODHD_API_KEY' in content:
                print("\n✅ EODHD_API_KEY already exists in .env")
                print("\nIf you need to update it, edit .env manually")
                print("\nReady to run tests!")
                print("\nRun this command:")
                print("  python3 financial_data_fetcher/test_eodhd.py")
                return

    print("\nThis will add your EODHD API key to your .env file")
    print("Get your API key from: https://eodhd.com/cp/dashboard")

    api_key = input("\nEnter your EODHD API key (or press Enter to skip): ").strip()

    if not api_key:
        print("\n⚠️ Skipped. You can add it manually to .env:")
        print("  EODHD_API_KEY=your_api_key_here")
        return

    # Append to .env
    with open(env_file, 'a') as f:
        f.write(f"\n# EODHD API for fundamental data\n")
        f.write(f"EODHD_API_KEY={api_key}\n")

    print("\n✅ Added EODHD_API_KEY to .env")
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Test your API key:")
    print("   python3 financial_data_fetcher/test_eodhd.py")
    print("\n2. After tests pass, start bulk download")
    print("\n" + "="*70)


if __name__ == '__main__':
    main()

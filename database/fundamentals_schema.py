"""
HDF5 Schema for Fundamental Data Storage

Structure for FUNDAMENTALS.h5:
/
├── companies/
│   ├── NSE/
│   │   └── {SYMBOL}/        (e.g., RELIANCE)
│   │       ├── general      (company info - dict attributes)
│   │       ├── highlights   (current metrics - dict attributes)
│   │       ├── balance_sheet_yearly
│   │       ├── balance_sheet_quarterly
│   │       ├── income_statement_yearly
│   │       ├── income_statement_quarterly
│   │       ├── cash_flow_yearly
│   │       └── cash_flow_quarterly
│   └── BSE/
│       └── {SYMBOL}/
│           └── ... (same structure)
└── metadata/
    ├── last_updated     (timestamp of last bulk update)
    ├── symbols_count    (number of companies)
    └── coverage_stats   (exchange-wise coverage)

Storage Strategy:
- One HDF5 file: FUNDAMENTALS.h5
- Group per company: /companies/{EXCHANGE}/{SYMBOL}/
- NumPy structured arrays for financial statements
- Company info and metrics stored as HDF5 attributes
- Optimized for: Time-series analysis, backtesting, ML training
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class BalanceSheetSchema:
    """
    Schema for Balance Sheet data (yearly or quarterly)
    """
    DTYPE = np.dtype([
        ('date', 'S10'),               # YYYY-MM-DD (bytes for HDF5 compatibility)
        ('total_assets', 'f8'),
        ('total_liabilities', 'f8'),
        ('total_equity', 'f8'),
        ('current_assets', 'f8'),
        ('current_liabilities', 'f8'),
        ('cash', 'f8'),
        ('short_term_investments', 'f8'),
        ('net_receivables', 'f8'),
        ('inventory', 'f8'),
        ('other_current_assets', 'f8'),
        ('long_term_investments', 'f8'),
        ('ppe_net', 'f8'),             # Property, Plant & Equipment
        ('goodwill', 'f8'),
        ('intangible_assets', 'f8'),
        ('other_assets', 'f8'),
        ('short_term_debt', 'f8'),
        ('long_term_debt', 'f8'),
        ('accounts_payable', 'f8'),
        ('deferred_revenue', 'f8'),
        ('other_current_liabilities', 'f8'),
        ('other_liabilities', 'f8'),
        ('common_stock', 'f8'),
        ('retained_earnings', 'f8'),
        ('treasury_stock', 'f8'),
        ('capital_surplus', 'f8'),
    ])

    REQUIRED_FIELDS = ['date', 'total_assets', 'total_liabilities', 'total_equity']


@dataclass
class IncomeStatementSchema:
    """
    Schema for Income Statement data (yearly or quarterly)
    """
    DTYPE = np.dtype([
        ('date', 'S10'),
        ('revenue', 'f8'),
        ('cost_of_revenue', 'f8'),
        ('gross_profit', 'f8'),
        ('operating_expenses', 'f8'),
        ('operating_income', 'f8'),
        ('ebitda', 'f8'),
        ('ebit', 'f8'),
        ('interest_expense', 'f8'),
        ('income_before_tax', 'f8'),
        ('income_tax', 'f8'),
        ('net_income', 'f8'),
        ('net_income_continuing', 'f8'),
        ('eps_basic', 'f8'),
        ('eps_diluted', 'f8'),
        ('weighted_avg_shares', 'f8'),
        ('weighted_avg_shares_diluted', 'f8'),
        ('research_development', 'f8'),
        ('selling_general_admin', 'f8'),
        ('depreciation', 'f8'),
        ('other_operating_expenses', 'f8'),
    ])

    REQUIRED_FIELDS = ['date', 'revenue', 'net_income']


@dataclass
class CashFlowSchema:
    """
    Schema for Cash Flow Statement data (yearly or quarterly)
    """
    DTYPE = np.dtype([
        ('date', 'S10'),
        ('operating_cash_flow', 'f8'),
        ('investing_cash_flow', 'f8'),
        ('financing_cash_flow', 'f8'),
        ('net_change_cash', 'f8'),
        ('free_cash_flow', 'f8'),
        ('capex', 'f8'),
        ('dividends_paid', 'f8'),
        ('depreciation', 'f8'),
        ('change_working_capital', 'f8'),
        ('stock_based_comp', 'f8'),
        ('change_receivables', 'f8'),
        ('change_inventory', 'f8'),
        ('change_payables', 'f8'),
        ('investments', 'f8'),
        ('other_investing_activities', 'f8'),
        ('net_borrowings', 'f8'),
        ('other_financing_activities', 'f8'),
    ])

    REQUIRED_FIELDS = ['date', 'operating_cash_flow', 'free_cash_flow']


@dataclass
class CompanyGeneralInfo:
    """
    Company general information (stored as HDF5 attributes)
    """
    FIELDS = [
        'symbol',
        'name',
        'exchange',
        'sector',
        'industry',
        'isin',
        'currency',
        'description',
        'ipo_date',
    ]


@dataclass
class CompanyHighlights:
    """
    Current financial metrics (stored as HDF5 attributes)
    """
    FIELDS = [
        'market_cap',
        'ebitda',
        'pe_ratio',
        'peg_ratio',
        'book_value',
        'div_share',
        'div_yield',
        'eps',
        'revenue_per_share',
        'profit_margin',
        'operating_margin',
        'roe',
        'roa',
        'revenue_ttm',
        'gross_profit_ttm',
    ]


class FundamentalsHDF5Structure:
    """
    Defines hierarchical structure for FUNDAMENTALS.h5
    """

    # Root groups
    ROOT_GROUPS = [
        '/companies',
        '/metadata',
    ]

    # Exchange subgroups
    EXCHANGE_GROUPS = [
        '/companies/NSE',
        '/companies/BSE',
    ]

    # Dataset names within company group
    DATASETS = [
        'balance_sheet_yearly',
        'balance_sheet_quarterly',
        'income_statement_yearly',
        'income_statement_quarterly',
        'cash_flow_yearly',
        'cash_flow_quarterly',
    ]

    @staticmethod
    def get_company_group_path(exchange: str, symbol: str) -> str:
        """
        Get HDF5 path for company group

        Args:
            exchange: NSE or BSE
            symbol: Company symbol (e.g., RELIANCE)

        Returns:
            Path like: /companies/NSE/RELIANCE
        """
        return f"/companies/{exchange}/{symbol}"

    @staticmethod
    def get_dataset_path(exchange: str, symbol: str, dataset: str) -> str:
        """
        Get HDF5 path for specific dataset

        Args:
            exchange: NSE or BSE
            symbol: Company symbol
            dataset: Dataset name (e.g., 'balance_sheet_yearly')

        Returns:
            Path like: /companies/NSE/RELIANCE/balance_sheet_yearly
        """
        return f"/companies/{exchange}/{symbol}/{dataset}"

    @staticmethod
    def validate_structure(file_handle) -> bool:
        """
        Validate FUNDAMENTALS.h5 has correct structure

        Args:
            file_handle: Open h5py.File object

        Returns:
            True if valid structure
        """
        try:
            # Check root groups exist
            for group in FundamentalsHDF5Structure.ROOT_GROUPS:
                if group not in file_handle:
                    return False

            # Check exchange groups exist
            for group in FundamentalsHDF5Structure.EXCHANGE_GROUPS:
                if group not in file_handle:
                    return False

            return True

        except Exception:
            return False


# Schema mapping for easy access
SCHEMA_MAP = {
    'balance_sheet_yearly': BalanceSheetSchema.DTYPE,
    'balance_sheet_quarterly': BalanceSheetSchema.DTYPE,
    'income_statement_yearly': IncomeStatementSchema.DTYPE,
    'income_statement_quarterly': IncomeStatementSchema.DTYPE,
    'cash_flow_yearly': CashFlowSchema.DTYPE,
    'cash_flow_quarterly': CashFlowSchema.DTYPE,
}


def get_schema_for_dataset(dataset_name: str) -> Optional[np.dtype]:
    """
    Get NumPy dtype for a dataset

    Args:
        dataset_name: Name like 'balance_sheet_yearly'

    Returns:
        NumPy dtype or None if not found
    """
    return SCHEMA_MAP.get(dataset_name)

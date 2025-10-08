"""
EODHD Data Parser
Converts EODHD JSON responses into structured NumPy arrays for HDF5 storage
"""

import numpy as np
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class FundamentalsParser:
    """
    Parses EODHD fundamental data into structured NumPy arrays

    EODHD Response Structure:
    {
        "General": {...},
        "Highlights": {...},
        "Valuation": {...},
        "Financials": {
            "Balance_Sheet": {
                "yearly": {...},
                "quarterly": {...}
            },
            "Income_Statement": {
                "yearly": {...},
                "quarterly": {...}
            },
            "Cash_Flow": {
                "yearly": {...},
                "quarterly": {...}
            }
        },
        "Earnings": {...},
        "SharesStats": {...},
        "Technicals": {...}
    }
    """

    @staticmethod
    def parse_general_info(data: Dict) -> Optional[Dict]:
        """
        Extract general company information

        Returns:
            Dict with: symbol, name, exchange, sector, industry, description
        """
        try:
            general = data.get('General', {})

            return {
                'symbol': general.get('Code', ''),
                'name': general.get('Name', ''),
                'exchange': general.get('Exchange', ''),
                'sector': general.get('Sector', ''),
                'industry': general.get('Industry', ''),
                'isin': general.get('ISIN', ''),
                'currency': general.get('CurrencyCode', 'INR'),
                'description': general.get('Description', ''),
                'ipo_date': general.get('IPODate', ''),
            }
        except Exception as e:
            logger.error(f"Error parsing general info: {e}")
            return None

    @staticmethod
    def parse_highlights(data: Dict) -> Optional[Dict]:
        """
        Extract key financial highlights/metrics

        Returns:
            Dict with current metrics: market_cap, pe_ratio, eps, etc.
        """
        try:
            highlights = data.get('Highlights', {})

            return {
                'market_cap': float(highlights.get('MarketCapitalization', 0) or 0),
                'ebitda': float(highlights.get('EBITDA', 0) or 0),
                'pe_ratio': float(highlights.get('PERatio', 0) or 0),
                'peg_ratio': float(highlights.get('PEGRatio', 0) or 0),
                'book_value': float(highlights.get('BookValue', 0) or 0),
                'div_share': float(highlights.get('DividendShare', 0) or 0),
                'div_yield': float(highlights.get('DividendYield', 0) or 0),
                'eps': float(highlights.get('EarningsShare', 0) or 0),
                'revenue_per_share': float(highlights.get('RevenueShare', 0) or 0),
                'profit_margin': float(highlights.get('ProfitMargin', 0) or 0),
                'operating_margin': float(highlights.get('OperatingMarginTTM', 0) or 0),
                'roe': float(highlights.get('ReturnOnEquityTTM', 0) or 0),
                'roa': float(highlights.get('ReturnOnAssetsTTM', 0) or 0),
                'revenue_ttm': float(highlights.get('RevenueTTM', 0) or 0),
                'gross_profit_ttm': float(highlights.get('GrossProfitTTM', 0) or 0),
            }
        except Exception as e:
            logger.error(f"Error parsing highlights: {e}")
            return None

    @staticmethod
    def parse_balance_sheet(data: Dict, period: str = 'yearly') -> Optional[np.ndarray]:
        """
        Parse balance sheet data into NumPy structured array

        Args:
            data: EODHD response dict
            period: 'yearly' or 'quarterly'

        Returns:
            NumPy structured array with balance sheet items
        """
        try:
            bs_data = data.get('Financials', {}).get('Balance_Sheet', {}).get(period, {})

            if not bs_data:
                return None

            # Get all dates and sort
            dates = sorted(bs_data.keys(), reverse=True)

            if not dates:
                return None

            # Define dtype for balance sheet
            dtype = np.dtype([
                ('date', 'S10'),  # bytes for HDF5 compatibility
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
                ('ppe_net', 'f8'),  # Property, Plant & Equipment
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

            # Parse each period
            records = []
            for date in dates:
                period_data = bs_data[date]

                record = (
                    date.encode('utf-8'),  # Convert to bytes
                    float(period_data.get('totalAssets', 0) or 0),
                    float(period_data.get('totalLiab', 0) or 0),
                    float(period_data.get('totalStockholderEquity', 0) or 0),
                    float(period_data.get('totalCurrentAssets', 0) or 0),
                    float(period_data.get('totalCurrentLiabilities', 0) or 0),
                    float(period_data.get('cash', 0) or 0),
                    float(period_data.get('shortTermInvestments', 0) or 0),
                    float(period_data.get('netReceivables', 0) or 0),
                    float(period_data.get('inventory', 0) or 0),
                    float(period_data.get('otherCurrentAssets', 0) or 0),
                    float(period_data.get('longTermInvestments', 0) or 0),
                    float(period_data.get('propertyPlantEquipment', 0) or 0),
                    float(period_data.get('goodWill', 0) or 0),
                    float(period_data.get('intangibleAssets', 0) or 0),
                    float(period_data.get('otherAssets', 0) or 0),
                    float(period_data.get('shortTermDebt', 0) or 0),
                    float(period_data.get('longTermDebt', 0) or 0),
                    float(period_data.get('accountsPayable', 0) or 0),
                    float(period_data.get('deferredLongTermLiab', 0) or 0),
                    float(period_data.get('otherCurrentLiab', 0) or 0),
                    float(period_data.get('otherLiab', 0) or 0),
                    float(period_data.get('commonStock', 0) or 0),
                    float(period_data.get('retainedEarnings', 0) or 0),
                    float(period_data.get('treasuryStock', 0) or 0),
                    float(period_data.get('capitalSurplus', 0) or 0),
                )
                records.append(record)

            return np.array(records, dtype=dtype)

        except Exception as e:
            logger.error(f"Error parsing balance sheet ({period}): {e}")
            return None

    @staticmethod
    def parse_income_statement(data: Dict, period: str = 'yearly') -> Optional[np.ndarray]:
        """
        Parse income statement data into NumPy structured array

        Args:
            data: EODHD response dict
            period: 'yearly' or 'quarterly'

        Returns:
            NumPy structured array with income statement items
        """
        try:
            is_data = data.get('Financials', {}).get('Income_Statement', {}).get(period, {})

            if not is_data:
                return None

            dates = sorted(is_data.keys(), reverse=True)

            if not dates:
                return None

            # Define dtype for income statement
            dtype = np.dtype([
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

            # Parse each period
            records = []
            for date in dates:
                period_data = is_data[date]

                record = (
                    date.encode('utf-8'),
                    float(period_data.get('totalRevenue', 0) or 0),
                    float(period_data.get('costOfRevenue', 0) or 0),
                    float(period_data.get('grossProfit', 0) or 0),
                    float(period_data.get('totalOperatingExpenses', 0) or 0),
                    float(period_data.get('operatingIncome', 0) or 0),
                    float(period_data.get('ebitda', 0) or 0),
                    float(period_data.get('ebit', 0) or 0),
                    float(period_data.get('interestExpense', 0) or 0),
                    float(period_data.get('incomeBeforeTax', 0) or 0),
                    float(period_data.get('incomeTaxExpense', 0) or 0),
                    float(period_data.get('netIncome', 0) or 0),
                    float(period_data.get('netIncomeFromContinuingOps', 0) or 0),
                    float(period_data.get('basicEPS', 0) or 0),
                    float(period_data.get('dilutedEPS', 0) or 0),
                    float(period_data.get('weightedAverageShsOut', 0) or 0),
                    float(period_data.get('weightedAverageShsOutDil', 0) or 0),
                    float(period_data.get('researchDevelopment', 0) or 0),
                    float(period_data.get('sellingGeneralAdministrative', 0) or 0),
                    float(period_data.get('depreciation', 0) or 0),
                    float(period_data.get('otherOperatingExpenses', 0) or 0),
                )
                records.append(record)

            return np.array(records, dtype=dtype)

        except Exception as e:
            logger.error(f"Error parsing income statement ({period}): {e}")
            return None

    @staticmethod
    def parse_cash_flow(data: Dict, period: str = 'yearly') -> Optional[np.ndarray]:
        """
        Parse cash flow statement data into NumPy structured array

        Args:
            data: EODHD response dict
            period: 'yearly' or 'quarterly'

        Returns:
            NumPy structured array with cash flow items
        """
        try:
            cf_data = data.get('Financials', {}).get('Cash_Flow', {}).get(period, {})

            if not cf_data:
                return None

            dates = sorted(cf_data.keys(), reverse=True)

            if not dates:
                return None

            # Define dtype for cash flow statement
            dtype = np.dtype([
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

            # Parse each period
            records = []
            for date in dates:
                period_data = cf_data[date]

                record = (
                    date.encode('utf-8'),
                    float(period_data.get('totalCashFromOperatingActivities', 0) or 0),
                    float(period_data.get('totalCashflowsFromInvestingActivities', 0) or 0),
                    float(period_data.get('totalCashFromFinancingActivities', 0) or 0),
                    float(period_data.get('changeInCash', 0) or 0),
                    float(period_data.get('freeCashFlow', 0) or 0),
                    float(period_data.get('capitalExpenditures', 0) or 0),
                    float(period_data.get('dividendsPaid', 0) or 0),
                    float(period_data.get('depreciation', 0) or 0),
                    float(period_data.get('changeToNetincome', 0) or 0),
                    float(period_data.get('stockBasedCompensation', 0) or 0),
                    float(period_data.get('changeReceivables', 0) or 0),
                    float(period_data.get('changeToInventory', 0) or 0),
                    float(period_data.get('changeToAccountReceivables', 0) or 0),
                    float(period_data.get('investments', 0) or 0),
                    float(period_data.get('otherCashflowsFromInvestingActivities', 0) or 0),
                    float(period_data.get('netBorrowings', 0) or 0),
                    float(period_data.get('otherCashflowsFromFinancingActivities', 0) or 0),
                )
                records.append(record)

            return np.array(records, dtype=dtype)

        except Exception as e:
            logger.error(f"Error parsing cash flow ({period}): {e}")
            return None

    @classmethod
    def parse_all(cls, data: Dict) -> Dict:
        """
        Parse all financial data from EODHD response

        Args:
            data: Full EODHD fundamental data response

        Returns:
            Dict with:
                - general: Company info
                - highlights: Current metrics
                - balance_sheet_yearly: NumPy array
                - balance_sheet_quarterly: NumPy array
                - income_statement_yearly: NumPy array
                - income_statement_quarterly: NumPy array
                - cash_flow_yearly: NumPy array
                - cash_flow_quarterly: NumPy array
        """
        return {
            'general': cls.parse_general_info(data),
            'highlights': cls.parse_highlights(data),
            'balance_sheet_yearly': cls.parse_balance_sheet(data, 'yearly'),
            'balance_sheet_quarterly': cls.parse_balance_sheet(data, 'quarterly'),
            'income_statement_yearly': cls.parse_income_statement(data, 'yearly'),
            'income_statement_quarterly': cls.parse_income_statement(data, 'quarterly'),
            'cash_flow_yearly': cls.parse_cash_flow(data, 'yearly'),
            'cash_flow_quarterly': cls.parse_cash_flow(data, 'quarterly'),
        }

    @staticmethod
    def validate_parsed_data(parsed: Dict) -> Tuple[bool, List[str]]:
        """
        Validate parsed data for completeness

        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []

        if not parsed.get('general'):
            warnings.append("Missing general company info")

        if not parsed.get('highlights'):
            warnings.append("Missing financial highlights")

        # Check if we have at least one financial statement
        has_financials = any([
            parsed.get('balance_sheet_yearly') is not None,
            parsed.get('income_statement_yearly') is not None,
            parsed.get('cash_flow_yearly') is not None,
        ])

        if not has_financials:
            warnings.append("No yearly financial statements available")

        is_valid = len(warnings) == 0

        return is_valid, warnings

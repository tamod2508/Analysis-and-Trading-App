"""
Fundamental Analysis Metrics Calculator

This module provides comprehensive financial metric calculations organized by category.

ORIGINAL METRICS (2024):
- Liquidity Ratios (4 metrics)
- Leverage/Solvency Ratios (5 metrics)
- Efficiency Ratios (8 metrics)
- Profitability Margins (5 metrics)
- Return Metrics (7 metrics + DuPont)
- Growth Metrics (YoY + CAGR)
- Per-Share Metrics (5 metrics)
- Quality Scores (Piotroski, Altman Z-Score)

NEW METRICS (2025):
- Cash Flow Quality (5 metrics) - Earnings quality assessment
- Shareholder Value (5 metrics) - Dividends, buybacks, total yield
- Balance Sheet Quality (6 metrics) - Asset quality, net debt, leverage
- Valuation Metrics (8 metrics) - P/E, P/B, P/S, EV/EBITDA, yields
- Working Capital (4 metrics) - Operational efficiency
- Detailed Profitability (5 metrics) - R&D, SG&A, tax, NOPAT
- Competitive Advantage (4 metrics) - Moat indicators, ROIC spread
- Enhanced Quality Scores (4 scores) - Beneish, Sloan, Ohlson, Zmijewski

TOTAL: 70+ financial metrics

Each class takes raw financial statement data and calculates derived metrics.
Designed for batch processing and storage in QuestDB time-series database.

Usage:
    from analysis.analysis_metrics import FinancialData, ComprehensiveMetricsCalculator

    # Create financial data object
    data = FinancialData.from_dict(raw_data)

    # Calculate all metrics
    metrics = ComprehensiveMetricsCalculator.calculate_all_metrics(
        current=current_period,
        previous=previous_period,  # Optional
        historical=historical_periods,  # Optional
        earnings_growth_rate=10.5,  # Optional (for PEG ratio)
        wacc=12.0,  # Optional (for ROIC spread)
        margins_5y=[...],  # Optional (for stability)
        revenues_5y=[...]  # Optional (for consistency)
    )
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
import numpy as np
from datetime import datetime


@dataclass
class FinancialData:
    """
    Container for raw financial statement data from a single period
    """
    # Balance Sheet
    total_assets: float
    total_liabilities: float
    total_equity: float
    current_assets: float
    current_liabilities: float
    cash: float
    short_term_investments: float
    inventory: float
    receivables: float
    accounts_payable: float
    short_term_debt: float
    long_term_debt: float
    intangible_assets: float
    goodwill: float
    ppe_net: float  # Property, Plant & Equipment

    # Income Statement
    revenue: float
    cost_of_revenue: float
    gross_profit: float
    operating_expenses: float
    operating_income: float
    ebitda: float
    ebit: float
    interest_expense: float
    income_before_tax: float
    income_tax: float
    net_income: float
    eps_diluted: float

    # Cash Flow
    operating_cash_flow: float
    investing_cash_flow: float
    financing_cash_flow: float
    free_cash_flow: float
    capex: float

    # Share Data
    shares_outstanding: float

    # Metadata (required fields - must come before optional fields)
    date: datetime
    symbol: str
    period_type: str  # 'yearly' or 'quarterly'

    # Shareholder Returns (Optional)
    dividends_paid: float = 0.0
    share_buybacks: float = 0.0  # Net buybacks (buybacks - issuances)

    # Market Data (Optional - for valuation metrics)
    market_price: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None

    # Additional Fields
    retained_earnings: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    rd_expense: Optional[float] = None  # R&D expense
    sga_expense: Optional[float] = None  # Selling, General & Administrative
    num_employees: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'FinancialData':
        """
        Create FinancialData from dictionary (e.g., from EODHD JSON)

        Handles missing values by setting to None/0.0
        """
        def safe_float(value, default=0.0):
            if value is None or value == 'None':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        return cls(
            # Balance Sheet
            total_assets=safe_float(data.get('total_assets')),
            total_liabilities=safe_float(data.get('total_liabilities')),
            total_equity=safe_float(data.get('total_equity')),
            current_assets=safe_float(data.get('current_assets')),
            current_liabilities=safe_float(data.get('current_liabilities')),
            cash=safe_float(data.get('cash')),
            short_term_investments=safe_float(data.get('short_term_investments')),
            inventory=safe_float(data.get('inventory')),
            receivables=safe_float(data.get('receivables')),
            accounts_payable=safe_float(data.get('accounts_payable')),
            short_term_debt=safe_float(data.get('short_term_debt')),
            long_term_debt=safe_float(data.get('long_term_debt')),
            intangible_assets=safe_float(data.get('intangible_assets')),
            goodwill=safe_float(data.get('goodwill')),
            ppe_net=safe_float(data.get('ppe_net')),

            # Income Statement
            revenue=safe_float(data.get('revenue')),
            cost_of_revenue=safe_float(data.get('cost_of_revenue')),
            gross_profit=safe_float(data.get('gross_profit')),
            operating_expenses=safe_float(data.get('operating_expenses')),
            operating_income=safe_float(data.get('operating_income')),
            ebitda=safe_float(data.get('ebitda')),
            ebit=safe_float(data.get('ebit')),
            interest_expense=safe_float(data.get('interest_expense')),
            income_before_tax=safe_float(data.get('income_before_tax')),
            income_tax=safe_float(data.get('income_tax')),
            net_income=safe_float(data.get('net_income')),
            eps_diluted=safe_float(data.get('eps_diluted')),

            # Cash Flow
            operating_cash_flow=safe_float(data.get('operating_cash_flow')),
            investing_cash_flow=safe_float(data.get('investing_cash_flow')),
            financing_cash_flow=safe_float(data.get('financing_cash_flow')),
            free_cash_flow=safe_float(data.get('free_cash_flow')),
            capex=safe_float(data.get('capex')),

            # Share Data
            shares_outstanding=safe_float(data.get('shares_outstanding')),

            # Metadata (required)
            date=data.get('date'),
            symbol=data.get('symbol', ''),
            period_type=data.get('period_type', 'yearly'),

            # Shareholder Returns (optional)
            dividends_paid=safe_float(data.get('dividends_paid')),
            share_buybacks=safe_float(data.get('share_buybacks')),

            # Market Data (optional)
            market_price=safe_float(data.get('market_price')) if data.get('market_price') else None,
            market_cap=safe_float(data.get('market_cap')) if data.get('market_cap') else None,
            enterprise_value=safe_float(data.get('enterprise_value')) if data.get('enterprise_value') else None,

            # Additional Fields (optional)
            retained_earnings=safe_float(data.get('retained_earnings')) if data.get('retained_earnings') else None,
            depreciation_amortization=safe_float(data.get('depreciation_amortization')) if data.get('depreciation_amortization') else None,
            rd_expense=safe_float(data.get('rd_expense')) if data.get('rd_expense') else None,
            sga_expense=safe_float(data.get('sga_expense')) if data.get('sga_expense') else None,
            num_employees=int(data.get('num_employees')) if data.get('num_employees') else None
        )


class LiquidityMetrics:
    """
    Liquidity ratios measure a company's ability to pay short-term obligations
    """

    @staticmethod
    def current_ratio(data: FinancialData) -> Optional[float]:
        """
        Current Ratio = Current Assets / Current Liabilities

        Measures ability to pay short-term obligations.
        > 1.5 is generally healthy, < 1.0 may indicate liquidity issues.
        """
        if data.current_liabilities == 0:
            return None
        return data.current_assets / data.current_liabilities

    @staticmethod
    def quick_ratio(data: FinancialData) -> Optional[float]:
        """
        Quick Ratio = (Current Assets - Inventory) / Current Liabilities

        More conservative than current ratio (excludes inventory).
        > 1.0 is generally healthy.
        """
        if data.current_liabilities == 0:
            return None
        return (data.current_assets - data.inventory) / data.current_liabilities

    @staticmethod
    def cash_ratio(data: FinancialData) -> Optional[float]:
        """
        Cash Ratio = (Cash + Short-term Investments) / Current Liabilities

        Most conservative liquidity ratio.
        > 0.5 is generally healthy.
        """
        if data.current_liabilities == 0:
            return None
        return (data.cash + data.short_term_investments) / data.current_liabilities

    @staticmethod
    def working_capital(data: FinancialData) -> float:
        """
        Working Capital = Current Assets - Current Liabilities

        Absolute measure of liquidity (not a ratio).
        Positive is healthy, negative may indicate issues.
        """
        return data.current_assets - data.current_liabilities

    @staticmethod
    def calculate_all(data: FinancialData) -> Dict[str, Optional[float]]:
        """Calculate all liquidity metrics"""
        return {
            'current_ratio': LiquidityMetrics.current_ratio(data),
            'quick_ratio': LiquidityMetrics.quick_ratio(data),
            'cash_ratio': LiquidityMetrics.cash_ratio(data),
            'working_capital': LiquidityMetrics.working_capital(data),
        }


class LeverageMetrics:
    """
    Leverage/Solvency ratios measure a company's debt levels and ability to meet long-term obligations
    """

    @staticmethod
    def debt_to_equity(data: FinancialData) -> Optional[float]:
        """
        Debt-to-Equity = Total Debt / Total Equity

        Measures financial leverage.
        < 1.0 is conservative, 1.0-2.0 is moderate, > 2.0 is aggressive.
        """
        if data.total_equity == 0:
            return None
        total_debt = data.short_term_debt + data.long_term_debt
        return total_debt / data.total_equity

    @staticmethod
    def debt_to_assets(data: FinancialData) -> Optional[float]:
        """
        Debt-to-Assets = Total Debt / Total Assets

        Measures proportion of assets financed by debt.
        < 0.3 is low, 0.3-0.6 is moderate, > 0.6 is high.
        """
        if data.total_assets == 0:
            return None
        total_debt = data.short_term_debt + data.long_term_debt
        return total_debt / data.total_assets

    @staticmethod
    def equity_ratio(data: FinancialData) -> Optional[float]:
        """
        Equity Ratio = Total Equity / Total Assets

        Measures proportion of assets financed by equity.
        Higher is better (less leveraged).
        """
        if data.total_assets == 0:
            return None
        return data.total_equity / data.total_assets

    @staticmethod
    def interest_coverage(data: FinancialData) -> Optional[float]:
        """
        Interest Coverage = EBIT / Interest Expense

        Measures ability to pay interest obligations.
        > 2.5 is healthy, < 1.5 may indicate distress.
        """
        if data.interest_expense == 0:
            return None
        return data.ebit / data.interest_expense

    @staticmethod
    def debt_service_coverage(data: FinancialData) -> Optional[float]:
        """
        Debt Service Coverage = Operating Cash Flow / Total Debt

        Measures ability to service total debt from operating cash flow.
        > 1.25 is healthy.
        """
        total_debt = data.short_term_debt + data.long_term_debt
        if total_debt == 0:
            return None
        return data.operating_cash_flow / total_debt

    @staticmethod
    def calculate_all(data: FinancialData) -> Dict[str, Optional[float]]:
        """Calculate all leverage metrics"""
        return {
            'debt_to_equity': LeverageMetrics.debt_to_equity(data),
            'debt_to_assets': LeverageMetrics.debt_to_assets(data),
            'equity_ratio': LeverageMetrics.equity_ratio(data),
            'interest_coverage': LeverageMetrics.interest_coverage(data),
            'debt_service_coverage': LeverageMetrics.debt_service_coverage(data),
        }


class EfficiencyMetrics:
    """
    Efficiency/Activity ratios measure how effectively a company uses its assets
    """

    @staticmethod
    def asset_turnover(data: FinancialData, avg_total_assets: float) -> Optional[float]:
        """
        Asset Turnover = Revenue / Average Total Assets

        Measures efficiency of asset utilization.
        Higher is better. Varies by industry.
        """
        if avg_total_assets == 0:
            return None
        return data.revenue / avg_total_assets

    @staticmethod
    def inventory_turnover(data: FinancialData, avg_inventory: float) -> Optional[float]:
        """
        Inventory Turnover = Cost of Revenue / Average Inventory

        Measures how quickly inventory is sold.
        Higher is generally better (faster turnover).
        """
        if avg_inventory == 0:
            return None
        return data.cost_of_revenue / avg_inventory

    @staticmethod
    def days_inventory_outstanding(data: FinancialData, avg_inventory: float) -> Optional[float]:
        """
        Days Inventory Outstanding (DIO) = 365 / Inventory Turnover

        Average days inventory sits before being sold.
        Lower is better.
        """
        turnover = EfficiencyMetrics.inventory_turnover(data, avg_inventory)
        if turnover is None or turnover == 0:
            return None
        return 365 / turnover

    @staticmethod
    def receivables_turnover(data: FinancialData, avg_receivables: float) -> Optional[float]:
        """
        Receivables Turnover = Revenue / Average Receivables

        Measures how quickly receivables are collected.
        Higher is better.
        """
        if avg_receivables == 0:
            return None
        return data.revenue / avg_receivables

    @staticmethod
    def days_sales_outstanding(data: FinancialData, avg_receivables: float) -> Optional[float]:
        """
        Days Sales Outstanding (DSO) = 365 / Receivables Turnover

        Average days to collect payment.
        Lower is better (faster collection).
        """
        turnover = EfficiencyMetrics.receivables_turnover(data, avg_receivables)
        if turnover is None or turnover == 0:
            return None
        return 365 / turnover

    @staticmethod
    def payables_turnover(data: FinancialData, avg_payables: float) -> Optional[float]:
        """
        Payables Turnover = Cost of Revenue / Average Payables

        Measures how quickly company pays suppliers.
        """
        if avg_payables == 0:
            return None
        return data.cost_of_revenue / avg_payables

    @staticmethod
    def days_payable_outstanding(data: FinancialData, avg_payables: float) -> Optional[float]:
        """
        Days Payable Outstanding (DPO) = 365 / Payables Turnover

        Average days to pay suppliers.
        Higher can be good (holding cash longer) but too high may indicate issues.
        """
        turnover = EfficiencyMetrics.payables_turnover(data, avg_payables)
        if turnover is None or turnover == 0:
            return None
        return 365 / turnover

    @staticmethod
    def cash_conversion_cycle(dio: Optional[float], dso: Optional[float], dpo: Optional[float]) -> Optional[float]:
        """
        Cash Conversion Cycle = DIO + DSO - DPO

        Days from paying suppliers to collecting from customers.
        Lower is better (faster cash conversion).
        """
        if dio is None or dso is None or dpo is None:
            return None
        return dio + dso - dpo

    @staticmethod
    def calculate_all(data: FinancialData, prev_data: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """
        Calculate all efficiency metrics

        Requires previous period data for averages (if not provided, uses current period)
        """
        # Calculate averages (if prev_data available)
        if prev_data:
            avg_assets = (data.total_assets + prev_data.total_assets) / 2
            avg_inventory = (data.inventory + prev_data.inventory) / 2
            avg_receivables = (data.receivables + prev_data.receivables) / 2
            avg_payables = (data.accounts_payable + prev_data.accounts_payable) / 2
        else:
            avg_assets = data.total_assets
            avg_inventory = data.inventory
            avg_receivables = data.receivables
            avg_payables = data.accounts_payable

        dio = EfficiencyMetrics.days_inventory_outstanding(data, avg_inventory)
        dso = EfficiencyMetrics.days_sales_outstanding(data, avg_receivables)
        dpo = EfficiencyMetrics.days_payable_outstanding(data, avg_payables)

        return {
            'asset_turnover': EfficiencyMetrics.asset_turnover(data, avg_assets),
            'inventory_turnover': EfficiencyMetrics.inventory_turnover(data, avg_inventory),
            'days_inventory_outstanding': dio,
            'receivables_turnover': EfficiencyMetrics.receivables_turnover(data, avg_receivables),
            'days_sales_outstanding': dso,
            'payables_turnover': EfficiencyMetrics.payables_turnover(data, avg_payables),
            'days_payable_outstanding': dpo,
            'cash_conversion_cycle': EfficiencyMetrics.cash_conversion_cycle(dio, dso, dpo),
        }


class ProfitabilityMetrics:
    """
    Profitability ratios measure a company's ability to generate profits
    """

    @staticmethod
    def gross_margin(data: FinancialData) -> Optional[float]:
        """
        Gross Margin % = (Gross Profit / Revenue) × 100

        Profit after direct costs.
        Higher is better. Varies by industry.
        """
        if data.revenue == 0:
            return None
        return (data.gross_profit / data.revenue) * 100

    @staticmethod
    def operating_margin(data: FinancialData) -> Optional[float]:
        """
        Operating Margin % = (Operating Income / Revenue) × 100

        Profit from operations before interest and taxes.
        Higher is better.
        """
        if data.revenue == 0:
            return None
        return (data.operating_income / data.revenue) * 100

    @staticmethod
    def net_margin(data: FinancialData) -> Optional[float]:
        """
        Net Margin % = (Net Income / Revenue) × 100

        Bottom-line profitability.
        Higher is better.
        """
        if data.revenue == 0:
            return None
        return (data.net_income / data.revenue) * 100

    @staticmethod
    def ebitda_margin(data: FinancialData) -> Optional[float]:
        """
        EBITDA Margin % = (EBITDA / Revenue) × 100

        Profitability before interest, taxes, depreciation, amortization.
        Higher is better.
        """
        if data.revenue == 0:
            return None
        return (data.ebitda / data.revenue) * 100

    @staticmethod
    def fcf_margin(data: FinancialData) -> Optional[float]:
        """
        FCF Margin % = (Free Cash Flow / Revenue) × 100

        Cash profitability after capital expenditures.
        Higher is better.
        """
        if data.revenue == 0:
            return None
        return (data.free_cash_flow / data.revenue) * 100

    @staticmethod
    def calculate_all(data: FinancialData) -> Dict[str, Optional[float]]:
        """Calculate all profitability metrics"""
        return {
            'gross_margin': ProfitabilityMetrics.gross_margin(data),
            'operating_margin': ProfitabilityMetrics.operating_margin(data),
            'net_margin': ProfitabilityMetrics.net_margin(data),
            'ebitda_margin': ProfitabilityMetrics.ebitda_margin(data),
            'fcf_margin': ProfitabilityMetrics.fcf_margin(data),
        }


class ReturnMetrics:
    """
    Return ratios measure returns generated on capital employed
    """

    @staticmethod
    def roe(data: FinancialData, avg_equity: float) -> Optional[float]:
        """
        Return on Equity (ROE) % = (Net Income / Average Equity) × 100

        Return generated for shareholders.
        > 15% is generally good, > 20% is excellent.
        """
        if avg_equity == 0:
            return None
        return (data.net_income / avg_equity) * 100

    @staticmethod
    def roa(data: FinancialData, avg_assets: float) -> Optional[float]:
        """
        Return on Assets (ROA) % = (Net Income / Average Assets) × 100

        Efficiency of asset utilization.
        > 5% is generally good. Varies by industry.
        """
        if avg_assets == 0:
            return None
        return (data.net_income / avg_assets) * 100

    @staticmethod
    def roic(data: FinancialData, avg_invested_capital: float) -> Optional[float]:
        """
        Return on Invested Capital (ROIC) % = (NOPAT / Average Invested Capital) × 100

        NOPAT = Net Operating Profit After Tax = EBIT × (1 - Tax Rate)
        Invested Capital = Total Equity + Total Debt

        Return generated on all capital (debt + equity).
        > 15% is excellent.
        """
        if avg_invested_capital == 0 or data.income_before_tax == 0:
            return None

        # Calculate tax rate
        tax_rate = data.income_tax / data.income_before_tax if data.income_before_tax != 0 else 0
        nopat = data.ebit * (1 - tax_rate)

        return (nopat / avg_invested_capital) * 100

    @staticmethod
    def dupont_roe_3factor(data: FinancialData, avg_equity: float, avg_assets: float) -> Dict[str, Optional[float]]:
        """
        DuPont 3-Factor ROE Analysis

        ROE = Net Margin × Asset Turnover × Equity Multiplier

        Decomposes ROE into:
        - Profitability (Net Margin)
        - Efficiency (Asset Turnover)
        - Leverage (Equity Multiplier)
        """
        if data.revenue == 0 or avg_assets == 0 or avg_equity == 0:
            return {
                'net_margin': None,
                'asset_turnover': None,
                'equity_multiplier': None,
                'roe_dupont': None,
            }

        net_margin = data.net_income / data.revenue
        asset_turnover = data.revenue / avg_assets
        equity_multiplier = avg_assets / avg_equity
        roe_dupont = net_margin * asset_turnover * equity_multiplier * 100

        return {
            'net_margin': net_margin * 100,
            'asset_turnover': asset_turnover,
            'equity_multiplier': equity_multiplier,
            'roe_dupont': roe_dupont,
        }

    @staticmethod
    def calculate_all(data: FinancialData, prev_data: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """Calculate all return metrics"""
        # Calculate averages
        if prev_data:
            avg_equity = (data.total_equity + prev_data.total_equity) / 2
            avg_assets = (data.total_assets + prev_data.total_assets) / 2
            total_debt = data.short_term_debt + data.long_term_debt
            prev_total_debt = prev_data.short_term_debt + prev_data.long_term_debt
            avg_invested_capital = (avg_equity + total_debt + avg_equity + prev_total_debt) / 2
        else:
            avg_equity = data.total_equity
            avg_assets = data.total_assets
            avg_invested_capital = data.total_equity + data.short_term_debt + data.long_term_debt

        metrics = {
            'roe': ReturnMetrics.roe(data, avg_equity),
            'roa': ReturnMetrics.roa(data, avg_assets),
            'roic': ReturnMetrics.roic(data, avg_invested_capital),
        }

        # Add DuPont analysis
        dupont = ReturnMetrics.dupont_roe_3factor(data, avg_equity, avg_assets)
        metrics.update({
            'dupont_net_margin': dupont['net_margin'],
            'dupont_asset_turnover': dupont['asset_turnover'],
            'dupont_equity_multiplier': dupont['equity_multiplier'],
            'roe_dupont': dupont['roe_dupont'],
        })

        return metrics


class GrowthMetrics:
    """
    Growth metrics measure year-over-year and multi-year growth rates
    """

    @staticmethod
    def yoy_growth(current: float, previous: float) -> Optional[float]:
        """
        Year-over-Year Growth % = ((Current - Previous) / Previous) × 100
        """
        if previous == 0:
            return None
        return ((current - previous) / previous) * 100

    @staticmethod
    def cagr(start_value: float, end_value: float, num_years: int) -> Optional[float]:
        """
        Compound Annual Growth Rate (CAGR) %

        CAGR = ((End Value / Start Value) ^ (1 / Years)) - 1) × 100
        """
        if start_value <= 0 or end_value <= 0 or num_years <= 0:
            return None
        return (((end_value / start_value) ** (1 / num_years)) - 1) * 100

    @staticmethod
    def calculate_growth_rates(
        current: FinancialData,
        historical: List[FinancialData]
    ) -> Dict[str, Optional[float]]:
        """
        Calculate growth rates for key metrics

        Args:
            current: Current period data
            historical: List of historical periods (sorted newest to oldest)

        Returns:
            Dict with YoY and CAGR metrics
        """
        metrics = {}

        # YoY Growth (if 1 year ago data exists)
        if len(historical) >= 1:
            prev = historical[0]
            metrics['revenue_growth_yoy'] = GrowthMetrics.yoy_growth(current.revenue, prev.revenue)
            metrics['earnings_growth_yoy'] = GrowthMetrics.yoy_growth(current.net_income, prev.net_income)
            metrics['fcf_growth_yoy'] = GrowthMetrics.yoy_growth(current.free_cash_flow, prev.free_cash_flow)
            metrics['equity_growth_yoy'] = GrowthMetrics.yoy_growth(current.total_equity, prev.total_equity)
        else:
            metrics['revenue_growth_yoy'] = None
            metrics['earnings_growth_yoy'] = None
            metrics['fcf_growth_yoy'] = None
            metrics['equity_growth_yoy'] = None

        # 3-Year CAGR
        if len(historical) >= 3:
            three_years_ago = historical[2]
            metrics['revenue_cagr_3y'] = GrowthMetrics.cagr(three_years_ago.revenue, current.revenue, 3)
            metrics['earnings_cagr_3y'] = GrowthMetrics.cagr(three_years_ago.net_income, current.net_income, 3)
            metrics['fcf_cagr_3y'] = GrowthMetrics.cagr(three_years_ago.free_cash_flow, current.free_cash_flow, 3)
        else:
            metrics['revenue_cagr_3y'] = None
            metrics['earnings_cagr_3y'] = None
            metrics['fcf_cagr_3y'] = None

        # 5-Year CAGR
        if len(historical) >= 5:
            five_years_ago = historical[4]
            metrics['revenue_cagr_5y'] = GrowthMetrics.cagr(five_years_ago.revenue, current.revenue, 5)
            metrics['earnings_cagr_5y'] = GrowthMetrics.cagr(five_years_ago.net_income, current.net_income, 5)
            metrics['fcf_cagr_5y'] = GrowthMetrics.cagr(five_years_ago.free_cash_flow, current.free_cash_flow, 5)
        else:
            metrics['revenue_cagr_5y'] = None
            metrics['earnings_cagr_5y'] = None
            metrics['fcf_cagr_5y'] = None

        return metrics


class PerShareMetrics:
    """
    Per-share metrics normalize values to per-share basis
    """

    @staticmethod
    def book_value_per_share(data: FinancialData) -> Optional[float]:
        """
        Book Value per Share = Total Equity / Shares Outstanding
        """
        if data.shares_outstanding == 0:
            return None
        return data.total_equity / data.shares_outstanding

    @staticmethod
    def tangible_book_value_per_share(data: FinancialData) -> Optional[float]:
        """
        Tangible Book Value per Share = (Equity - Intangibles - Goodwill) / Shares

        More conservative than book value (excludes intangible assets).
        """
        if data.shares_outstanding == 0:
            return None
        tangible_equity = data.total_equity - data.intangible_assets - data.goodwill
        return tangible_equity / data.shares_outstanding

    @staticmethod
    def fcf_per_share(data: FinancialData) -> Optional[float]:
        """
        Free Cash Flow per Share = FCF / Shares Outstanding
        """
        if data.shares_outstanding == 0:
            return None
        return data.free_cash_flow / data.shares_outstanding

    @staticmethod
    def operating_cf_per_share(data: FinancialData) -> Optional[float]:
        """
        Operating Cash Flow per Share = Operating CF / Shares Outstanding
        """
        if data.shares_outstanding == 0:
            return None
        return data.operating_cash_flow / data.shares_outstanding

    @staticmethod
    def revenue_per_share(data: FinancialData) -> Optional[float]:
        """
        Revenue per Share = Revenue / Shares Outstanding
        """
        if data.shares_outstanding == 0:
            return None
        return data.revenue / data.shares_outstanding

    @staticmethod
    def calculate_all(data: FinancialData) -> Dict[str, Optional[float]]:
        """Calculate all per-share metrics"""
        return {
            'book_value_per_share': PerShareMetrics.book_value_per_share(data),
            'tangible_book_value_per_share': PerShareMetrics.tangible_book_value_per_share(data),
            'fcf_per_share': PerShareMetrics.fcf_per_share(data),
            'operating_cf_per_share': PerShareMetrics.operating_cf_per_share(data),
            'revenue_per_share': PerShareMetrics.revenue_per_share(data),
        }


class CashFlowQualityMetrics:
    """
    Cash flow quality metrics - assess earnings quality and cash generation sustainability
    """

    @staticmethod
    def cash_flow_to_net_income(data: FinancialData) -> Optional[float]:
        """
        Operating CF / Net Income

        Measures how much of net income is backed by actual cash flow.
        > 1.0 = High quality earnings (cash-backed)
        < 1.0 = Earnings supported by accruals (lower quality)
        < 0 = Red flag (negative cash flow or earnings)
        """
        if data.net_income == 0:
            return None
        return data.operating_cash_flow / data.net_income

    @staticmethod
    def cash_roi(data: FinancialData, avg_invested_capital: float) -> Optional[float]:
        """
        Cash ROI % = (Operating Cash Flow / Average Invested Capital) × 100

        Cash-based alternative to ROIC.
        Measures cash return on invested capital.
        > 15% is excellent.
        """
        if avg_invested_capital == 0:
            return None
        return (data.operating_cash_flow / avg_invested_capital) * 100

    @staticmethod
    def capex_to_operating_cf_ratio(data: FinancialData) -> Optional[float]:
        """
        CapEx to Operating CF Ratio = CapEx / Operating Cash Flow

        Measures capital intensity and reinvestment rate.
        < 0.5 = Conservative reinvestment, strong FCF generation
        0.5-0.8 = Moderate reinvestment
        > 0.8 = Heavy reinvestment (growth or high maintenance?)
        """
        if data.operating_cash_flow == 0:
            return None
        return abs(data.capex) / data.operating_cash_flow

    @staticmethod
    def free_cash_flow_conversion(data: FinancialData) -> Optional[float]:
        """
        FCF Conversion = FCF / Net Income

        Measures how much net income converts to free cash flow.
        > 1.0 = Excellent cash conversion
        0.5-1.0 = Good conversion
        < 0.5 = Poor conversion (high capex or working capital needs)
        """
        if data.net_income == 0:
            return None
        return data.free_cash_flow / data.net_income

    @staticmethod
    def cash_flow_margin(data: FinancialData) -> Optional[float]:
        """
        Operating Cash Flow Margin % = (Operating CF / Revenue) × 100

        Measures cash profitability.
        Higher is better. Compare to net margin.
        """
        if data.revenue == 0:
            return None
        return (data.operating_cash_flow / data.revenue) * 100

    @staticmethod
    def calculate_all(data: FinancialData, prev_data: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """Calculate all cash flow quality metrics"""
        # Calculate average invested capital
        if prev_data:
            total_debt = data.short_term_debt + data.long_term_debt
            prev_total_debt = prev_data.short_term_debt + prev_data.long_term_debt
            avg_invested_capital = (data.total_equity + total_debt + prev_data.total_equity + prev_total_debt) / 2
        else:
            avg_invested_capital = data.total_equity + data.short_term_debt + data.long_term_debt

        return {
            'cash_flow_to_net_income': CashFlowQualityMetrics.cash_flow_to_net_income(data),
            'cash_roi': CashFlowQualityMetrics.cash_roi(data, avg_invested_capital),
            'capex_to_operating_cf': CashFlowQualityMetrics.capex_to_operating_cf_ratio(data),
            'fcf_conversion': CashFlowQualityMetrics.free_cash_flow_conversion(data),
            'operating_cf_margin': CashFlowQualityMetrics.cash_flow_margin(data),
        }


class ShareholderValueMetrics:
    """
    Shareholder value metrics - capital allocation and returns to shareholders
    """

    @staticmethod
    def dividend_payout_ratio(data: FinancialData) -> Optional[float]:
        """
        Dividend Payout Ratio % = (Dividends Paid / Net Income) × 100

        Measures portion of earnings paid as dividends.
        < 40% = Conservative, room to grow dividends
        40-60% = Sustainable payout
        > 80% = Potentially unsustainable (check FCF payout)
        """
        if data.net_income <= 0 or data.dividends_paid == 0:
            return None
        return (data.dividends_paid / data.net_income) * 100

    @staticmethod
    def fcf_payout_ratio(data: FinancialData) -> Optional[float]:
        """
        FCF Payout Ratio % = (Dividends Paid / Free Cash Flow) × 100

        More sustainable measure than earnings-based payout.
        < 50% = Very sustainable
        50-80% = Moderate sustainability
        > 100% = Unsustainable (paying from reserves or debt)
        """
        if data.free_cash_flow <= 0 or data.dividends_paid == 0:
            return None
        return (data.dividends_paid / data.free_cash_flow) * 100

    @staticmethod
    def share_buyback_yield(data: FinancialData) -> Optional[float]:
        """
        Share Buyback Yield % = (Net Share Buybacks / Market Cap) × 100

        Measures shareholder returns via buybacks.
        Positive = Net buybacks (shareholder friendly)
        Negative = Net issuances (dilution)
        """
        if data.market_cap is None or data.market_cap == 0:
            return None
        return (data.share_buybacks / data.market_cap) * 100

    @staticmethod
    def total_shareholder_yield(data: FinancialData) -> Optional[float]:
        """
        Total Shareholder Yield % = ((Dividends + Buybacks) / Market Cap) × 100

        Total cash returned to shareholders (dividends + buybacks).
        > 5% = Strong shareholder returns
        3-5% = Good returns
        < 3% = Low returns
        """
        if data.market_cap is None or data.market_cap == 0:
            return None
        total_return = data.dividends_paid + data.share_buybacks
        return (total_return / data.market_cap) * 100

    @staticmethod
    def earnings_retention_rate(data: FinancialData) -> Optional[float]:
        """
        Earnings Retention Rate % = ((Net Income - Dividends) / Net Income) × 100

        Percentage of earnings retained for growth.
        Higher = More reinvestment in growth
        Lower = More income distribution
        """
        if data.net_income <= 0:
            return None
        return ((data.net_income - data.dividends_paid) / data.net_income) * 100

    @staticmethod
    def calculate_all(data: FinancialData) -> Dict[str, Optional[float]]:
        """Calculate all shareholder value metrics"""
        return {
            'dividend_payout_ratio': ShareholderValueMetrics.dividend_payout_ratio(data),
            'fcf_payout_ratio': ShareholderValueMetrics.fcf_payout_ratio(data),
            'share_buyback_yield': ShareholderValueMetrics.share_buyback_yield(data),
            'total_shareholder_yield': ShareholderValueMetrics.total_shareholder_yield(data),
            'earnings_retention_rate': ShareholderValueMetrics.earnings_retention_rate(data),
        }


class BalanceSheetQualityMetrics:
    """
    Balance sheet quality - asset quality and financial flexibility
    """

    @staticmethod
    def tangible_asset_ratio(data: FinancialData) -> Optional[float]:
        """
        Tangible Asset Ratio % = ((Total Assets - Intangibles - Goodwill) / Total Assets) × 100

        Measures proportion of "real" assets.
        Higher = More tangible assets, less reliance on intangibles
        < 50% = Asset-light business or M&A-heavy
        > 80% = Asset-heavy, tangible business
        """
        if data.total_assets == 0:
            return None
        tangible_assets = data.total_assets - data.intangible_assets - data.goodwill
        return (tangible_assets / data.total_assets) * 100

    @staticmethod
    def fixed_asset_turnover(data: FinancialData, avg_ppe_net: float) -> Optional[float]:
        """
        Fixed Asset Turnover = Revenue / Average Net PP&E

        Measures capital intensity and asset productivity.
        Higher = More efficient use of fixed assets
        Varies widely by industry (tech vs manufacturing)
        """
        if avg_ppe_net == 0:
            return None
        return data.revenue / avg_ppe_net

    @staticmethod
    def cash_to_debt_ratio(data: FinancialData) -> Optional[float]:
        """
        Cash to Debt Ratio = Cash / Total Debt

        Measures debt coverage by liquid assets.
        > 1.0 = Net cash position (very strong)
        0.5-1.0 = Strong liquidity
        < 0.2 = Limited liquidity
        """
        total_debt = data.short_term_debt + data.long_term_debt
        if total_debt == 0:
            return None
        return data.cash / total_debt

    @staticmethod
    def net_debt(data: FinancialData) -> float:
        """
        Net Debt = Total Debt - (Cash + Short-term Investments)

        Absolute measure of debt after liquid assets.
        Negative = Net cash position (no net debt)
        Positive = Net debt position
        """
        total_debt = data.short_term_debt + data.long_term_debt
        liquid_assets = data.cash + data.short_term_investments
        return total_debt - liquid_assets

    @staticmethod
    def net_debt_to_ebitda(data: FinancialData) -> Optional[float]:
        """
        Net Debt to EBITDA = Net Debt / EBITDA

        Measures leverage relative to cash flow generation.
        < 1.0 = Very low leverage
        1.0-3.0 = Moderate leverage
        3.0-5.0 = High leverage
        > 5.0 = Very high leverage (potential distress)

        Common metric in LBO/M&A analysis.
        """
        if data.ebitda == 0:
            return None
        net_debt = BalanceSheetQualityMetrics.net_debt(data)
        return net_debt / data.ebitda

    @staticmethod
    def financial_leverage_ratio(data: FinancialData) -> Optional[float]:
        """
        Financial Leverage Ratio = Total Assets / Total Equity

        DuPont component - measures leverage amplification of ROE.
        1.0 = No leverage (100% equity financed)
        2.0 = 50% debt, 50% equity
        Higher = More leverage (amplifies both gains and losses)
        """
        if data.total_equity == 0:
            return None
        return data.total_assets / data.total_equity

    @staticmethod
    def calculate_all(data: FinancialData, prev_data: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """Calculate all balance sheet quality metrics"""
        # Calculate average PP&E
        if prev_data:
            avg_ppe = (data.ppe_net + prev_data.ppe_net) / 2
        else:
            avg_ppe = data.ppe_net

        return {
            'tangible_asset_ratio': BalanceSheetQualityMetrics.tangible_asset_ratio(data),
            'fixed_asset_turnover': BalanceSheetQualityMetrics.fixed_asset_turnover(data, avg_ppe),
            'cash_to_debt_ratio': BalanceSheetQualityMetrics.cash_to_debt_ratio(data),
            'net_debt': BalanceSheetQualityMetrics.net_debt(data),
            'net_debt_to_ebitda': BalanceSheetQualityMetrics.net_debt_to_ebitda(data),
            'financial_leverage_ratio': BalanceSheetQualityMetrics.financial_leverage_ratio(data),
        }


class ValuationMetrics:
    """
    Market valuation ratios (requires market price data)
    """

    @staticmethod
    def pe_ratio(data: FinancialData) -> Optional[float]:
        """
        P/E Ratio = Market Price / EPS (Diluted)

        Most common valuation metric.
        < 15 = Potentially undervalued (or low growth)
        15-25 = Fair value
        > 25 = Potentially overvalued (or high growth)
        """
        if data.market_price is None or data.eps_diluted == 0:
            return None
        return data.market_price / data.eps_diluted

    @staticmethod
    def price_to_book(data: FinancialData) -> Optional[float]:
        """
        P/B Ratio = Market Price / Book Value per Share

        < 1.0 = Trading below book value (value stock)
        1.0-3.0 = Fair value
        > 3.0 = Premium valuation (growth or quality premium)
        """
        if data.market_price is None or data.shares_outstanding == 0:
            return None
        book_value_per_share = data.total_equity / data.shares_outstanding
        if book_value_per_share == 0:
            return None
        return data.market_price / book_value_per_share

    @staticmethod
    def price_to_sales(data: FinancialData) -> Optional[float]:
        """
        P/S Ratio = Market Cap / Revenue

        Useful for unprofitable growth companies.
        < 1.0 = Very cheap
        1.0-2.0 = Reasonable
        > 5.0 = Expensive (unless high-growth SaaS)
        """
        if data.market_cap is None or data.revenue == 0:
            return None
        return data.market_cap / data.revenue

    @staticmethod
    def ev_to_ebitda(data: FinancialData) -> Optional[float]:
        """
        EV/EBITDA = Enterprise Value / EBITDA

        Capital-structure neutral valuation (adjusts for debt).
        < 10 = Potentially undervalued
        10-15 = Fair value
        > 15 = Potentially overvalued
        """
        if data.enterprise_value is None or data.ebitda == 0:
            return None
        return data.enterprise_value / data.ebitda

    @staticmethod
    def price_to_fcf(data: FinancialData) -> Optional[float]:
        """
        P/FCF Ratio = Market Cap / Free Cash Flow

        Cash-based valuation alternative to P/E.
        < 15 = Potentially undervalued
        15-25 = Fair value
        > 25 = Potentially overvalued
        """
        if data.market_cap is None or data.free_cash_flow == 0:
            return None
        return data.market_cap / data.free_cash_flow

    @staticmethod
    def peg_ratio(data: FinancialData, earnings_growth_rate: Optional[float]) -> Optional[float]:
        """
        PEG Ratio = P/E Ratio / Earnings Growth Rate

        Adjusts P/E for growth.
        < 1.0 = Potentially undervalued relative to growth
        1.0-2.0 = Fair value
        > 2.0 = Potentially overvalued relative to growth
        """
        if earnings_growth_rate is None or earnings_growth_rate == 0:
            return None
        pe = ValuationMetrics.pe_ratio(data)
        if pe is None:
            return None
        return pe / earnings_growth_rate

    @staticmethod
    def earnings_yield(data: FinancialData) -> Optional[float]:
        """
        Earnings Yield % = (EPS / Price) × 100

        Inverse of P/E ratio - comparable to bond yields.
        Higher = Better value (more earnings per rupee invested)
        Compare to 10-year bond yield for relative value.
        """
        if data.market_price is None or data.market_price == 0:
            return None
        return (data.eps_diluted / data.market_price) * 100

    @staticmethod
    def fcf_yield(data: FinancialData) -> Optional[float]:
        """
        FCF Yield % = (FCF per Share / Price) × 100

        Cash flow yield - measures cash return.
        > 5% = Strong cash generation relative to price
        3-5% = Moderate
        < 3% = Low cash yield
        """
        if data.market_price is None or data.market_price == 0 or data.shares_outstanding == 0:
            return None
        fcf_per_share = data.free_cash_flow / data.shares_outstanding
        return (fcf_per_share / data.market_price) * 100

    @staticmethod
    def calculate_all(data: FinancialData, earnings_growth_rate: Optional[float] = None) -> Dict[str, Optional[float]]:
        """Calculate all valuation metrics"""
        return {
            'pe_ratio': ValuationMetrics.pe_ratio(data),
            'price_to_book': ValuationMetrics.price_to_book(data),
            'price_to_sales': ValuationMetrics.price_to_sales(data),
            'ev_to_ebitda': ValuationMetrics.ev_to_ebitda(data),
            'price_to_fcf': ValuationMetrics.price_to_fcf(data),
            'peg_ratio': ValuationMetrics.peg_ratio(data, earnings_growth_rate),
            'earnings_yield': ValuationMetrics.earnings_yield(data),
            'fcf_yield': ValuationMetrics.fcf_yield(data),
        }


class WorkingCapitalMetrics:
    """
    Working capital efficiency - granular operational efficiency metrics
    """

    @staticmethod
    def working_capital_turnover(data: FinancialData, avg_working_capital: float) -> Optional[float]:
        """
        Working Capital Turnover = Revenue / Average Working Capital

        Measures efficiency of working capital utilization.
        Higher = More efficient (less working capital needed per revenue)
        Industry-specific benchmarks apply
        """
        if avg_working_capital == 0:
            return None
        return data.revenue / avg_working_capital

    @staticmethod
    def working_capital_to_sales(data: FinancialData) -> Optional[float]:
        """
        Working Capital to Sales % = (Working Capital / Revenue) × 100

        Measures working capital as % of sales.
        Lower = More efficient (less capital tied up)
        Industry-specific (e.g., retail vs manufacturing)
        """
        if data.revenue == 0:
            return None
        working_capital = data.current_assets - data.current_liabilities
        return (working_capital / data.revenue) * 100

    @staticmethod
    def defensive_interval_ratio(data: FinancialData) -> Optional[float]:
        """
        Defensive Interval Ratio = (Cash + ST Inv + Receivables) / Daily Operating Expenses

        Days company can operate without additional revenue.
        > 90 days = Strong defensive position
        30-90 days = Adequate
        < 30 days = Weak position
        """
        # Estimate daily operating expenses
        if data.operating_expenses == 0:
            return None
        daily_op_expenses = data.operating_expenses / 365
        if daily_op_expenses == 0:
            return None

        defensive_assets = data.cash + data.short_term_investments + data.receivables
        return defensive_assets / daily_op_expenses

    @staticmethod
    def net_working_capital_ratio(data: FinancialData) -> Optional[float]:
        """
        Net Working Capital Ratio % = (Working Capital / Total Assets) × 100

        Measures liquidity as % of total assets.
        Higher = More liquid asset base
        """
        if data.total_assets == 0:
            return None
        working_capital = data.current_assets - data.current_liabilities
        return (working_capital / data.total_assets) * 100

    @staticmethod
    def calculate_all(data: FinancialData, prev_data: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """Calculate all working capital metrics"""
        # Calculate average working capital
        if prev_data:
            curr_wc = data.current_assets - data.current_liabilities
            prev_wc = prev_data.current_assets - prev_data.current_liabilities
            avg_wc = (curr_wc + prev_wc) / 2
        else:
            avg_wc = data.current_assets - data.current_liabilities

        return {
            'working_capital_turnover': WorkingCapitalMetrics.working_capital_turnover(data, avg_wc),
            'working_capital_to_sales': WorkingCapitalMetrics.working_capital_to_sales(data),
            'defensive_interval_ratio': WorkingCapitalMetrics.defensive_interval_ratio(data),
            'net_working_capital_ratio': WorkingCapitalMetrics.net_working_capital_ratio(data),
        }


class DetailedProfitabilityMetrics:
    """
    Detailed profitability - granular margin and cost analysis
    """

    @staticmethod
    def rd_intensity(data: FinancialData) -> Optional[float]:
        """
        R&D Intensity % = (R&D Expense / Revenue) × 100

        Measures investment in innovation.
        Tech/Pharma: 10-20% (high R&D)
        Industrial: 2-5% (moderate R&D)
        Retail: < 1% (low R&D)
        """
        if data.rd_expense is None or data.revenue == 0:
            return None
        return (data.rd_expense / data.revenue) * 100

    @staticmethod
    def sga_ratio(data: FinancialData) -> Optional[float]:
        """
        SG&A Ratio % = (SG&A Expense / Revenue) × 100

        Measures overhead efficiency.
        Lower = More efficient operations
        Varies by industry (retail vs software)
        """
        if data.sga_expense is None or data.revenue == 0:
            return None
        return (data.sga_expense / data.revenue) * 100

    @staticmethod
    def effective_tax_rate(data: FinancialData) -> Optional[float]:
        """
        Effective Tax Rate % = (Tax Expense / Income Before Tax) × 100

        Actual tax rate paid (vs statutory rate).
        Compare to country statutory rate (India: ~25%)
        Lower = Tax efficiency or one-time benefits
        """
        if data.income_before_tax == 0:
            return None
        return (data.income_tax / data.income_before_tax) * 100

    @staticmethod
    def nopat_margin(data: FinancialData) -> Optional[float]:
        """
        NOPAT Margin % = (NOPAT / Revenue) × 100
        NOPAT = EBIT × (1 - Tax Rate)

        Operating profit after tax, before financing costs.
        Higher = Better core operating profitability
        """
        if data.revenue == 0 or data.income_before_tax == 0:
            return None

        # Calculate tax rate
        tax_rate = data.income_tax / data.income_before_tax if data.income_before_tax != 0 else 0
        nopat = data.ebit * (1 - tax_rate)

        return (nopat / data.revenue) * 100

    @staticmethod
    def gross_profit_per_employee(data: FinancialData) -> Optional[float]:
        """
        Gross Profit per Employee = Gross Profit / Number of Employees

        Productivity metric.
        Higher = More productive workforce
        Compare across peers in same industry
        """
        if data.num_employees is None or data.num_employees == 0:
            return None
        return data.gross_profit / data.num_employees

    @staticmethod
    def calculate_all(data: FinancialData) -> Dict[str, Optional[float]]:
        """Calculate all detailed profitability metrics"""
        return {
            'rd_intensity': DetailedProfitabilityMetrics.rd_intensity(data),
            'sga_ratio': DetailedProfitabilityMetrics.sga_ratio(data),
            'effective_tax_rate': DetailedProfitabilityMetrics.effective_tax_rate(data),
            'nopat_margin': DetailedProfitabilityMetrics.nopat_margin(data),
            'gross_profit_per_employee': DetailedProfitabilityMetrics.gross_profit_per_employee(data),
        }


class CompetitiveAdvantageMetrics:
    """
    Competitive advantage indicators - moat and sustainability signals
    """

    @staticmethod
    def gross_margin_stability(margins_5y: List[float]) -> Optional[float]:
        """
        Gross Margin Stability = Standard Deviation of 5-year Gross Margins

        Lower = More stable pricing power (stronger moat)
        Higher = Volatile margins (competitive pressure)
        < 2% = Very stable
        > 5% = Unstable
        """
        if not margins_5y or len(margins_5y) < 2:
            return None
        return float(np.std(margins_5y))

    @staticmethod
    def revenue_consistency(revenues_5y: List[float]) -> Optional[float]:
        """
        Revenue Consistency = Coefficient of Variation (CV) = StdDev / Mean

        Measures revenue predictability.
        Lower = More predictable/consistent revenue stream
        Higher = Cyclical or volatile business
        """
        if not revenues_5y or len(revenues_5y) < 2:
            return None
        mean_revenue = np.mean(revenues_5y)
        if mean_revenue == 0:
            return None
        std_revenue = np.std(revenues_5y)
        return float(std_revenue / mean_revenue)

    @staticmethod
    def roic_spread(data: FinancialData, wacc: Optional[float]) -> Optional[float]:
        """
        ROIC Spread = ROIC - WACC

        Economic value creation measure.
        Positive = Value creation (ROIC > cost of capital)
        Negative = Value destruction (ROIC < cost of capital)
        > 5% = Strong value creation
        """
        if wacc is None:
            return None

        # Calculate ROIC
        total_debt = data.short_term_debt + data.long_term_debt
        invested_capital = data.total_equity + total_debt

        if invested_capital == 0 or data.income_before_tax == 0:
            return None

        tax_rate = data.income_tax / data.income_before_tax
        nopat = data.ebit * (1 - tax_rate)
        roic = (nopat / invested_capital) * 100

        return roic - wacc

    @staticmethod
    def reinvestment_rate(data: FinancialData) -> Optional[float]:
        """
        Reinvestment Rate % = ((CapEx + R&D) / Operating Cash Flow) × 100

        Measures growth investment intensity.
        < 40% = Low reinvestment (mature/harvesting)
        40-70% = Moderate reinvestment (steady growth)
        > 70% = High reinvestment (aggressive growth)
        """
        if data.operating_cash_flow == 0:
            return None

        rd = data.rd_expense if data.rd_expense is not None else 0
        reinvestment = abs(data.capex) + rd

        return (reinvestment / data.operating_cash_flow) * 100

    @staticmethod
    def calculate_all(
        data: FinancialData,
        margins_5y: Optional[List[float]] = None,
        revenues_5y: Optional[List[float]] = None,
        wacc: Optional[float] = None
    ) -> Dict[str, Optional[float]]:
        """Calculate all competitive advantage metrics"""
        return {
            'gross_margin_stability': CompetitiveAdvantageMetrics.gross_margin_stability(margins_5y) if margins_5y else None,
            'revenue_consistency': CompetitiveAdvantageMetrics.revenue_consistency(revenues_5y) if revenues_5y else None,
            'roic_spread': CompetitiveAdvantageMetrics.roic_spread(data, wacc),
            'reinvestment_rate': CompetitiveAdvantageMetrics.reinvestment_rate(data),
        }


class EnhancedQualityScores:
    """
    Enhanced quality scores - fraud detection and distress prediction
    """

    @staticmethod
    def beneish_m_score(current: FinancialData, previous: FinancialData) -> Optional[float]:
        """
        Beneish M-Score (Earnings Manipulation Detector)

        8-variable model detecting accounting manipulation:
        - DSRI: Days Sales in Receivables Index
        - GMI: Gross Margin Index
        - AQI: Asset Quality Index
        - SGI: Sales Growth Index
        - DEPI: Depreciation Index
        - SGAI: SG&A Index
        - LVGI: Leverage Index
        - TATA: Total Accruals to Total Assets

        Interpretation:
        > -1.78 = Likely manipulator (red flag)
        < -2.22 = Unlikely manipulator
        """
        try:
            # 1. DSRI (Days Sales in Receivables Index)
            curr_dsr = (current.receivables / current.revenue) * 365 if current.revenue != 0 else 0
            prev_dsr = (previous.receivables / previous.revenue) * 365 if previous.revenue != 0 else 0
            dsri = curr_dsr / prev_dsr if prev_dsr != 0 else 1

            # 2. GMI (Gross Margin Index)
            curr_gm = current.gross_profit / current.revenue if current.revenue != 0 else 0
            prev_gm = previous.gross_profit / previous.revenue if previous.revenue != 0 else 0
            gmi = prev_gm / curr_gm if curr_gm != 0 else 1

            # 3. AQI (Asset Quality Index)
            curr_nca = current.total_assets - current.current_assets - current.ppe_net
            prev_nca = previous.total_assets - previous.current_assets - previous.ppe_net
            curr_aqi = curr_nca / current.total_assets if current.total_assets != 0 else 0
            prev_aqi = prev_nca / previous.total_assets if previous.total_assets != 0 else 0
            aqi = curr_aqi / prev_aqi if prev_aqi != 0 else 1

            # 4. SGI (Sales Growth Index)
            sgi = current.revenue / previous.revenue if previous.revenue != 0 else 1

            # 5. DEPI (Depreciation Index) - using depreciation if available
            depr = current.depreciation_amortization if current.depreciation_amortization else 0
            prev_depr = previous.depreciation_amortization if previous.depreciation_amortization else 0
            curr_depr_rate = depr / (depr + current.ppe_net) if (depr + current.ppe_net) != 0 else 0
            prev_depr_rate = prev_depr / (prev_depr + previous.ppe_net) if (prev_depr + previous.ppe_net) != 0 else 0
            depi = prev_depr_rate / curr_depr_rate if curr_depr_rate != 0 else 1

            # 6. SGAI (SG&A Index)
            curr_sga = current.sga_expense if current.sga_expense else current.operating_expenses
            prev_sga = previous.sga_expense if previous.sga_expense else previous.operating_expenses
            curr_sga_idx = curr_sga / current.revenue if current.revenue != 0 else 0
            prev_sga_idx = prev_sga / previous.revenue if previous.revenue != 0 else 0
            sgai = curr_sga_idx / prev_sga_idx if prev_sga_idx != 0 else 1

            # 7. LVGI (Leverage Index)
            curr_debt = current.short_term_debt + current.long_term_debt
            prev_debt = previous.short_term_debt + previous.long_term_debt
            curr_lev = curr_debt / current.total_assets if current.total_assets != 0 else 0
            prev_lev = prev_debt / previous.total_assets if previous.total_assets != 0 else 0
            lvgi = curr_lev / prev_lev if prev_lev != 0 else 1

            # 8. TATA (Total Accruals to Total Assets)
            working_capital_change = (current.current_assets - current.current_liabilities) - \
                                   (previous.current_assets - previous.current_liabilities)
            tata = (working_capital_change - current.operating_cash_flow) / current.total_assets \
                   if current.total_assets != 0 else 0

            # M-Score calculation
            m_score = (
                -4.84 +
                0.920 * dsri +
                0.528 * gmi +
                0.404 * aqi +
                0.892 * sgi +
                0.115 * depi -
                0.172 * sgai +
                4.679 * tata -
                0.327 * lvgi
            )

            return m_score

        except Exception:
            return None

    @staticmethod
    def sloan_accruals_quality(data: FinancialData) -> Optional[float]:
        """
        Sloan Accruals Quality Factor

        Accruals = Net Income - Operating Cash Flow
        Scaled by Average Total Assets

        Lower accruals = Higher quality earnings
        High accruals often predict negative future returns
        """
        if data.total_assets == 0:
            return None

        accruals = data.net_income - data.operating_cash_flow
        return accruals / data.total_assets

    @staticmethod
    def ohlson_o_score(data: FinancialData) -> Optional[float]:
        """
        Ohlson O-Score (Bankruptcy Prediction)

        9-variable logistic regression model:
        > 0.5 = High bankruptcy probability
        0.0-0.5 = Moderate risk
        < 0.0 = Low risk

        Alternative to Altman Z-Score, works better for small firms.
        """
        try:
            # Size (log of total assets / GNP price-level index - simplified)
            size = np.log(data.total_assets) if data.total_assets > 0 else 0

            # Total liabilities / Total assets
            tlta = data.total_liabilities / data.total_assets if data.total_assets != 0 else 0

            # Working capital / Total assets
            wcta = (data.current_assets - data.current_liabilities) / data.total_assets \
                   if data.total_assets != 0 else 0

            # Current liabilities / Current assets
            clca = data.current_liabilities / data.current_assets if data.current_assets != 0 else 0

            # One if total liabilities > total assets
            oeneg = 1 if data.total_liabilities > data.total_assets else 0

            # Net income / Total assets
            nita = data.net_income / data.total_assets if data.total_assets != 0 else 0

            # Operating cash flow / Total liabilities
            futl = data.operating_cash_flow / data.total_liabilities if data.total_liabilities != 0 else 0

            # One if net income was negative for the last two years (simplified to current)
            intwo = 1 if data.net_income < 0 else 0

            # (NIt - NIt-1) / (|NIt| + |NIt-1|) - simplified
            chin = 0  # Would need previous year data

            o_score = (
                -1.32 -
                0.407 * size +
                6.03 * tlta -
                1.43 * wcta +
                0.0757 * clca -
                2.37 * nita -
                1.83 * futl +
                0.285 * intwo -
                1.72 * oeneg -
                0.521 * chin
            )

            return o_score

        except Exception:
            return None

    @staticmethod
    def zmijewski_score(data: FinancialData) -> Optional[float]:
        """
        Zmijewski Financial Distress Score

        3-variable probit model:
        > 0.5 = Higher probability of distress
        < 0.0 = Lower probability

        More conservative than Altman (higher false positive rate).
        """
        try:
            if data.total_assets == 0:
                return None

            # ROA (Return on Assets)
            roa = data.net_income / data.total_assets

            # Leverage (Debt to Assets)
            leverage = data.total_liabilities / data.total_assets

            # Liquidity (Current Ratio)
            liquidity = data.current_assets / data.current_liabilities if data.current_liabilities != 0 else 0

            z_score = -4.3 - 4.5 * roa + 5.7 * leverage - 0.004 * liquidity

            return z_score

        except Exception:
            return None

    @staticmethod
    def calculate_all(current: FinancialData, previous: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """Calculate all enhanced quality scores"""
        metrics = {}

        if previous:
            metrics['beneish_m_score'] = EnhancedQualityScores.beneish_m_score(current, previous)
        else:
            metrics['beneish_m_score'] = None

        metrics['sloan_accruals'] = EnhancedQualityScores.sloan_accruals_quality(current)
        metrics['ohlson_o_score'] = EnhancedQualityScores.ohlson_o_score(current)
        metrics['zmijewski_score'] = EnhancedQualityScores.zmijewski_score(current)

        return metrics


class QualityScores:
    """
    Quality/strength scores for fundamental analysis
    """

    @staticmethod
    def piotroski_f_score(current: FinancialData, previous: FinancialData) -> int:
        """
        Piotroski F-Score (0-9)

        9-point score measuring financial strength:
        - Profitability (4 points)
        - Leverage/Liquidity (3 points)
        - Operating Efficiency (2 points)

        Score >= 7: Strong
        Score 4-6: Average
        Score <= 3: Weak
        """
        score = 0

        # 1. Profitability Signals (4 points)
        # Positive ROA
        avg_assets = (current.total_assets + previous.total_assets) / 2
        if avg_assets > 0:
            roa = current.net_income / avg_assets
            if roa > 0:
                score += 1

        # Positive Operating Cash Flow
        if current.operating_cash_flow > 0:
            score += 1

        # ROA increase (current vs previous)
        if previous.total_assets > 0:
            prev_roa = previous.net_income / previous.total_assets
            curr_roa = current.net_income / current.total_assets if current.total_assets > 0 else 0
            if curr_roa > prev_roa:
                score += 1

        # Quality of Earnings (Accruals < 0)
        # Accruals = Net Income - Operating Cash Flow
        accruals = current.net_income - current.operating_cash_flow
        if accruals < 0:  # Cash earnings > accrual earnings
            score += 1

        # 2. Leverage, Liquidity, and Source of Funds (3 points)
        # Decrease in long-term debt
        if current.long_term_debt < previous.long_term_debt:
            score += 1

        # Increase in current ratio
        curr_current_ratio = current.current_assets / current.current_liabilities if current.current_liabilities > 0 else 0
        prev_current_ratio = previous.current_assets / previous.current_liabilities if previous.current_liabilities > 0 else 0
        if curr_current_ratio > prev_current_ratio:
            score += 1

        # No new shares issued (shares outstanding decreased or stayed same)
        if current.shares_outstanding <= previous.shares_outstanding:
            score += 1

        # 3. Operating Efficiency (2 points)
        # Increase in gross margin
        curr_gross_margin = current.gross_profit / current.revenue if current.revenue > 0 else 0
        prev_gross_margin = previous.gross_profit / previous.revenue if previous.revenue > 0 else 0
        if curr_gross_margin > prev_gross_margin:
            score += 1

        # Increase in asset turnover
        curr_asset_turnover = current.revenue / current.total_assets if current.total_assets > 0 else 0
        prev_asset_turnover = previous.revenue / previous.total_assets if previous.total_assets > 0 else 0
        if curr_asset_turnover > prev_asset_turnover:
            score += 1

        return score

    @staticmethod
    def altman_z_score(data: FinancialData) -> Optional[float]:
        """
        Altman Z-Score (Bankruptcy Prediction)

        Z = 1.2×(WC/TA) + 1.4×(RE/TA) + 3.3×(EBIT/TA) + 0.6×(MVE/TL) + 1.0×(Sales/TA)

        Where:
        - WC = Working Capital
        - TA = Total Assets
        - RE = Retained Earnings
        - MVE = Market Value of Equity (approximated as book value if market cap unavailable)
        - TL = Total Liabilities

        Interpretation:
        - Z > 2.99: Safe zone
        - 1.81 < Z < 2.99: Grey zone
        - Z < 1.81: Distress zone

        Note: This uses book value for equity since market cap may not be available
        """
        if data.total_assets == 0 or data.total_liabilities == 0:
            return None

        wc = data.current_assets - data.current_liabilities
        ta = data.total_assets
        re = data.retained_earnings if hasattr(data, 'retained_earnings') else data.total_equity  # Approximation
        ebit = data.ebit
        mve = data.total_equity  # Using book value as proxy for market value
        tl = data.total_liabilities
        sales = data.revenue

        z_score = (
            1.2 * (wc / ta) +
            1.4 * (re / ta) +
            3.3 * (ebit / ta) +
            0.6 * (mve / tl) +
            1.0 * (sales / ta)
        )

        return z_score

    @staticmethod
    def calculate_all(current: FinancialData, previous: Optional[FinancialData] = None) -> Dict[str, Optional[float]]:
        """Calculate all quality scores"""
        metrics = {}

        if previous:
            metrics['piotroski_score'] = QualityScores.piotroski_f_score(current, previous)
        else:
            metrics['piotroski_score'] = None

        metrics['altman_z_score'] = QualityScores.altman_z_score(current)

        return metrics


class ComprehensiveMetricsCalculator:
    """
    Main calculator that computes all metrics for a given company and period
    """

    @staticmethod
    def calculate_all_metrics(
        current: FinancialData,
        previous: Optional[FinancialData] = None,
        historical: Optional[List[FinancialData]] = None,
        earnings_growth_rate: Optional[float] = None,
        wacc: Optional[float] = None,
        margins_5y: Optional[List[float]] = None,
        revenues_5y: Optional[List[float]] = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculate all fundamental analysis metrics

        Args:
            current: Current period financial data
            previous: Previous period data (for period-over-period comparisons)
            historical: List of historical periods (for growth calculations)
            earnings_growth_rate: YoY earnings growth rate (for PEG ratio)
            wacc: Weighted Average Cost of Capital (for ROIC spread)
            margins_5y: List of 5-year gross margins (for stability analysis)
            revenues_5y: List of 5-year revenues (for consistency analysis)

        Returns:
            Dictionary with all calculated metrics (70+ metrics)
        """
        all_metrics = {}

        # ===== ORIGINAL METRICS =====

        # Liquidity
        all_metrics.update(LiquidityMetrics.calculate_all(current))

        # Leverage
        all_metrics.update(LeverageMetrics.calculate_all(current))

        # Efficiency (requires previous period for averages)
        all_metrics.update(EfficiencyMetrics.calculate_all(current, previous))

        # Profitability
        all_metrics.update(ProfitabilityMetrics.calculate_all(current))

        # Returns (requires previous period for averages)
        all_metrics.update(ReturnMetrics.calculate_all(current, previous))

        # Growth (requires historical data)
        if historical:
            all_metrics.update(GrowthMetrics.calculate_growth_rates(current, historical))

        # Per-Share
        all_metrics.update(PerShareMetrics.calculate_all(current))

        # Quality Scores (requires previous period)
        all_metrics.update(QualityScores.calculate_all(current, previous))

        # ===== NEW METRICS (2025) =====

        # Cash Flow Quality
        all_metrics.update(CashFlowQualityMetrics.calculate_all(current, previous))

        # Shareholder Value
        all_metrics.update(ShareholderValueMetrics.calculate_all(current))

        # Balance Sheet Quality
        all_metrics.update(BalanceSheetQualityMetrics.calculate_all(current, previous))

        # Valuation (requires market data)
        all_metrics.update(ValuationMetrics.calculate_all(current, earnings_growth_rate))

        # Working Capital
        all_metrics.update(WorkingCapitalMetrics.calculate_all(current, previous))

        # Detailed Profitability
        all_metrics.update(DetailedProfitabilityMetrics.calculate_all(current))

        # Competitive Advantage
        all_metrics.update(CompetitiveAdvantageMetrics.calculate_all(
            current,
            margins_5y=margins_5y,
            revenues_5y=revenues_5y,
            wacc=wacc
        ))

        # Enhanced Quality Scores
        all_metrics.update(EnhancedQualityScores.calculate_all(current, previous))

        # Add metadata
        all_metrics['symbol'] = current.symbol
        all_metrics['date'] = current.date
        all_metrics['period_type'] = current.period_type

        return all_metrics


# Example usage
if __name__ == "__main__":
    # Example: Calculate metrics for sample data
    sample_data = FinancialData(
        # Balance Sheet
        total_assets=1000000,
        total_liabilities=400000,
        total_equity=600000,
        current_assets=300000,
        current_liabilities=150000,
        cash=50000,
        short_term_investments=30000,
        inventory=80000,
        receivables=70000,
        accounts_payable=60000,
        short_term_debt=50000,
        long_term_debt=200000,
        intangible_assets=20000,
        goodwill=10000,
        ppe_net=500000,
        # Income Statement
        revenue=800000,
        cost_of_revenue=400000,
        gross_profit=400000,
        operating_expenses=200000,
        operating_income=200000,
        ebitda=250000,
        ebit=220000,
        interest_expense=20000,
        income_before_tax=200000,
        income_tax=40000,
        net_income=160000,
        eps_diluted=4.0,
        # Cash Flow
        operating_cash_flow=180000,
        investing_cash_flow=-50000,
        financing_cash_flow=-30000,
        free_cash_flow=130000,
        capex=50000,
        # Share Data
        shares_outstanding=40000,
        # Shareholder Returns (NEW)
        dividends_paid=60000,
        share_buybacks=20000,
        # Market Data (NEW)
        market_price=50.0,
        market_cap=2000000,
        enterprise_value=2120000,  # Market cap + net debt
        # Additional Fields (NEW)
        retained_earnings=400000,
        depreciation_amortization=30000,
        rd_expense=40000,
        sga_expense=100000,
        num_employees=500,
        # Metadata
        date=datetime(2024, 3, 31),
        symbol="EXAMPLE",
        period_type="yearly"
    )

    # Calculate all metrics (70+ metrics)
    metrics = ComprehensiveMetricsCalculator.calculate_all_metrics(
        current=sample_data,
        earnings_growth_rate=15.0,  # 15% YoY growth
        wacc=10.0  # 10% weighted average cost of capital
    )

    print("=" * 70)
    print("COMPREHENSIVE FINANCIAL METRICS ANALYSIS")
    print("=" * 70)
    print(f"Symbol: {metrics.get('symbol')}")
    print(f"Date: {metrics.get('date')}")
    print(f"Period: {metrics.get('period_type')}")
    print("=" * 70)

    # Group metrics by category for better readability
    categories = {
        'Liquidity': ['current_ratio', 'quick_ratio', 'cash_ratio', 'working_capital'],
        'Leverage': ['debt_to_equity', 'debt_to_assets', 'interest_coverage', 'net_debt_to_ebitda'],
        'Profitability': ['gross_margin', 'operating_margin', 'net_margin', 'ebitda_margin', 'fcf_margin'],
        'Returns': ['roe', 'roa', 'roic'],
        'Cash Flow Quality': ['cash_flow_to_net_income', 'fcf_conversion', 'operating_cf_margin'],
        'Shareholder Value': ['dividend_payout_ratio', 'total_shareholder_yield', 'earnings_retention_rate'],
        'Valuation': ['pe_ratio', 'price_to_book', 'ev_to_ebitda', 'earnings_yield', 'fcf_yield'],
        'Balance Sheet Quality': ['tangible_asset_ratio', 'net_debt', 'cash_to_debt_ratio'],
        'Quality Scores': ['piotroski_score', 'altman_z_score', 'beneish_m_score', 'zmijewski_score'],
    }

    for category, metric_keys in categories.items():
        print(f"\n{category}:")
        print("-" * 70)
        for key in metric_keys:
            value = metrics.get(key)
            if value is not None:
                if isinstance(value, int):
                    print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: N/A")

    print("\n" + "=" * 70)
    print(f"TOTAL METRICS CALCULATED: {len([k for k, v in metrics.items() if v is not None])}")
    print("=" * 70)

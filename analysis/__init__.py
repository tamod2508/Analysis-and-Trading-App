"""
Fundamental Analysis Module

This module provides comprehensive financial metric calculations for stock analysis.

Key Components:
- LiquidityMetrics: Current ratio, quick ratio, cash ratio
- LeverageMetrics: Debt-to-equity, interest coverage, debt service coverage
- EfficiencyMetrics: Asset turnover, inventory turnover, cash conversion cycle
- ProfitabilityMetrics: Gross/operating/net margins, EBITDA/FCF margins
- ReturnMetrics: ROE, ROA, ROIC, DuPont analysis
- GrowthMetrics: YoY growth, CAGR (1Y/3Y/5Y)
- PerShareMetrics: Book value, FCF per share, tangible book value
- QualityScores: Piotroski F-Score, Altman Z-Score

Usage:
    from analysis import ComprehensiveMetricsCalculator, FinancialData

    # Create financial data object
    data = FinancialData(...)

    # Calculate all metrics
    metrics = ComprehensiveMetricsCalculator.calculate_all_metrics(data)
"""

from analysis.analysis_metrics import (
    FinancialData,
    LiquidityMetrics,
    LeverageMetrics,
    EfficiencyMetrics,
    ProfitabilityMetrics,
    ReturnMetrics,
    GrowthMetrics,
    PerShareMetrics,
    QualityScores,
    ComprehensiveMetricsCalculator,
)

__all__ = [
    'FinancialData',
    'LiquidityMetrics',
    'LeverageMetrics',
    'EfficiencyMetrics',
    'ProfitabilityMetrics',
    'ReturnMetrics',
    'GrowthMetrics',
    'PerShareMetrics',
    'QualityScores',
    'ComprehensiveMetricsCalculator',
]

__version__ = '1.0.0'

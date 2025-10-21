"""
Analysis module configuration and QuestDB table schemas

Defines the database schema for storing fundamental analysis metrics in QuestDB.

Usage:
    from analysis.config import get_all_analysis_schemas

    schemas = get_all_analysis_schemas()
    for schema in schemas:
        client.execute_query(schema.create_sql)
"""

from typing import List
from dataclasses import dataclass


@dataclass
class TableSchema:
    """Schema definition for a QuestDB table"""
    name: str
    create_sql: str
    description: str


class AnalysisTableSchemas:
    """
    QuestDB table schemas for fundamental analysis metrics

    All metrics are stored as time-series with partitioning for efficient querying.
    """

    @staticmethod
    def get_liquidity_metrics_schema() -> TableSchema:
        """
        Liquidity metrics table

        Stores short-term debt-paying ability metrics
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS liquidity_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            current_ratio DOUBLE,
            quick_ratio DOUBLE,
            cash_ratio DOUBLE,
            working_capital DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='liquidity_metrics',
            create_sql=create_sql,
            description='Short-term debt-paying ability metrics'
        )

    @staticmethod
    def get_leverage_metrics_schema() -> TableSchema:
        """
        Leverage/solvency metrics table

        Stores debt and long-term obligation metrics
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS leverage_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            debt_to_equity DOUBLE,
            debt_to_assets DOUBLE,
            equity_ratio DOUBLE,
            interest_coverage DOUBLE,
            debt_service_coverage DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='leverage_metrics',
            create_sql=create_sql,
            description='Debt and solvency metrics'
        )

    @staticmethod
    def get_efficiency_metrics_schema() -> TableSchema:
        """
        Efficiency/activity metrics table

        Stores asset utilization and turnover metrics
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS efficiency_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            asset_turnover DOUBLE,
            inventory_turnover DOUBLE,
            days_inventory_outstanding DOUBLE,
            receivables_turnover DOUBLE,
            days_sales_outstanding DOUBLE,
            payables_turnover DOUBLE,
            days_payable_outstanding DOUBLE,
            cash_conversion_cycle DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='efficiency_metrics',
            create_sql=create_sql,
            description='Asset utilization and turnover metrics'
        )

    @staticmethod
    def get_profitability_metrics_schema() -> TableSchema:
        """
        Profitability metrics table

        Stores profit margin metrics
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS profitability_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            gross_margin DOUBLE,
            operating_margin DOUBLE,
            net_margin DOUBLE,
            ebitda_margin DOUBLE,
            fcf_margin DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='profitability_metrics',
            create_sql=create_sql,
            description='Profit margin metrics'
        )

    @staticmethod
    def get_return_metrics_schema() -> TableSchema:
        """
        Return metrics table

        Stores return on capital metrics and DuPont analysis
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS return_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            roe DOUBLE,
            roa DOUBLE,
            roic DOUBLE,
            dupont_net_margin DOUBLE,
            dupont_asset_turnover DOUBLE,
            dupont_equity_multiplier DOUBLE,
            roe_dupont DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='return_metrics',
            create_sql=create_sql,
            description='Return on capital metrics and DuPont analysis'
        )

    @staticmethod
    def get_growth_metrics_schema() -> TableSchema:
        """
        Growth metrics table

        Stores year-over-year and CAGR metrics
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS growth_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            revenue_growth_yoy DOUBLE,
            earnings_growth_yoy DOUBLE,
            fcf_growth_yoy DOUBLE,
            equity_growth_yoy DOUBLE,
            revenue_cagr_3y DOUBLE,
            earnings_cagr_3y DOUBLE,
            fcf_cagr_3y DOUBLE,
            revenue_cagr_5y DOUBLE,
            earnings_cagr_5y DOUBLE,
            fcf_cagr_5y DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='growth_metrics',
            create_sql=create_sql,
            description='Year-over-year and CAGR growth metrics'
        )

    @staticmethod
    def get_per_share_metrics_schema() -> TableSchema:
        """
        Per-share metrics table

        Stores normalized per-share values
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS per_share_metrics (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            book_value_per_share DOUBLE,
            tangible_book_value_per_share DOUBLE,
            fcf_per_share DOUBLE,
            operating_cf_per_share DOUBLE,
            revenue_per_share DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='per_share_metrics',
            create_sql=create_sql,
            description='Normalized per-share values'
        )

    @staticmethod
    def get_quality_scores_schema() -> TableSchema:
        """
        Quality/strength scores table

        Stores fundamental quality indicators
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS quality_scores (
            calculated_at TIMESTAMP,
            symbol SYMBOL,
            period_date TIMESTAMP,
            period_type SYMBOL,
            piotroski_score INT,
            altman_z_score DOUBLE
        ) TIMESTAMP(calculated_at) PARTITION BY MONTH;
        """

        return TableSchema(
            name='quality_scores',
            create_sql=create_sql,
            description='Fundamental quality indicators (Piotroski, Altman Z-Score)'
        )


def get_all_analysis_schemas() -> List[TableSchema]:
    """
    Get all analysis table schemas

    Returns:
        List of TableSchema objects for all analysis tables
    """
    return [
        AnalysisTableSchemas.get_liquidity_metrics_schema(),
        AnalysisTableSchemas.get_leverage_metrics_schema(),
        AnalysisTableSchemas.get_efficiency_metrics_schema(),
        AnalysisTableSchemas.get_profitability_metrics_schema(),
        AnalysisTableSchemas.get_return_metrics_schema(),
        AnalysisTableSchemas.get_growth_metrics_schema(),
        AnalysisTableSchemas.get_per_share_metrics_schema(),
        AnalysisTableSchemas.get_quality_scores_schema(),
    ]


def get_create_all_sql() -> str:
    """
    Get SQL to create all analysis tables

    Returns:
        Combined SQL CREATE statements
    """
    schemas = get_all_analysis_schemas()
    return '\n\n'.join(schema.create_sql for schema in schemas)


# Metric categories for reference
METRIC_CATEGORIES = {
    'liquidity': ['current_ratio', 'quick_ratio', 'cash_ratio', 'working_capital'],
    'leverage': ['debt_to_equity', 'debt_to_assets', 'equity_ratio', 'interest_coverage', 'debt_service_coverage'],
    'efficiency': ['asset_turnover', 'inventory_turnover', 'days_inventory_outstanding',
                   'receivables_turnover', 'days_sales_outstanding', 'payables_turnover',
                   'days_payable_outstanding', 'cash_conversion_cycle'],
    'profitability': ['gross_margin', 'operating_margin', 'net_margin', 'ebitda_margin', 'fcf_margin'],
    'returns': ['roe', 'roa', 'roic', 'dupont_net_margin', 'dupont_asset_turnover',
                'dupont_equity_multiplier', 'roe_dupont'],
    'growth': ['revenue_growth_yoy', 'earnings_growth_yoy', 'fcf_growth_yoy', 'equity_growth_yoy',
               'revenue_cagr_3y', 'earnings_cagr_3y', 'fcf_cagr_3y',
               'revenue_cagr_5y', 'earnings_cagr_5y', 'fcf_cagr_5y'],
    'per_share': ['book_value_per_share', 'tangible_book_value_per_share', 'fcf_per_share',
                  'operating_cf_per_share', 'revenue_per_share'],
    'quality': ['piotroski_score', 'altman_z_score'],
}


__all__ = [
    'TableSchema',
    'AnalysisTableSchemas',
    'get_all_analysis_schemas',
    'get_create_all_sql',
    'METRIC_CATEGORIES',
]

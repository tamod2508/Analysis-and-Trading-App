"""
QuestDB Saver for Analysis Metrics

Saves calculated fundamental analysis metrics to QuestDB.

Usage:
    from analysis.questdb_saver import AnalysisMetricsSaver
    from analysis.analysis_metrics import ComprehensiveMetricsCalculator, FinancialData

    # Calculate metrics
    metrics = ComprehensiveMetricsCalculator.calculate_all_metrics(financial_data)

    # Save to QuestDB
    saver = AnalysisMetricsSaver()
    saver.save_all_metrics(metrics)
"""

from datetime import datetime
from typing import Dict, Optional, List
import logging

from database2.client import QuestDBClient
from analysis.config import METRIC_CATEGORIES

logger = logging.getLogger(__name__)


class AnalysisMetricsSaver:
    """
    Saves fundamental analysis metrics to QuestDB

    Splits metrics by category and saves to appropriate tables.
    """

    def __init__(self, client: QuestDBClient = None):
        """
        Initialize metrics saver

        Args:
            client: QuestDBClient instance (creates new if None)
        """
        self.client = client or QuestDBClient()
        logger.info("Analysis metrics saver initialized")

    def save_all_metrics(
        self,
        metrics: Dict[str, Optional[float]],
        calculated_at: Optional[datetime] = None
    ) -> bool:
        """
        Save all calculated metrics to QuestDB

        Args:
            metrics: Dictionary of calculated metrics (from ComprehensiveMetricsCalculator)
            calculated_at: When metrics were calculated (defaults to now)

        Returns:
            True if all saves successful
        """
        if calculated_at is None:
            calculated_at = datetime.now()

        # Extract metadata
        symbol = metrics.get('symbol', '')
        period_date = metrics.get('date')
        period_type = metrics.get('period_type', 'yearly')

        if not symbol or not period_date:
            logger.error("Missing symbol or period_date in metrics")
            return False

        # Save each category
        success = True
        success &= self._save_liquidity_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_leverage_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_efficiency_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_profitability_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_return_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_growth_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_per_share_metrics(metrics, calculated_at, symbol, period_date, period_type)
        success &= self._save_quality_scores(metrics, calculated_at, symbol, period_date, period_type)

        if success:
            logger.info(f"✅ Saved all metrics for {symbol} ({period_date})")
        else:
            logger.warning(f"⚠️  Some metrics failed to save for {symbol}")

        return success

    def _save_liquidity_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save liquidity metrics to liquidity_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO liquidity_metrics (
                    calculated_at, symbol, period_date, period_type,
                    current_ratio, quick_ratio, cash_ratio, working_capital
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('current_ratio'),
                metrics.get('quick_ratio'),
                metrics.get('cash_ratio'),
                metrics.get('working_capital')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save liquidity metrics: {e}")
            return False

    def _save_leverage_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save leverage metrics to leverage_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO leverage_metrics (
                    calculated_at, symbol, period_date, period_type,
                    debt_to_equity, debt_to_assets, equity_ratio,
                    interest_coverage, debt_service_coverage
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('debt_to_equity'),
                metrics.get('debt_to_assets'),
                metrics.get('equity_ratio'),
                metrics.get('interest_coverage'),
                metrics.get('debt_service_coverage')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save leverage metrics: {e}")
            return False

    def _save_efficiency_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save efficiency metrics to efficiency_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO efficiency_metrics (
                    calculated_at, symbol, period_date, period_type,
                    asset_turnover, inventory_turnover, days_inventory_outstanding,
                    receivables_turnover, days_sales_outstanding,
                    payables_turnover, days_payable_outstanding, cash_conversion_cycle
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('asset_turnover'),
                metrics.get('inventory_turnover'),
                metrics.get('days_inventory_outstanding'),
                metrics.get('receivables_turnover'),
                metrics.get('days_sales_outstanding'),
                metrics.get('payables_turnover'),
                metrics.get('days_payable_outstanding'),
                metrics.get('cash_conversion_cycle')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save efficiency metrics: {e}")
            return False

    def _save_profitability_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save profitability metrics to profitability_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO profitability_metrics (
                    calculated_at, symbol, period_date, period_type,
                    gross_margin, operating_margin, net_margin,
                    ebitda_margin, fcf_margin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('gross_margin'),
                metrics.get('operating_margin'),
                metrics.get('net_margin'),
                metrics.get('ebitda_margin'),
                metrics.get('fcf_margin')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save profitability metrics: {e}")
            return False

    def _save_return_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save return metrics to return_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO return_metrics (
                    calculated_at, symbol, period_date, period_type,
                    roe, roa, roic, dupont_net_margin,
                    dupont_asset_turnover, dupont_equity_multiplier, roe_dupont
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('roe'),
                metrics.get('roa'),
                metrics.get('roic'),
                metrics.get('dupont_net_margin'),
                metrics.get('dupont_asset_turnover'),
                metrics.get('dupont_equity_multiplier'),
                metrics.get('roe_dupont')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save return metrics: {e}")
            return False

    def _save_growth_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save growth metrics to growth_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO growth_metrics (
                    calculated_at, symbol, period_date, period_type,
                    revenue_growth_yoy, earnings_growth_yoy, fcf_growth_yoy, equity_growth_yoy,
                    revenue_cagr_3y, earnings_cagr_3y, fcf_cagr_3y,
                    revenue_cagr_5y, earnings_cagr_5y, fcf_cagr_5y
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('revenue_growth_yoy'),
                metrics.get('earnings_growth_yoy'),
                metrics.get('fcf_growth_yoy'),
                metrics.get('equity_growth_yoy'),
                metrics.get('revenue_cagr_3y'),
                metrics.get('earnings_cagr_3y'),
                metrics.get('fcf_cagr_3y'),
                metrics.get('revenue_cagr_5y'),
                metrics.get('earnings_cagr_5y'),
                metrics.get('fcf_cagr_5y')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save growth metrics: {e}")
            return False

    def _save_per_share_metrics(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save per-share metrics to per_share_metrics table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO per_share_metrics (
                    calculated_at, symbol, period_date, period_type,
                    book_value_per_share, tangible_book_value_per_share,
                    fcf_per_share, operating_cf_per_share, revenue_per_share
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('book_value_per_share'),
                metrics.get('tangible_book_value_per_share'),
                metrics.get('fcf_per_share'),
                metrics.get('operating_cf_per_share'),
                metrics.get('revenue_per_share')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save per-share metrics: {e}")
            return False

    def _save_quality_scores(
        self,
        metrics: Dict,
        calculated_at: datetime,
        symbol: str,
        period_date: datetime,
        period_type: str
    ) -> bool:
        """Save quality scores to quality_scores table"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.client.config.HOST,
                port=self.client.config.PG_PORT,
                user=self.client.config.PG_USER,
                password=self.client.config.PG_PASSWORD,
                database=self.client.config.PG_DATABASE
            )

            cur = conn.cursor()
            query = """
                INSERT INTO quality_scores (
                    calculated_at, symbol, period_date, period_type,
                    piotroski_score, altman_z_score
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            cur.execute(query, (
                calculated_at,
                symbol,
                period_date,
                period_type,
                metrics.get('piotroski_score'),
                metrics.get('altman_z_score')
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save quality scores: {e}")
            return False


__all__ = ['AnalysisMetricsSaver']

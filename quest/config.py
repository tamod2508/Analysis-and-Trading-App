"""
QuestDB Configuration - Single Source of Truth

Centralized configuration for all QuestDB operations including:
- Connection settings (HTTP, ILP)
- Table names and schemas
- Partition strategies
- Performance tuning
- Data retention policies
"""

from dataclasses import dataclass
from typing import Dict, List
import os
from pathlib import Path


# ==============================================================================
# CONNECTION SETTINGS
# ==============================================================================

@dataclass
class QuestDBConnectionConfig:
    """QuestDB connection configuration"""

    # HTTP API (for queries)
    http_host: str = os.getenv('QUESTDB_HTTP_HOST', 'localhost')
    http_port: int = int(os.getenv('QUESTDB_HTTP_PORT', '9000'))

    # ILP Protocol (for fast writes)
    ilp_host: str = os.getenv('QUESTDB_ILP_HOST', 'localhost')
    ilp_port: int = int(os.getenv('QUESTDB_ILP_PORT', '9009'))

    #SQL protocol (for queries)
    sql_host: str = os.getenv('QUESTDB_SQL_HOST', 'localhost')
    sql_port: int = int(os.getenv('QUESTDB_SQL_PORT', '5432'))

    # Timeouts
    http_timeout: int = 30 
    ilp_timeout: int = 10   # seconds for ILP writes
    sql_timeout: int = 30   # seconds for SQL queries

    # Connection pooling
    max_connections: int = 10

    @property
    def http_url(self) -> str:
        return f"http://{self.http_host}:{self.http_port}"

    @property
    def ilp_address(self) -> tuple:
        return (self.ilp_host, self.ilp_port)


class TableNames:
    """Centralized table names"""

    # Main OHLCV data
    OHLCV_EQUITY = 'ohlcv_equity'
    OHLCV_DERIVATIVES = 'ohlcv_derivatives'

    # Corporate actions
    CORPORATE_ACTIONS = 'corporate_actions'

    # Audit and logging
    DATA_LINEAGE = 'data_lineage'
    VALIDATION_RESULTS = 'validation_results'

    #Financial Data
    FUNDAMENTAL_DATA = 'fundamental_data'
    COMPANY_INFO = 'company_info'
    EARNINGS_HISTORY = 'earnings_history'
    EARNINGS_ESTIMATE = 'earnings_estimate'
    INSTITUTIONAL_SHAREHOLDERS = 'institutional_shareholders'
    INSIDER_TRADES = 'insider_trades'

    @classmethod
    def all_tables(cls) -> List[str]:
        """Get all table names"""
        return [
            cls.OHLCV_EQUITY,
            cls.OHLCV_DERIVATIVES,
            cls.CORPORATE_ACTIONS,
            cls.DATA_LINEAGE,
            cls.VALIDATION_RESULTS,
            cls.FUNDAMENTAL_DATA,
            cls.COMPANY_INFO,
            cls.EARNINGS_HISTORY,
            cls.EARNINGS_ESTIMATE,
            cls.INSTITUTIONAL_SHAREHOLDERS,
            cls.INSIDER_TRADES
        ]

class ColumnTypes:
    """QuestDB column type definitions"""

    # Timestamp (designated timestamp column)
    TIMESTAMP = 'TIMESTAMP'
    DATE = 'DATE'

    # String types
    SYMBOL = 'SYMBOL'      # Indexed string (for low cardinality: exchange, symbol, interval)
    STRING = 'STRING'      # Regular string (for high cardinality: notes, metadata)

    # Numeric types
    DOUBLE = 'DOUBLE'      # 64-bit floating point (prices)
    LONG = 'LONG'          # 64-bit integer (volume, timestamps)
    INT = 'INT'            # 32-bit integer (counts)

    # Boolean
    BOOLEAN = 'BOOLEAN'


# OHLCV Equity Schema
OHLCV_EQUITY_SCHEMA = {
    'timestamp': ColumnTypes.TIMESTAMP,
    'exchange': ColumnTypes.SYMBOL,
    'symbol': ColumnTypes.SYMBOL,
    'interval': ColumnTypes.SYMBOL,
    'open': ColumnTypes.DOUBLE,
    'high': ColumnTypes.DOUBLE,
    'low': ColumnTypes.DOUBLE,
    'close': ColumnTypes.DOUBLE,
    'volume': ColumnTypes.LONG,
    'prev_close': ColumnTypes.DOUBLE,
    'change_pct': ColumnTypes.DOUBLE,
    'is_anomaly': ColumnTypes.BOOLEAN,
    'adjusted': ColumnTypes.BOOLEAN,
    'data_source': ColumnTypes.SYMBOL,
    'inserted_at': ColumnTypes.TIMESTAMP,
}

# OHLCV Derivatives Schema (includes Open Interest)
OHLCV_DERIVATIVES_SCHEMA = {
    'timestamp': ColumnTypes.TIMESTAMP,
    'exchange': ColumnTypes.SYMBOL,
    'symbol': ColumnTypes.SYMBOL,
    'interval': ColumnTypes.SYMBOL,
    'open': ColumnTypes.DOUBLE,
    'high': ColumnTypes.DOUBLE,
    'low': ColumnTypes.DOUBLE,
    'close': ColumnTypes.DOUBLE,
    'volume': ColumnTypes.LONG,
    'oi': ColumnTypes.LONG,                 # Open Interest
    'prev_close': ColumnTypes.DOUBLE,
    'change_pct': ColumnTypes.DOUBLE,
    'is_anomaly': ColumnTypes.BOOLEAN,
    'adjusted': ColumnTypes.BOOLEAN,
    'data_source': ColumnTypes.SYMBOL,
    'inserted_at': ColumnTypes.TIMESTAMP,
}

# Corporate Actions Schema
CORPORATE_ACTIONS_SCHEMA = {
    'timestamp': ColumnTypes.TIMESTAMP,      # Action date
    'symbol': ColumnTypes.SYMBOL,
    'exchange': ColumnTypes.SYMBOL,
    'detection_date': ColumnTypes.TIMESTAMP,
    'price_change_pct': ColumnTypes.DOUBLE,
    'prev_close': ColumnTypes.DOUBLE,
    'curr_close': ColumnTypes.DOUBLE,
    'suspected_type': ColumnTypes.SYMBOL,    # 'split', 'bonus', 'dividend', 'unknown'
    'suspected_ratio': ColumnTypes.STRING,
    'confidence': ColumnTypes.SYMBOL,        # 'high', 'medium', 'low'
    'status': ColumnTypes.SYMBOL,            # 'pending', 'verified', 'rejected'
    'verified_type': ColumnTypes.SYMBOL,     # After manual verification
    'verified_ratio': ColumnTypes.STRING,
    'adjusted': ColumnTypes.BOOLEAN,
    'adjustment_date': ColumnTypes.TIMESTAMP,
    'notes': ColumnTypes.STRING,
}

# Data Lineage Schema (audit trail)
DATA_LINEAGE_SCHEMA = {
    'timestamp': ColumnTypes.TIMESTAMP,
    'operation': ColumnTypes.SYMBOL,         # 'insert', 'update', 'adjust', 'migrate'
    'table_name': ColumnTypes.SYMBOL,
    'symbol': ColumnTypes.SYMBOL,
    'exchange': ColumnTypes.SYMBOL,
    'interval': ColumnTypes.SYMBOL,
    'rows_affected': ColumnTypes.LONG,
    'source': ColumnTypes.SYMBOL,            # 'kite_api', 'hdf5_migration', 'manual'
    'user': ColumnTypes.STRING,
    'success': ColumnTypes.BOOLEAN,
    'error': ColumnTypes.STRING,
    'duration_ms': ColumnTypes.LONG,
    'metadata': ColumnTypes.STRING,          # JSON string with additional details
}

# Validation Results Schema
VALIDATION_RESULTS_SCHEMA = {
    'timestamp': ColumnTypes.TIMESTAMP,
    'symbol': ColumnTypes.SYMBOL,
    'exchange': ColumnTypes.SYMBOL,
    'interval': ColumnTypes.SYMBOL,
    'is_valid': ColumnTypes.BOOLEAN,
    'error_count': ColumnTypes.INT,
    'warning_count': ColumnTypes.INT,
    'anomaly_count': ColumnTypes.INT,
    'total_rows': ColumnTypes.LONG,
    'errors': ColumnTypes.STRING,            # JSON array
    'warnings': ColumnTypes.STRING,          # JSON array
    'anomalies': ColumnTypes.STRING,         # JSON array
}

FUNDAMENTALS_DATA_SCHEMA = { 
    "timestamp" :ColumnTypes.TIMESTAMP,                    
    "symbol" :ColumnTypes.SYMBOL,
    "exchange" :ColumnTypes.SYMBOL,
    "period_type" :ColumnTypes.SYMBOL,                   # 'yearly', 'quarterly'
    "fiscal_year": ColumnTypes.INT,                      # 2024, 2025
    "fiscal_quarter" :ColumnTypes.INT,                   # 1, 2, 3, 4, NULL for yearly
    "fetched_at" :ColumnTypes.TIMESTAMP,
    "currency_symbol" :ColumnTypes.SYMBOL,               # 'INR', 'USD'
    
    #Balance Sheet (prefix: bs_)
    "bs_total_assets" :ColumnTypes.DOUBLE,
    "bs_current_assets" :ColumnTypes.DOUBLE,
    "bs_cash" :ColumnTypes.DOUBLE,
    "bs_short_term_investments" :ColumnTypes.DOUBLE,
    "bs_net_receivables" :ColumnTypes.DOUBLE,
    "bs_inventory" :ColumnTypes.DOUBLE,
    "bs_other_current_assets" :ColumnTypes.DOUBLE,
    "bs_long_term_investments" :ColumnTypes.DOUBLE,
    "bs_ppe_net" :ColumnTypes.DOUBLE,                    # Property, Plant & Equipment
    "bs_goodwill":ColumnTypes.DOUBLE,
    "bs_intangible_assets" :ColumnTypes.DOUBLE,
    "bs_other_assets" :ColumnTypes.DOUBLE,
    
    "bs_total_liabilities": ColumnTypes.DOUBLE,
    "bs_current_liabilities": ColumnTypes.DOUBLE,
    "bs_short_term_debt" :ColumnTypes.DOUBLE,
    "bs_accounts_payable" :ColumnTypes.DOUBLE,
    "bs_other_current_liabilities":ColumnTypes. DOUBLE,
    "bs_long_term_debt" :ColumnTypes.DOUBLE,
    "bs_deferred_tax_liabilities" :ColumnTypes.DOUBLE,
    "bs_other_liabilities" :ColumnTypes.DOUBLE,
    
    "bs_total_equity" :ColumnTypes.DOUBLE,
    "bs_common_stock" :ColumnTypes.DOUBLE,
    "bs_retained_earnings" :ColumnTypes.DOUBLE,
    "bs_treasury_stock" :ColumnTypes.DOUBLE,
    "bs_capital_surplus" :ColumnTypes.DOUBLE,
    "bs_minority_interest" :ColumnTypes.DOUBLE,
    
    #Income Statement (prefix: inc_)
    "inc_revenue" :ColumnTypes.DOUBLE,
    "inc_cost_of_revenue" :ColumnTypes.DOUBLE,
    "inc_gross_profit" :ColumnTypes.DOUBLE,
    "inc_operating_expenses": ColumnTypes.DOUBLE,
    "inc_rd_expenses" :ColumnTypes.DOUBLE,
    "inc_sg_and_a" :ColumnTypes.DOUBLE,                   #Selling, General & Admin
    "inc_operating_income" :ColumnTypes.DOUBLE,
    "inc_ebitda" :ColumnTypes.DOUBLE,
    "inc_ebit" :ColumnTypes.DOUBLE,
    "inc_interest_expense" :ColumnTypes.DOUBLE,
    "inc_other_income_expense" :ColumnTypes.DOUBLE,
    "inc_income_before_tax" :ColumnTypes.DOUBLE,
    "inc_income_tax" :ColumnTypes.DOUBLE,
    "inc_net_income_continuing" :ColumnTypes.DOUBLE,
    "inc_net_income" :ColumnTypes.DOUBLE,
    "inc_eps_basic" :ColumnTypes.DOUBLE,
    "inc_eps_diluted" :ColumnTypes.DOUBLE,
    "inc_weighted_avg_shares" :ColumnTypes.DOUBLE,
    "inc_weighted_avg_shares_diluted" :ColumnTypes.DOUBLE,
    "inc_depreciation" :ColumnTypes.DOUBLE,
    "inc_amortization" :ColumnTypes.DOUBLE,
    
    #Cash Flow (prefix: cf_)
    "cf_operating_cash_flow" :ColumnTypes.DOUBLE,
    "cf_net_income" :ColumnTypes.DOUBLE,
    "cf_depreciation_amortization" :ColumnTypes.DOUBLE,
    "cf_change_working_capital": ColumnTypes.DOUBLE,
    "cf_change_receivables": ColumnTypes.DOUBLE,
    "cf_change_inventory": ColumnTypes.DOUBLE,
    "cf_change_payables" :ColumnTypes.DOUBLE,
    "cf_other_operating_activities": ColumnTypes.DOUBLE,
    
    "cf_investing_cash_flow" :ColumnTypes.DOUBLE,
    "cf_capex" :ColumnTypes.DOUBLE,
    "cf_investments" :ColumnTypes.DOUBLE,
    "cf_acquisitions" :ColumnTypes.DOUBLE,
    "cf_other_investing_activities" :ColumnTypes.DOUBLE,
    
    "cf_financing_cash_flow" :ColumnTypes.DOUBLE,
    "cf_dividends_paid" :ColumnTypes.DOUBLE,
    "cf_stock_issued_repurchased" :ColumnTypes.DOUBLE,
    "cf_debt_issued_repaid":ColumnTypes.DOUBLE,
    "cf_other_financing_activities" :ColumnTypes.DOUBLE,
    
    "cf_net_change_cash" :ColumnTypes.DOUBLE,
    "cf_free_cash_flow" :ColumnTypes.DOUBLE,             # Calculated: Operating CF - CapEx
    "cf_beginning_cash" :ColumnTypes.DOUBLE,
    "cf_ending_cash" :ColumnTypes.DOUBLE,
    
    #Data completeness flags
    "has_balance_sheet" :ColumnTypes.BOOLEAN,
    "has_income_statement" :ColumnTypes.BOOLEAN,
    "has_cash_flow" :ColumnTypes.BOOLEAN,
    
 }

COMPANY_INFO_SCHEMA = {
    "timestamp" :ColumnTypes.TIMESTAMP,                   # last_updated (designated timestamp)
    "symbol":ColumnTypes.SYMBOL,
    "exchange" :ColumnTypes.SYMBOL,
    
    #  General Info (from EODHD General section)
    "company_name" :ColumnTypes.STRING,
    "sector" :ColumnTypes.SYMBOL,                          
    "industry" :ColumnTypes.STRING,                        
    "gic_sector" :ColumnTypes.SYMBOL,
    "gic_group" :ColumnTypes.SYMBOL,
    "gic_industry" :ColumnTypes.SYMBOL,
    "description" :ColumnTypes.STRING,                    
    "website" :ColumnTypes.STRING,
    
    "isin" :ColumnTypes.STRING,                            
    "fiscal_year_end" :ColumnTypes.STRING,                 
    "ipo_date" :ColumnTypes.DATE,
    "full_time_employees" :ColumnTypes.INT,
    
    # Current Metrics (from Highlights - updated frequently)
    "market_cap" :ColumnTypes.DOUBLE,
    "market_cap_mln" :ColumnTypes.DOUBLE,
    
    #Valuation Ratios
    "pe_ratio" :ColumnTypes.DOUBLE,
    "peg_ratio" :ColumnTypes.DOUBLE,
    "price_to_sales" :ColumnTypes.DOUBLE,
    "price_to_book" :ColumnTypes.DOUBLE,
    "ev" :ColumnTypes.DOUBLE,                              
    "ev_to_revenue" :ColumnTypes.DOUBLE,
    "ev_to_ebitda" :ColumnTypes.DOUBLE,
    
    # Profitability Metrics
    "profit_margin_ttm" :ColumnTypes.DOUBLE,
    "operating_margin_ttm" :ColumnTypes.DOUBLE,
    "return_on_assets_ttm" :ColumnTypes.DOUBLE,
    "return_on_equity_ttm" :ColumnTypes.DOUBLE,
    "revenue_ttm" :ColumnTypes.DOUBLE,
    "revenue_per_share_ttm" :ColumnTypes.DOUBLE,
    "gross_profit_ttm" :ColumnTypes.DOUBLE,
    "ebitda_ttm" :ColumnTypes.DOUBLE,
    
    #Per-Share Metrics
    "book_value" :ColumnTypes.DOUBLE,
    "eps_ttm" :ColumnTypes.DOUBLE,
    "eps_estimate_current_year" :ColumnTypes.DOUBLE,
    "eps_estimate_next_year" :ColumnTypes.DOUBLE,
    
    # Dividend Info
    "dividend_per_share" :ColumnTypes.DOUBLE,
    "dividend_yield" :ColumnTypes.DOUBLE,
    "dividend_date" :ColumnTypes.DATE,
    "ex_dividend_date" :ColumnTypes.DATE,
    "payout_ratio" :ColumnTypes.DOUBLE,
    
    # Growth Metrics
    "quarterly_earnings_growth_yoy" :ColumnTypes.DOUBLE,
    "quarterly_revenue_growth_yoy" :ColumnTypes.DOUBLE,
    "revenue_growth_3y" :ColumnTypes.DOUBLE,
    "revenue_growth_5y" :ColumnTypes.DOUBLE,
    
    # Share Statistics
    "shares_outstanding" :ColumnTypes.DOUBLE,
    "shares_float" :ColumnTypes.DOUBLE,
    "percent_insiders" :ColumnTypes.DOUBLE,
    "percent_institutions" :ColumnTypes.DOUBLE,
    "shares_short" :ColumnTypes.DOUBLE,
    "short_ratio" :ColumnTypes.DOUBLE,
    
    # Technical Indicators (optional)
    "beta" :ColumnTypes.DOUBLE,
    "week_52_high" :ColumnTypes.DOUBLE,
    "week_52_low" :ColumnTypes.DOUBLE,
    "day_50_ma" :ColumnTypes.DOUBLE,
    "day_200_ma" :ColumnTypes.DOUBLE,
    
    # Analyst Ratings
    "analyst_rating" :ColumnTypes.STRING,                 
    "analyst_target_price" :ColumnTypes.DOUBLE,
    "analyst_count" :ColumnTypes.INT,
    
    # Metadata
    "data_source" :ColumnTypes.SYMBOL,                    
    "fetched_at" :ColumnTypes.TIMESTAMP,
    
}

EARNINGS_HISTORY_SCHEMA = {
    "timestamp" :ColumnTypes.TIMESTAMP,                    # report_date (designated)
    "symbol" :ColumnTypes.SYMBOL,
    "exchange" :ColumnTypes.SYMBOL,
    
    #Period info
    "period_end_date" :ColumnTypes.DATE,                   # Quarter end date
    "report_date" :ColumnTypes.DATE,                       # When reported
    "before_after_market" :ColumnTypes.SYMBOL,             #'BeforeMarket', 'AfterMarket'
    
    #EPS data
    "eps_actual" :ColumnTypes.DOUBLE,
    "eps_estimate" :ColumnTypes.DOUBLE,                    
    "eps_difference" :ColumnTypes.DOUBLE,
    "surprise_percent" :ColumnTypes.DOUBLE,
    
    #Metadata
    "currency" :ColumnTypes.SYMBOL,
    "data_source" :ColumnTypes.SYMBOL,
    "fetched_at" :ColumnTypes.TIMESTAMP
}

EARNINGS_ESTIMATE_SCHEMA = {
    "timestamp" :ColumnTypes.TIMESTAMP,                    # estimate_date (designated)
    "symbol" :ColumnTypes.SYMBOL,
    "exchange" :ColumnTypes.SYMBOL,
    
    # Period info
    "period_end_date" :ColumnTypes.DATE,                   # Future quarter/year
    "period_type" :ColumnTypes.SYMBOL,                     # '0q' (current Q), '+1q', '0y', '+1y'
    
    # EPS Consensus Estimates
    "eps_estimate_avg" :ColumnTypes.DOUBLE,                
    "eps_estimate_low" :ColumnTypes.DOUBLE,               
    "eps_estimate_high" :ColumnTypes.DOUBLE,               
    "analyst_count_eps" :ColumnTypes.INT,                  # Number of analysts
    "eps_growth_estimate" :ColumnTypes.DOUBLE,             # Expected growth
    
    # Revenue Consensus Estimates
    "revenue_estimate_avg" :ColumnTypes.DOUBLE,           
    "revenue_estimate_low" :ColumnTypes.DOUBLE,            
    "revenue_estimate_high" :ColumnTypes.DOUBLE,           
    "analyst_count_revenue" :ColumnTypes.INT,             
    "revenue_growth_estimate" :ColumnTypes.DOUBLE,         
    
    # EPS Estimate Trends (showing revisions)
    "eps_trend_current" :ColumnTypes.DOUBLE,               #Current estimate
    "eps_trend_7days_ago" :ColumnTypes.DOUBLE,
    "eps_trend_30days_ago" :ColumnTypes.DOUBLE,            
    "eps_trend_60days_ago" :ColumnTypes.DOUBLE,            
    "eps_trend_90days_ago" :ColumnTypes.DOUBLE,           
    
    #Analyst Revisions (sentiment indicator)
    "eps_revisions_up_last_7days" :ColumnTypes.INT,        #How many upgraded
    "eps_revisions_down_last_7days" :ColumnTypes.INT,      #How many downgraded
    "eps_revisions_up_last_30days" :ColumnTypes.INT,       
    "eps_revisions_down_last_30days" :ColumnTypes.INT,     
    
    #Metadata
    "data_source" :ColumnTypes.SYMBOL,
    "fetched_at" :ColumnTypes.TIMESTAMP,
}

INSTITUTIONAL_SHAREHOLDERS_SCHEMA = {
    "timestamp" :ColumnTypes.TIMESTAMP,                    #filing_date (designated timestamp)
    "symbol" :ColumnTypes.SYMBOL,
    "exchange" :ColumnTypes.SYMBOL,
    
    # Holder Information
    "holder_name" :ColumnTypes.STRING,                     # Institution/Fund name
    "holder_type" :ColumnTypes.SYMBOL,                     # 'mutual_fund', 'hedge_fund', 'pension', 'insurance', 'bank', 'other'
    
    # Holding Details
    "shares_held" :ColumnTypes.LONG,                       # Number of shares held
    "percent_of_shares" :ColumnTypes.DOUBLE,               # % of company's total shares
    "market_value" :ColumnTypes.DOUBLE,                    # Market value of holding (in INR)
    
    # Changes Since Last Filing
    "shares_change" :ColumnTypes.LONG,                     # Change in shares (+ or -)
    "shares_change_percent" :ColumnTypes.DOUBLE,           # % change in shares
    
    # Holder Portfolio Context
    "holder_total_assets" :ColumnTypes.DOUBLE,             # Total AUM of the holder
    "portfolio_percent" :ColumnTypes.DOUBLE,               # % of holder's portfolio this represents
    
    # Activity Classification
    "activity_type" :ColumnTypes.SYMBOL,                   # 'new_position', 'add', 'reduce', 'sold_out', 'no_change'
    
    # Filing Info
    "filing_date" :ColumnTypes.DATE,                       # Date of filing
    "period_end_date" :ColumnTypes.DATE,                   #Quarter end date for holding
    
    # Metadata
    "data_source" :ColumnTypes.SYMBOL,                    
    "fetched_at" :ColumnTypes.TIMESTAMP,
}

INSIDER_TRADES_SCHEMA = {
    "timestamp" :ColumnTypes.TIMESTAMP,                    #transaction_date (designated timestamp)
    "symbol" :ColumnTypes.SYMBOL,
    "exchange" :ColumnTypes.SYMBOL,
    
    #Insider Information
    "insider_name" :ColumnTypes.STRING,                    # Name of insider
    "insider_title" :ColumnTypes.STRING,                   # 'CEO', 'CFO', 'Director', 'Promoter'
    "insider_relation" :ColumnTypes.SYMBOL,                # 'officer', 'director', 'beneficial_owner', 'promoter'
    
    #Transaction Details
    "transaction_type" :ColumnTypes.SYMBOL,                # 'buy', 'sell', 'gift', 'exercise_option', 'conversion'
    "transaction_date" :ColumnTypes.DATE,                  # Date of transaction
    "filing_date" :ColumnTypes.DATE,                       # Date of filing with SEBI
    
    "shares_traded" :ColumnTypes.LONG,                     # Number of shares
    "price_per_share" :ColumnTypes.DOUBLE,                 # Transaction price
    "total_value" :ColumnTypes.DOUBLE,                     # Total transaction value
    
    #Post-Transaction Ownership
    "shares_owned_before" :ColumnTypes.LONG,
    "shares_owned_after" :ColumnTypes.LONG,
    "percent_change" :ColumnTypes.DOUBLE,                  # % change in ownership
    
    #Transaction Context
    "is_10b5_1_plan" :ColumnTypes.BOOLEAN,                 # Part of pre-arranged trading plan
    "is_derivative" :ColumnTypes.BOOLEAN,                  # Options, warrants, etc.
    
    #Classification
    "significance" :ColumnTypes.SYMBOL,                    # 'major', 'significant', 'minor' (based on size)
    "sentiment" :ColumnTypes.SYMBOL,                       # 'bullish', 'bearish', 'neutral'
    
    #Metadata
    "data_source" :ColumnTypes.SYMBOL,                     # 'eodhd', 'sebi', 'bse', 'nse'
    "fetched_at" :ColumnTypes.TIMESTAMP,
    
}


class PartitionSettings:
    """Partition strategies for different tables"""

    OHLCV = 'DAY'

    # Corporate actions - yearly partitions (infrequent events)
    CORPORATE_ACTIONS = 'YEAR'

    # Audit tables - monthly partitions
    LINEAGE = 'MONTH'
    VALIDATION = 'MONTH'

    #Fundamental data - yearly partitions
    FUNDAMENTAL = 'YEAR'

@dataclass
class PerformanceConfig:
    """Performance tuning settings"""

    # ILP Protocol
    ilp_buffer_size: int = 100000         # Rows per buffer
    ilp_auto_flush_rows: int = 500000    # Auto-flush every n rows

    # Parallel processing
    write_workers: int = 8               # Parallel write threads

    # Batch sizes
    query_batch_size: int = 20000        # Rows per query batch

    # Deduplication
    enable_dedup: bool = True            # Enable automatic deduplication

    # Query limits
    max_query_rows: int = 1_000_000      # Max rows returned per query

class DataSource:
    """Data source identifiers"""

    KITE_API = 'kite_api'
    MANUAL = 'manual'
    ADJUSTMENT = 'adjustment'
    BACKFILL = 'backfill'
    YFINANCE = 'yfinance'

class Intervals:
    """Supported intervals (must match HDF5 structure)"""

    DAY = 'day'
    MINUTE_60 = '60minute'
    MINUTE_15 = '15minute'
    MINUTE_5 = '5minute'
    MINUTE_3 = '3minute'
    MINUTE = 'minute'

    @classmethod
    def all(cls) -> List[str]:
        return [cls.DAY, cls.MINUTE_60, cls.MINUTE_15, cls.MINUTE_5, cls.MINUTE_3, cls.MINUTE]

    @classmethod
    def common(cls) -> List[str]:
        """Most commonly used intervals"""
        return [cls.DAY, cls.MINUTE_60, cls.MINUTE_15]

class Exchanges:
    """Supported exchanges"""

    # Equity
    NSE = 'NSE'
    BSE = 'BSE'

    # Derivatives
    NFO = 'NFO'
    BFO = 'BFO'

    @classmethod
    def equity(cls) -> List[str]:
        return [cls.NSE, cls.BSE]

    @classmethod
    def derivatives(cls) -> List[str]:
        return [cls.NFO, cls.BFO]

    @classmethod
    def all(cls) -> List[str]:
        return cls.equity() + cls.derivatives()

# Connection config (can be overridden via environment variables)
CONNECTION_CONFIG = QuestDBConnectionConfig()

# Performance config
PERFORMANCE_CONFIG = PerformanceConfig()

# Table schemas mapping
TABLE_SCHEMAS = {
    TableNames.OHLCV_EQUITY: OHLCV_EQUITY_SCHEMA,
    TableNames.OHLCV_DERIVATIVES: OHLCV_DERIVATIVES_SCHEMA,
    TableNames.CORPORATE_ACTIONS: CORPORATE_ACTIONS_SCHEMA,
    TableNames.DATA_LINEAGE: DATA_LINEAGE_SCHEMA,
    TableNames.VALIDATION_RESULTS: VALIDATION_RESULTS_SCHEMA,
    TableNames.FUNDAMENTAL_DATA: FUNDAMENTALS_DATA_SCHEMA,
    TableNames.COMPANY_INFO: COMPANY_INFO_SCHEMA,
    TableNames.EARNINGS_HISTORY: EARNINGS_HISTORY_SCHEMA,
    TableNames.EARNINGS_ESTIMATE: EARNINGS_ESTIMATE_SCHEMA,
    TableNames.INSTITUTIONAL_SHAREHOLDERS: INSTITUTIONAL_SHAREHOLDERS_SCHEMA,
    TableNames.INSIDER_TRADES: INSIDER_TRADES_SCHEMA,
}

# Partition strategies mapping
TABLE_PARTITIONS = {
    TableNames.OHLCV_EQUITY: PartitionSettings.OHLCV,
    TableNames.OHLCV_DERIVATIVES: PartitionSettings.OHLCV,
    TableNames.CORPORATE_ACTIONS: PartitionSettings.CORPORATE_ACTIONS,
    TableNames.DATA_LINEAGE: PartitionSettings.LINEAGE,
    TableNames.VALIDATION_RESULTS: PartitionSettings.VALIDATION,
    TableNames.FUNDAMENTAL_DATA: PartitionSettings.FUNDAMENTAL,
    TableNames.COMPANY_INFO: PartitionSettings.FUNDAMENTAL,
    TableNames.EARNINGS_HISTORY: PartitionSettings.FUNDAMENTAL,
    TableNames.EARNINGS_ESTIMATE: PartitionSettings.FUNDAMENTAL,
    TableNames.INSTITUTIONAL_SHAREHOLDERS: PartitionSettings.FUNDAMENTAL,
    TableNames.INSIDER_TRADES: PartitionSettings.FUNDAMENTAL,
}


def get_table_schema(table_name: str) -> Dict[str, str]:
    """Get schema for a table"""
    return TABLE_SCHEMAS.get(table_name, {})


def get_partition_strategy(table_name: str) -> str:
    """Get partition strategy for a table"""
    return TABLE_PARTITIONS.get(table_name, PartitionSettings.OHLCV)


def get_designated_timestamp_column() -> str:
    """Get the name of the designated timestamp column (always 'timestamp')"""
    return 'timestamp'


def is_equity_exchange(exchange: str) -> bool:
    """Check if exchange is equity"""
    return exchange.upper() in Exchanges.equity()


def is_derivatives_exchange(exchange: str) -> bool:
    """Check if exchange is derivatives"""
    return exchange.upper() in Exchanges.derivatives()


def get_table_for_exchange(exchange: str) -> str:
    """Get appropriate table name for an exchange"""
    if is_equity_exchange(exchange):
        return TableNames.OHLCV_EQUITY
    elif is_derivatives_exchange(exchange):
        return TableNames.OHLCV_DERIVATIVES
    else:
        raise ValueError(f"Unknown exchange: {exchange}")

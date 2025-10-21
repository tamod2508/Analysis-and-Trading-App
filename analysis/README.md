# Fundamental Analysis Metrics

Comprehensive fundamental analysis metrics calculator and QuestDB storage.

## Overview

This module calculates 50+ financial metrics across 8 categories and stores them in QuestDB for time-series analysis.

## Metric Categories

### 1. **Liquidity Metrics** (4 metrics)
Measure short-term debt-paying ability:
- Current Ratio
- Quick Ratio
- Cash Ratio
- Working Capital

### 2. **Leverage Metrics** (5 metrics)
Measure debt levels and solvency:
- Debt-to-Equity
- Debt-to-Assets
- Equity Ratio
- Interest Coverage
- Debt Service Coverage

### 3. **Efficiency Metrics** (8 metrics)
Measure asset utilization:
- Asset Turnover
- Inventory Turnover
- Days Inventory Outstanding (DIO)
- Receivables Turnover
- Days Sales Outstanding (DSO)
- Payables Turnover
- Days Payable Outstanding (DPO)
- Cash Conversion Cycle

### 4. **Profitability Metrics** (5 metrics)
Measure profit margins:
- Gross Margin %
- Operating Margin %
- Net Margin %
- EBITDA Margin %
- FCF Margin %

### 5. **Return Metrics** (7 metrics)
Measure returns on capital:
- ROE (Return on Equity)
- ROA (Return on Assets)
- ROIC (Return on Invested Capital)
- DuPont 3-Factor Analysis:
  - Net Margin
  - Asset Turnover
  - Equity Multiplier
  - ROE (DuPont)

### 6. **Growth Metrics** (10 metrics)
Measure year-over-year and CAGR:
- Revenue Growth YoY
- Earnings Growth YoY
- FCF Growth YoY
- Equity Growth YoY
- Revenue CAGR (3Y, 5Y)
- Earnings CAGR (3Y, 5Y)
- FCF CAGR (3Y, 5Y)

### 7. **Per-Share Metrics** (5 metrics)
Normalize values to per-share:
- Book Value per Share
- Tangible Book Value per Share
- FCF per Share
- Operating CF per Share
- Revenue per Share

### 8. **Quality Scores** (2 metrics)
Fundamental quality indicators:
- Piotroski F-Score (0-9)
- Altman Z-Score

## Usage

### 1. Setup Tables (One-Time)

```bash
python3 scripts/setup_analysis_tables.py
```

This creates 8 tables in QuestDB:
- `liquidity_metrics`
- `leverage_metrics`
- `efficiency_metrics`
- `profitability_metrics`
- `return_metrics`
- `growth_metrics`
- `per_share_metrics`
- `quality_scores`

### 2. Calculate Metrics

```python
from analysis.analysis_metrics import (
    FinancialData,
    ComprehensiveMetricsCalculator
)

# Create financial data object
financial_data = FinancialData(
    total_assets=1000000,
    total_liabilities=400000,
    total_equity=600000,
    # ... (see FinancialData dataclass for all fields)
)

# Calculate all metrics
metrics = ComprehensiveMetricsCalculator.calculate_all_metrics(
    current=financial_data,
    previous=previous_period_data,  # Optional
    historical=[year1, year2, year3]  # Optional, for growth metrics
)
```

### 3. Save to QuestDB

```python
from analysis.questdb_saver import AnalysisMetricsSaver

saver = AnalysisMetricsSaver()
saver.save_all_metrics(metrics)
```

### 4. Query from QuestDB

```sql
-- Get latest metrics for a symbol
SELECT * FROM profitability_metrics
WHERE symbol = 'RELIANCE'
ORDER BY calculated_at DESC
LIMIT 1;

-- Get Piotroski score trend over time
SELECT period_date, piotroski_score
FROM quality_scores
WHERE symbol = 'RELIANCE'
ORDER BY period_date DESC;

-- Compare ROE across companies
SELECT symbol, roe, roa, roic
FROM return_metrics
WHERE period_date = '2024-03-31'
ORDER BY roe DESC;
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  RAW FINANCIAL DATA (from EODHD or other source)           │
│  - Balance Sheet                                            │
│  - Income Statement                                         │
│  - Cash Flow Statement                                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  ANALYSIS METRICS CALCULATOR                                │
│  - Calculates 50+ metrics across 8 categories              │
│  - Requires current + previous period for comparisons      │
│  - Requires historical data for growth metrics             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  QUESTDB SAVER                                              │
│  - Splits metrics by category                              │
│  - Saves to 8 separate tables                              │
│  - Time-series partitioned by month                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  QUESTDB TABLES (time-series storage)                      │
│  - Query metrics over time                                 │
│  - Compare across companies                                │
│  - Build dashboards and analytics                          │
└─────────────────────────────────────────────────────────────┘
```

## Files

- **`analysis_metrics.py`** - Core metrics calculation classes
- **`config.py`** - QuestDB table schemas
- **`questdb_saver.py`** - Save metrics to QuestDB
- **`scripts/setup_analysis_tables.py`** - Setup script

## Table Schemas

All tables share this structure:
```sql
CREATE TABLE <metric_category> (
    calculated_at TIMESTAMP,  -- When metrics were calculated
    symbol SYMBOL,             -- Company symbol
    period_date TIMESTAMP,     -- Financial statement date
    period_type SYMBOL,        -- 'yearly' or 'quarterly'
    <metric_1> DOUBLE,
    <metric_2> DOUBLE,
    ...
) TIMESTAMP(calculated_at) PARTITION BY MONTH;
```

**Partitioning:** By MONTH on `calculated_at` for efficient time-series queries.

## Example: Full Workflow

```python
from datetime import datetime
from analysis.analysis_metrics import (
    FinancialData,
    ComprehensiveMetricsCalculator
)
from analysis.questdb_saver import AnalysisMetricsSaver

# 1. Create financial data (from EODHD, Yahoo Finance, etc.)
current_data = FinancialData(
    # Balance Sheet
    total_assets=1_000_000,
    total_liabilities=400_000,
    total_equity=600_000,
    current_assets=300_000,
    current_liabilities=150_000,
    cash=50_000,
    # ... (all other fields)

    # Metadata
    date=datetime(2024, 3, 31),
    symbol='RELIANCE',
    period_type='yearly'
)

# 2. Calculate metrics
metrics = ComprehensiveMetricsCalculator.calculate_all_metrics(
    current=current_data,
    previous=previous_year_data,  # For period-over-period comparison
    historical=[y1, y2, y3, y4, y5]  # For growth CAGRs
)

# 3. Save to QuestDB
saver = AnalysisMetricsSaver()
saver.save_all_metrics(metrics)

# 4. Query later
# SELECT * FROM profitability_metrics WHERE symbol = 'RELIANCE';
```

## Interpreting Metrics

### Liquidity (Higher is Better)
- **Current Ratio > 1.5**: Healthy
- **Quick Ratio > 1.0**: Healthy
- **Cash Ratio > 0.5**: Healthy

### Leverage (Lower is Better)
- **Debt-to-Equity < 1.0**: Conservative
- **Interest Coverage > 2.5**: Healthy

### Profitability (Higher is Better)
- **Gross Margin**: Industry-specific
- **Net Margin**: Higher = more profitable

### Returns (Higher is Better)
- **ROE > 15%**: Good, > 20% Excellent
- **ROA > 5%**: Good (varies by industry)
- **ROIC > 15%**: Excellent

### Quality Scores
- **Piotroski F-Score**:
  - 7-9: Strong
  - 4-6: Average
  - 0-3: Weak
- **Altman Z-Score**:
  - \> 2.99: Safe zone
  - 1.81-2.99: Grey zone
  - < 1.81: Distress zone

## Future Enhancements

- [ ] Valuation metrics (P/E, P/B, P/S, EV/EBITDA)
- [ ] Sector-specific metrics
- [ ] Trend analysis utilities
- [ ] Automated alerts on metric changes
- [ ] Dashboard integration

---

**Last Updated:** 2025-01-10
**Status:** Ready for production use
**Storage:** QuestDB (8 time-series tables)

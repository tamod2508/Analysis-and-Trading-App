"""
Justified Valuation Ratios Calculator

This module calculates "justified" valuation multiples based on fundamental drivers.
These ratios represent the theoretical fair value multiples a company should trade at
given its growth, profitability, and risk profile.

Justified ratios are derived from dividend discount models (DDM) and discounted cash flow (DCF)
models, providing a fundamental basis for valuation rather than relying on market comparables.

Usage:
    from analysis.justified_ratios import JustifiedRatios, ValuationInputs

    inputs = ValuationInputs(
        roe=0.20,
        retention_ratio=0.60,
        growth_rate=0.12,
        required_return=0.15,
        earnings=100000,
        sales=500000,
        fcfe=80000
    )

    ratios = JustifiedRatios.calculate_all(inputs)
"""

from dataclasses import dataclass
from typing import Optional, Dict
import warnings


@dataclass
class ValuationInputs:
    """
    Input parameters for justified valuation calculations

    All rates should be expressed as decimals (e.g., 0.15 for 15%)

    NOTE: All fields are optional. Calculations will be performed only for metrics
    where sufficient data is available. This allows graceful degradation when
    some financial data is missing.
    """
    # Profitability (Optional - required for P/B)
    roe: Optional[float] = None  # Return on Equity (e.g., 0.20 for 20%)

    # Capital Allocation (Optional - required for P/E, P/S)
    retention_ratio: Optional[float] = None  # Earnings retained (1 - payout ratio) (e.g., 0.60 for 60%)

    # Growth (Optional - required for all ratios)
    growth_rate: Optional[float] = None  # Expected growth rate (e.g., 0.12 for 12%)

    # Risk/Discount Rate (Optional - required for all ratios)
    required_return: Optional[float] = None  # Required rate of return / Cost of Equity (e.g., 0.15 for 15%)

    # Financial Metrics (Optional - for specific calculations)
    earnings: Optional[float] = None  # Earnings (most recent period) - for P/S
    sales: Optional[float] = None  # Sales/Revenue (most recent period) - for P/S
    fcfe: Optional[float] = None  # Free Cash Flow to Equity - for P/CF

    def __post_init__(self):
        """Validate inputs after initialization"""
        self._validate()

    def _validate(self):
        """
        Validate input parameters - only validates non-None values

        This allows partial data to be provided without triggering validation errors.
        Individual calculation methods will check for required fields.
        """
        # Only validate fields that are provided (not None)

        if self.roe is not None:
            if self.roe < -1.0 or self.roe > 2.0:
                warnings.warn(f"ROE of {self.roe:.1%} seems unusual (expected -100% to 200%)")

        if self.retention_ratio is not None:
            if self.retention_ratio < 0.0 or self.retention_ratio > 1.0:
                raise ValueError(f"Retention ratio must be between 0 and 1, got {self.retention_ratio}")

        if self.growth_rate is not None:
            if self.growth_rate < -0.5 or self.growth_rate > 1.0:
                warnings.warn(f"Growth rate of {self.growth_rate:.1%} seems unusual (expected -50% to 100%)")

        if self.required_return is not None:
            if self.required_return <= 0:
                raise ValueError(f"Required return must be positive, got {self.required_return}")

        # Check for sustainable growth (only if both ROE and retention are provided)
        if self.roe is not None and self.retention_ratio is not None and self.growth_rate is not None:
            sustainable_growth = self.roe * self.retention_ratio
            if abs(self.growth_rate - sustainable_growth) > 0.05:  # 5% tolerance
                warnings.warn(
                    f"Growth rate {self.growth_rate:.1%} differs significantly from "
                    f"sustainable growth {sustainable_growth:.1%} (ROE × Retention)"
                )

        # Check if growth rate exceeds required return (only if both provided)
        if self.growth_rate is not None and self.required_return is not None:
            if self.growth_rate >= self.required_return:
                raise ValueError(
                    f"Growth rate ({self.growth_rate:.1%}) must be less than "
                    f"required return ({self.required_return:.1%}) for stable valuation"
                )


class JustifiedRatios:
    """
    Calculate justified valuation multiples based on fundamental drivers
    """

    @staticmethod
    def justified_pe(inputs: ValuationInputs) -> Optional[float]:
        """
        Justified P/E Ratio = (1 - Retention Ratio) / (Required Return - Growth Rate)

        Required fields: retention_ratio, required_return, growth_rate

        Derived from Gordon Growth Model (constant growth DDM):
        P₀ = D₁ / (r - g)

        Where:
        - D₁ = E₁ × (1 - b) = next year's dividend
        - E₁ = next year's earnings
        - b = retention ratio
        - r = required return (cost of equity)
        - g = growth rate

        Therefore: P/E = (1 - b) / (r - g)

        Interpretation:
        - Higher P/E justified when:
          • Lower retention (higher payout) → more current cash to investors
          • Lower required return (less risky)
          • Higher growth rate
        - Compare actual P/E to justified P/E:
          • Actual > Justified = Potentially overvalued
          • Actual < Justified = Potentially undervalued

        Example:
        - If retention = 40%, required return = 12%, growth = 8%
        - Justified P/E = (1 - 0.40) / (0.12 - 0.08) = 0.60 / 0.04 = 15.0x

        Args:
            inputs: ValuationInputs object with required parameters

        Returns:
            Justified P/E ratio or None if required data is missing or calculation is invalid
        """
        try:
            # Check for required fields
            if inputs.retention_ratio is None:
                return None
            if inputs.required_return is None:
                return None
            if inputs.growth_rate is None:
                return None

            # CRITICAL: Growth rate MUST be less than required return (validated in __post_init__)
            # This is already enforced by ValuationInputs._validate()

            payout_ratio = 1 - inputs.retention_ratio
            denominator = inputs.required_return - inputs.growth_rate

            # This should never happen due to validation, but double-check
            if denominator <= 0:
                warnings.warn(
                    f"Invalid: Required return ({inputs.required_return:.1%}) must exceed "
                    f"growth rate ({inputs.growth_rate:.1%})"
                )
                return None

            justified_pe = payout_ratio / denominator

            # Sanity check: P/E should typically be between 0 and 100
            if justified_pe < 0 or justified_pe > 100:
                warnings.warn(f"Unusual justified P/E calculated: {justified_pe:.2f}x")

            return justified_pe

        except Exception as e:
            warnings.warn(f"Error calculating justified P/E: {e}")
            return None

    @staticmethod
    def justified_pb(inputs: ValuationInputs) -> Optional[float]:
        """
        Justified P/B Ratio = (ROE - Growth Rate) / (Required Return - Growth Rate)

        Required fields: roe, required_return, growth_rate

        Derived from residual income model and Gordon Growth Model:
        P/B = (ROE - g) / (r - g)

        Where:
        - ROE = Return on Equity
        - r = required return (cost of equity)
        - g = growth rate

        Alternative formulation:
        P/B = ROE × (1 - b) / (r - g)
        where b = retention ratio

        Interpretation:
        - Higher P/B justified when:
          • Higher ROE (more profitable use of equity)
          • Lower required return (less risky)
          • Higher growth rate (but not exceeding ROE)
        - P/B = 1.0 implies market value = book value (no value creation)
        - P/B > 1.0 implies positive value creation (ROE > required return)
        - P/B < 1.0 implies value destruction (ROE < required return)

        Example:
        - If ROE = 20%, growth = 12%, required return = 15%
        - Justified P/B = (0.20 - 0.12) / (0.15 - 0.12) = 0.08 / 0.03 = 2.67x

        Args:
            inputs: ValuationInputs object with required parameters

        Returns:
            Justified P/B ratio or None if required data is missing or calculation is invalid
        """
        try:
            # Check for required fields
            if inputs.roe is None:
                return None
            if inputs.required_return is None:
                return None
            if inputs.growth_rate is None:
                return None

            # CRITICAL: Growth rate MUST be less than required return (validated in __post_init__)

            numerator = inputs.roe - inputs.growth_rate
            denominator = inputs.required_return - inputs.growth_rate

            # This should never happen due to validation, but double-check
            if denominator <= 0:
                warnings.warn(
                    f"Invalid: Required return ({inputs.required_return:.1%}) must exceed "
                    f"growth rate ({inputs.growth_rate:.1%})"
                )
                return None

            justified_pb = numerator / denominator

            # Sanity check: P/B typically between 0 and 20
            if justified_pb < 0:
                warnings.warn(
                    f"Negative justified P/B ({justified_pb:.2f}x) indicates "
                    f"ROE ({inputs.roe:.1%}) < Growth ({inputs.growth_rate:.1%}), "
                    f"suggesting unsustainable growth or value destruction"
                )
            elif justified_pb > 20:
                warnings.warn(f"Unusually high justified P/B calculated: {justified_pb:.2f}x")

            return justified_pb

        except Exception as e:
            warnings.warn(f"Error calculating justified P/B: {e}")
            return None

    @staticmethod
    def justified_ps(inputs: ValuationInputs) -> Optional[float]:
        """
        Justified P/S Ratio = (Profit Margin) × (1 - Retention Ratio) × (1 + Growth Rate) / (Required Return - Growth Rate)

        Required fields: earnings, sales, retention_ratio, required_return, growth_rate

        Derived from Gordon Growth Model applied to sales:
        P/S = (E/S) × (1 - b) × (1 + g) / (r - g)

        Where:
        - E/S = Earnings/Sales = Profit Margin (net margin)
        - b = retention ratio
        - g = growth rate
        - r = required return
        - (1 + g) adjusts for next period's earnings

        Interpretation:
        - Higher P/S justified when:
          • Higher profit margins
          • Higher payout ratio (lower retention)
          • Higher growth rate
          • Lower required return
        - Useful for comparing companies with different margins
        - P/S less affected by accounting policies than P/E

        Example:
        - If margin = 10%, retention = 40%, growth = 12%, required return = 15%
        - Justified P/S = (0.10) × (1 - 0.40) × (1 + 0.12) / (0.15 - 0.12)
        - Justified P/S = 0.10 × 0.60 × 1.12 / 0.03 = 2.24x

        Args:
            inputs: ValuationInputs object with earnings and sales data

        Returns:
            Justified P/S ratio or None if required data is missing or calculation is invalid
        """
        try:
            # Check for required fields
            if inputs.earnings is None or inputs.sales is None:
                return None
            if inputs.retention_ratio is None:
                return None
            if inputs.required_return is None:
                return None
            if inputs.growth_rate is None:
                return None

            if inputs.sales == 0:
                return None

            # CRITICAL: Growth rate MUST be less than required return (validated in __post_init__)

            # Calculate profit margin
            profit_margin = inputs.earnings / inputs.sales

            # Calculate justified P/S
            payout_ratio = 1 - inputs.retention_ratio
            growth_adjusted_earnings = 1 + inputs.growth_rate
            denominator = inputs.required_return - inputs.growth_rate

            # This should never happen due to validation, but double-check
            if denominator <= 0:
                warnings.warn(
                    f"Invalid: Required return ({inputs.required_return:.1%}) must exceed "
                    f"growth rate ({inputs.growth_rate:.1%})"
                )
                return None

            justified_ps = (profit_margin * payout_ratio * growth_adjusted_earnings) / denominator

            # Sanity check: P/S typically between 0 and 20
            if justified_ps < 0:
                warnings.warn(
                    f"Negative justified P/S ({justified_ps:.2f}x) indicates "
                    f"negative profit margin ({profit_margin:.1%})"
                )
            elif justified_ps > 20:
                warnings.warn(f"Unusually high justified P/S calculated: {justified_ps:.2f}x")

            return justified_ps

        except Exception as e:
            warnings.warn(f"Error calculating justified P/S: {e}")
            return None

    @staticmethod
    def justified_pcf(inputs: ValuationInputs) -> Optional[float]:
        """
        Justified P/CF Ratio = (1 + Growth Rate) / (Required Return - Growth Rate)

        Required fields: required_return, growth_rate
        Optional: fcfe (for validation only)

        Based on Free Cash Flow to Equity (FCFE) model:
        P = FCFE₁ / (r - g)

        Where:
        - FCFE₁ = FCFE₀ × (1 + g) = next year's free cash flow to equity
        - r = required return
        - g = growth rate

        Therefore: P/CF = (1 + g) / (r - g)

        Interpretation:
        - Higher P/CF justified when:
          • Higher expected growth
          • Lower required return (less risky)
        - P/CF based on actual cash generation (less accounting manipulation)
        - Useful for capital-intensive businesses
        - Compare to P/E to assess quality of earnings (cash vs accruals)

        Example:
        - If growth = 8%, required return = 12%
        - Justified P/CF = (1 + 0.08) / (0.12 - 0.08) = 1.08 / 0.04 = 27.0x

        Args:
            inputs: ValuationInputs object with required data

        Returns:
            Justified P/CF ratio or None if required data is missing or calculation is invalid
        """
        try:
            # Check for required fields
            if inputs.required_return is None:
                return None
            if inputs.growth_rate is None:
                return None

            # FCFE is optional - we can calculate P/CF multiple without it
            # It's only used for validation if provided
            if inputs.fcfe is not None and inputs.fcfe == 0:
                return None

            # CRITICAL: Growth rate MUST be less than required return (validated in __post_init__)

            # Calculate justified P/CF
            growth_adjusted = 1 + inputs.growth_rate
            denominator = inputs.required_return - inputs.growth_rate

            # This should never happen due to validation, but double-check
            if denominator <= 0:
                warnings.warn(
                    f"Invalid: Required return ({inputs.required_return:.1%}) must exceed "
                    f"growth rate ({inputs.growth_rate:.1%})"
                )
                return None

            justified_pcf = growth_adjusted / denominator

            # Sanity check: P/CF typically between 0 and 50
            if justified_pcf < 0:
                warnings.warn(f"Negative justified P/CF: {justified_pcf:.2f}x (unusual)")
            elif justified_pcf > 50:
                warnings.warn(f"Unusually high justified P/CF calculated: {justified_pcf:.2f}x")

            return justified_pcf

        except Exception as e:
            warnings.warn(f"Error calculating justified P/CF: {e}")
            return None

    @staticmethod
    def calculate_all(inputs: ValuationInputs) -> Dict[str, Optional[float]]:
        """
        Calculate all justified valuation ratios

        Gracefully handles missing data - only calculates metrics where sufficient data exists.

        Args:
            inputs: ValuationInputs object (fields can be None/optional)

        Returns:
            Dictionary with all justified ratios and additional metrics
            (None values for metrics that cannot be calculated due to missing data)
        """
        results = {
            # Core justified ratios (will be None if required fields are missing)
            'justified_pe': JustifiedRatios.justified_pe(inputs),
            'justified_pb': JustifiedRatios.justified_pb(inputs),
            'justified_ps': JustifiedRatios.justified_ps(inputs),
            'justified_pcf': JustifiedRatios.justified_pcf(inputs),

            # Input parameters (for reference - may be None)
            'roe': inputs.roe,
            'retention_ratio': inputs.retention_ratio,
            'growth_rate': inputs.growth_rate,
            'required_return': inputs.required_return,
        }

        # Add payout ratio only if retention ratio is available
        if inputs.retention_ratio is not None:
            results['payout_ratio'] = 1 - inputs.retention_ratio
        else:
            results['payout_ratio'] = None

        # Add sustainable growth only if both ROE and retention are available
        if inputs.roe is not None and inputs.retention_ratio is not None:
            results['sustainable_growth'] = inputs.roe * inputs.retention_ratio
        else:
            results['sustainable_growth'] = None

        # Add implied risk premium only if both required return and growth are available
        if inputs.required_return is not None and inputs.growth_rate is not None:
            results['implied_risk_premium'] = inputs.required_return - inputs.growth_rate
        else:
            results['implied_risk_premium'] = None

        # Add profit margin if available
        if inputs.earnings is not None and inputs.sales is not None and inputs.sales != 0:
            results['profit_margin'] = inputs.earnings / inputs.sales
        else:
            results['profit_margin'] = None

        return results

    @staticmethod
    def compare_to_actual(
        justified: Dict[str, Optional[float]],
        actual_pe: Optional[float] = None,
        actual_pb: Optional[float] = None,
        actual_ps: Optional[float] = None,
        actual_pcf: Optional[float] = None
    ) -> Dict[str, Optional[float]]:
        """
        Compare actual market multiples to justified multiples

        Args:
            justified: Dictionary from calculate_all()
            actual_pe: Actual market P/E ratio
            actual_pb: Actual market P/B ratio
            actual_ps: Actual market P/S ratio
            actual_pcf: Actual market P/CF ratio

        Returns:
            Dictionary with comparison metrics:
            - premium/discount percentages
            - overvalued/undervalued flags
        """
        comparison = {}

        # P/E comparison
        if justified.get('justified_pe') and actual_pe:
            pe_diff = actual_pe - justified['justified_pe']
            pe_premium = (pe_diff / justified['justified_pe']) * 100
            comparison['pe_premium_pct'] = pe_premium
            comparison['pe_overvalued'] = pe_premium > 0
            comparison['actual_pe'] = actual_pe
            comparison['justified_pe'] = justified['justified_pe']

        # P/B comparison
        if justified.get('justified_pb') and actual_pb:
            pb_diff = actual_pb - justified['justified_pb']
            pb_premium = (pb_diff / justified['justified_pb']) * 100
            comparison['pb_premium_pct'] = pb_premium
            comparison['pb_overvalued'] = pb_premium > 0
            comparison['actual_pb'] = actual_pb
            comparison['justified_pb'] = justified['justified_pb']

        # P/S comparison
        if justified.get('justified_ps') and actual_ps:
            ps_diff = actual_ps - justified['justified_ps']
            ps_premium = (ps_diff / justified['justified_ps']) * 100
            comparison['ps_premium_pct'] = ps_premium
            comparison['ps_overvalued'] = ps_premium > 0
            comparison['actual_ps'] = actual_ps
            comparison['justified_ps'] = justified['justified_ps']

        # P/CF comparison
        if justified.get('justified_pcf') and actual_pcf:
            pcf_diff = actual_pcf - justified['justified_pcf']
            pcf_premium = (pcf_diff / justified['justified_pcf']) * 100
            comparison['pcf_premium_pct'] = pcf_premium
            comparison['pcf_overvalued'] = pcf_premium > 0
            comparison['actual_pcf'] = actual_pcf
            comparison['justified_pcf'] = justified['justified_pcf']

        return comparison


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("JUSTIFIED VALUATION RATIOS CALCULATOR")
    print("=" * 80)

    # Example 1: High-growth tech company
    print("\nExample 1: High-Growth Tech Company")
    print("-" * 80)
    tech_inputs = ValuationInputs(
        roe=0.25,              # 25% ROE
        retention_ratio=0.80,  # 80% retention (reinvesting for growth)
        growth_rate=0.20,      # 20% growth rate (sustainable = 25% × 80% = 20%)
        required_return=0.25,  # 25% required return (higher risk)
        earnings=50000000,     # $50M earnings
        sales=200000000,       # $200M sales (25% margin)
        fcfe=40000000         # $40M FCFE
    )

    tech_ratios = JustifiedRatios.calculate_all(tech_inputs)

    print(f"ROE: {tech_ratios['roe']:.1%}")
    print(f"Retention Ratio: {tech_ratios['retention_ratio']:.1%}")
    print(f"Growth Rate: {tech_ratios['growth_rate']:.1%}")
    print(f"Required Return: {tech_ratios['required_return']:.1%}")
    print(f"Sustainable Growth: {tech_ratios['sustainable_growth']:.1%}")
    print(f"\nJustified Multiples:")
    print(f"  P/E:  {tech_ratios['justified_pe']:.2f}x" if tech_ratios['justified_pe'] else "  P/E:  N/A")
    print(f"  P/B:  {tech_ratios['justified_pb']:.2f}x" if tech_ratios['justified_pb'] else "  P/B:  N/A")
    print(f"  P/S:  {tech_ratios['justified_ps']:.2f}x" if tech_ratios['justified_ps'] else "  P/S:  N/A")
    print(f"  P/CF: {tech_ratios['justified_pcf']:.2f}x" if tech_ratios['justified_pcf'] else "  P/CF: N/A")

    # Example 2: Mature dividend-paying company
    print("\n\nExample 2: Mature Dividend-Paying Company")
    print("-" * 80)
    mature_inputs = ValuationInputs(
        roe=0.15,              # 15% ROE
        retention_ratio=0.40,  # 40% retention (60% payout)
        growth_rate=0.06,      # 6% growth rate (sustainable = 15% × 40% = 6%)
        required_return=0.12,  # 12% required return (lower risk)
        earnings=100000000,    # $100M earnings
        sales=800000000,       # $800M sales (12.5% margin)
        fcfe=90000000         # $90M FCFE
    )

    mature_ratios = JustifiedRatios.calculate_all(mature_inputs)

    print(f"ROE: {mature_ratios['roe']:.1%}")
    print(f"Retention Ratio: {mature_ratios['retention_ratio']:.1%}")
    print(f"Payout Ratio: {mature_ratios['payout_ratio']:.1%}")
    print(f"Growth Rate: {mature_ratios['growth_rate']:.1%}")
    print(f"Required Return: {mature_ratios['required_return']:.1%}")
    print(f"Sustainable Growth: {mature_ratios['sustainable_growth']:.1%}")
    print(f"\nJustified Multiples:")
    print(f"  P/E:  {mature_ratios['justified_pe']:.2f}x" if mature_ratios['justified_pe'] else "  P/E:  N/A")
    print(f"  P/B:  {mature_ratios['justified_pb']:.2f}x" if mature_ratios['justified_pb'] else "  P/B:  N/A")
    print(f"  P/S:  {mature_ratios['justified_ps']:.2f}x" if mature_ratios['justified_ps'] else "  P/S:  N/A")
    print(f"  P/CF: {mature_ratios['justified_pcf']:.2f}x" if mature_ratios['justified_pcf'] else "  P/CF: N/A")

    # Example 3: Compare to actual market multiples
    print("\n\nExample 3: Comparison to Market Multiples")
    print("-" * 80)

    comparison = JustifiedRatios.compare_to_actual(
        justified=mature_ratios,
        actual_pe=12.0,    # Market P/E = 12x
        actual_pb=2.0,     # Market P/B = 2x
        actual_ps=1.8,     # Market P/S = 1.8x
        actual_pcf=15.0    # Market P/CF = 15x
    )

    print("Valuation Assessment:")
    if 'pe_premium_pct' in comparison:
        print(f"\nP/E Ratio:")
        print(f"  Actual:    {comparison['actual_pe']:.2f}x")
        print(f"  Justified: {comparison['justified_pe']:.2f}x")
        print(f"  Premium:   {comparison['pe_premium_pct']:+.1f}%")
        print(f"  Assessment: {'OVERVALUED' if comparison['pe_overvalued'] else 'UNDERVALUED'}")

    if 'pb_premium_pct' in comparison:
        print(f"\nP/B Ratio:")
        print(f"  Actual:    {comparison['actual_pb']:.2f}x")
        print(f"  Justified: {comparison['justified_pb']:.2f}x")
        print(f"  Premium:   {comparison['pb_premium_pct']:+.1f}%")
        print(f"  Assessment: {'OVERVALUED' if comparison['pb_overvalued'] else 'UNDERVALUED'}")

    if 'ps_premium_pct' in comparison:
        print(f"\nP/S Ratio:")
        print(f"  Actual:    {comparison['actual_ps']:.2f}x")
        print(f"  Justified: {comparison['justified_ps']:.2f}x")
        print(f"  Premium:   {comparison['ps_premium_pct']:+.1f}%")
        print(f"  Assessment: {'OVERVALUED' if comparison['ps_overvalued'] else 'UNDERVALUED'}")

    if 'pcf_premium_pct' in comparison:
        print(f"\nP/CF Ratio:")
        print(f"  Actual:    {comparison['actual_pcf']:.2f}x")
        print(f"  Justified: {comparison['justified_pcf']:.2f}x")
        print(f"  Premium:   {comparison['pcf_premium_pct']:+.1f}%")
        print(f"  Assessment: {'OVERVALUED' if comparison['pcf_overvalued'] else 'UNDERVALUED'}")

    print("\n" + "=" * 80)

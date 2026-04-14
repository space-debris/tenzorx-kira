"""
KIRA — Loan Sizer

Converts revenue estimates and risk assessments into actionable loan
recommendations. Uses EMI-to-income ratios and risk band multipliers
to compute sustainable loan ranges.

Owner: Orchestration Lead
Phase: 3.3

Loan Sizing Logic:
    1. EMI Capacity = monthly_revenue_low × emi_ratio (default 15%)
    2. Risk Multiplier = f(risk_band) → LOW=1.0, MEDIUM=0.8, HIGH=0.6
    3. Max Loan = EMI Capacity × tenure_months / (1 + interest_rate_factor)
    4. Loan Range = [min_loan, max_loan] capped at ₹5L
    5. If fraud_flagged → eligible = False
"""

from __future__ import annotations

import logging

from models.output_schema import (
    CVSignals,
    FraudDetection,
    GeoSignals,
    LoanRecommendation,
    RevenueEstimate,
    RiskAssessment,
    RiskBand,
    ValueRange,
)
from orchestration.pricing_engine import recommend_pricing
from orchestration.repayment_recommender import (
    estimate_installment_from_monthly_equivalent,
    recommend_repayment_cadence,
)

logger = logging.getLogger("kira.loan_sizer")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum EMI-to-income ratio (conservative for kirana segment)
MAX_EMI_TO_INCOME_RATIO = 0.15

# Risk band multipliers — reduce loan capacity based on risk
RISK_MULTIPLIERS = {
    RiskBand.LOW: 1.0,
    RiskBand.MEDIUM: 0.8,
    RiskBand.HIGH: 0.6,
    RiskBand.VERY_HIGH: 0.0,  # Not eligible
}

# Tenure options (months)
TENURE_OPTIONS = [12, 18, 24, 36]
DEFAULT_TENURE = 18

# Interest rate assumptions (for EMI calculation)
ANNUAL_INTEREST_RATE = 0.18  # 18% per annum (typical NBFC kirana rate)
MONTHLY_INTEREST_RATE = ANNUAL_INTEREST_RATE / 12

# Loan caps
MIN_LOAN_AMOUNT = 25000    # ₹25K minimum
MAX_LOAN_AMOUNT = 500000   # ₹5L maximum (policy cap)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def compute_loan_recommendation(
    revenue_estimate: RevenueEstimate,
    risk_assessment: RiskAssessment,
    fraud_detection: FraudDetection,
    cv_signals: CVSignals | None = None,
    geo_signals: GeoSignals | None = None,
) -> LoanRecommendation:
    """
    Compute a loan recommendation from revenue estimate and risk assessment.

    Uses conservative EMI-to-income ratios to ensure sustainable lending.
    Loan amounts are capped at ₹5L and only offered if the store is not
    fraud-flagged and risk band is not VERY_HIGH.

    Args:
        revenue_estimate: Monthly revenue range from the fusion engine.
        risk_assessment: Risk band and score from the fusion engine.
        fraud_detection: Fraud detection results.

    Returns:
        LoanRecommendation: Eligibility, policy range, concrete amount,
        cadence, pricing guidance, and affordability metrics.
    """
    risk_band = risk_assessment.risk_band

    # Step 1: Check eligibility
    is_eligible = (
        not fraud_detection.is_flagged
        and risk_band != RiskBand.VERY_HIGH
    )

    if not is_eligible:
        reason = (
            "fraud flagged" if fraud_detection.is_flagged
            else f"risk band is {risk_band.value}"
        )
        logger.info(f"Loan not eligible: {reason}")
        return LoanRecommendation(
            eligible=False,
            loan_range=ValueRange(low=0, high=0),
            suggested_tenure_months=DEFAULT_TENURE,
            estimated_emi=0,
            emi_to_income_ratio=0,
        )

    # Step 2: Compute base EMI capacity from conservative (low) revenue
    base_emi_capacity = revenue_estimate.monthly_low * MAX_EMI_TO_INCOME_RATIO
    logger.info(
        f"Base EMI capacity: ₹{base_emi_capacity:,.0f} "
        f"(15% of ₹{revenue_estimate.monthly_low:,.0f})"
    )

    # Step 3: Apply risk band multiplier
    risk_multiplier = RISK_MULTIPLIERS.get(risk_band, 0.6)
    adjusted_emi_capacity = base_emi_capacity * risk_multiplier
    logger.info(
        f"Risk-adjusted EMI capacity: ₹{adjusted_emi_capacity:,.0f} "
        f"(multiplier={risk_multiplier} for {risk_band.value})"
    )

    # Step 4: Select optimal tenure
    optimal_tenure = _select_optimal_tenure(adjusted_emi_capacity, risk_band)

    # Step 5: Compute max loan from EMI capacity
    uncapped_max_loan = _compute_max_loan_from_emi(
        max_emi=adjusted_emi_capacity,
        monthly_rate=MONTHLY_INTEREST_RATE,
        tenure_months=optimal_tenure,
    )

    # Do not force the minimum ticket size onto stores that cannot sustain it.
    if uncapped_max_loan < MIN_LOAN_AMOUNT:
        logger.info(
            f"Loan below minimum (₹{uncapped_max_loan:,.0f} < ₹{MIN_LOAN_AMOUNT:,.0f})"
        )
        return LoanRecommendation(
            eligible=False,
            loan_range=ValueRange(low=0, high=0),
            suggested_tenure_months=DEFAULT_TENURE,
            estimated_emi=0,
            emi_to_income_ratio=0,
        )

    # Step 6: Compute min loan (using conservative 60% of max)
    max_loan = uncapped_max_loan
    min_loan = max_loan * 0.6

    # Step 7: Apply loan amount caps
    max_loan = max(MIN_LOAN_AMOUNT, min(MAX_LOAN_AMOUNT, max_loan))
    min_loan = max(MIN_LOAN_AMOUNT, min(max_loan, min_loan))

    # Round to nearest 1000
    max_loan = round(max_loan / 1000) * 1000
    min_loan = round(min_loan / 1000) * 1000

    # Step 8: Pick a concrete recommendation within the approved range
    recommended_amount = _select_recommended_amount(
        min_loan=min_loan,
        max_loan=max_loan,
        confidence=risk_assessment.confidence,
        risk_band=risk_band,
    )

    # Step 9: Compute EMI for the concrete recommended loan
    estimated_emi = _compute_emi(
        principal=recommended_amount,
        monthly_rate=MONTHLY_INTEREST_RATE,
        tenure_months=optimal_tenure,
    )

    # Step 10: Compute EMI-to-income ratio (using conservative revenue)
    emi_to_income = (
        estimated_emi / revenue_estimate.monthly_low
        if revenue_estimate.monthly_low > 0
        else 1.0
    )
    emi_to_income = min(1.0, emi_to_income)

    # Step 11: Recommend cadence and convert monthly equivalent into collection-size
    cadence_result = recommend_repayment_cadence(
        revenue_estimate=revenue_estimate,
        risk_assessment=risk_assessment,
        cv_signals=cv_signals,
        geo_signals=geo_signals,
    )
    repayment_cadence = cadence_result["cadence"]
    estimated_installment = estimate_installment_from_monthly_equivalent(
        estimated_emi,
        repayment_cadence,
    )

    # Step 12: Recommend pricing
    pricing_recommendation = recommend_pricing(
        risk_assessment=risk_assessment,
        revenue_estimate=revenue_estimate,
        recommended_amount=recommended_amount,
        loan_range=ValueRange(low=min_loan, high=max_loan),
        repayment_cadence=repayment_cadence,
        emi_to_income_ratio=emi_to_income,
    )

    logger.info(
        f"Loan recommendation: range=₹{min_loan:,.0f}-₹{max_loan:,.0f}, "
        f"recommended=₹{recommended_amount:,.0f}, tenure={optimal_tenure}m, "
        f"cadence={repayment_cadence.value}, EMI=₹{estimated_emi:,.0f}, "
        f"EMI/income={emi_to_income:.2%}"
    )

    return LoanRecommendation(
        eligible=True,
        loan_range=ValueRange(low=min_loan, high=max_loan),
        recommended_amount=recommended_amount,
        suggested_tenure_months=optimal_tenure,
        estimated_emi=round(estimated_emi, 2),
        emi_to_income_ratio=round(emi_to_income, 4),
        repayment_cadence=repayment_cadence,
        estimated_installment=estimated_installment,
        pricing_recommendation=pricing_recommendation,
    )


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _compute_emi(
    principal: float,
    monthly_rate: float,
    tenure_months: int,
) -> float:
    """
    Compute EMI using the standard reducing balance formula.

    EMI = P × r × (1+r)^n / ((1+r)^n - 1)

    Args:
        principal: Loan principal amount in INR.
        monthly_rate: Monthly interest rate (decimal).
        tenure_months: Loan tenure in months.

    Returns:
        float: Monthly EMI amount in INR.
    """
    if principal <= 0:
        return 0.0

    if monthly_rate <= 0:
        # Zero interest — simple division
        return principal / tenure_months if tenure_months > 0 else principal

    if tenure_months <= 0:
        return principal

    r = monthly_rate
    n = tenure_months
    factor = (1 + r) ** n

    emi = principal * r * factor / (factor - 1)
    return round(emi, 2)


def _compute_max_loan_from_emi(
    max_emi: float,
    monthly_rate: float,
    tenure_months: int,
) -> float:
    """
    Reverse-compute maximum loan principal from an EMI capacity.

    P = EMI × ((1+r)^n - 1) / (r × (1+r)^n)

    Args:
        max_emi: Maximum affordable monthly EMI in INR.
        monthly_rate: Monthly interest rate (decimal).
        tenure_months: Loan tenure in months.

    Returns:
        float: Maximum loan principal in INR.
    """
    if max_emi <= 0:
        return 0.0

    if monthly_rate <= 0:
        return max_emi * tenure_months

    if tenure_months <= 0:
        return 0.0

    r = monthly_rate
    n = tenure_months
    factor = (1 + r) ** n

    principal = max_emi * (factor - 1) / (r * factor)
    return round(principal, 2)


def _select_optimal_tenure(
    emi_capacity: float,
    risk_band: RiskBand,
) -> int:
    """
    Select the optimal loan tenure based on EMI capacity and risk band.

    Lower-risk borrowers get longer tenure options (lower monthly burden).
    Higher-risk borrowers get shorter tenures (reduce exposure duration).

    Args:
        emi_capacity: Monthly EMI the borrower can afford (INR).
        risk_band: Assessed risk band.

    Returns:
        int: Recommended tenure in months.
    """
    # Max tenure allowed per risk band
    max_tenure_by_risk = {
        RiskBand.LOW: 36,
        RiskBand.MEDIUM: 24,
        RiskBand.HIGH: 18,
        RiskBand.VERY_HIGH: 12,
    }
    max_allowed = max_tenure_by_risk.get(risk_band, 18)

    # Filter tenure options to those within risk-allowed maximum
    available_tenures = [t for t in TENURE_OPTIONS if t <= max_allowed]
    if not available_tenures:
        return min(TENURE_OPTIONS)

    # For higher EMI capacity, prefer shorter tenures (faster repayment)
    # For lower EMI capacity, prefer longer tenures (lower monthly burden)
    if emi_capacity >= 15000:
        # High capacity — shortest available tenure
        return min(available_tenures)
    elif emi_capacity >= 8000:
        # Moderate capacity — medium tenure
        return available_tenures[len(available_tenures) // 2]
    else:
        # Low capacity — longest available tenure
        return max(available_tenures)


def _select_recommended_amount(
    *,
    min_loan: float,
    max_loan: float,
    confidence: float,
    risk_band: RiskBand,
) -> float:
    """
    Select a concrete recommended amount within the policy guardrail range.

    Higher confidence and lower risk push the recommendation closer to the
    upper end of the approved range. Higher-risk cases stay more conservative.
    """
    if max_loan <= min_loan:
        return round(max_loan / 1000) * 1000

    base_position = {
        RiskBand.LOW: 0.72,
        RiskBand.MEDIUM: 0.58,
        RiskBand.HIGH: 0.42,
        RiskBand.VERY_HIGH: 0.25,
    }.get(risk_band, 0.5)

    confidence_adjustment = (confidence - 0.5) * 0.2
    position = min(0.85, max(0.25, base_position + confidence_adjustment))

    recommended_amount = min_loan + ((max_loan - min_loan) * position)
    return round(recommended_amount / 1000) * 1000

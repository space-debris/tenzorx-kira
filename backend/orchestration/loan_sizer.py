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
from typing import Any

from models.output_schema import (
    FraudDetection,
    LoanRecommendation,
    RevenueEstimate,
    RiskAssessment,
    RiskBand,
    ValueRange,
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
) -> LoanRecommendation:
    """
    Compute a loan recommendation from revenue estimate and risk assessment.

    Uses conservative EMI-to-income ratios to ensure sustainable lending.
    Loan amounts are capped at ₹5L and only offered if the store is not
    fraud-flagged and risk band is not VERY_HIGH.

    Args:
        revenue_estimate: Monthly revenue range from the fusion engine.
            Uses monthly_low for conservative EMI calculation.
        risk_assessment: Risk band and score from the fusion engine.
            Determines risk multiplier applied to loan capacity.
        fraud_detection: Fraud detection results.
            If is_flagged=True, loan is not offered.

    Returns:
        LoanRecommendation: Eligibility, loan range, tenure, EMI estimate,
        and EMI-to-income ratio.

    Processing Steps:
        1. Check eligibility (not fraud-flagged, not VERY_HIGH risk)
        2. Compute base EMI capacity = monthly_low × MAX_EMI_TO_INCOME_RATIO
        3. Apply risk band multiplier
        4. Compute max loan from EMI capacity and tenure
        5. Apply loan amount caps (₹25K min, ₹5L max)
        6. Select optimal tenure from TENURE_OPTIONS
        7. Return complete recommendation

    TODO:
        - Implement loan sizing logic
        - Add tenure optimization (find tenure that minimizes EMI while staying within cap)
        - Add regional interest rate variation
        - Log recommendation rationale for audit
    """
    # TODO: Implement loan recommendation computation
    raise NotImplementedError("Loan sizer not yet implemented")


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
        monthly_rate: Monthly interest rate (decimal, e.g., 0.015 for 1.5%).
        tenure_months: Loan tenure in months.

    Returns:
        float: Monthly EMI amount in INR.

    TODO:
        - Implement EMI formula
        - Handle edge cases (zero interest, very short tenure)
    """
    # TODO: Implement EMI calculation
    raise NotImplementedError


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

    TODO:
        - Implement reverse EMI formula
    """
    # TODO: Implement max loan computation
    raise NotImplementedError


def _select_optimal_tenure(
    emi_capacity: float,
    risk_band: RiskBand,
) -> int:
    """
    Select the optimal loan tenure based on EMI capacity and risk band.

    Lower-risk borrowers get longer tenure options.
    Higher EMI capacity allows shorter tenures.

    Args:
        emi_capacity: Monthly EMI the borrower can afford (INR).
        risk_band: Assessed risk band.

    Returns:
        int: Recommended tenure in months.

    TODO:
        - Implement tenure selection logic
        - Consider risk band in tenure decision
    """
    # TODO: Implement tenure selection
    raise NotImplementedError

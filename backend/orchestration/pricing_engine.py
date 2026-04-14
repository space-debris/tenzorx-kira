"""
KIRA — Pricing Engine

Produces explainable pricing guidance from risk, confidence, and
utilization assumptions. The output is a recommended rate and fee plus
policy guardrail bands that underwriting overrides can be checked against.
"""

from __future__ import annotations

from models.output_schema import (
    PricingRecommendation,
    RepaymentCadence,
    RevenueEstimate,
    RiskAssessment,
    RiskBand,
    ValueRange,
)

_BASE_INTEREST_RATE = {
    RiskBand.LOW: 16.0,
    RiskBand.MEDIUM: 18.5,
    RiskBand.HIGH: 21.5,
    RiskBand.VERY_HIGH: 24.0,
}

_BASE_PROCESSING_FEE = {
    RiskBand.LOW: 1.0,
    RiskBand.MEDIUM: 1.5,
    RiskBand.HIGH: 2.0,
    RiskBand.VERY_HIGH: 2.5,
}

_PRICING_TIERS = {
    RiskBand.LOW: "standard_plus",
    RiskBand.MEDIUM: "standard",
    RiskBand.HIGH: "protected",
    RiskBand.VERY_HIGH: "exception_only",
}


def recommend_pricing(
    *,
    risk_assessment: RiskAssessment,
    revenue_estimate: RevenueEstimate,
    recommended_amount: float,
    loan_range: ValueRange,
    repayment_cadence: RepaymentCadence | None,
    emi_to_income_ratio: float,
) -> PricingRecommendation:
    """Return dynamic pricing guidance for the proposed loan."""
    risk_band = risk_assessment.risk_band
    utilization = 0.0
    if loan_range.high > 0:
        utilization = min(1.0, recommended_amount / loan_range.high)

    rate = _BASE_INTEREST_RATE[risk_band]
    fee = _BASE_PROCESSING_FEE[risk_band]
    rationale_parts: list[str] = [
        f"{risk_band.value} risk band anchors pricing to the {_PRICING_TIERS[risk_band].replace('_', ' ')} tier"
    ]

    if risk_assessment.confidence < 0.55:
        rate += 0.75
        rationale_parts.append("lower model confidence adds a modest pricing buffer")
    elif risk_assessment.confidence > 0.8:
        rate -= 0.5
        rationale_parts.append("strong confidence supports tighter pricing")

    if utilization > 0.85:
        rate += 0.5
        fee += 0.25
        rationale_parts.append("high utilization against the policy cap increases risk loading")
    elif utilization < 0.55:
        rate -= 0.25
        rationale_parts.append("moderate utilization supports a slightly sharper rate")

    if emi_to_income_ratio > 0.14:
        rate -= 0.25
        rationale_parts.append("affordability is protected by keeping pricing slightly softer")

    midpoint_revenue = (revenue_estimate.monthly_low + revenue_estimate.monthly_high) / 2.0
    if midpoint_revenue > 300000:
        fee = max(0.75, fee - 0.25)
        rationale_parts.append("stronger revenue base allows a lower upfront fee")

    if repayment_cadence == RepaymentCadence.DAILY:
        rate -= 0.25
        rationale_parts.append("daily collections reduce control risk")
    elif repayment_cadence == RepaymentCadence.MONTHLY:
        rate += 0.25
        rationale_parts.append("monthly collections warrant a small control premium")

    rate = round(min(30.0, max(12.0, rate)), 2)
    fee = round(min(4.0, max(0.5, fee)), 2)

    rate_band = ValueRange(low=max(10.0, round(rate - 1.5, 2)), high=min(32.0, round(rate + 1.5, 2)))
    fee_band = ValueRange(low=max(0.5, round(fee - 0.5, 2)), high=min(5.0, round(fee + 0.5, 2)))

    return PricingRecommendation(
        annual_interest_rate_pct=rate,
        processing_fee_pct=fee,
        annual_interest_rate_band=rate_band,
        processing_fee_band=fee_band,
        pricing_tier=_PRICING_TIERS[risk_band],
        rationale=". ".join(rationale_parts).strip() + ".",
    )

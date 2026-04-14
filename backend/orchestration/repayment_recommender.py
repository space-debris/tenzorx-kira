"""
KIRA — Repayment Recommender

Suggests a repayment cadence that aligns with the merchant's likely
cash-flow rhythm. Phase 10 uses intentionally simple heuristics so the
output remains explainable and stable even when the available data is
incomplete.
"""

from __future__ import annotations

from typing import Any

from models.output_schema import (
    CVSignals,
    GeoSignals,
    RepaymentCadence,
    RevenueEstimate,
    RiskAssessment,
)

_WEEKS_PER_MONTH = 4.33
_DAYS_PER_MONTH = 30.0


def recommend_repayment_cadence(
    revenue_estimate: RevenueEstimate,
    risk_assessment: RiskAssessment,
    cv_signals: CVSignals | None = None,
    geo_signals: GeoSignals | None = None,
) -> dict[str, Any]:
    """
    Recommend daily, weekly, or monthly repayment cadence.

    Heuristics favor:
    - daily for high-footfall, smaller, more frequent-turnover stores
    - weekly for balanced cases
    - monthly for larger, lower-frequency, or rural merchants
    """
    daily_score = 0.0
    weekly_score = 0.35
    monthly_score = 0.0
    reasons: list[str] = []

    midpoint_revenue = (
        revenue_estimate.monthly_low + revenue_estimate.monthly_high
    ) / 2.0
    confidence = risk_assessment.confidence

    if geo_signals is not None:
        if geo_signals.area_type.value == "urban":
            daily_score += 0.25
            reasons.append("urban location supports frequent collections")
        elif geo_signals.area_type.value == "semi_urban":
            weekly_score += 0.1
            reasons.append("semi-urban location supports weekly collection cycles")
        else:
            monthly_score += 0.3
            reasons.append("rural operating pattern favors lower-frequency collections")

        if geo_signals.footfall_score >= 0.7:
            daily_score += 0.25
            reasons.append("strong footfall indicates regular cash rotation")
        elif geo_signals.footfall_score <= 0.35:
            monthly_score += 0.2
            reasons.append("weaker footfall suggests slower cash inflow")
        else:
            weekly_score += 0.15

    if cv_signals is not None:
        if cv_signals.store_size_category.value == "small":
            daily_score += 0.2
            reasons.append("smaller format stores usually cycle inventory faster")
        elif cv_signals.store_size_category.value == "large":
            monthly_score += 0.2
            reasons.append("larger format stores are better suited to monthly settlement")
        else:
            weekly_score += 0.1

        if cv_signals.consistency_score >= 0.8:
            daily_score += 0.1
        elif cv_signals.consistency_score <= 0.5:
            weekly_score += 0.1
            monthly_score += 0.05

    if midpoint_revenue >= 300000:
        monthly_score += 0.15
        reasons.append("higher ticket size supports monthly repayment batching")
    elif midpoint_revenue <= 150000:
        daily_score += 0.1
        weekly_score += 0.1
        reasons.append("leaner revenue profile benefits from smaller collection bites")
    else:
        weekly_score += 0.15

    if risk_assessment.risk_band.value in {"HIGH", "VERY_HIGH"}:
        daily_score += 0.1
        weekly_score += 0.1
        reasons.append("tighter collection rhythm helps control higher-risk exposure")
    elif confidence < 0.55:
        weekly_score += 0.15
        reasons.append("moderate confidence favors a balanced weekly cadence")

    scores = {
        RepaymentCadence.DAILY: daily_score,
        RepaymentCadence.WEEKLY: weekly_score,
        RepaymentCadence.MONTHLY: monthly_score,
    }
    cadence = max(scores, key=scores.get)

    rationale_lookup = {
        RepaymentCadence.DAILY: (
            "Daily collection is recommended because the merchant profile suggests "
            "fast inventory turns and regular cash movement."
        ),
        RepaymentCadence.WEEKLY: (
            "Weekly collection is recommended as the best middle ground between "
            "merchant flexibility and portfolio control."
        ),
        RepaymentCadence.MONTHLY: (
            "Monthly collection is recommended because the merchant profile points "
            "to slower but steadier settlement cycles."
        ),
    }

    detail = "; ".join(dict.fromkeys(reasons))
    rationale = rationale_lookup[cadence]
    if detail:
        rationale = f"{rationale} Key drivers: {detail}."

    return {
        "cadence": cadence,
        "rationale": rationale,
        "scores": {key.value: round(value, 3) for key, value in scores.items()},
    }


def estimate_installment_from_monthly_equivalent(
    monthly_equivalent: float,
    cadence: RepaymentCadence | None,
) -> float | None:
    """Convert a monthly-equivalent obligation into the chosen collection cadence."""
    if monthly_equivalent <= 0 or cadence is None:
        return None

    if cadence == RepaymentCadence.DAILY:
        return round(monthly_equivalent / _DAYS_PER_MONTH, 2)
    if cadence == RepaymentCadence.WEEKLY:
        return round(monthly_equivalent / _WEEKS_PER_MONTH, 2)
    return round(monthly_equivalent, 2)

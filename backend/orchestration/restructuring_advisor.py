"""
KIRA — Restructuring Advisor

Phase 11: Early restructuring recommendation logic.

Detects meaningful drops in inflow velocity, generates alerts for
potential stress, and suggests tenor extension or temporary relief
when appropriate. Uses conservative heuristics to avoid overwhelming
lenders with false positives.

Owner: Analytics Lead
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from models.output_schema import RiskBand
from models.platform_schema import (
    LoanAccount,
    LoanAccountStatus,
    MonitoringRun,
    RestructuringSuggestion,
    TransactionSummary,
    UtilizationBreakdown,
)

logger = logging.getLogger("kira.restructuring_advisor")


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# If inflow velocity drops by this much or more, flag as stress
INFLOW_DROP_WARNING_PCT = -15.0
INFLOW_DROP_CRITICAL_PCT = -30.0

# If days past due exceeds this, suggest restructuring
DPD_WARNING_THRESHOLD = 15
DPD_CRITICAL_THRESHOLD = 30

# If avg daily balance drops below this fraction of the installment
BALANCE_STRESS_RATIO = 1.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assess_restructuring_need(
    loan: LoanAccount,
    current_summary: TransactionSummary | None,
    previous_summary: TransactionSummary | None,
    utilization: UtilizationBreakdown | None,
    monitoring_run: MonitoringRun | None = None,
) -> RestructuringSuggestion | None:
    """
    Evaluate whether a loan needs restructuring based on monitoring signals.

    The advisor checks:
    1. Inflow velocity change (credit flow momentum)
    2. Days past due
    3. Balance adequacy relative to installment obligations
    4. Utilization diversion patterns

    Returns None if no restructuring is warranted.
    """
    alerts: list[str] = []
    stress_score = 0.0

    # Check 1: Inflow velocity change
    inflow_change_pct = _compute_inflow_velocity_change(
        current_summary, previous_summary,
    )
    if inflow_change_pct is not None:
        if inflow_change_pct <= INFLOW_DROP_CRITICAL_PCT:
            stress_score += 0.4
            alerts.append(
                f"Critical inflow drop: {inflow_change_pct:+.1f}% decline in credit velocity"
            )
        elif inflow_change_pct <= INFLOW_DROP_WARNING_PCT:
            stress_score += 0.2
            alerts.append(
                f"Inflow slowdown: {inflow_change_pct:+.1f}% decline in credit velocity"
            )

    # Check 2: Days past due
    if loan.days_past_due >= DPD_CRITICAL_THRESHOLD:
        stress_score += 0.35
        alerts.append(f"Loan is {loan.days_past_due} days past due (critical)")
    elif loan.days_past_due >= DPD_WARNING_THRESHOLD:
        stress_score += 0.15
        alerts.append(f"Loan is {loan.days_past_due} days past due")

    # Check 3: Balance adequacy
    if current_summary and loan.estimated_installment > 0:
        balance_ratio = (
            current_summary.avg_daily_balance / loan.estimated_installment
        )
        if balance_ratio < BALANCE_STRESS_RATIO:
            stress_score += 0.2
            alerts.append(
                f"Average daily balance (₹{current_summary.avg_daily_balance:,.0f}) "
                f"is only {balance_ratio:.1f}x the installment"
            )

    # Check 4: Utilization concerns
    if utilization:
        if utilization.diversion_risk == "high":
            stress_score += 0.2
            alerts.append("Fund utilization shows high diversion risk")
        elif utilization.diversion_risk == "medium":
            stress_score += 0.1
            alerts.append("Fund utilization shows moderate diversion risk")

    # Decide if restructuring is warranted
    if stress_score < 0.3:
        logger.info(
            "Loan %s: stress_score=%.2f — no restructuring needed",
            loan.id, stress_score,
        )
        return None

    # Generate the restructuring suggestion
    suggestion = _generate_suggestion(
        loan=loan,
        stress_score=stress_score,
        inflow_change_pct=inflow_change_pct,
        alerts=alerts,
    )

    logger.info(
        "Restructuring suggested for loan %s: type=%s, stress=%.2f, alerts=%d",
        loan.id, suggestion.suggestion_type, stress_score, len(alerts),
    )

    return suggestion


def generate_stress_alerts(
    loan: LoanAccount,
    current_summary: TransactionSummary | None,
    previous_summary: TransactionSummary | None,
) -> list[str]:
    """
    Generate alert strings for deteriorating cash-flow patterns.
    Returns a list of alert descriptions (may be empty).
    """
    alerts: list[str] = []

    inflow_change = _compute_inflow_velocity_change(current_summary, previous_summary)
    if inflow_change is not None and inflow_change <= INFLOW_DROP_WARNING_PCT:
        alerts.append(
            f"Inflow velocity declined by {abs(inflow_change):.1f}% — "
            f"monitor closely for sustained stress"
        )

    if current_summary and loan.estimated_installment > 0:
        months_runway = (
            current_summary.avg_daily_balance * 30
        ) / max(1, loan.estimated_installment)
        if months_runway < 2:
            alerts.append(
                f"Balance runway is approximately {months_runway:.1f} months — "
                f"near-term collection risk elevated"
            )

    if loan.days_past_due >= DPD_WARNING_THRESHOLD:
        alerts.append(
            f"Loan has been {loan.days_past_due} days past due — "
            f"manual follow-up recommended"
        )

    if loan.status in {LoanAccountStatus.OVERDUE, LoanAccountStatus.NPA}:
        alerts.append(
            f"Loan is in {loan.status.value.upper()} status — "
            f"immediate attention required"
        )

    return alerts


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _compute_inflow_velocity_change(
    current: TransactionSummary | None,
    previous: TransactionSummary | None,
) -> float | None:
    """
    Compute the percentage change in credit inflow velocity.

    Velocity = total_credits / period_days (normalized daily inflow).
    Returns None if insufficient data.
    """
    if current is None or previous is None:
        return None

    current_days = max(1, current.period_days)
    previous_days = max(1, previous.period_days)

    current_velocity = current.total_credits / current_days
    previous_velocity = previous.total_credits / previous_days

    if previous_velocity <= 0:
        return None

    change_pct = ((current_velocity - previous_velocity) / previous_velocity) * 100
    return round(change_pct, 2)


def _generate_suggestion(
    *,
    loan: LoanAccount,
    stress_score: float,
    inflow_change_pct: float | None,
    alerts: list[str],
) -> RestructuringSuggestion:
    """Generate a restructuring suggestion based on the severity of stress."""

    # Severe stress → moratorium + tenure extension
    if stress_score >= 0.6:
        return RestructuringSuggestion(
            loan_id=loan.id,
            case_id=loan.case_id,
            org_id=loan.org_id,
            trigger="; ".join(alerts[:3]),
            suggestion_type="moratorium_plus_extension",
            suggested_moratorium_months=2,
            suggested_tenure_extension_months=6,
            rationale=(
                f"The loan shows significant stress (score {stress_score:.2f}) with "
                f"multiple deterioration signals. A 2-month moratorium followed by "
                f"6-month tenure extension would reduce immediate collection pressure "
                f"and allow the merchant time to recover cash-flow stability."
            ),
        )

    # Moderate stress → tenure extension
    if stress_score >= 0.4:
        extension = 3 if loan.tenure_months <= 18 else 6
        return RestructuringSuggestion(
            loan_id=loan.id,
            case_id=loan.case_id,
            org_id=loan.org_id,
            trigger="; ".join(alerts[:3]),
            suggestion_type="tenure_extension",
            suggested_tenure_extension_months=extension,
            suggested_emi_reduction_pct=round((extension / (loan.tenure_months + extension)) * 100, 1),
            rationale=(
                f"Moderate stress indicators (score {stress_score:.2f}) suggest the "
                f"merchant is experiencing temporary cash-flow tightness. Extending "
                f"tenure by {extension} months would reduce the per-period obligation "
                f"and improve sustainability without requiring a moratorium."
            ),
        )

    # Mild stress → EMI reduction
    return RestructuringSuggestion(
        loan_id=loan.id,
        case_id=loan.case_id,
        org_id=loan.org_id,
        trigger="; ".join(alerts[:3]),
        suggestion_type="emi_reduction",
        suggested_emi_reduction_pct=15.0,
        suggested_tenure_extension_months=3,
        rationale=(
            f"Early stress signals (score {stress_score:.2f}) warrant a preventive "
            f"adjustment. A 15% EMI reduction with 3-month extension provides headroom "
            f"while keeping the total restructuring impact minimal."
        ),
    )

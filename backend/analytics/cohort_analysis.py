"""
KIRA — Cohort Analysis

Phase 12: Cohort segmentation, vintage analysis, and benchmark logic.

Groups loans by origination period, geography, risk tier, and product
type. Produces comparative metrics for trend visualization.

Owner: Analytics Lead
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from models.output_schema import RiskBand
from models.platform_schema import LoanAccount, LoanAccountStatus
from storage.repository import PlatformRepository

logger = logging.getLogger("kira.cohort_analysis")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class CohortBucket(BaseModel):
    """A single cohort bucket with aggregated metrics."""

    label: str
    loan_count: int = 0
    total_disbursed: float = 0.0
    total_outstanding: float = 0.0
    avg_dpd: float = 0.0
    overdue_pct: float = 0.0
    npa_pct: float = 0.0
    avg_risk_score: float = 0.0


class CohortSeries(BaseModel):
    """A named series of cohort buckets for charting."""

    dimension: str
    buckets: list[CohortBucket] = Field(default_factory=list)


class CohortAnalysisResult(BaseModel):
    """Full cohort analysis result."""

    by_vintage: CohortSeries
    by_risk_tier: CohortSeries
    by_state: CohortSeries
    by_cadence: CohortSeries
    benchmarks: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_cohort_analysis(
    repository: PlatformRepository,
    org_id: uuid.UUID,
) -> CohortAnalysisResult:
    """
    Run cohort analysis across the lender's loan portfolio.

    Segments by:
    1. Vintage (disbursement month)
    2. Risk tier (original risk band)
    3. Geography (state)
    4. Repayment cadence
    """
    loans = repository.list_loan_accounts(org_id=org_id)
    kiranas = repository.list_kiranas(org_id)
    kirana_map = {str(k.id): k for k in kiranas}

    by_vintage = _segment_by_vintage(loans)
    by_risk = _segment_by_risk_tier(loans)
    by_state = _segment_by_state(loans, kirana_map)
    by_cadence = _segment_by_cadence(loans)
    benchmarks = _compute_benchmarks(loans)

    logger.info("Cohort analysis: %d loans segmented", len(loans))

    return CohortAnalysisResult(
        by_vintage=by_vintage,
        by_risk_tier=by_risk,
        by_state=by_state,
        by_cadence=by_cadence,
        benchmarks=benchmarks,
    )


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------


def _segment_by_vintage(loans: list[LoanAccount]) -> CohortSeries:
    """Group loans by disbursement month."""
    groups: dict[str, list[LoanAccount]] = defaultdict(list)
    for loan in loans:
        if loan.disbursed_at:
            key = loan.disbursed_at.strftime("%Y-%m")
        else:
            key = loan.created_at.strftime("%Y-%m")
        groups[key].append(loan)

    buckets = [
        _build_bucket(label, group)
        for label, group in sorted(groups.items())
    ]
    return CohortSeries(dimension="vintage_month", buckets=buckets)


def _segment_by_risk_tier(loans: list[LoanAccount]) -> CohortSeries:
    """Group loans by original risk band."""
    groups: dict[str, list[LoanAccount]] = defaultdict(list)
    for loan in loans:
        band = (loan.original_risk_band or RiskBand.MEDIUM).value
        groups[band].append(loan)

    order = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    buckets = [
        _build_bucket(label, groups.get(label, []))
        for label in order
        if groups.get(label)
    ]
    return CohortSeries(dimension="risk_tier", buckets=buckets)


def _segment_by_state(
    loans: list[LoanAccount],
    kirana_map: dict[str, Any],
) -> CohortSeries:
    """Group loans by kirana state."""
    groups: dict[str, list[LoanAccount]] = defaultdict(list)
    for loan in loans:
        kirana = kirana_map.get(str(loan.kirana_id))
        state = kirana.location.state if kirana else "Unknown"
        groups[state].append(loan)

    buckets = sorted(
        [_build_bucket(label, group) for label, group in groups.items()],
        key=lambda b: b.total_outstanding,
        reverse=True,
    )
    return CohortSeries(dimension="state", buckets=buckets[:15])


def _segment_by_cadence(loans: list[LoanAccount]) -> CohortSeries:
    """Group loans by repayment cadence."""
    groups: dict[str, list[LoanAccount]] = defaultdict(list)
    for loan in loans:
        groups[loan.repayment_cadence.value].append(loan)

    buckets = [_build_bucket(label, group) for label, group in groups.items()]
    return CohortSeries(dimension="repayment_cadence", buckets=buckets)


# ---------------------------------------------------------------------------
# Bucket Builder
# ---------------------------------------------------------------------------


def _build_bucket(label: str, loans: list[LoanAccount]) -> CohortBucket:
    """Aggregate metrics for a group of loans."""
    if not loans:
        return CohortBucket(label=label)

    count = len(loans)
    total_disbursed = sum(l.principal_amount for l in loans)
    total_outstanding = sum(l.outstanding_principal or 0 for l in loans)
    avg_dpd = sum(l.days_past_due for l in loans) / count

    overdue_count = sum(
        1 for l in loans
        if l.status in {LoanAccountStatus.OVERDUE, LoanAccountStatus.NPA}
    )
    npa_count = sum(1 for l in loans if l.status == LoanAccountStatus.NPA)

    risk_scores = {
        RiskBand.LOW: 0.25,
        RiskBand.MEDIUM: 0.45,
        RiskBand.HIGH: 0.65,
        RiskBand.VERY_HIGH: 0.85,
    }
    avg_risk = sum(
        risk_scores.get(l.original_risk_band or RiskBand.MEDIUM, 0.45)
        for l in loans
    ) / count

    return CohortBucket(
        label=label,
        loan_count=count,
        total_disbursed=round(total_disbursed, 2),
        total_outstanding=round(total_outstanding, 2),
        avg_dpd=round(avg_dpd, 1),
        overdue_pct=round(overdue_count / count * 100, 1),
        npa_pct=round(npa_count / count * 100, 1),
        avg_risk_score=round(avg_risk, 3),
    )


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


def _compute_benchmarks(loans: list[LoanAccount]) -> dict[str, Any]:
    """Compute portfolio-wide benchmark metrics."""
    if not loans:
        return {
            "portfolio_avg_dpd": 0,
            "portfolio_overdue_rate": 0,
            "portfolio_npa_rate": 0,
            "portfolio_avg_tenure": 0,
            "portfolio_avg_rate": 0,
        }

    count = len(loans)
    return {
        "portfolio_avg_dpd": round(sum(l.days_past_due for l in loans) / count, 1),
        "portfolio_overdue_rate": round(
            sum(1 for l in loans if l.status == LoanAccountStatus.OVERDUE) / count * 100, 1
        ),
        "portfolio_npa_rate": round(
            sum(1 for l in loans if l.status == LoanAccountStatus.NPA) / count * 100, 1
        ),
        "portfolio_avg_tenure": round(sum(l.tenure_months for l in loans) / count, 1),
        "portfolio_avg_rate": round(
            sum(l.annual_interest_rate_pct for l in loans) / count, 2
        ),
    }

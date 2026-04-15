"""
KIRA — Portfolio Metrics

Phase 12: KPI aggregation and summary metrics for the lender portfolio.

Computes portfolio-level statistics from persistent loan, case, and
kirana data. Designed for dashboard rendering and CSV/JSON export.

Owner: Analytics Lead
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from models.output_schema import RiskBand
from models.platform_schema import (
    CaseStatus,
    LoanAccount,
    LoanAccountStatus,
)
from storage.repository import PlatformRepository

logger = logging.getLogger("kira.portfolio_metrics")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class PortfolioKpis(BaseModel):
    """Top-level KPI strip for the portfolio dashboard."""

    total_kiranas: int = 0
    total_cases: int = 0
    total_loans: int = 0
    active_loans: int = 0
    total_disbursed: float = 0.0
    total_outstanding: float = 0.0
    total_collected: float = 0.0
    avg_loan_size: float = 0.0
    overdue_count: int = 0
    npa_count: int = 0
    restructured_count: int = 0
    closed_count: int = 0
    high_risk_count: int = 0
    fraud_flagged_count: int = 0
    open_alerts: int = 0


class RiskDistribution(BaseModel):
    """Risk band distribution across the portfolio."""

    low: int = 0
    medium: int = 0
    high: int = 0
    very_high: int = 0


class GeographicConcentration(BaseModel):
    """Loan concentration by state and district."""

    by_state: dict[str, int] = Field(default_factory=dict)
    by_district: dict[str, int] = Field(default_factory=dict)
    by_pin_code: dict[str, int] = Field(default_factory=dict)


class StatusBreakdown(BaseModel):
    """Case and loan status distribution."""

    cases_by_status: dict[str, int] = Field(default_factory=dict)
    loans_by_status: dict[str, int] = Field(default_factory=dict)


class PortfolioSummary(BaseModel):
    """Full portfolio summary for the dashboard."""

    kpis: PortfolioKpis
    risk_distribution: RiskDistribution
    geographic_concentration: GeographicConcentration
    status_breakdown: StatusBreakdown
    exposure_by_risk: dict[str, float] = Field(default_factory=dict)
    top_exposures: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

import uuid


def compute_portfolio_summary(
    repository: PlatformRepository,
    org_id: uuid.UUID,
) -> PortfolioSummary:
    """
    Compute complete portfolio summary for a lender organization.

    Aggregates across kiranas, cases, loans, assessments, and alerts
    to produce dashboard-ready metrics.
    """
    kiranas = repository.list_kiranas(org_id)
    cases = repository.list_cases(org_id)
    loans = repository.list_loan_accounts(org_id=org_id)
    alerts = repository.list_alerts(org_id=org_id)
    open_alerts = [a for a in alerts if a.status.value == "open"]

    # --- KPIs ---
    active_statuses = {
        LoanAccountStatus.ACTIVE,
        LoanAccountStatus.CURRENT,
        LoanAccountStatus.OVERDUE,
    }
    active_loans = [l for l in loans if l.status in active_statuses]
    total_disbursed = sum(l.principal_amount for l in loans)
    total_outstanding = sum(l.outstanding_principal or 0 for l in loans)
    total_collected = sum(l.total_collected for l in loans)

    overdue_count = sum(1 for l in loans if l.status == LoanAccountStatus.OVERDUE)
    npa_count = sum(1 for l in loans if l.status == LoanAccountStatus.NPA)
    restructured_count = sum(1 for l in loans if l.status == LoanAccountStatus.RESTRUCTURED)
    closed_count = sum(1 for l in loans if l.status == LoanAccountStatus.CLOSED)

    high_risk_count = sum(
        1 for l in loans
        if l.original_risk_band in {RiskBand.HIGH, RiskBand.VERY_HIGH}
    )

    fraud_flagged_count = 0
    for case in cases:
        if case.latest_assessment_session_id:
            summary = repository.get_assessment_summary(case.latest_assessment_session_id)
            if summary and summary.fraud_flagged:
                fraud_flagged_count += 1

    kpis = PortfolioKpis(
        total_kiranas=len(kiranas),
        total_cases=len(cases),
        total_loans=len(loans),
        active_loans=len(active_loans),
        total_disbursed=round(total_disbursed, 2),
        total_outstanding=round(total_outstanding, 2),
        total_collected=round(total_collected, 2),
        avg_loan_size=round(total_disbursed / max(1, len(loans)), 2),
        overdue_count=overdue_count,
        npa_count=npa_count,
        restructured_count=restructured_count,
        closed_count=closed_count,
        high_risk_count=high_risk_count,
        fraud_flagged_count=fraud_flagged_count,
        open_alerts=len(open_alerts),
    )

    # --- Risk Distribution ---
    risk_dist = RiskDistribution()
    for loan in loans:
        band = loan.original_risk_band
        if band == RiskBand.LOW:
            risk_dist.low += 1
        elif band == RiskBand.MEDIUM:
            risk_dist.medium += 1
        elif band == RiskBand.HIGH:
            risk_dist.high += 1
        elif band == RiskBand.VERY_HIGH:
            risk_dist.very_high += 1

    # --- Geographic Concentration ---
    kirana_map = {str(k.id): k for k in kiranas}
    by_state: Counter = Counter()
    by_district: Counter = Counter()
    by_pin: Counter = Counter()

    for loan in loans:
        kirana = kirana_map.get(str(loan.kirana_id))
        if kirana:
            by_state[kirana.location.state] += 1
            by_district[kirana.location.district] += 1
            by_pin[kirana.location.pin_code] += 1

    geo = GeographicConcentration(
        by_state=dict(by_state.most_common(20)),
        by_district=dict(by_district.most_common(20)),
        by_pin_code=dict(by_pin.most_common(20)),
    )

    # --- Status Breakdown ---
    cases_by_status = Counter(c.status.value for c in cases)
    loans_by_status = Counter(l.status.value for l in loans)

    status = StatusBreakdown(
        cases_by_status=dict(cases_by_status),
        loans_by_status=dict(loans_by_status),
    )

    # --- Exposure by Risk ---
    exposure_by_risk: dict[str, float] = defaultdict(float)
    for loan in loans:
        band = (loan.original_risk_band or RiskBand.MEDIUM).value
        exposure_by_risk[band] += loan.outstanding_principal or 0

    # --- Top Exposures ---
    top = sorted(loans, key=lambda l: l.outstanding_principal or 0, reverse=True)[:10]
    top_exposures = []
    for loan in top:
        kirana = kirana_map.get(str(loan.kirana_id))
        top_exposures.append({
            "loan_id": str(loan.id),
            "kirana_name": kirana.store_name if kirana else "Unknown",
            "state": kirana.location.state if kirana else "Unknown",
            "outstanding": loan.outstanding_principal or 0,
            "principal": loan.principal_amount,
            "risk_band": (loan.original_risk_band or RiskBand.MEDIUM).value,
            "status": loan.status.value,
            "days_past_due": loan.days_past_due,
        })

    logger.info(
        "Portfolio summary: %d loans, ₹%s outstanding, %d high-risk",
        len(loans), f"{total_outstanding:,.0f}", high_risk_count,
    )

    return PortfolioSummary(
        kpis=kpis,
        risk_distribution=risk_dist,
        geographic_concentration=geo,
        status_breakdown=status,
        exposure_by_risk={k: round(v, 2) for k, v in exposure_by_risk.items()},
        top_exposures=top_exposures,
    )

"""Portfolio KPI aggregation helpers."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.platform_schema import AlertStatus, CaseStatus, PortfolioMetricCard
from storage.repository import PlatformRepository


class PortfolioKpis(BaseModel):
    total_kiranas: int = 0
    total_cases: int = 0
    total_loans: int = 0
    active_loans: int = 0
    total_disbursed: float = 0.0
    total_outstanding: float = 0.0


class RiskDistribution(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    very_high: int = 0


class GeographicConcentration(BaseModel):
    by_state: dict[str, int] = Field(default_factory=dict)


class StatusBreakdown(BaseModel):
    cases_by_status: dict[str, int] = Field(default_factory=dict)


class PortfolioSummary(BaseModel):
    kpis: PortfolioKpis = Field(default_factory=PortfolioKpis)
    risk_distribution: RiskDistribution = Field(default_factory=RiskDistribution)
    geographic_concentration: GeographicConcentration = Field(default_factory=GeographicConcentration)
    status_breakdown: StatusBreakdown = Field(default_factory=StatusBreakdown)


def build_portfolio_metrics(repository: PlatformRepository, org_id) -> list[PortfolioMetricCard]:
    cases = repository.list_cases(org_id)
    alerts = repository.list_alerts(org_id=org_id)
    loans = repository.list_loan_accounts(org_id=org_id)

    return [
        PortfolioMetricCard(label="Total kiranas onboarded", value=len(repository.list_kiranas(org_id))),
        PortfolioMetricCard(label="Total approved and disbursed", value=sum(1 for case in cases if case.status in {CaseStatus.APPROVED, CaseStatus.DISBURSED, CaseStatus.MONITORING, CaseStatus.RESTRUCTURED, CaseStatus.CLOSED})),
        PortfolioMetricCard(label="Active exposure", value=round(sum((loan.outstanding_principal or 0) for loan in loans), 2)),
        PortfolioMetricCard(label="High-risk count", value=sum(1 for case in cases if getattr(case.latest_risk_band, "value", None) in {"HIGH", "VERY_HIGH"})),
        PortfolioMetricCard(label="Stress-alert count", value=len([alert for alert in alerts if alert.status == AlertStatus.OPEN])),
        PortfolioMetricCard(label="Restructured count", value=sum(1 for case in cases if case.status == CaseStatus.RESTRUCTURED)),
    ]

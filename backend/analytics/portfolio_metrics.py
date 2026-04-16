"""Portfolio KPI aggregation helpers."""

from __future__ import annotations

from models.platform_schema import AlertStatus, CaseStatus, PortfolioMetricCard
from storage.repository import PlatformRepository


def build_portfolio_metrics(repository: PlatformRepository, org_id) -> list[PortfolioMetricCard]:
    cases = repository.list_cases(org_id)
    alerts = repository.list_alerts(org_id=org_id)
    loans = repository.list_loan_accounts(org_id=org_id)

    return [
        PortfolioMetricCard(label="Total kiranas onboarded", value=len(repository.list_kiranas(org_id))),
        PortfolioMetricCard(label="Total approved and disbursed", value=sum(1 for case in cases if case.status in {CaseStatus.APPROVED, CaseStatus.DISBURSED, CaseStatus.MONITORING, CaseStatus.RESTRUCTURED, CaseStatus.CLOSED})),
        PortfolioMetricCard(label="Active exposure", value=round(sum(loan.outstanding_amount for loan in loans), 2)),
        PortfolioMetricCard(label="High-risk count", value=sum(1 for case in cases if getattr(case.latest_risk_band, "value", None) in {"HIGH", "VERY_HIGH"})),
        PortfolioMetricCard(label="Stress-alert count", value=len([alert for alert in alerts if alert.status == AlertStatus.OPEN])),
        PortfolioMetricCard(label="Restructured count", value=sum(1 for case in cases if case.status == CaseStatus.RESTRUCTURED)),
    ]

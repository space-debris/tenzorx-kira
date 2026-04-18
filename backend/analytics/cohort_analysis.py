"""
Cohort and segmentation helpers for portfolio views.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel, Field

from storage.repository import PlatformRepository


class CohortBucket(BaseModel):
    label: str
    loan_count: int = 0
    total_disbursed: float = 0.0
    overdue_pct: float = 0.0


class CohortSeries(BaseModel):
    dimension: str
    buckets: list[CohortBucket] = Field(default_factory=list)


class CohortAnalysisResult(BaseModel):
    by_vintage: CohortSeries
    by_risk_tier: CohortSeries
    by_state: CohortSeries
    by_cadence: CohortSeries


def _build_bucket(label: str, loans: list) -> CohortBucket:
    loan_count = len(loans)
    total_disbursed = round(sum(float(getattr(loan, "principal_amount", 0.0) or 0.0) for loan in loans), 2)
    overdue_count = sum(1 for loan in loans if int(getattr(loan, "days_past_due", 0) or 0) > 0)
    overdue_pct = round((overdue_count / loan_count) * 100, 2) if loan_count else 0.0
    return CohortBucket(
        label=label,
        loan_count=loan_count,
        total_disbursed=total_disbursed,
        overdue_pct=overdue_pct,
    )


def build_cohort_analysis(repository: PlatformRepository, org_id) -> list[dict]:
    cohorts: dict[str, dict] = defaultdict(lambda: {"cases": 0, "exposure": 0.0, "high_risk": 0})
    for case in repository.list_cases(org_id):
        month_key = case.created_at.strftime("%Y-%m")
        cohorts[month_key]["cases"] += 1
        cohorts[month_key]["exposure"] += (case.latest_loan_range.high if case.latest_loan_range else 0.0)
        if getattr(case.latest_risk_band, "value", None) in {"HIGH", "VERY_HIGH"}:
            cohorts[month_key]["high_risk"] += 1

    results = [
        {
            "cohort": key,
            "cases": value["cases"],
            "exposure": round(value["exposure"], 2),
            "high_risk_share": round(value["high_risk"] / value["cases"], 3) if value["cases"] else 0.0,
        }
        for key, value in sorted(cohorts.items())
    ]

    if not results:
        return results

    month_sequence = []
    current = datetime.utcnow().replace(day=1)
    for _ in range(6):
        month_sequence.append(current.strftime("%Y-%m"))
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12)
        else:
            current = current.replace(month=current.month - 1)
    month_sequence.reverse()

    result_map = {item["cohort"]: item for item in results}
    return [
        result_map.get(
            cohort,
            {
                "cohort": cohort,
                "cases": 0,
                "exposure": 0.0,
                "high_risk_share": 0.0,
            },
        )
        for cohort in month_sequence
    ]

"""
Cohort and segmentation helpers for portfolio views.
"""

from __future__ import annotations

from collections import defaultdict

from storage.repository import PlatformRepository


def build_cohort_analysis(repository: PlatformRepository, org_id) -> list[dict]:
    cohorts: dict[str, dict] = defaultdict(lambda: {"cases": 0, "exposure": 0.0, "high_risk": 0})
    for case in repository.list_cases(org_id):
        month_key = case.created_at.strftime("%Y-%m")
        cohorts[month_key]["cases"] += 1
        cohorts[month_key]["exposure"] += (case.latest_loan_range.high if case.latest_loan_range else 0.0)
        if getattr(case.latest_risk_band, "value", None) in {"HIGH", "VERY_HIGH"}:
            cohorts[month_key]["high_risk"] += 1

    return [
        {
            "cohort": key,
            "cases": value["cases"],
            "exposure": round(value["exposure"], 2),
            "high_risk_share": round(value["high_risk"] / value["cases"], 3) if value["cases"] else 0.0,
        }
        for key, value in sorted(cohorts.items())
    ]

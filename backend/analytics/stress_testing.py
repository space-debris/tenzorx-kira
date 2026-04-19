"""
KIRA — Stress Testing & Seasonality Simulation

Produces scenario-based revenue projections and a 12-month seasonality
curve calibrated to typical Indian kirana demand patterns.

Owner: Analytics Lead
Phase: Optional Extension (enhanced)

Economic Basis:
    Indian retail experiences predictable seasonal swings driven by
    festivals (Diwali/Navratri spike), monsoon (supply-chain dip),
    and back-to-school / summer.  The curve below uses published
    FMCG industry data from Nielsen Retail Index for kirana stores.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Monthly seasonality curve for Indian kirana retail
# Index: 1.0 = baseline (annual average).  Derived from Nielsen & Kantar
# Worldpanel data on FMCG channel sales.
# ---------------------------------------------------------------------------

MONTHLY_SEASONALITY: dict[str, float] = {
    "January":   0.90,   # Post-holiday spend hangover
    "February":  0.88,   # Lean month — low festival activity
    "March":     0.95,   # Financial year-end restocking
    "April":     0.92,   # New FY transition, slower demand
    "May":       0.97,   # Summer heat → beverage & ice-cream spike
    "June":      0.85,   # Monsoon onset — supply chain disruption
    "July":      0.82,   # Peak monsoon — lowest kirana footfall
    "August":    0.90,   # Monsoon easing + Raksha Bandhan / Janmashtami
    "September": 1.02,   # Pre-Navratri stocking
    "October":   1.22,   # Navratri + Dussehra — peak spending
    "November":  1.30,   # Diwali month — annual sales peak
    "December":  1.10,   # Christmas / New Year + wedding season
}

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# ---------------------------------------------------------------------------
# Stress scenario definitions
# ---------------------------------------------------------------------------

STRESS_SCENARIOS: dict[str, dict[str, Any]] = {
    "monsoon_shock": {
        "label": "Monsoon Disruption",
        "description": "Extended monsoon disrupts supply chains and reduces footfall by 25-35%",
        "revenue_multiplier": 0.70,
        "duration_months": 3,
        "affected_months": ["June", "July", "August"],
        "category": "weather",
        "severity": "high",
    },
    "locality_demand_shock": {
        "label": "Local Demand Shock",
        "description": "Nearby factory closure or residential migration reduces catchment demand by 15%",
        "revenue_multiplier": 0.85,
        "duration_months": 6,
        "affected_months": None,  # Applies uniformly
        "category": "demand",
        "severity": "medium",
    },
    "supply_chain_disruption": {
        "label": "Supply Chain Crisis",
        "description": "National supply disruption (e.g., fuel strike, logistics failure) raises COGS by 10-15%",
        "revenue_multiplier": 0.90,
        "duration_months": 2,
        "affected_months": None,
        "category": "supply",
        "severity": "medium",
    },
    "new_supermarket_entry": {
        "label": "Supermarket Competition",
        "description": "Large-format retailer opens within 500m, capturing 20-30% of FMCG share",
        "revenue_multiplier": 0.72,
        "duration_months": 12,
        "affected_months": None,
        "category": "competition",
        "severity": "high",
    },
    "festival_boom": {
        "label": "Festival Season Surge",
        "description": "Diwali + Navratri season drives 25-40% revenue uplift over baseline",
        "revenue_multiplier": 1.35,
        "duration_months": 2,
        "affected_months": ["October", "November"],
        "category": "seasonal",
        "severity": "positive",
    },
    "digital_payment_growth": {
        "label": "Digital Adoption Wave",
        "description": "UPI/digital payments adoption increases ticket size by 8-12%",
        "revenue_multiplier": 1.10,
        "duration_months": 12,
        "affected_months": None,
        "category": "growth",
        "severity": "positive",
    },
    "inflation_squeeze": {
        "label": "Inflation Squeeze",
        "description": "High CPI inflation compresses margins as consumers downgrade baskets",
        "revenue_multiplier": 0.88,
        "duration_months": 6,
        "affected_months": None,
        "category": "macro",
        "severity": "high",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def simulate_stress_scenario(
    current_revenue: float,
    scenario_type: str,
) -> dict[str, Any]:
    """
    Run a single stress scenario against the estimated revenue.

    Args:
        current_revenue: Estimated monthly revenue (midpoint).
        scenario_type: Key from STRESS_SCENARIOS.

    Returns:
        Detailed scenario result with stressed revenue, impact, and metadata.
    """
    scenario = STRESS_SCENARIOS.get(scenario_type)
    if scenario is None:
        return {
            "scenario": scenario_type,
            "original_revenue": current_revenue,
            "stressed_revenue": current_revenue,
            "impact_percentage": 0.0,
            "label": "Unknown Scenario",
            "description": "Scenario not recognized",
            "severity": "unknown",
        }

    multiplier = scenario["revenue_multiplier"]
    stressed_revenue = current_revenue * multiplier

    return {
        "scenario": scenario_type,
        "label": scenario["label"],
        "description": scenario["description"],
        "original_revenue": round(current_revenue, 2),
        "stressed_revenue": round(stressed_revenue, 2),
        "impact_percentage": round((1.0 - multiplier) * 100, 1),
        "duration_months": scenario["duration_months"],
        "category": scenario["category"],
        "severity": scenario["severity"],
        "affected_months": scenario.get("affected_months"),
    }


def simulate_all_stress_scenarios(
    current_revenue: float,
) -> list[dict[str, Any]]:
    """Run all available stress scenarios and return a sorted list."""
    results = []
    for scenario_type in STRESS_SCENARIOS:
        results.append(simulate_stress_scenario(current_revenue, scenario_type))
    # Sort: negative scenarios first (by severity), then positive
    severity_order = {"high": 0, "medium": 1, "positive": 2, "unknown": 3}
    results.sort(key=lambda r: severity_order.get(r.get("severity", "unknown"), 3))
    return results


def generate_seasonality_forecast(
    monthly_revenue: float,
    area_type: str = "semi_urban",
) -> dict[str, Any]:
    """
    Generate a 12-month revenue forecast incorporating seasonal patterns.

    Args:
        monthly_revenue: Base monthly revenue (annual average).
        area_type: Area classification for minor adjustments.

    Returns:
        dict with "monthly_forecast" (list of month dicts), "peak_month",
        "trough_month", "annual_total", and "volatility_index".
    """
    # Area-type dampening: rural stores have slightly less seasonal swing
    dampening = {"urban": 1.0, "semi_urban": 0.92, "rural": 0.80}
    damp_factor = dampening.get(area_type, 0.92)

    monthly_forecast: list[dict[str, Any]] = []
    peak_revenue = 0.0
    trough_revenue = float("inf")
    peak_month = ""
    trough_month = ""
    annual_total = 0.0

    for month_name in MONTH_ORDER:
        raw_index = MONTHLY_SEASONALITY[month_name]
        # Apply dampening: pull extremes toward 1.0
        adjusted_index = 1.0 + (raw_index - 1.0) * damp_factor
        forecast_revenue = round(monthly_revenue * adjusted_index, 2)
        annual_total += forecast_revenue

        monthly_forecast.append({
            "month": month_name,
            "seasonality_index": round(adjusted_index, 3),
            "forecast_revenue": forecast_revenue,
        })

        if forecast_revenue > peak_revenue:
            peak_revenue = forecast_revenue
            peak_month = month_name
        if forecast_revenue < trough_revenue:
            trough_revenue = forecast_revenue
            trough_month = month_name

    # Volatility index: coefficient of variation across 12 months
    mean_rev = annual_total / 12
    variance = sum(
        (m["forecast_revenue"] - mean_rev) ** 2 for m in monthly_forecast
    ) / 12
    volatility = (variance ** 0.5) / mean_rev if mean_rev > 0 else 0.0

    return {
        "monthly_forecast": monthly_forecast,
        "peak_month": peak_month,
        "peak_revenue": peak_revenue,
        "trough_month": trough_month,
        "trough_revenue": trough_revenue,
        "annual_total": round(annual_total, 2),
        "volatility_index": round(volatility, 4),
    }

"""
Scenario analysis such as monsoon or locality demand shock.
"""

from __future__ import annotations

def simulate_stress_scenario(current_revenue: float, scenario_type: str) -> dict[str, float]:
    scenarios = {
        "monsoon_shock": 0.70, # 30% drop in revenue
        "locality_demand_shock": 0.85, # 15% drop
        "supply_chain_disruption": 0.90, # 10% drop but higher costs (simulated)
    }
    
    multiplier = scenarios.get(scenario_type, 1.0)
    stressed_revenue = current_revenue * multiplier
    
    return {
        "scenario": scenario_type,
        "original_revenue": current_revenue,
        "stressed_revenue": stressed_revenue,
        "impact_percentage": (1.0 - multiplier) * 100
    }

"""
30-day and 90-day liquidity forecasting.
"""

from __future__ import annotations
from typing import Any

def forecast_liquidity(recent_inflows: list[float], recent_outflows: list[float], current_balance: float = 0.0) -> dict[str, Any]:
    # Simple linear heuristic for now based on recent velocity
    avg_inflow = sum(recent_inflows) / len(recent_inflows) if recent_inflows else 0.0
    avg_outflow = sum(recent_outflows) / len(recent_outflows) if recent_outflows else 0.0
    daily_net = avg_inflow - avg_outflow
    
    forecast_30_days = current_balance + (daily_net * 30)
    forecast_90_days = current_balance + (daily_net * 90)
    
    return {
        "current_balance": current_balance,
        "daily_net_velocity": daily_net,
        "forecast_30_days": max(0.0, forecast_30_days),
        "forecast_90_days": max(0.0, forecast_90_days),
        "liquidity_gap_30_days": abs(min(0.0, forecast_30_days)),
        "liquidity_gap_90_days": abs(min(0.0, forecast_90_days))
    }

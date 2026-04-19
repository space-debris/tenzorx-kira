"""
KIRA — Peer Benchmarking Engine

Compares the assessed store's signals against area-type peer distributions
to produce a percentile ranking.  This answers: "How does this store compare
to a typical kirana in the same kind of neighbourhood?"

Owner: Orchestration Lead
Phase: Optional Extension

Design Decision:
    We use pre-calibrated distribution parameters (mean / std) per area type
    rather than querying a live database — this keeps the module stateless
    and deterministic while still producing defensible percentile ranks.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from models.output_schema import CVSignals, GeoSignals

logger = logging.getLogger("kira.peer_benchmark")


# ---------------------------------------------------------------------------
# Peer distribution parameters by area type (mean, std_dev)
# Based on RBI-published MSME data & FMCG channel research
# ---------------------------------------------------------------------------

PEER_DISTRIBUTIONS: dict[str, dict[str, tuple[float, float]]] = {
    "urban": {
        "shelf_density":      (0.65, 0.14),
        "sku_diversity_score": (0.60, 0.16),
        "footfall_score":     (0.68, 0.14),
        "competition_score":  (0.42, 0.18),
        "demand_index":       (0.55, 0.17),
    },
    "semi_urban": {
        "shelf_density":      (0.55, 0.17),
        "sku_diversity_score": (0.48, 0.18),
        "footfall_score":     (0.50, 0.17),
        "competition_score":  (0.56, 0.19),
        "demand_index":       (0.50, 0.18),
    },
    "rural": {
        "shelf_density":      (0.42, 0.18),
        "sku_diversity_score": (0.35, 0.17),
        "footfall_score":     (0.30, 0.17),
        "competition_score":  (0.68, 0.18),
        "demand_index":       (0.45, 0.20),
    },
}

# Revenue benchmarks per area type (median monthly, INR)
REVENUE_BENCHMARKS: dict[str, dict[str, float]] = {
    "urban":      {"p25": 120000, "p50": 220000, "p75": 380000},
    "semi_urban": {"p25":  80000, "p50": 150000, "p75": 260000},
    "rural":      {"p25":  45000, "p50":  90000, "p75": 170000},
}

# Human-friendly labels
SIGNAL_LABELS = {
    "shelf_density":       "Shelf Density",
    "sku_diversity_score": "SKU Diversity",
    "footfall_score":      "Footfall Potential",
    "competition_score":   "Competitive Position",
    "demand_index":        "Demand Index",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_peer_benchmark(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
    composite_score: float,
    monthly_revenue_low: float,
    monthly_revenue_high: float,
) -> dict[str, Any]:
    """
    Benchmark this store against peers in the same area type.

    For each signal, compute a percentile rank using the z-score against
    the area-type distribution, then convert to a cumulative normal %.

    Returns:
        dict with:
            - "area_type" (str): The peer group used.
            - "overall_percentile" (int): Weighted average percentile (0-100).
            - "signal_percentiles" (dict): Per-signal percentile breakdown.
            - "revenue_percentile" (int): Where estimated revenue falls vs peers.
            - "peer_summary" (str): One-sentence natural-language summary.
            - "strengths_vs_peers" (list[str]): Signals where store exceeds p75.
            - "weaknesses_vs_peers" (list[str]): Signals where store is below p25.
    """
    area_type = geo_signals.area_type.value
    distributions = PEER_DISTRIBUTIONS.get(area_type, PEER_DISTRIBUTIONS["semi_urban"])

    actual_signals = {
        "shelf_density":       cv_signals.shelf_density,
        "sku_diversity_score": cv_signals.sku_diversity_score,
        "footfall_score":      geo_signals.footfall_score,
        "competition_score":   geo_signals.competition_score,
        "demand_index":        geo_signals.demand_index,
    }

    signal_percentiles: dict[str, int] = {}
    strengths: list[str] = []
    weaknesses: list[str] = []

    for signal_name, actual_value in actual_signals.items():
        if signal_name not in distributions:
            continue
        mean, std = distributions[signal_name]
        percentile = _z_to_percentile(actual_value, mean, std)
        signal_percentiles[signal_name] = percentile

        label = SIGNAL_LABELS.get(signal_name, signal_name)
        if percentile >= 75:
            strengths.append(f"{label} is in the top quartile (P{percentile}) vs {area_type} peers")
        elif percentile <= 25:
            weaknesses.append(f"{label} is below the 25th percentile (P{percentile}) vs {area_type} peers")

    # Overall percentile (weighted average matching fusion weights)
    weights = {
        "shelf_density": 0.25,
        "sku_diversity_score": 0.20,
        "footfall_score": 0.20,
        "competition_score": 0.15,
        "demand_index": 0.20,
    }
    weighted_sum = 0.0
    total_weight = 0.0
    for sig, pct in signal_percentiles.items():
        w = weights.get(sig, 0.2)
        weighted_sum += pct * w
        total_weight += w
    overall_percentile = int(weighted_sum / total_weight) if total_weight > 0 else 50

    # Revenue percentile
    rev_midpoint = (monthly_revenue_low + monthly_revenue_high) / 2.0
    rev_bench = REVENUE_BENCHMARKS.get(area_type, REVENUE_BENCHMARKS["semi_urban"])
    revenue_percentile = _revenue_to_percentile(rev_midpoint, rev_bench)

    # Natural language summary
    if overall_percentile >= 75:
        tier = "top quartile"
    elif overall_percentile >= 50:
        tier = "above average"
    elif overall_percentile >= 25:
        tier = "below average"
    else:
        tier = "bottom quartile"

    peer_summary = (
        f"This store ranks in the {tier} (P{overall_percentile}) compared to "
        f"similar {area_type} kirana stores. Estimated revenue places it at the "
        f"P{revenue_percentile} level against {area_type} peer benchmarks."
    )

    result = {
        "area_type": area_type,
        "overall_percentile": overall_percentile,
        "signal_percentiles": signal_percentiles,
        "revenue_percentile": revenue_percentile,
        "peer_summary": peer_summary,
        "strengths_vs_peers": strengths,
        "weaknesses_vs_peers": weaknesses,
    }

    logger.info(
        f"Peer benchmark complete: overall=P{overall_percentile}, "
        f"revenue=P{revenue_percentile}, area={area_type}, "
        f"strengths={len(strengths)}, weaknesses={len(weaknesses)}"
    )

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _z_to_percentile(value: float, mean: float, std: float) -> int:
    """Convert a raw signal value to a percentile using the normal CDF."""
    if std <= 0:
        return 50
    z = (value - mean) / std
    # Approximate the standard normal CDF using the error function
    percentile = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(1, min(99, int(percentile * 100)))


def _revenue_to_percentile(
    midpoint: float,
    benchmarks: dict[str, float],
) -> int:
    """Map estimated revenue midpoint to a percentile using p25/p50/p75 benchmarks."""
    p25 = benchmarks["p25"]
    p50 = benchmarks["p50"]
    p75 = benchmarks["p75"]

    if midpoint <= p25:
        # Linear interpolation 0-25
        ratio = max(0.0, midpoint / p25) if p25 > 0 else 0.0
        return max(1, int(ratio * 25))
    elif midpoint <= p50:
        # Linear interpolation 25-50
        ratio = (midpoint - p25) / (p50 - p25) if (p50 - p25) > 0 else 0.5
        return 25 + int(ratio * 25)
    elif midpoint <= p75:
        # Linear interpolation 50-75
        ratio = (midpoint - p50) / (p75 - p50) if (p75 - p50) > 0 else 0.5
        return 50 + int(ratio * 25)
    else:
        # Above p75 — estimate 75-99
        overshoot = (midpoint - p75) / p75 if p75 > 0 else 0.0
        return min(99, 75 + int(overshoot * 24))

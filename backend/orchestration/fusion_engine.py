"""
KIRA — Fusion Engine

Combines CV (visual) and Geo (spatial) signals into a composite revenue
estimate and risk assessment using a calibrated weighted scoring model.

This is NOT a black-box ML model. It applies a transparent, configurable
weight matrix where each weight has an economic justification.

Owner: Orchestration Lead
Phase: 3.1

Economic Foundation:
    Revenue Score = w1 * shelf_density
                  + w2 * sku_diversity
                  + w3 * inventory_normalized
                  + w4 * footfall_score
                  + w5 * demand_index
                  - w6 * competition_penalty
"""

from __future__ import annotations

import logging
from typing import Any

from models.output_schema import (
    CVSignals,
    GeoSignals,
    RevenueEstimate,
    RiskAssessment,
    RiskBand,
)

logger = logging.getLogger("kira.fusion")

# ---------------------------------------------------------------------------
# Default Weight Configuration
# ---------------------------------------------------------------------------
# These weights are configurable per NBFC's risk appetite.
# Each weight has an economic justification documented in ARCHITECTURE.md.

DEFAULT_WEIGHTS = {
    "shelf_density": 0.25,       # Higher stock = more capital deployed
    "sku_diversity": 0.20,       # More categories = broader customer base
    "inventory_value": 0.20,     # Direct proxy for working capital
    "footfall_score": 0.15,      # More footfall = more daily transactions
    "demand_index": 0.10,        # More demand per store = better revenue potential
    "competition_penalty": 0.10, # More competitors = revenue split
}

# Revenue calibration table: maps composite score ranges to monthly revenue bands
# These are based on FMCG industry data for kirana store revenue distribution
REVENUE_CALIBRATION = {
    # (score_low, score_high): (monthly_revenue_low, monthly_revenue_high)
    (0.0, 0.2): (30000, 80000),       # Very small / poorly stocked
    (0.2, 0.4): (80000, 150000),      # Small but functional
    (0.4, 0.6): (150000, 300000),     # Medium, well-managed
    (0.6, 0.8): (300000, 500000),     # Large, well-stocked
    (0.8, 1.0): (500000, 1000000),    # Premium / high-traffic
}

# Area-type revenue multipliers — urban stores earn more than rural
AREA_REVENUE_MULTIPLIERS = {
    "urban": 1.2,
    "semi_urban": 1.0,
    "rural": 0.75,
}

# Risk band thresholds (based on inverse of composite score)
RISK_THRESHOLDS = {
    RiskBand.LOW: (0.6, 1.0),
    RiskBand.MEDIUM: (0.4, 0.6),
    RiskBand.HIGH: (0.2, 0.4),
    RiskBand.VERY_HIGH: (0.0, 0.2),
}

# Inventory value normalization bounds by area type (INR)
INVENTORY_NORM_BOUNDS = {
    "urban": {"min": 20000, "max": 800000},
    "semi_urban": {"min": 15000, "max": 500000},
    "rural": {"min": 10000, "max": 300000},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_fusion_engine(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Fuse CV and Geo signals into a composite revenue estimate and risk assessment.

    This function implements the core scoring logic of KIRA. It normalizes
    all input signals, applies a weighted scoring matrix, and maps the
    composite score to revenue ranges and risk bands.

    Args:
        cv_signals: Computer vision signals from the CV module.
        geo_signals: Geo intelligence signals from the Geo module.
        weights: Optional custom weight dict. If None, uses DEFAULT_WEIGHTS.

    Returns:
        dict containing:
            - "composite_score" (float): Overall score 0-1.
            - "revenue_estimate" (RevenueEstimate): Monthly revenue range.
            - "risk_assessment" (RiskAssessment): Risk band and score.
            - "signal_contributions" (dict): Per-signal weighted contribution.
    """
    active_weights = weights if weights is not None else DEFAULT_WEIGHTS

    # Validate weights sum to ~1.0 (allowing 5% tolerance)
    weight_sum = sum(active_weights.values())
    if abs(weight_sum - 1.0) > 0.05:
        logger.warning(
            f"Weights sum to {weight_sum:.3f}, expected ~1.0. "
            "Results may be miscalibrated."
        )

    area_type = geo_signals.area_type.value

    # Step 1: Normalize all signals to [0, 1]
    inventory_norm = _normalize_inventory_value(
        inventory_range={
            "low": cv_signals.inventory_value_range.low,
            "high": cv_signals.inventory_value_range.high,
        },
        area_type=area_type,
    )

    normalized_signals = {
        "shelf_density": cv_signals.shelf_density,
        "sku_diversity": cv_signals.sku_diversity_score,
        "inventory_value": inventory_norm,
        "footfall_score": geo_signals.footfall_score,
        "demand_index": geo_signals.demand_index,
        "competition_penalty": 1.0 - geo_signals.competition_score,  # Invert: higher competition = penalty
    }

    logger.info(f"Normalized signals: {normalized_signals}")

    # Step 2: Compute composite score
    composite_score, signal_contributions = _compute_composite_score(
        normalized_signals, active_weights
    )

    logger.info(f"Composite score: {composite_score:.4f}")
    logger.info(f"Signal contributions: {signal_contributions}")

    # Step 3: Map to revenue range
    monthly_low, monthly_high = _map_score_to_revenue(composite_score, area_type)

    # Step 4: Determine risk band
    risk_band = _determine_risk_band(composite_score)

    # Step 5: Compute confidence
    confidence = _compute_confidence(cv_signals, geo_signals)

    # Step 6: Compute risk score (inverse of composite — higher = riskier)
    risk_score = max(0.0, min(1.0, 1.0 - composite_score))

    # Build output objects
    revenue_estimate = RevenueEstimate(
        monthly_low=round(monthly_low, 2),
        monthly_high=round(monthly_high, 2),
        confidence=round(confidence, 4),
        methodology="inventory_turnover_model",
    )

    risk_assessment = RiskAssessment(
        risk_band=risk_band,
        risk_score=round(risk_score, 4),
        confidence=round(confidence, 4),
    )

    logger.info(
        f"Fusion complete: revenue=[₹{monthly_low:,.0f} - ₹{monthly_high:,.0f}], "
        f"risk_band={risk_band.value}, confidence={confidence:.2f}"
    )

    return {
        "composite_score": round(composite_score, 4),
        "revenue_estimate": revenue_estimate,
        "risk_assessment": risk_assessment,
        "signal_contributions": signal_contributions,
        "normalized_signals": normalized_signals,
    }


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _normalize_inventory_value(
    inventory_range: dict[str, float],
    area_type: str,
) -> float:
    """
    Normalize inventory value range to a 0-1 score.

    Uses area-type-specific scaling: urban stores typically have higher
    inventory values, so normalization accounts for this.

    Args:
        inventory_range: Dict with "low" and "high" keys (INR values).
        area_type: "urban", "semi_urban", or "rural".

    Returns:
        float: Normalized inventory score (0-1).
    """
    bounds = INVENTORY_NORM_BOUNDS.get(area_type, INVENTORY_NORM_BOUNDS["semi_urban"])
    norm_min = bounds["min"]
    norm_max = bounds["max"]

    # Use midpoint of the range as the representative value
    midpoint = (inventory_range.get("low", 0) + inventory_range.get("high", 0)) / 2.0

    if norm_max <= norm_min:
        return 0.5

    # Linear normalization clamped to [0, 1]
    normalized = (midpoint - norm_min) / (norm_max - norm_min)
    return max(0.0, min(1.0, normalized))


def _compute_composite_score(
    normalized_signals: dict[str, float],
    weights: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """
    Compute weighted composite score from normalized signals.

    Args:
        normalized_signals: Dict of signal_name → normalized_value (0-1).
        weights: Dict of signal_name → weight.

    Returns:
        tuple: (composite_score, signal_contributions_dict)
    """
    composite = 0.0
    contributions: dict[str, float] = {}

    for signal_name, weight in weights.items():
        signal_value = normalized_signals.get(signal_name, 0.0)

        # Competition penalty is subtracted, not added
        if signal_name == "competition_penalty":
            contribution = -(weight * signal_value)
        else:
            contribution = weight * signal_value

        contributions[signal_name] = round(contribution, 4)
        composite += contribution

    # Clamp to [0, 1]
    composite = max(0.0, min(1.0, composite))

    return composite, contributions


def _map_score_to_revenue(
    composite_score: float,
    area_type: str,
) -> tuple[float, float]:
    """
    Map a composite score to a monthly revenue range using the calibration table.

    Uses linear interpolation within bands for smoother estimates and applies
    area-type revenue multipliers.

    Args:
        composite_score: Overall score (0-1).
        area_type: Area classification for calibration adjustment.

    Returns:
        tuple: (monthly_low, monthly_high) in INR.
    """
    # Find the matching band
    matched_low = 30000
    matched_high = 80000
    band_start = 0.0
    band_end = 0.2

    for (score_lo, score_hi), (rev_lo, rev_hi) in REVENUE_CALIBRATION.items():
        if score_lo <= composite_score < score_hi:
            matched_low = rev_lo
            matched_high = rev_hi
            band_start = score_lo
            band_end = score_hi
            break
    else:
        # Score is exactly 1.0 — use the highest band
        if composite_score >= 0.8:
            matched_low = 500000
            matched_high = 1000000
            band_start = 0.8
            band_end = 1.0

    # Linear interpolation within the band for smoother estimates
    band_width = band_end - band_start
    if band_width > 0:
        position_in_band = (composite_score - band_start) / band_width
    else:
        position_in_band = 0.5

    # Interpolate revenue within band boundaries
    rev_range = matched_high - matched_low
    interpolated_low = matched_low + (position_in_band * rev_range * 0.3)
    interpolated_high = matched_low + (position_in_band * rev_range * 0.7) + (rev_range * 0.3)

    # Apply area-type multiplier
    multiplier = AREA_REVENUE_MULTIPLIERS.get(area_type, 1.0)
    final_low = interpolated_low * multiplier
    final_high = interpolated_high * multiplier

    return round(final_low, -2), round(final_high, -2)  # Round to nearest 100


def _determine_risk_band(composite_score: float) -> RiskBand:
    """
    Map composite score to risk band.

    Lower composite scores → higher risk (inverse relationship).

    Args:
        composite_score: Overall score (0-1).

    Returns:
        RiskBand: LOW, MEDIUM, HIGH, or VERY_HIGH.
    """
    for risk_band, (threshold_low, threshold_high) in RISK_THRESHOLDS.items():
        if threshold_low <= composite_score < threshold_high:
            return risk_band

    # Edge case: score is exactly 1.0
    if composite_score >= 1.0:
        return RiskBand.LOW

    return RiskBand.VERY_HIGH


def _compute_confidence(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
) -> float:
    """
    Compute overall confidence score for the assessment.

    Confidence degrades when:
    - Image consistency is low (possible fraud)
    - CV and Geo signals conflict (e.g., high visual score but low geo score)

    Args:
        cv_signals: CV module outputs.
        geo_signals: Geo module outputs.

    Returns:
        float: Confidence score (0-1).
    """
    # Base confidence starts at 1.0 and is degraded by issues
    confidence = 1.0

    # Factor 1: Image consistency (weight: 40%)
    # consistency_score < 0.7 starts degrading confidence
    consistency_factor = min(1.0, cv_signals.consistency_score / 0.7)
    confidence *= (0.6 + 0.4 * consistency_factor)

    # Factor 2: Signal conflict detection (weight: 30%)
    # Measure divergence between CV quality and Geo quality
    cv_avg = (cv_signals.shelf_density + cv_signals.sku_diversity_score) / 2.0
    geo_avg = (geo_signals.footfall_score + geo_signals.demand_index) / 2.0
    signal_divergence = abs(cv_avg - geo_avg)

    # High divergence (>0.4) degrades confidence
    if signal_divergence > 0.4:
        conflict_penalty = (signal_divergence - 0.4) / 0.6  # 0 at 0.4, 1 at 1.0
        confidence *= (1.0 - 0.3 * conflict_penalty)

    # Factor 3: Data completeness (weight: 30%)
    # Penalize if key signals are at extreme defaults (likely missing data)
    extreme_count = 0
    all_signals = [
        cv_signals.shelf_density,
        cv_signals.sku_diversity_score,
        geo_signals.footfall_score,
        geo_signals.competition_score,
        geo_signals.demand_index,
    ]
    for sig in all_signals:
        if sig <= 0.01 or sig >= 0.99:
            extreme_count += 1

    if extreme_count > 0:
        completeness_penalty = extreme_count / len(all_signals)
        confidence *= (1.0 - 0.3 * completeness_penalty)

    return max(0.1, min(1.0, round(confidence, 4)))

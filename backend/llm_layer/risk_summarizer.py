"""
KIRA — Risk Summarizer

Generates structured summaries (strengths, concerns, recommendation)
from the complete assessment output. Unlike the narrative explainer,
this module produces machine-readable structured data suitable for
dashboards and decision systems.

Owner: Orchestration Lead
Phase: 4.2
"""

from __future__ import annotations

import logging
from typing import Any

from models.output_schema import ExplanationSummary

logger = logging.getLogger("kira.llm.summarizer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Signal thresholds for strengths/concerns classification
STRENGTH_THRESHOLD = 0.7   # Signals above this are strengths
CONCERN_THRESHOLD = 0.4    # Signals below this are concerns

# Signal display names for human-readable summaries
SIGNAL_DISPLAY_NAMES = {
    "shelf_density": "Shelf occupancy",
    "sku_diversity_score": "Product diversity",
    "inventory_value": "Inventory value",
    "consistency_score": "Image consistency",
    "footfall_score": "Footfall potential",
    "competition_score": "Competition level",
    "demand_index": "Local demand",
}

# Strength description templates
STRENGTH_DESCRIPTIONS = {
    "shelf_density": "Well-stocked shelves ({score:.0%}) indicate active inventory management",
    "sku_diversity_score": "Strong product diversity ({score:.0%}) suggests broad customer appeal",
    "inventory_value": "Healthy inventory investment reflects business commitment",
    "consistency_score": "High image consistency ({score:.0%}) confirms authentic documentation",
    "footfall_score": "Excellent location with strong footfall potential ({score:.0%})",
    "competition_score": "Favorable competitive position with manageable competition ({score:.0%})",
    "demand_index": "Strong local demand ({score:.0%}) indicates robust customer base",
}

# Concern description templates
CONCERN_DESCRIPTIONS = {
    "shelf_density": "Low shelf occupancy ({score:.0%}) may indicate stock or capital issues",
    "sku_diversity_score": "Limited product range ({score:.0%}) restricts revenue potential",
    "inventory_value": "Low inventory investment raises concerns about business viability",
    "consistency_score": "Low image consistency ({score:.0%}) raises documentation concerns",
    "footfall_score": "Weak footfall potential ({score:.0%}) limits customer acquisition",
    "competition_score": "High competition density ({score:.0%}) pressures margins",
    "demand_index": "Low local demand ({score:.0%}) constrains revenue growth",
}

# Recommendation thresholds based on risk band
RECOMMENDATION_MAP = {
    "LOW": "Approve with standard terms",
    "MEDIUM": "Approve with enhanced monitoring",
    "HIGH": "Refer for detailed manual review",
    "VERY_HIGH": "Decline — high risk indicators",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_risk_summary(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any],
) -> ExplanationSummary:
    """
    Generate a structured summary with strengths, concerns, and recommendation.

    Analyzes all signal values to identify the top positive and negative
    factors, then generates a recommendation based on the risk band
    and fraud detection results.

    Args:
        cv_signals: CV module output with all visual signals.
        geo_signals: Geo module output with all spatial signals.
        fusion_result: Fusion output with risk_band, risk_score.
        fraud_detection: Fraud output with is_flagged, flags.

    Returns:
        ExplanationSummary: Structured summary with strengths, concerns,
        and recommendation.
    """
    # Collect all signals into a flat dict for analysis
    all_signals = _collect_signals(cv_signals, geo_signals)

    # Extract fraud flags
    if hasattr(fraud_detection, "flags"):
        fraud_flags = fraud_detection.flags
        is_flagged = fraud_detection.is_flagged
    else:
        fraud_flags = fraud_detection.get("flags", [])
        is_flagged = fraud_detection.get("is_flagged", False)

    # Extract risk band
    risk_assessment = fusion_result.get("risk_assessment", {})
    if hasattr(risk_assessment, "risk_band"):
        risk_band = risk_assessment.risk_band.value
    else:
        risk_band = risk_assessment.get("risk_band", "MEDIUM")
        if hasattr(risk_band, "value"):
            risk_band = risk_band.value

    # Identify strengths and concerns
    strengths = _identify_strengths(all_signals, top_n=3)
    concerns = _identify_concerns(all_signals, fraud_flags, top_n=3)

    # Determine recommendation
    recommendation = _determine_recommendation(risk_band, is_flagged)

    logger.info(
        f"Risk summary: {len(strengths)} strengths, "
        f"{len(concerns)} concerns, recommendation={recommendation}"
    )

    return ExplanationSummary(
        strengths=strengths,
        concerns=concerns,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _collect_signals(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
) -> dict[str, float]:
    """
    Collect all relevant signals into a flat dict for analysis.

    Handles both dict and Pydantic model inputs.
    """
    signals: dict[str, float] = {}

    # CV signals
    for key in ["shelf_density", "sku_diversity_score", "consistency_score"]:
        if hasattr(cv_signals, key):
            signals[key] = getattr(cv_signals, key)
        elif isinstance(cv_signals, dict) and key in cv_signals:
            signals[key] = float(cv_signals[key])

    # Inventory value — normalize to 0-1 for comparison
    if hasattr(cv_signals, "inventory_value_range"):
        inv = cv_signals.inventory_value_range
        midpoint = (inv.low + inv.high) / 2.0
        signals["inventory_value"] = min(1.0, midpoint / 500000)  # Normalize against 5L
    elif isinstance(cv_signals, dict) and "inventory_value_range" in cv_signals:
        inv = cv_signals["inventory_value_range"]
        if hasattr(inv, "low"):
            midpoint = (inv.low + inv.high) / 2.0
        else:
            midpoint = (inv.get("low", 0) + inv.get("high", 0)) / 2.0
        signals["inventory_value"] = min(1.0, midpoint / 500000)

    # Geo signals
    for key in ["footfall_score", "competition_score", "demand_index"]:
        if hasattr(geo_signals, key):
            signals[key] = getattr(geo_signals, key)
        elif isinstance(geo_signals, dict) and key in geo_signals:
            signals[key] = float(geo_signals[key])

    return signals


def _identify_strengths(
    signals: dict[str, float],
    top_n: int = 3,
) -> list[str]:
    """
    Identify top N strengths from signal values.

    Filters signals above STRENGTH_THRESHOLD, sorts descending,
    and generates human-readable descriptions.
    """
    strengths: list[tuple[float, str]] = []

    for signal_name, score in signals.items():
        if score >= STRENGTH_THRESHOLD and signal_name in STRENGTH_DESCRIPTIONS:
            description = STRENGTH_DESCRIPTIONS[signal_name].format(score=score)
            strengths.append((score, description))

    # Sort by score descending and take top N
    strengths.sort(key=lambda x: x[0], reverse=True)
    result = [desc for _, desc in strengths[:top_n]]

    # If no signals above threshold, find the best ones
    if not result:
        best = sorted(
            signals.items(), key=lambda x: x[1], reverse=True
        )
        for signal_name, score in best[:top_n]:
            if signal_name in SIGNAL_DISPLAY_NAMES:
                display_name = SIGNAL_DISPLAY_NAMES[signal_name]
                result.append(
                    f"{display_name} at {score:.0%} — "
                    "above average for this segment"
                )

    return result


def _identify_concerns(
    signals: dict[str, float],
    fraud_flags: list[str],
    top_n: int = 3,
) -> list[str]:
    """
    Identify top N concerns from signal values and fraud flags.

    Filters signals below CONCERN_THRESHOLD, includes fraud flags,
    sorts ascending (worst first), and generates descriptions.
    """
    concerns: list[tuple[float, str]] = []

    for signal_name, score in signals.items():
        if score < CONCERN_THRESHOLD and signal_name in CONCERN_DESCRIPTIONS:
            description = CONCERN_DESCRIPTIONS[signal_name].format(score=score)
            # Lower scores get higher priority (lower value = more concerning)
            concerns.append((score, description))

    # Add fraud flags as high-priority concerns
    for flag in fraud_flags[:2]:
        concerns.append((0.0, f"Fraud alert: {flag}"))

    # Sort by score ascending (worst first) and take top N
    concerns.sort(key=lambda x: x[0])
    result = [desc for _, desc in concerns[:top_n]]

    # If no concerns found, provide a neutral message
    if not result:
        result.append("No significant concerns identified in this assessment")

    return result


def _determine_recommendation(
    risk_band: str,
    is_fraud_flagged: bool,
) -> str:
    """
    Generate recommendation based on risk band and fraud status.

    Fraud flagged always overrides to manual review regardless of risk band.
    """
    if is_fraud_flagged:
        return (
            "Hold for manual review — assessment flagged for potential "
            "inconsistencies requiring human verification"
        )

    recommendation = RECOMMENDATION_MAP.get(
        risk_band,
        "Refer for manual review"
    )

    return recommendation

"""
KIRA — Shelf Density Analyzer

Extracts shelf occupancy metrics from Gemini Vision analysis results.
Produces a normalized shelf density score (0-1) that serves as a proxy
for inventory volume and store management quality.

Owner: Analytics & CV Lead
Phase: 1.2 (P0)

Economic Significance:
    Shelf density directly correlates with working capital deployed.
    A store with 90% shelf occupancy has demonstrably more inventory
    (and thus more capital at risk) than one with 40% occupancy.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kira.cv.shelf_density")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Scoring parameters
OPTIMAL_OCCUPANCY = 85  # Ideal occupancy %; above this may indicate overstocking
MIN_VIABLE_OCCUPANCY = 30  # Below this, store is critically understocked

# Empty shelf penalty — each empty shelf area reduces score
EMPTY_SHELF_PENALTY = 0.05

# Organization adjustment multipliers
ORGANIZATION_MULTIPLIERS = {
    "well_organized": 1.10,   # +10% — well-managed store signal
    "average": 1.00,           # No adjustment
    "disorganized": 0.90,      # -10% — poor management signal
}

# Overstocking threshold — above this, slight penalty (possible staging)
OVERSTOCKING_THRESHOLD = 95


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_shelf_density(
    image_analysis: dict[str, Any],
) -> dict[str, float]:
    """
    Compute shelf density score from image analysis features.

    Takes the raw shelf occupancy percentage from Gemini Vision analysis
    and produces a normalized score factoring in occupancy quality,
    empty shelf patterns, and stacking efficiency.

    Args:
        image_analysis: Aggregated image analysis dict from image_analyzer.py.
            Expected keys:
                - "shelf_occupancy" (float): 0-100 percentage
                - "empty_shelf_areas" (int): Count of visibly empty zones
                - "organization_level" (str): "disorganized"|"average"|"well_organized"

    Returns:
        dict containing:
            - "shelf_density_score" (float): Normalized score 0-1.
                Higher = more/better stocked.
            - "empty_shelf_ratio" (float): Proportion of empty shelf areas.
            - "occupancy_raw" (float): Raw occupancy percentage 0-100.
            - "quality_adjustment" (float): Organization-based adjustment factor.
    """
    # Extract raw values with safe defaults
    occupancy_raw = float(image_analysis.get("shelf_occupancy", 50.0))
    empty_shelf_areas = int(image_analysis.get("empty_shelf_areas", 0))
    organization_level = image_analysis.get("organization_level", "average")

    logger.info(
        f"Computing shelf density: occupancy={occupancy_raw}%, "
        f"empty_areas={empty_shelf_areas}, org={organization_level}"
    )

    # Step 1: Normalize raw occupancy to 0-1 scale
    normalized_score = _normalize_occupancy(occupancy_raw)

    # Step 2: Apply empty shelf penalty
    # Each empty shelf area reduces the score, capped at 50% reduction
    empty_penalty = min(empty_shelf_areas * EMPTY_SHELF_PENALTY, 0.50)
    score_after_penalty = normalized_score * (1.0 - empty_penalty)

    # Step 3: Compute empty shelf ratio
    # Approximate: empty areas relative to total possible areas
    # A typical small store has ~10-20 shelf sections
    estimated_total_sections = max(
        int(occupancy_raw / 10) + empty_shelf_areas, 1
    )
    empty_shelf_ratio = empty_shelf_areas / estimated_total_sections

    # Step 4: Apply organization quality adjustment
    quality_adjustment = ORGANIZATION_MULTIPLIERS.get(organization_level, 1.0)
    final_score = _apply_organization_adjustment(score_after_penalty, organization_level)

    # Step 5: Clamp to [0, 1]
    final_score = max(0.0, min(1.0, final_score))

    result = {
        "shelf_density_score": round(final_score, 4),
        "empty_shelf_ratio": round(empty_shelf_ratio, 4),
        "occupancy_raw": round(occupancy_raw, 2),
        "quality_adjustment": quality_adjustment,
    }

    logger.info(f"Shelf density result: {result}")
    return result


def _normalize_occupancy(occupancy_percent: float) -> float:
    """
    Normalize raw occupancy percentage to a 0-1 score.

    Uses a piecewise function:
        - 0-30%: Score 0 (critically low)
        - 30-85%: Linear scale 0 to 1
        - 85-95%: Score 1.0 (optimal)
        - 95-100%: Slight penalty (possible staging)

    Args:
        occupancy_percent: Raw shelf occupancy (0-100).

    Returns:
        float: Normalized score (0-1).
    """
    # Clamp input to valid range
    occupancy = max(0.0, min(100.0, occupancy_percent))

    if occupancy < MIN_VIABLE_OCCUPANCY:
        # 0-30%: Critically low — linear from 0 to 0
        # Give a small score for any non-zero occupancy
        return occupancy / MIN_VIABLE_OCCUPANCY * 0.1

    elif occupancy <= OPTIMAL_OCCUPANCY:
        # 30-85%: Linear scale from 0.1 to 1.0
        ratio = (occupancy - MIN_VIABLE_OCCUPANCY) / (
            OPTIMAL_OCCUPANCY - MIN_VIABLE_OCCUPANCY
        )
        return 0.1 + ratio * 0.9

    elif occupancy <= OVERSTOCKING_THRESHOLD:
        # 85-95%: Optimal — score is 1.0
        return 1.0

    else:
        # 95-100%: Possible staging — slight linear penalty
        # Score goes from 1.0 at 95% down to 0.9 at 100%
        overage = (occupancy - OVERSTOCKING_THRESHOLD) / (
            100.0 - OVERSTOCKING_THRESHOLD
        )
        return 1.0 - (overage * 0.1)


def _apply_organization_adjustment(
    base_score: float,
    organization_level: str,
) -> float:
    """
    Adjust shelf density score based on organization quality.

    A well-organized store with moderate stock may be better managed
    (and thus more creditworthy) than a chaotic store with full shelves.

    Args:
        base_score: Pre-adjustment shelf density score.
        organization_level: "disorganized", "average", or "well_organized".

    Returns:
        float: Adjusted score.
    """
    multiplier = ORGANIZATION_MULTIPLIERS.get(organization_level, 1.0)

    adjusted = base_score * multiplier

    # Log the adjustment impact
    if multiplier != 1.0:
        logger.debug(
            f"Organization adjustment: {organization_level} "
            f"({multiplier}x) — {base_score:.3f} → {adjusted:.3f}"
        )

    return adjusted

"""
KIRA — Fraud Detector

Cross-signal fraud and adversarial input detection module.
Implements four independent fraud checks that together provide
multi-dimensional validation of assessment inputs.

Owner: Orchestration Lead
Phase: 3.2

Fraud Checks:
    1. Image Consistency — cross-image feature validation
    2. GPS-Visual Mismatch — location vs store profile mismatch
    3. Signal Cross-Validation — implausible signal combinations
    4. Statistical Outlier — deviation from area-type distributions
"""

from __future__ import annotations

import logging
import math
from typing import Any

from models.output_schema import CVSignals, FraudDetection, GeoSignals

logger = logging.getLogger("kira.fraud")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Fraud score threshold — above this, assessment is flagged for manual review
FRAUD_THRESHOLD = 0.5

# Weights for combining individual check scores into aggregate fraud score
CHECK_WEIGHTS = {
    "image_consistency": 0.30,
    "gps_visual_mismatch": 0.25,
    "signal_cross_validation": 0.25,
    "statistical_outlier": 0.20,
}

# Known adversarial patterns
ADVERSARIAL_PATTERNS = {
    "high_stock_low_footfall": {
        "description": "Premium inventory in low-demand area",
        "cv_threshold": {"shelf_density": 0.8, "sku_diversity_score": 0.7},
        "geo_threshold": {"footfall_score": 0.3, "demand_index": 0.25},
    },
    "luxury_in_rural": {
        "description": "Premium brand mix in rural/low-income location",
        "cv_threshold": {"brand_tier_mix": "premium_dominant"},
        "geo_threshold": {"area_type": "rural"},
    },
}

# Expected signal distributions per area type (mean, std_dev)
# Used by the statistical outlier check
AREA_DISTRIBUTIONS = {
    "urban": {
        "shelf_density": (0.65, 0.15),
        "sku_diversity_score": (0.60, 0.18),
        "footfall_score": (0.70, 0.15),
        "competition_score": (0.40, 0.20),
        "demand_index": (0.55, 0.18),
    },
    "semi_urban": {
        "shelf_density": (0.55, 0.18),
        "sku_diversity_score": (0.50, 0.20),
        "footfall_score": (0.50, 0.18),
        "competition_score": (0.55, 0.20),
        "demand_index": (0.50, 0.20),
    },
    "rural": {
        "shelf_density": (0.40, 0.20),
        "sku_diversity_score": (0.35, 0.18),
        "footfall_score": (0.30, 0.18),
        "competition_score": (0.70, 0.20),
        "demand_index": (0.45, 0.22),
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_fraud_detection(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
    fusion_result: dict[str, Any],
    image_metadata: dict[str, Any] | None = None,
) -> FraudDetection:
    """
    Run all fraud detection checks on an assessment.

    Executes four independent checks, computes weighted aggregate fraud score,
    and returns detailed results including specific flags.

    Args:
        cv_signals: Computer vision signals including consistency_score.
        geo_signals: Geo intelligence signals including area_type.
        fusion_result: Output from the fusion engine (composite score, etc.).
        image_metadata: Optional image metadata (EXIF, file properties).

    Returns:
        FraudDetection: Aggregate fraud score, is_flagged boolean,
        list of specific flags, and list of checks performed.
    """
    all_flags: list[str] = []
    check_scores: dict[str, float] = {}
    checks_performed: list[str] = []

    # Check 1: Image consistency
    score_1, flags_1 = await _check_image_consistency(cv_signals, image_metadata)
    check_scores["image_consistency"] = score_1
    all_flags.extend(flags_1)
    checks_performed.append("image_consistency")
    logger.info(f"Image consistency check: score={score_1:.3f}, flags={flags_1}")

    # Check 2: GPS-Visual mismatch
    score_2, flags_2 = await _check_gps_visual_mismatch(cv_signals, geo_signals)
    check_scores["gps_visual_mismatch"] = score_2
    all_flags.extend(flags_2)
    checks_performed.append("gps_visual_mismatch")
    logger.info(f"GPS-visual mismatch check: score={score_2:.3f}, flags={flags_2}")

    # Check 3: Signal cross-validation
    score_3, flags_3 = await _check_signal_cross_validation(cv_signals, geo_signals)
    check_scores["signal_cross_validation"] = score_3
    all_flags.extend(flags_3)
    checks_performed.append("signal_cross_validation")
    logger.info(f"Signal cross-validation check: score={score_3:.3f}, flags={flags_3}")

    # Check 4: Statistical outlier
    score_4, flags_4 = await _check_statistical_outlier(cv_signals, geo_signals)
    check_scores["statistical_outlier"] = score_4
    all_flags.extend(flags_4)
    checks_performed.append("statistical_outlier")
    logger.info(f"Statistical outlier check: score={score_4:.3f}, flags={flags_4}")

    # Compute weighted aggregate fraud score
    aggregate_score = sum(
        CHECK_WEIGHTS[check_name] * score
        for check_name, score in check_scores.items()
    )
    aggregate_score = max(0.0, min(1.0, aggregate_score))

    is_flagged = aggregate_score > FRAUD_THRESHOLD

    logger.info(
        f"Fraud detection complete: aggregate_score={aggregate_score:.3f}, "
        f"is_flagged={is_flagged}, total_flags={len(all_flags)}"
    )

    return FraudDetection(
        fraud_score=round(aggregate_score, 4),
        is_flagged=is_flagged,
        flags=all_flags,
        checks_performed=checks_performed,
    )


# ---------------------------------------------------------------------------
# Individual Fraud Checks
# ---------------------------------------------------------------------------

async def _check_image_consistency(
    cv_signals: CVSignals,
    image_metadata: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    """
    Check consistency across multiple submitted images.

    Leverages the consistency_score from cv_module/consistency_checker.py
    and adds additional metadata-based checks.

    Returns:
        tuple: (fraud_score_component 0-1, list_of_flags)
    """
    flags: list[str] = []
    score = 0.0

    # Primary check: consistency_score from CV module
    consistency = cv_signals.consistency_score

    if consistency < 0.4:
        score += 0.7
        flags.append(
            f"Very low image consistency ({consistency:.2f}): "
            "images may not be from the same store"
        )
    elif consistency < 0.6:
        score += 0.4
        flags.append(
            f"Low image consistency ({consistency:.2f}): "
            "possible mismatched or reused images"
        )
    elif consistency < 0.7:
        score += 0.15
        # Mild concern, no flag

    # Metadata-based checks (if available)
    if image_metadata:
        # Check for duplicate image hashes
        hashes = image_metadata.get("file_hashes", [])
        if hashes and len(hashes) != len(set(hashes)):
            score += 0.3
            flags.append("Duplicate images detected: identical file hashes found")

        # Check for mismatched resolutions
        resolutions = image_metadata.get("resolutions", [])
        if resolutions and len(set(resolutions)) > 2:
            score += 0.1
            flags.append(
                "Mismatched image resolutions: images from different devices"
            )

        # Check for suspicious timestamps
        timestamps = image_metadata.get("timestamps", [])
        if timestamps and len(timestamps) >= 2:
            # If timestamps span > 7 days, suspicious
            valid_ts = [t for t in timestamps if t is not None]
            if len(valid_ts) >= 2:
                ts_sorted = sorted(valid_ts)
                span_seconds = (ts_sorted[-1] - ts_sorted[0]).total_seconds()
                if span_seconds > 7 * 86400:
                    score += 0.2
                    flags.append(
                        "Image timestamps span more than 7 days: possibly collected from different visits"
                    )

    return min(1.0, score), flags


async def _check_gps_visual_mismatch(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
) -> tuple[float, list[str]]:
    """
    Detect mismatch between visual store profile and GPS location profile.

    A premium-looking store in a rural area, or a very large store in a
    residential zone, suggests GPS spoofing or borrowed images.

    Returns:
        tuple: (fraud_score_component 0-1, list_of_flags)
    """
    flags: list[str] = []
    score = 0.0
    area_type = geo_signals.area_type.value

    # Pattern 1: Premium brand mix in rural area
    if (
        cv_signals.brand_tier_mix.value == "premium_dominant"
        and area_type == "rural"
    ):
        score += 0.5
        flags.append(
            "GPS-visual mismatch: premium brand inventory detected in rural area"
        )

    # Pattern 2: Large store in low-footfall area
    if (
        cv_signals.store_size_category.value == "large"
        and geo_signals.footfall_score < 0.25
    ):
        score += 0.35
        flags.append(
            "GPS-visual mismatch: large store detected in very low footfall area"
        )

    # Pattern 3: High inventory value in rural with low demand
    inv_midpoint = (
        cv_signals.inventory_value_range.low
        + cv_signals.inventory_value_range.high
    ) / 2.0
    if area_type == "rural" and inv_midpoint > 400000:
        score += 0.3
        flags.append(
            f"GPS-visual mismatch: high inventory value (₹{inv_midpoint:,.0f}) "
            "in rural location"
        )

    # Pattern 4: Well-organized premium store in semi-urban with no competition
    if (
        cv_signals.brand_tier_mix.value == "premium_dominant"
        and area_type == "semi_urban"
        and geo_signals.competition_count == 0
    ):
        score += 0.2
        flags.append(
            "GPS-visual mismatch: premium store with zero nearby competition"
        )

    return min(1.0, score), flags


async def _check_signal_cross_validation(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
) -> tuple[float, list[str]]:
    """
    Detect implausible signal combinations across CV and Geo.

    Certain signal combinations are economically impossible or highly unlikely.

    Returns:
        tuple: (fraud_score_component 0-1, list_of_flags)
    """
    flags: list[str] = []
    score = 0.0

    # Pattern 1: Very high shelf density + very low demand area
    if cv_signals.shelf_density > 0.8 and geo_signals.demand_index < 0.2:
        score += 0.4
        flags.append(
            "Cross-validation: overstocked shelves in low-demand area "
            f"(shelf={cv_signals.shelf_density:.2f}, demand={geo_signals.demand_index:.2f})"
        )

    # Pattern 2: High inventory + low footfall
    inv_midpoint = (
        cv_signals.inventory_value_range.low
        + cv_signals.inventory_value_range.high
    ) / 2.0
    if inv_midpoint > 300000 and geo_signals.footfall_score < 0.2:
        score += 0.35
        flags.append(
            f"Cross-validation: high inventory (₹{inv_midpoint:,.0f}) "
            f"in very low footfall area ({geo_signals.footfall_score:.2f})"
        )

    # Pattern 3: Premium brand tier + very low catchment
    if (
        cv_signals.brand_tier_mix.value == "premium_dominant"
        and geo_signals.catchment_population < 2000
    ):
        score += 0.3
        flags.append(
            "Cross-validation: premium brand inventory with very small "
            f"catchment population ({geo_signals.catchment_population})"
        )

    # Pattern 4: High SKU diversity + tiny store
    if (
        cv_signals.sku_diversity_score > 0.8
        and cv_signals.store_size_category.value == "small"
    ):
        score += 0.2
        flags.append(
            "Cross-validation: unusually high SKU diversity for small store size"
        )

    # Pattern 5: Very high store quality but very high competition (unusual)
    if (
        cv_signals.shelf_density > 0.85
        and cv_signals.sku_diversity_score > 0.8
        and geo_signals.competition_score < 0.15
    ):
        score += 0.15
        flags.append(
            "Cross-validation: exceptionally stocked store in saturated market"
        )

    return min(1.0, score), flags


async def _check_statistical_outlier(
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
) -> tuple[float, list[str]]:
    """
    Detect statistical outliers relative to area-type distributions.

    Compares individual signal values against the expected distribution
    for stores in similar area types.

    Returns:
        tuple: (fraud_score_component 0-1, list_of_flags)
    """
    flags: list[str] = []
    area_type = geo_signals.area_type.value

    distributions = AREA_DISTRIBUTIONS.get(
        area_type, AREA_DISTRIBUTIONS["semi_urban"]
    )

    # Collect actual signal values
    actual_signals = {
        "shelf_density": cv_signals.shelf_density,
        "sku_diversity_score": cv_signals.sku_diversity_score,
        "footfall_score": geo_signals.footfall_score,
        "competition_score": geo_signals.competition_score,
        "demand_index": geo_signals.demand_index,
    }

    # Compute z-scores and check for outliers
    z_scores: dict[str, float] = {}
    outlier_count = 0

    for signal_name, actual_value in actual_signals.items():
        if signal_name not in distributions:
            continue

        mean, std_dev = distributions[signal_name]
        if std_dev <= 0:
            continue

        z = abs(actual_value - mean) / std_dev
        z_scores[signal_name] = z

        if z > 3.0:
            outlier_count += 1
            flags.append(
                f"Statistical outlier: {signal_name}={actual_value:.2f} "
                f"is {z:.1f}σ from {area_type} mean ({mean:.2f}±{std_dev:.2f})"
            )
        elif z > 2.5:
            outlier_count += 0.5

    # Compute Mahalanobis-like aggregate distance
    if z_scores:
        rms_z = math.sqrt(
            sum(z ** 2 for z in z_scores.values()) / len(z_scores)
        )
    else:
        rms_z = 0.0

    # Map RMS z-score to fraud score component
    # RMS z > 2.0 is suspicious, > 3.0 is very suspicious
    if rms_z > 3.0:
        score = 0.8
    elif rms_z > 2.5:
        score = 0.5
    elif rms_z > 2.0:
        score = 0.3
    elif rms_z > 1.5:
        score = 0.1
    else:
        score = 0.0

    # Bonus penalty for multiple individual outliers
    if outlier_count >= 3:
        score = min(1.0, score + 0.2)
        flags.append(
            f"Multiple statistical outliers detected ({int(outlier_count)} signals)"
        )

    return min(1.0, score), flags

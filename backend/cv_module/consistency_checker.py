"""
KIRA — Multi-Image Consistency Checker

Cross-validates features extracted from multiple images of the same store
to detect staging, fraud, or image reuse. The consistency score acts as
a confidence multiplier on the overall assessment.

Owner: Analytics & CV Lead
Phase: 1.5 (P1)

Fraud Detection Role:
    This module is the first line of defense against adversarial inputs.
    If someone submits images from different stores, stock photos, or
    digitally manipulated images, the consistency checker should flag it.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kira.cv.consistency_checker")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Consistency thresholds
HIGH_CONSISTENCY_THRESHOLD = 0.8   # Above this = reliable
LOW_CONSISTENCY_THRESHOLD = 0.5    # Below this = suspicious
FRAUD_THRESHOLD = 0.3              # Below this = likely fraudulent

# Feature comparison weights
FEATURE_WEIGHTS = {
    "store_size": 0.20,         # Store size should be consistent
    "organization_level": 0.15, # Organization shouldn't vary wildly
    "brand_tier": 0.15,         # Brand mix should be consistent
    "product_overlap": 0.25,    # Product categories should overlap
    "lighting": 0.10,           # Lighting should be consistent (same visit)
    "image_quality": 0.15,      # Image quality should be similar (same device)
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_consistency(
    raw_analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Cross-validate features across multiple images for internal consistency.

    Compares key features between all image pairs to detect mismatches
    that suggest images are from different stores or have been manipulated.

    Args:
        raw_analyses: List of per-image analysis dicts from image_analyzer.py.
            Each dict should have keys: store_size, organization_level,
            brand_tier, product_categories (or visible_product_categories),
            lighting_quality, image_quality_score.

    Returns:
        dict containing:
            - "consistency_score" (float): Overall consistency 0-1.
                Higher = more consistent (trustworthy).
            - "fraud_flags" (list[str]): Specific inconsistencies detected.
            - "pairwise_scores" (list[dict]): Per-pair comparison scores.
            - "feature_variances" (dict): Per-feature variance across images.
            - "is_suspicious" (bool): True if score < LOW_CONSISTENCY_THRESHOLD.
    """
    fraud_flags: list[str] = []

    # Handle edge cases
    if not raw_analyses:
        return {
            "consistency_score": 0.0,
            "fraud_flags": ["no_images_provided"],
            "pairwise_scores": [],
            "feature_variances": {},
            "is_suspicious": True,
        }

    if len(raw_analyses) == 1:
        # Can't check consistency with a single image
        stock_flags = _detect_stock_photos(raw_analyses)
        fraud_flags.extend(stock_flags)
        return {
            "consistency_score": 0.6,  # Moderate — can't verify with one image
            "fraud_flags": fraud_flags or ["single_image_unverifiable"],
            "pairwise_scores": [],
            "feature_variances": {},
            "is_suspicious": len(fraud_flags) > 0,
        }

    logger.info(
        f"Checking consistency across {len(raw_analyses)} images"
    )

    # Step 1: Pairwise comparison
    pairwise_scores: list[dict[str, Any]] = []
    all_pair_scores: list[float] = []

    for i in range(len(raw_analyses)):
        for j in range(i + 1, len(raw_analyses)):
            score, mismatches = _compare_pair(raw_analyses[i], raw_analyses[j])
            pair_result = {
                "image_a": i,
                "image_b": j,
                "similarity_score": round(score, 4),
                "mismatches": mismatches,
            }
            pairwise_scores.append(pair_result)
            all_pair_scores.append(score)
            fraud_flags.extend(mismatches)

    # Step 2: Compute aggregate consistency score
    if all_pair_scores:
        consistency_score = sum(all_pair_scores) / len(all_pair_scores)
    else:
        consistency_score = 0.5

    # Step 3: Compute per-feature variance across all images
    feature_variances = _compute_feature_variances(raw_analyses)

    # Step 4: Check for stock photos
    stock_photo_flags = _detect_stock_photos(raw_analyses)
    fraud_flags.extend(stock_photo_flags)

    # Step 5: Apply stock photo penalty to consistency score
    if stock_photo_flags:
        consistency_score *= 0.8  # Penalty for stock photo indicators

    # Clamp to [0, 1]
    consistency_score = max(0.0, min(1.0, consistency_score))

    # Deduplicate fraud flags
    fraud_flags = list(dict.fromkeys(fraud_flags))

    is_suspicious = consistency_score < LOW_CONSISTENCY_THRESHOLD

    result = {
        "consistency_score": round(consistency_score, 4),
        "fraud_flags": fraud_flags,
        "pairwise_scores": pairwise_scores,
        "feature_variances": feature_variances,
        "is_suspicious": is_suspicious,
    }

    logger.info(
        f"Consistency check: score={consistency_score:.3f}, "
        f"flags={len(fraud_flags)}, suspicious={is_suspicious}"
    )

    return result


def _compare_pair(
    analysis_a: dict[str, Any],
    analysis_b: dict[str, Any],
) -> tuple[float, list[str]]:
    """
    Compare features between two image analyses.

    Args:
        analysis_a: Analysis dict for first image.
        analysis_b: Analysis dict for second image.

    Returns:
        tuple: (similarity_score, list_of_mismatches)
            similarity_score: 0-1, higher = more similar
            mismatches: Human-readable mismatch descriptions
    """
    scores: dict[str, float] = {}
    mismatches: list[str] = []

    # --- Store size comparison ---
    size_a = analysis_a.get("store_size", "")
    size_b = analysis_b.get("store_size", "")
    if size_a and size_b:
        if size_a == size_b:
            scores["store_size"] = 1.0
        else:
            # Adjacent sizes (small/medium or medium/large) get partial credit
            size_order = {"small": 0, "medium": 1, "large": 2}
            diff = abs(size_order.get(size_a, 1) - size_order.get(size_b, 1))
            if diff == 1:
                scores["store_size"] = 0.6
            else:
                scores["store_size"] = 0.2
                mismatches.append(
                    f"store_size_mismatch: {size_a} vs {size_b}"
                )
    else:
        scores["store_size"] = 0.5  # Unknown — neutral

    # --- Organization level comparison ---
    org_a = analysis_a.get("organization_level", "")
    org_b = analysis_b.get("organization_level", "")
    if org_a and org_b:
        if org_a == org_b:
            scores["organization_level"] = 1.0
        else:
            org_order = {"disorganized": 0, "average": 1, "well_organized": 2}
            diff = abs(org_order.get(org_a, 1) - org_order.get(org_b, 1))
            if diff == 1:
                scores["organization_level"] = 0.7
            else:
                scores["organization_level"] = 0.3
                mismatches.append(
                    f"organization_mismatch: {org_a} vs {org_b}"
                )
    else:
        scores["organization_level"] = 0.5

    # --- Brand tier comparison ---
    tier_a = analysis_a.get("brand_tier", "")
    tier_b = analysis_b.get("brand_tier", "")
    if tier_a and tier_b:
        if tier_a == tier_b:
            scores["brand_tier"] = 1.0
        else:
            scores["brand_tier"] = 0.4
            mismatches.append(
                f"brand_tier_mismatch: {tier_a} vs {tier_b}"
            )
    else:
        scores["brand_tier"] = 0.5

    # --- Product category overlap ---
    cats_a = set(analysis_a.get("visible_product_categories") or [])
    cats_b = set(analysis_b.get("visible_product_categories") or [])
    if cats_a and cats_b:
        # Jaccard similarity
        intersection = len(cats_a & cats_b)
        union = len(cats_a | cats_b)
        if union > 0:
            jaccard = intersection / union
            scores["product_overlap"] = jaccard
            if jaccard < 0.2:
                mismatches.append(
                    f"low_product_overlap: only {intersection}/{union} categories shared"
                )
        else:
            scores["product_overlap"] = 0.5
    else:
        scores["product_overlap"] = 0.5

    # --- Lighting comparison ---
    light_a = analysis_a.get("lighting_quality", "")
    light_b = analysis_b.get("lighting_quality", "")
    if light_a and light_b:
        if light_a == light_b:
            scores["lighting"] = 1.0
        else:
            light_order = {"poor": 0, "adequate": 1, "good": 2}
            diff = abs(light_order.get(light_a, 1) - light_order.get(light_b, 1))
            if diff == 1:
                scores["lighting"] = 0.7
            else:
                scores["lighting"] = 0.3
                mismatches.append(
                    f"lighting_mismatch: {light_a} vs {light_b}"
                )
    else:
        scores["lighting"] = 0.5

    # --- Image quality comparison ---
    qual_a = analysis_a.get("image_quality_score")
    qual_b = analysis_b.get("image_quality_score")
    if qual_a is not None and qual_b is not None:
        try:
            quality_diff = abs(float(qual_a) - float(qual_b))
            if quality_diff < 0.15:
                scores["image_quality"] = 1.0
            elif quality_diff < 0.30:
                scores["image_quality"] = 0.7
            else:
                scores["image_quality"] = 0.3
                mismatches.append(
                    f"image_quality_mismatch: {qual_a:.2f} vs {qual_b:.2f}"
                )
        except (ValueError, TypeError):
            scores["image_quality"] = 0.5
    else:
        scores["image_quality"] = 0.5

    # Compute weighted similarity
    total_weight = 0.0
    weighted_sum = 0.0
    for feature, weight in FEATURE_WEIGHTS.items():
        if feature in scores:
            weighted_sum += scores[feature] * weight
            total_weight += weight

    if total_weight > 0:
        similarity = weighted_sum / total_weight
    else:
        similarity = 0.5

    return similarity, mismatches


def _compute_feature_variances(
    raw_analyses: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Compute per-feature variance across all images.

    High variance on key features indicates inconsistency.
    """
    variances = {}

    # Occupancy variance
    occupancies = [
        float(a.get("shelf_occupancy_percent", 50))
        for a in raw_analyses
        if a.get("shelf_occupancy_percent") is not None
    ]
    if len(occupancies) >= 2:
        mean_occ = sum(occupancies) / len(occupancies)
        variance = sum((x - mean_occ) ** 2 for x in occupancies) / len(occupancies)
        variances["shelf_occupancy_variance"] = round(variance, 4)

    # Image quality variance
    qualities = []
    for a in raw_analyses:
        q = a.get("image_quality_score")
        if q is not None:
            try:
                qualities.append(float(q))
            except (ValueError, TypeError):
                pass
    if len(qualities) >= 2:
        mean_q = sum(qualities) / len(qualities)
        variance = sum((x - mean_q) ** 2 for x in qualities) / len(qualities)
        variances["image_quality_variance"] = round(variance, 4)

    # SKU count variance
    skus = []
    for a in raw_analyses:
        s = a.get("estimated_unique_sku_count")
        if s is not None:
            try:
                skus.append(float(s))
            except (ValueError, TypeError):
                pass
    if len(skus) >= 2:
        mean_s = sum(skus) / len(skus)
        variance = sum((x - mean_s) ** 2 for x in skus) / len(skus)
        variances["sku_count_variance"] = round(variance, 4)

    return variances


def _detect_stock_photos(
    raw_analyses: list[dict[str, Any]],
) -> list[str]:
    """
    Detect indicators of stock photography or professional images.

    Stock photos tend to have unusually high quality, perfect composition,
    and generic product arrangements that don't match real kirana stores.

    Args:
        raw_analyses: Per-image analysis dicts.

    Returns:
        list[str]: Flags for suspected stock photos.

    Heuristics:
        - Image quality score > 0.95 → flag
        - All images have identical quality → flag (different angles usually vary)
        - Organization level "well_organized" across all images → flag
    """
    flags: list[str] = []

    if not raw_analyses:
        return flags

    # Check 1: Any image quality > 0.95 (unusually professional)
    high_quality_count = 0
    qualities = []
    for analysis in raw_analyses:
        quality = analysis.get("image_quality_score")
        if quality is not None:
            try:
                q = float(quality)
                qualities.append(q)
                if q > 0.95:
                    high_quality_count += 1
            except (ValueError, TypeError):
                pass

    if high_quality_count > 0:
        flags.append(
            f"possible_stock_photo: {high_quality_count} image(s) with "
            f"unusually high quality score (>0.95)"
        )

    # Check 2: Image quality suspiciously uniform
    if len(qualities) >= 2:
        max_q = max(qualities)
        min_q = min(qualities)
        if max_q - min_q < 0.03 and max_q > 0.7:
            flags.append(
                "identical_image_quality: all images have nearly identical "
                "quality — unusual for real-world captures from different angles"
            )

    # Check 3: All images show "well_organized" — unusual for typical kirana
    org_levels = [
        a.get("organization_level") for a in raw_analyses
        if a.get("organization_level")
    ]
    if org_levels and all(o == "well_organized" for o in org_levels):
        if len(org_levels) >= 2:
            flags.append(
                "perfect_organization_all_images: all images show "
                "well-organized store — unusual for typical kirana stores"
            )

    # Check 4: Very large store size with perfect organization
    sizes = [a.get("store_size") for a in raw_analyses if a.get("store_size")]
    if sizes and all(s == "large" for s in sizes) and org_levels and all(
        o == "well_organized" for o in org_levels
    ):
        flags.append(
            "supermarket_profile: store appears to be a supermarket/chain "
            "rather than a typical kirana — verify store type"
        )

    return flags

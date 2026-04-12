"""
KIRA — Inventory Value Estimator

Estimates the total visible inventory value (in INR) by cross-referencing
detected products with known wholesale price bands and extrapolating
from visible shelf space allocation.

Owner: Analytics & CV Lead
Phase: 1.4 (P1)

Economic Significance:
    Visible inventory ≈ working capital deployed. A store with ₹3-5L
    of visible stock has demonstrably deployed that capital. Combined
    with estimated inventory turnover (30-45 days for FMCG), this
    directly yields a revenue estimate:
        Monthly Revenue ≈ Inventory Value × (30 / Avg Days to Turn)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kira.cv.inventory_estimator")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Wholesale price bands per product category (₹ per typical unit)
# These represent average wholesale cost, not MRP
CATEGORY_PRICE_BANDS = {
    "fmcg_staples": {"low": 20, "mid": 50, "high": 150},
    "fmcg_packaged": {"low": 10, "mid": 30, "high": 80},
    "beverages": {"low": 15, "mid": 25, "high": 60},
    "dairy": {"low": 20, "mid": 40, "high": 100},
    "personal_care": {"low": 30, "mid": 80, "high": 250},
    "household": {"low": 25, "mid": 60, "high": 200},
    "tobacco": {"low": 5, "mid": 15, "high": 50},
    "snacks": {"low": 5, "mid": 15, "high": 40},
    "stationery": {"low": 5, "mid": 20, "high": 50},
    "pharma_otc": {"low": 20, "mid": 60, "high": 200},
    "baby_care": {"low": 50, "mid": 150, "high": 400},
    "frozen_processed": {"low": 30, "mid": 80, "high": 200},
}

# Store size to total SKU capacity mapping (approximate units on display)
STORE_SIZE_CAPACITY = {
    "small": {"min_units": 200, "max_units": 800},
    "medium": {"min_units": 800, "max_units": 2500},
    "large": {"min_units": 2500, "max_units": 8000},
}

# Inventory turnover assumptions (days)
FMCG_TURNOVER_DAYS = 30  # Fast-moving consumer goods
SLOW_MOVING_TURNOVER_DAYS = 60  # Stationery, household, etc.

# Brand tier price multipliers
BRAND_TIER_PRICE_MULTIPLIERS = {
    "premium_dominant": 1.5,    # Premium products cost more
    "mass_dominant": 1.0,       # Standard pricing
    "value_dominant": 0.7,      # Budget products cost less
    "mixed": 1.0,               # Average
}

# Default category shelf share (rough distribution of typical kirana inventory)
DEFAULT_CATEGORY_SHARES = {
    "fmcg_staples": 0.20,
    "fmcg_packaged": 0.15,
    "beverages": 0.12,
    "dairy": 0.08,
    "personal_care": 0.10,
    "household": 0.08,
    "tobacco": 0.05,
    "snacks": 0.10,
    "stationery": 0.03,
    "pharma_otc": 0.03,
    "baby_care": 0.03,
    "frozen_processed": 0.03,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_inventory_value(
    image_analysis: dict[str, Any],
    shelf_density_result: dict[str, Any],
    sku_diversity_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Estimate total visible inventory value in INR.

    Cross-references detected product categories with wholesale price bands,
    estimates quantity from shelf space allocation and store size, and
    produces a value range (conservative low-high).

    Args:
        image_analysis: Aggregated analysis from image_analyzer.py.
            Expected: "store_size", "product_categories", "brand_tier"
        shelf_density_result: Shelf density scoring output.
            Expected: "shelf_density_score", "occupancy_raw"
        sku_diversity_result: SKU diversity output.
            Expected: "category_count", "estimated_sku_count", "brand_tier"

    Returns:
        dict containing:
            - "inventory_value_low" (float): Conservative estimate (INR)
            - "inventory_value_high" (float): Optimistic estimate (INR)
            - "estimated_total_units" (int): Estimated total units on display
            - "average_unit_value" (float): Weighted average unit value (INR)
            - "value_by_category" (dict): Per-category value breakdown
            - "methodology" (str): Description of estimation method

    Key Decision:
        Use conservative price bands. Overestimation is a bigger risk than
        underestimation for credit decisioning.
    """
    # Extract inputs with safe defaults
    store_size = image_analysis.get("store_size", "medium")
    detected_categories = sku_diversity_result.get("category_breakdown", {})
    active_categories = [
        cat for cat, detected in detected_categories.items() if detected
    ]
    if not active_categories:
        # Fallback: use raw categories from image analysis
        active_categories = image_analysis.get("product_categories", [])

    brand_tier = sku_diversity_result.get(
        "brand_tier", image_analysis.get("brand_tier", "mixed")
    )
    occupancy_raw = shelf_density_result.get("occupancy_raw", 50.0)
    sku_count = sku_diversity_result.get("estimated_sku_count", 100)

    logger.info(
        f"Estimating inventory: store_size={store_size}, "
        f"categories={len(active_categories)}, brand_tier={brand_tier}, "
        f"occupancy={occupancy_raw}%"
    )

    # Step 1: Estimate total units on display
    min_units, max_units = _estimate_units_on_display(store_size, occupancy_raw)

    # Use the midpoint as our working estimate, capped by SKU estimate
    estimated_units = int((min_units + max_units) / 2)
    # Cross-reference with SKU count — if SKU estimate is much lower, use it
    # (Each SKU might have ~3-5 facing units on average)
    sku_based_units = sku_count * 4  # Average facings per SKU
    estimated_units = min(estimated_units, max(sku_based_units, min_units))

    # Step 2: Distribute units across detected categories
    category_unit_distribution = _distribute_units_across_categories(
        total_units=estimated_units,
        active_categories=active_categories,
    )

    # Step 3: Compute value per category
    value_by_category = {}
    total_value_low = 0.0
    total_value_high = 0.0

    for category, units in category_unit_distribution.items():
        cat_low, cat_high = _compute_category_value(category, units, brand_tier)
        value_by_category[category] = {
            "units": units,
            "value_low": round(cat_low, 2),
            "value_high": round(cat_high, 2),
        }
        total_value_low += cat_low
        total_value_high += cat_high

    # Step 4: Compute average unit value
    average_unit_value = 0.0
    if estimated_units > 0:
        average_unit_value = (total_value_low + total_value_high) / (
            2 * estimated_units
        )

    result = {
        "inventory_value_low": round(total_value_low, 2),
        "inventory_value_high": round(total_value_high, 2),
        "estimated_total_units": estimated_units,
        "average_unit_value": round(average_unit_value, 2),
        "value_by_category": value_by_category,
        "methodology": (
            "Visual inventory estimation using shelf density × "
            "store size capacity × category-specific wholesale price bands. "
            "Conservative (low) uses minimum price bands; "
            "optimistic (high) uses maximum price bands with brand tier adjustment."
        ),
    }

    logger.info(
        f"Inventory value estimate: ₹{total_value_low:,.0f} — "
        f"₹{total_value_high:,.0f} ({estimated_units} units)"
    )

    return result


def _estimate_units_on_display(
    store_size: str,
    occupancy_percent: float,
) -> tuple[int, int]:
    """
    Estimate the number of product units currently on display.

    Args:
        store_size: "small", "medium", or "large".
        occupancy_percent: Shelf occupancy (0-100).

    Returns:
        tuple: (min_units, max_units) adjusted for occupancy.
    """
    capacity = STORE_SIZE_CAPACITY.get(
        store_size, STORE_SIZE_CAPACITY["medium"]
    )

    # Scale by occupancy percentage
    occupancy_ratio = max(0.0, min(100.0, occupancy_percent)) / 100.0

    min_units = int(capacity["min_units"] * occupancy_ratio)
    max_units = int(capacity["max_units"] * occupancy_ratio)

    # Ensure minimum sensible values
    min_units = max(min_units, 50)
    max_units = max(max_units, min_units + 50)

    return min_units, max_units


def _distribute_units_across_categories(
    total_units: int,
    active_categories: list[str],
) -> dict[str, int]:
    """
    Distribute estimated total units across detected categories
    using default shelf share proportions.

    Args:
        total_units: Total estimated units on display.
        active_categories: List of detected standard categories.

    Returns:
        dict: category → estimated units for that category.
    """
    if not active_categories:
        return {}

    # Get shares for active categories and normalize
    raw_shares = {}
    for cat in active_categories:
        raw_shares[cat] = DEFAULT_CATEGORY_SHARES.get(cat, 0.05)

    # Normalize so shares sum to 1.0
    total_share = sum(raw_shares.values())
    if total_share == 0:
        total_share = 1.0

    distribution = {}
    for cat, share in raw_shares.items():
        normalized_share = share / total_share
        units = max(1, int(total_units * normalized_share))
        distribution[cat] = units

    return distribution


def _compute_category_value(
    category: str,
    estimated_units: int,
    brand_tier: str,
) -> tuple[float, float]:
    """
    Compute estimated value for a single product category.

    Args:
        category: Standard category name.
        estimated_units: Estimated units of this category.
        brand_tier: Dominant brand tier for price adjustment.

    Returns:
        tuple: (value_low, value_high) for this category.
    """
    # Get price band for this category
    price_band = CATEGORY_PRICE_BANDS.get(
        category,
        {"low": 10, "mid": 30, "high": 80},  # Default if category unknown
    )

    # Get brand tier multiplier
    tier_multiplier = BRAND_TIER_PRICE_MULTIPLIERS.get(brand_tier, 1.0)

    # Compute value range
    # Low estimate: use "low" price × units (conservative)
    value_low = estimated_units * price_band["low"] * tier_multiplier

    # High estimate: use "high" price × units (optimistic)
    value_high = estimated_units * price_band["high"] * tier_multiplier

    return value_low, value_high

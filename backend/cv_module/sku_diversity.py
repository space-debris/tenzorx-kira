"""
KIRA — SKU Diversity Analyzer

Identifies and scores product category diversity from Gemini Vision analysis.
Product diversity is a strong proxy for customer base breadth and basket size,
both of which correlate with revenue.

Owner: Analytics & CV Lead
Phase: 1.3 (P0)

Economic Significance:
    A store carrying 12 product categories serves a broad customer base
    (one-stop-shop) with higher average basket size. A store with only
    3-4 categories (e.g., tobacco + beverages only) has narrower appeal
    and likely lower revenue.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kira.cv.sku_diversity")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Standard kirana product categories
PRODUCT_CATEGORIES = [
    "fmcg_staples",       # Rice, dal, oil, flour, sugar
    "fmcg_packaged",      # Biscuits, noodles, ready-to-eat
    "beverages",          # Soft drinks, juices, water
    "dairy",              # Milk, curd, paneer, butter
    "personal_care",      # Soap, shampoo, toothpaste
    "household",          # Detergent, cleaning supplies
    "tobacco",            # Cigarettes, gutka, paan
    "snacks",             # Chips, namkeen, confectionery
    "stationery",         # Notebooks, pens
    "pharma_otc",         # OTC medicines, health supplements
    "baby_care",          # Diapers, baby food
    "frozen_processed",   # Ice cream, frozen foods
]

# Max expected categories for scoring (stores rarely exceed 10-12)
MAX_CATEGORIES = 12

# Brand tier definitions
BRAND_TIERS = {
    "premium_dominant": 1.1,   # Slight positive signal (margin indicator)
    "mass_dominant": 1.0,      # Neutral (most common)
    "value_dominant": 0.9,     # Slight negative (thin margins)
    "mixed": 1.0,              # Neutral
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_sku_diversity(
    image_analysis: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute product diversity score from image analysis features.

    Analyzes detected product categories, SKU count, and brand tier mix
    to produce a diversity score that reflects the store's commercial
    breadth and customer appeal.

    Args:
        image_analysis: Aggregated analysis dict from image_analyzer.py.
            Expected keys:
                - "product_categories" (list[str]): Detected category names
                - "sku_count_estimate" (int): Estimated unique SKU count
                - "brand_tier" (str): Dominant brand tier classification
                - "brand_names" (list[str]): Detected brand names

    Returns:
        dict containing:
            - "sku_diversity_score" (float): Normalized diversity score 0-1.
            - "category_count" (int): Number of distinct categories detected.
            - "category_coverage" (float): categories / MAX_CATEGORIES.
            - "brand_tier" (str): Dominant brand tier.
            - "brand_tier_multiplier" (float): Score adjustment for brand tier.
            - "category_breakdown" (dict): Per-category detection results.
            - "estimated_sku_count" (int): Total estimated SKU count.

    Processing Logic:
        1. Map detected categories to standard PRODUCT_CATEGORIES list
        2. Count distinct categories and compute coverage ratio
        3. Factor in SKU count within categories (depth vs breadth)
        4. Apply brand tier multiplier
        5. Normalize to 0-1 score

    TODO:
        - Implement SKU diversity scoring
        - Add category mapping from Gemini's free-text to standard list
        - Add SKU depth scoring (many products per category = deeper)
        - Calibrate scoring against real store data
    """
    # TODO: Implement SKU diversity computation
    raise NotImplementedError("SKU diversity not yet implemented")


def _map_to_standard_categories(
    detected_categories: list[str],
) -> list[str]:
    """
    Map Gemini's free-text category names to standardized category list.

    Gemini Vision may return categories like "packaged snacks", "chips",
    "namkeen" — all of which should map to "snacks".

    Args:
        detected_categories: Raw category names from Gemini Vision.

    Returns:
        list[str]: Standardized category names from PRODUCT_CATEGORIES.

    TODO:
        - Implement fuzzy matching / keyword mapping
        - Handle edge cases and ambiguous categories
    """
    # TODO: Implement category mapping
    raise NotImplementedError


def _score_category_depth(
    category_count: int,
    sku_count: int,
) -> float:
    """
    Score the depth of product assortment within categories.

    A store with 8 categories and 200 SKUs has deeper assortment
    (more variants per category) than one with 8 categories and 50 SKUs.

    Args:
        category_count: Number of distinct categories.
        sku_count: Total estimated SKU count.

    Returns:
        float: Depth score (0-1).

    TODO:
        - Implement depth scoring
        - Average SKUs per category vs benchmarks
    """
    # TODO: Implement category depth scoring
    raise NotImplementedError

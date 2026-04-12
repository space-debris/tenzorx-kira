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

# Keyword mapping for fuzzy category matching
# Maps common Gemini Vision output terms to standard categories
CATEGORY_KEYWORDS = {
    "fmcg_staples": [
        "rice", "dal", "lentil", "oil", "cooking oil", "flour", "atta",
        "sugar", "salt", "spice", "masala", "wheat", "grain", "staple",
        "pulses", "cereals", "ghee", "turmeric", "chilli", "cumin",
    ],
    "fmcg_packaged": [
        "biscuit", "noodle", "maggi", "instant", "ready to eat",
        "packaged food", "packet", "packed", "rte", "cookies",
        "cake", "bread", "rusk", "jam", "ketchup", "sauce",
    ],
    "beverages": [
        "beverage", "drink", "soft drink", "juice", "water", "cola",
        "pepsi", "coca", "coke", "sprite", "fanta", "thumbs up",
        "mineral water", "soda", "energy drink", "tea", "coffee",
    ],
    "dairy": [
        "dairy", "milk", "curd", "yogurt", "paneer", "cheese",
        "butter", "cream", "lassi", "buttermilk", "amul",
    ],
    "personal_care": [
        "personal care", "soap", "shampoo", "toothpaste", "toothbrush",
        "hair oil", "cream", "lotion", "deodorant", "razor", "cosmetic",
        "beauty", "skincare", "face wash", "body wash", "perfume",
    ],
    "household": [
        "household", "detergent", "cleaning", "cleaner", "wash",
        "broom", "mop", "bucket", "brush", "toilet", "disinfectant",
        "floor cleaner", "dish wash", "laundry", "harpic", "lizol",
    ],
    "tobacco": [
        "tobacco", "cigarette", "bidi", "gutka", "paan", "betel",
        "supari", "zarda", "hookah", "smoking", "cigar",
    ],
    "snacks": [
        "snack", "chip", "wafer", "namkeen", "confectionery", "candy",
        "chocolate", "toffee", "sweet", "mithai", "lays", "kurkure",
        "bhujia", "mixture", "haldiram", "nuts", "dry fruit",
    ],
    "stationery": [
        "stationery", "notebook", "pen", "pencil", "eraser", "ruler",
        "paper", "glue", "tape", "school", "office supplies",
    ],
    "pharma_otc": [
        "pharma", "medicine", "tablet", "syrup", "ointment", "balm",
        "bandage", "otc", "health", "supplement", "vitamin",
        "cough", "pain relief", "antacid", "first aid",
    ],
    "baby_care": [
        "baby", "diaper", "baby food", "infant", "cerelac", "baby care",
        "baby powder", "baby oil", "nappy", "feeding bottle",
    ],
    "frozen_processed": [
        "frozen", "ice cream", "processed", "frozen food", "ready meal",
        "frozen vegetable", "nugget", "fries", "popsicle",
    ],
}

# SKU depth benchmarks (average SKUs per category for a typical kirana)
SKU_DEPTH_BENCHMARKS = {
    "low": 5,      # < 5 SKUs per category
    "medium": 15,  # 5-15 SKUs per category
    "high": 30,    # > 15 SKUs per category
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
    """
    # Extract values with safe defaults
    detected_categories = image_analysis.get("product_categories", [])
    sku_count = int(image_analysis.get("sku_count_estimate", 50))
    brand_tier = image_analysis.get("brand_tier", "mixed")
    brand_names = image_analysis.get("brand_names", [])

    logger.info(
        f"Computing SKU diversity: {len(detected_categories)} raw categories, "
        f"~{sku_count} SKUs, brand_tier={brand_tier}"
    )

    # Step 1: Map detected categories to standard PRODUCT_CATEGORIES
    standard_categories = _map_to_standard_categories(detected_categories)
    category_count = len(standard_categories)

    # Step 2: Compute category coverage (breadth)
    category_coverage = min(category_count / MAX_CATEGORIES, 1.0)

    # Step 3: Score category depth (SKUs per category)
    depth_score = _score_category_depth(category_count, sku_count)

    # Step 4: Compute raw diversity score (70% breadth, 30% depth)
    raw_diversity = (0.7 * category_coverage) + (0.3 * depth_score)

    # Step 5: Apply brand tier multiplier
    brand_tier_multiplier = BRAND_TIERS.get(brand_tier, 1.0)
    final_score = raw_diversity * brand_tier_multiplier

    # Clamp to [0, 1]
    final_score = max(0.0, min(1.0, final_score))

    # Build category breakdown
    category_breakdown = {}
    for cat in PRODUCT_CATEGORIES:
        category_breakdown[cat] = cat in standard_categories

    result = {
        "sku_diversity_score": round(final_score, 4),
        "category_count": category_count,
        "category_coverage": round(category_coverage, 4),
        "brand_tier": brand_tier,
        "brand_tier_multiplier": brand_tier_multiplier,
        "category_breakdown": category_breakdown,
        "estimated_sku_count": sku_count,
    }

    logger.info(
        f"SKU diversity result: score={final_score:.3f}, "
        f"categories={category_count}/{MAX_CATEGORIES}, "
        f"depth={depth_score:.3f}"
    )

    return result


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
    """
    matched_categories: set[str] = set()

    for raw_category in detected_categories:
        raw_lower = raw_category.lower().strip()

        # Direct match check first
        if raw_lower in PRODUCT_CATEGORIES:
            matched_categories.add(raw_lower)
            continue

        # Fuzzy keyword matching
        best_match = None
        best_match_count = 0

        for standard_cat, keywords in CATEGORY_KEYWORDS.items():
            match_count = 0
            for keyword in keywords:
                if keyword in raw_lower or raw_lower in keyword:
                    match_count += 1
            if match_count > best_match_count:
                best_match_count = match_count
                best_match = standard_cat

        if best_match and best_match_count > 0:
            matched_categories.add(best_match)
        else:
            # Try partial word matching as fallback
            for standard_cat, keywords in CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    # Check if any word in raw category matches a keyword
                    raw_words = raw_lower.split()
                    for word in raw_words:
                        if len(word) >= 3 and (word in keyword or keyword in word):
                            matched_categories.add(standard_cat)
                            break

    logger.debug(
        f"Category mapping: {detected_categories} → {list(matched_categories)}"
    )

    return list(matched_categories)


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
    """
    if category_count == 0 or sku_count == 0:
        return 0.0

    # Average SKUs per category
    avg_skus_per_cat = sku_count / category_count

    # Score relative to benchmarks
    # < 5 SKUs/cat → 0.2 (low depth)
    # 5-15 SKUs/cat → linear 0.2 to 0.7
    # 15-30 SKUs/cat → linear 0.7 to 1.0
    # > 30 SKUs/cat → 1.0 (max depth)

    if avg_skus_per_cat < SKU_DEPTH_BENCHMARKS["low"]:
        score = 0.2 * (avg_skus_per_cat / SKU_DEPTH_BENCHMARKS["low"])
    elif avg_skus_per_cat < SKU_DEPTH_BENCHMARKS["medium"]:
        ratio = (avg_skus_per_cat - SKU_DEPTH_BENCHMARKS["low"]) / (
            SKU_DEPTH_BENCHMARKS["medium"] - SKU_DEPTH_BENCHMARKS["low"]
        )
        score = 0.2 + ratio * 0.5
    elif avg_skus_per_cat < SKU_DEPTH_BENCHMARKS["high"]:
        ratio = (avg_skus_per_cat - SKU_DEPTH_BENCHMARKS["medium"]) / (
            SKU_DEPTH_BENCHMARKS["high"] - SKU_DEPTH_BENCHMARKS["medium"]
        )
        score = 0.7 + ratio * 0.3
    else:
        score = 1.0

    return min(score, 1.0)

"""
KIRA — Computer Vision Module

Extracts visual intelligence signals from kirana store images using
the Google Gemini Vision API. Produces shelf density, SKU diversity,
inventory estimates, and consistency signals.

Owner: Analytics & CV Lead
"""

from .image_analyzer import analyze_images
from .shelf_density import compute_shelf_density
from .sku_diversity import compute_sku_diversity
from .inventory_estimator import estimate_inventory_value
from .consistency_checker import check_consistency

__all__ = [
    "analyze_images",
    "compute_shelf_density",
    "compute_sku_diversity",
    "estimate_inventory_value",
    "check_consistency",
]

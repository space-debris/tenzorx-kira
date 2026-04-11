"""
KIRA — Catchment Area Estimator

Estimates the serviceable population and demand within the store's
catchment area. Combines area type, competition data, and population
density proxies to compute a demand-per-store index.

Owner: Analytics & CV Lead
Phase: 2.4 (P1)

Economic Significance:
    Demand index = catchment population / (competitors + 1).
    A store with 15,000 people within walking distance and only
    3 competitors has ~3,750 potential customers per store.
    The same store with 15 competitors has only 937 per store.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kira.geo.catchment")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Catchment radius by area type (meters)
CATCHMENT_RADIUS = {
    "urban": 500,        # Walking distance in urban areas
    "semi_urban": 1000,  # Slightly larger serviceable area
    "rural": 2000,       # Much larger catchment in rural areas
}

# Population density proxies by area type (people per sq km)
# These are rough national averages; production should use census data
POPULATION_DENSITY = {
    "urban": 10000,      # Metro/urban average
    "semi_urban": 3000,  # Town average
    "rural": 500,        # Rural average
}

# Demand index normalization
MAX_DEMAND_PER_STORE = 5000   # Above this, demand index = 1.0
MIN_DEMAND_PER_STORE = 200    # Below this, demand index = 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def estimate_catchment(
    latitude: float,
    longitude: float,
    area_type: str,
    competition_count: int,
) -> dict[str, Any]:
    """
    Estimate the serviceable catchment area and demand potential.

    Combines area type with population density and competition data
    to compute a demand-per-store index that indicates how much
    untapped demand exists for this specific store.

    Args:
        latitude: Store latitude.
        longitude: Store longitude.
        area_type: "urban", "semi_urban", or "rural".
        competition_count: Number of competing stores from competition module.

    Returns:
        dict containing:
            - "catchment_radius_m" (int): Serviceable radius in meters.
            - "catchment_area_sqkm" (float): Catchment area in sq km.
            - "catchment_population" (int): Estimated population in catchment.
            - "stores_in_catchment" (int): competition_count + 1 (including this store).
            - "demand_per_store" (int): Population / stores.
            - "demand_index" (float): Normalized demand score 0-1.

    Processing Logic:
        1. Determine catchment radius from area type
        2. Compute catchment area (π × r²)
        3. Estimate population from area × density proxy
        4. Compute demand per store: population / (competition + 1)
        5. Normalize demand to 0-1 index

    TODO:
        - Implement catchment estimation
        - Add census-based population density lookup (PIN code level)
        - Add POI density as population proxy (more POIs = more people)
        - Consider residential building density from OSM
    """
    # TODO: Implement catchment estimation
    raise NotImplementedError("Catchment estimator not yet implemented")


def _compute_catchment_area(
    radius_meters: int,
) -> float:
    """
    Compute catchment area in square kilometers.

    Args:
        radius_meters: Catchment radius in meters.

    Returns:
        float: Area in square kilometers.

    TODO:
        - Implement: area = π × (radius/1000)²
    """
    # TODO: Implement area computation
    raise NotImplementedError


def _estimate_population(
    area_sqkm: float,
    area_type: str,
) -> int:
    """
    Estimate population within the catchment area.

    Args:
        area_sqkm: Catchment area in square kilometers.
        area_type: Area classification for density selection.

    Returns:
        int: Estimated population.

    TODO:
        - Implement using POPULATION_DENSITY lookup
        - Add PIN-code-level census data (future enhancement)
    """
    # TODO: Implement population estimation
    raise NotImplementedError


def _compute_demand_index(
    population: int,
    store_count: int,
) -> float:
    """
    Compute normalized demand-per-store index.

    Args:
        population: Catchment population.
        store_count: Total stores in catchment (competition + 1).

    Returns:
        float: Demand index 0-1 (higher = more unserved demand = better).

    TODO:
        - Implement: demand_per_store = population / store_count
        - Normalize using MIN/MAX_DEMAND_PER_STORE
    """
    # TODO: Implement demand index computation
    raise NotImplementedError

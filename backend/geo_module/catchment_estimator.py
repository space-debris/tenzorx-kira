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
import math
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
    """
    logger.info(
        f"Estimating catchment: lat={latitude}, lon={longitude}, "
        f"area_type={area_type}, competitors={competition_count}"
    )

    # Step 1: Determine catchment radius from area type
    radius_m = CATCHMENT_RADIUS.get(area_type, CATCHMENT_RADIUS["semi_urban"])

    # Step 2: Compute catchment area (π × r²)
    area_sqkm = _compute_catchment_area(radius_m)

    # Step 3: Estimate population from area × density proxy
    population = _estimate_population(area_sqkm, area_type)

    # Step 4: Compute demand per store
    stores_in_catchment = competition_count + 1  # Include this store
    demand_per_store = int(population / stores_in_catchment)

    # Step 5: Normalize demand to 0-1 index
    demand_index = _compute_demand_index(population, stores_in_catchment)

    result = {
        "catchment_radius_m": radius_m,
        "catchment_area_sqkm": round(area_sqkm, 4),
        "catchment_population": population,
        "stores_in_catchment": stores_in_catchment,
        "demand_per_store": demand_per_store,
        "demand_index": round(demand_index, 4),
    }

    logger.info(
        f"Catchment estimation complete: radius={radius_m}m, "
        f"area={area_sqkm:.3f} sq km, population={population}, "
        f"demand_per_store={demand_per_store}, index={demand_index:.3f}"
    )

    return result


def _compute_catchment_area(
    radius_meters: int,
) -> float:
    """
    Compute catchment area in square kilometers.

    Args:
        radius_meters: Catchment radius in meters.

    Returns:
        float: Area in square kilometers.
    """
    # Convert meters to kilometers, then compute area of circle
    radius_km = radius_meters / 1000.0
    area = math.pi * radius_km ** 2
    return area


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
    """
    density = POPULATION_DENSITY.get(
        area_type, POPULATION_DENSITY["semi_urban"]
    )
    population = int(area_sqkm * density)

    # Ensure minimum reasonable population
    return max(population, 50)


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
    """
    # Ensure we don't divide by zero
    store_count = max(store_count, 1)

    # Compute raw demand per store
    demand_per_store = population / store_count

    # Normalize to 0-1 using MIN/MAX thresholds
    if demand_per_store <= MIN_DEMAND_PER_STORE:
        index = 0.0
    elif demand_per_store >= MAX_DEMAND_PER_STORE:
        index = 1.0
    else:
        # Linear interpolation between thresholds
        index = (demand_per_store - MIN_DEMAND_PER_STORE) / (
            MAX_DEMAND_PER_STORE - MIN_DEMAND_PER_STORE
        )

    return max(0.0, min(1.0, index))

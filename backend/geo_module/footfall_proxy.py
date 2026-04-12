"""
KIRA — Footfall Proxy Estimator

Estimates potential customer footfall using nearby Points of Interest (POIs)
and road type classification. High-footfall locations (near transit, schools,
markets) correlate with higher kirana store revenue.

Owner: Analytics & CV Lead
Phase: 2.2 (P0)

Data Sources:
    - Google Maps Places API: Transit stops, schools, hospitals, markets
    - Road type: Main road vs interior lane vs highway
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("kira.geo.footfall")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# Search radius for POIs (meters)
POI_SEARCH_RADIUS = 500

# POI types and their footfall contribution weights
# Higher weight = stronger footfall signal
POI_WEIGHTS = {
    "transit_station": 0.20,    # Bus stops, metro, railway
    "bus_station": 0.18,
    "subway_station": 0.22,
    "train_station": 0.20,
    "school": 0.15,             # Schools and colleges
    "university": 0.12,
    "hospital": 0.10,           # Healthcare
    "doctor": 0.08,
    "shopping_mall": 0.15,      # Commercial areas
    "market": 0.18,
    "supermarket": 0.10,
    "bank": 0.08,               # Financial services
    "atm": 0.05,
    "restaurant": 0.06,         # Food & dining
    "place_of_worship": 0.10,   # Temples, mosques, churches
    "park": 0.05,               # Recreation
}

# Road type scores (Google Maps road classification)
ROAD_TYPE_SCORES = {
    "highway": 0.3,          # High speed, low walk-in traffic
    "arterial": 0.8,         # Main roads, high footfall
    "collector": 0.7,        # Secondary main roads
    "local": 0.5,            # Interior roads, moderate footfall
    "residential": 0.4,      # Residential lanes, lower footfall
}

# Area type normalization — urban areas naturally have more POIs
AREA_TYPE_NORMALIZATION = {
    "urban": 1.0,       # POIs expected — don't inflate score
    "semi_urban": 1.3,  # Fewer POIs expected — boost signal
    "rural": 1.8,       # Very few POIs — each one matters more
}

# Maximum raw footfall score before normalization (caps diminishing returns)
MAX_RAW_FOOTFALL = 3.0

# HTTP request timeout
HTTP_TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def estimate_footfall(
    latitude: float,
    longitude: float,
    area_type: str,
) -> dict[str, Any]:
    """
    Estimate potential customer footfall from location features.

    Queries Google Maps Places API for nearby POIs, classifies road type,
    and computes a weighted footfall score.

    Args:
        latitude: Store latitude.
        longitude: Store longitude.
        area_type: "urban", "semi_urban", or "rural" (from geo_analyzer).

    Returns:
        dict containing:
            - "footfall_score" (float): Normalized footfall score 0-1.
            - "poi_count" (int): Total POIs found within radius.
            - "poi_breakdown" (dict): Count per POI type.
            - "top_pois" (list[dict]): Top 5 highest-weight POIs with names.
            - "road_type" (str): Detected road classification.
            - "road_type_score" (float): Road type's footfall contribution.
    """
    logger.info(
        f"Estimating footfall: lat={latitude}, lon={longitude}, "
        f"area_type={area_type}"
    )

    # Step 1: Query nearby places
    all_places = await _query_nearby_places(
        latitude=latitude,
        longitude=longitude,
        radius=POI_SEARCH_RADIUS,
        place_types=list(POI_WEIGHTS.keys()),
    )

    # Step 2: Categorize and count POIs
    poi_breakdown: dict[str, int] = {}
    top_pois: list[dict[str, Any]] = []

    for place in all_places:
        place_types = place.get("types", [])
        place_name = place.get("name", "Unknown")

        # Find the highest-weight matching type
        best_type = None
        best_weight = 0.0
        for ptype in place_types:
            if ptype in POI_WEIGHTS and POI_WEIGHTS[ptype] > best_weight:
                best_type = ptype
                best_weight = POI_WEIGHTS[ptype]

        if best_type:
            poi_breakdown[best_type] = poi_breakdown.get(best_type, 0) + 1
            top_pois.append({
                "name": place_name,
                "type": best_type,
                "weight": best_weight,
            })

    # Sort top POIs by weight and take top 5
    top_pois.sort(key=lambda x: x["weight"], reverse=True)
    top_pois = top_pois[:5]

    poi_count = sum(poi_breakdown.values())

    # Step 3: Estimate road type from nearby POIs and place density
    road_type = _estimate_road_type(poi_breakdown, area_type)
    road_type_score = ROAD_TYPE_SCORES.get(road_type, 0.5)

    # Step 4: Compute weighted footfall score
    footfall_score = _compute_weighted_footfall(
        poi_breakdown=poi_breakdown,
        road_type=road_type,
        area_type=area_type,
    )

    result = {
        "footfall_score": round(footfall_score, 4),
        "poi_count": poi_count,
        "poi_breakdown": poi_breakdown,
        "top_pois": top_pois,
        "road_type": road_type,
        "road_type_score": round(road_type_score, 4),
    }

    logger.info(
        f"Footfall estimation complete: score={footfall_score:.3f}, "
        f"poi_count={poi_count}, road_type={road_type}"
    )

    return result


async def _query_nearby_places(
    latitude: float,
    longitude: float,
    radius: int,
    place_types: list[str],
) -> list[dict[str, Any]]:
    """
    Query Google Maps Places API for nearby POIs.

    Args:
        latitude: Center latitude.
        longitude: Center longitude.
        radius: Search radius in meters.
        place_types: List of Google Place types to search for.

    Returns:
        list[dict]: List of found places with type, name, location.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning(
            "GOOGLE_MAPS_API_KEY not configured. "
            "Using fallback footfall estimation."
        )
        return _fallback_places(latitude, longitude)

    all_places: list[dict[str, Any]] = []
    seen_place_ids: set[str] = set()

    # Query in batches — Google Places API allows one type per request
    # Group related types to reduce API calls
    type_groups = [
        ["transit_station", "bus_station", "subway_station", "train_station"],
        ["school", "university"],
        ["hospital", "doctor"],
        ["shopping_mall", "supermarket"],
        ["bank", "atm"],
        ["restaurant"],
        ["place_of_worship"],
        ["park"],
    ]

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for type_group in type_groups:
            for place_type in type_group:
                try:
                    params = {
                        "location": f"{latitude},{longitude}",
                        "radius": radius,
                        "type": place_type,
                        "key": GOOGLE_MAPS_API_KEY,
                    }

                    response = await client.get(PLACES_API_URL, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("status") in ("OK", "ZERO_RESULTS"):
                        for place in data.get("results", []):
                            place_id = place.get("place_id", "")
                            if place_id and place_id not in seen_place_ids:
                                seen_place_ids.add(place_id)
                                all_places.append({
                                    "name": place.get("name", "Unknown"),
                                    "types": place.get("types", []),
                                    "place_id": place_id,
                                    "vicinity": place.get("vicinity", ""),
                                })
                    else:
                        logger.warning(
                            f"Places API status={data.get('status')} "
                            f"for type={place_type}"
                        )

                except httpx.HTTPError as e:
                    logger.warning(
                        f"Places API error for type={place_type}: {e}"
                    )
                    continue
                except Exception as e:
                    logger.warning(
                        f"Unexpected error querying type={place_type}: {e}"
                    )
                    continue

    logger.info(f"Found {len(all_places)} unique POIs within {radius}m")
    return all_places


def _estimate_road_type(
    poi_breakdown: dict[str, int],
    area_type: str,
) -> str:
    """
    Estimate road type based on POI density and area type.

    This is a heuristic — ideal implementation would use Google Roads API.

    Args:
        poi_breakdown: Count per POI type.
        area_type: Area classification.

    Returns:
        str: Estimated road type.
    """
    total_pois = sum(poi_breakdown.values())

    # Transit-heavy areas are likely on arterial roads
    transit_count = sum(
        poi_breakdown.get(t, 0)
        for t in ["transit_station", "bus_station", "subway_station", "train_station"]
    )

    # Commercial-heavy areas suggest main roads
    commercial_count = sum(
        poi_breakdown.get(t, 0)
        for t in ["shopping_mall", "supermarket", "bank", "restaurant"]
    )

    if transit_count >= 2 or commercial_count >= 5:
        return "arterial"
    elif transit_count >= 1 or commercial_count >= 3:
        return "collector"
    elif total_pois >= 5:
        return "local"
    elif area_type == "rural":
        return "local"
    else:
        return "residential"


def _compute_weighted_footfall(
    poi_breakdown: dict[str, int],
    road_type: str,
    area_type: str,
) -> float:
    """
    Compute weighted footfall score from POI counts and road type.

    Uses diminishing returns per POI type — the 1st transit station adds
    more value than the 5th.

    Args:
        poi_breakdown: Dict of POI type → count.
        road_type: Road classification string.
        area_type: "urban", "semi_urban", or "rural".

    Returns:
        float: Footfall score 0-1.
    """
    raw_score = 0.0

    # Compute weighted POI score with diminishing returns
    for poi_type, count in poi_breakdown.items():
        weight = POI_WEIGHTS.get(poi_type, 0.05)

        # Diminishing returns: each additional POI of same type adds
        # progressively less value. Formula: weight * ln(1 + count)
        if count > 0:
            poi_contribution = weight * math.log(1 + count)
            raw_score += poi_contribution

    # Add road type contribution (weighted at 20% of total)
    road_score = ROAD_TYPE_SCORES.get(road_type, 0.5)
    raw_score += road_score * 0.3  # Road type adds 0.3 max to raw score

    # Apply area type normalization
    area_multiplier = AREA_TYPE_NORMALIZATION.get(area_type, 1.0)
    raw_score *= area_multiplier

    # Normalize to 0-1 using sigmoid-like scaling
    # Maps raw_score (0 to ~3+) to (0, 1) smoothly
    normalized = raw_score / (raw_score + MAX_RAW_FOOTFALL)

    # Clamp to [0, 1]
    return max(0.0, min(1.0, normalized))


def _fallback_places(
    latitude: float,
    longitude: float,
) -> list[dict[str, Any]]:
    """
    Fallback when Google Maps API is unavailable.

    Returns a minimal set of synthetic POI data for development/testing.
    """
    logger.info("Using fallback POI data — API key not configured")
    return [
        {
            "name": "Nearby Area",
            "types": ["locality"],
            "place_id": "fallback_1",
            "vicinity": f"{latitude:.4f}, {longitude:.4f}",
        }
    ]

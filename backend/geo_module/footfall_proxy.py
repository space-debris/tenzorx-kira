"""
KIRA — Footfall Proxy Estimator

Estimates potential customer footfall using nearby Points of Interest (POIs)
and road-type heuristics. High-footfall locations (near transit, schools,
markets) correlate with higher kirana store revenue.

Owner: Analytics & CV Lead
Phase: 2.2 (P0)

Data Source:
    OpenStreetMap Overpass API — free, no API key required.
    Same API already used by competition_density.py.
    Single batched Overpass QL query fetches all POI types at once,
    making this MORE efficient than the previous Google Places approach
    (which required one HTTP call per POI type).
"""

from __future__ import annotations

import logging
import math
from typing import Any

import httpx

logger = logging.getLogger("kira.geo.footfall")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Overpass API endpoint (same as competition_density.py)
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Search radius for POIs (meters)
POI_SEARCH_RADIUS = 500

# POI types and their footfall contribution weights.
# Key: OSM amenity/shop/public_transport tag value → weight
# Higher weight = stronger footfall signal
POI_WEIGHTS = {
    # Transit
    "transit_station": 0.20,
    "bus_stop_area": 0.18,       # highway=bus_stop aggregated
    "subway_station": 0.22,
    "train_station": 0.20,
    "tram_stop": 0.15,
    # Education
    "school": 0.15,
    "university": 0.12,
    "college": 0.12,
    # Healthcare
    "hospital": 0.10,
    "clinic": 0.08,
    "doctors": 0.07,
    "pharmacy": 0.06,
    # Commerce
    "marketplace": 0.18,
    "supermarket": 0.10,
    "mall": 0.15,
    "bank": 0.08,
    "atm": 0.05,
    # Food & social
    "restaurant": 0.06,
    "cafe": 0.05,
    "fast_food": 0.05,
    "place_of_worship": 0.10,
    # Recreation
    "park": 0.05,
    "community_centre": 0.07,
}

# Maps OSM tag (key, value) pairs to internal POI weight keys
# Format: (osm_tag_key, osm_tag_value) → poi_weight_key
OSM_TAG_MAP = [
    # Transit — public_transport=station covers metro/rail
    ("public_transport", "station",     "transit_station"),
    ("railway",          "station",     "train_station"),
    ("railway",          "subway_entrance", "subway_station"),
    ("railway",          "tram_stop",   "tram_stop"),
    ("highway",          "bus_stop",    "bus_stop_area"),
    # Education
    ("amenity",          "school",      "school"),
    ("amenity",          "university",  "university"),
    ("amenity",          "college",     "college"),
    # Healthcare
    ("amenity",          "hospital",    "hospital"),
    ("amenity",          "clinic",      "clinic"),
    ("amenity",          "doctors",     "doctors"),
    ("amenity",          "pharmacy",    "pharmacy"),
    # Commerce
    ("amenity",          "marketplace", "marketplace"),
    ("shop",             "supermarket", "supermarket"),
    ("shop",             "mall",        "mall"),
    ("amenity",          "bank",        "bank"),
    ("amenity",          "atm",         "atm"),
    # Food & social
    ("amenity",          "restaurant",  "restaurant"),
    ("amenity",          "cafe",        "cafe"),
    ("amenity",          "fast_food",   "fast_food"),
    ("amenity",          "place_of_worship", "place_of_worship"),
    # Recreation
    ("leisure",          "park",        "park"),
    ("amenity",          "community_centre", "community_centre"),
]

# Road type scores (estimated from POI density heuristic)
ROAD_TYPE_SCORES = {
    "highway": 0.3,        # High speed, low walk-in traffic
    "arterial": 0.8,       # Main roads, high footfall
    "collector": 0.7,      # Secondary main roads
    "local": 0.5,          # Interior roads, moderate footfall
    "residential": 0.4,    # Residential lanes, lower footfall
}

# Area type normalization — urban areas naturally have more POIs
AREA_TYPE_NORMALIZATION = {
    "urban": 1.0,       # POIs expected — don't inflate score
    "semi_urban": 1.3,  # Fewer POIs expected — boost signal
    "rural": 1.8,       # Very few POIs — each one matters more
}

# Maximum raw footfall score before normalization
MAX_RAW_FOOTFALL = 3.0

# HTTP timeout (Overpass can be slow under load)
HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def estimate_footfall(
    latitude: float,
    longitude: float,
    area_type: str,
) -> dict[str, Any]:
    """
    Estimate potential customer footfall from nearby POIs.

    Queries the OSM Overpass API for all relevant POI types in a single
    batched request, then computes a weighted footfall score using
    diminishing returns per POI category.

    No API key required — uses Overpass API (same as competition_density.py).

    Args:
        latitude: Store latitude.
        longitude: Store longitude.
        area_type: "urban", "semi_urban", or "rural" (from geo_analyzer).

    Returns:
        dict containing:
            - "footfall_score" (float): Normalized footfall score 0-1.
            - "poi_count" (int): Total POIs found within radius.
            - "poi_breakdown" (dict): Count per internal POI weight key.
            - "top_pois" (list[dict]): Top 5 highest-weight POIs with names.
            - "road_type" (str): Detected road classification.
            - "road_type_score" (float): Road type's footfall contribution.
    """
    logger.info(
        f"Estimating footfall: lat={latitude}, lon={longitude}, "
        f"area_type={area_type}"
    )

    # Step 1: Query all POI types in one Overpass QL request
    raw_elements = await _query_pois_overpass(latitude, longitude, POI_SEARCH_RADIUS)

    # Step 2: Categorize elements using OSM_TAG_MAP
    poi_breakdown: dict[str, int] = {}
    top_pois: list[dict[str, Any]] = []

    for element in raw_elements:
        tags = element.get("tags", {})
        name = tags.get("name", "Unnamed")
        matched_key, matched_weight = _match_poi_type(tags)

        if matched_key:
            poi_breakdown[matched_key] = poi_breakdown.get(matched_key, 0) + 1
            top_pois.append({
                "name": name,
                "type": matched_key,
                "weight": matched_weight,
            })

    # Sort top POIs by weight, take top 5
    top_pois.sort(key=lambda x: x["weight"], reverse=True)
    top_pois = top_pois[:5]

    poi_count = sum(poi_breakdown.values())

    # Step 3: Estimate road type from POI density
    road_type = _estimate_road_type(poi_breakdown, area_type)
    road_type_score = ROAD_TYPE_SCORES.get(road_type, 0.5)

    # Step 4: Compute weighted footfall score with diminishing returns
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


# ---------------------------------------------------------------------------
# Overpass Query Helpers
# ---------------------------------------------------------------------------

async def _query_pois_overpass(
    latitude: float,
    longitude: float,
    radius: int,
) -> list[dict[str, Any]]:
    """
    Fetch all POI types from OSM Overpass in a single batched query.

    Builds one Overpass QL query covering all tag combinations in OSM_TAG_MAP.
    This is more efficient than Google Places (which needed 1 call per type).

    Args:
        latitude: Centre latitude.
        longitude: Centre longitude.
        radius: Search radius in metres.

    Returns:
        list[dict]: Overpass elements with tags and coordinates.
    """
    query = _build_poi_overpass_query(latitude, longitude, radius)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                OVERPASS_API_URL,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

        elements = data.get("elements", [])

        # Deduplicate by (lat, lon, primary tag) to avoid way + node doubles
        seen_ids: set[int] = set()
        unique: list[dict[str, Any]] = []
        for elem in elements:
            eid = elem.get("id")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                # Normalise way centres to top-level lat/lon
                if "center" in elem:
                    elem["lat"] = elem["center"].get("lat")
                    elem["lon"] = elem["center"].get("lon")
                unique.append(elem)

        logger.info(f"Overpass POI query returned {len(unique)} elements")
        return unique

    except httpx.HTTPError as e:
        logger.warning(f"Overpass POI query HTTP error: {e} — returning empty")
        return []
    except Exception as e:
        logger.warning(f"Overpass POI query unexpected error: {e} — returning empty")
        return []


def _build_poi_overpass_query(
    latitude: float,
    longitude: float,
    radius: int,
) -> str:
    """
    Build an Overpass QL query that covers all POI types in OSM_TAG_MAP.

    Generates both node and way queries for each tag combination
    using around:<radius>,<lat>,<lon> syntax.

    Returns:
        str: Complete Overpass QL query string.
    """
    lines: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    for osm_key, osm_value, _ in OSM_TAG_MAP:
        pair = (osm_key, osm_value)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        around = f"around:{radius},{latitude},{longitude}"
        lines.append(f'  node["{osm_key}"="{osm_value}"]({around});')
        lines.append(f'  way["{osm_key}"="{osm_value}"]({around});')

    body = "\n".join(lines)
    return f"[out:json][timeout:25];\n(\n{body}\n);\nout center body;"


def _match_poi_type(
    tags: dict[str, str],
) -> tuple[str | None, float]:
    """
    Match an OSM element's tags to an internal POI weight key.

    Iterates OSM_TAG_MAP in order (highest-weight types first after sorting)
    and returns the first match.

    Args:
        tags: OSM tag dict from the element.

    Returns:
        tuple: (weight_key, weight_value) or (None, 0.0) if no match.
    """
    for osm_key, osm_value, weight_key in OSM_TAG_MAP:
        if tags.get(osm_key) == osm_value:
            return weight_key, POI_WEIGHTS.get(weight_key, 0.05)
    return None, 0.0


# ---------------------------------------------------------------------------
# Scoring Helpers
# ---------------------------------------------------------------------------

def _estimate_road_type(
    poi_breakdown: dict[str, int],
    area_type: str,
) -> str:
    """
    Estimate road type from POI density heuristic.

    Transit-heavy → arterial, commercial-heavy → collector, sparse → residential.
    """
    transit_keys = {"transit_station", "train_station", "subway_station",
                    "bus_stop_area", "tram_stop"}
    commercial_keys = {"supermarket", "mall", "bank", "restaurant",
                       "marketplace", "fast_food"}

    transit_count = sum(poi_breakdown.get(k, 0) for k in transit_keys)
    commercial_count = sum(poi_breakdown.get(k, 0) for k in commercial_keys)
    total_pois = sum(poi_breakdown.values())

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
    Compute normalized footfall score (0-1) from POI counts and road type.

    Uses logarithmic diminishing returns per POI type — the 1st transit
    station adds more value than the 5th.

    Formula per type: weight × ln(1 + count)
    Road type adds up to 0.3 to raw score.
    Area normalization adjusts for expected POI density.
    Final score = raw / (raw + MAX_RAW_FOOTFALL) — smooth 0-1 mapping.
    """
    raw_score = 0.0

    for poi_type, count in poi_breakdown.items():
        weight = POI_WEIGHTS.get(poi_type, 0.05)
        if count > 0:
            raw_score += weight * math.log(1 + count)

    # Road type contribution
    road_score = ROAD_TYPE_SCORES.get(road_type, 0.5)
    raw_score += road_score * 0.3

    # Area type normalization
    area_multiplier = AREA_TYPE_NORMALIZATION.get(area_type, 1.0)
    raw_score *= area_multiplier

    # Map to 0-1 using smooth saturation
    normalized = raw_score / (raw_score + MAX_RAW_FOOTFALL)
    return max(0.0, min(1.0, normalized))

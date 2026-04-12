"""
KIRA — Competition Density Analyzer

Maps and counts competing retail stores near the target location
using OpenStreetMap Overpass API. Higher competition density means
revenue is split across more stores, reducing per-store revenue potential.

Owner: Analytics & CV Lead
Phase: 2.3 (P1)

Data Source:
    OpenStreetMap Overpass API (free, no API key required)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("kira.geo.competition")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Search radius for competitors (meters)
COMPETITION_SEARCH_RADIUS = 500

# OSM tags that indicate competing retail stores
COMPETITOR_TAGS = {
    "direct": [
        # Direct competitors — same store type
        {"shop": "convenience"},
        {"shop": "general"},
        {"shop": "kiosk"},
        {"shop": "variety_store"},
    ],
    "adjacent": [
        # Adjacent competitors — different format, some overlap
        {"shop": "supermarket"},
        {"shop": "department_store"},
        {"shop": "chemist"},
        {"amenity": "pharmacy"},
    ],
}

# Competition score parameters
# Higher competition = lower score (inverse relationship)
MAX_DIRECT_COMPETITORS = 15     # Beyond this, score is 0
LOW_COMPETITION_THRESHOLD = 3   # Below this, score is 1.0

# Area type competition normalization factors
# Urban areas naturally have more stores — don't over-penalize
AREA_COMPETITION_NORMALIZATION = {
    "urban": 1.5,       # Expect more competitors — reduce penalty
    "semi_urban": 1.0,  # Baseline
    "rural": 0.7,       # Fewer competitors expected — increase penalty
}

# HTTP request timeout (Overpass can be slow)
HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_competition(
    latitude: float,
    longitude: float,
    area_type: str,
) -> dict[str, Any]:
    """
    Analyze competition density around the store location.

    Queries OpenStreetMap Overpass API for nearby retail/convenience stores,
    categorizes them as direct or adjacent competitors, and computes a
    competition-adjusted score.

    Args:
        latitude: Store latitude.
        longitude: Store longitude.
        area_type: "urban", "semi_urban", or "rural" (affects normalization).

    Returns:
        dict containing:
            - "competition_count" (int): Total competing stores found.
            - "direct_competitors" (int): Direct competitor count.
            - "adjacent_competitors" (int): Adjacent competitor count.
            - "competition_score" (float): 0-1, higher = less competition (better).
            - "competitor_details" (list[dict]): Names and types of found stores.
            - "density_per_sqkm" (float): Competitors per square kilometer.
    """
    logger.info(
        f"Analyzing competition: lat={latitude}, lon={longitude}, "
        f"area_type={area_type}"
    )

    # Step 1: Build Overpass query
    query = _build_overpass_query(latitude, longitude, COMPETITION_SEARCH_RADIUS)

    # Step 2: Execute query
    raw_results = await _execute_overpass_query(query)

    # Step 3: Categorize results as direct or adjacent competitors
    direct_competitors = 0
    adjacent_competitors = 0
    competitor_details: list[dict[str, Any]] = []

    direct_shop_types = {
        tag_val
        for tag_dict in COMPETITOR_TAGS["direct"]
        for tag_val in tag_dict.values()
    }
    adjacent_shop_types = {
        tag_val
        for tag_dict in COMPETITOR_TAGS["adjacent"]
        for tag_val in tag_dict.values()
    }

    for element in raw_results:
        tags = element.get("tags", {})
        shop_type = tags.get("shop", "")
        amenity_type = tags.get("amenity", "")
        name = tags.get("name", "Unnamed Store")
        store_type_val = shop_type or amenity_type

        is_direct = shop_type in direct_shop_types
        is_adjacent = (
            shop_type in adjacent_shop_types
            or amenity_type in adjacent_shop_types
        )

        if is_direct:
            direct_competitors += 1
            competitor_details.append({
                "name": name,
                "type": store_type_val,
                "category": "direct",
                "lat": element.get("lat"),
                "lon": element.get("lon"),
            })
        elif is_adjacent:
            adjacent_competitors += 1
            competitor_details.append({
                "name": name,
                "type": store_type_val,
                "category": "adjacent",
                "lat": element.get("lat"),
                "lon": element.get("lon"),
            })

    competition_count = direct_competitors + adjacent_competitors

    # Step 4: Compute competition score (inverse relationship)
    competition_score = _compute_competition_score(
        direct_count=direct_competitors,
        adjacent_count=adjacent_competitors,
        area_type=area_type,
    )

    # Step 5: Compute density per sq km
    import math
    search_area_sqkm = math.pi * (COMPETITION_SEARCH_RADIUS / 1000) ** 2
    density_per_sqkm = competition_count / search_area_sqkm if search_area_sqkm > 0 else 0

    result = {
        "competition_count": competition_count,
        "direct_competitors": direct_competitors,
        "adjacent_competitors": adjacent_competitors,
        "competition_score": round(competition_score, 4),
        "competitor_details": competitor_details,
        "density_per_sqkm": round(density_per_sqkm, 2),
    }

    logger.info(
        f"Competition analysis complete: {direct_competitors} direct, "
        f"{adjacent_competitors} adjacent, score={competition_score:.3f}"
    )

    return result


def _build_overpass_query(
    latitude: float,
    longitude: float,
    radius: int,
) -> str:
    """
    Build an Overpass QL query for nearby retail stores.

    Args:
        latitude: Center latitude.
        longitude: Center longitude.
        radius: Search radius in meters.

    Returns:
        str: Overpass QL query string.
    """
    # Build union of all competitor tag queries
    queries = []

    for category in ["direct", "adjacent"]:
        for tag_dict in COMPETITOR_TAGS[category]:
            for key, value in tag_dict.items():
                queries.append(
                    f'  node["{key}"="{value}"](around:{radius},{latitude},{longitude});'
                )
                queries.append(
                    f'  way["{key}"="{value}"](around:{radius},{latitude},{longitude});'
                )

    query_body = "\n".join(queries)

    overpass_query = f"""
[out:json][timeout:25];
(
{query_body}
);
out center body;
"""
    return overpass_query.strip()


async def _execute_overpass_query(
    query: str,
) -> list[dict[str, Any]]:
    """
    Execute an Overpass API query and parse results.

    Args:
        query: Overpass QL query string.

    Returns:
        list[dict]: Parsed store results with name, type, coordinates.
    """
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

        # Normalize elements — ways may have center coordinates
        normalized: list[dict[str, Any]] = []
        for elem in elements:
            entry = {
                "id": elem.get("id"),
                "type": elem.get("type"),
                "tags": elem.get("tags", {}),
            }

            # Get coordinates (nodes have lat/lon, ways have center)
            if "lat" in elem and "lon" in elem:
                entry["lat"] = elem["lat"]
                entry["lon"] = elem["lon"]
            elif "center" in elem:
                entry["lat"] = elem["center"].get("lat")
                entry["lon"] = elem["center"].get("lon")

            normalized.append(entry)

        logger.info(f"Overpass query returned {len(normalized)} elements")
        return normalized

    except httpx.HTTPError as e:
        logger.warning(f"Overpass API error: {e} — returning empty results")
        return []
    except Exception as e:
        logger.warning(f"Unexpected Overpass error: {e} — returning empty results")
        return []


def _compute_competition_score(
    direct_count: int,
    adjacent_count: int,
    area_type: str,
) -> float:
    """
    Compute competition score from competitor counts.

    Score is inversely proportional to competition density,
    with area-type normalization (urban naturally has more stores).

    Args:
        direct_count: Number of direct competitors.
        adjacent_count: Number of adjacent competitors.
        area_type: Area type for normalization.

    Returns:
        float: Competition score 0-1 (higher = less competition = better).
    """
    # Weight direct competitors more heavily than adjacent
    # Direct competitors: full weight
    # Adjacent competitors: 50% weight (different format, partial overlap)
    effective_competition = direct_count + (adjacent_count * 0.5)

    # Apply area-type normalization
    normalization = AREA_COMPETITION_NORMALIZATION.get(area_type, 1.0)
    # Higher normalization = more expected → divide to reduce penalty
    normalized_competition = effective_competition / normalization

    # Compute score — inverse relationship with thresholds
    if normalized_competition <= LOW_COMPETITION_THRESHOLD:
        # Low competition — score is 1.0 (best)
        score = 1.0
    elif normalized_competition >= MAX_DIRECT_COMPETITORS:
        # Extreme competition — score is 0.0 (worst)
        score = 0.0
    else:
        # Linear interpolation between thresholds
        score = 1.0 - (
            (normalized_competition - LOW_COMPETITION_THRESHOLD)
            / (MAX_DIRECT_COMPETITORS - LOW_COMPETITION_THRESHOLD)
        )

    return max(0.0, min(1.0, score))

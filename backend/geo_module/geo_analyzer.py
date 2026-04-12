"""
KIRA — Geo Analyzer

Base GPS coordinate processing module. Validates GPS inputs,
performs reverse geocoding, and classifies the area type
(urban/semi-urban/rural).

Owner: Analytics & CV Lead
Phase: 2.1 (P0 — blocking for all other Geo work)

Data Source:
    Nominatim (OpenStreetMap) — free, no API key required.
    Endpoint: https://nominatim.openstreetmap.org/reverse
    Usage policy: max 1 req/sec, must set a descriptive User-Agent.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import httpx

logger = logging.getLogger("kira.geo.analyzer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# India bounding box (approximate)
INDIA_BOUNDS = {
    "lat_min": 6.5,
    "lat_max": 37.5,
    "lon_min": 68.0,
    "lon_max": 97.5,
}

# GPS accuracy threshold — reject readings above this (meters)
MAX_GPS_ACCURACY = 100

# Nominatim reverse geocoding endpoint (OSM — free, no API key)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# User-Agent is REQUIRED by Nominatim usage policy.
# Must identify the application; generic strings may be blocked.
NOMINATIM_HEADERS = {
    "User-Agent": "KIRA-Underwriting/1.0 (kirana credit assessment; hackathon project)",
    "Accept-Language": "en",
}

# Area type classification based on known metropolitan cities
METRO_CITIES = [
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad",
    "ahmedabad", "chennai", "kolkata", "pune", "jaipur",
    "lucknow", "kanpur", "nagpur", "indore", "thane",
    "bhopal", "visakhapatnam", "pimpri-chinchwad", "patna",
    "vadodara", "ghaziabad", "ludhiana", "agra", "nashik",
    "faridabad", "meerut", "rajkot", "varanasi", "srinagar",
    "aurangabad", "dhanbad", "amritsar", "allahabad", "ranchi",
    "howrah", "coimbatore", "jabalpur", "gwalior", "vijayawada",
    "jodhpur", "madurai", "raipur", "kota", "chandigarh",
    "guwahati", "solapur", "hubli-dharwad", "mysore", "mysuru",
    "tiruchirappalli", "noida", "gurugram", "gurgaon", "navi mumbai",
    "new delhi",
]

# Known large towns / district headquarters (semi-urban classification)
SEMI_URBAN_KEYWORDS = [
    "nagar", "town", "tehsil", "taluka", "mandal", "taluk",
]

# HTTP request timeout
HTTP_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_location(
    latitude: float,
    longitude: float,
    accuracy_meters: float = 50.0,
) -> dict[str, Any]:
    """
    Process and enrich GPS coordinates for a store location.

    Validates coordinates, performs reverse geocoding via Nominatim
    (OpenStreetMap) to get locality information, and classifies the
    area type (urban / semi_urban / rural).

    No API key required. Nominatim is a free OSM service.

    Args:
        latitude: Store latitude (must be within India).
        longitude: Store longitude (must be within India).
        accuracy_meters: GPS accuracy in meters. Readings >100m are
            flagged as unreliable but processing continues.

    Returns:
        dict containing:
            - "latitude" (float): Validated latitude.
            - "longitude" (float): Validated longitude.
            - "accuracy_meters" (float): GPS accuracy.
            - "is_accurate" (bool): True if accuracy <= MAX_GPS_ACCURACY.
            - "area_type" (str): "urban", "semi_urban", or "rural".
            - "locality" (str): Locality/neighbourhood name.
            - "district" (str): District name.
            - "state" (str): State name.
            - "pin_code" (str): PIN code (if available).
            - "formatted_address" (str): Full formatted address.

    Raises:
        ValueError: If coordinates are outside India's bounding box.
    """
    logger.info(
        f"Analyzing location: lat={latitude}, lon={longitude}, "
        f"accuracy={accuracy_meters}m"
    )

    # Step 1: Validate coordinates are within India
    if not _validate_coordinates(latitude, longitude):
        raise ValueError(
            f"Coordinates ({latitude}, {longitude}) are outside India's bounds. "
            f"Latitude must be {INDIA_BOUNDS['lat_min']}-{INDIA_BOUNDS['lat_max']}, "
            f"longitude must be {INDIA_BOUNDS['lon_min']}-{INDIA_BOUNDS['lon_max']}."
        )

    # Step 2: Check GPS accuracy
    is_accurate = accuracy_meters <= MAX_GPS_ACCURACY
    if not is_accurate:
        logger.warning(
            f"GPS accuracy {accuracy_meters}m exceeds threshold "
            f"({MAX_GPS_ACCURACY}m) — results may be unreliable"
        )

    # Step 3: Reverse geocode via Nominatim (OSM)
    geocode_result = await _reverse_geocode_nominatim(latitude, longitude)

    # Step 4: Extract location components from Nominatim response
    address = geocode_result.get("address", {})
    locality = _extract_locality(address)
    district = _extract_district(address)
    state = address.get("state", "Unknown")
    pin_code = address.get("postcode", "")
    formatted_address = geocode_result.get("display_name", "")

    # Step 5: Classify area type
    area_type = _classify_area_type(address, formatted_address)

    result = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_meters": accuracy_meters,
        "is_accurate": is_accurate,
        "area_type": area_type,
        "locality": locality,
        "district": district,
        "state": state,
        "pin_code": pin_code,
        "formatted_address": formatted_address,
    }

    logger.info(
        f"Location analysis complete: area_type={area_type}, "
        f"locality={locality}, district={district}, state={state}"
    )

    return result


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def _validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate that coordinates are within India's bounding box."""
    return (
        INDIA_BOUNDS["lat_min"] <= latitude <= INDIA_BOUNDS["lat_max"]
        and INDIA_BOUNDS["lon_min"] <= longitude <= INDIA_BOUNDS["lon_max"]
    )


async def _reverse_geocode_nominatim(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Reverse geocode coordinates using Nominatim (OpenStreetMap).

    Free, no API key. Must set User-Agent and respect 1 req/sec limit.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.

    Returns:
        dict: Nominatim JSON response with "address" and "display_name" keys.
    """
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1,
        "zoom": 14,          # Neighbourhood-level detail
        "accept-language": "en",
    }

    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            headers=NOMINATIM_HEADERS,
        ) as client:
            response = await client.get(NOMINATIM_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            logger.warning(f"Nominatim error: {data['error']} — using fallback")
            return _fallback_geocode(latitude, longitude)

        logger.debug(f"Nominatim response: {data.get('display_name', '')}")
        return data

    except httpx.HTTPError as e:
        logger.warning(f"Nominatim HTTP error: {e} — using fallback")
        return _fallback_geocode(latitude, longitude)
    except Exception as e:
        logger.warning(f"Nominatim unexpected error: {e} — using fallback")
        return _fallback_geocode(latitude, longitude)


# ---------------------------------------------------------------------------
# Address Component Extraction
# ---------------------------------------------------------------------------

def _extract_locality(address: dict[str, Any]) -> str:
    """
    Extract the most granular locality name from Nominatim address dict.

    Nominatim returns different keys at different zoom levels.
    Priority order: neighbourhood > suburb > quarter > city_district > city > town > village
    """
    for key in [
        "neighbourhood",
        "suburb",
        "quarter",
        "city_district",
        "city",
        "town",
        "village",
        "county",
    ]:
        value = address.get(key)
        if value:
            return value
    return "Unknown"


def _extract_district(address: dict[str, Any]) -> str:
    """
    Extract district / county name from Nominatim address dict.

    Priority: state_district > county > city (when city is large enough
    to be treated as its own district, e.g. Mumbai, Delhi).
    """
    for key in ["state_district", "county", "city"]:
        value = address.get(key)
        if value:
            return value
    return "Unknown"


# ---------------------------------------------------------------------------
# Area Type Classification
# ---------------------------------------------------------------------------

def _classify_area_type(
    address: dict[str, Any],
    formatted_address: str,
) -> str:
    """
    Classify location as urban, semi_urban, or rural.

    Uses locality names and known city lists — no additional API call needed.

    Args:
        address: Parsed Nominatim address dict.
        formatted_address: Full display_name string from Nominatim.

    Returns:
        str: "urban", "semi_urban", or "rural".
    """
    # Combine all text for keyword search
    city = (address.get("city") or "").lower()
    town = (address.get("town") or "").lower()
    county = (address.get("county") or "").lower()
    state_dist = (address.get("state_district") or "").lower()
    full_text = f"{city} {town} {county} {state_dist} {formatted_address.lower()}"

    # Check 1: Known metro cities → urban
    for metro in METRO_CITIES:
        if metro in city or metro in full_text:
            logger.debug(f"Area classified as urban — metro match: {metro}")
            return "urban"

    # Check 2: Has a "city" tag in address → urban
    if address.get("city"):
        logger.debug("Area classified as urban — has 'city' in address")
        return "urban"

    # Check 3: Has a "town" → semi_urban
    if address.get("town"):
        logger.debug("Area classified as semi_urban — has 'town' in address")
        return "semi_urban"

    # Check 4: Semi-urban keywords in text
    for keyword in SEMI_URBAN_KEYWORDS:
        if keyword in full_text:
            logger.debug(f"Area classified as semi_urban — keyword: {keyword}")
            return "semi_urban"

    # Check 5: Has PIN code → at least semi_urban (addressable area)
    if address.get("postcode"):
        logger.debug("Area classified as semi_urban — has postcode")
        return "semi_urban"

    # Default: rural
    logger.debug("Area classified as rural — no urban/semi-urban indicators found")
    return "rural"


# ---------------------------------------------------------------------------
# Fallback (when Nominatim is unavailable)
# ---------------------------------------------------------------------------

def _fallback_geocode(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Coordinate-based fallback when Nominatim is unavailable.

    Approximates the nearest known metro city using Euclidean distance
    and returns a minimal address dict.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.

    Returns:
        dict: Approximate Nominatim-shaped response.
    """
    logger.info("Using coordinate-based fallback geocoding")

    metro_coords = {
        "Mumbai": (19.076, 72.877),
        "Delhi": (28.704, 77.102),
        "Bangalore": (12.971, 77.594),
        "Hyderabad": (17.385, 78.486),
        "Chennai": (13.082, 80.270),
        "Kolkata": (22.572, 88.363),
        "Pune": (18.520, 73.856),
        "Ahmedabad": (23.022, 72.571),
        "Jaipur": (26.912, 75.787),
        "Lucknow": (26.846, 80.946),
    }

    closest_city = "Unknown"
    closest_dist = float("inf")

    for city, (lat, lon) in metro_coords.items():
        dist = math.sqrt((latitude - lat) ** 2 + (longitude - lon) ** 2)
        if dist < closest_dist:
            closest_dist = dist
            closest_city = city

    # Within ~50km of a metro → treat as urban
    if closest_dist < 0.5:
        address = {
            "city": closest_city,
            "state": "India",
            "postcode": "",
        }
    else:
        address = {
            "town": "Unknown",
            "state": "India",
            "postcode": "",
        }

    return {
        "display_name": f"{latitude:.4f}, {longitude:.4f}",
        "address": address,
    }

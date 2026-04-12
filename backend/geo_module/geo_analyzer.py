"""
KIRA — Geo Analyzer

Base GPS coordinate processing module. Validates GPS inputs,
performs reverse geocoding, and classifies the area type
(urban/semi-urban/rural).

Owner: Analytics & CV Lead
Phase: 2.1 (P0 — blocking for all other Geo work)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("kira.geo.analyzer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# India bounding box (approximate)
INDIA_BOUNDS = {
    "lat_min": 6.5,
    "lat_max": 37.5,
    "lon_min": 68.0,
    "lon_max": 97.5,
}

# GPS accuracy threshold — reject readings above this (meters)
MAX_GPS_ACCURACY = 100

# Reverse geocoding API endpoint
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Area type classification based on location characteristics
URBAN_INDICATORS = [
    "metropolitan",
    "corporation",
    "municipal_corporation",
    "megacity",
    "metro",
    "city",
    "nagar_nigam",
]
SEMI_URBAN_INDICATORS = [
    "municipality",
    "town",
    "nagar_panchayat",
    "nagar_palika",
    "cantonment",
    "census_town",
]

# Known metro cities for faster classification
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
    "guwahati", "solapur", "hubli-dharwad", "mysore", "tiruchirappalli",
    "noida", "gurugram", "gurgaon", "navi mumbai",
]

# HTTP request timeout
HTTP_TIMEOUT = 10.0


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

    Validates coordinates, performs reverse geocoding to get locality
    information, and classifies the area type.

    Args:
        latitude: Store latitude (must be within India).
        longitude: Store longitude (must be within India).
        accuracy_meters: GPS accuracy in meters. Readings >100m are
            flagged as unreliable.

    Returns:
        dict containing:
            - "latitude" (float): Validated latitude.
            - "longitude" (float): Validated longitude.
            - "accuracy_meters" (float): GPS accuracy.
            - "is_accurate" (bool): True if accuracy < MAX_GPS_ACCURACY.
            - "area_type" (str): "urban", "semi_urban", or "rural".
            - "locality" (str): Locality/neighborhood name.
            - "district" (str): District name.
            - "state" (str): State name.
            - "pin_code" (str): PIN code (if available).
            - "formatted_address" (str): Full formatted address.

    Raises:
        ValueError: If coordinates are outside India.
        RuntimeError: If Google Maps API key is not configured.
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

    # Step 3: Reverse geocode
    geocode_result = await _reverse_geocode(latitude, longitude)

    # Step 4: Extract location components
    locality = geocode_result.get("locality", "Unknown")
    district = geocode_result.get("district", "Unknown")
    state = geocode_result.get("state", "Unknown")
    pin_code = geocode_result.get("pin_code", "")
    formatted_address = geocode_result.get("formatted_address", "")

    # Step 5: Classify area type
    area_type = _classify_area_type(geocode_result)

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


def _validate_coordinates(
    latitude: float,
    longitude: float,
) -> bool:
    """
    Validate that coordinates are within India's bounding box.

    Args:
        latitude: Latitude to validate.
        longitude: Longitude to validate.

    Returns:
        bool: True if within India.
    """
    return (
        INDIA_BOUNDS["lat_min"] <= latitude <= INDIA_BOUNDS["lat_max"]
        and INDIA_BOUNDS["lon_min"] <= longitude <= INDIA_BOUNDS["lon_max"]
    )


async def _reverse_geocode(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Perform reverse geocoding using Google Maps Geocoding API.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.

    Returns:
        dict: Geocoding result with address components.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning(
            "GOOGLE_MAPS_API_KEY not configured. Using fallback geocoding."
        )
        return _fallback_geocode(latitude, longitude)

    params = {
        "latlng": f"{latitude},{longitude}",
        "key": GOOGLE_MAPS_API_KEY,
        "language": "en",
        "result_type": "street_address|locality|administrative_area_level_3",
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(GEOCODE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            logger.warning(
                f"Geocoding returned status={data.get('status')} — using fallback"
            )
            return _fallback_geocode(latitude, longitude)

        # Parse address components from the best result
        result = data["results"][0]
        return _parse_address_components(result)

    except httpx.HTTPError as e:
        logger.warning(f"Geocoding API error: {e} — using fallback")
        return _fallback_geocode(latitude, longitude)
    except Exception as e:
        logger.warning(f"Unexpected geocoding error: {e} — using fallback")
        return _fallback_geocode(latitude, longitude)


def _parse_address_components(
    geocode_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Parse Google Maps geocode response into structured location data.

    Args:
        geocode_result: Single geocode result from Google Maps API.

    Returns:
        dict: Parsed location components.
    """
    components = geocode_result.get("address_components", [])
    formatted_address = geocode_result.get("formatted_address", "")

    parsed = {
        "formatted_address": formatted_address,
        "locality": "",
        "district": "",
        "state": "",
        "pin_code": "",
        "country": "",
        "sublocality": "",
        "admin_level_types": [],
    }

    for component in components:
        types = component.get("types", [])
        name = component.get("long_name", "")

        if "locality" in types:
            parsed["locality"] = name
        elif "sublocality_level_1" in types or "sublocality" in types:
            parsed["sublocality"] = name
        elif "administrative_area_level_2" in types:
            parsed["district"] = name
        elif "administrative_area_level_1" in types:
            parsed["state"] = name
        elif "postal_code" in types:
            parsed["pin_code"] = name
        elif "country" in types:
            parsed["country"] = name

        # Track all administrative types for area classification
        for t in types:
            if "administrative" in t or "locality" in t:
                parsed["admin_level_types"].append(t)

    # If no locality found, use sublocality
    if not parsed["locality"] and parsed["sublocality"]:
        parsed["locality"] = parsed["sublocality"]

    return parsed


def _classify_area_type(
    geocode_result: dict[str, Any],
) -> str:
    """
    Classify location as urban, semi-urban, or rural.

    Uses geocoding result's administrative level types and
    locality indicators.

    Args:
        geocode_result: Parsed geocoding response.

    Returns:
        str: "urban", "semi_urban", or "rural".
    """
    locality = geocode_result.get("locality", "").lower()
    district = geocode_result.get("district", "").lower()
    formatted_address = geocode_result.get("formatted_address", "").lower()
    admin_types = geocode_result.get("admin_level_types", [])

    # Check 1: Known metro cities
    for metro in METRO_CITIES:
        if metro in locality or metro in district or metro in formatted_address:
            logger.debug(f"Area classified as urban — metro city match: {metro}")
            return "urban"

    # Check 2: Urban indicators in address
    full_text = f"{locality} {district} {formatted_address}"
    for indicator in URBAN_INDICATORS:
        if indicator in full_text:
            logger.debug(
                f"Area classified as urban — indicator: {indicator}"
            )
            return "urban"

    # Check 3: Semi-urban indicators
    for indicator in SEMI_URBAN_INDICATORS:
        if indicator in full_text:
            logger.debug(
                f"Area classified as semi_urban — indicator: {indicator}"
            )
            return "semi_urban"

    # Check 4: Administrative level types from Google
    if "administrative_area_level_3" in admin_types:
        # Level 3 usually indicates a smaller administrative unit
        return "semi_urban"

    # Check 5: If we have a PIN code, check PIN-based heuristics
    pin_code = geocode_result.get("pin_code", "")
    if pin_code:
        # Indian PINs starting with certain digits map to regions —
        # but this is too coarse for urban/rural classification.
        # Default to semi_urban if we have a PIN (at least addressable)
        return "semi_urban"

    # Default: rural
    logger.debug("Area classified as rural — no urban/semi-urban indicators found")
    return "rural"


def _fallback_geocode(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Fallback geocoding when Google Maps API is unavailable.

    Uses approximate region classification based on coordinates.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.

    Returns:
        dict: Approximate location data.
    """
    # Very rough region classification based on known Indian city coordinates
    # This is a fallback — primary should always use Google Maps API

    # Default result
    result = {
        "formatted_address": f"{latitude:.4f}, {longitude:.4f}",
        "locality": "Unknown",
        "district": "Unknown",
        "state": "Unknown",
        "pin_code": "",
        "admin_level_types": [],
    }

    # Rough state estimation from lat/lon
    # Major metro area detection (very approximate)
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

    import math

    closest_metro = None
    closest_distance = float("inf")

    for city, (lat, lon) in metro_coords.items():
        dist = math.sqrt((latitude - lat) ** 2 + (longitude - lon) ** 2)
        if dist < closest_distance:
            closest_distance = dist
            closest_metro = city

    if closest_distance < 0.5:  # ~50km
        result["locality"] = closest_metro or "Unknown"
        result["admin_level_types"] = ["locality"]
    elif closest_distance < 1.5:
        result["locality"] = f"Near {closest_metro}"

    return result

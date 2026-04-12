"""
KIRA — Geo Intelligence Module

Extracts spatial intelligence signals from GPS coordinates using
Google Maps Places API and OpenStreetMap Overpass API. Produces
footfall, competition, and catchment signals.

Owner: Analytics & CV Lead
"""

from .geo_analyzer import analyze_location
from .footfall_proxy import estimate_footfall
from .competition_density import analyze_competition
from .catchment_estimator import estimate_catchment

__all__ = [
    "analyze_location",
    "estimate_footfall",
    "analyze_competition",
    "estimate_catchment",
]

"""
KIRA Backend — Models Package

Exports all input/output schema models for the KIRA assessment API.
"""

from .input_schema import (
    AssessmentMetadata,
    AssessmentRequest,
    GPSInput,
    ImageInput,
    ImageType,
)
from .output_schema import (
    AreaType,
    AssessmentOutput,
    AssessmentStatus,
    BrandTierMix,
    CVSignals,
    Explanation,
    ExplanationSummary,
    FraudDetection,
    GeoSignals,
    LoanRecommendation,
    RevenueEstimate,
    RiskAssessment,
    RiskBand,
    StoreSizeCategory,
    ValueRange,
)

__all__ = [
    # Input schemas
    "AssessmentRequest",
    "ImageInput",
    "ImageType",
    "GPSInput",
    "AssessmentMetadata",
    # Output schemas
    "AssessmentOutput",
    "RevenueEstimate",
    "RiskAssessment",
    "RiskBand",
    "CVSignals",
    "GeoSignals",
    "LoanRecommendation",
    "FraudDetection",
    "Explanation",
    "ExplanationSummary",
    "ValueRange",
    "AreaType",
    "StoreSizeCategory",
    "BrandTierMix",
    "AssessmentStatus",
]

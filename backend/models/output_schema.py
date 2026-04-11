"""
KIRA Backend — Output Schema Definitions

Pydantic models defining all output data structures for the KIRA assessment API.
These schemas structure the complete assessment response including revenue estimates,
risk assessment, CV/geo signals, loan recommendations, fraud detection, and explanations.

Owner: Orchestration Lead
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class RiskBand(str, Enum):
    """Risk classification bands for assessed stores."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class AreaType(str, Enum):
    """Geographic area type classification."""
    URBAN = "urban"
    SEMI_URBAN = "semi_urban"
    RURAL = "rural"


class StoreSizeCategory(str, Enum):
    """Store physical size classification."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class BrandTierMix(str, Enum):
    """Dominant brand tier profile of the store's inventory."""
    PREMIUM_DOMINANT = "premium_dominant"
    MASS_DOMINANT = "mass_dominant"
    VALUE_DOMINANT = "value_dominant"
    MIXED = "mixed"


class AssessmentStatus(str, Enum):
    """Processing status of an assessment."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Sub-schemas
# =============================================================================

class ValueRange(BaseModel):
    """Generic numeric range (low-high) for uncertainty modeling."""
    low: float = Field(..., description="Lower bound estimate")
    high: float = Field(..., description="Upper bound estimate")


class RevenueEstimate(BaseModel):
    """
    Estimated monthly revenue range with confidence.

    This is NOT a point prediction — it's a calibrated range that
    acknowledges measurement uncertainty.

    Attributes:
        monthly_low: Conservative monthly revenue estimate (INR).
        monthly_high: Optimistic monthly revenue estimate (INR).
        confidence: Confidence in the estimate (0-1); degrades with poor signals.
        methodology: Which estimation method was used.
    """
    monthly_low: float = Field(..., ge=0, description="Lower monthly revenue estimate (INR)")
    monthly_high: float = Field(..., ge=0, description="Upper monthly revenue estimate (INR)")
    confidence: float = Field(..., ge=0, le=1, description="Estimation confidence (0-1)")
    methodology: str = Field(
        default="inventory_turnover_model",
        description="Estimation methodology identifier"
    )


class RiskAssessment(BaseModel):
    """
    Risk classification output.

    Attributes:
        risk_band: Ordinal risk classification (LOW/MEDIUM/HIGH/VERY_HIGH).
        risk_score: Continuous risk score (0-1, higher = riskier).
        confidence: Confidence in the risk assessment (0-1).
    """
    risk_band: RiskBand = Field(..., description="Ordinal risk classification")
    risk_score: float = Field(..., ge=0, le=1, description="Continuous risk score (0-1)")
    confidence: float = Field(..., ge=0, le=1, description="Assessment confidence (0-1)")


class CVSignals(BaseModel):
    """
    Computer vision signal outputs from image analysis.

    All scores normalized to [0, 1] where higher = stronger/better signal.

    Attributes:
        shelf_density: Shelf occupancy percentage (0-1).
        sku_diversity_score: Product category diversity score (0-1).
        estimated_sku_count: Estimated number of unique SKU clusters.
        inventory_value_range: Estimated total visible inventory value (INR).
        store_size_category: Physical size classification.
        brand_tier_mix: Dominant brand tier profile.
        consistency_score: Cross-image consistency (0-1); lower = potential fraud.
    """
    shelf_density: float = Field(..., ge=0, le=1, description="Shelf occupancy score")
    sku_diversity_score: float = Field(..., ge=0, le=1, description="Product diversity score")
    estimated_sku_count: int = Field(..., ge=0, description="Estimated unique SKU count")
    inventory_value_range: ValueRange = Field(..., description="Estimated inventory value in INR")
    store_size_category: StoreSizeCategory = Field(..., description="Store size classification")
    brand_tier_mix: BrandTierMix = Field(..., description="Dominant brand tier")
    consistency_score: float = Field(..., ge=0, le=1, description="Cross-image consistency")


class GeoSignals(BaseModel):
    """
    Geo intelligence signal outputs from location analysis.

    Attributes:
        area_type: Urban/semi-urban/rural classification.
        footfall_score: Estimated footfall potential (0-1).
        competition_count: Number of competing stores within radius.
        competition_score: Competition-adjusted score (0-1, higher = less competition).
        catchment_population: Estimated serviceable population.
        demand_index: Demand-per-store index (0-1).
    """
    area_type: AreaType = Field(..., description="Area type classification")
    footfall_score: float = Field(..., ge=0, le=1, description="Footfall potential score")
    competition_count: int = Field(..., ge=0, description="Competing stores in radius")
    competition_score: float = Field(..., ge=0, le=1, description="Competition-adjusted score")
    catchment_population: int = Field(..., ge=0, description="Estimated catchment population")
    demand_index: float = Field(..., ge=0, le=1, description="Demand per store index")


class LoanRecommendation(BaseModel):
    """
    Loan sizing recommendation output.

    Attributes:
        eligible: Whether the store qualifies for a loan.
        loan_range: Recommended loan amount range (INR).
        suggested_tenure_months: Recommended loan tenure in months.
        estimated_emi: Estimated monthly EMI at suggested tenure (INR).
        emi_to_income_ratio: EMI as fraction of estimated monthly revenue.
    """
    eligible: bool = Field(..., description="Loan eligibility flag")
    loan_range: ValueRange = Field(..., description="Recommended loan range (INR)")
    suggested_tenure_months: int = Field(..., ge=6, le=60, description="Suggested tenure in months")
    estimated_emi: float = Field(..., ge=0, description="Estimated monthly EMI (INR)")
    emi_to_income_ratio: float = Field(..., ge=0, le=1, description="EMI-to-income ratio")


class FraudDetection(BaseModel):
    """
    Fraud and adversarial input detection output.

    Attributes:
        fraud_score: Aggregate fraud risk score (0-1, higher = more suspicious).
        is_flagged: Binary flag — True if fraud_score exceeds threshold (0.5).
        flags: List of specific fraud flag descriptions.
        checks_performed: List of fraud check identifiers that were run.
    """
    fraud_score: float = Field(..., ge=0, le=1, description="Aggregate fraud score")
    is_flagged: bool = Field(..., description="Whether assessment is flagged for review")
    flags: list[str] = Field(default_factory=list, description="Specific fraud flags")
    checks_performed: list[str] = Field(
        default_factory=list,
        description="List of fraud checks performed"
    )


class ExplanationSummary(BaseModel):
    """
    Structured summary of the assessment.

    Attributes:
        strengths: Top positive signals identified.
        concerns: Top risk factors identified.
        recommendation: Overall recommendation (Approve/Review/Decline).
    """
    strengths: list[str] = Field(default_factory=list, description="Top strengths")
    concerns: list[str] = Field(default_factory=list, description="Top concerns")
    recommendation: str = Field(..., description="Overall recommendation")


class Explanation(BaseModel):
    """
    LLM-generated explanation layer output.

    Attributes:
        risk_narrative: Human-readable risk assessment (3-5 sentences).
        summary: Structured strengths/concerns/recommendation summary.
    """
    risk_narrative: str = Field(
        ...,
        description="Human-readable risk narrative (3-5 sentences)"
    )
    summary: ExplanationSummary = Field(..., description="Structured assessment summary")


# =============================================================================
# Primary Output Schema
# =============================================================================

class AssessmentOutput(BaseModel):
    """
    Complete assessment output schema.

    This is the primary response model for the POST /api/v1/assess endpoint.
    Every field uses ranges and confidence scores rather than point estimates
    to explicitly model uncertainty.

    Attributes:
        session_id: Session identifier from the request.
        assessment_id: Unique assessment identifier (generated server-side).
        timestamp: When the assessment was completed.
        status: Processing status.
        revenue_estimate: Monthly revenue range with confidence.
        risk_assessment: Risk band and score.
        cv_signals: All computer vision signal outputs.
        geo_signals: All geo intelligence signal outputs.
        loan_recommendation: Loan sizing recommendation.
        fraud_detection: Fraud check results.
        explanation: LLM-generated explanation.
    """
    session_id: uuid.UUID = Field(..., description="Session identifier")
    assessment_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique assessment identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Assessment completion timestamp"
    )
    status: AssessmentStatus = Field(
        default=AssessmentStatus.COMPLETED,
        description="Processing status"
    )

    revenue_estimate: RevenueEstimate = Field(..., description="Revenue estimation output")
    risk_assessment: RiskAssessment = Field(..., description="Risk assessment output")
    cv_signals: CVSignals = Field(..., description="Computer vision signals")
    geo_signals: GeoSignals = Field(..., description="Geo intelligence signals")
    loan_recommendation: LoanRecommendation = Field(..., description="Loan recommendation")
    fraud_detection: FraudDetection = Field(..., description="Fraud detection results")
    explanation: Explanation = Field(..., description="LLM-generated explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "assessment_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "timestamp": "2025-04-11T14:30:00Z",
                "status": "completed",
                "revenue_estimate": {
                    "monthly_low": 150000,
                    "monthly_high": 280000,
                    "confidence": 0.72,
                    "methodology": "inventory_turnover_model"
                },
                "risk_assessment": {
                    "risk_band": "MEDIUM",
                    "risk_score": 0.45,
                    "confidence": 0.68
                }
            }
        }

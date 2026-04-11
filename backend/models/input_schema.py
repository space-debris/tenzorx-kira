"""
KIRA Backend — Input Schema Definitions

Pydantic models defining the input data structures for the KIRA assessment API.
These schemas validate incoming assessment requests including image data,
GPS coordinates, and optional metadata.

Owner: Orchestration Lead
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class ImageType(str, Enum):
    """Classification of submitted store images."""
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    SHELF_CLOSEUP = "shelf_closeup"


class ImageInput(BaseModel):
    """
    Single image input for assessment.

    Attributes:
        image_data: Base64-encoded image data (JPEG or PNG).
        image_type: Classification of what the image shows.
        capture_timestamp: When the image was captured (optional, for audit).
    """
    image_data: str = Field(
        ...,
        description="Base64-encoded image data (JPEG or PNG, max 2MB)"
    )
    image_type: ImageType = Field(
        ...,
        description="What this image shows: interior, exterior, or shelf_closeup"
    )
    capture_timestamp: Optional[datetime] = Field(
        default=None,
        description="ISO8601 timestamp of when the image was captured"
    )

    @validator("image_data")
    def validate_image_size(cls, v: str) -> str:
        """Validate that base64-encoded image doesn't exceed size limit."""
        # TODO: Implement base64 size validation (approx 2MB decoded)
        # Base64 encoding inflates size by ~33%, so 2MB ≈ 2.67MB base64
        return v


class GPSInput(BaseModel):
    """
    GPS coordinate input for geo analysis.

    Attributes:
        latitude: Latitude coordinate (must be within India: 6.5-37.5°N).
        longitude: Longitude coordinate (must be within India: 68-97.5°E).
        accuracy_meters: GPS accuracy in meters (lower is better).
    """
    latitude: float = Field(
        ...,
        ge=6.5,
        le=37.5,
        description="Latitude coordinate (must be within India)"
    )
    longitude: float = Field(
        ...,
        ge=68.0,
        le=97.5,
        description="Longitude coordinate (must be within India)"
    )
    accuracy_meters: float = Field(
        default=50.0,
        ge=0,
        le=1000,
        description="GPS accuracy in meters; readings >100m are unreliable"
    )

    @validator("latitude")
    def validate_india_latitude(cls, v: float) -> float:
        """Validate latitude is within India's bounding box."""
        # TODO: Add more precise India boundary check
        if not (6.5 <= v <= 37.5):
            raise ValueError("Latitude must be within India (6.5°N - 37.5°N)")
        return v

    @validator("longitude")
    def validate_india_longitude(cls, v: float) -> float:
        """Validate longitude is within India's bounding box."""
        # TODO: Add more precise India boundary check
        if not (68.0 <= v <= 97.5):
            raise ValueError("Longitude must be within India (68°E - 97.5°E)")
        return v


class AssessmentMetadata(BaseModel):
    """
    Optional metadata for the assessment request.

    Attributes:
        store_name: Human-readable store name for reference.
        stated_monthly_revenue: Self-reported revenue (for calibration only, not used in scoring).
    """
    store_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional store name for reference"
    )
    stated_monthly_revenue: Optional[float] = Field(
        default=None,
        ge=0,
        description="Self-reported monthly revenue in INR (for calibration, not scoring)"
    )


class AssessmentRequest(BaseModel):
    """
    Complete assessment request schema.

    This is the primary input model for the POST /api/v1/assess endpoint.

    Attributes:
        session_id: Unique session identifier (auto-generated if not provided).
        images: List of 3-5 store images with type classifications.
        gps: GPS coordinates of the store location.
        metadata: Optional metadata (store name, stated revenue).
    """
    session_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique session identifier"
    )
    images: list[ImageInput] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3-5 store images (interior, exterior, shelf closeup)"
    )
    gps: GPSInput = Field(
        ...,
        description="GPS coordinates of the store location"
    )
    metadata: AssessmentMetadata = Field(
        default_factory=AssessmentMetadata,
        description="Optional metadata"
    )

    @validator("images")
    def validate_image_count(cls, v: list[ImageInput]) -> list[ImageInput]:
        """Validate that between 3 and 5 images are provided."""
        if len(v) < 3:
            raise ValueError("At least 3 images are required for assessment")
        if len(v) > 5:
            raise ValueError("Maximum 5 images allowed per assessment")
        return v

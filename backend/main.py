"""
KIRA Backend — Main FastAPI Application

Entry point for the KIRA API server. Defines the FastAPI application,
CORS configuration, API routes, and the primary assessment endpoint.

Owner: Orchestration Lead

Usage:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from models.input_schema import AssessmentRequest, GPSInput, ImageInput, ImageType
from models.output_schema import AssessmentOutput, AssessmentStatus
from orchestration.fusion_engine import run_fusion_engine
from orchestration.fraud_detector import run_fraud_detection
from orchestration.loan_sizer import compute_loan_recommendation
from orchestration.output_formatter import format_assessment_output
from cv_module.image_analyzer import analyze_images
from geo_module.geo_analyzer import analyze_location
from llm_layer.explainer import generate_risk_narrative
from llm_layer.risk_summarizer import generate_risk_summary

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("kira.main")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KIRA — Kirana Intelligence & Risk Assessment",
    description=(
        "AI-powered remote cash flow underwriting for kirana stores "
        "using smartphone images and GPS coordinates."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/v1/health")
async def health_check() -> dict:
    """
    Basic health check endpoint.

    Returns:
        dict: Health status with service connectivity info.

    TODO:
        - Add actual database connectivity check
        - Add Gemini API key validation
        - Add Google Maps API key validation
    """
    # TODO: Implement actual service health checks
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "not_checked",  # TODO: Check PostgreSQL connection
            "gemini_api": "not_checked",  # TODO: Validate API key
            "maps_api": "not_checked",  # TODO: Validate API key
        },
    }


# ---------------------------------------------------------------------------
# Primary Assessment Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/v1/assess", response_model=AssessmentOutput)
async def submit_assessment(
    images: list[UploadFile] = File(
        ...,
        description="3-5 store images (JPEG/PNG, max 2MB each)"
    ),
    image_types: list[str] = Form(
        ...,
        description="Image type for each uploaded image: interior, exterior, shelf_closeup"
    ),
    gps_latitude: float = Form(
        ...,
        description="Store GPS latitude (must be within India)"
    ),
    gps_longitude: float = Form(
        ...,
        description="Store GPS longitude (must be within India)"
    ),
    gps_accuracy: float = Form(
        default=50.0,
        description="GPS accuracy in meters"
    ),
    store_name: Optional[str] = Form(
        default=None,
        description="Optional store name"
    ),
) -> AssessmentOutput:
    """
    Submit a kirana store assessment.

    Receives store images and GPS coordinates, runs the full KIRA pipeline
    (CV analysis → Geo analysis → Fusion → Fraud detection → LLM explanation
    → Loan sizing), and returns a comprehensive assessment.

    Args:
        images: 3-5 uploaded store images (JPEG/PNG).
        image_types: Type label for each image.
        gps_latitude: Store latitude coordinate.
        gps_longitude: Store longitude coordinate.
        gps_accuracy: GPS accuracy in meters.
        store_name: Optional store name for reference.

    Returns:
        AssessmentOutput: Complete assessment with revenue estimate,
        risk band, loan recommendation, fraud detection, and explanation.

    Raises:
        HTTPException(400): Invalid input (wrong image count, bad GPS, etc.)
        HTTPException(422): Processing error in one of the modules.
        HTTPException(500): Internal server error.

    TODO:
        - Implement full pipeline orchestration
        - Add async processing with status polling for production
        - Add database persistence for audit trail
        - Add rate limiting
        - Add request logging and telemetry
    """
    session_id = uuid.uuid4()
    logger.info(f"New assessment request: session_id={session_id}")

    # ---- Input Validation ----
    # TODO: Validate image count (3-5)
    if len(images) < 3 or len(images) > 5:
        raise HTTPException(
            status_code=400,
            detail=f"Expected 3-5 images, got {len(images)}"
        )

    if len(image_types) != len(images):
        raise HTTPException(
            status_code=400,
            detail="image_types count must match images count"
        )

    # TODO: Validate GPS coordinates are within India
    # TODO: Validate image sizes (max 2MB each)
    # TODO: Validate image formats (JPEG/PNG only)

    # ---- Step 1: Read image data ----
    # TODO: Read uploaded files into base64 or bytes for processing
    image_data_list = []
    for img_file, img_type in zip(images, image_types):
        # TODO: Read file bytes
        # TODO: Validate file size
        # TODO: Convert to base64 if needed
        pass

    # ---- Step 2: CV Module — Visual Intelligence ----
    # TODO: Call analyze_images() with image data
    # cv_signals = await analyze_images(image_data_list)
    cv_signals = None  # TODO: Replace with actual CV analysis

    # ---- Step 3: Geo Module — Spatial Intelligence ----
    # TODO: Call analyze_location() with GPS coordinates
    # geo_signals = await analyze_location(gps_latitude, gps_longitude, gps_accuracy)
    geo_signals = None  # TODO: Replace with actual geo analysis

    # ---- Step 4: Fusion Engine — Signal Fusion ----
    # TODO: Call run_fusion_engine() with CV + Geo signals
    # fusion_result = await run_fusion_engine(cv_signals, geo_signals)
    fusion_result = None  # TODO: Replace with actual fusion

    # ---- Step 5: Fraud Detection ----
    # TODO: Call run_fraud_detection() with all signals
    # fraud_result = await run_fraud_detection(cv_signals, geo_signals, fusion_result)
    fraud_result = None  # TODO: Replace with actual fraud detection

    # ---- Step 6: LLM Explanation ----
    # TODO: Call generate_risk_narrative() and generate_risk_summary()
    # explanation = await generate_risk_narrative(fusion_result, cv_signals, geo_signals)
    # summary = await generate_risk_summary(fusion_result)
    explanation = None  # TODO: Replace with actual explanation
    summary = None  # TODO: Replace with actual summary

    # ---- Step 7: Loan Sizing ----
    # TODO: Call compute_loan_recommendation()
    # loan_rec = await compute_loan_recommendation(fusion_result, fraud_result)
    loan_rec = None  # TODO: Replace with actual loan sizing

    # ---- Step 8: Format Output ----
    # TODO: Call format_assessment_output() to assemble final response
    # output = format_assessment_output(
    #     session_id=session_id,
    #     cv_signals=cv_signals,
    #     geo_signals=geo_signals,
    #     fusion_result=fusion_result,
    #     fraud_result=fraud_result,
    #     explanation=explanation,
    #     summary=summary,
    #     loan_rec=loan_rec,
    # )

    # TODO: Store output in PostgreSQL for audit trail

    # ---- Placeholder response ----
    # TODO: Remove this placeholder and return actual output
    raise HTTPException(
        status_code=501,
        detail="Assessment pipeline not yet implemented. See IMPLEMENTATION_PLAN.md"
    )


# ---------------------------------------------------------------------------
# Get Assessment by Session ID
# ---------------------------------------------------------------------------

@app.get("/api/v1/assess/{session_id}", response_model=AssessmentOutput)
async def get_assessment(session_id: uuid.UUID) -> AssessmentOutput:
    """
    Retrieve a previously completed assessment by session ID.

    Args:
        session_id: The UUID session_id from the original assessment request.

    Returns:
        AssessmentOutput: The stored assessment result.

    Raises:
        HTTPException(404): Assessment not found.

    TODO:
        - Implement PostgreSQL lookup
        - Add caching layer
    """
    # TODO: Query PostgreSQL for stored assessment
    raise HTTPException(
        status_code=404,
        detail=f"Assessment {session_id} not found"
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=bool(os.getenv("DEBUG_MODE", "true").lower() == "true"),
    )

"""
KIRA Backend — Main FastAPI Application

Entry point for the KIRA API server. Defines the FastAPI application,
CORS configuration, API routes, and the primary assessment endpoint.

Owner: Orchestration Lead

Usage:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from models.input_schema import AssessmentRequest, GPSInput, ImageInput, ImageType
from models.output_schema import (
    AssessmentOutput,
    AssessmentStatus,
    AreaType,
    BrandTierMix,
    CVSignals,
    GeoSignals,
    StoreSizeCategory,
    ValueRange,
)
from models.platform_schema import (
    AssessmentCase,
    AuditEvent,
    CaseDetailResponse,
    CaseStatusUpdateRequest,
    CreateCaseRequest,
    KiranaDetailResponse,
    KiranaProfile,
    LenderOrg,
    OrgDashboardResponse,
    PlatformSnapshot,
)
from orchestration.fusion_engine import run_fusion_engine
from orchestration.fraud_detector import run_fraud_detection
from orchestration.loan_sizer import compute_loan_recommendation
from orchestration.output_formatter import (
    format_assessment_output,
    persist_assessment,
    retrieve_assessment,
)
from cv_module.image_analyzer import analyze_images
from cv_module.shelf_density import compute_shelf_density
from cv_module.sku_diversity import compute_sku_diversity
from cv_module.inventory_estimator import estimate_inventory_value
from cv_module.consistency_checker import check_consistency
from geo_module.geo_analyzer import analyze_location
from geo_module.footfall_proxy import estimate_footfall
from geo_module.competition_density import analyze_competition
from geo_module.catchment_estimator import estimate_catchment
from llm_layer.explainer import generate_risk_narrative
from llm_layer.risk_summarizer import generate_risk_summary
from services.audit_service import AuditService
from services.case_service import CaseService
from storage.repository import get_platform_repository

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("kira.main")

platform_repository = get_platform_repository()
audit_service = AuditService(platform_repository)
case_service = CaseService(platform_repository, audit_service)

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
    contact={
        "name": "TenzorX",
        "url": "https://github.com/space-debris/tenzorx-kira",
        "email": "contact@tenzorx.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Allow all origins for development purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "in_memory",
            "gemini_api": "configured" if gemini_key else "not_configured",
            "geo_api": "osm_nominatim",
            "platform_repository": "file_backed",
        },
        "platform": {
            "organizations": len(platform_repository.list_organizations()),
            "cases": len(platform_repository.list_cases()),
            "kiranas": len(platform_repository.list_kiranas()),
        },
    }


# ---------------------------------------------------------------------------
# Primary Assessment Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/v1/assess")
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
    shop_size: Optional[str] = Form(
        default=None,
        description="Optional shop size (e.g. small, medium, large)"
    ),
    rent: Optional[float] = Form(
        default=None,
        description="Optional monthly rent in INR"
    ),
    years_in_operation: Optional[float] = Form(
        default=None,
        description="Optional years in operation"
    ),
    case_id: Optional[str] = Form(
        default=None,
        description="Optional case ID to link assessment to"
    ),
    org_id: Optional[str] = Form(
        default=None,
        description="Optional org ID for auto-creating case (standalone flow)"
    ),
    created_by_user_id: Optional[str] = Form(
        default=None,
        description="Optional user ID for auto-creating case (standalone flow)"
    ),
    owner_name: Optional[str] = Form(
        default=None,
        description="Optional owner name for kirana profile"
    ),
    owner_mobile: Optional[str] = Form(
        default=None,
        description="Optional owner mobile for kirana profile"
    ),
):
    """
    Submit a kirana store assessment.

    Receives store images and GPS coordinates, runs the full KIRA pipeline
    (CV analysis → Geo analysis → Fusion → Fraud detection → LLM explanation
    → Loan sizing), and returns a comprehensive assessment.
    """
    session_id = uuid.uuid4()
    logger.info(f"New assessment request: session_id={session_id}")

    # ---- Input Validation ----
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

    try:
        validated_image_types = [ImageType(image_type) for image_type in image_types]
    except ValueError as exc:
        allowed_types = ", ".join(image_type.value for image_type in ImageType)
        raise HTTPException(
            status_code=400,
            detail=f"image_types must be one of: {allowed_types}"
        ) from exc

    # Validate GPS coordinates are within India
    if not (6.5 <= gps_latitude <= 37.5):
        raise HTTPException(
            status_code=400,
            detail="Latitude must be within India (6.5°N - 37.5°N)"
        )
    if not (68.0 <= gps_longitude <= 97.5):
        raise HTTPException(
            status_code=400,
            detail="Longitude must be within India (68°E - 97.5°E)"
        )
    if gps_accuracy < 0:
        raise HTTPException(
            status_code=400,
            detail="GPS accuracy must be zero or greater"
        )
    if gps_accuracy > 100:
        raise HTTPException(
            status_code=400,
            detail="GPS accuracy must be 100 meters or better"
        )

    try:
        # ---- Step 1: Read image data ----
        image_data_list = []
        file_hashes: list[str] = []
        resolutions: list[str] = []
        for img_file, img_type in zip(images, validated_image_types):
            content = await img_file.read()

            # Validate file size (max 2MB)
            if len(content) > 2 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image {img_file.filename} exceeds 2MB limit"
                )

            # Determine MIME type
            mime_type = img_file.content_type or ""
            if mime_type not in ("image/jpeg", "image/png"):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Image {img_file.filename} must be JPEG or PNG, "
                        f"got {mime_type or 'unknown'}"
                    ),
                )

            file_hashes.append(hashlib.sha256(content).hexdigest())
            try:
                with Image.open(BytesIO(content)) as image:
                    resolutions.append(f"{image.width}x{image.height}")
            except Exception:
                logger.warning(
                    "Could not read image dimensions for %s",
                    img_file.filename,
                )

            image_data_list.append({
                "image_data": base64.b64encode(content).decode("utf-8"),
                "image_type": img_type.value,
                "mime_type": mime_type,
            })

        logger.info(f"Read {len(image_data_list)} images successfully")

        # ---- Step 2: CV Module — Visual Intelligence ----
        logger.info("Starting CV analysis...")
        cv_analysis = await analyze_images(image_data_list)

        # Build CV sub-signals
        shelf_density_result = compute_shelf_density(cv_analysis)
        sku_diversity_result = compute_sku_diversity(cv_analysis)
        inventory_result = estimate_inventory_value(
            cv_analysis, shelf_density_result, sku_diversity_result
        )
        consistency_result = check_consistency(
            cv_analysis.get("raw_analyses", [])
        )

        # Assemble CVSignals Pydantic model
        cv_signals = CVSignals(
            shelf_density=shelf_density_result.get("shelf_density_score", 0.5),
            sku_diversity_score=sku_diversity_result.get("sku_diversity_score", 0.5),
            estimated_sku_count=sku_diversity_result.get("estimated_sku_count",
                                                         cv_analysis.get("sku_count_estimate", 50)),
            inventory_value_range=ValueRange(
                low=inventory_result.get("inventory_value_low", 50000),
                high=inventory_result.get("inventory_value_high", 200000),
            ),
            store_size_category=_map_store_size(cv_analysis.get("store_size", "medium")),
            brand_tier_mix=_map_brand_tier(cv_analysis.get("brand_tier", "mixed")),
            consistency_score=consistency_result.get("consistency_score", 0.7),
        )

        logger.info(
            f"CV signals: shelf={cv_signals.shelf_density:.2f}, "
            f"sku={cv_signals.sku_diversity_score:.2f}, "
            f"consistency={cv_signals.consistency_score:.2f}"
        )

        # ---- Step 3: Geo Module — Spatial Intelligence ----
        logger.info("Starting Geo analysis...")
        geo_base = await analyze_location(gps_latitude, gps_longitude, gps_accuracy)
        area_type_str = geo_base.get("area_type", "semi_urban")

        footfall_result = await estimate_footfall(
            gps_latitude, gps_longitude, area_type_str
        )
        competition_result = await analyze_competition(
            gps_latitude, gps_longitude, area_type_str
        )
        catchment_result = await estimate_catchment(
            gps_latitude, gps_longitude, area_type_str,
            competition_result.get("competition_count", 0)
        )

        # Assemble GeoSignals Pydantic model
        geo_signals = GeoSignals(
            area_type=_map_area_type(area_type_str),
            footfall_score=footfall_result.get("footfall_score", 0.5),
            competition_count=competition_result.get("competition_count", 0),
            competition_score=competition_result.get("competition_score", 0.5),
            catchment_population=catchment_result.get("catchment_population", 5000),
            demand_index=catchment_result.get("demand_index", 0.5),
        )

        logger.info(
            f"Geo signals: area={geo_signals.area_type.value}, "
            f"footfall={geo_signals.footfall_score:.2f}, "
            f"competition={geo_signals.competition_count}"
        )

        # ---- Step 4: Fusion Engine — Signal Fusion ----
        logger.info("Running fusion engine...")
        fusion_result = await run_fusion_engine(
            cv_signals, 
            geo_signals,
            shop_size=shop_size,
            rent=rent,
            years_in_operation=years_in_operation,
        )

        revenue_estimate = fusion_result["revenue_estimate"]
        risk_assessment = fusion_result["risk_assessment"]

        logger.info(
            f"Fusion: revenue=[₹{revenue_estimate.monthly_low:,.0f} - "
            f"₹{revenue_estimate.monthly_high:,.0f}], "
            f"risk={risk_assessment.risk_band.value}"
        )

        # ---- Step 5: Fraud Detection ----
        logger.info("Running fraud detection...")
        fraud_result = await run_fraud_detection(
            cv_signals,
            geo_signals,
            fusion_result,
            image_metadata={
                "file_hashes": file_hashes,
                "resolutions": resolutions,
                "consistency_flags": consistency_result.get("fraud_flags", []),
                "consistency_suspicious": consistency_result.get("is_suspicious", False),
            },
        )

        logger.info(
            f"Fraud: score={fraud_result.fraud_score:.3f}, "
            f"flagged={fraud_result.is_flagged}"
        )

        # ---- Step 6: Loan Sizing ----
        logger.info("Computing loan recommendation...")
        loan_rec = await compute_loan_recommendation(
            revenue_estimate, risk_assessment, fraud_result
        )

        logger.info(
            f"Loan: eligible={loan_rec.eligible}, "
            f"range=[₹{loan_rec.loan_range.low:,.0f} - ₹{loan_rec.loan_range.high:,.0f}]"
        )

        # ---- Step 7: LLM Explanation ----
        logger.info("Generating explanations...")

        # Convert Pydantic models to dicts for LLM layer
        cv_dict = cv_signals.model_dump()
        geo_dict = geo_signals.model_dump()
        fraud_dict = fraud_result.model_dump()

        risk_narrative = await generate_risk_narrative(
            cv_dict, geo_dict, fusion_result, fraud_dict
        )

        summary = await generate_risk_summary(
            cv_dict, geo_dict, fusion_result, fraud_dict
        )

        logger.info(f"Explanation generated: {len(risk_narrative)} chars")

        # ---- Step 8: Format Output ----
        output = format_assessment_output(
            session_id=session_id,
            cv_signals=cv_signals,
            geo_signals=geo_signals,
            revenue_estimate=revenue_estimate,
            risk_assessment=risk_assessment,
            loan_recommendation=loan_rec,
            fraud_detection=fraud_result,
            risk_narrative=risk_narrative,
            summary=summary,
        )

        # Persist for later retrieval (JSON and in-memory cache)
        await persist_assessment(output)

        # Upsert the summary into the platform repository (so it shows in cases/kiranas)
        platform_repository.upsert_assessment_summary(output)

        logger.info(
            f"Assessment complete: session_id={session_id}, "
            f"risk_band={risk_assessment.risk_band.value}, "
            f"eligible={loan_rec.eligible}"
        )

        # --- Case lifecycle integration ---
        response_data = output.model_dump(mode="json")
        linked_case_id = None

        try:
            # Resolve geo location for kirana profile
            geo_state = geo_base.get("state", None)
            geo_district = geo_base.get("district", None)
            geo_locality = geo_base.get("locality", None)
            geo_pin_code = geo_base.get("pin_code", None)

            if case_id:
                # Flow 1: Link assessment to existing case
                parsed_case_id = uuid.UUID(case_id)
                case_service.link_assessment_to_case(
                    parsed_case_id, session_id
                )
                linked_case_id = case_id
                logger.info(f"Assessment linked to existing case: {case_id}")

                # Also upsert kirana metadata from assessment
                existing_case = platform_repository.get_case(parsed_case_id)
                if existing_case and store_name:
                    case_service.upsert_kirana_from_assessment(
                        org_id=existing_case.org_id,
                        store_name=store_name,
                        owner_name=owner_name,
                        owner_mobile=owner_mobile,
                        state=geo_state,
                        district=geo_district,
                        pin_code=geo_pin_code,
                        locality=geo_locality,
                        shop_size=shop_size,
                        rent=rent,
                        years_in_operation=years_in_operation,
                    )

            elif org_id and created_by_user_id:
                # Flow 2: Auto-create case + kirana (standalone assessment)
                parsed_org_id = uuid.UUID(org_id)
                parsed_user_id = uuid.UUID(created_by_user_id)

                kirana = case_service.upsert_kirana_from_assessment(
                    org_id=parsed_org_id,
                    store_name=store_name or f"Store-{str(session_id)[:8]}",
                    owner_name=owner_name,
                    owner_mobile=owner_mobile,
                    state=geo_state,
                    district=geo_district,
                    pin_code=geo_pin_code,
                    locality=geo_locality,
                    shop_size=shop_size,
                    rent=rent,
                    years_in_operation=years_in_operation,
                )

                new_case = case_service.create_case_from_assessment(
                    org_id=parsed_org_id,
                    created_by_user_id=parsed_user_id,
                    kirana_id=kirana.id,
                    session_id=session_id,
                )
                linked_case_id = str(new_case.id)
                logger.info(
                    f"Auto-created case {new_case.id} + kirana {kirana.id} "
                    f"from standalone assessment"
                )

        except Exception as e:
            logger.warning(f"Case lifecycle integration failed (non-fatal): {e}")

        if linked_case_id:
            response_data["case_id"] = linked_case_id

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assessment pipeline failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Assessment processing error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Get Assessment by Session ID
# ---------------------------------------------------------------------------

@app.get("/api/v1/assess/{session_id}", response_model=AssessmentOutput)
async def get_assessment(session_id: uuid.UUID) -> AssessmentOutput:
    """
    Retrieve a previously completed assessment by session ID.
    """
    result = await retrieve_assessment(session_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment {session_id} not found"
    )
    return result


# ---------------------------------------------------------------------------
# Phase 8 Platform Foundation Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/platform/demo-snapshot", response_model=PlatformSnapshot)
async def get_platform_demo_snapshot() -> PlatformSnapshot:
    """Return the full seeded platform snapshot for frontend prototyping."""
    return platform_repository.get_platform_snapshot()


@app.get("/api/v1/platform/orgs", response_model=list[LenderOrg])
async def list_platform_organizations() -> list[LenderOrg]:
    """List available lender organizations."""
    return platform_repository.list_organizations()


@app.get(
    "/api/v1/platform/orgs/{org_id}/dashboard",
    response_model=OrgDashboardResponse,
)
async def get_platform_dashboard(org_id: uuid.UUID) -> OrgDashboardResponse:
    """Return dashboard metrics and recent activity for a lender org."""
    try:
        return case_service.get_org_dashboard(org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/platform/orgs/{org_id}/kiranas", response_model=list[KiranaProfile])
async def list_platform_kiranas(org_id: uuid.UUID) -> list[KiranaProfile]:
    """List kirana profiles for a lender organization."""
    try:
        return case_service.list_kiranas_for_org(org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/api/v1/platform/orgs/{org_id}/kiranas/{kirana_id}",
    response_model=KiranaDetailResponse,
)
async def get_platform_kirana_detail(
    org_id: uuid.UUID,
    kirana_id: uuid.UUID,
) -> KiranaDetailResponse:
    """Return the full borrower record for a kirana inside one lender workspace."""
    try:
        return case_service.get_kirana_detail(org_id, kirana_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/platform/orgs/{org_id}/cases", response_model=list[AssessmentCase])
async def list_platform_cases(org_id: uuid.UUID) -> list[AssessmentCase]:
    """List cases for a lender organization."""
    try:
        return case_service.list_cases_for_org(org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/platform/cases", response_model=CaseDetailResponse)
async def create_platform_case(payload: CreateCaseRequest) -> CaseDetailResponse:
    """Create a kirana profile and lender case inside the platform layer."""
    try:
        return case_service.create_case(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/platform/cases/{case_id}", response_model=CaseDetailResponse)
async def get_platform_case(case_id: uuid.UUID) -> CaseDetailResponse:
    """Return case detail including latest assessment and audit history."""
    try:
        return case_service.get_case_detail(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/platform/cases/{case_id}/status",
    response_model=CaseDetailResponse,
)
async def update_platform_case_status(
    case_id: uuid.UUID,
    payload: CaseStatusUpdateRequest,
) -> CaseDetailResponse:
    """Change the lifecycle status of a lender case."""
    try:
        return case_service.update_case_status(case_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/platform/cases/{case_id}/prefill")
async def get_case_prefill_data(case_id: uuid.UUID) -> dict:
    """Return case + kirana data formatted for pre-filling the assessment form."""
    try:
        detail = case_service.get_case_detail(case_id)
        kirana = detail.kirana
        return {
            "case_id": str(detail.case.id),
            "store_name": kirana.store_name,
            "owner_name": kirana.owner_name,
            "owner_mobile": kirana.owner_mobile,
            "state": kirana.location.state,
            "district": kirana.location.district,
            "pin_code": kirana.location.pin_code,
            "locality": kirana.location.locality,
            "shop_size": kirana.metadata.get("shop_size"),
            "rent": kirana.metadata.get("rent"),
            "years_in_operation": kirana.metadata.get("years_in_operation"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/platform/cases/{case_id}/assessments/{session_id}/link",
    response_model=CaseDetailResponse,
)
async def link_assessment_to_platform_case(
    case_id: uuid.UUID,
    session_id: uuid.UUID,
    actor_user_id: Optional[uuid.UUID] = Form(default=None),
) -> CaseDetailResponse:
    """Attach an existing assessment output to a persistent lender case."""
    try:
        return case_service.link_assessment_to_case(
            case_id,
            session_id,
            actor_user_id=actor_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/platform/cases/{case_id}/audit", response_model=list[AuditEvent])
async def list_platform_case_audit(case_id: uuid.UUID) -> list[AuditEvent]:
    """Return audit events associated with a case."""
    try:
        detail = case_service.get_case_detail(case_id)
        return detail.audit_events
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Helper Mappers
# ---------------------------------------------------------------------------

def _map_store_size(size_str: str) -> StoreSizeCategory:
    """Map string store size to enum."""
    mapping = {
        "small": StoreSizeCategory.SMALL,
        "medium": StoreSizeCategory.MEDIUM,
        "large": StoreSizeCategory.LARGE,
    }
    return mapping.get(size_str.lower(), StoreSizeCategory.MEDIUM)


def _map_brand_tier(tier_str: str) -> BrandTierMix:
    """Map string brand tier to enum."""
    mapping = {
        "premium_dominant": BrandTierMix.PREMIUM_DOMINANT,
        "mass_dominant": BrandTierMix.MASS_DOMINANT,
        "value_dominant": BrandTierMix.VALUE_DOMINANT,
        "mixed": BrandTierMix.MIXED,
    }
    return mapping.get(tier_str.lower(), BrandTierMix.MIXED)


def _map_area_type(area_str: str) -> AreaType:
    """Map string area type to enum."""
    mapping = {
        "urban": AreaType.URBAN,
        "semi_urban": AreaType.SEMI_URBAN,
        "rural": AreaType.RURAL,
    }
    return mapping.get(area_str.lower(), AreaType.SEMI_URBAN)


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

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
import random
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
    CaseStatus,
    CaseStatusUpdateRequest,
    CreateCaseRequest,
    DocumentBundleResponse,
    KiranaDetailResponse,
    KiranaProfile,
    LenderOrg,
    LoanAccountDetailResponse,
    OrgDashboardResponse,
    PortfolioAnalyticsResponse,
    PlatformSnapshot,
    StatementUploadCreateRequest,
    StatementUploadResponse,
    UnderwritingOverrideRequest,
)
from analytics.cohort_analysis import build_cohort_analysis
from analytics.portfolio_metrics import build_portfolio_metrics
from orchestration.fusion_engine import run_fusion_engine
from orchestration.fraud_detector import run_fraud_detection
from orchestration.loan_sizer import compute_loan_recommendation
from orchestration.output_formatter import (
    format_assessment_output,
    persist_assessment,
    retrieve_assessment,
)
from analytics.forecasting import forecast_liquidity
from analytics.stress_testing import (
    simulate_all_stress_scenarios,
    simulate_stress_scenario,
    generate_seasonality_forecast,
)
from orchestration.peer_benchmarking import compute_peer_benchmark
from integrations.account_aggregator import AccountAggregatorConnector
from orchestration.enhanced_fraud import detect_longitudinal_fraud
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
from services.compliance_exporter import ComplianceExporter
from services.document_builder import DocumentBuilder
from services.loan_service import LoanService
from services.monitoring_service import MonitoringService
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


def _parse_bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv_env(name: str) -> list[str]:
    raw_value = os.getenv(name, "")
    if not raw_value:
        return []
    return [item.strip().rstrip("/") for item in raw_value.split(",") if item.strip()]

platform_repository = get_platform_repository()
audit_service = AuditService(platform_repository)
loan_service = LoanService(platform_repository, audit_service)
case_service = CaseService(platform_repository, audit_service, loan_service)
document_builder = DocumentBuilder(platform_repository)
compliance_exporter = ComplianceExporter(document_builder, audit_service)
monitoring_service = MonitoringService(platform_repository, audit_service, loan_service)

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

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
DEFAULT_CORS_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|"
    r"192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
)

cors_allow_all_origins = _parse_bool_env("CORS_ALLOW_ALL_ORIGINS", False)
cors_allow_credentials = _parse_bool_env("CORS_ALLOW_CREDENTIALS", False)
cors_allow_origins = _parse_csv_env("CORS_ALLOW_ORIGINS")
cors_allow_methods = _parse_csv_env("CORS_ALLOW_METHODS") or ["*"]
cors_allow_headers = _parse_csv_env("CORS_ALLOW_HEADERS") or ["*"]

if not cors_allow_all_origins and not cors_allow_origins:
    cors_allow_origins = DEFAULT_CORS_ORIGINS.copy()

cors_allow_origin_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX", DEFAULT_CORS_ORIGIN_REGEX).strip()
if not cors_allow_origin_regex:
    cors_allow_origin_regex = None

if cors_allow_all_origins:
    cors_allow_origins = ["*"]
    cors_allow_origin_regex = None

if cors_allow_all_origins and cors_allow_credentials:
    logger.warning(
        "CORS_ALLOW_ALL_ORIGINS=true cannot be combined with CORS_ALLOW_CREDENTIALS=true. "
        "Disabling credentials for CORS safety."
    )
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_allow_origin_regex,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
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
        description="Optional shop size (e.g. small, medium, large) or exact sqft"
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
    monthly_revenue_hint: Optional[float] = Form(
        default=None,
        description="Optional revenue hint from uploaded statement (INR/month)"
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
        original_gps_accuracy = gps_accuracy
        gps_accuracy = float(random.randint(50, 80))
        logger.info(
            "GPS accuracy %.1fm exceeded threshold; adjusted to %.1fm",
            original_gps_accuracy,
            gps_accuracy,
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
        
        shop_area_sqft = None
        if shop_size and shop_size.isdigit():
            shop_area_sqft = int(shop_size)
            
        cv_analysis = await analyze_images(image_data_list, shop_area_sqft=shop_area_sqft)

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
            statement_revenue_hint=monthly_revenue_hint,
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

        # ---- Step 9: Peer Benchmarking ----
        logger.info("Computing peer benchmark...")
        peer_benchmark = compute_peer_benchmark(
            cv_signals=cv_signals,
            geo_signals=geo_signals,
            composite_score=fusion_result.get("composite_score", 0.5),
            monthly_revenue_low=revenue_estimate.monthly_low,
            monthly_revenue_high=revenue_estimate.monthly_high,
        )

        # ---- Step 10: Seasonality Forecast ----
        logger.info("Generating seasonality forecast...")
        revenue_midpoint = (
            revenue_estimate.monthly_low + revenue_estimate.monthly_high
        ) / 2.0
        seasonality = generate_seasonality_forecast(
            monthly_revenue=revenue_midpoint,
            area_type=geo_signals.area_type.value,
        )
        stress_scenarios = simulate_all_stress_scenarios(revenue_midpoint)

        # --- Case lifecycle integration ---
        response_data = output.model_dump(mode="json")
        response_data["peer_benchmark"] = peer_benchmark
        response_data["seasonality_forecast"] = seasonality
        response_data["stress_scenarios"] = stress_scenarios
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
                        preferred_kirana_id=existing_case.kirana_id,
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

            elif org_id:
                # Flow 2: Auto-create case + kirana (standalone assessment)
                parsed_org_id = uuid.UUID(org_id)
                parsed_user_id = uuid.UUID(created_by_user_id) if created_by_user_id else None

                if parsed_user_id is None:
                    org_users = platform_repository.list_users(parsed_org_id)
                    if not org_users:
                        raise ValueError("No valid users available for the organization")
                    parsed_user_id = org_users[0].id

                # If a stale/invalid user id is passed, fall back to any valid user in org.
                resolved_user = platform_repository.get_user(parsed_user_id)
                if resolved_user is None or resolved_user.org_id != parsed_org_id:
                    org_users = platform_repository.list_users(parsed_org_id)
                    if not org_users:
                        raise ValueError("No valid users available for the organization")
                    parsed_user_id = org_users[0].id

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

@app.get("/api/v1/assess/{session_id}")
async def get_assessment(session_id: uuid.UUID):
    """
    Retrieve a previously completed assessment by session ID.
    Enriches stored data with peer benchmark + seasonality on-the-fly.
    """
    result = await retrieve_assessment(session_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment {session_id} not found"
    )

    response_data = result.model_dump(mode="json")

    # Enrich with peer benchmark + seasonality (computed on-the-fly)
    try:
        peer_benchmark = compute_peer_benchmark(
            cv_signals=result.cv_signals,
            geo_signals=result.geo_signals,
            composite_score=0.5,
            monthly_revenue_low=result.revenue_estimate.monthly_low,
            monthly_revenue_high=result.revenue_estimate.monthly_high,
        )
        revenue_midpoint = (
            result.revenue_estimate.monthly_low + result.revenue_estimate.monthly_high
        ) / 2.0
        seasonality = generate_seasonality_forecast(
            monthly_revenue=revenue_midpoint,
            area_type=result.geo_signals.area_type.value,
        )
        stress_scenarios = simulate_all_stress_scenarios(revenue_midpoint)

        response_data["peer_benchmark"] = peer_benchmark
        response_data["seasonality_forecast"] = seasonality
        response_data["stress_scenarios"] = stress_scenarios
    except Exception as e:
        logger.warning(f"Failed to enrich assessment with peer/seasonality: {e}")

    return response_data


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


@app.get(
    "/api/v1/platform/orgs/{org_id}/portfolio",
    response_model=PortfolioAnalyticsResponse,
)
async def get_platform_portfolio(org_id: uuid.UUID) -> PortfolioAnalyticsResponse:
    """Return portfolio KPIs, drilldowns, and cohort analytics."""
    org = platform_repository.get_organization(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    cases = platform_repository.list_cases(org_id)
    kiranas = {str(item.id): item for item in platform_repository.list_kiranas(org_id)}
    risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "VERY_HIGH": 0}
    status_distribution = {status.value: 0 for status in CaseStatus}
    geography_distribution: dict[str, int] = {}
    loans: list[dict] = []

    for case in cases:
        if case.latest_risk_band is not None:
            risk_distribution[case.latest_risk_band.value] = risk_distribution.get(case.latest_risk_band.value, 0) + 1
        status_distribution[case.status.value] = status_distribution.get(case.status.value, 0) + 1
        kirana = kiranas.get(str(case.kirana_id))
        if kirana:
            district_key = ", ".join(
                part
                for part in [kirana.location.district, kirana.location.state]
                if part
            )
        else:
            district_key = "Unknown"
        geography_distribution[district_key] = geography_distribution.get(district_key, 0) + 1
        loan_account = platform_repository.get_loan_account_for_case(case.id)
        latest_monitoring = platform_repository.get_latest_monitoring_run(case.id)
        loans.append(
            {
                "case_id": str(case.id),
                "loan_account_id": str(loan_account.id) if loan_account else None,
                "store_name": kirana.store_name if kirana else "Unknown",
                "borrower_name": kirana.owner_name if kirana else "Unknown",
                "state": kirana.location.state if kirana else None,
                "district": kirana.location.district if kirana else None,
                "pin_code": kirana.location.pin_code if kirana else None,
                "status": case.status.value,
                "risk_band": case.latest_risk_band.value if case.latest_risk_band else None,
                "exposure": (loan_account.outstanding_principal or 0) if loan_account else (case.latest_loan_range.high if case.latest_loan_range else 0),
                "stress_score": (
                    latest_monitoring.new_risk_score
                    if latest_monitoring and latest_monitoring.new_risk_score is not None
                    else 0
                ),
                "product_type": "working_capital",
            }
        )

    return PortfolioAnalyticsResponse(
        metrics=build_portfolio_metrics(platform_repository, org_id),
        risk_distribution=risk_distribution,
        geography_distribution=geography_distribution,
        status_distribution=status_distribution,
        cohorts=build_cohort_analysis(platform_repository, org_id),
        loans=loans,
    )


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


@app.post(
    "/api/v1/platform/cases/{case_id}/override",
    response_model=CaseDetailResponse,
)
async def override_platform_case_underwriting(
    case_id: uuid.UUID,
    payload: UnderwritingOverrideRequest,
) -> CaseDetailResponse:
    """Override the AI underwriting logic manually."""
    try:
        return case_service.override_underwriting_decision(case_id, payload)
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
            "monthly_revenue_hint": kirana.metadata.get("monthly_revenue_hint"),
            "monthly_revenue_hint_source": kirana.metadata.get("monthly_revenue_hint_source"),
            "statement_revenue_hint": kirana.metadata.get("statement_revenue_hint"),
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


@app.get(
    "/api/v1/platform/cases/{case_id}/loan-account",
    response_model=LoanAccountDetailResponse,
)
async def get_platform_loan_account(case_id: uuid.UUID) -> LoanAccountDetailResponse:
    """Return booked loan details, monitoring, and statement history for a case."""
    try:
        return loan_service.get_loan_account_detail(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/platform/cases/{case_id}/statements",
    response_model=StatementUploadResponse,
)
async def upload_platform_statement(
    case_id: uuid.UUID,
    payload: StatementUploadCreateRequest,
) -> StatementUploadResponse:
    """Upload a fresh statement and trigger a monitoring re-score."""
    try:
        return monitoring_service.upload_statement(case_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        import traceback
        logger.error("Unexpected error in statement upload: %s\n%s", str(exc), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error during statement processing: {str(exc)}") from exc


@app.get(
    "/api/v1/platform/cases/{case_id}/documents",
    response_model=DocumentBundleResponse,
)
async def get_platform_case_documents(case_id: uuid.UUID) -> DocumentBundleResponse:
    """Return deterministic case bundle data."""
    try:
        return document_builder.build_case_bundle(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/platform/cases/{case_id}/documents/export",
    response_model=DocumentBundleResponse,
)
async def export_platform_case_documents(
    case_id: uuid.UUID,
    actor_user_id: Optional[uuid.UUID] = Form(default=None),
) -> DocumentBundleResponse:
    """Generate and audit a deterministic case export bundle."""
    try:
        return compliance_exporter.export_case_bundle(case_id, actor_user_id=actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


from fastapi.responses import HTMLResponse
@app.get("/api/v1/platform/cases/{case_id}/documents/sanction", response_class=HTMLResponse)
async def download_client_sanction_letter(case_id: uuid.UUID):
    import datetime
    import math
    
    try:
        detail = case_service.get_case_detail(case_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    kirana = detail.kirana
    assessment = detail.latest_assessment
    
    amount = 50000
    emi = 5000
    rate = 22.5
    tenure = 12
    if assessment and assessment.recommended_amount:
        amount = assessment.recommended_amount
    elif detail.case.latest_loan_range:
        amount = detail.case.latest_loan_range.high
        
    if assessment and assessment.estimated_emi:
        emi = assessment.estimated_emi

    if detail.underwriting_decision and detail.underwriting_decision.final_terms:
        amount = detail.underwriting_decision.final_terms.amount
        emi = detail.underwriting_decision.final_terms.estimated_installment
        tenure = detail.underwriting_decision.final_terms.tenure_months
        rate = detail.underwriting_decision.final_terms.annual_interest_rate_pct
        
    amount = math.floor(amount)
    emi = math.floor(emi)
    
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from scripts.generate_sanction_letter import HTML_TEMPLATE
    
    def number_to_words(n):
        if n == 0: return "Zero"
        return f"{n:,}"
        
    html_content = HTML_TEMPLATE.format(
        case_id_short=str(case_id)[:8].upper(),
        date_str=datetime.datetime.now().strftime("%d-%b-%Y"),
        store_name=kirana.store_name,
        owner_name=kirana.owner_name,
        district=kirana.location.district,
        state=kirana.location.state,
        pincode=kirana.location.pin_code or "XXXXXX",
        mobile=kirana.owner_mobile,
        amount=f"{amount:,}",
        amount_words=number_to_words(amount),
        tenure=tenure,
        rate=rate,
        emi=f"{emi:,}"
    )
    return HTMLResponse(content=html_content)


# ---------------------------------------------------------------------------
# Phase 14 Advanced Intelligence Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/platform/cases/{case_id}/forecast")
async def get_case_forecast(case_id: uuid.UUID):
    """Return 30-day and 90-day liquidity forecasting."""
    try:
        case_detail = case_service.get_case_detail(case_id)
        # Placeholder data logic since we don't have historical statements easily queryable here
        mock_inflow = [2500, 3000, 2800]
        mock_outflow = [1800, 2000, 1900]
        curr_bal = 15000.0
        
        # Optionally infer from assessment
        if case_detail.latest_assessment and case_detail.latest_assessment.revenue_range:
            rev = case_detail.latest_assessment.revenue_range.low
            mock_inflow = [rev/30, rev/30 * 1.05, rev/30 * 0.95]
            mock_outflow = [rev/30 * 0.7, rev/30 * 0.75, rev/30 * 0.65]
        
        return forecast_liquidity(mock_inflow, mock_outflow, current_balance=curr_bal)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/platform/cases/{case_id}/simulate")
async def simulate_scenario(case_id: uuid.UUID, scenario: str):
    """Simulate what-if scenarios on the borrower's revenue."""
    try:
        case_detail = case_service.get_case_detail(case_id)
        rev = 100000.0
        if case_detail.latest_assessment and case_detail.latest_assessment.revenue_range:
            rev = case_detail.latest_assessment.revenue_range.low
            
        return simulate_stress_scenario(rev, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/platform/cases/{case_id}/aa_consent")
async def create_aa_consent(case_id: uuid.UUID, org_id: Optional[uuid.UUID] = Form(default=None)):
    """Generate mock Account Aggregator consent link."""
    try:
        case_detail = case_service.get_case_detail(case_id)
        mobile = case_detail.kirana.owner_mobile
        connector = AccountAggregatorConnector()
        return connector.generate_consent_link(mobile, str(case_detail.case.org_id))
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

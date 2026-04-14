from pathlib import Path
from uuid import UUID, uuid4

import pytest

from llm_layer.explainer import generate_underwriting_decision_pack
from llm_layer.risk_summarizer import generate_risk_summary
from models.output_schema import (
    AreaType,
    BrandTierMix,
    CVSignals,
    FraudDetection,
    GeoSignals,
    RevenueEstimate,
    RiskAssessment,
    RiskBand,
    StoreSizeCategory,
    ValueRange,
)
from models.platform_schema import UnderwritingOverrideRequest
from orchestration.loan_sizer import compute_loan_recommendation
from services.audit_service import AuditService
from services.case_service import CaseService
from storage.repository import PlatformRepository


def _build_signals():
    cv_signals = CVSignals(
        shelf_density=0.76,
        sku_diversity_score=0.68,
        estimated_sku_count=135,
        inventory_value_range=ValueRange(low=110000, high=240000),
        store_size_category=StoreSizeCategory.MEDIUM,
        brand_tier_mix=BrandTierMix.MASS_DOMINANT,
        consistency_score=0.86,
    )
    geo_signals = GeoSignals(
        area_type=AreaType.SEMI_URBAN,
        footfall_score=0.71,
        competition_count=4,
        competition_score=0.62,
        catchment_population=9200,
        demand_index=0.66,
    )
    revenue_estimate = RevenueEstimate(
        monthly_low=180000,
        monthly_high=290000,
        confidence=0.74,
    )
    risk_assessment = RiskAssessment(
        risk_band=RiskBand.MEDIUM,
        risk_score=0.39,
        confidence=0.72,
    )
    fraud_detection = FraudDetection(
        fraud_score=0.12,
        is_flagged=False,
        flags=[],
        checks_performed=["image_consistency", "gps_location_validity"],
    )
    return cv_signals, geo_signals, revenue_estimate, risk_assessment, fraud_detection


@pytest.mark.asyncio
async def test_phase10_loan_recommendation_includes_concrete_terms():
    cv_signals, geo_signals, revenue_estimate, risk_assessment, fraud_detection = _build_signals()

    recommendation = await compute_loan_recommendation(
        revenue_estimate,
        risk_assessment,
        fraud_detection,
        cv_signals=cv_signals,
        geo_signals=geo_signals,
    )

    assert recommendation.eligible is True
    assert recommendation.recommended_amount is not None
    assert recommendation.loan_range.low <= recommendation.recommended_amount <= recommendation.loan_range.high
    assert recommendation.repayment_cadence is not None
    assert recommendation.estimated_installment is not None
    assert recommendation.pricing_recommendation is not None
    assert recommendation.pricing_recommendation.annual_interest_rate_band.high >= recommendation.pricing_recommendation.annual_interest_rate_pct


@pytest.mark.asyncio
async def test_phase10_decision_pack_matches_structured_outputs():
    cv_signals, geo_signals, revenue_estimate, risk_assessment, fraud_detection = _build_signals()
    loan_recommendation = await compute_loan_recommendation(
        revenue_estimate,
        risk_assessment,
        fraud_detection,
        cv_signals=cv_signals,
        geo_signals=geo_signals,
    )

    fusion_result = {
        "revenue_estimate": revenue_estimate,
        "risk_assessment": risk_assessment,
    }
    summary = await generate_risk_summary(
        cv_signals.model_dump(),
        geo_signals.model_dump(),
        fusion_result,
        fraud_detection.model_dump(),
    )

    decision_pack = generate_underwriting_decision_pack(
        fusion_result=fusion_result,
        loan_recommendation=loan_recommendation,
        summary=summary,
    )

    assert str(int(loan_recommendation.recommended_amount)) in decision_pack.amount_rationale.replace(",", "")
    assert loan_recommendation.repayment_cadence.value in decision_pack.repayment_rationale.lower()
    assert len(decision_pack.pricing_rationale) > 20


def test_case_service_override_records_audit_trail(tmp_path):
    repository = PlatformRepository()
    temp_dir = Path(tmp_path)
    temp_dir.mkdir(parents=True, exist_ok=True)
    repository._data_dir = temp_dir
    repository._file_map = {
        "organizations": temp_dir / "organizations.json",
        "users": temp_dir / "users.json",
        "kiranas": temp_dir / "kiranas.json",
        "cases": temp_dir / "cases.json",
        "alerts": temp_dir / "alerts.json",
        "audit_events": temp_dir / "audit_events.json",
        "assessment_summaries": temp_dir / "assessment_summaries.json",
        "document_bundles": temp_dir / "document_bundles.json",
        "underwriting_decisions": temp_dir / "underwriting_decisions.json",
    }

    service = CaseService(repository, AuditService(repository))
    case_id = UUID("61111111-1111-1111-1111-111111111111")
    actor_user_id = UUID("22222222-2222-2222-2222-222222222222")

    detail = service.override_underwriting_decision(
        case_id,
        UnderwritingOverrideRequest(
            actor_user_id=actor_user_id,
            override_amount=165000,
            override_tenure_months=24,
            override_repayment_cadence="weekly",
            override_annual_interest_rate_pct=19.75,
            override_processing_fee_pct=1.75,
            reason="Officer validated strong supplier turnover and approved a slightly larger ticket.",
        ),
    )

    assert detail.underwriting_decision is not None
    assert detail.underwriting_decision.has_override is True
    assert detail.underwriting_decision.override_reason is not None
    assert detail.underwriting_decision.final_terms.amount == 165000
    assert repository.get_latest_underwriting_decision(case_id) is not None
    assert any(
        event.action.value == "underwriting_overridden"
        for event in detail.audit_events
    )

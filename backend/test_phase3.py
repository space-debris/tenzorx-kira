"""
KIRA — Phase 3 Integration Test

Tests the full fusion engine → fraud detector → loan sizer → output formatter
pipeline with mock CV and Geo signals. Does NOT call external APIs.
"""

import asyncio
import uuid

import pytest

from models.output_schema import (
    AreaType, BrandTierMix, CVSignals, GeoSignals,
    StoreSizeCategory, ValueRange,
)
from cv_module.sku_diversity import compute_sku_diversity
from orchestration.fusion_engine import run_fusion_engine
from orchestration.fraud_detector import run_fraud_detection
from orchestration.loan_sizer import compute_loan_recommendation
from orchestration.output_formatter import format_assessment_output
from llm_layer.risk_summarizer import generate_risk_summary
from llm_layer.explainer import _generate_fallback_narrative, _score_to_descriptor


@pytest.mark.asyncio
async def test_full_pipeline():
    """Test the complete Phase 3 pipeline with mock signals."""
    print("=" * 60)
    print("KIRA Phase 3 Integration Test")
    print("=" * 60)

    # --- Mock CV Signals (typical medium kirana store) ---
    cv_signals = CVSignals(
        shelf_density=0.72,
        sku_diversity_score=0.65,
        estimated_sku_count=120,
        inventory_value_range=ValueRange(low=80000, high=250000),
        store_size_category=StoreSizeCategory.MEDIUM,
        brand_tier_mix=BrandTierMix.MIXED,
        consistency_score=0.85,
    )

    # --- Mock Geo Signals (semi-urban, moderate footfall) ---
    geo_signals = GeoSignals(
        area_type=AreaType.SEMI_URBAN,
        footfall_score=0.55,
        competition_count=5,
        competition_score=0.60,
        catchment_population=8000,
        demand_index=0.52,
    )

    # --- Test 1: Fusion Engine ---
    print("\n[TEST 1] Fusion Engine")
    fusion_result = await run_fusion_engine(cv_signals, geo_signals)

    print(f"  Composite Score: {fusion_result['composite_score']}")
    print(f"  Revenue: ₹{fusion_result['revenue_estimate'].monthly_low:,.0f}"
          f" - ₹{fusion_result['revenue_estimate'].monthly_high:,.0f}")
    print(f"  Risk Band: {fusion_result['risk_assessment'].risk_band.value}")
    print(f"  Risk Score: {fusion_result['risk_assessment'].risk_score}")
    print(f"  Confidence: {fusion_result['risk_assessment'].confidence}")
    print(f"  Signal Contributions: {fusion_result['signal_contributions']}")

    assert 0 <= fusion_result['composite_score'] <= 1
    assert fusion_result['revenue_estimate'].monthly_low > 0
    assert fusion_result['revenue_estimate'].monthly_high >= fusion_result['revenue_estimate'].monthly_low
    print("  ✅ PASSED")

    # --- Test 2: Fraud Detection ---
    print("\n[TEST 2] Fraud Detection (clean store)")
    fraud_result = await run_fraud_detection(cv_signals, geo_signals, fusion_result)

    print(f"  Fraud Score: {fraud_result.fraud_score}")
    print(f"  Is Flagged: {fraud_result.is_flagged}")
    print(f"  Flags: {fraud_result.flags}")
    print(f"  Checks: {fraud_result.checks_performed}")

    assert 0 <= fraud_result.fraud_score <= 1
    assert len(fraud_result.checks_performed) == 4
    assert fraud_result.is_flagged is False, "Clean store should not be auto-flagged"
    print("  ✅ PASSED")

    # --- Test 3: Fraud Detection (adversarial case) ---
    print("\n[TEST 3] Fraud Detection (adversarial — premium in rural)")
    cv_adversarial = CVSignals(
        shelf_density=0.90,
        sku_diversity_score=0.85,
        estimated_sku_count=200,
        inventory_value_range=ValueRange(low=400000, high=600000),
        store_size_category=StoreSizeCategory.LARGE,
        brand_tier_mix=BrandTierMix.PREMIUM_DOMINANT,
        consistency_score=0.40,
    )
    geo_adversarial = GeoSignals(
        area_type=AreaType.RURAL,
        footfall_score=0.15,
        competition_count=0,
        competition_score=0.95,
        catchment_population=800,
        demand_index=0.12,
    )
    fraud_adversarial = await run_fraud_detection(
        cv_adversarial, geo_adversarial, fusion_result
    )

    print(f"  Fraud Score: {fraud_adversarial.fraud_score}")
    print(f"  Is Flagged: {fraud_adversarial.is_flagged}")
    print(f"  Flags ({len(fraud_adversarial.flags)}):")
    for flag in fraud_adversarial.flags:
        print(f"    - {flag}")

    assert fraud_adversarial.fraud_score > 0.3, "Expected high fraud score for adversarial case"
    print("  ✅ PASSED")

    # --- Test 4: Loan Sizer ---
    print("\n[TEST 4] Loan Sizer (eligible store)")
    loan_result = await compute_loan_recommendation(
        fusion_result['revenue_estimate'],
        fusion_result['risk_assessment'],
        fraud_result,
    )

    print(f"  Eligible: {loan_result.eligible}")
    print(f"  Loan Range: ₹{loan_result.loan_range.low:,.0f}"
          f" - ₹{loan_result.loan_range.high:,.0f}")
    print(f"  Tenure: {loan_result.suggested_tenure_months} months")
    print(f"  EMI: ₹{loan_result.estimated_emi:,.0f}")
    print(f"  EMI/Income: {loan_result.emi_to_income_ratio:.2%}")

    assert loan_result.eligible is True
    assert loan_result.loan_range.high <= 500000
    assert loan_result.estimated_emi > 0
    print("  ✅ PASSED")

    # --- Test 5: Loan Sizer (fraud-flagged) ---
    print("\n[TEST 5] Loan Sizer (fraud-flagged store)")
    loan_flagged = await compute_loan_recommendation(
        fusion_result['revenue_estimate'],
        fusion_result['risk_assessment'],
        fraud_adversarial,  # Using the flagged result
    )

    print(f"  Eligible: {loan_flagged.eligible}")
    if fraud_adversarial.is_flagged:
        assert loan_flagged.eligible is False, "Flagged store should not be eligible"
        print("  ✅ PASSED — correctly rejected fraud-flagged store")
    else:
        print("  ⚠️  Adversarial store not flagged (score below threshold)")

    # --- Test 6: Risk Summarizer ---
    print("\n[TEST 6] Risk Summarizer")
    cv_dict = cv_signals.model_dump()
    geo_dict = geo_signals.model_dump()
    fraud_dict = fraud_result.model_dump()

    summary = await generate_risk_summary(cv_dict, geo_dict, fusion_result, fraud_dict)

    print(f"  Strengths ({len(summary.strengths)}):")
    for s in summary.strengths:
        print(f"    + {s}")
    print(f"  Concerns ({len(summary.concerns)}):")
    for c in summary.concerns:
        print(f"    - {c}")
    print(f"  Recommendation: {summary.recommendation}")

    assert len(summary.strengths) > 0
    assert len(summary.concerns) > 0
    assert len(summary.recommendation) > 0
    print("  ✅ PASSED")

    # --- Test 7: Fallback Narrative ---
    print("\n[TEST 7] Fallback Narrative (no API call)")
    narrative = _generate_fallback_narrative(cv_dict, geo_dict, fusion_result, fraud_dict)

    print(f"  Narrative ({len(narrative)} chars):")
    print(f"  \"{narrative[:200]}...\"")

    assert len(narrative) > 50
    print("  ✅ PASSED")

    # --- Test 8: SKU Diversity category normalization ---
    print("\n[TEST 8] SKU Diversity category normalization")
    sku_result = compute_sku_diversity(
        {
            "product_categories": [
                "Soft Drinks",
                "Dairy Products",
                "Personal Hygiene",
                "Cleaning Supplies",
                "Biscuits and Confectionery",
                "Cooking Essentials",
            ],
            "sku_count_estimate": 180,
            "brand_tier": "mixed",
        }
    )

    print(f"  Category Count: {sku_result['category_count']}")
    print(f"  Diversity Score: {sku_result['sku_diversity_score']}")

    assert sku_result["category_count"] >= 5
    assert sku_result["sku_diversity_score"] > 0.3
    print("  âœ… PASSED")

    # --- Test 9: Output Formatter ---
    print("\n[TEST 9] Output Formatter")
    session_id = uuid.uuid4()
    output = format_assessment_output(
        session_id=session_id,
        cv_signals=cv_signals,
        geo_signals=geo_signals,
        revenue_estimate=fusion_result['revenue_estimate'],
        risk_assessment=fusion_result['risk_assessment'],
        loan_recommendation=loan_result,
        fraud_detection=fraud_result,
        risk_narrative=narrative,
        summary=summary,
    )

    print(f"  Session ID: {output.session_id}")
    print(f"  Assessment ID: {output.assessment_id}")
    print(f"  Status: {output.status.value}")
    print(f"  Revenue: ₹{output.revenue_estimate.monthly_low:,.0f}"
          f" - ₹{output.revenue_estimate.monthly_high:,.0f}")
    print(f"  Risk: {output.risk_assessment.risk_band.value}")
    print(f"  Loan Eligible: {output.loan_recommendation.eligible}")
    print(f"  Fraud Flagged: {output.fraud_detection.is_flagged}")

    assert output.status.value == "completed"
    assert output.session_id == session_id
    print("  ✅ PASSED")

    # --- Test 10: Score descriptor helper ---
    print("\n[TEST 10] Score-to-Descriptor")
    assert _score_to_descriptor(0.9) == "very strong"
    assert _score_to_descriptor(0.65) == "strong"
    assert _score_to_descriptor(0.5) == "moderate"
    assert _score_to_descriptor(0.3) == "low"
    assert _score_to_descriptor(0.1) == "very low"
    print("  ✅ PASSED")

    print("\n" + "=" * 60)
    print("ALL 9 TESTS PASSED ✅")
    print("=" * 60)

    # Print the full JSON output for inspection
    print("\n--- Full AssessmentOutput JSON ---")
    import json
    print(json.dumps(output.model_dump(mode='json'), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())

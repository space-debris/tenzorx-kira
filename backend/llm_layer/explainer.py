"""
KIRA — Risk Narrative Explainer

Uses Google Gemma 4 31B API to generate human-readable risk assessment
narratives from structured signal data. This makes KIRA's assessments
auditable and understandable by credit officers.

Owner: Orchestration Lead
Phase: 4.1

Design Decision:
    The explainer receives structured data (not raw images) and generates
    text. This ensures explanations are grounded in the same signals
    used for scoring, not a separate interpretation of the images.

Model Choice:
    Using Gemma 4 31B (gemma-4-31b-it) for text generation due to:
    - High rate limits: 15 RPM, Unlimited TPM, 1.5K RPD
    - Strong instruction-following capability
    - Available on the free tier
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from models.output_schema import (
    ExplanationSummary,
    LoanRecommendation,
    UnderwritingDecisionPack,
)

# Load repo-root or workspace-root .env so key resolution does not depend on launch cwd.
_ENV_ROOT = Path(__file__).resolve().parents[2]
for env_path in (_ENV_ROOT / ".env", _ENV_ROOT.parent / ".env"):
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
logger = logging.getLogger("kira.llm.explainer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_gemini_api_key() -> str:
    """Fetch Gemini API key at call time so .env updates are picked up after reload."""
    return os.getenv("GEMINI_API_KEY", "")

# Using Gemma 4 31B for text generation — high rate limits on free tier
LLM_MODEL = "gemma-4-31b-it"

# Explanation generation prompt
EXPLANATION_PROMPT_TEMPLATE = """
You are a credit risk analyst writing a brief assessment of a kirana
(small Indian retail) store's creditworthiness. Based on the following
signals, write a 3-5 sentence risk narrative in professional but
accessible English.

VISUAL SIGNALS:
- Shelf Density: {shelf_density} (0-1 scale, higher = more stocked)
- SKU Diversity Score: {sku_diversity} (0-1 scale)
- Estimated SKU Count: {sku_count}
- Inventory Value: ₹{inventory_low:,.0f} - ₹{inventory_high:,.0f}
- Store Size: {store_size}
- Brand Tier: {brand_tier}
- Image Consistency: {consistency} (0-1 scale)

LOCATION SIGNALS:
- Area Type: {area_type}
- Footfall Score: {footfall} (0-1 scale)
- Competition: {competition_count} nearby stores
- Catchment Population: ~{catchment_pop:,} people
- Demand Index: {demand_index} (0-1 scale)

ASSESSMENT RESULTS:
- Estimated Monthly Revenue: ₹{revenue_low:,.0f} - ₹{revenue_high:,.0f}
- Risk Band: {risk_band}
- Confidence: {confidence:.0%}
- Fraud Flagged: {fraud_flagged}
- Recommended Loan Amount: ₹{recommended_amount:,.0f}
- Suggested Tenure: {tenure_months} months
- Suggested Repayment Cadence: {repayment_cadence}
- Suggested Annual Rate: {interest_rate:.2f}%

Write the narrative focusing on:
1. Overall store health and inventory quality
2. Location advantages or disadvantages
3. Key risk factors
4. Lending recommendation rationale

Keep the tone professional, balanced, and specific. Reference actual
signal values where relevant. Do NOT use bullet points — write in
paragraph form.
"""

# Template fallback for when Gemini API is unavailable
FALLBACK_TEMPLATE = (
    "This {store_size} kirana store in a {area_type} area shows "
    "{density_desc} shelf occupancy with {diversity_desc} product diversity. "
    "The location has {footfall_desc} footfall potential with "
    "{competition_count} competing stores nearby, serving an estimated "
    "catchment of {catchment_pop:,} people. "
    "Estimated monthly revenue of ₹{revenue_low:,.0f} - ₹{revenue_high:,.0f} "
    "supports a {risk_band} risk classification with {confidence:.0%} confidence. "
    "{fraud_note}"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_risk_narrative(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any],
    loan_recommendation: LoanRecommendation | dict[str, Any] | None = None,
) -> str:
    """
    Generate a human-readable risk narrative using Gemma 4 31B.

    Takes all structured signal data and generates a 3-5 sentence
    paragraph explaining the assessment in plain English. Falls back
    to a template-based explanation if the API is unavailable.

    Args:
        cv_signals: CV module output dict.
        geo_signals: Geo module output dict.
        fusion_result: Fusion engine output with revenue_estimate, risk_band.
        fraud_detection: Fraud detection output with is_flagged, flags.

    Returns:
        str: Human-readable risk narrative (3-5 sentences, ~100-200 words).
    """
    try:
        gemini_api_key = _get_gemini_api_key()
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not set, using fallback template")
            return _generate_fallback_narrative(
                cv_signals,
                geo_signals,
                fusion_result,
                fraud_detection,
                loan_recommendation,
            )

        client = genai.Client(api_key=gemini_api_key)

        # Format the prompt with actual signal values
        prompt = _format_prompt(
            cv_signals,
            geo_signals,
            fusion_result,
            fraud_detection,
            loan_recommendation,
        )

        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,  # Slightly creative but factual
                max_output_tokens=512,
            ),
        )

        narrative = response.text.strip()

        # Basic validation: ensure reasonable length
        if len(narrative) < 50:
            logger.warning(
                f"Generated narrative too short ({len(narrative)} chars), "
                "using fallback"
            )
            return _generate_fallback_narrative(
                cv_signals,
                geo_signals,
                fusion_result,
                fraud_detection,
                loan_recommendation,
            )

        logger.info(
            f"Risk narrative generated via {LLM_MODEL} "
            f"({len(narrative)} chars)"
        )
        return narrative

    except Exception as e:
        logger.warning(f"LLM narrative generation failed: {e}. Using fallback.")
        return _generate_fallback_narrative(
            cv_signals,
            geo_signals,
            fusion_result,
            fraud_detection,
            loan_recommendation,
        )


def _format_prompt(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any],
    loan_recommendation: LoanRecommendation | dict[str, Any] | None = None,
) -> str:
    """
    Format all signal data into the explanation prompt template.

    Handles missing/null values gracefully with safe defaults.
    """
    # Extract revenue estimate values
    revenue_est = fusion_result.get("revenue_estimate", {})
    if hasattr(revenue_est, "monthly_low"):
        rev_low = revenue_est.monthly_low
        rev_high = revenue_est.monthly_high
        confidence = revenue_est.confidence
    else:
        rev_low = revenue_est.get("monthly_low", 0)
        rev_high = revenue_est.get("monthly_high", 0)
        confidence = revenue_est.get("confidence", 0)

    # Extract risk band
    risk_assessment = fusion_result.get("risk_assessment", {})
    if hasattr(risk_assessment, "risk_band"):
        risk_band = risk_assessment.risk_band.value
    else:
        risk_band = risk_assessment.get("risk_band", "UNKNOWN")

    # Extract inventory range
    inv_range = cv_signals.get("inventory_value_range", {})
    if hasattr(inv_range, "low"):
        inv_low = inv_range.low
        inv_high = inv_range.high
    else:
        inv_low = inv_range.get("low", 0)
        inv_high = inv_range.get("high", 0)

    # Fraud status
    if hasattr(fraud_detection, "is_flagged"):
        fraud_flagged = "Yes" if fraud_detection.is_flagged else "No"
    else:
        fraud_flagged = "Yes" if fraud_detection.get("is_flagged", False) else "No"

    recommended_amount, tenure_months, repayment_cadence, interest_rate = _extract_loan_fields(
        loan_recommendation
    )

    return EXPLANATION_PROMPT_TEMPLATE.format(
        shelf_density=cv_signals.get("shelf_density", 0),
        sku_diversity=cv_signals.get("sku_diversity_score", 0),
        sku_count=cv_signals.get("estimated_sku_count", 0),
        inventory_low=inv_low,
        inventory_high=inv_high,
        store_size=cv_signals.get("store_size_category", "medium"),
        brand_tier=cv_signals.get("brand_tier_mix", "mixed"),
        consistency=cv_signals.get("consistency_score", 0),
        area_type=geo_signals.get("area_type", "semi_urban"),
        footfall=geo_signals.get("footfall_score", 0),
        competition_count=geo_signals.get("competition_count", 0),
        catchment_pop=geo_signals.get("catchment_population", 0),
        demand_index=geo_signals.get("demand_index", 0),
        revenue_low=rev_low,
        revenue_high=rev_high,
        risk_band=risk_band,
        confidence=confidence,
        fraud_flagged=fraud_flagged,
        recommended_amount=recommended_amount,
        tenure_months=tenure_months,
        repayment_cadence=repayment_cadence,
        interest_rate=interest_rate,
    )


def _generate_fallback_narrative(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any] | None = None,
    loan_recommendation: LoanRecommendation | dict[str, Any] | None = None,
) -> str:
    """
    Generate a template-based narrative when Gemini API is unavailable.

    Uses simple string formatting with descriptor functions to convert
    scores to human-readable descriptors.
    """
    # Extract values safely — handle both dict and enum values
    shelf_density = cv_signals.get("shelf_density", 0.5)
    sku_diversity = cv_signals.get("sku_diversity_score", 0.5)
    store_size_raw = cv_signals.get("store_size_category", "medium")
    store_size = store_size_raw.value if hasattr(store_size_raw, "value") else str(store_size_raw)
    area_type_raw = geo_signals.get("area_type", "semi_urban")
    area_type = area_type_raw.value if hasattr(area_type_raw, "value") else str(area_type_raw)
    footfall = geo_signals.get("footfall_score", 0.5)
    competition_count = geo_signals.get("competition_count", 0)
    catchment_pop = geo_signals.get("catchment_population", 0)

    # Revenue
    revenue_est = fusion_result.get("revenue_estimate", {})
    if hasattr(revenue_est, "monthly_low"):
        rev_low = revenue_est.monthly_low
        rev_high = revenue_est.monthly_high
        confidence = revenue_est.confidence
    else:
        rev_low = revenue_est.get("monthly_low", 0)
        rev_high = revenue_est.get("monthly_high", 0)
        confidence = revenue_est.get("confidence", 0)

    # Risk band
    risk_assessment = fusion_result.get("risk_assessment", {})
    if hasattr(risk_assessment, "risk_band"):
        risk_band = risk_assessment.risk_band.value
    else:
        risk_band = risk_assessment.get("risk_band", "MEDIUM")

    # Fraud note
    fraud_note = ""
    if fraud_detection:
        is_flagged = (
            fraud_detection.is_flagged
            if hasattr(fraud_detection, "is_flagged")
            else fraud_detection.get("is_flagged", False)
        )
        if is_flagged:
            fraud_note = "Note: This assessment has been flagged for additional review due to potential inconsistencies."

    recommended_amount, tenure_months, repayment_cadence, interest_rate = _extract_loan_fields(
        loan_recommendation
    )
    recommendation_note = (
        f" The recommended structure is ₹{recommended_amount:,.0f} over "
        f"{tenure_months} months with {repayment_cadence} collections at "
        f"an annual rate of {interest_rate:.2f}%."
        if recommended_amount > 0
        else ""
    )

    return FALLBACK_TEMPLATE.format(
        store_size=store_size,
        area_type=area_type.replace("_", "-"),
        density_desc=_score_to_descriptor(shelf_density),
        diversity_desc=_score_to_descriptor(sku_diversity),
        footfall_desc=_score_to_descriptor(footfall),
        competition_count=competition_count,
        catchment_pop=catchment_pop,
        revenue_low=rev_low,
        revenue_high=rev_high,
        risk_band=risk_band,
        confidence=confidence,
        fraud_note=f"{fraud_note}{recommendation_note}".strip(),
    ).strip()


def generate_underwriting_decision_pack(
    *,
    fusion_result: dict[str, Any],
    loan_recommendation: LoanRecommendation,
    summary: ExplanationSummary,
) -> UnderwritingDecisionPack:
    """Generate an officer-friendly explanation pack from structured outputs."""
    revenue_est = fusion_result.get("revenue_estimate", {})
    if hasattr(revenue_est, "monthly_low"):
        rev_low = revenue_est.monthly_low
        rev_high = revenue_est.monthly_high
    else:
        rev_low = revenue_est.get("monthly_low", 0)
        rev_high = revenue_est.get("monthly_high", 0)

    risk_assessment = fusion_result.get("risk_assessment", {})
    if hasattr(risk_assessment, "risk_band"):
        risk_band = risk_assessment.risk_band.value
    else:
        risk_band = getattr(risk_assessment, "risk_band", "MEDIUM")
        if hasattr(risk_band, "value"):
            risk_band = risk_band.value

    strengths = "; ".join(summary.strengths[:2]) or "signal quality and store economics remain acceptable"
    concerns = "; ".join(summary.concerns[:2]) or "no major concerns were surfaced"
    cadence = (
        loan_recommendation.repayment_cadence.value
        if loan_recommendation.repayment_cadence
        else "weekly"
    )
    pricing = loan_recommendation.pricing_recommendation
    recommended_amount = loan_recommendation.recommended_amount or 0.0
    loan_range_low = loan_recommendation.loan_range.low if loan_recommendation.loan_range else 0.0
    loan_range_high = loan_recommendation.loan_range.high if loan_recommendation.loan_range else 0.0

    if not loan_recommendation.eligible or recommended_amount <= 0:
        return UnderwritingDecisionPack(
            amount_rationale=(
                f"No lendable amount is recommended because the current assessment does not "
                f"clear the eligibility checks for a {risk_band} risk posture."
            ),
            tenure_rationale=(
                "Tenure remains advisory only until the assessment clears manual review and policy checks."
            ),
            repayment_rationale=(
                f"Repayment cadence is not activated for lending. Key concerns: {concerns}."
            ),
            pricing_rationale=(
                "Pricing guidance is withheld because the case is not currently eligible for a standard offer."
            ),
        )

    amount_rationale = (
        f"The recommended amount of ₹{recommended_amount:,.0f} sits "
        f"inside the approved guardrail of ₹{loan_range_low:,.0f} "
        f"to ₹{loan_range_high:,.0f}, using the conservative revenue "
        f"view of ₹{rev_low:,.0f} to ₹{rev_high:,.0f} and a {risk_band} risk posture."
    )
    tenure_rationale = (
        f"The {loan_recommendation.suggested_tenure_months}-month tenure keeps the monthly "
        f"equivalent payment near ₹{loan_recommendation.estimated_emi:,.0f}, preserving an "
        f"EMI-to-income ratio of {loan_recommendation.emi_to_income_ratio:.0%}."
    )
    repayment_rationale = (
        f"{cadence.capitalize()} repayment is recommended to match the observed operating "
        f"pattern while balancing lender control. Key strengths: {strengths}. Key concerns: {concerns}."
    )
    pricing_rationale = (
        pricing.rationale
        if pricing is not None
        else "Pricing falls back to standard policy because no dynamic pricing output was available."
    )

    return UnderwritingDecisionPack(
        amount_rationale=amount_rationale,
        tenure_rationale=tenure_rationale,
        repayment_rationale=repayment_rationale,
        pricing_rationale=pricing_rationale,
    )


def _extract_loan_fields(
    loan_recommendation: LoanRecommendation | dict[str, Any] | None,
) -> tuple[float, int, str, float]:
    """Read key loan recommendation fields from either a model or dict."""
    if loan_recommendation is None:
        return 0.0, 18, "weekly", 18.0

    if hasattr(loan_recommendation, "recommended_amount"):
        pricing = getattr(loan_recommendation, "pricing_recommendation", None)
        interest_rate = (
            getattr(pricing, "annual_interest_rate_pct", 18.0)
            if pricing is not None
            else 18.0
        )
        cadence = getattr(loan_recommendation, "repayment_cadence", None)
        cadence_value = cadence.value if hasattr(cadence, "value") else cadence or "weekly"
        return (
            float(getattr(loan_recommendation, "recommended_amount", 0) or 0),
            int(getattr(loan_recommendation, "suggested_tenure_months", 18) or 18),
            str(cadence_value),
            float(interest_rate),
        )

    pricing = loan_recommendation.get("pricing_recommendation") or {}
    cadence = loan_recommendation.get("repayment_cadence", "weekly")
    if hasattr(cadence, "value"):
        cadence = cadence.value
    return (
        float(loan_recommendation.get("recommended_amount", 0) or 0),
        int(loan_recommendation.get("suggested_tenure_months", 18) or 18),
        str(cadence),
        float(pricing.get("annual_interest_rate_pct", 18.0) or 18.0),
    )


def _score_to_descriptor(score: float) -> str:
    """
    Convert a 0-1 score to a human-readable descriptor.

    Args:
        score: Numeric score (0-1).

    Returns:
        str: "very low" | "low" | "moderate" | "strong" | "very strong"
    """
    if score >= 0.8:
        return "very strong"
    elif score >= 0.6:
        return "strong"
    elif score >= 0.4:
        return "moderate"
    elif score >= 0.2:
        return "low"
    else:
        return "very low"

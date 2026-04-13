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

# Load repo-root .env explicitly so key resolution does not depend on launch cwd.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
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
                cv_signals, geo_signals, fusion_result, fraud_detection
            )

        client = genai.Client(api_key=gemini_api_key)

        # Format the prompt with actual signal values
        prompt = _format_prompt(
            cv_signals, geo_signals, fusion_result, fraud_detection
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
                cv_signals, geo_signals, fusion_result, fraud_detection
            )

        logger.info(
            f"Risk narrative generated via {LLM_MODEL} "
            f"({len(narrative)} chars)"
        )
        return narrative

    except Exception as e:
        logger.warning(f"LLM narrative generation failed: {e}. Using fallback.")
        return _generate_fallback_narrative(
            cv_signals, geo_signals, fusion_result, fraud_detection
        )


def _format_prompt(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any],
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
    )


def _generate_fallback_narrative(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any] | None = None,
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
        fraud_note=fraud_note,
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

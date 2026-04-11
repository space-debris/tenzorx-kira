"""
KIRA — Risk Narrative Explainer

Uses Google Gemini Pro API to generate human-readable risk assessment
narratives from structured signal data. This makes KIRA's assessments
auditable and understandable by credit officers.

Owner: Orchestration Lead
Phase: 4.1

Design Decision:
    The explainer receives structured data (not raw images) and generates
    text. This ensures explanations are grounded in the same signals
    used for scoring, not a separate interpretation of the images.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("kira.llm.explainer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = "gemini-1.5-pro-latest"

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
    "{competition_count} competing stores nearby. "
    "Estimated monthly revenue of ₹{revenue_low:,.0f} - ₹{revenue_high:,.0f} "
    "supports a {risk_band} risk classification with {confidence:.0%} confidence."
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
    Generate a human-readable risk narrative using Gemini Pro.

    Takes all structured signal data and generates a 3-5 sentence
    paragraph explaining the assessment in plain English. Falls back
    to a template-based explanation if the API is unavailable.

    Args:
        cv_signals: CV module output dict with shelf_density,
            sku_diversity_score, inventory_value_range, etc.
        geo_signals: Geo module output dict with area_type,
            footfall_score, competition_count, etc.
        fusion_result: Fusion engine output with revenue_estimate,
            risk_band, confidence.
        fraud_detection: Fraud detection output with is_flagged, flags.

    Returns:
        str: Human-readable risk narrative (3-5 sentences, ~100-200 words).

    Processing Steps:
        1. Format all signals into EXPLANATION_PROMPT_TEMPLATE
        2. Send formatted prompt to Gemini Pro
        3. Parse and validate response (ensure appropriate length/tone)
        4. If API fails, use FALLBACK_TEMPLATE
        5. Log generated narrative for audit

    TODO:
        - Implement Gemini Pro API call for narrative generation
        - Implement response validation (length, tone, content)
        - Implement template-based fallback
        - Add prompt versioning for A/B testing
        - Add narrative caching
    """
    # TODO: Implement risk narrative generation
    raise NotImplementedError("Explainer not yet implemented")


def _format_prompt(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
    fraud_detection: dict[str, Any],
) -> str:
    """
    Format all signal data into the explanation prompt template.

    Args:
        cv_signals: CV module output.
        geo_signals: Geo module output.
        fusion_result: Fusion engine output.
        fraud_detection: Fraud detection output.

    Returns:
        str: Formatted prompt ready for Gemini Pro.

    TODO:
        - Implement template formatting with all signal values
        - Handle missing/null values gracefully
    """
    # TODO: Implement prompt formatting
    raise NotImplementedError


def _generate_fallback_narrative(
    cv_signals: dict[str, Any],
    geo_signals: dict[str, Any],
    fusion_result: dict[str, Any],
) -> str:
    """
    Generate a template-based narrative when Gemini API is unavailable.

    Uses simple string formatting with descriptor functions to convert
    scores to human-readable descriptors (e.g., 0.8 → "strong").

    Args:
        cv_signals: CV module output.
        geo_signals: Geo module output.
        fusion_result: Fusion engine output.

    Returns:
        str: Template-based risk narrative.

    TODO:
        - Implement score-to-descriptor conversion
        - Implement template formatting
    """
    # TODO: Implement fallback narrative generation
    raise NotImplementedError


def _score_to_descriptor(score: float) -> str:
    """
    Convert a 0-1 score to a human-readable descriptor.

    Args:
        score: Numeric score (0-1).

    Returns:
        str: "very low" | "low" | "moderate" | "strong" | "very strong"

    TODO:
        - Implement threshold-based mapping
    """
    # TODO: Implement score to descriptor conversion
    raise NotImplementedError

"""
KIRA — Image Analyzer

Core integration with Google Gemini Vision API for kirana store image analysis.
This module sends store images to Gemini Vision with structured extraction
prompts and parses the response into feature dictionaries.

Owner: Analytics & CV Lead
Phase: 1.1 (P0 — blocking for all other CV work)

Key Design Decision:
    Prompt engineering is critical. The prompt must ask Gemini to extract
    specific, quantifiable features — not just describe the image. We use
    structured output format (JSON) in the prompt to get parseable responses.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from collections import Counter
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load repo-root or workspace-root .env so key resolution does not depend on launch cwd.
_ENV_ROOT = Path(__file__).resolve().parents[2]
for env_path in (_ENV_ROOT / ".env", _ENV_ROOT.parent / ".env"):
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
logger = logging.getLogger("kira.cv.image_analyzer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_gemini_api_key() -> str:
    """Fetch Gemini API key at call time so .env updates are picked up after reload."""
    return os.getenv("GEMINI_API_KEY", "")

# Model to use for vision analysis
# Using gemma-4-31b-it — free tier: 15 RPM, Unlimited TPM, 1.5K RPD
# Better multimodal capability and much higher rate limits than gemini-2.5-flash
VISION_MODEL = "gemma-4-31b-it"

# Maximum retries for API calls
MAX_RETRIES = 3

# Structured extraction prompt for kirana store analysis
ANALYSIS_PROMPT = """
You are analyzing images of a kirana (small Indian retail) store for credit
assessment purposes. Extract the following features in JSON format:
{area_context}

{
    "store_type": "kirana | general_store | superette | specialty | modern_bazaar",
    "store_size": "small | medium | large | mega",
    "store_size_sqft_estimate": <integer estimate>,
    "lighting_quality": "poor | adequate | good | excellent",
    "aesthetic_appeal": "basic | functional | premium",
    "organization_level": "disorganized | average | well_organized",
    "shelf_occupancy_percent": <0-100>,
    "empty_shelf_areas": <integer count>,
    "visible_product_categories": [<list of categories detected>],
    "estimated_unique_sku_count": <integer>,
    "brand_names_visible": [<list of brand names>],
    "brand_tier": "premium_dominant | mass_dominant | value_dominant | mixed",
    "freshness_indicators": {
        "has_perishables": <boolean>,
        "visible_expiry_risk": <boolean>,
        "recent_stock_visible": <boolean>
    },
    "infrastructure": {
        "has_refrigeration": <boolean>,
        "has_digital_payment": <boolean>,
        "has_signage": <boolean>,
        "counter_type": "basic | organized | professional"
    },
    "image_quality_score": <0.0-1.0>,
    "confidence": <0.0-1.0>
}

Be precise and conservative in your estimates. If you cannot determine
a feature with reasonable confidence, use null.

IMPORTANT: Return ONLY the JSON object, no additional text or markdown.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_images(
    images: list[dict[str, Any]],
    shop_area_sqft: int | None = None,
) -> dict[str, Any]:
    """
    Analyze multiple store images using Google Gemini Vision API.

    Sends each image to Gemini Vision with a structured extraction prompt,
    parses the responses, and aggregates features across all images into
    a unified analysis result.

    Args:
        images: List of image dicts, each containing:
            - "image_data" (str): Base64-encoded image data
            - "image_type" (str): "interior", "exterior", or "shelf_closeup"
            - "mime_type" (str): "image/jpeg" or "image/png"
        shop_area_sqft: Exact store area provided by the user, if any.

    Returns:
        dict: Aggregated image analysis result containing:
            - "raw_analyses" (list[dict]): Per-image Gemini responses
            - "store_type" (str): Consensus store type
            - "store_size" (str): Consensus store size
            - "store_size_sqft_estimate" (int): Average sqft estimate
            - "shelf_occupancy" (float): Average shelf occupancy 0-100
            - "empty_shelf_areas" (int): Average empty shelf areas
            - "product_categories" (list[str]): Union of all detected categories
            - "sku_count_estimate" (int): Best estimate of unique SKUs
            - "brand_tier" (str): Consensus brand tier
            - "brand_names" (list[str]): All detected brand names
            - "infrastructure" (dict): Aggregated infrastructure features
            - "freshness_indicators" (dict): Aggregated freshness signals
            - "organization_level" (str): Consensus organization level
            - "lighting_quality" (str): Consensus lighting quality
            - "image_quality" (float): Average image quality score
            - "analysis_confidence" (float): Overall analysis confidence

    Raises:
        ValueError: If no images provided or all API calls fail.
        RuntimeError: If Gemini API key is not configured.
    """
    if not images:
        raise ValueError("At least one image is required for analysis")

    gemini_api_key = _get_gemini_api_key()
    if not gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Set it in the repo root .env or as an environment variable."
        )

    # API key will be passed to client in _send_to_gemini_vision

    # Process each image through Gemini Vision
    raw_analyses: list[dict[str, Any]] = []
    for idx, img in enumerate(images):
        image_data = img.get("image_data", "")
        mime_type = img.get("mime_type", "image/jpeg")
        image_type = img.get("image_type", "interior")

        logger.info(
            f"Analyzing image {idx + 1}/{len(images)} "
            f"(type={image_type}, mime={mime_type})"
        )

        try:
            area_context = ""
            if shop_area_sqft:
                area_context = f"\\nKNOWN DATA: The user has provided an exact store area of {shop_area_sqft} sq ft. Highly weigh this parameter when scaling capacity, aesthetic scores, and sku limits. Be extremely liberal in your sanctions and classifications if the area is huge (like > 1000)."
                
            result = await _send_to_gemini_vision(
                image_base64=image_data,
                mime_type=mime_type,
                prompt=ANALYSIS_PROMPT.replace("{area_context}", area_context),
                api_key=gemini_api_key,
            )
            result["_image_type"] = image_type
            result["_image_index"] = idx
            raw_analyses.append(result)
            logger.info(f"Image {idx + 1} analyzed successfully")
        except Exception as e:
            logger.warning(
                f"Failed to analyze image {idx + 1}: {e}. Skipping."
            )
            continue

    if not raw_analyses:
        raise ValueError(
            "All image analyses failed. Check API key and image data."
        )

    # Aggregate features across all images
    aggregated = _aggregate_analyses(raw_analyses)
    aggregated["raw_analyses"] = raw_analyses

    logger.info(
        f"Image analysis complete: {len(raw_analyses)}/{len(images)} images "
        f"processed successfully. Confidence: {aggregated.get('analysis_confidence', 0):.2f}"
    )

    return aggregated


async def _send_to_gemini_vision(
    image_base64: str,
    mime_type: str,
    prompt: str,
    api_key: str,
) -> dict[str, Any]:
    """
    Send a single image to Gemini Vision API with a structured prompt.

    Args:
        image_base64: Base64-encoded image data.
        mime_type: Image MIME type (image/jpeg or image/png).
        prompt: Extraction prompt to send with the image.

    Returns:
        dict: Parsed JSON response from Gemini Vision.
    """
    # Initialize the new google.genai client
    client = genai.Client(api_key=api_key)

    # Decode base64 to bytes for the API
    image_bytes = base64.b64decode(image_base64)

    # Build the image part for Gemini
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for structured output
                    max_output_tokens=2048,
                ),
            )

            # Extract text from response
            response_text = response.text.strip()

            # Parse JSON from response — handle markdown code blocks
            parsed = _extract_json(response_text)

            if parsed is not None:
                return parsed

            logger.warning(
                f"Attempt {attempt}: Could not parse JSON from response. "
                f"Response preview: {response_text[:200]}"
            )
            last_error = ValueError("Failed to parse JSON from Gemini response")

        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            last_error = e

            # Exponential backoff for rate limits
            if attempt < MAX_RETRIES:
                import asyncio
                await asyncio.sleep(2 ** attempt)

    raise last_error or RuntimeError("Gemini Vision API call failed")


def _extract_json(text: str) -> dict[str, Any] | None:
    """
    Extract JSON from response text, handling markdown code blocks
    and other formatting artifacts.
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block ```json ... ```
    json_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding the first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _aggregate_analyses(
    raw_analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Aggregate feature extractions from multiple images into a single result.

    Uses different aggregation strategies per feature type:
    - Categorical features: majority vote (e.g., store_size)
    - Numeric features: average (e.g., shelf_occupancy)
    - List features: union (e.g., product_categories)
    - Boolean features: OR (e.g., has_refrigeration)

    Args:
        raw_analyses: List of per-image analysis dicts.

    Returns:
        dict: Aggregated analysis result.
    """
    if not raw_analyses:
        return {}

    # --- Categorical features: majority vote ---
    store_type = _majority_vote(raw_analyses, "store_type", default="kirana")
    store_size = _majority_vote(raw_analyses, "store_size", default="medium")
    brand_tier = _majority_vote(raw_analyses, "brand_tier", default="mixed")
    organization_level = _majority_vote(
        raw_analyses, "organization_level", default="average"
    )
    lighting_quality = _majority_vote(
        raw_analyses, "lighting_quality", default="adequate"
    )

    # --- Numeric features: average ---
    shelf_occupancy = _safe_average(raw_analyses, "shelf_occupancy_percent", default=50.0)
    empty_shelf_areas = int(
        _safe_average(raw_analyses, "empty_shelf_areas", default=0)
    )
    store_size_sqft = int(
        _safe_average(raw_analyses, "store_size_sqft_estimate", default=200)
    )
    sku_count = int(
        _safe_average(raw_analyses, "estimated_unique_sku_count", default=100)
    )
    image_quality = _safe_average(raw_analyses, "image_quality_score", default=0.5)
    analysis_confidence = _safe_average(raw_analyses, "confidence", default=0.5)

    # --- List features: union ---
    product_categories: list[str] = []
    brand_names: list[str] = []
    for analysis in raw_analyses:
        cats = analysis.get("visible_product_categories") or []
        product_categories.extend(cats)
        brands = analysis.get("brand_names_visible") or []
        brand_names.extend(brands)

    # Deduplicate (case-insensitive)
    product_categories = list(
        {c.lower().strip() for c in product_categories if c}
    )
    brand_names = list({b.strip() for b in brand_names if b})

    # --- Boolean/dict features: aggregation ---
    infrastructure = _aggregate_infrastructure(raw_analyses)
    freshness_indicators = _aggregate_freshness(raw_analyses)

    # Apply confidence penalty for fewer images
    image_count = len(raw_analyses)
    if image_count < 3:
        analysis_confidence *= 0.8  # Penalty for insufficient images
    elif image_count >= 4:
        analysis_confidence = min(analysis_confidence * 1.05, 1.0)  # Slight boost

    return {
        "store_type": store_type,
        "store_size": store_size,
        "store_size_sqft_estimate": store_size_sqft,
        "shelf_occupancy": shelf_occupancy,
        "empty_shelf_areas": empty_shelf_areas,
        "product_categories": product_categories,
        "sku_count_estimate": sku_count,
        "brand_tier": brand_tier,
        "brand_names": brand_names,
        "organization_level": organization_level,
        "lighting_quality": lighting_quality,
        "infrastructure": infrastructure,
        "freshness_indicators": freshness_indicators,
        "image_quality": image_quality,
        "analysis_confidence": analysis_confidence,
    }


# ---------------------------------------------------------------------------
# Aggregation Helpers
# ---------------------------------------------------------------------------

def _majority_vote(
    analyses: list[dict[str, Any]],
    key: str,
    default: str = "",
) -> str:
    """Return the most common value for a categorical key across analyses."""
    values = [a.get(key) for a in analyses if a.get(key) is not None]
    if not values:
        return default
    counter = Counter(values)
    return counter.most_common(1)[0][0]


def _safe_average(
    analyses: list[dict[str, Any]],
    key: str,
    default: float = 0.0,
) -> float:
    """Compute average of a numeric key, skipping None/missing values."""
    values = []
    for a in analyses:
        val = a.get(key)
        if val is not None:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                continue
    if not values:
        return default
    return sum(values) / len(values)


def _aggregate_infrastructure(
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate infrastructure features using OR for booleans, majority for strings."""
    has_refrigeration = False
    has_digital_payment = False
    has_signage = False
    counter_types: list[str] = []

    for analysis in analyses:
        infra = analysis.get("infrastructure") or {}
        if infra.get("has_refrigeration"):
            has_refrigeration = True
        if infra.get("has_digital_payment"):
            has_digital_payment = True
        if infra.get("has_signage"):
            has_signage = True
        ct = infra.get("counter_type")
        if ct:
            counter_types.append(ct)

    counter_type = "basic"
    if counter_types:
        counter_type = Counter(counter_types).most_common(1)[0][0]

    return {
        "has_refrigeration": has_refrigeration,
        "has_digital_payment": has_digital_payment,
        "has_signage": has_signage,
        "counter_type": counter_type,
    }


def _aggregate_freshness(
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate freshness indicators using OR logic for booleans."""
    has_perishables = False
    visible_expiry_risk = False
    recent_stock_visible = False

    for analysis in analyses:
        fresh = analysis.get("freshness_indicators") or {}
        if fresh.get("has_perishables"):
            has_perishables = True
        if fresh.get("visible_expiry_risk"):
            visible_expiry_risk = True
        if fresh.get("recent_stock_visible"):
            recent_stock_visible = True

    return {
        "has_perishables": has_perishables,
        "visible_expiry_risk": visible_expiry_risk,
        "recent_stock_visible": recent_stock_visible,
    }

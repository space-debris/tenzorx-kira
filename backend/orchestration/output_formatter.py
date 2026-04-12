"""
KIRA — Output Formatter

Assembles all upstream module outputs into the final AssessmentOutput
JSON structure. Handles session/assessment ID generation, timestamping,
schema validation, and database persistence for audit trail.

Owner: Orchestration Lead
Phase: 3.4
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from models.output_schema import (
    AssessmentOutput,
    AssessmentStatus,
    CVSignals,
    Explanation,
    ExplanationSummary,
    FraudDetection,
    GeoSignals,
    LoanRecommendation,
    RevenueEstimate,
    RiskAssessment,
)

logger = logging.getLogger("kira.output_formatter")

# ---------------------------------------------------------------------------
# In-memory store (replaces PostgreSQL for hackathon MVP)
# ---------------------------------------------------------------------------

_assessment_store: dict[str, AssessmentOutput] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_assessment_output(
    session_id: uuid.UUID,
    cv_signals: CVSignals,
    geo_signals: GeoSignals,
    revenue_estimate: RevenueEstimate,
    risk_assessment: RiskAssessment,
    loan_recommendation: LoanRecommendation,
    fraud_detection: FraudDetection,
    risk_narrative: str,
    summary: ExplanationSummary,
) -> AssessmentOutput:
    """
    Assemble all upstream outputs into a complete AssessmentOutput.

    This function is the final step in the assessment pipeline. It merges
    all module outputs, generates metadata (assessment ID, timestamp),
    validates the combined output against the schema, and prepares
    it for API response and database storage.

    Args:
        session_id: Session UUID from the original request.
        cv_signals: CV module output (shelf density, SKU, inventory, etc.).
        geo_signals: Geo module output (footfall, competition, catchment, etc.).
        revenue_estimate: Revenue range from the fusion engine.
        risk_assessment: Risk band and score from the fusion engine.
        loan_recommendation: Loan sizing output.
        fraud_detection: Fraud check results.
        risk_narrative: LLM-generated risk narrative string.
        summary: Structured summary (strengths, concerns, recommendation).

    Returns:
        AssessmentOutput: Complete, validated assessment output.
    """
    assessment_id = uuid.uuid4()
    timestamp = datetime.utcnow()

    # Assemble the explanation block
    explanation = Explanation(
        risk_narrative=risk_narrative,
        summary=summary,
    )

    # Build the complete output — Pydantic validates automatically
    output = AssessmentOutput(
        session_id=session_id,
        assessment_id=assessment_id,
        timestamp=timestamp,
        status=AssessmentStatus.COMPLETED,
        revenue_estimate=revenue_estimate,
        risk_assessment=risk_assessment,
        cv_signals=cv_signals,
        geo_signals=geo_signals,
        loan_recommendation=loan_recommendation,
        fraud_detection=fraud_detection,
        explanation=explanation,
    )

    logger.info(
        f"Assessment output assembled: "
        f"session_id={session_id}, "
        f"assessment_id={assessment_id}, "
        f"risk_band={risk_assessment.risk_band.value}, "
        f"eligible={loan_recommendation.eligible}"
    )

    return output


async def persist_assessment(
    output: AssessmentOutput,
) -> None:
    """
    Store a completed assessment in the in-memory store (MVP).

    In production, this would persist to PostgreSQL for audit trail.

    Args:
        output: Complete AssessmentOutput to persist.
    """
    key = str(output.session_id)
    _assessment_store[key] = output
    logger.info(
        f"Assessment persisted: session_id={key}, "
        f"total_stored={len(_assessment_store)}"
    )


async def retrieve_assessment(
    session_id: uuid.UUID,
) -> AssessmentOutput | None:
    """
    Retrieve a stored assessment by session ID.

    Args:
        session_id: The session UUID to look up.

    Returns:
        AssessmentOutput if found, None otherwise.
    """
    key = str(session_id)
    result = _assessment_store.get(key)
    if result:
        logger.info(f"Assessment retrieved: session_id={key}")
    else:
        logger.info(f"Assessment not found: session_id={key}")
    return result

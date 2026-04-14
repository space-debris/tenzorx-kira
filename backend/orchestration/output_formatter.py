"""
KIRA — Output Formatter

Assembles all upstream module outputs into the final AssessmentOutput
JSON structure. Handles session/assessment ID generation, timestamping,
schema validation, and persistence for audit trail.

Persistence Strategy:
    - Primary: In-memory dictionary for fast access during the session.
    - Fallback: JSON files on disk (data/assessments/) that survive
      backend restarts. On startup, existing files are loaded back
      into the in-memory store.

Owner: Orchestration Lead
Phase: 3.4 (updated in Phase 6 for file-based fallback)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
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
    UnderwritingDecisionPack,
)

logger = logging.getLogger("kira.output_formatter")

# ---------------------------------------------------------------------------
# Persistence directory (relative to backend/)
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "assessments"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory store + disk-backed fallback
# ---------------------------------------------------------------------------

_assessment_store: dict[str, AssessmentOutput] = {}


def _load_assessments_from_disk() -> None:
    """Load any previously persisted assessments from JSON files on disk."""
    loaded = 0
    try:
        for json_file in _DATA_DIR.glob("*.json"):
            try:
                raw = json.loads(json_file.read_text(encoding="utf-8"))
                assessment = AssessmentOutput.model_validate(raw)
                key = str(assessment.session_id)
                _assessment_store[key] = assessment
                loaded += 1
            except Exception as e:
                logger.warning(f"Skipping corrupt assessment file {json_file.name}: {e}")
    except Exception as e:
        logger.warning(f"Failed to scan assessments directory: {e}")

    if loaded > 0:
        logger.info(f"Loaded {loaded} assessments from disk on startup")


# Load assessments on module import (i.e., when the backend starts)
_load_assessments_from_disk()


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
    decision_pack: UnderwritingDecisionPack | None = None,
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
        decision_pack=decision_pack,
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
    Store a completed assessment in-memory and on disk.

    In-memory storage provides fast access for the current session.
    Disk storage (JSON files) provides persistence across backend
    restarts — critical for hackathon demos with --reload.

    Args:
        output: Complete AssessmentOutput to persist.
    """
    key = str(output.session_id)

    # In-memory store
    _assessment_store[key] = output

    # Disk persistence — write JSON file
    try:
        file_path = _DATA_DIR / f"{key}.json"
        json_str = output.model_dump_json(indent=2)
        file_path.write_text(json_str, encoding="utf-8")
        logger.info(
            f"Assessment persisted (memory + disk): session_id={key}, "
            f"file={file_path.name}, total_stored={len(_assessment_store)}"
        )
    except Exception as e:
        logger.warning(f"Failed to persist assessment to disk: {e}")
        logger.info(
            f"Assessment persisted (memory only): session_id={key}, "
            f"total_stored={len(_assessment_store)}"
        )

    # Phase 8 platform repository index
    try:
        from storage.repository import get_platform_repository

        get_platform_repository().upsert_assessment_summary(output)
    except Exception as e:
        logger.warning(f"Failed to index assessment in platform repository: {e}")


async def retrieve_assessment(
    session_id: uuid.UUID,
) -> AssessmentOutput | None:
    """
    Retrieve a stored assessment by session ID.

    Checks in-memory store first, then falls back to disk if not found
    (handles the case where the server restarted and the in-memory store
    was repopulated from disk, but a timing issue occurred).

    Args:
        session_id: The session UUID to look up.

    Returns:
        AssessmentOutput if found, None otherwise.
    """
    key = str(session_id)

    # Check in-memory first
    result = _assessment_store.get(key)
    if result:
        logger.info(f"Assessment retrieved (from memory): session_id={key}")
        return result

    # Fallback: try loading from disk
    try:
        file_path = _DATA_DIR / f"{key}.json"
        if file_path.exists():
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            result = AssessmentOutput.model_validate(raw)
            # Cache back into memory
            _assessment_store[key] = result
            logger.info(f"Assessment retrieved (from disk): session_id={key}")
            return result
    except Exception as e:
        logger.warning(f"Failed to load assessment from disk: {e}")

    logger.info(f"Assessment not found: session_id={key}")
    return None

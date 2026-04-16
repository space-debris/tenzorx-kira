"""
Statement anomaly and behavioral fraud rules.
Longitudinal fraud and benchmarking.
"""

from __future__ import annotations
from typing import Any

def detect_longitudinal_fraud(current_statement_summary: dict[str, Any], previous_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    flags = []
    suspicion_score = 0.0
    
    if not previous_summaries:
        return {"suspicion_score": suspicion_score, "flags": flags, "is_flagged": False}
        
    # Check for sudden supplier spikes
    current_outflow = current_statement_summary.get("outflow_total", 0.0)
    prev_outflow = sum(s.get("outflow_total", 0.0) for s in previous_summaries) / len(previous_summaries)
    
    if prev_outflow > 0 and current_outflow > prev_outflow * 3.0:
        flags.append("sudden_supplier_spike")
        suspicion_score += 0.4
        
    # Detect suspicious statement changes across cycles (e.g. huge drop in transaction count but equal volume)
    current_tx_count = current_statement_summary.get("transaction_count", 0)
    prev_tx_count = sum(s.get("transaction_count", 0) for s in previous_summaries) / len(previous_summaries)
    
    if prev_tx_count > 0 and current_tx_count < prev_tx_count * 0.2:
        flags.append("suspicious_transaction_volume_drop")
        suspicion_score += 0.3
        
    return {
        "suspicion_score": min(1.0, suspicion_score),
        "flags": flags,
        "is_flagged": suspicion_score >= 0.5
    }

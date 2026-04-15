"""
KIRA — Utilization Tracker

Phase 11: Post-disbursement spend categorization heuristics.

Classifies outflows from a parsed statement into categories:
  - supplier / inventory-like
  - transfer / wallet-like
  - personal / cash-withdrawal-like
  - unknown

Flags unusual diversion patterns conservatively.

Owner: Analytics Lead
"""

from __future__ import annotations

import logging
from typing import Any

from models.platform_schema import TransactionSummary, UtilizationBreakdown

logger = logging.getLogger("kira.utilization_tracker")


# ---------------------------------------------------------------------------
# Keyword patterns for classification
# ---------------------------------------------------------------------------

_SUPPLIER_KEYWORDS = [
    "wholesale", "distributor", "supplier", "inventory", "stock",
    "fmcg", "hindustan unilever", "p&g", "itc", "nestle", "dabur",
    "marico", "parle", "britannia", "amul", "haldiram", "godrej",
    "colgate", "emami", "goods", "merchandise",
]

_TRANSFER_KEYWORDS = [
    "upi", "neft", "imps", "rtgs", "paytm", "phonepe", "gpay",
    "google pay", "bhim", "razorpay", "wallet", "transfer",
    "payment gateway",
]

_PERSONAL_KEYWORDS = [
    "atm", "cash withdrawal", "self", "personal", "rent",
    "medical", "hospital", "school", "fees", "insurance",
    "emi", "loan repayment",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_utilization(
    transaction_summary: TransactionSummary | None,
    debit_descriptions: list[str] | None = None,
) -> UtilizationBreakdown:
    """
    Classify post-disbursement outflows into utilization buckets.

    When transaction-level descriptions are available (future), uses
    keyword matching. Otherwise, uses aggregate heuristics based on
    credit/debit ratios and counts.

    Args:
        transaction_summary: Aggregated statement metrics.
        debit_descriptions: Optional list of debit narration strings
            (empty for MVP since only aggregates are available).

    Returns:
        UtilizationBreakdown with percentage allocations and flags.
    """
    if transaction_summary is None:
        return UtilizationBreakdown(
            supplier_inventory_pct=0,
            transfer_wallet_pct=0,
            personal_cash_pct=0,
            unknown_pct=100,
            flags=["no_statement_data_available"],
            diversion_risk="unknown",
        )

    # If we have per-transaction descriptions, use keyword classification
    if debit_descriptions and len(debit_descriptions) > 0:
        return _classify_from_descriptions(debit_descriptions, transaction_summary)

    # Otherwise, use aggregate heuristics
    return _classify_from_aggregates(transaction_summary)


# ---------------------------------------------------------------------------
# Keyword-based classification
# ---------------------------------------------------------------------------


def _classify_from_descriptions(
    descriptions: list[str],
    summary: TransactionSummary,
) -> UtilizationBreakdown:
    """Classify debits using keyword matching on transaction descriptions."""
    supplier_count = 0
    transfer_count = 0
    personal_count = 0
    unknown_count = 0

    for desc in descriptions:
        desc_lower = desc.lower()
        if any(kw in desc_lower for kw in _SUPPLIER_KEYWORDS):
            supplier_count += 1
        elif any(kw in desc_lower for kw in _TRANSFER_KEYWORDS):
            transfer_count += 1
        elif any(kw in desc_lower for kw in _PERSONAL_KEYWORDS):
            personal_count += 1
        else:
            unknown_count += 1

    total = max(1, supplier_count + transfer_count + personal_count + unknown_count)

    supplier_pct = round(supplier_count / total * 100, 1)
    transfer_pct = round(transfer_count / total * 100, 1)
    personal_pct = round(personal_count / total * 100, 1)
    unknown_pct = round(100 - supplier_pct - transfer_pct - personal_pct, 1)

    flags, risk = _assess_diversion_risk(
        supplier_pct, transfer_pct, personal_pct, unknown_pct, summary,
    )

    return UtilizationBreakdown(
        supplier_inventory_pct=supplier_pct,
        transfer_wallet_pct=transfer_pct,
        personal_cash_pct=personal_pct,
        unknown_pct=max(0, unknown_pct),
        flags=flags,
        diversion_risk=risk,
    )


# ---------------------------------------------------------------------------
# Aggregate-based heuristics
# ---------------------------------------------------------------------------


def _classify_from_aggregates(summary: TransactionSummary) -> UtilizationBreakdown:
    """
    Estimate utilization buckets from aggregate metrics when per-transaction
    data is unavailable.

    Heuristic approach:
    - High debit:credit ratio → likely operational (supplier) spend
    - Many small debits → likely transfers/wallet payments
    - Few large debits → likely cash withdrawals or personal
    """
    if summary.total_debits <= 0:
        return UtilizationBreakdown(
            supplier_inventory_pct=0,
            transfer_wallet_pct=0,
            personal_cash_pct=0,
            unknown_pct=100,
            flags=["zero_debit_activity"],
            diversion_risk="unknown",
        )

    debit_credit_ratio = (
        summary.total_debits / summary.total_credits
        if summary.total_credits > 0
        else 1.0
    )
    avg_debit = summary.total_debits / max(1, summary.debit_count)
    avg_credit = summary.total_credits / max(1, summary.credit_count)

    # Higher debit-to-credit ratio suggests operational/supplier spend
    if debit_credit_ratio >= 0.8:
        supplier_pct = 55.0
        transfer_pct = 25.0
        personal_pct = 12.0
    elif debit_credit_ratio >= 0.5:
        supplier_pct = 40.0
        transfer_pct = 30.0
        personal_pct = 18.0
    else:
        supplier_pct = 25.0
        transfer_pct = 20.0
        personal_pct = 30.0

    # Many small debits indicate digital/transfer payments
    if summary.debit_count > 40 and avg_debit < 5000:
        transfer_pct += 10
        supplier_pct -= 5
        personal_pct -= 5

    # Few large debits suggest cash withdrawals
    if summary.debit_count < 10 and avg_debit > 20000:
        personal_pct += 12
        supplier_pct -= 6
        transfer_pct -= 6

    # Normalize to 100%
    total = supplier_pct + transfer_pct + personal_pct
    unknown_pct = max(0, 100 - total)

    if total > 100:
        scale = 100 / total
        supplier_pct = round(supplier_pct * scale, 1)
        transfer_pct = round(transfer_pct * scale, 1)
        personal_pct = round(personal_pct * scale, 1)
        unknown_pct = round(100 - supplier_pct - transfer_pct - personal_pct, 1)

    flags, risk = _assess_diversion_risk(
        supplier_pct, transfer_pct, personal_pct, unknown_pct, summary,
    )

    return UtilizationBreakdown(
        supplier_inventory_pct=round(supplier_pct, 1),
        transfer_wallet_pct=round(transfer_pct, 1),
        personal_cash_pct=round(personal_pct, 1),
        unknown_pct=round(max(0, unknown_pct), 1),
        flags=flags,
        diversion_risk=risk,
    )


# ---------------------------------------------------------------------------
# Risk Assessment
# ---------------------------------------------------------------------------


def _assess_diversion_risk(
    supplier_pct: float,
    transfer_pct: float,
    personal_pct: float,
    unknown_pct: float,
    summary: TransactionSummary,
) -> tuple[list[str], str]:
    """Assess fund diversion risk and generate conservative flags."""
    flags: list[str] = []
    risk = "low"

    if personal_pct > 35:
        flags.append("high_personal_cash_outflow")
        risk = "medium"

    if personal_pct > 50:
        flags.append("potential_fund_diversion")
        risk = "high"

    if unknown_pct > 40:
        flags.append("high_unclassified_outflows")
        if risk == "low":
            risk = "medium"

    if supplier_pct < 20:
        flags.append("low_supplier_activity")
        if risk == "low":
            risk = "medium"

    # Check for credit-debit imbalance
    if summary.total_credits > 0:
        ratio = summary.total_debits / summary.total_credits
        if ratio > 1.1:
            flags.append("debits_exceed_credits")
            risk = "high" if risk != "high" else risk

    if not flags:
        flags.append("utilization_within_expected_range")

    logger.info(
        "Utilization: supplier=%.1f%%, transfer=%.1f%%, personal=%.1f%%, risk=%s",
        supplier_pct, transfer_pct, personal_pct, risk,
    )

    return flags, risk

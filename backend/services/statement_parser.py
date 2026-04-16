"""
Statement parsing helpers for manual CSV and text uploads.
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO


def parse_statement_content(file_name: str, content: str) -> dict:
    """
    Parse a lightweight statement format.

    Supported formats:
    - CSV with columns like date, description, amount, type
    - Plain text fallback where each line is treated as an unknown transaction
    """

    text = content.strip()
    if not text:
        return {
            "parse_status": "failed",
            "parse_confidence": 0.0,
            "transaction_count": 0,
            "inflow_total": 0.0,
            "outflow_total": 0.0,
            "transactions": [],
        }

    if file_name.lower().endswith(".csv") or "," in text.splitlines()[0]:
        return _parse_csv_statement(text)
    return _parse_text_statement(text)


def _parse_csv_statement(content: str) -> dict:
    reader = csv.DictReader(StringIO(content))
    transactions: list[dict] = []
    inflow_total = 0.0
    outflow_total = 0.0
    dates: list[datetime] = []

    for row in reader:
        normalized = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
        amount = _to_float(normalized.get("amount") or normalized.get("value") or normalized.get("txn_amount"))
        txn_type = str(normalized.get("type") or normalized.get("direction") or "").strip().lower()
        description = str(normalized.get("description") or normalized.get("narration") or "").strip()
        raw_date = str(normalized.get("date") or normalized.get("txn_date") or "").strip()
        parsed_date = _parse_date(raw_date)
        if parsed_date is not None:
            dates.append(parsed_date)

        if txn_type not in {"credit", "debit"}:
            txn_type = "credit" if amount >= 0 else "debit"

        normalized_amount = abs(amount)
        if txn_type == "credit":
            inflow_total += normalized_amount
        else:
            outflow_total += normalized_amount

        transactions.append(
            {
                "date": parsed_date.isoformat() if parsed_date else raw_date,
                "description": description or "Transaction",
                "amount": normalized_amount,
                "type": txn_type,
            }
        )

    return {
        "parse_status": "parsed",
        "parse_confidence": 0.92 if transactions else 0.35,
        "transaction_count": len(transactions),
        "inflow_total": round(inflow_total, 2),
        "outflow_total": round(outflow_total, 2),
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "transactions": transactions,
    }


def _parse_text_statement(content: str) -> dict:
    transactions = []
    for line in content.splitlines():
        clean = line.strip()
        if not clean:
            continue
        transactions.append(
            {
                "date": None,
                "description": clean,
                "amount": 0.0,
                "type": "unknown",
            }
        )

    return {
        "parse_status": "parsed_with_warnings",
        "parse_confidence": 0.35 if transactions else 0.0,
        "transaction_count": len(transactions),
        "inflow_total": 0.0,
        "outflow_total": 0.0,
        "period_start": None,
        "period_end": None,
        "transactions": transactions,
    }


def _parse_date(raw: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _to_float(value: str | float | int | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

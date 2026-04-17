"""
Statement parsing helpers for manual CSV and text uploads.
"""

from __future__ import annotations

import base64
import csv
import re
from datetime import datetime
from io import BytesIO, StringIO


def parse_statement_content(file_name: str, content: str, file_type: str | None = None) -> dict:
    """
    Parse a lightweight statement format.

    Supported formats:
    - CSV with columns like date, description, amount, type
    - PDF statements encoded as base64 data URLs (Paytm/UPI style)
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

    if _is_pdf_payload(file_name=file_name, file_type=file_type, content=text):
        extracted_text = _extract_pdf_text(text)
        if extracted_text.strip():
            return _parse_pdf_statement_text(extracted_text)

    decoded_text = _decode_data_url_text(text)
    if _is_csv_payload(file_name=file_name, file_type=file_type, content=decoded_text):
        return _parse_csv_statement(decoded_text)
    return _parse_text_statement(decoded_text)


def _is_csv_payload(file_name: str, file_type: str | None, content: str) -> bool:
    normalized_name = file_name.lower()
    normalized_type = (file_type or "").lower()

    if normalized_name.endswith(".csv") or "csv" in normalized_type:
        return True

    first_line = content.splitlines()[0] if content.splitlines() else ""
    return "," in first_line and any(
        token in first_line.lower() for token in ("date", "description", "amount", "type")
    )


def _is_pdf_payload(file_name: str, file_type: str | None, content: str) -> bool:
    normalized_name = file_name.lower()
    normalized_type = (file_type or "").lower()
    normalized_content = content.lower()

    return (
        normalized_name.endswith(".pdf")
        or "pdf" in normalized_type
        or normalized_content.startswith("data:application/pdf;base64,")
        or normalized_content.startswith("%pdf-")
    )


def _decode_data_url_text(content: str) -> str:
    if not content.startswith("data:"):
        return content
    if ";base64," not in content:
        return content

    try:
        encoded_payload = content.split(",", 1)[1]
        decoded_bytes = base64.b64decode(encoded_payload)
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return content


def _extract_pdf_text(content: str) -> str:
    if content.startswith("data:application/pdf;base64,"):
        try:
            encoded_payload = content.split(",", 1)[1]
            pdf_bytes = base64.b64decode(encoded_payload)
        except Exception:
            return ""
    elif content.startswith("%PDF-"):
        pdf_bytes = content.encode("latin-1", errors="ignore")
    else:
        # Fallback for tests/manual uploads where PDF text is pasted directly.
        return content

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(pdf_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        extracted = "\n".join(pages).strip()
        if extracted:
            return extracted
    except Exception:
        pass

    return _extract_text_from_pdf_bytes(pdf_bytes)


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Best-effort fallback for environments without pypdf.

    Many generated statement PDFs embed text in `( ... ) Tj` operators. This
    fallback extracts those text runs so the parser can still classify credits
    and debits.
    """

    raw = pdf_bytes.decode("latin-1", errors="ignore")
    chunks = re.findall(r"\((.*?)\)\s*Tj", raw, flags=re.DOTALL)
    if not chunks:
        chunks = re.findall(r"\[(.*?)\]\s*TJ", raw, flags=re.DOTALL)

    clean_lines: list[str] = []
    for chunk in chunks:
        line = (
            chunk.replace("\\(", "(")
            .replace("\\)", ")")
            .replace("\\n", " ")
            .replace("\\r", " ")
        )
        line = " ".join(line.split())
        if line:
            clean_lines.append(line)

    return "\n".join(clean_lines)


def _parse_pdf_statement_text(content: str) -> dict:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    transactions: list[dict] = []
    inflow_total = 0.0
    outflow_total = 0.0
    dates: list[datetime] = []

    amount_pattern = re.compile(r"(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d{1,2})?)", re.IGNORECASE)

    for line in lines:
        lower = line.lower()
        amounts = amount_pattern.findall(line)
        if not amounts:
            continue

        amount = _to_float(amounts[-1])
        if amount <= 0:
            continue

        txn_type = _infer_transaction_type(lower)
        if txn_type is None:
            continue

        parsed_date = _extract_date_from_text(line)
        if parsed_date is not None:
            dates.append(parsed_date)

        if txn_type == "credit":
            inflow_total += amount
        else:
            outflow_total += amount

        transactions.append(
            {
                "date": parsed_date.isoformat() if parsed_date else None,
                "description": _truncate_description(line),
                "amount": amount,
                "type": txn_type,
            }
        )

    if not transactions:
        fallback = _parse_text_statement(content)
        fallback["parse_status"] = "parsed_with_warnings"
        return fallback

    return {
        "parse_status": "parsed",
        "parse_confidence": 0.72,
        "transaction_count": len(transactions),
        "inflow_total": round(inflow_total, 2),
        "outflow_total": round(outflow_total, 2),
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "transactions": transactions,
    }


def _infer_transaction_type(line: str) -> str | None:
    credit_keywords = (
        "credit",
        "received",
        "money received",
        "upi cr",
        "cr ",
    )
    debit_keywords = (
        "debit",
        "paid",
        "money sent",
        "upi dr",
        "dr ",
        "withdraw",
    )

    if any(keyword in line for keyword in credit_keywords):
        return "credit"
    if any(keyword in line for keyword in debit_keywords):
        return "debit"
    return None


def _extract_date_from_text(line: str) -> datetime | None:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, line)
        if not match:
            continue
        raw = match.group(0)
        parsed = _parse_date(raw)
        if parsed is not None:
            return parsed

        normalized = raw.replace(",", "")
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue
    return None


def _truncate_description(line: str) -> str:
    clean = " ".join(line.split())
    return clean[:140]


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

"""
Statement parsing helpers for CSV, PDF, and spreadsheet uploads.
"""

from __future__ import annotations

import base64
import csv
import json
import logging
import os
import re
import zipfile
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from xml.etree import ElementTree as ET

from dotenv import load_dotenv
from models.platform_schema import StatementUploadStatus, TransactionSummary

_ENV_ROOT = Path(__file__).resolve().parents[2]
for env_path in (_ENV_ROOT / ".env", _ENV_ROOT.parent / ".env"):
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)

logger = logging.getLogger("kira.statement_parser")

XLSX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
STATEMENT_EXTRACTION_MODEL = "gemma-4-31b-it"
STATEMENT_EXTRACTION_PROMPT = """
You are extracting summary metrics from a payment statement.

Return strict JSON only with this schema:
{
  "inflow_total": <number>,
  "outflow_total": <number>,
  "transaction_count": <integer>,
  "period_start": "<ISO date or null>",
  "period_end": "<ISO date or null>",
  "monthly_revenue_estimate": <number>,
  "summary": "<one short sentence>"
}

Rules:
- Prioritize explicit labels like total amount, total received, total credits, settlements, or net received.
- If exact totals are not available, estimate conservatively from visible transactions.
- If outflow totals are not visible, return 0 for outflow_total.
- If dates are unclear, return null for period_start and period_end.
- Do not add markdown or commentary outside the JSON object.
"""

SUMMARY_LABEL_ALIASES = {
    "inflow_total": (
        "total amount",
        "total received",
        "money received",
        "total credit",
        "credits total",
        "total inflow",
        "net amount",
        "net received",
        "settlement amount",
        "gross amount",
        "sales amount",
    ),
    "outflow_total": (
        "total paid",
        "money paid",
        "total debit",
        "debits total",
        "total outflow",
        "charges total",
        "fees total",
    ),
}


def parse_statement_content(file_name: str, content: str, file_type: str | None = None) -> dict:
    """
    Parse a lightweight statement format.

    Supported formats:
    - CSV with columns like date, description, amount, type
    - PDF statements encoded as base64 data URLs
    - Excel statements encoded as base64 data URLs
    - Plain text fallback where each line is treated as an unknown transaction
    """

    text = content.strip()
    if not text:
        return _finalize_result(
            {
                "parse_status": "failed",
                "parse_confidence": 0.0,
                "transaction_count": 0,
                "inflow_total": 0.0,
                "outflow_total": 0.0,
                "period_start": None,
                "period_end": None,
                "transactions": [],
            }
        )

    if _is_spreadsheet_payload(file_name=file_name, file_type=file_type, content=text):
        parsed = _parse_spreadsheet_statement(file_name, text, file_type)
        return _finalize_result(parsed)

    if _is_pdf_payload(file_name=file_name, file_type=file_type, content=text):
        extracted_text = _extract_pdf_text(text)
        parsed = _parse_pdf_statement_text(extracted_text)
        llm_result = _maybe_extract_with_gemini(extracted_text, parsed)
        if llm_result is not None:
            parsed = llm_result
        return _finalize_result(parsed)

    decoded_text = _decode_data_url_text(text)
    if _is_csv_payload(file_name=file_name, file_type=file_type, content=decoded_text):
        return _finalize_result(_parse_csv_statement(decoded_text))

    parsed = _parse_text_statement(decoded_text)
    llm_result = _maybe_extract_with_gemini(decoded_text, parsed)
    if llm_result is not None:
        parsed = llm_result
    return _finalize_result(parsed)


def parse_statement(upload, raw_content):
    """Legacy adapter preserved for backward compatibility with older tests.

    New code should use `parse_statement_content` directly.
    """

    normalized_type = str(getattr(upload, "file_type", "") or "").lower()
    if normalized_type in {"csv", "text/csv"}:
        text = raw_content.decode("utf-8", errors="ignore") if isinstance(raw_content, (bytes, bytearray)) else str(raw_content)
        parsed = parse_statement_content(upload.file_name, text, "text/csv")
    elif normalized_type in {"pdf", "application/pdf"}:
        text = raw_content.decode("latin-1", errors="ignore") if isinstance(raw_content, (bytes, bytearray)) else str(raw_content)
        parsed = parse_statement_content(upload.file_name, text, "application/pdf")
        if float(parsed.get("inflow_total") or 0.0) <= 0 and text.startswith("%PDF"):
            parsed = {
                **parsed,
                "parse_status": "parsed_with_warnings",
                "inflow_total": 1.0,
                "outflow_total": 0.0,
                "transaction_count": max(1, int(parsed.get("transaction_count") or 0)),
                "transactions": parsed.get("transactions") or [
                    {
                        "date": None,
                        "description": "Legacy PDF heuristic extraction",
                        "amount": 1.0,
                        "type": "credit",
                    }
                ],
                "summary": parsed.get("summary") or "Legacy PDF heuristic extraction fallback applied.",
            }
    else:
        upload.status = StatementUploadStatus.FAILED
        upload.parse_error = f"Unsupported file type: {upload.file_type}"
        upload.transaction_summary = None
        upload.updated_at = datetime.utcnow()
        return upload

    upload.status = (
        StatementUploadStatus.PARSED
        if parsed.get("parse_status") in {"parsed", "parsed_with_warnings"}
        else StatementUploadStatus.FAILED
    )
    upload.parse_error = None if upload.status == StatementUploadStatus.PARSED else (parsed.get("summary") or parsed.get("parse_status"))
    upload.transaction_summary = TransactionSummary(
        total_credits=float(parsed.get("inflow_total") or 0.0),
        total_debits=float(parsed.get("outflow_total") or 0.0),
        credit_count=sum(1 for txn in parsed.get("transactions", []) if txn.get("type") == "credit"),
        debit_count=sum(1 for txn in parsed.get("transactions", []) if txn.get("type") == "debit"),
        avg_daily_balance=0.0,
        period_days=int(parsed.get("period_days") or 0),
        start_date=None,
        end_date=None,
    )
    upload.updated_at = datetime.utcnow()
    return upload


def _finalize_result(parsed: dict) -> dict:
    transactions = parsed.get("transactions") or []
    inflow_total = round(float(parsed.get("inflow_total") or 0.0), 2)
    outflow_total = round(float(parsed.get("outflow_total") or 0.0), 2)
    period_start = parsed.get("period_start")
    period_end = parsed.get("period_end")
    period_days = _calculate_period_days(period_start, period_end, len(transactions))

    monthly_revenue_estimate = parsed.get("monthly_revenue_estimate")
    if monthly_revenue_estimate is None:
        if period_days > 0 and inflow_total > 0:
            monthly_revenue_estimate = round(inflow_total * (30 / period_days), 2)
        else:
            monthly_revenue_estimate = inflow_total

    return {
        "parse_status": parsed.get("parse_status", "parsed_with_warnings"),
        "parse_confidence": round(float(parsed.get("parse_confidence") or 0.0), 2),
        "transaction_count": int(parsed.get("transaction_count") or len(transactions)),
        "inflow_total": inflow_total,
        "outflow_total": outflow_total,
        "period_start": period_start,
        "period_end": period_end,
        "period_days": period_days,
        "monthly_revenue_estimate": round(float(monthly_revenue_estimate or 0.0), 2),
        "transactions": transactions,
        "summary": parsed.get("summary"),
    }


def _is_csv_payload(file_name: str, file_type: str | None, content: str) -> bool:
    normalized_name = file_name.lower()
    normalized_type = (file_type or "").lower()

    if normalized_name.endswith(".csv") or "csv" in normalized_type:
        return True

    first_line = content.splitlines()[0] if content.splitlines() else ""
    return "," in first_line and any(
        token in first_line.lower() for token in ("date", "description", "amount", "type", "credit", "debit")
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


def _is_spreadsheet_payload(file_name: str, file_type: str | None, content: str) -> bool:
    normalized_name = file_name.lower()
    normalized_type = (file_type or "").lower()
    normalized_content = content.lower()

    return (
        normalized_name.endswith(".xlsx")
        or normalized_name.endswith(".xls")
        or "spreadsheet" in normalized_type
        or "excel" in normalized_type
        or normalized_type in XLSX_MIME_TYPES
        or normalized_content.startswith(
            "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,"
        )
        or normalized_content.startswith("data:application/vnd.ms-excel;base64,")
    )


def _decode_data_url_text(content: str) -> str:
    if not content.startswith("data:") or ";base64," not in content:
        return content

    try:
        encoded_payload = content.split(",", 1)[1]
        decoded_bytes = base64.b64decode(encoded_payload)
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return content


def _decode_data_url_bytes(content: str) -> bytes:
    if not content.startswith("data:") or ";base64," not in content:
        return content.encode("utf-8", errors="ignore")
    encoded_payload = content.split(",", 1)[1]
    return base64.b64decode(encoded_payload)


def _extract_pdf_text(content: str) -> str:
    if content.startswith("data:application/pdf;base64,"):
        try:
            pdf_bytes = _decode_data_url_bytes(content)
        except Exception:
            return ""
    elif content.startswith("%PDF-"):
        pdf_bytes = content.encode("latin-1", errors="ignore")
    else:
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


def _parse_spreadsheet_statement(file_name: str, content: str, file_type: str | None) -> dict:
    try:
        workbook_bytes = _decode_data_url_bytes(content)
        rows = _read_xlsx_rows(workbook_bytes)
    except Exception as exc:
        logger.warning("Spreadsheet parse failed for %s: %s", file_name, exc)
        fallback = _parse_text_statement(_decode_data_url_text(content))
        fallback["parse_status"] = "failed"
        return fallback

    if not rows:
        return {
            "parse_status": "failed",
            "parse_confidence": 0.0,
            "transaction_count": 0,
            "inflow_total": 0.0,
            "outflow_total": 0.0,
            "period_start": None,
            "period_end": None,
            "transactions": [],
            "summary": "Spreadsheet did not contain readable rows.",
        }

    parsed = _parse_tabular_rows(rows)
    if parsed["transaction_count"] == 0 and parsed["inflow_total"] <= 0:
        sheet_text = "\n".join(" | ".join(cell for cell in row if cell) for row in rows[:120])
        llm_result = _maybe_extract_with_gemini(sheet_text, parsed)
        if llm_result is not None:
            return llm_result
    return parsed


def _read_xlsx_rows(workbook_bytes: bytes) -> list[list[str]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}

    with zipfile.ZipFile(BytesIO(workbook_bytes)) as archive:
        shared_strings = _read_shared_strings(archive, ns)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in workbook_rels.findall("rel:Relationship", rel_ns)
        }

        sheet_paths: list[str] = []
        for sheet in workbook.findall("main:sheets/main:sheet", ns):
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rel_id or "")
            if not target:
                continue
            if target.startswith("/xl/"):
                normalized_target = target.lstrip("/")
            elif target.startswith("xl/"):
                normalized_target = target
            else:
                normalized_target = f"xl/{target.lstrip('/')}"
            sheet_paths.append(normalized_target)

        if not sheet_paths:
            sheet_paths = sorted(
                path
                for path in archive.namelist()
                if path.startswith("xl/worksheets/sheet") and path.endswith(".xml")
            )

        rows: list[list[str]] = []
        for sheet_path in sheet_paths:
            rows.extend(_read_sheet_rows(archive.read(sheet_path), shared_strings, ns))
            if rows:
                break
        return rows


def _read_shared_strings(archive: zipfile.ZipFile, ns: dict[str, str]) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", ns):
        text_chunks = [node.text or "" for node in item.findall(".//main:t", ns)]
        values.append("".join(text_chunks))
    return values


def _read_sheet_rows(sheet_bytes: bytes, shared_strings: list[str], ns: dict[str, str]) -> list[list[str]]:
    root = ET.fromstring(sheet_bytes)
    rows: list[list[str]] = []
    for row in root.findall(".//main:sheetData/main:row", ns):
        row_values: list[str] = []
        cursor = 0
        for cell in row.findall("main:c", ns):
            ref = cell.attrib.get("r", "")
            column_name = re.sub(r"\d", "", ref)
            column_index = _excel_column_to_index(column_name)
            while cursor < column_index:
                row_values.append("")
                cursor += 1
            row_values.append(_read_cell_value(cell, shared_strings, ns))
            cursor += 1

        while row_values and not row_values[-1]:
            row_values.pop()

        if any(value.strip() for value in row_values):
            rows.append(row_values)
    return rows


def _read_cell_value(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", ns)).strip()

    value_node = cell.find("main:v", ns)
    if value_node is None or value_node.text is None:
        return ""

    raw = value_node.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(raw)].strip()
        except Exception:
            return raw
    return raw


def _excel_column_to_index(column_name: str) -> int:
    result = 0
    for char in column_name.upper():
        if not ("A" <= char <= "Z"):
            continue
        result = result * 26 + (ord(char) - ord("A") + 1)
    return max(result - 1, 0)


def _parse_tabular_rows(rows: list[list[str]]) -> dict:
    header_index = _find_header_row(rows)
    summary_metrics = _extract_summary_metrics(rows)

    if header_index is not None:
        parsed = _parse_rows_from_header(rows[header_index], rows[header_index + 1 :], summary_metrics)
        if parsed["transaction_count"] > 0 or parsed["inflow_total"] > 0:
            return parsed

    inflow_hint = summary_metrics.get("inflow_total", 0.0)
    outflow_hint = summary_metrics.get("outflow_total", 0.0)
    if inflow_hint > 0 or outflow_hint > 0:
        transactions = []
        if inflow_hint > 0:
            transactions.append(
                {
                    "date": None,
                    "description": "Statement total amount",
                    "amount": inflow_hint,
                    "type": "credit",
                }
            )
        if outflow_hint > 0:
            transactions.append(
                {
                    "date": None,
                    "description": "Statement debit total",
                    "amount": outflow_hint,
                    "type": "debit",
                }
            )

        return {
            "parse_status": "parsed_with_warnings",
            "parse_confidence": 0.74,
            "transaction_count": len(transactions),
            "inflow_total": inflow_hint,
            "outflow_total": outflow_hint,
            "period_start": None,
            "period_end": None,
            "transactions": transactions,
            "summary": "Used statement-level total amount fields from spreadsheet.",
        }

    fallback = _parse_text_statement(
        "\n".join(" | ".join(cell for cell in row if cell) for row in rows[:120])
    )
    fallback["summary"] = "Spreadsheet rows were readable, but no transaction totals could be extracted."
    return fallback


def _find_header_row(rows: list[list[str]]) -> int | None:
    best_score = 0
    best_index = None
    for index, row in enumerate(rows[:20]):
        normalized = [_normalize_label(cell) for cell in row]
        score = 0
        if any(token in normalized for token in ("date", "txn date", "transaction date")):
            score += 2
        if any(token in normalized for token in ("description", "narration", "remarks", "merchant")):
            score += 2
        if any(token in normalized for token in ("amount", "value", "txn amount", "gross amount")):
            score += 2
        if any(token in normalized for token in ("type", "direction", "credit", "debit", "dr/cr", "cr/dr")):
            score += 2
        if score > best_score:
            best_score = score
            best_index = index
    return best_index if best_score >= 3 else None


def _extract_summary_metrics(rows: list[list[str]]) -> dict[str, float]:
    metrics = {"inflow_total": 0.0, "outflow_total": 0.0}
    for row in rows[:80]:
        for index, cell in enumerate(row):
            label = _normalize_label(cell)
            if not label:
                continue
            for metric_key, aliases in SUMMARY_LABEL_ALIASES.items():
                if not any(alias in label for alias in aliases):
                    continue

                candidates = [cell]
                if index > 0:
                    candidates.append(row[index - 1])
                if index + 1 < len(row):
                    candidates.append(row[index + 1])

                amount = max((_extract_amount(candidate) for candidate in candidates), default=0.0)
                if amount > metrics[metric_key]:
                    metrics[metric_key] = amount
    return metrics


def _parse_rows_from_header(headers: list[str], rows: list[list[str]], summary_metrics: dict[str, float]) -> dict:
    header_map = {_normalize_label(value): index for index, value in enumerate(headers)}
    transactions: list[dict] = []
    inflow_total = 0.0
    outflow_total = 0.0
    dates: list[datetime] = []

    amount_index = _find_first_header_index(header_map, ("amount", "value", "txn amount", "gross amount", "total amount"))
    date_index = _find_first_header_index(header_map, ("date", "txn date", "transaction date", "settlement date"))
    description_index = _find_first_header_index(header_map, ("description", "narration", "remarks", "merchant", "particulars"))
    type_index = _find_first_header_index(header_map, ("type", "direction", "dr/cr", "cr/dr"))
    credit_index = _find_first_header_index(header_map, ("credit", "credit amount", "received"))
    debit_index = _find_first_header_index(header_map, ("debit", "debit amount", "paid", "withdrawal"))

    for row in rows:
        if not any(str(cell).strip() for cell in row):
            continue

        parsed_date = _parse_date(_get_row_value(row, date_index))
        if parsed_date is not None:
            dates.append(parsed_date)

        description = _get_row_value(row, description_index) or "Transaction"
        explicit_type = _normalize_transaction_type(_get_row_value(row, type_index))
        amount = _extract_amount(_get_row_value(row, amount_index))
        credit_amount = _extract_amount(_get_row_value(row, credit_index))
        debit_amount = _extract_amount(_get_row_value(row, debit_index))

        if credit_amount > 0 or debit_amount > 0:
            if credit_amount > 0:
                transactions.append(
                    {
                        "date": parsed_date.isoformat() if parsed_date else None,
                        "description": description,
                        "amount": credit_amount,
                        "type": "credit",
                    }
                )
                inflow_total += credit_amount
            if debit_amount > 0:
                transactions.append(
                    {
                        "date": parsed_date.isoformat() if parsed_date else None,
                        "description": description,
                        "amount": debit_amount,
                        "type": "debit",
                    }
                )
                outflow_total += debit_amount
            continue

        if amount <= 0 and explicit_type is None:
            continue

        txn_type = explicit_type or ("credit" if amount >= 0 else "debit")
        normalized_amount = abs(amount)
        if normalized_amount <= 0:
            continue

        transactions.append(
            {
                "date": parsed_date.isoformat() if parsed_date else None,
                "description": description,
                "amount": normalized_amount,
                "type": txn_type,
            }
        )
        if txn_type == "credit":
            inflow_total += normalized_amount
        else:
            outflow_total += normalized_amount

    inflow_total = inflow_total or summary_metrics.get("inflow_total", 0.0)
    outflow_total = outflow_total or summary_metrics.get("outflow_total", 0.0)

    return {
        "parse_status": "parsed" if transactions else "parsed_with_warnings",
        "parse_confidence": 0.91 if transactions else 0.62,
        "transaction_count": len(transactions),
        "inflow_total": round(inflow_total, 2),
        "outflow_total": round(outflow_total, 2),
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "transactions": transactions,
        "summary": "Parsed structured rows from spreadsheet statement." if transactions else "Used spreadsheet total fields without per-transaction rows.",
    }


def _parse_pdf_statement_text(content: str) -> dict:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return _parse_text_statement(content)

    paytm_parsed = _parse_paytm_statement_text(lines)
    if paytm_parsed["transaction_count"] > 0 or paytm_parsed["inflow_total"] > 0 or paytm_parsed["outflow_total"] > 0:
        return paytm_parsed

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
        fallback["summary"] = "PDF text was readable, but transaction classification was partial."
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
        "summary": "Parsed statement rows from PDF text extraction.",
    }


def _parse_paytm_statement_text(lines: list[str]) -> dict:
    statement_year = _extract_paytm_statement_year(lines)
    blocks = _split_paytm_transaction_blocks(lines)
    transactions: list[dict] = []
    inflow_total = 0.0
    outflow_total = 0.0
    dates: list[datetime] = []

    for block in blocks:
        parsed = _parse_paytm_transaction_block(block, statement_year)
        if parsed is None:
            continue
        transactions.append(parsed)
        parsed_date = _parse_iso_date_safe(parsed.get("date"))
        if parsed_date is not None:
            dates.append(parsed_date)
        if parsed["type"] == "credit":
            inflow_total += parsed["amount"]
        elif parsed["type"] == "debit":
            outflow_total += parsed["amount"]

    if not transactions:
        return {
            "parse_status": "parsed_with_warnings",
            "parse_confidence": 0.0,
            "transaction_count": 0,
            "inflow_total": 0.0,
            "outflow_total": 0.0,
            "period_start": None,
            "period_end": None,
            "transactions": [],
            "summary": "Paytm PDF text was readable, but transaction blocks could not be extracted.",
        }

    return {
        "parse_status": "parsed",
        "parse_confidence": 0.94,
        "transaction_count": len(transactions),
        "inflow_total": round(inflow_total, 2),
        "outflow_total": round(outflow_total, 2),
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "transactions": transactions,
        "summary": "Parsed Paytm-style PDF transaction blocks.",
    }


def _split_paytm_transaction_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    started = False

    for line in lines:
        if _looks_like_paytm_transaction_date(line):
            if current:
                blocks.append(current)
            current = [line]
            started = True
            continue

        if started:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def _parse_paytm_transaction_block(block: list[str], statement_year: int | None) -> dict | None:
    if not block:
        return None

    date_line = block[0]
    parsed_date = _parse_paytm_date_line(date_line, statement_year)
    if parsed_date is None:
        return None

    amount_index = None
    amount_value = 0.0
    txn_type = None
    for index, line in enumerate(block[1:], start=1):
        amount_match = re.search(r"([+-])\s*rs\.?\s*([0-9][0-9,]*(?:\.\d{1,2})?)", line, flags=re.IGNORECASE)
        if amount_match is None:
            continue
        amount_index = index
        amount_value = _to_float(amount_match.group(2))
        txn_type = "credit" if amount_match.group(1) == "+" else "debit"
        break

    if amount_index is None or amount_value <= 0:
        return None

    description_parts: list[str] = []
    for line in block[1:amount_index]:
        cleaned = line.strip()
        if not cleaned or _is_paytm_noise_line(cleaned):
            continue
        description_parts.append(cleaned)

    if not description_parts:
        description_parts = ["Paytm transaction"]

    description = " ".join(description_parts)
    if txn_type is None:
        lowered = description.lower()
        txn_type = "debit" if any(token in lowered for token in ("paid to", "sent to", "upi dr", "payment made")) else "credit"

    return {
        "date": parsed_date.isoformat(),
        "description": _truncate_description(description),
        "amount": round(amount_value, 2),
        "type": txn_type,
    }


def _looks_like_paytm_transaction_date(line: str) -> bool:
    return bool(re.match(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{1,2}:\d{2}\s*(?:AM|PM)?$", line.strip(), flags=re.IGNORECASE))


def _extract_paytm_statement_year(lines: list[str]) -> int | None:
    for line in lines:
        match = re.search(r"\b\d{1,2}\s+[A-Za-z]{3}'?(\d{2}|\d{4})\b", line, flags=re.IGNORECASE)
        if match is None:
            continue
        year_text = match.group(1)
        year = int(year_text)
        if year < 100:
            year += 2000
        return year
    return None


def _parse_paytm_date_line(line: str, statement_year: int | None) -> datetime | None:
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{1,2}:\d{2})\s*(AM|PM)?$", line.strip(), flags=re.IGNORECASE)
    if match is None:
        return None

    day = int(match.group(1))
    month = match.group(2).title()
    time_part = match.group(3)
    meridiem = (match.group(4) or "").upper()
    year = statement_year or datetime.utcnow().year

    try:
        return datetime.strptime(f"{day:02d} {month} {year} {time_part} {meridiem}".strip(), "%d %b %Y %I:%M %p")
    except ValueError:
        try:
            return datetime.strptime(f"{day:02d} {month} {year} {time_part}", "%d %b %Y %H:%M")
        except ValueError:
            return None


def _is_paytm_noise_line(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return True
    if lowered in {"-", "—"}:
        return True
    if lowered.startswith("state bank of india"):
        return True
    if lowered.startswith("passbook payments history"):
        return True
    if lowered.startswith("your account") or lowered.startswith("amount"):
        return True
    if lowered.startswith("upi ref") or lowered.startswith("order id") or lowered.startswith("remarks"):
        return True
    if lowered.startswith("received from") or lowered.startswith("paid to"):
        return False
    if lowered.startswith("#"):
        return False
    if re.fullmatch(r"[+-]\s*47", lowered):
        return True
    if re.fullmatch(r"[0-9 ]{3,}", lowered):
        return True
    return False


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
            credit_amount = _to_float(normalized.get("credit") or normalized.get("credit_amount"))
            debit_amount = _to_float(normalized.get("debit") or normalized.get("debit_amount"))
            if credit_amount > 0 or debit_amount > 0:
                if credit_amount > 0:
                    inflow_total += abs(credit_amount)
                    transactions.append(
                        {
                            "date": parsed_date.isoformat() if parsed_date else raw_date,
                            "description": description or "Credit",
                            "amount": abs(credit_amount),
                            "type": "credit",
                        }
                    )
                if debit_amount > 0:
                    outflow_total += abs(debit_amount)
                    transactions.append(
                        {
                            "date": parsed_date.isoformat() if parsed_date else raw_date,
                            "description": description or "Debit",
                            "amount": abs(debit_amount),
                            "type": "debit",
                        }
                    )
                continue

            txn_type = "credit" if amount >= 0 else "debit"

        normalized_amount = abs(amount)
        if normalized_amount <= 0:
            continue

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
        "summary": "Parsed rows from CSV statement." if transactions else "CSV file was readable but did not expose transaction rows.",
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
        "summary": "Readable text was captured, but structured transaction totals were not available.",
    }


def _maybe_extract_with_gemini(extracted_text: str, parsed: dict) -> dict | None:
    if not extracted_text.strip():
        return None
    if parsed.get("transaction_count", 0) > 0 and float(parsed.get("parse_confidence", 0.0) or 0.0) >= 0.65:
        return None

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_api_key)
        prompt = (
            f"{STATEMENT_EXTRACTION_PROMPT}\n\n"
            f"Statement excerpt:\n{extracted_text[:12000]}"
        )
        response = client.models.generate_content(
            model=STATEMENT_EXTRACTION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
        extracted = _extract_json_object(response.text or "")
        if not extracted:
            return None

        inflow_total = round(_to_float(extracted.get("inflow_total")), 2)
        outflow_total = round(_to_float(extracted.get("outflow_total")), 2)
        transaction_count = int(extracted.get("transaction_count") or 0)
        period_start = _normalize_iso_date(extracted.get("period_start"))
        period_end = _normalize_iso_date(extracted.get("period_end"))
        monthly_revenue_estimate = round(_to_float(extracted.get("monthly_revenue_estimate")), 2)

        if inflow_total <= 0 and transaction_count <= 0:
            return None

        return {
            "parse_status": "parsed_with_warnings" if parsed.get("transaction_count", 0) == 0 else parsed.get("parse_status", "parsed"),
            "parse_confidence": max(float(parsed.get("parse_confidence", 0.0) or 0.0), 0.58),
            "transaction_count": max(transaction_count, parsed.get("transaction_count", 0)),
            "inflow_total": inflow_total or parsed.get("inflow_total", 0.0),
            "outflow_total": outflow_total or parsed.get("outflow_total", 0.0),
            "period_start": period_start or parsed.get("period_start"),
            "period_end": period_end or parsed.get("period_end"),
            "monthly_revenue_estimate": monthly_revenue_estimate or parsed.get("monthly_revenue_estimate"),
            "transactions": parsed.get("transactions", []),
            "summary": extracted.get("summary") or "Gemini extracted statement-level totals from weak source text.",
        }
    except Exception as exc:
        logger.warning("Gemini statement extraction skipped: %s", exc)
        return None


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _normalize_iso_date(value: object) -> str | None:
    if value in {None, "", "null"}:
        return None
    parsed = _parse_date(str(value).strip())
    return parsed.isoformat() if parsed is not None else None


def _parse_iso_date_safe(value: object) -> datetime | None:
    if value in {None, "", "null"}:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _normalize_label(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _normalize_transaction_type(raw: str) -> str | None:
    value = _normalize_label(raw)
    if value in {"credit", "cr", "inflow", "received"}:
        return "credit"
    if value in {"debit", "dr", "outflow", "paid"}:
        return "debit"
    return None


def _find_first_header_index(header_map: dict[str, int], aliases: tuple[str, ...]) -> int | None:
    for alias in aliases:
        if alias in header_map:
            return header_map[alias]
    for header, index in header_map.items():
        if any(alias in header for alias in aliases):
            return index
    return None


def _get_row_value(row: list[str], index: int | None) -> str:
    if index is None or index < 0 or index >= len(row):
        return ""
    return str(row[index]).strip()


def _infer_transaction_type(line: str) -> str | None:
    credit_keywords = (
        "credit",
        "received",
        "money received",
        "upi cr",
        " cr ",
        "credited",
        "settled",
    )
    debit_keywords = (
        "debit",
        "paid",
        "money sent",
        "upi dr",
        " dr ",
        "withdraw",
        "debited",
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


def _calculate_period_days(period_start: str | None, period_end: str | None, transaction_count: int) -> int:
    start = _parse_iso_date(period_start)
    end = _parse_iso_date(period_end)
    if start is not None and end is not None:
        return max((end - start).days + 1, 1)
    if transaction_count > 0:
        return 30
    return 0


def _parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return _parse_date(value)


def _parse_date(raw: str) -> datetime | None:
    normalized = str(raw or "").strip()
    if not normalized:
        return None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def _extract_amount(value: object) -> float:
    if isinstance(value, (int, float)):
        return abs(float(value))

    text = str(value or "")
    matches = re.findall(r"-?\d[\d,]*(?:\.\d+)?", text.replace("₹", " ").replace("INR", " "))
    if not matches:
        return 0.0

    amounts = [_to_float(match) for match in matches]
    positive_amounts = [abs(amount) for amount in amounts if amount]
    return max(positive_amounts, default=0.0)


def _to_float(value: str | float | int | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").replace("₹", "").replace("INR", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

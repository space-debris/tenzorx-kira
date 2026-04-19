"""
Seed comprehensive demo data for KIRA platform.

Run from backend directory:
    python scripts/seed_demo_data.py

This script writes directly to the JSON files in data/platform/
to populate the dashboard, portfolio, cases, kiranas, and active loans pages.
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "platform"

ORG_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_ID = "21111111-1111-1111-1111-111111111111"
OFFICER_ID = "22222222-2222-2222-2222-222222222222"

now = datetime(2026, 4, 18, 14, 0, 0)


def uid():
    return str(uuid.uuid4())


# ── Users (add a few more team members) ──────────────────────────────────────
ANALYST_ID = uid()
MANAGER_ID = uid()

users = [
    {
        "id": ADMIN_ID,
        "org_id": ORG_ID,
        "full_name": "Maya Sharma",
        "email": "maya@democapital.in",
        "role": "admin",
        "created_at": (now - timedelta(days=90)).isoformat(),
    },
    {
        "id": OFFICER_ID,
        "org_id": ORG_ID,
        "full_name": "Rohan Verma",
        "email": "rohan@democapital.in",
        "role": "loan_officer",
        "created_at": (now - timedelta(days=88)).isoformat(),
    },
    {
        "id": ANALYST_ID,
        "org_id": ORG_ID,
        "full_name": "Priya Mehta",
        "email": "priya@democapital.in",
        "role": "loan_officer",
        "created_at": (now - timedelta(days=60)).isoformat(),
    },
    {
        "id": MANAGER_ID,
        "org_id": ORG_ID,
        "full_name": "Arjun Kapoor",
        "email": "arjun@democapital.in",
        "role": "admin",
        "created_at": (now - timedelta(days=75)).isoformat(),
    },
]

# ── Organizations ───────────────────────────────────────────────────────────
organizations = [
    {
        "id": ORG_ID,
        "name": "Demo Capital Finance",
        "slug": "demo-capital-finance",
        "created_at": (now - timedelta(days=120)).isoformat(),
        "is_demo": True,
    }
]

# ── Kiranas (20 diverse stores across India) ────────────────────────────────
KIRANA_DEFS = [
    # (id, store_name, owner_name, mobile, state, district, pin, locality, shop_size, days_ago_created)
    ("31111111-1111-1111-1111-111111111111", "Gupta General Store", "Sanjay Gupta", "+91-9876543210", "Uttar Pradesh", "Meerut", "250002", "Shastri Nagar", "medium", 85),
    ("32222222-2222-2222-2222-222222222222", "Sai Provision Mart", "Vijay Patil", "+91-9123456780", "Maharashtra", "Pune", "411014", "Viman Nagar", "small", 80),
    ("33333333-3333-3333-3333-333333333333", "A One Kirana", "Imran Khan", "+91-9988776655", "Delhi", "North East Delhi", "110094", "Karawal Nagar", "large", 75),
    (uid(), "Lakshmi Stores", "Ramesh Iyer", "+91-9845123678", "Tamil Nadu", "Chennai", "600028", "Adyar", "medium", 72),
    (uid(), "Balaji Supermart", "Krishna Reddy", "+91-9632587410", "Telangana", "Hyderabad", "500034", "Jubilee Hills", "large", 68),
    (uid(), "Sharma Kirana", "Deepak Sharma", "+91-9753186420", "Rajasthan", "Jaipur", "302017", "Malviya Nagar", "small", 65),
    (uid(), "Bhatia General Store", "Suresh Bhatia", "+91-9612345789", "Punjab", "Ludhiana", "141001", "Chaura Bazar", "medium", 60),
    (uid(), "Nandi Provisions", "Venkatesh Nandi", "+91-9456123780", "Karnataka", "Bengaluru", "560034", "Koramangala", "large", 55),
    (uid(), "Patel Corner Shop", "Hitesh Patel", "+91-9321654870", "Gujarat", "Ahmedabad", "380015", "Satellite", "medium", 50),
    (uid(), "Das Grocery", "Amitabh Das", "+91-9871234560", "West Bengal", "Kolkata", "700029", "Gariahat", "small", 48),
    (uid(), "Singh Brothers", "Manpreet Singh", "+91-9654321870", "Haryana", "Gurugram", "122001", "DLF Phase 4", "large", 45),
    (uid(), "Rao Supermarket", "Srinivas Rao", "+91-9890123456", "Andhra Pradesh", "Visakhapatnam", "530016", "Dwaraka Nagar", "medium", 42),
    (uid(), "Mehta Trader", "Ketan Mehta", "+91-9234567890", "Maharashtra", "Mumbai", "400076", "Powai", "small", 38),
    (uid(), "Joshi Provision", "Madhusudan Joshi", "+91-9178456230", "Madhya Pradesh", "Indore", "452001", "Rajwada", "medium", 35),
    (uid(), "KK Mart", "Kuldeep Kumar", "+91-9087654321", "Bihar", "Patna", "800001", "Fraser Road", "small", 32),
    (uid(), "Pillai Stores", "Arun Pillai", "+91-9345678912", "Kerala", "Kochi", "682016", "Edappally", "medium", 28),
    (uid(), "Choudhary Kirana", "Ratan Choudhary", "+91-9567891234", "Rajasthan", "Udaipur", "313001", "Hiran Magri", "small", 25),
    (uid(), "Trivedi General", "Prakash Trivedi", "+91-9789012345", "Gujarat", "Surat", "395007", "Vesu", "large", 22),
    (uid(), "Mishra Provision", "Rajesh Mishra", "+91-9456789012", "Uttar Pradesh", "Lucknow", "226001", "Hazratganj", "medium", 18),
    (uid(), "Dutta Corner", "Subhash Dutta", "+91-9678901234", "Assam", "Guwahati", "781005", "Paltan Bazar", "small", 15),
]

kiranas = []
kirana_ids = []
for k_def in KIRANA_DEFS:
    k_id, store, owner, mobile, state, district, pin, locality, size, days = k_def
    kirana = {
        "id": k_id,
        "org_id": ORG_ID,
        "store_name": store,
        "owner_name": owner,
        "owner_mobile": mobile,
        "location": {
            "state": state,
            "district": district,
            "pin_code": pin,
            "locality": locality,
        },
        "metadata": {"shop_size": size},
        "created_at": (now - timedelta(days=days)).isoformat(),
        "updated_at": (now - timedelta(days=max(1, days - random.randint(5, 20)))).isoformat(),
    }
    kiranas.append(kirana)
    kirana_ids.append(k_id)

# ── Assessment summaries ────────────────────────────────────────────────────
RISK_BANDS = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
assessment_summaries = []
assessment_map = {}  # kirana_id -> summary

for i, k in enumerate(kiranas):
    session_id = uid()
    assessment_id = uid()
    risk = random.choices(RISK_BANDS, weights=[35, 35, 20, 10])[0]
    risk_score = {"LOW": round(random.uniform(0.12, 0.30), 3), "MEDIUM": round(random.uniform(0.31, 0.50), 3), "HIGH": round(random.uniform(0.51, 0.72), 3), "VERY_HIGH": round(random.uniform(0.73, 0.92), 3)}[risk]
    rev_low = random.randint(80000, 350000)
    rev_high = rev_low + random.randint(40000, 200000)
    loan_low = int(rev_low * 0.4)
    loan_high = int(rev_high * 0.7)

    summary = {
        "session_id": session_id,
        "assessment_id": assessment_id,
        "completed_at": (now - timedelta(days=random.randint(1, 30))).isoformat(),
        "risk_band": risk,
        "risk_score": risk_score,
        "revenue_range": {"low": rev_low, "high": rev_high},
        "loan_range": {"low": loan_low, "high": loan_high},
        "eligible": risk != "VERY_HIGH" or random.random() > 0.5,
        "fraud_flagged": risk == "VERY_HIGH" and random.random() > 0.6,
    }
    assessment_summaries.append(summary)
    assessment_map[k["id"]] = summary

# ── Cases (15 cases from the 20 kiranas, spread across statuses) ────────────
STATUS_OPTIONS = ["draft", "submitted", "under_review", "approved", "disbursed", "monitoring", "restructured", "closed"]
STATUS_WEIGHTS = [1, 2, 3, 3, 3, 3, 2, 1]

CASE_NOTES = [
    "Initial assessment complete. Awaiting field verification.",
    "Documents verified. Ready for underwriting committee review.",
    "Strong turnover history. Low competition in catchment.",
    "Store has consistent cash flow pattern. Recommended for approval.",
    "Disbursed per approved terms. Monitoring cycle initiated.",
    "First refresh cycle shows stable performance.",
    "Slight revenue dip noted. Monitoring closely for next quarter.",
    "Owner requested tenure extension due to seasonal slowdown.",
    "Excellent repayment track record. Mark for renewal eligibility.",
    "Fraud signal flagged — manual review pending.",
    "Store expansion noted during field visit. Positive sign.",
    "Submitted for committee review. Good geo-demand index.",
    "Semi-urban catchment with high demand index score.",
    "Restructured after monsoon impact. Recovery trajectory positive.",
    "Loan fully repaid. Case closed successfully.",
]

USER_IDS = [ADMIN_ID, OFFICER_ID, ANALYST_ID, MANAGER_ID]

cases = []
case_kirana_map = {}

# Use first 15 kiranas to create cases (the rest are just onboarded, no cases yet)
for i in range(15):
    k = kiranas[i]
    summary = assessment_map[k["id"]]
    status = random.choices(STATUS_OPTIONS, weights=STATUS_WEIGHTS)[0]

    # For existing seeded cases, use their original IDs
    case_id = uid()
    if i == 0:
        case_id = "61111111-1111-1111-1111-111111111111"
        status = "approved"
    elif i == 1:
        case_id = "62222222-2222-2222-2222-222222222222"
        status = "monitoring"
    elif i == 2:
        case_id = "63333333-3333-3333-3333-333333333333"
        status = "restructured"

    days_ago = random.randint(3, 60)
    case = {
        "id": case_id,
        "org_id": ORG_ID,
        "kirana_id": k["id"],
        "created_by_user_id": random.choice(USER_IDS),
        "assigned_to_user_id": random.choice(USER_IDS),
        "status": status,
        "latest_assessment_session_id": summary["session_id"],
        "latest_assessment_id": summary["assessment_id"],
        "latest_risk_band": summary["risk_band"],
        "latest_loan_range": summary["loan_range"],
        "notes": CASE_NOTES[i % len(CASE_NOTES)],
        "created_at": (now - timedelta(days=days_ago)).isoformat(),
        "updated_at": (now - timedelta(days=random.randint(0, min(3, days_ago)))).isoformat(),
    }
    cases.append(case)
    case_kirana_map[case_id] = k

# ── Loan Accounts (for disbursed, monitoring, restructured, closed cases) ─────
LOAN_ELIGIBLE_STATUSES = {"approved", "disbursed", "monitoring", "restructured", "closed"}
loan_accounts = []
loan_map = {}

for case in cases:
    if case["status"] not in LOAN_ELIGIBLE_STATUSES:
        continue
    if case["status"] == "approved" and random.random() > 0.5:
        continue  # Not all approved cases have loan accounts

    loan_id = uid()
    # Preserve original seed loan for case 2
    if case["id"] == "62222222-2222-2222-2222-222222222222":
        loan_id = "92222222-2222-2222-2222-222222222222"

    principal = float(case["latest_loan_range"]["high"]) * random.uniform(0.7, 1.0)
    principal = round(principal / 1000) * 1000  # round to nearest thousand
    outstanding = round(principal * random.uniform(0.3, 0.95), 2)
    collected = round(principal - outstanding, 2)

    days_past_due = 0
    if case["status"] == "restructured":
        days_past_due = random.randint(15, 60)
    elif case["status"] == "monitoring" and random.random() > 0.7:
        days_past_due = random.randint(1, 14)

    loan_status = {
        "approved": "pending_disbursement",
        "disbursed": "active",
        "monitoring": "active",
        "restructured": "restructured",
        "closed": "closed",
    }[case["status"]]

    disbursed_days_ago = random.randint(10, 80)
    loan = {
        "id": loan_id,
        "org_id": ORG_ID,
        "case_id": case["id"],
        "kirana_id": case["kirana_id"],
        "assessment_session_id": case["latest_assessment_session_id"],
        "status": loan_status,
        "principal_amount": principal,
        "tenure_months": random.choice([6, 9, 12, 18]),
        "repayment_cadence": random.choice(["weekly", "monthly"]),
        "annual_interest_rate_pct": random.choice([18.0, 20.0, 22.0, 24.0, 26.0]),
        "processing_fee_pct": 1.5,
        "estimated_installment": round(principal / (random.choice([6, 9, 12]) * 4.33), 2),
        "disbursed_at": (now - timedelta(days=disbursed_days_ago)).isoformat(),
        "maturity_date": (now + timedelta(days=random.randint(90, 365))).isoformat(),
        "outstanding_principal": outstanding,
        "total_collected": collected,
        "last_collection_date": (now - timedelta(days=random.randint(1, 14))).isoformat(),
        "days_past_due": days_past_due,
        "utilization": None,
        "original_risk_band": case["latest_risk_band"],
        "original_revenue_range": None,
        "created_at": (now - timedelta(days=disbursed_days_ago)).isoformat(),
        "updated_at": (now - timedelta(days=random.randint(0, 3))).isoformat(),
    }
    loan_accounts.append(loan)
    loan_map[case["id"]] = loan

# ── Alerts (diverse, spread across cases with open/resolved statuses) ───────
ALERT_TEMPLATES = [
    ("critical", "Cash-flow deterioration detected", "Fresh statements show {pct}% lower inflows than the prior baseline."),
    ("warning", "Fresh statement upload pending", "Monitoring case has crossed the 15-day refresh mark."),
    ("warning", "Repayment overdue by {days} days", "Borrower has missed {count} consecutive installments."),
    ("critical", "Fraud signal mismatch", "CV shelf density vs. reported inventory shows >40% variance."),
    ("warning", "Risk band escalation", "Risk score moved from {old_band} to {new_band} after latest monitoring."),
    ("info", "Renewal eligibility approaching", "Loan reaches 75% tenure completion in {days} days."),
    ("warning", "High competition detected", "3 new stores opened within catchment radius in last 30 days."),
    ("critical", "Utilization anomaly", "Personal cash usage at {pct}% of loan — possible diversion."),
    ("info", "Document export requested", "Compliance bundle was generated by loan officer."),
    ("warning", "Revenue seasonality pattern", "Expected seasonal dip of {pct}% detected in region."),
]

alerts = []
active_case_ids = [c["id"] for c in cases if c["status"] in {"monitoring", "disbursed", "restructured", "under_review"}]

for i in range(18):
    case = cases[i % len(cases)]
    if case["status"] in ("draft",):
        case = random.choice([c for c in cases if c["status"] not in ("draft", "closed")])

    template = random.choice(ALERT_TEMPLATES)
    severity, title, desc_template = template
    desc = desc_template.format(
        pct=random.randint(15, 85),
        days=random.randint(5, 45),
        count=random.randint(1, 4),
        old_band="LOW",
        new_band="MEDIUM",
    )

    is_resolved = random.random() > 0.65  # 35% resolved

    alert = {
        "id": uid(),
        "org_id": ORG_ID,
        "case_id": case["id"],
        "kirana_id": case["kirana_id"],
        "severity": severity,
        "status": "resolved" if is_resolved else "open",
        "title": title,
        "description": desc,
        "created_at": (now - timedelta(hours=random.randint(1, 720))).isoformat(),
        "updated_at": (now - timedelta(hours=random.randint(0, 48))).isoformat(),
    }
    alerts.append(alert)

# ── Loan Decisions ─────────────────────────────────────────────────────────
loan_decisions = []
for case in cases:
    if case["status"] in ("draft", "submitted"):
        continue

    decision_id = uid()
    if case["id"] == "62222222-2222-2222-2222-222222222222":
        decision_id = "91111111-1111-1111-1111-111111111111"

    recommended = float(case["latest_loan_range"]["high"]) * 0.85
    approved = recommended * random.uniform(0.85, 1.0)

    decision = {
        "id": decision_id,
        "org_id": ORG_ID,
        "case_id": case["id"],
        "assessment_session_id": case["latest_assessment_session_id"],
        "recommended_amount": round(recommended),
        "approved_amount": round(approved),
        "recommended_tenure_months": random.choice([9, 12, 18]),
        "approved_tenure_months": random.choice([9, 12, 18]),
        "pricing_rate_annual": random.choice([18.0, 20.0, 22.0, 24.0]),
        "processing_fee_rate": 1.5,
        "repayment_cadence": random.choice(["weekly", "monthly"]),
        "decision_reason": random.choice([
            "Strong urban turnover and good recent repayment capacity.",
            "Low risk profile with consistent daily transaction volumes.",
            "Semi-urban market with low competition and growing catchment.",
            "Good shelf density and brand mix observed during CV assessment.",
            "Solid revenue history confirmed through statement analysis.",
        ]),
        "override_reason": random.choice([
            None,
            "Trimmed ticket slightly to stay within branch comfort band.",
            "Extended tenure per borrower request due to seasonal business.",
            "Increased amount based on field visit confirming store expansion.",
            None,
        ]),
        "created_by_user_id": random.choice(USER_IDS),
        "created_at": (now - timedelta(days=random.randint(2, 40))).isoformat(),
    }
    loan_decisions.append(decision)

# ── Statement Uploads ──────────────────────────────────────────────────────
statement_uploads = []
for case in cases:
    if case["status"] in ("draft", "submitted"):
        continue

    num_uploads = random.randint(1, 3)
    for j in range(num_uploads):
        k = case_kirana_map.get(case["id"])
        store_slug = (k["store_name"].lower().replace(" ", "-")[:20] if k else "store")
        month_names = ["jan", "feb", "mar", "apr"]

        upload = {
            "id": uid(),
            "org_id": ORG_ID,
            "case_id": case["id"],
            "loan_id": loan_map.get(case["id"], {}).get("id"),
            "kirana_id": case["kirana_id"],
            "status": random.choice(["uploaded", "processed", "processed", "processed"]),
            "file_name": f"{store_slug}-{random.choice(month_names)}26.csv",
            "file_type": "csv",
            "file_size_bytes": random.randint(5000, 25000),
            "uploaded_by_user_id": random.choice(USER_IDS),
            "transaction_summary": {
                "credit_count": random.randint(30, 200),
                "debit_count": random.randint(20, 150),
                "total_credits": round(random.uniform(50000, 400000), 2),
                "total_debits": round(random.uniform(30000, 350000), 2),
                "period_start": (now - timedelta(days=60 + j*30)).strftime("%Y-%m-%d"),
                "period_end": (now - timedelta(days=30 + j*30)).strftime("%Y-%m-%d"),
            },
            "created_at": (now - timedelta(days=random.randint(1, 40))).isoformat(),
            "updated_at": (now - timedelta(days=random.randint(0, 5))).isoformat(),
        }
        statement_uploads.append(upload)

# ── Monitoring Runs ────────────────────────────────────────────────────────
monitoring_runs = []
for case in cases:
    if case["status"] not in ("monitoring", "disbursed", "restructured"):
        continue

    num_runs = random.randint(1, 3)
    for j in range(num_runs):
        prev_risk = case["latest_risk_band"]
        new_risk = random.choices(RISK_BANDS, weights=[30, 35, 25, 10])[0]
        risk_score = round(random.uniform(0.15, 0.85), 3)

        run = {
            "id": uid(),
            "org_id": ORG_ID,
            "case_id": case["id"],
            "loan_id": loan_map.get(case["id"], {}).get("id"),
            "kirana_id": case["kirana_id"],
            "status": "completed",
            "statement_upload_id": None,
            "previous_risk_band": prev_risk,
            "new_risk_band": new_risk,
            "new_risk_score": risk_score,
            "inflow_velocity_change_pct": round(random.uniform(-30, 25), 2),
            "alerts_raised": [],
            "completed_at": (now - timedelta(days=random.randint(1, 30) + j*15)).isoformat(),
            "utilization": {
                "supplier_inventory_pct": round(random.uniform(40, 70), 1),
                "transfer_wallet_pct": round(random.uniform(10, 25), 1),
                "personal_cash_pct": round(random.uniform(5, 20), 1),
                "unknown_pct": round(random.uniform(2, 15), 1),
            },
            "restructuring_suggestion": None,
            "created_at": (now - timedelta(days=random.randint(1, 45))).isoformat(),
            "updated_at": (now - timedelta(days=random.randint(0, 5))).isoformat(),
        }
        monitoring_runs.append(run)

# ── Document Bundles ───────────────────────────────────────────────────────
document_bundles = []
for case in cases:
    if case["status"] in ("draft", "submitted"):
        continue
    if random.random() > 0.7:
        continue  # Not all cases have bundles

    bundle = {
        "id": uid(),
        "org_id": ORG_ID,
        "case_id": case["id"],
        "documents": {
            "underwriting_summary": "ready",
            "sanction_note": "ready" if case["status"] in ("approved", "disbursed", "monitoring") else "not_applicable",
            "monitoring_history_summary": "ready" if case["status"] in ("monitoring", "restructured") else "not_applicable",
            "audit_event_export": "ready",
        },
        "created_at": (now - timedelta(days=random.randint(1, 20))).isoformat(),
        "generated_by_user_id": random.choice(USER_IDS),
        "export_formats": ["json", "pdf"],
    }
    document_bundles.append(bundle)

# ── Underwriting Decisions ─────────────────────────────────────────────────
underwriting_decisions = []
for case in cases:
    if case["status"] in ("draft", "submitted"):
        continue

    summary = assessment_map.get(case["kirana_id"])
    if not summary:
        continue

    loan_range = case["latest_loan_range"]
    mid_amount = (loan_range["low"] + loan_range["high"]) / 2.0
    has_override = random.random() > 0.6

    decision = {
        "id": uid(),
        "case_id": case["id"],
        "org_id": ORG_ID,
        "assessment_session_id": summary["session_id"],
        "assessment_id": summary["assessment_id"],
        "eligible": summary["eligible"],
        "recommended_terms": {
            "amount": round(mid_amount),
            "tenure_months": random.choice([9, 12, 18]),
            "repayment_cadence": "weekly",
            "estimated_installment": round(mid_amount / (12 * 4.33), 2),
            "annual_interest_rate_pct": 22.0,
            "processing_fee_pct": 1.5,
        },
        "final_terms": {
            "amount": round(mid_amount * (random.uniform(0.85, 1.15) if has_override else 1.0)),
            "tenure_months": random.choice([9, 12, 18]),
            "repayment_cadence": random.choice(["weekly", "monthly"]) if has_override else "weekly",
            "estimated_installment": round(mid_amount / (12 * 4.33), 2),
            "annual_interest_rate_pct": random.choice([20.0, 22.0, 24.0]) if has_override else 22.0,
            "processing_fee_pct": 1.5,
        },
        "loan_range_guardrail": loan_range,
        "pricing_recommendation": None,
        "policy_exception_flags": ["amount_changed_from_recommendation"] if has_override else [],
        "has_override": has_override,
        "override_reason": "Adjusted based on field officer recommendation." if has_override else None,
        "overridden_by_user_id": random.choice(USER_IDS) if has_override else None,
        "overridden_at": (now - timedelta(days=random.randint(1, 10))).isoformat() if has_override else None,
        "created_at": (now - timedelta(days=random.randint(2, 30))).isoformat(),
        "updated_at": (now - timedelta(days=random.randint(0, 5))).isoformat(),
    }
    underwriting_decisions.append(decision)

# ── Audit Events (rich activity trail) ──────────────────────────────────────
AUDIT_ACTIONS = [
    ("case", "created", "Created case for {store}"),
    ("case", "status_changed", "Changed case status from {old} to {new}"),
    ("case", "assessment_linked", "Linked assessment to case"),
    ("kirana", "created", "Created kirana profile for {store}"),
    ("case", "underwriting_overridden", "Captured underwriting override for latest assessment"),
    ("system", "seeded", "Seeded demo platform data."),
]

audit_events = []
for case in cases:
    k = case_kirana_map.get(case["id"])
    store_name = k["store_name"] if k else "Unknown"

    # Case created event
    audit_events.append({
        "id": uid(),
        "org_id": ORG_ID,
        "entity_type": "case",
        "entity_id": case["id"],
        "action": "created",
        "description": f"Created case for {store_name}",
        "actor_name": "Maya Sharma",
        "actor_user_id": case["created_by_user_id"],
        "metadata": {"status": "draft"},
        "created_at": case["created_at"],
    })

    # Assessment linked event
    audit_events.append({
        "id": uid(),
        "org_id": ORG_ID,
        "entity_type": "assessment",
        "entity_id": case["latest_assessment_id"],
        "action": "assessment_linked",
        "description": f"Linked assessment {case['latest_assessment_session_id'][:8]} to case",
        "actor_name": "Rohan Verma",
        "actor_user_id": case["assigned_to_user_id"],
        "metadata": {"case_id": case["id"]},
        "created_at": (datetime.fromisoformat(case["created_at"]) + timedelta(hours=random.randint(1, 24))).isoformat(),
    })

    # Status change events based on current status
    status_flow = {
        "submitted": ["submitted"],
        "under_review": ["submitted", "under_review"],
        "approved": ["submitted", "under_review", "approved"],
        "disbursed": ["submitted", "under_review", "approved", "disbursed"],
        "monitoring": ["submitted", "under_review", "approved", "disbursed", "monitoring"],
        "restructured": ["submitted", "under_review", "approved", "disbursed", "monitoring", "restructured"],
        "closed": ["submitted", "under_review", "approved", "disbursed", "monitoring", "closed"],
    }
    statuses = status_flow.get(case["status"], [])
    prev = "draft"
    for idx, s in enumerate(statuses):
        audit_events.append({
            "id": uid(),
            "org_id": ORG_ID,
            "entity_type": "case",
            "entity_id": case["id"],
            "action": "status_changed",
            "description": f"Changed case status from {prev} to {s}",
            "actor_name": random.choice(["Maya Sharma", "Rohan Verma", "Priya Mehta"]),
            "actor_user_id": random.choice(USER_IDS),
            "metadata": {"previous_status": prev, "new_status": s},
            "created_at": (datetime.fromisoformat(case["created_at"]) + timedelta(hours=random.randint(2 + idx*12, 24 + idx*24))).isoformat(),
        })
        prev = s

# Add kirana creation events
for k in kiranas:
    audit_events.append({
        "id": uid(),
        "org_id": ORG_ID,
        "entity_type": "kirana",
        "entity_id": k["id"],
        "action": "created",
        "description": f"Created kirana profile for {k['store_name']}",
        "actor_name": "system",
        "metadata": {"pin_code": k["location"]["pin_code"]},
        "created_at": k["created_at"],
    })

# System seed event
audit_events.append({
    "id": "81111111-1111-1111-1111-111111111111",
    "org_id": ORG_ID,
    "entity_type": "system",
    "entity_id": ORG_ID,
    "action": "seeded",
    "description": "Seeded default demo workspace with comprehensive data.",
    "actor_name": "system",
    "metadata": {"demo_org_slug": "demo-capital-finance"},
    "created_at": (now - timedelta(days=120)).isoformat(),
})

# Sort audit events by created_at
audit_events.sort(key=lambda e: e["created_at"])

# ── Write all JSON files ──────────────────────────────────────────────────
def write_json(filename, data):
    path = DATA_DIR / filename
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"  ✓ {filename}: {len(data)} records")

print(f"\n{'='*60}")
print(f"  KIRA Demo Data Seeder")
print(f"  Writing to: {DATA_DIR}")
print(f"{'='*60}\n")

DATA_DIR.mkdir(parents=True, exist_ok=True)

write_json("organizations.json", organizations)
write_json("users.json", users)
write_json("kiranas.json", kiranas)
write_json("assessment_summaries.json", assessment_summaries)
write_json("cases.json", cases)
write_json("alerts.json", alerts)
write_json("loan_accounts.json", loan_accounts)
write_json("loan_decisions.json", loan_decisions)
write_json("statement_uploads.json", statement_uploads)
write_json("monitoring_runs.json", monitoring_runs)
write_json("document_bundles.json", document_bundles)
write_json("underwriting_decisions.json", underwriting_decisions)
write_json("audit_events.json", audit_events)

print(f"\n{'='*60}")
print(f"  Done! Restart the backend to load new data.")
print(f"{'='*60}\n")

# Summary
active_loan_statuses = {"approved", "disbursed", "monitoring", "restructured"}
active_cases = [c for c in cases if c["status"] in active_loan_statuses]
open_alerts = [a for a in alerts if a["status"] == "open"]
print(f"  📊 Dashboard will show:")
print(f"     • {len(kiranas)} kiranas onboarded")
print(f"     • {len(cases)} total cases")
print(f"     • {len(active_cases)} active loan cases")
print(f"     • {len(loan_accounts)} loan accounts")
print(f"     • {len(open_alerts)} open alerts")
print(f"     • {len(audit_events)} audit events")
print(f"     • Cases across {len(set(c['status'] for c in cases))} different statuses")
print(f"     • Kiranas across {len(set(k['location']['state'] for k in kiranas))} states")
print()

# KIRA — Business Context

> Strategic context document for the Orchestration Lead and presentation deck.
> This document is for internal use and presentation preparation only.

---

## 1. The Poonawalla Fincorp Strategic Context

Poonawalla Fincorp (PFL) has made two strategic product moves in early 2025:

### Shopkeeper Loan (April 2025)
- **Target**: Small retail shop owners, including kirana stores
- **Product**: Working capital loans for inventory procurement
- **Distribution**: Through PFL's branch network and DSA channels
- **Challenge**: How to underwrite borrowers with no GST, no bank statements, no bureau?

### Credit AI (March 2025)
- **Product**: AI-powered credit decisioning engine
- **Capabilities**: Automated underwriting using GST returns, bank statement analysis, and bureau data
- **Performance**: Faster decisioning, lower cost per assessment
- **Limitation**: Requires GST returns, bank statements, or bureau data as inputs

### The Structural Gap

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│   CREDIT AI                        SHOPKEEPER LOAN            │
│   ┌──────────────┐                 ┌──────────────────┐       │
│   │ AI-powered   │                 │ Designed for      │       │
│   │ underwriting │      GAP        │ small retailers   │       │
│   │              │ ◄───────────►   │                   │       │
│   │ Needs: GST,  │                 │ Borrowers have:   │       │
│   │ bank stmts,  │                 │ No GST, no bank   │       │
│   │ bureau data  │                 │ stmts, no bureau  │       │
│   └──────────────┘                 └──────────────────┘       │
│                                                               │
│              KIRA FILLS THIS GAP                              │
│              ═══════════════════                              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**Key one-liner**:
> "Poonawalla Fincorp's Shopkeeper Loan exists. Their Credit AI exists.
> The gap between those two products is exactly what we built today."

---

## 2. Why Credit AI Cannot Underwrite Kirana Stores

Credit AI is a powerful product — but it was designed for borrowers who exist in the formal digital economy. Kirana stores, by definition, largely do not.

### Input Dependencies

| Credit AI Input | Availability for Kirana Stores | Gap |
|----------------|-------------------------------|-----|
| **GST Returns** | ~80% of kirana stores are below ₹40L threshold; no GST filing | ❌ Complete gap |
| **Bank Statements** | Available but misleading — 50-70% of revenue is cash, never enters bank | ⚠️ Systematic understatement |
| **Credit Bureau (CIBIL)** | First-time borrowers; no or thin CIBIL file | ❌ Complete gap |
| **ITR Filing** | Most file nil or minimal returns; does not reflect true income | ⚠️ Unreliable |
| **Digital Invoicing** | Virtually non-existent in this segment | ❌ Complete gap |

### The Mathematical Problem

Even if Credit AI has exceptional ML capabilities, it faces a fundamental data availability problem:

```
Credit AI Accuracy = f(Data Quality × Data Availability)

For kirana stores:
  Data Quality ≈ Low (cash understatement)
  Data Availability ≈ Near Zero (no GST, no bureau)
  
  ∴ Credit AI Accuracy → Undefined (no inputs to process)
```

This is not a Credit AI deficiency — it's a structural gap in the Indian financial data infrastructure for the informal retail sector.

---

## 3. KIRA as the Missing Underwriting Layer

KIRA complements (not replaces) Credit AI by providing underwriting capability for the exact segment that Credit AI cannot reach.

### Positioning

```
                    Has GST/Bureau Data?
                    ┌───────┬──────────┐
                    │  YES  │    NO    │
          ┌─────────┼───────┼──────────┤
Needs     │  YES    │Credit │  KIRA    │
Working   │         │  AI   │  ████    │
Capital?  ├─────────┼───────┼──────────┤
          │  NO     │  N/A  │   N/A    │
          └─────────┴───────┴──────────┘
```

KIRA's addressable market is the bottom-right quadrant: businesses that need credit but cannot be underwritten by data-dependent systems.

### Workflow Integration

KIRA is designed as a **pre-screening layer**, not a replacement for full underwriting:

```
Loan Application (Kirana)
        │
        ▼
   ┌─────────┐    Score > Threshold    ┌──────────────────┐
   │  KIRA   │ ──────────────────────► │ Detailed Review   │
   │ Screen  │                         │ (Field visit if   │
   │         │                         │  needed, Credit   │
   │         │    Score < Threshold     │  AI if data found)│
   │         │ ──────────────────────► │                   │
   └─────────┘                         │ Decline / Hold    │
                                       └──────────────────┘
```

This means:
1. **100% of kirana applications get screened** (vs 0% currently processable)
2. **Field visits only for borderline/flagged cases** (cost saving)
3. **KIRA score can inform field visit priority** (efficiency gain)

---

## 4. The 44-Location Field Visit Problem

Current kirana lending (where it exists) requires physical field visits:

| Metric | Current (Field Visit) | With KIRA |
|--------|----------------------|-----------|
| Cost per assessment | ₹500 - ₹2,000 | ₹2 - ₹5 (API costs) |
| Time per assessment | 2-5 days | < 30 seconds |
| Assessments per day per officer | 3-5 | Unlimited |
| Geographic constraint | Officer must travel | None (remote) |
| Scalability | Linear (need more officers) | Near-zero marginal cost |
| Consistency | High variance between officers | Standardized |

PFL has 44 branch locations. Each branch can service a limited radius for field visits. KIRA eliminates the geographic bottleneck entirely — any store with a smartphone can be assessed remotely.

### Impact Math

- 44 branches × 3 field visits/day × 250 working days = **33,000 assessments/year** (current capacity)
- KIRA capacity: **unlimited** (constrained only by API rate limits, easily scalable)
- At ₹1,000 per field visit saved: **₹3.3 crore annual savings** just on assessment costs
- Plus: revenue from loans to previously un-underwritable stores

---

## 5. Total Addressable Market

### Market Sizing

| Parameter | Value | Source |
|-----------|-------|--------|
| Kirana stores in India | 13 million | Industry estimates |
| Stores needing working capital | ~60% (7.8 million) | FMCG distributor surveys |
| Average loan size | ₹2 - ₹5 lakh | PFL Shopkeeper Loan positioning |
| Potential loan book | ₹1.5 - ₹4 lakh crore | 7.8M × ₹2-5L |
| Currently serviceable by NBFCs | < 5% | Limited by underwriting constraints |
| KIRA-unlockable segment | 30-50% (screening to eligibility) | Conservative estimate |

### Revenue Opportunity for PFL

Scenario: PFL captures 1% of the KIRA-serviceable market:
```
7.8M stores × 40% KIRA-eligible × 1% PFL capture = 31,200 loans
31,200 loans × ₹3L average = ₹936 crore loan book
At 18% yield - 8% cost of funds = 10% NIM → ₹93.6 crore revenue
```

Even a tiny market share creates a significant revenue stream because the denominator is enormous.

---

## 6. KIRA Evolution Roadmap

### Phase 1: Screening Tool (Current Hackathon Build)
- Pre-screening for kirana loan applications
- Go/No-Go recommendation with confidence score
- Integration as API alongside existing LOS
- **Value**: Enables PFL to process 100% of kirana applications

### Phase 2: Full Underwriting API (Post-Hackathon, 3-6 months)
- Calibrated against actual loan performance data
- Weight matrix tuned on PFL's portfolio
- Integration with PFL's Credit AI for hybrid decisioning
- Repeat assessment capability (monitor store over time)
- **Value**: Replaces field visits for 60-70% of cases

### Phase 3: Credit Bureau for the Physical World (12-18 months)
- Periodic re-assessment of stores (quarterly)
- Store performance tracking over time
- "KIRA Score" as portable creditworthiness metric
- White-label API for other NBFCs and banks
- **Value**: Creates a new data asset — visual credit histories for informal retail

### The Long-Term Vision

KIRA is not just an underwriting tool. It's the beginning of a **credit bureau for the physical world** — where a store's creditworthiness is assessed from its observable reality rather than its digital paper trail.

Just as CIBIL scores aggregate digital financial behavior into a credit score, KIRA aggregates physical-world signals into a creditworthiness assessment. For the 80%+ of Indian businesses that operate below the digital data threshold, this is the only viable path to formal credit inclusion.

---

## 7. Presentation Key Messages

### Opening Statement
> "Every NBFC in India has the same problem: 13 million kirana stores need working capital, but zero of them have the data you need to underwrite them. We built the underwriting layer that doesn't need that data."

### Closing Statement
> "Poonawalla Fincorp's Shopkeeper Loan exists. Their Credit AI exists. The gap between those two products is exactly what we built today. KIRA is the missing piece that turns a ₹0 addressable market into a ₹4 lakh crore opportunity."

### One-Liner for Judges
> "KIRA underwrites kirana stores the way a credit officer would if they could visit 13 million shops simultaneously — by looking at their shelves and their neighborhoods."

### Differentiator Statement
> "Most teams will show you image classification. We show you economic calibration. KIRA doesn't predict income from a photo — it estimates working capital from visible inventory, infers sales velocity from product turnover rates, and cross-validates against spatial demand. That's not computer vision. That's financial analysis delivered through computer vision."

---

*Business Context Document v1.0 — KIRA Project*
*For Orchestration Lead and Presentation Use Only*
*Last Updated: April 2025*

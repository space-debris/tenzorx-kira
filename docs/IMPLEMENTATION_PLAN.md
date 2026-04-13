# KIRA — Implementation Plan

> Phased development roadmap with ownership, sequencing, dependencies, and expansion from a single-assessment underwriting tool into a lender-facing Kirana Lending Intelligence Platform.

---

## Team Ownership

| Role | Person | Core Responsibility |
| --- | --- | --- |
| Orchestration Lead | You | Backend workflow, domain model, APIs, loan lifecycle, audit trail, document generation |
| Analytics Lead | Abhishek | CV and geo signals, underwriting logic, monitoring logic, forecasting, portfolio analytics |
| Frontend Lead | Ayush | Dashboard UX, onboarding flow, case pages, monitoring views, portfolio command center |

---

## Planning Principles

The original KIRA scope was a remote underwriting engine based on images and GPS. The new scope keeps that engine, but expands KIRA into a lender-facing operating system.

Non-negotiable product decisions for the next build:

1. Preserve the current assessment pipeline as the underwriting core. Do not rebuild from scratch.
2. Build lender workflow first: onboarding, underwriting, approval, monitoring, portfolio.
3. For MVP, use manual lender-side statement upload for fresh UPI or bank data.
4. Treat Account Aggregator as a later integration, not a blocker for product progress.
5. Use deterministic templates plus LLM-written narratives for reports. Do not depend on RAG for core compliance documents.
6. Keep embedded value-adds like khata, insurance, and POS out of the MVP.
7. Every lender override must be captured with a reason and stored in the audit trail.

---

## Phase Overview (Original MVP Track)

```
PHASE 0 ──► PHASE 1 (CV) ──────────────────────┐
         ├► PHASE 2 (Geo) ─── parallel to 1 ───┤
         │                                       ▼
         │                               PHASE 3 (Fusion)
         │                                       │
         │                               PHASE 4 (LLM)
         │                                       │
         ├► PHASE 5 (Frontend) ─────────────────┤
         │        uses mocks until Phase 3       │
         │                                       ▼
         └───────────────────────────────► PHASE 6 (Integration)
                                                 │
                                          PHASE 7 (Presentation)
```

---

## PHASE 0 — FOUNDATION

**Owner**: Orchestration Lead (coordinates), all three roles contribute
**Duration**: Day 1 morning
**Prerequisite**: None — this is the starting phase

### Objectives

- [x] Repository initialized with full folder structure
- [x] Environment templates (`.env.example`) created
- [x] Docker compose skeleton defined
- [ ] Input/output schemas finalized in `backend/models/`
- [ ] API contract documented in `docs/API_REFERENCE.md`
- [ ] Mock response structure agreed between backend and frontend
- [ ] All team members can run `docker-compose up` successfully

### Deliverables

| File                              | Owner              | Description                             |
| --------------------------------- | ------------------ | --------------------------------------- |
| `backend/models/input_schema.py`  | Orchestration Lead | Pydantic models for assessment request  |
| `backend/models/output_schema.py` | Orchestration Lead | Pydantic models for assessment response |
| `docs/API_REFERENCE.md`           | Orchestration Lead | Complete API endpoint documentation     |
| `docker-compose.yml`              | Orchestration Lead | Multi-container development setup       |
| `.env.example`                    | Orchestration Lead | Environment variable template           |

### API Contract

The primary endpoint is:

```
POST /api/v1/assess
Content-Type: multipart/form-data

Body:
  - images: File[] (3-5 JPEG/PNG images)
  - gps_latitude: float
  - gps_longitude: float
  - gps_accuracy: float (optional)
  - store_name: string (optional)

Response: AssessmentOutput (see output_schema.py)
```

### Success Criteria

- All three team members have the repo cloned and can build containers
- Input/output schemas are frozen (breaking changes require all-team discussion)
- Frontend Lead can begin building against mock API immediately

---

## PHASE 1 — CV MODULE

**Owner**: Analytics & CV Lead
**Duration**: Day 1 afternoon → Day 2 morning
**Prerequisite**: Phase 0 complete (schemas finalized)
**Parallel**: Can run simultaneously with Phase 2

### Sequence (Order matters — each builds on the previous)

#### 1.1 `image_analyzer.py` — Base Image Analysis

- **Priority**: P0 (blocking for all other CV work)
- **Task**: Implement Gemini Vision API integration
- **Input**: Raw image bytes (base64 or file upload)
- **Processing**:
  1. Construct structured prompt for Gemini Vision API
  2. Send image with extraction instructions
  3. Parse structured response into feature dictionary
  4. Handle API errors, rate limits, and malformed responses
- **Output**: `ImageAnalysisResult` dict with raw features
- **Key Decision**: Prompt engineering is critical. The prompt must ask Gemini to extract specific, quantifiable features — not just describe the image.

#### 1.2 `shelf_density.py` — Shelf Occupancy Scoring

- **Priority**: P0
- **Task**: Extract shelf occupancy metrics from Gemini Vision response
- **Input**: `ImageAnalysisResult` from `image_analyzer.py`
- **Processing**:
  1. Parse shelf-related features from Vision response
  2. Calculate occupancy percentage (filled shelf space / total shelf space)
  3. Detect empty shelf patterns (indicates low stock or poor turnover)
  4. Normalize to 0-1 score
- **Output**: `shelf_density_score: float`, `empty_shelf_ratio: float`

#### 1.3 `sku_diversity.py` — Product Category Detection

- **Priority**: P0
- **Task**: Identify and score product diversity
- **Input**: `ImageAnalysisResult`
- **Processing**:
  1. Identify product categories (FMCG, beverages, tobacco, personal care, snacks, dairy, household)
  2. Count unique SKU clusters per category
  3. Determine brand tier mix (premium/mass/value)
  4. Score diversity using category coverage and depth
- **Output**: `sku_diversity_score: float`, `category_count: int`, `brand_tier: str`, `category_breakdown: dict`

#### 1.4 `inventory_estimator.py` — Inventory Value Estimation

- **Priority**: P1
- **Task**: Estimate total visible inventory value in INR
- **Input**: Shelf density + SKU data + store size estimate
- **Processing**:
  1. Map detected products to wholesale price bands (lookup table)
  2. Estimate quantity per SKU cluster from shelf space allocation
  3. Cross-reference with store size for scale calibration
  4. Output value as a range (low-high), not point estimate
- **Output**: `inventory_value_range: {low: float, high: float}`
- **Key Decision**: Use conservative price bands. Overestimation is a bigger risk than underestimation for credit decisioning.

#### 1.5 `consistency_checker.py` — Multi-Image Validation

- **Priority**: P1
- **Task**: Cross-validate features across multiple images
- **Input**: List of `ImageAnalysisResult` objects (3-5 images)
- **Processing**:
  1. Compare store layout features across images
  2. Check for impossible combinations (e.g., two images showing different store sizes)
  3. Detect potential stock photo usage (unusually high quality, generic composition)
  4. Score consistency as confidence multiplier
- **Output**: `consistency_score: float`, `flags: list[str]`

### Phase 1 Validation

- [ ] Can process 3 test images and return structured CV signals
- [ ] All scores are in [0, 1] range
- [ ] Inventory value range is plausible for store size
- [ ] Consistency checker flags obviously mismatched images

---

## PHASE 2 — GEO MODULE

**Owner**: Analytics & CV Lead
**Duration**: Day 1 afternoon → Day 2 morning (parallel with Phase 1)
**Prerequisite**: Phase 0 complete
**Parallel**: Runs simultaneously with Phase 1

### Sequence

#### 2.1 `geo_analyzer.py` — Base GPS Processing

- **Priority**: P0 (blocking for all other Geo work)
- **Task**: Validate and enrich GPS coordinates
- **Input**: `latitude: float`, `longitude: float`, `accuracy: float`
- **Processing**:
  1. Validate coordinates are within India's bounding box
  2. Reject if GPS accuracy > 100m (unreliable)
  3. Reverse geocode to get locality, district, state, pin code
  4. Classify area type: `urban` / `semi_urban` / `rural`
- **Output**: `GeoBaseResult` with area type, locality, pin code

#### 2.2 `footfall_proxy.py` — Footfall Estimation

- **Priority**: P0
- **Task**: Estimate potential customer footfall from location features
- **Input**: GPS coordinates + area type
- **Processing**:
  1. Query Google Maps Places API for nearby POIs within 500m:
     - Transit stops (bus, metro, rail)
     - Schools, colleges
     - Hospitals, clinics
     - Markets, commercial areas
     - Residential complexes
  2. Score each POI type by footfall contribution weight
  3. Query road type (main road vs interior lane vs highway)
  4. Compute weighted footfall proxy score
- **Output**: `footfall_score: float (0-1)`, `poi_breakdown: dict`

#### 2.3 `competition_density.py` — Competitor Mapping

- **Priority**: P1
- **Task**: Count and map nearby competing stores
- **Input**: GPS coordinates
- **Processing**:
  1. Query OSM Overpass API for retail/convenience stores within 500m
  2. Categorize as: direct competitor (kirana/general store) vs adjacent (supermarket, pharmacy)
  3. Compute competition density score (higher competition = lower score)
  4. Adjust for area type (urban areas naturally have more stores)
- **Output**: `competition_count: int`, `competition_score: float (0-1)`, `competitor_types: dict`

#### 2.4 `catchment_estimator.py` — Demand Estimation

- **Priority**: P1
- **Task**: Estimate serviceable population and demand
- **Input**: GPS coordinates + area type + competition data
- **Processing**:
  1. Define catchment radius: 500m (urban), 1km (semi-urban), 2km (rural)
  2. Estimate population within catchment using density proxies
  3. Compute demand per store: catchment population / (competition count + 1)
  4. Normalize to demand index (0-1)
- **Output**: `catchment_population: int`, `demand_index: float (0-1)`

### Phase 2 Validation

- [ ] Correctly identifies area type for known coordinates
- [ ] Footfall scores correlate intuitively with location quality
- [ ] Competition density returns sensible counts for urban vs rural
- [ ] Catchment radius adjusts for area type

---

## PHASE 3 — FUSION ENGINE

**Owner**: Orchestration Lead
**Duration**: Day 2 afternoon
**Prerequisite**: Phase 1 AND Phase 2 complete (or mock outputs available)

### Sequence

#### 3.1 `fusion_engine.py` — Signal Fusion & Revenue Estimation

- **Priority**: P0
- **Task**: Combine CV and Geo signals into revenue estimate
- **Input**: `CVSignals` + `GeoSignals`
- **Processing**:
  1. Normalize all input signals to [0, 1]
  2. Apply weight matrix:
     ```
     Revenue Score = w1 * shelf_density
                   + w2 * sku_diversity
                   + w3 * inventory_normalized
                   + w4 * footfall_score
                   + w5 * demand_index
                   - w6 * competition_penalty
     ```
  3. Map composite score to revenue range using calibration table
  4. Compute risk band (LOW / MEDIUM / HIGH / VERY_HIGH)
  5. Compute confidence score based on signal quality and consistency
- **Output**: `revenue_estimate`, `risk_band`, `risk_score`, `confidence`
- **Key Decision**: Weights should be configurable per NBFC. Default weights based on economic reasoning, not ML training.

#### 3.2 `fraud_detector.py` — Cross-Signal Fraud Detection

- **Priority**: P0
- **Task**: Detect adversarial or inconsistent submissions
- **Input**: All signals + image metadata
- **Processing**:
  1. **Image Consistency Check**: Leverage `consistency_checker.py` output
  2. **GPS-Visual Mismatch**: Compare store profile vs location profile
  3. **Signal Cross-Validation**: Flag impossible signal combinations
  4. **Statistical Outlier**: Compare against area-type distributions
  5. Compute aggregate fraud score (0-1)
  6. Flag if `fraud_score >= 0.5` or any individual fraud check reaches the severe-review threshold
- **Output**: `fraud_score`, `is_flagged`, `flags`, `checks_performed`

#### 3.3 `loan_sizer.py` — Loan Range Estimation

- **Priority**: P0
- **Task**: Convert revenue estimate to actionable loan recommendation
- **Input**: Revenue estimate + risk band + fraud score
- **Processing**:
  1. Calculate monthly EMI capacity: `revenue_estimate.monthly_low * emi_ratio`
  2. Apply risk band multiplier (LOW=1.0, MEDIUM=0.8, HIGH=0.6, VERY_HIGH=0.0)
  3. Compute sustainable loan range from EMI capacity × tenure options
  4. Cap at ₹5L or policy maximum
  5. If fraud flagged → eligible = false
- **Output**: `loan_range`, `suggested_tenure`, `estimated_emi`, `eligible`

#### 3.4 `output_formatter.py` — Final Output Assembly

- **Priority**: P0
- **Task**: Assemble all upstream results into final API response
- **Input**: All module outputs
- **Processing**:
  1. Merge CV signals, Geo signals, fusion output, fraud detection, loan sizing
  2. Generate session/assessment IDs
  3. Attach timestamp and metadata
  4. Validate output against `AssessmentOutput` schema
  5. Store in PostgreSQL for audit trail
- **Output**: Complete `AssessmentOutput` JSON

### Phase 3 Validation

- [ ] Fusion with mock inputs produces sensible revenue ranges
- [ ] Fraud detector correctly flags test adversarial scenarios
- [ ] Loan sizer respects risk band multipliers and caps
- [ ] Output matches `AssessmentOutput` schema exactly

---

## PHASE 4 — LLM EXPLANATION LAYER

**Owner**: Orchestration Lead
**Duration**: Day 2 evening
**Prerequisite**: Phase 3 complete

### Sequence

#### 4.1 `explainer.py` — Risk Narrative Generation

- **Priority**: P1
- **Task**: Generate human-readable risk assessment narrative
- **Input**: Fusion output + raw signals
- **Processing**:
  1. Construct structured prompt for Gemini Pro:
     - Include all signal values with labels
     - Ask for 3-5 sentence risk assessment in plain English
     - Include strengths and concerns
  2. Parse response and validate tone/content
  3. Fallback to template-based explanation if API fails
- **Output**: `risk_narrative: str`

#### 4.2 `risk_summarizer.py` — Structured Summary

- **Priority**: P1
- **Task**: Generate structured strength/concern/recommendation summary
- **Input**: Full assessment output
- **Processing**:
  1. Extract top 3 strengths from signal analysis
  2. Extract top 3 concerns
  3. Generate recommendation (Approve / Review / Decline)
  4. Format as structured JSON
- **Output**: `summary: {strengths, concerns, recommendation}`

### Phase 4 Validation

- [ ] Risk narratives are coherent and reference actual store signals
- [ ] Summaries correctly identify top strengths and concerns
- [ ] Template fallback works when API is unavailable

---

## PHASE 5 — FRONTEND

**Owner**: Frontend Lead
**Duration**: Day 1 afternoon → Day 2 (parallel with backend)
**Prerequisite**: Phase 0 complete (API contract agreed)
**Note**: Uses mock API responses until Phase 3 is live

### Sequence

#### 5.1 `Home.jsx` — Landing Page

- Product framing and value proposition
- "Start Assessment" CTA
- How it works section (3 steps)
- Clean, professional design

#### 5.2 `Assessment.jsx` — Input Form

- Multi-image upload (3-5 images with preview)
- Image type selection (interior / exterior / shelf closeup)
- GPS coordinate input (auto-detect + manual override)
- Optional store name field
- Form validation and submit handling

#### 5.3 `kiraApi.js` — API Integration

- `submitAssessment(formData)` → POST /api/v1/assess
- `getAssessmentStatus(sessionId)` → GET /api/v1/assess/{id}
- Mock response functions matching exact output schema
- Toggle between mock and live API via env variable

#### 5.4 `ResultsDashboard.jsx` — Results Display

- Revenue estimate with range visualization
- Risk band display with color coding
- CV signals breakdown
- Geo signals breakdown
- Confidence score indicators

#### 5.5 `RiskScoreCard.jsx` — Risk Visualization

- Circular/gauge risk score display
- Risk band label (LOW/MEDIUM/HIGH/VERY_HIGH)
- Confidence indicator
- Color-coded presentation

#### 5.6 `LoanOfferCard.jsx` — Loan Recommendation

- Loan range display (min-max)
- Suggested tenure
- EMI estimate
- Eligibility status

#### 5.7 `FraudFlagBanner.jsx` — Fraud Warning

- Conditional banner (only shown if `is_flagged: true`)
- Lists specific fraud flags
- Professional, non-alarming presentation

#### 5.8 `Results.jsx` — Full Results Page

- Assembles all result components
- Risk narrative display
- Summary section (strengths/concerns/recommendation)
- Assessment metadata

### Phase 5 Validation

- [ ] All pages render correctly with mock data
- [ ] Image upload works with preview
- [ ] GPS auto-detection works in browser
- [ ] Results display matches output schema
- [ ] Responsive design works on mobile

---

## PHASE 6 — INTEGRATION & TESTING

**Owner**: All roles
**Duration**: Day 2 evening → Day 3 morning
**Prerequisite**: Phases 1-5 substantially complete

### Tasks

1. **Connect Frontend to Live Backend**
   - Switch `kiraApi.js` from mock to live API
   - Test end-to-end flow: upload → process → display
   - Debug CORS, file upload, and response format issues

2. **End-to-End Testing**
   - Prepare 5+ synthetic test cases with varied store profiles
   - Test happy path (good store, good location)
   - Test edge cases (rural store, very small store)
   - Verify revenue estimates are plausible

3. **Fraud Scenario Testing**
   - Overstocked shelf images + low footfall GPS → should flag
   - Same images submitted twice → should flag
   - Premium store images + rural GPS → should flag
   - Mismatch between exterior and interior → should flag

4. **Output Calibration**
   - Review revenue ranges against known store benchmarks
   - Adjust fusion engine weights if needed
   - Tune confidence score sensitivity

5. **Docker Compose Full Stack**
   - `docker-compose up --build` runs all services
   - Database initializes correctly
   - Frontend can reach backend
   - All API calls work through Docker networking

### Phase 6 Validation

- [ ] Full end-to-end flow works from image upload to results display
- [ ] All fraud scenarios correctly flagged
- [ ] Revenue estimates within plausible ranges
- [ ] Docker compose runs without errors

---

## PHASE 7 — PRESENTATION LAYER

**Owner**: Orchestration Lead
**Duration**: Day 3
**Prerequisite**: Phase 6 complete

### Tasks

1. **Finalize `BUSINESS_CONTEXT.md`** for presentation deck content
2. **Write Demo Script**
   - 3-minute live demo flow
   - Pre-staged test images and coordinates
   - Talking points for each screen
3. **Judging Criteria Checklist Review**
   - Map every criterion to specific KIRA feature
   - Prepare 1-sentence answers for each criterion
4. **README Polish**
   - Final review of README.md
   - Ensure quick start instructions work
   - Add demo screenshot placeholders
5. **Strategic Framing**
   - Incorporate Poonawalla Fincorp product context
   - Position KIRA as complementary to existing stack
   - Emphasize deployability, not just innovation

---

## PHASE 8 - PLATFORM FOUNDATION

**Owner**: Orchestration Lead  
**Duration**: Sprint 3  
**Prerequisite**: Phase 6 complete

This phase transforms KIRA from a stateless assessment tool into a persistent lender platform.

### Objectives

- Introduce multi-entity persistence beyond `AssessmentOutput`
- Create lender-side domain model for kiranas, cases, loan offers, loans, monitoring runs, and documents
- Add role-aware account structure for lender organizations
- Establish audit logging as a first-class capability
- Seed realistic demo data for portfolio development

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `backend/models/platform_schema.py` | Orchestration Lead | Domain entities for lender orgs, kiranas, cases, offers, loans, alerts |
| `backend/services/case_service.py` | Orchestration Lead | Case lifecycle management |
| `backend/services/audit_service.py` | Orchestration Lead | Immutable audit-event recording |
| `backend/storage/repository.py` | Orchestration Lead | Persistence abstraction for assessments, kiranas, and loans |
| `frontend/src/data/demoPortfolio.js` | Frontend Lead | Seeded lender demo data |
| `docs/API_REFERENCE.md` | Orchestration Lead | Expanded platform endpoint plan |

### Domain Model to Introduce

- `LenderOrg`
- `User`
- `KiranaProfile`
- `AssessmentCase`
- `LoanRecommendation`
- `LoanDecision`
- `LoanAccount`
- `StatementUpload`
- `MonitoringRun`
- `RiskAlert`
- `DocumentBundle`
- `AuditEvent`

### Sequence

#### 8.1 Persistence Design

- Decide storage strategy for the next phase of the app
- Separate assessment snapshot data from living loan records
- Ensure every entity is linked by stable IDs

#### 8.2 Role and Workspace Model

- Support `admin` and `loan_officer` roles
- Scope data by lender organization
- Avoid cross-tenant data leakage by design

#### 8.3 Case State Machine

- Define statuses: `draft`, `submitted`, `under_review`, `approved`, `disbursed`, `monitoring`, `restructured`, `closed`
- Capture transitions with timestamps and actor IDs

#### 8.4 Audit Foundation

- Record create, update, approve, override, upload, and export events
- Make audit data queryable for UI and reports

### Phase 8 Validation

- Domain entities exist with clean ownership boundaries
- Case and loan records persist independently of assessment response payloads
- Audit events are written for all major actions
- Demo data can support frontend platform screens before full backend completion

---

## PHASE 9 - LENDER WORKSPACE

**Owner**: Frontend Lead  
**Duration**: Sprint 3-4  
**Prerequisite**: Phase 8 complete  
**Parallel**: Can run with Phase 10

### Objectives

- Replace the single-flow MVP UI with a lender dashboard experience
- Let lenders view kiranas, cases, assessments, and active loans in one workspace
- Keep the current assessment flow available, but embed it inside case management

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `frontend/src/pages/Login.jsx` | Frontend Lead | Lender login screen or auth placeholder |
| `frontend/src/pages/Dashboard.jsx` | Frontend Lead | Main lender landing page |
| `frontend/src/pages/KiranaList.jsx` | Frontend Lead | List view of all kiranas and cases |
| `frontend/src/pages/KiranaDetail.jsx` | Frontend Lead | Full borrower record with timeline |
| `frontend/src/pages/NewCase.jsx` | Frontend Lead | Guided onboarding and assessment launch |
| `frontend/src/components/layout/LenderShell.jsx` | Frontend Lead | Persistent nav, header, and workspace layout |
| `frontend/src/components/CaseTimeline.jsx` | Frontend Lead | Full activity history for a borrower |

### Sequence

#### 9.1 Authentication Shell

- Add login screen or mocked auth entry
- Route users into lender workspace rather than public landing only

#### 9.2 Dashboard Navigation

- Left navigation for dashboard, kiranas, active loans, portfolio, documents
- Header context for organization and user role

#### 9.3 Kirana and Case List Views

- Search by store name, owner, district, pin code
- Filter by case status and risk tier
- Show latest assessment and next action

#### 9.4 Borrower Detail View

- Basic profile
- Assessment history
- Loan history
- Statement uploads
- Risk alert timeline

### Phase 9 Validation

- Lender can navigate from dashboard to case to borrower detail
- Demo data supports realistic end-to-end walkthrough
- Existing assessment pages still function or are cleanly absorbed into the new shell

---

## PHASE 10 - UNDERWRITING 2.0

**Owner**: Analytics Lead with Orchestration Lead support  
**Duration**: Sprint 3-4  
**Prerequisite**: Phase 8 complete  
**Parallel**: Can run with Phase 9

This phase upgrades KIRA from a "yes/no plus loan range" engine into an actionable underwriting assistant.

### Objectives

- Recommend a concrete loan amount, not only a range
- Recommend repayment structure based on observed cash-flow rhythm
- Add pricing guidance tied to risk
- Generate explainable decision support for loan officers
- Support lender override with reason capture

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `backend/orchestration/loan_sizer.py` | Orchestration Lead | Extend from range output to concrete recommendation |
| `backend/orchestration/repayment_recommender.py` | Analytics Lead | Daily, weekly, or monthly repayment suggestion |
| `backend/orchestration/pricing_engine.py` | Analytics Lead | Dynamic pricing and fee suggestion |
| `backend/llm_layer/explainer.py` | Orchestration Lead | Expand into officer-friendly explainability |
| `frontend/src/components/UnderwritingDecisionPanel.jsx` | Frontend Lead | Decision summary for officer review |
| `frontend/src/components/OverrideDecisionForm.jsx` | Frontend Lead | Override amount, tenure, pricing with reason |

### Sequence

#### 10.1 Concrete Loan Recommendation

- Move from broad range to `recommended_amount`
- Keep `loan_range` as policy guardrail
- Base recommendation on conservative revenue estimate and policy cap

#### 10.2 Repayment Structure Suggestion

- Infer whether daily, weekly, or monthly collection fits the merchant best
- Use observed inflow regularity and seasonality markers where available
- Default to simple heuristics when data is incomplete

#### 10.3 Pricing Recommendation

- Suggest rate and fee band based on risk, confidence, and utilization assumptions
- Keep lender override mandatory for any exception outside policy

#### 10.4 Explainable Decision Pack

- Generate officer-facing explanation:
  - why this amount
  - why this tenure
  - why this repayment cadence
  - key strengths
  - key concerns

#### 10.5 Override Logging

- Record original recommendation
- Record officer override values
- Capture reason text and timestamp

### Phase 10 Validation

- System recommends a concrete amount and cadence for each assessment
- Officer can override decision inputs without breaking auditability
- Explanations align with model outputs and policy logic

---

## PHASE 11 - LOAN LIFECYCLE AND MONITORING

**Owner**: Orchestration Lead with Analytics Lead support  
**Duration**: Sprint 4-5  
**Prerequisite**: Phase 9 and Phase 10 complete

This is the phase that turns KIRA into a live lender product after approval.

### Objectives

- Convert approved cases into real loan accounts inside the system
- Allow fresh statement uploads after disbursement
- Re-score borrowers periodically
- Flag early stress and suspicious usage
- Surface restructuring suggestions before severe delinquency

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `backend/services/loan_service.py` | Orchestration Lead | Loan creation, status changes, booking, closure |
| `backend/services/statement_parser.py` | Orchestration Lead | Parse uploaded PDF or CSV bank and UPI data |
| `backend/services/monitoring_service.py` | Orchestration Lead | Scheduled or manual re-assessment pipeline |
| `backend/orchestration/utilization_tracker.py` | Analytics Lead | Post-disbursement spend categorization heuristics |
| `backend/orchestration/restructuring_advisor.py` | Analytics Lead | Early restructuring recommendation logic |
| `frontend/src/components/StatementUploadCard.jsx` | Frontend Lead | Upload refreshed statements |
| `frontend/src/components/RiskTimeline.jsx` | Frontend Lead | Monitoring history and alerts |
| `frontend/src/pages/LoanAccount.jsx` | Frontend Lead | Active loan detail view |

### Sequence

#### 11.1 Approval to Loan Booking Flow

- When lender approves a case, create a `LoanDecision`
- On disbursement confirmation, create `LoanAccount`
- Freeze the original assessment snapshot for traceability

#### 11.2 Statement Upload Pipeline

- Support manual upload for fresh UPI or bank statements
- Store source file metadata and parsed transaction summaries
- Handle malformed files gracefully

#### 11.3 Monitoring Re-Score

- Recompute risk using latest statement-derived features plus prior assessment context
- Record each monitoring run separately from the original underwriting run

#### 11.4 Loan Utilization Tracking

- Classify post-disbursement outflows:
  - supplier or inventory-like
  - transfer or wallet-like
  - personal or cash-withdrawal-like
  - unknown
- Flag unusual diversion patterns conservatively

#### 11.5 Early Stress and Restructuring

- Detect meaningful drops in inflow velocity
- Generate alerts for potential stress
- Suggest tenor extension or temporary relief when appropriate

### Phase 11 Validation

- Approved borrowers become persistent loan accounts
- Fresh statement upload triggers a new monitoring run
- Alerts appear for deteriorating cash-flow patterns
- Utilization tracker produces usable categories, even if heuristic-based

---

## PHASE 12 - PORTFOLIO COMMAND CENTER

**Owner**: Frontend Lead with Analytics Lead support  
**Duration**: Sprint 5  
**Prerequisite**: Phase 11 complete

### Objectives

- Give the lender a true portfolio dashboard rather than isolated case pages
- Show risk concentration, loan counts, and stress distribution across the book
- Support geographic and status-based drilldown

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `backend/analytics/portfolio_metrics.py` | Analytics Lead | KPI aggregation and summary metrics |
| `backend/analytics/cohort_analysis.py` | Analytics Lead | Cohort, segmentation, and benchmark logic |
| `frontend/src/pages/Portfolio.jsx` | Frontend Lead | Main portfolio screen |
| `frontend/src/components/PortfolioKpiStrip.jsx` | Frontend Lead | Summary KPI cards |
| `frontend/src/components/LoanTable.jsx` | Frontend Lead | Filterable loan and kirana list |
| `frontend/src/components/RiskHeatmap.jsx` | Frontend Lead | Risk concentration by geography or segment |
| `frontend/src/components/CohortChart.jsx` | Frontend Lead | Cohort and trend visualization |

### Sequence

#### 12.1 Portfolio KPIs

- Total kiranas onboarded
- Total approved and disbursed
- Active exposure
- High-risk count
- Stress-alert count
- Restructured count

#### 12.2 Filter and Drilldown

- Filter by state, district, pin code, status, risk tier, product type
- Search by borrower or store name

#### 12.3 Risk Distribution Views

- Heatmap by geography
- Breakdown by case stage
- Monitoring status and alert severity

#### 12.4 Cohort and Benchmark Analytics

- Compare vintages, regions, and merchant segments
- Start with internal cohort comparisons
- Add external benchmark placeholders for later data integration

### Phase 12 Validation

- Lender can answer "where is my risk?" from one screen
- Filters and drilldowns match underlying loan data
- Portfolio metrics remain stable and reproducible

---

## PHASE 13 - COMPLIANCE AND LOAN FILE AUTOMATION

**Owner**: Orchestration Lead  
**Duration**: Sprint 5  
**Prerequisite**: Phase 11 complete  
**Parallel**: Can run with Phase 12

### Objectives

- Turn platform activity into exportable loan files
- Make every important action auditable
- Reduce manual preparation for sanction and review packets

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `backend/services/document_builder.py` | Orchestration Lead | Deterministic loan and case file generation |
| `backend/services/compliance_exporter.py` | Orchestration Lead | Export audit and reporting bundles |
| `backend/templates/` | Orchestration Lead | Sanction, case summary, and monitoring templates |
| `frontend/src/components/DocumentCenter.jsx` | Frontend Lead | Download and export center |
| `frontend/src/components/AuditLogTable.jsx` | Frontend Lead | Human-readable audit log view |

### Sequence

#### 13.1 Document Bundle Definitions

- Underwriting summary
- Sanction note
- Decision override sheet
- Monitoring history summary
- Audit event export

#### 13.2 Deterministic File Generation

- Use structured templates with inserted values
- Use LLM only for narrative sections where helpful
- Avoid free-form generation for policy-critical fields

#### 13.3 Audit Log UI and Exports

- Filter by entity, user, event type, and date
- Export PDF or structured machine-readable formats where appropriate

### Phase 13 Validation

- Every loan can generate a complete file packet
- Override reasons and approval actions appear in audit exports
- Reports are reproducible and not dependent on live model calls

---

## PHASE 14 - ADVANCED INTELLIGENCE

**Owner**: Shared - Analytics Lead drives models, Orchestration Lead owns integration, Frontend Lead owns surfacing  
**Duration**: Sprint 6+  
**Prerequisite**: Phases 12 and 13 complete

This phase contains the higher-ambition features that should only be built after the lender workflow is real and persistent.

### Objectives

- Add forecasting and richer stress prediction
- Introduce Account Aggregator integration points
- Strengthen fraud checks using longitudinal behavior
- Improve benchmark analytics and scenario testing

### Deliverables

| File or Module | Owner | Description |
| --- | --- | --- |
| `backend/analytics/forecasting.py` | Analytics Lead | 30-day and 90-day liquidity forecasting |
| `backend/integrations/account_aggregator.py` | Orchestration Lead | AA connector abstraction and consent flow placeholder |
| `backend/orchestration/enhanced_fraud.py` | Analytics Lead | Statement anomaly and behavioral fraud rules |
| `backend/analytics/stress_testing.py` | Analytics Lead | Scenario analysis such as monsoon or locality demand shock |
| `frontend/src/components/ForecastPanel.jsx` | Frontend Lead | Liquidity gap and stress outlook UI |
| `frontend/src/components/ScenarioSimulator.jsx` | Frontend Lead | What-if simulation interface |

### Sequence

#### 14.1 Forecasting

- Predict near-term inflow and outflow patterns
- Surface projected liquidity gaps

#### 14.2 Restructuring Intelligence Upgrade

- Move from heuristic alerts to stronger recommendation logic
- Prioritize intervention timing and expected impact

#### 14.3 Account Aggregator Path

- Add consent request placeholder
- Support future automated data refresh without redesigning the platform

#### 14.4 Longitudinal Fraud and Benchmarking

- Flag sudden supplier spikes
- Detect suspicious statement changes across cycles
- Compare regions and merchant types across lender portfolio

### Phase 14 Validation

- Forecast outputs are consistent with stored history
- Advanced fraud checks improve recall without overwhelming reviewers
- AA integration can be enabled later without breaking current workflows

---

## Recommended Build Order From Today

If the team starts the next round of implementation immediately, the recommended order is:

1. Finish or stabilize anything missing in Phases 6 and 7
2. Execute Phase 8 first
3. Split work between Phase 9 and Phase 10 in parallel
4. Rejoin on Phase 11 because it depends on both tracks
5. Split again across Phase 12 and Phase 13
6. Leave Phase 14 for after the workflow is already demoable

This gives the team the fastest route to a convincing product:

- first: lender workspace and persistent records
- then: richer underwriting decisions
- then: live monitoring and portfolio intelligence
- finally: advanced forecasting and integrations

---

## Legacy Dependency Graph Summary

```
Phase 0 (Foundation)
├──► Phase 1 (CV Module)     ──┐
├──► Phase 2 (Geo Module)    ──┤
├──► Phase 5 (Frontend)        │
│    (uses mocks)              │
│                              ▼
│                    Phase 3 (Fusion Engine)
│                              │
│                              ▼
│                    Phase 4 (LLM Layer)
│                              │
└──────────────────────────────┤
                               ▼
                     Phase 6 (Integration)
                               │
                               ▼
                     Phase 7 (Presentation)
```

The full lender-platform dependency path is shown below in **Updated Dependency Graph Summary**.

---

## Updated Dependency Graph Summary

```text
Phase 0 -> Phase 1
Phase 0 -> Phase 2
Phase 0 -> Phase 5
Phase 1 + Phase 2 -> Phase 3
Phase 3 -> Phase 4
Phase 3 + Phase 4 + Phase 5 -> Phase 6
Phase 6 -> Phase 7
Phase 6 -> Phase 8
Phase 8 -> Phase 9
Phase 8 -> Phase 10
Phase 9 + Phase 10 -> Phase 11
Phase 11 -> Phase 12
Phase 11 -> Phase 13
Phase 12 + Phase 13 -> Phase 14
```

---

## Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Image and geo signals remain too noisy for confident loan sizing | Weak underwriting credibility | Keep outputs conservative and explainable; preserve manual override |
| Multi-tenant model is added too late | Painful refactor across the whole app | Introduce tenant-aware IDs and role model in Phase 8 |
| Statement parsing is brittle across PDF formats | Monitoring flow becomes unreliable | Support PDF plus CSV; store parse confidence and allow manual correction |
| Fraud rules become too aggressive | Review team loses trust in alerts | Separate soft alerts from hard flags; tune thresholds with demo data |
| Dashboard work starts before persistent entities exist | Frontend velocity stalls on unstable contracts | Finish Phase 8 before major portfolio UI work |
| Compliance docs depend too much on LLM output | Inconsistent exports | Use deterministic templates for policy-critical sections |
| Team parallel work conflicts | Merge delays and unclear ownership | Keep files and modules phase-owned; freeze interfaces before parallel implementation |

---

_Implementation Plan v1.0 — KIRA Project_
_(Expanded with Phase 8-14 lender-platform roadmap)_  
_Last Updated: April 13, 2026_

# KIRA — Implementation Plan

> Phased development roadmap with ownership, sequencing, and dependency tracking.

---

## Phase Overview

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

## Dependency Graph Summary

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

---

## Risk Register

| Risk                                | Impact                     | Mitigation                                                     |
| ----------------------------------- | -------------------------- | -------------------------------------------------------------- |
| Gemini Vision API rate limits       | CV module blocked          | Implement caching; use 3 images not 5                          |
| OSM Overpass API downtime           | Geo module incomplete      | Cache responses; hardcode test data                            |
| Revenue estimates wildly inaccurate | Demo credibility           | Use conservative ranges; emphasize methodology over precision  |
| Image upload exceeds API limits     | Can't process large images | Resize on frontend before upload; cap at 2MB per image         |
| Team member unavailable             | Phase delays               | Each phase has clear specs; any member can implement from docs |

---

_Implementation Plan v1.0 — KIRA Project_
_Last Updated: April 2025_

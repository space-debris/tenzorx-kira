# KIRA — System Architecture

> **Kirana Intelligence & Risk Assessment**
> AI-powered remote cash flow underwriting for India's 13 million kirana stores.

---

## 1. System Overview & Problem Framing

KIRA is an AI-powered underwriting system that estimates a kirana store's daily/monthly revenue and creditworthiness using only **smartphone images** and **GPS coordinates** — with zero dependency on GST data, bank statements, or credit bureau scores.

### The Problem

India has **13 million kirana stores**. They represent the backbone of India's retail distribution, handling an estimated ₹12 lakh crore in annual trade. Yet these stores are structurally invisible to formal credit infrastructure:

- **Cash-dominant**: 80-90% of transactions are cash. UPI adoption is growing but doesn't capture B2B procurement.
- **GST-exempt**: Stores below ₹40L annual turnover (the vast majority) are not required to file GST returns.
- **Thin bureau files**: No formal credit history. Most proprietors have sparse or absent CIBIL records.
- **No digital paper trail**: No invoicing software, no inventory management systems, no POS data.

### Why Existing NBFC Underwriting Fails

Modern NBFC underwriting stacks rely on three pillars — all of which fail for kirana stores:

| Pillar | Mechanism | Why It Fails for Kirana |
|--------|-----------|------------------------|
| **GST Returns** | Revenue proxy via filed returns | 80%+ stores are below ₹40L threshold; no GST filing |
| **Account Aggregator** | Bank statement analysis | Cash-dominant; bank flows understate true revenue by 50-70% |
| **Credit Bureau (CIBIL)** | Existing credit behavior scoring | First-time borrowers; thin or absent bureau files |

This creates a structural exclusion: the very stores that need working capital credit the most are the ones that cannot be underwritten by existing systems.

### KIRA's Thesis

**Physical stores leak information visually and spatially.** A kirana store's shelf density, product diversity, inventory freshness, brand composition, and physical footprint are observable proxies for working capital deployed, sales velocity, and revenue. Similarly, a store's GPS location encodes footfall potential, competitive density, and catchment demand.

KIRA systematically extracts, quantifies, and fuses these signals into a creditworthiness assessment.

---

## 2. Three-Layer Architecture

KIRA operates on three intelligence layers that feed into a fusion engine:

```
┌─────────────────────────────────────────────────────────────────┐
│                    KIRA ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LAYER 1: VISUAL INTELLIGENCE          LAYER 2: GEO INTELLIGENCE│
│  ┌──────────────────────────┐          ┌──────────────────────┐ │
│  │  • Shelf Density         │          │  • Footfall Proxy    │ │
│  │  • SKU Diversity         │          │  • Competition       │ │
│  │  • Inventory Estimation  │          │    Density           │ │
│  │  • Consistency Checking  │          │  • Catchment         │ │
│  │  • Store Size Estimation │          │    Estimation        │ │
│  └───────────┬──────────────┘          └──────────┬───────────┘ │
│              │                                     │             │
│              └──────────┬──────────────────────────┘             │
│                         ▼                                        │
│           ┌─────────────────────────────┐                        │
│           │   LAYER 3: FUSION ENGINE    │                        │
│           │   • Weighted Signal Fusion  │                        │
│           │   • Fraud Detection         │                        │
│           │   • Revenue Estimation      │                        │
│           │   • Loan Sizing             │                        │
│           │   • LLM Explanation         │                        │
│           └─────────────┬───────────────┘                        │
│                         ▼                                        │
│              ┌──────────────────────┐                            │
│              │   OUTPUT API         │                            │
│              │   → Frontend         │                            │
│              └──────────────────────┘                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Full Data Flow

```
                          ┌─────────────────────┐
                          │   SMARTPHONE INPUT   │
                          │  • 3-5 store images  │
                          │  • GPS coordinates   │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                                  ▼
        ┌───────────────────┐              ┌───────────────────┐
        │    CV MODULE       │              │    GEO MODULE      │
        │  (Gemini Vision)   │              │  (Maps + OSM)      │
        ├───────────────────┤              ├───────────────────┤
        │ image_analyzer.py  │              │ geo_analyzer.py    │
        │   ├─ Parse images  │              │   ├─ Validate GPS  │
        │   └─ Extract base  │              │   └─ Reverse       │
        │      features      │              │      geocode       │
        │                    │              │                    │
        │ shelf_density.py   │              │ footfall_proxy.py  │
        │   └─ Occupancy %   │              │   └─ Road type +   │
        │                    │              │      POI scoring    │
        │ sku_diversity.py   │              │                    │
        │   └─ Category      │              │ competition_       │
        │      detection     │              │ density.py         │
        │                    │              │   └─ Nearby store   │
        │ inventory_         │              │      count          │
        │ estimator.py       │              │                    │
        │   └─ Value bands   │              │ catchment_         │
        │                    │              │ estimator.py       │
        │ consistency_       │              │   └─ Population     │
        │ checker.py         │              │      & demand       │
        │   └─ Cross-image   │              │      radius         │
        │      validation    │              │                    │
        └────────┬──────────┘              └────────┬──────────┘
                 │                                   │
                 │        CV Signals Object           │
                 │    {shelf_density: 0.82,          │
                 │     sku_count: 145,               │
                 │     inventory_value: "3-5L",      │
                 │     consistency_score: 0.91}      │
                 │                                   │
                 │        Geo Signals Object          │
                 │    {footfall_score: 0.74,          │
                 │     competition_count: 8,          │
                 │     catchment_pop: 15000,          │
                 │     demand_index: 0.68}            │
                 │                                   │
                 └──────────┬────────────────────────┘
                            ▼
              ┌──────────────────────────┐
              │     FUSION ENGINE        │
              │   fusion_engine.py       │
              │   ├─ Normalize signals   │
              │   ├─ Apply weights       │
              │   └─ Compute composite   │
              │      revenue estimate    │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │    FRAUD DETECTOR        │
              │   fraud_detector.py      │
              │   ├─ Cross-signal        │
              │   │   consistency        │
              │   ├─ Image tampering     │
              │   │   detection          │
              │   ├─ GPS spoofing        │
              │   │   checks             │
              │   └─ Statistical         │
              │       outlier flagging   │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │    LLM EXPLAINER         │
              │   explainer.py           │
              │   ├─ Risk narrative      │
              │   └─ Decision rationale  │
              │                          │
              │   risk_summarizer.py     │
              │   └─ Structured summary  │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │     LOAN SIZER           │
              │   loan_sizer.py          │
              │   ├─ Revenue → EMI       │
              │   │   capacity           │
              │   ├─ Risk band →         │
              │   │   loan range         │
              │   └─ Terms & conditions  │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │   OUTPUT FORMATTER       │
              │   output_formatter.py    │
              │   ├─ Assemble final JSON │
              │   ├─ Confidence scores   │
              │   └─ Range estimates     │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │      OUTPUT API          │
              │   POST /api/v1/assess    │
              │                          │
              │   → Frontend Dashboard   │
              └──────────────────────────┘
```

---

## 4. Module Specifications

### 4.1 CV Module — Visual Intelligence

**Owner**: Analytics & CV Lead

| Submodule | Input | Processing | Output |
|-----------|-------|------------|--------|
| `image_analyzer.py` | Raw store images (3-5 JPEG/PNG) | Send to Gemini Vision API with structured extraction prompt; parse response into feature dict | Base feature extraction: store type, size estimate, lighting, organization |
| `shelf_density.py` | Gemini Vision response | Analyze shelf occupancy percentage, empty shelf ratio, stacking patterns | `shelf_density_score: float (0-1)` — higher = more stocked |
| `sku_diversity.py` | Gemini Vision response | Identify product categories (FMCG, beverages, personal care, snacks, etc.); count unique SKU clusters | `sku_diversity_score: float (0-1)`, `category_count: int`, `brand_tier: str` |
| `inventory_estimator.py` | Shelf density + SKU diversity + store size | Cross-reference detected products with known wholesale price bands; estimate total visible inventory value | `inventory_value_range: {low: float, high: float}` in INR |
| `consistency_checker.py` | Multiple image features | Compare features across 3-5 images for internal consistency; detect staging or reuse | `consistency_score: float (0-1)`, `fraud_flags: list[str]` |

#### Visual Signal Economics

The key insight is that **visible inventory ≈ working capital deployed**. A store with ₹3-5L of visible stock on shelves has demonstrably deployed that capital. Combined with estimated turns (30-45 days for FMCG), this yields:

```
Monthly Revenue ≈ Inventory Value × (30 / Avg Days to Turn)
```

This is not a prediction — it's an accounting identity observed through computer vision.

### 4.2 Geo Module — Spatial Intelligence

**Owner**: Analytics & CV Lead

| Submodule | Input | Processing | Output |
|-----------|-------|------------|--------|
| `geo_analyzer.py` | GPS lat/lng | Reverse geocode; validate coordinates are in India; determine area type (urban/semi-urban/rural) | `area_type: str`, `locality: str`, `pin_code: str` |
| `footfall_proxy.py` | GPS coordinates | Query Google Maps for road type, nearby transit stops, schools, hospitals; compute weighted footfall score | `footfall_score: float (0-1)`, `poi_breakdown: dict` |
| `competition_density.py` | GPS coordinates | Query OSM Overpass for nearby retail/convenience stores within 500m radius; count and categorize | `competition_count: int`, `competition_score: float (0-1)` |
| `catchment_estimator.py` | GPS + area type | Estimate population within serviceable radius (500m urban, 2km rural); compute demand per store | `catchment_population: int`, `demand_index: float (0-1)` |

### 4.3 Fusion Engine — Intelligence Synthesis

**Owner**: Orchestration Lead

| Submodule | Input | Processing | Output |
|-----------|-------|------------|--------|
| `fusion_engine.py` | CV signals + Geo signals | Normalize all signals to [0, 1]; apply calibrated weight matrix; compute composite scores | `revenue_estimate: {monthly_low, monthly_high}`, `risk_band: str`, `confidence: float` |
| `fraud_detector.py` | All signals + raw images metadata | Run 4 cross-signal fraud checks (see Section 6) | `fraud_score: float (0-1)`, `flags: list[str]`, `is_flagged: bool` |
| `loan_sizer.py` | Revenue estimate + risk band + fraud score | Apply EMI-to-income ratio, risk multipliers; compute sustainable loan range | `loan_range: {low, high}`, `suggested_tenure: int`, `emi_estimate: float` |
| `output_formatter.py` | All upstream outputs | Assemble final output JSON with all fields, ranges, and confidence scores | Complete `AssessmentOutput` schema |

### 4.4 LLM Explanation Layer

**Owner**: Orchestration Lead

| Submodule | Input | Processing | Output |
|-----------|-------|------------|--------|
| `explainer.py` | Fusion output + raw signals | Craft structured prompt for Gemini Pro; generate human-readable risk narrative | `risk_narrative: str` (3-5 sentences) |
| `risk_summarizer.py` | Full assessment output | Generate structured summary: strengths, concerns, recommendation | `summary: {strengths: list, concerns: list, recommendation: str}` |

---

## 5. Input / Output Schemas

### Input Schema

```json
{
  "session_id": "uuid",
  "images": [
    {
      "image_data": "base64_encoded_string",
      "image_type": "interior | exterior | shelf_closeup",
      "capture_timestamp": "ISO8601"
    }
  ],
  "gps": {
    "latitude": 19.0760,
    "longitude": 72.8777,
    "accuracy_meters": 10.5
  },
  "metadata": {
    "store_name": "optional string",
    "stated_monthly_revenue": "optional float (for calibration only)"
  }
}
```

### Output Schema

```json
{
  "session_id": "uuid",
  "assessment_id": "uuid",
  "timestamp": "ISO8601",

  "revenue_estimate": {
    "monthly_low": 150000,
    "monthly_high": 280000,
    "confidence": 0.72,
    "methodology": "inventory_turnover_model"
  },

  "risk_assessment": {
    "risk_band": "MEDIUM",
    "risk_score": 0.45,
    "confidence": 0.68
  },

  "cv_signals": {
    "shelf_density": 0.82,
    "sku_diversity_score": 0.71,
    "estimated_sku_count": 145,
    "inventory_value_range": {"low": 300000, "high": 500000},
    "store_size_category": "medium",
    "brand_tier_mix": "mass_dominant",
    "consistency_score": 0.91
  },

  "geo_signals": {
    "area_type": "semi_urban",
    "footfall_score": 0.74,
    "competition_count": 8,
    "competition_score": 0.55,
    "catchment_population": 15000,
    "demand_index": 0.68
  },

  "loan_recommendation": {
    "eligible": true,
    "loan_range": {"low": 100000, "high": 250000},
    "suggested_tenure_months": 18,
    "estimated_emi": 6500,
    "emi_to_income_ratio": 0.15
  },

  "fraud_detection": {
    "fraud_score": 0.12,
    "is_flagged": false,
    "flags": [],
    "checks_performed": [
      "image_consistency",
      "gps_location_validity",
      "signal_cross_validation",
      "statistical_outlier_detection"
    ]
  },

  "explanation": {
    "risk_narrative": "string — 3-5 sentence human-readable assessment",
    "summary": {
      "strengths": ["Well-stocked shelves", "High footfall location"],
      "concerns": ["High competition density"],
      "recommendation": "Approve with standard terms"
    }
  }
}
```

---

## 6. Fraud & Adversarial Signal Detection

KIRA implements four cross-signal fraud checks:

### Check 1: Image Consistency
- Compare features extracted from multiple images of the same store
- Flag if images appear to be from different stores (different product sets, lighting, store layout)
- Flag if images are stock photos or previously submitted

### Check 2: GPS-Visual Mismatch
- Cross-validate store size/type from images with expected store profile for the GPS location
- Flag: premium store images + rural GPS coordinates
- Flag: large store images + residential neighborhood GPS

### Check 3: Signal Cross-Validation
- Flag: extremely high shelf density + very low competition area (unusual for low-demand zones)
- Flag: high inventory value + low footfall area (why stock heavily if no customers?)
- Flag: premium brand mix + very low-income catchment area

### Check 4: Statistical Outlier Detection
- Compare extracted signals against distribution of known stores in similar area types
- Flag assessments where any signal is >3 standard deviations from the area-type mean
- Use Mahalanobis distance for multivariate outlier detection

---

## 7. Scalability & Deployment Architecture

### Current (Hackathon)
```
Docker Compose → Single machine
├── PostgreSQL container
├── FastAPI container (1 worker)
└── React container (Vite dev server)
```

### Production Path
```
Cloud Deployment (GCP/AWS)
├── Cloud SQL (PostgreSQL)
├── Cloud Run / ECS (FastAPI, auto-scaling)
├── CDN-hosted React SPA (Vercel/Cloudfront)
├── Redis cache (Gemini API response caching)
├── Cloud Storage (image storage with lifecycle)
└── Pub/Sub queue (async assessment processing)
```

### Key Scaling Considerations
1. **Gemini API rate limits**: Implement request queuing and response caching
2. **Image processing latency**: Async processing with webhook callbacks for production
3. **Database growth**: Partition assessments by month; archive after 12 months
4. **Multi-tenancy**: Designed for white-label deployment across NBFCs

---

## 8. Why This Is Deployable by an NBFC Today

| Requirement | KIRA's Approach |
|-------------|----------------|
| No proprietary data needed | Uses only smartphone images + GPS — data the borrower provides |
| No hardware dependency | Works on any smartphone with a camera and GPS |
| No integration required | Standalone API; can run alongside existing LOS |
| Regulatory compliance | Generates explainable, auditable risk narratives |
| Cost per assessment | ~₹2-5 per assessment (API costs only) |
| Assessment time | < 30 seconds end-to-end |
| Field visit replacement | Can screen 100% of applications; field visits only for flagged cases |
| Calibration | Weight matrix can be tuned per NBFC's risk appetite |

---

## 9. Technology Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI (Python) | Async-native, auto-generated OpenAPI docs, type-safe |
| Computer Vision | Gemini Vision API | Best-in-class multimodal understanding; structured extraction |
| LLM | Gemini Pro API | Consistent with CV API; strong structured output |
| Geo Data | Google Maps Places + OSM Overpass | Maps for POI/footfall; OSM for competition (free, comprehensive) |
| Frontend | React (Vite) | Fast dev iteration; rich component ecosystem |
| Database | PostgreSQL | ACID compliance for audit trails; JSON column support |
| Containerization | Docker + docker-compose | Reproducible environments; single-command deployment |

---

*Architecture Document v1.0 — KIRA Project*
*Last Updated: April 2025*

# KIRA — Judging Criteria Map

> Mapping every evaluation criterion from PS4C to specific KIRA modules and capabilities.

---

## Criterion-to-Module Mapping

### 1. Feature Depth

**What judges evaluate**: Richness and sophistication of feature extraction from available data.

**KIRA's answer**: 9 distinct signals across two intelligence layers.

| Signal | Module | Type | Measurement |
|--------|--------|------|-------------|
| Shelf Density | `cv_module/shelf_density.py` | Visual | Occupancy percentage (0-1) |
| SKU Diversity | `cv_module/sku_diversity.py` | Visual | Category count + diversity score |
| Inventory Value | `cv_module/inventory_estimator.py` | Visual | INR range (low-high) |
| Image Consistency | `cv_module/consistency_checker.py` | Visual | Cross-image validation score |
| Store Size | `cv_module/image_analyzer.py` | Visual | Size category (small/medium/large) |
| Footfall Proxy | `geo_module/footfall_proxy.py` | Spatial | Road type + POI weighted score |
| Competition Density | `geo_module/competition_density.py` | Spatial | Nearby store count + adjusted score |
| Catchment Demand | `geo_module/catchment_estimator.py` | Spatial | Population ÷ stores in radius |
| Area Classification | `geo_module/geo_analyzer.py` | Spatial | Urban/semi-urban/rural |

**Key differentiator**: These are not arbitrary features. Each one maps to a specific component of the kirana store income statement:
- Shelf density + inventory value → **working capital deployed** (balance sheet proxy)
- SKU diversity + brand tier → **product mix and margin profile** (P&L proxy)
- Footfall + catchment + competition → **revenue potential** (market addressable demand)

---

### 2. Economic Logic

**What judges evaluate**: Is the model economically grounded, or is it a black-box ML prediction?

**KIRA's answer**: Calibrated weighted scoring with transparent economic reasoning.

**Module**: `orchestration/fusion_engine.py`

KIRA does NOT use a black-box ML model to predict income from images. Instead, it follows an economic identity:

```
Monthly Revenue ≈ f(Inventory Value, Turnover Rate, Footfall, Competition)

Where:
  Inventory Value   ← directly observed via CV (working capital deployed)
  Turnover Rate     ← inferred from product type (FMCG = 30-45 day turns)
  Footfall          ← estimated from GPS + POI data
  Competition       ← observed from OSM competitor count
```

This is closer to **financial analysis** than machine learning. The fusion engine applies a **transparent, configurable weight matrix** — not a trained neural network. Every weight has an economic justification:

| Weight | Signal | Economic Reasoning |
|--------|--------|--------------------|
| w1 (0.25) | Shelf Density | Higher stock = more capital deployed = higher revenue capacity |
| w2 (0.20) | SKU Diversity | More categories = broader customer base = higher basket size |
| w3 (0.20) | Inventory Value | Direct proxy for working capital, the best single predictor |
| w4 (0.15) | Footfall Score | More footfall = more transactions per day |
| w5 (0.10) | Demand Index | More demand per store = less competition for revenue |
| w6 (-0.10) | Competition | More competitors = revenue split across more stores |

---

### 3. Uncertainty Modeling

**What judges evaluate**: Does the system output point estimates or acknowledge and quantify uncertainty?

**KIRA's answer**: Range estimates with explicit confidence scores.

**Module**: `orchestration/output_formatter.py`

Every numeric output in KIRA is expressed as a **range, not a point estimate**:

| Output | Format | Example |
|--------|--------|---------|
| Monthly Revenue | `{monthly_low, monthly_high}` | ₹1.5L — ₹2.8L |
| Inventory Value | `{low, high}` | ₹3L — ₹5L |
| Loan Amount | `{low, high}` | ₹1L — ₹2.5L |
| Risk Score | `float (0-1)` with `confidence: float` | 0.45 (confidence: 0.68) |

Additionally:
- **Confidence score** (0-1) on every major output reflects signal quality and internal consistency
- **Confidence degrades** when: fewer images provided, GPS accuracy is low, signals conflict
- **Risk band** (LOW/MEDIUM/HIGH/VERY_HIGH) provides ordinal classification for decisioning

This is intentional: **a creditworthy range with quantified uncertainty is more useful to an NBFC than a precise-looking point estimate with hidden uncertainty.**

---

### 4. Fraud Resilience

**What judges evaluate**: How robust is the system against adversarial or manipulated inputs?

**KIRA's answer**: 4 cross-signal fraud detection checks.

**Module**: `orchestration/fraud_detector.py`

| Check | What It Detects | How |
|-------|----------------|-----|
| **Image Consistency** | Staged/borrowed store images | Cross-validate features across 3-5 images; flag mismatches |
| **GPS-Visual Mismatch** | Location spoofing or wrong GPS | Compare visual store profile against location expectations |
| **Signal Cross-Validation** | Implausible signal combinations | Flag: premium stock + rural slum GPS; huge inventory + no footfall |
| **Statistical Outlier** | Gaming the system | Compare signals against area-type distributions; flag 3σ outliers |

**Aggregate fraud score** (0-1) with binary flag at threshold 0.5. Flagged assessments are marked for manual review; fraud flags are listed explicitly in the output.

**Why this matters**: Any image-based system is vulnerable to adversarial inputs. KIRA's multi-signal approach makes it hard to game — fabricating consistent signals across vision AND geo is much harder than faking a single input.

---

### 5. Practicality / Deployability

**What judges evaluate**: Could an NBFC actually use this in production?

**KIRA's answer**: Yes — today, with zero proprietary dependencies.

| Deployment Requirement | KIRA Status |
|------------------------|-------------|
| **Data inputs** | Smartphone images + GPS. No bank statements, no GST, no bureau. Borrower provides everything. |
| **Hardware** | Any smartphone with a camera and GPS. No special equipment. |
| **Integration** | Standalone REST API. Can sit alongside existing LOS without modification. |
| **Cost** | ~₹2-5 per assessment (Gemini API costs). At scale, cheaper than a field visit (~₹500-2000). |
| **Speed** | < 30 seconds per assessment. Current field visits take days. |
| **Containerized** | Docker compose for development; Cloud Run/ECS for production. |
| **Regulatory** | Generates explainable, auditable risk narratives. No opaque ML. |
| **Calibration** | Weight matrix is configurable per NBFC risk appetite. No retraining required. |

---

### 6. Explainability

**What judges evaluate**: Can a credit officer understand why a particular decision was made?

**KIRA's answer**: LLM-generated risk narratives + structured summaries.

**Module**: `llm_layer/explainer.py`, `llm_layer/risk_summarizer.py`

Every KIRA assessment produces:

1. **Risk Narrative** (3-5 sentences): Human-readable paragraph explaining the assessment
   > "This medium-sized kirana store in a semi-urban location shows strong inventory management with 82% shelf occupancy across 12 product categories. The location benefits from proximity to a school and bus stop, though competition density is moderate with 8 stores within 500m. Estimated monthly revenue of ₹1.5-2.8L supports a loan of ₹1-2.5L with comfortable EMI servicing capacity."

2. **Structured Summary**:
   - **Strengths**: Top 3 positive signals (e.g., "Well-stocked shelves", "High footfall location")
   - **Concerns**: Top 3 risk factors (e.g., "High competition density", "Low GPS accuracy")
   - **Recommendation**: Approve / Review / Decline

3. **Full Signal Breakdown**: Every signal with its raw value and interpretation available for audit

---

## What Separates KIRA from a Generic CV Submission

Many hackathon submissions will use computer vision to look at store images and output a score. Here's what makes KIRA fundamentally different:

### It's Not an ML Prediction — It's Economic Calibration

| Generic Approach | KIRA's Approach |
|-----------------|-----------------|
| Train a model on images → predict revenue | Observe inventory → estimate working capital → infer sales velocity |
| Black-box score | Transparent weighted fusion with economic justification |
| Point estimate | Range with confidence interval |
| Single signal (images only) | Multi-modal: vision + spatial + cross-validation |
| No fraud detection | 4-check adversarial resilience |
| "Cool tech demo" | Deployable underwriting layer |

### The Core Insight

**KIRA does not predict income from images.** It:

1. **Estimates working capital deployed** (visible inventory value from CV)
2. **Infers sales velocity** (inventory turnover from product type + shelf patterns)
3. **Cross-validates with spatial demand** (geo signals: footfall, competition, catchment)
4. **Outputs a range with explicit uncertainty** (not a false-precision point estimate)

This is the difference between a demo and a deployable tool. An NBFC credit officer doesn't need an ML model's "confidence" — they need to understand **why** a loan is recommended and **what could go wrong**.

---

## Scoring Summary

| Criterion | KIRA Feature | Module | Strength (1-5) |
|-----------|-------------|--------|----------------|
| Feature Depth | 9 signals, 2 modalities | CV + Geo modules | ⭐⭐⭐⭐⭐ |
| Economic Logic | Calibrated weighted scoring | Fusion Engine | ⭐⭐⭐⭐⭐ |
| Uncertainty Modeling | Ranges + confidence scores | Output Formatter | ⭐⭐⭐⭐ |
| Fraud Resilience | 4 cross-signal checks | Fraud Detector | ⭐⭐⭐⭐ |
| Deployability | Docker, REST API, zero dependencies | Full stack | ⭐⭐⭐⭐⭐ |
| Explainability | LLM narratives + structured summaries | LLM Layer | ⭐⭐⭐⭐ |

---

*Judging Criteria Map v1.0 — KIRA Project*
*Last Updated: April 2025*

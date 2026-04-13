# KIRA — API Reference

> Complete API endpoint documentation for frontend-backend integration.

---

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.kira.example.com/api/v1
```

---

## Authentication

Currently no authentication required (hackathon build). Production deployment should use API key or OAuth2.

---

## Endpoints

### 1. Submit Assessment

**Create a new kirana store creditworthiness assessment.**

```
POST /api/v1/assess
Content-Type: multipart/form-data
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | `File[]` | Yes | 3-5 JPEG/PNG images of the store (max 2MB each) |
| `image_types` | `string[]` | Yes | Type label for each image: `interior`, `exterior`, `shelf_closeup` |
| `gps_latitude` | `float` | Yes | Latitude coordinate (must be within India) |
| `gps_longitude` | `float` | Yes | Longitude coordinate (must be within India) |
| `gps_accuracy` | `float` | No | GPS accuracy in meters (default: 50) |
| `store_name` | `string` | No | Optional store name for reference |

#### Example Request (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/assess \
  -F "images=@store_interior.jpg" \
  -F "images=@store_exterior.jpg" \
  -F "images=@shelf_closeup.jpg" \
  -F "image_types=interior" \
  -F "image_types=exterior" \
  -F "image_types=shelf_closeup" \
  -F "gps_latitude=19.0760" \
  -F "gps_longitude=72.8777" \
  -F "gps_accuracy=10.5" \
  -F "store_name=Test Kirana Store"
```

#### Success Response (200 OK)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "assessment_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "timestamp": "2025-04-11T14:30:00Z",
  "status": "completed",

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
    "inventory_value_range": {
      "low": 300000,
      "high": 500000
    },
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
    "loan_range": {
      "low": 100000,
      "high": 250000
    },
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
    "risk_narrative": "This medium-sized kirana store in a semi-urban location shows strong inventory management with 82% shelf occupancy across 12 product categories. The location benefits from proximity to a school and bus stop, though competition density is moderate with 8 stores within 500m. Estimated monthly revenue of ₹1.5-2.8L supports a loan of ₹1-2.5L with comfortable EMI servicing capacity.",
    "summary": {
      "strengths": [
        "Well-stocked shelves with 82% occupancy",
        "High footfall location near transit and school",
        "Diverse product mix across 12 categories"
      ],
      "concerns": [
        "Moderate competition with 8 nearby stores",
        "Semi-urban location limits premium pricing"
      ],
      "recommendation": "Approve with standard terms"
    }
  }
}
```

#### Error Responses

| Status | Description | Body |
|--------|-------------|------|
| `400` | Invalid input | `{"error": "validation_error", "detail": "At least 3 images required"}` |
| `400` | Invalid GPS | `{"error": "validation_error", "detail": "GPS coordinates outside India"}` |
| `413` | Image too large | `{"error": "payload_too_large", "detail": "Image exceeds 2MB limit"}` |
| `422` | Processing error | `{"error": "processing_error", "detail": "..."}` |
| `429` | Rate limited | `{"error": "rate_limit", "detail": "Too many requests. Try again in 60s"}` |
| `500` | Server error | `{"error": "internal_error", "detail": "..."}` |

---

### 2. Get Assessment Status

**Retrieve a previously completed assessment by session ID.**

```
GET /api/v1/assess/{session_id}
```

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `uuid` | The session ID returned from the assessment submission |

#### Success Response (200 OK)

Returns the same `AssessmentOutput` schema as the POST endpoint.

#### Error Responses

| Status | Description |
|--------|-------------|
| `404` | Assessment not found |
| `500` | Server error |

---

### 3. Health Check

**Basic health check endpoint.**

```
GET /api/v1/health
```

#### Success Response (200 OK)

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "gemini_api": "available",
    "maps_api": "available"
  }
}
```

---

## Data Types Reference

### Enums

```python
class RiskBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class AreaType(str, Enum):
    URBAN = "urban"
    SEMI_URBAN = "semi_urban"
    RURAL = "rural"

class ImageType(str, Enum):
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    SHELF_CLOSEUP = "shelf_closeup"

class StoreSizeCategory(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class BrandTierMix(str, Enum):
    PREMIUM_DOMINANT = "premium_dominant"
    MASS_DOMINANT = "mass_dominant"
    VALUE_DOMINANT = "value_dominant"
    MIXED = "mixed"
```

### Score Ranges

| Score | Range | Interpretation |
|-------|-------|----------------|
| All signal scores | 0.0 — 1.0 | Higher = better/stronger signal |
| Confidence scores | 0.0 — 1.0 | Higher = more reliable estimate |
| Fraud score | 0.0 — 1.0 | Higher = more suspicious |
| Risk score | 0.0 — 1.0 | Higher = higher risk |

---

## Frontend Integration Notes

1. **Use `multipart/form-data`** for the assessment submission (not JSON), due to image uploads
2. **Poll or wait**: The POST endpoint is synchronous — it blocks until processing completes (~15-30 seconds)
3. **Mock mode**: Set `VITE_USE_MOCK_API=true` in frontend `.env` to use mock responses during development
4. **Error handling**: Always check for `fraud_detection.is_flagged` before displaying loan recommendation
5. **Display formatting**: All INR values are in raw numbers (e.g., `150000` = ₹1,50,000). Format in frontend.

---

*API Reference v1.0 — KIRA Project*
*Last Updated: April 2025*

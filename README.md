# KIRA — Kirana Intelligence & Risk Assessment

> AI-powered remote cash flow underwriting for India's 13 million kirana stores using only smartphone images and GPS coordinates.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Problem Statement

**Poonawalla Fincorp Hackathon — PS4C: Remote Cash Flow Underwriting for Kirana Stores**

India has 13 million kirana stores that collectively handle ₹12 lakh crore in annual trade. Yet they are structurally invisible to formal credit infrastructure:

- **80%+** are below the ₹40L GST threshold — no GST returns exist
- **50-70%** of revenue is cash — bank statements systematically understate income
- **Most proprietors** have no or thin CIBIL records — no credit history exists

Existing NBFC underwriting stacks (GST + Account Aggregator + Bureau) cannot process these applications. The borrowers are not "risky" — they're simply **invisible** to the data infrastructure.

## Solution

KIRA builds the missing underwriting layer using **visual and spatial intelligence** as substitutes for financial statements:

1. **Visual Intelligence** — Smartphone photos of the store reveal working capital deployed (shelf density, SKU diversity, inventory value, brand mix)
2. **Geo Intelligence** — GPS coordinates reveal revenue potential (footfall, competition, catchment population)
3. **Fusion Engine** — Calibrated weighted scoring combines visual + spatial signals into a revenue estimate with explicit uncertainty

**KIRA does not predict income from images. It estimates working capital from visible inventory, infers sales velocity from product turnover rates, and cross-validates against spatial demand.**

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         KIRA SYSTEM                              │
│                                                                  │
│  ┌────────────────┐              ┌────────────────┐              │
│  │  SMARTPHONE    │              │                │              │
│  │  • 3-5 images  ├──────────┐   │                │              │
│  │  • GPS coords  │          │   │                │              │
│  └────────────────┘          │   │                │              │
│                              ▼   │                │              │
│  ┌──────────────────┐   ┌────────────────┐   ┌────────────┐     │
│  │   CV MODULE      │   │  GEO MODULE    │   │  FUSION    │     │
│  │  (Gemini Vision) │   │ (Maps + OSM)   │   │  ENGINE    │     │
│  │                  │   │                │   │            │     │
│  │ • Shelf Density  │   │ • Footfall     │──►│ • Weighted │     │
│  │ • SKU Diversity  │──►│ • Competition  │   │   Scoring  │     │
│  │ • Inventory Est. │   │ • Catchment    │   │ • Fraud    │     │
│  │ • Consistency    │   │ • Area Type    │   │   Detect   │     │
│  └──────────────────┘   └────────────────┘   │ • Loan     │     │
│                                               │   Sizing   │     │
│                                               │ • LLM      │     │
│                                               │   Explain  │     │
│                                               └─────┬──────┘     │
│                                                     │            │
│                                                     ▼            │
│                                        ┌──────────────────┐      │
│                                        │   OUTPUT API     │      │
│                                        │  Revenue Range   │      │
│                                        │  Risk Band       │      │
│                                        │  Loan Recommend  │      │
│                                        │  Fraud Flags     │      │
│                                        │  LLM Narrative   │      │
│                                        └────────┬─────────┘      │
│                                                 │                │
│                                                 ▼                │
│                                        ┌──────────────────┐      │
│                                        │   REACT          │      │
│                                        │   FRONTEND       │      │
│                                        │   Dashboard      │      │
│                                        └──────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Google Gemini API key
- Google Maps API key

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/kira-underwriting.git
cd kira-underwriting

# Configure environment
cp .env.example .env
cp backend/.env.example backend/.env
# Edit .env files with your API keys

# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/api/v1
# API Docs: http://localhost:8000/docs
```

### Development (Without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Module Overview

| Module | Description | Key Technology |
|--------|-------------|---------------|
| **CV Module** | Extracts visual signals from store images | Gemini Vision API |
| **Geo Module** | Extracts spatial signals from GPS coordinates | Google Maps + OSM |
| **Fusion Engine** | Combines signals into revenue estimate | Weighted scoring model |
| **Fraud Detector** | Cross-signal adversarial detection | 4-check validation |
| **LLM Layer** | Human-readable risk narratives | Gemini Pro API |
| **Loan Sizer** | Revenue → loan recommendation | EMI capacity model |
| **Frontend** | Store submission + results dashboard | React + Vite |

## Output

Every assessment produces:

- **Revenue Estimate**: Monthly revenue range (₹ low — ₹ high) with confidence score
- **Risk Band**: LOW / MEDIUM / HIGH / VERY_HIGH with risk score
- **Loan Recommendation**: Eligible amount range, tenure, EMI estimate
- **Fraud Detection**: 4-check fraud score with specific flags
- **Explanation**: LLM-generated risk narrative + structured summary

All outputs are **ranges with explicit uncertainty** — never false-precision point estimates.

## Team Roles

| Role | Responsibility |
|------|---------------|
| **Orchestration Lead** | Backend orchestration, fusion engine, fraud detection, loan sizing, LLM layer, strategic framing |
| **Analytics & CV Lead** | Computer vision module, geo module, image feature extraction, ML calibration |
| **Frontend Lead** | React frontend, store submission UI, results dashboard, responsive design |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+) |
| CV & LLM | Google Gemini Vision API + Gemini Pro |
| Geo Intelligence | Google Maps Places API + OpenStreetMap Overpass |
| Frontend | React 18 + Vite |
| Database | PostgreSQL 16 |
| Containerization | Docker + docker-compose |

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, module specifications |
| [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) | Phased development roadmap with dependencies |
| [API Reference](docs/API_REFERENCE.md) | Complete endpoint documentation |
| [Judging Criteria Map](docs/JUDGING_CRITERIA_MAP.md) | How KIRA addresses each evaluation criterion |
| [Business Context](docs/BUSINESS_CONTEXT.md) | Strategic framing and market analysis |

## Hackathon Context

**Event**: Poonawalla Fincorp — Punavalia Hackathon
**Problem Statement**: PS4C — Remote Cash Flow Underwriting for Kirana Stores using Vision & Geo Intelligence

**Core Insight**: Physical stores leak information visually and spatially. KIRA systematically extracts, quantifies, and fuses these signals into a creditworthiness assessment — no GST, no bank statements, no bureau scores required.

---

*Built for the Punavalia Hackathon 2025*

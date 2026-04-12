/**
 * KIRA — API Integration Layer
 *
 * Provides functions for communicating with the KIRA backend API.
 * Includes mock response functions for frontend development without
 * a running backend.
 *
 * Toggle between mock and live API via VITE_USE_MOCK_API env variable.
 *
 * Owner: Frontend Lead
 * Phase: 5.3
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === 'true';

// ---------------------------------------------------------------------------
// Axios Instance
// ---------------------------------------------------------------------------

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes (300000ms) — Gemini vision analysis of 4 images takes ~3.5 minutes
});

// ---------------------------------------------------------------------------
// Mock Data
// ---------------------------------------------------------------------------

/**
 * Mock assessment response matching the exact AssessmentOutput schema.
 * Used for frontend development before backend is ready.
 */
const MOCK_ASSESSMENT_RESPONSE = {
  session_id: '550e8400-e29b-41d4-a716-446655440000',
  assessment_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  timestamp: new Date().toISOString(),
  status: 'completed',

  revenue_estimate: {
    monthly_low: 150000,
    monthly_high: 280000,
    confidence: 0.72,
    methodology: 'inventory_turnover_model',
  },

  risk_assessment: {
    risk_band: 'MEDIUM',
    risk_score: 0.45,
    confidence: 0.68,
  },

  cv_signals: {
    shelf_density: 0.82,
    sku_diversity_score: 0.71,
    estimated_sku_count: 145,
    inventory_value_range: { low: 300000, high: 500000 },
    store_size_category: 'medium',
    brand_tier_mix: 'mass_dominant',
    consistency_score: 0.91,
  },

  geo_signals: {
    area_type: 'semi_urban',
    footfall_score: 0.74,
    competition_count: 8,
    competition_score: 0.55,
    catchment_population: 15000,
    demand_index: 0.68,
  },

  loan_recommendation: {
    eligible: true,
    loan_range: { min: 100000, max: 250000 },
    suggested_tenure_months: 18,
    estimated_emi: 6500,
    emi_to_income_ratio: 0.15,
  },

  fraud_detection: {
    fraud_score: 0.12,
    is_flagged: false,
    flags: [],
    checks_performed: [
      'image_consistency',
      'gps_location_validity',
      'signal_cross_validation',
      'statistical_outlier_detection',
    ],
  },

  explanation: {
    risk_narrative:
      'This medium-sized kirana store in a semi-urban location shows strong inventory management with 82% shelf occupancy across 12 product categories. The location benefits from proximity to a school and bus stop, though competition density is moderate with 8 stores within 500m. Estimated monthly revenue of ₹1.5-2.8L supports a loan of ₹1-2.5L with comfortable EMI servicing capacity.',
    summary: {
      strengths: [
        'Well-stocked shelves with 82% occupancy',
        'High footfall location near transit and school',
        'Diverse product mix across 12 categories',
      ],
      concerns: [
        'Moderate competition with 8 nearby stores',
        'Semi-urban location limits premium pricing',
      ],
      recommendation: 'Approve with standard terms',
    },
  },
};

// ---------------------------------------------------------------------------
// Public API Functions
// ---------------------------------------------------------------------------

/**
 * Submit a kirana store assessment.
 *
 * @param {FormData} formData - FormData containing:
 *   - images (File[]): 3-5 store images
 *   - image_types (string[]): Type for each image
 *   - gps_latitude (number): Store latitude
 *   - gps_longitude (number): Store longitude
 *   - gps_accuracy (number): GPS accuracy in meters
 *   - store_name (string, optional): Store name
 * @returns {Promise<object>} AssessmentOutput response
 */
export async function submitAssessment(formData) {
  if (USE_MOCK) {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 3000));
    return {
      data: {
        ...MOCK_ASSESSMENT_RESPONSE,
        session_id: crypto.randomUUID(),
        assessment_id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  return apiClient.post('/assess', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * Retrieve a previously completed assessment by session ID.
 *
 * @param {string} sessionId - UUID session ID from original assessment
 * @returns {Promise<object>} AssessmentOutput response
 */
export async function getAssessmentStatus(sessionId) {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return {
      data: {
        ...MOCK_ASSESSMENT_RESPONSE,
        session_id: sessionId,
      },
    };
  }

  return apiClient.get(`/assess/${sessionId}`);
}

/**
 * Check API health status.
 *
 * @returns {Promise<object>} Health check response
 */
export async function checkHealth() {
  if (USE_MOCK) {
    return {
      data: {
        status: 'healthy',
        version: '1.0.0',
        services: {
          database: 'mock',
          gemini_api: 'mock',
          maps_api: 'mock',
        },
      },
    };
  }

  return apiClient.get('/health');
}

export default {
  submitAssessment,
  getAssessmentStatus,
  checkHealth,
};

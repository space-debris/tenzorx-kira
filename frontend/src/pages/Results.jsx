/**
 * KIRA — Results Page
 *
 * Full assessment results display. Assembles ResultsDashboard,
 * RiskScoreCard, LoanOfferCard, FraudFlagBanner, and explanation sections.
 *
 * Owner: Frontend Lead
 * Phase: 5.8
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getAssessmentStatus } from '../api/kiraApi';
import ResultsDashboard from '../components/ResultsDashboard';
import RiskScoreCard from '../components/RiskScoreCard';
import LoanOfferCard from '../components/LoanOfferCard';
import FraudFlagBanner from '../components/FraudFlagBanner';

export default function Results() {
  const { sessionId } = useParams();
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // TODO: Fetch assessment data on mount using getAssessmentStatus(sessionId)
  // TODO: Handle loading, error, and success states
  // TODO: Compose all result components with assessment data

  return (
    <div>
      <h1>Assessment Results</h1>
      {/* TODO: Loading spinner */}
      {/* TODO: Error state */}
      {/* TODO: FraudFlagBanner (conditional — only if is_flagged) */}
      {/* TODO: RiskScoreCard */}
      {/* TODO: ResultsDashboard (CV + Geo signals breakdown) */}
      {/* TODO: LoanOfferCard */}
      {/* TODO: Risk narrative and summary display */}
    </div>
  );
}

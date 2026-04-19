/**
 * KIRA — Results Page
 *
 * Full assessment results display. Assembles ResultsDashboard,
 * RiskScoreCard, LoanOfferCard, FraudFlagBanner, and explanation sections.
 *
 * Data flow:
 *   1. Primary: receives full assessment data via React Router location state
 *      (passed from Assessment.jsx after submit)
 *   2. Fallback: fetches from GET /api/v1/assess/{sessionId} on page refresh
 *   3. Last resort: checks sessionStorage for cached assessment data
 *
 * Owner: Frontend Lead
 * Phase: 5.8 (updated in Phase 6)
 */

import { useEffect, useState, useRef } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useReactToPrint } from 'react-to-print';
import { getAssessmentStatus } from '../api/kiraApi';
import ResultsDashboard from '../components/ResultsDashboard';
import RiskScoreCard from '../components/RiskScoreCard';
import LoanOfferCard from '../components/LoanOfferCard';
import FraudFlagBanner from '../components/FraudFlagBanner';
import PeerBenchmarkCard from '../components/PeerBenchmarkCard';
import SeasonalityStressCard from '../components/SeasonalityStressCard';
import { Store, ChevronLeft, Loader2, AlertCircle, FileText, CheckCircle2, AlertTriangle, Download } from 'lucide-react';

export default function Results() {
  const { sessionId } = useParams();
  const location = useLocation();
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const contentRef = useRef(null);

  const handleDownloadPdf = useReactToPrint({
    contentRef: contentRef,
    documentTitle: assessment ? `KIRA_Report_${assessment.assessment_id?.split('-')[0]}` : 'KIRA_Report',
    onBeforePrint: () => {
      setIsExporting(true);
      return Promise.resolve();
    },
    onAfterPrint: () => {
      setIsExporting(false);
    },
  });

  useEffect(() => {
    let active = true;

    async function loadAssessment() {
      try {
        setLoading(true);

        // Strategy 1: Check React Router location state (passed from Assessment.jsx)
        if (location.state?.assessment) {
          const data = location.state.assessment;
          if (active) {
            setAssessment(data);
            // Cache to sessionStorage for page refresh resilience
            try {
              sessionStorage.setItem(`kira_assessment_${sessionId}`, JSON.stringify(data));
            } catch (e) {
              console.warn('Failed to cache assessment to sessionStorage:', e);
            }
            setError(null);
          }
          return;
        }

        // Strategy 2: Check sessionStorage (survives page refresh, not tab close)
        try {
          const cached = sessionStorage.getItem(`kira_assessment_${sessionId}`);
          if (cached) {
            const data = JSON.parse(cached);
            if (active) {
              setAssessment(data);
              setError(null);
            }
            return;
          }
        } catch (e) {
          console.warn('Failed to read cached assessment:', e);
        }

        // Strategy 3: Fetch from backend API (works if backend hasn't restarted)
        const response = await getAssessmentStatus(sessionId);
        if (active) {
          setAssessment(response.data);
          // Cache for future refreshes
          try {
            sessionStorage.setItem(`kira_assessment_${sessionId}`, JSON.stringify(response.data));
          } catch (e) {
            console.warn('Failed to cache assessment to sessionStorage:', e);
          }
          setError(null);
        }
      } catch (err) {
        if (active) {
          console.error("Failed to load results:", err);
          if (err?.response?.status === 404) {
            setError("This assessment could not be found. It may have expired or the session ID may be incorrect.");
          } else if (err?.response?.status === 422) {
            setError("The assessment ID format is invalid. Please start from a valid KIRA results link.");
          } else {
            setError("Failed to load assessment results. Please retry or run a new assessment.");
          }
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    if (sessionId) {
      loadAssessment();
    }

    return () => { active = false; };
  }, [sessionId, location.state]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center mt-20">
        <div className="bg-indigo-100 p-4 rounded-full mb-6 relative">
          <div className="absolute inset-0 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <Store className="w-8 h-8 text-indigo-700" />
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Analyzing Store Data...</h2>
        <p className="text-slate-500 max-w-md">Our Fusion Engine is running Computer Vision models to estimate inventory density and calculating spatial footfall maps.</p>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center mt-20">
        <div className="bg-red-100 p-4 rounded-full mb-6">
          <AlertCircle className="w-8 h-8 text-red-600" />
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Assessment Not Found</h2>
        <p className="text-slate-500 max-w-md mb-8">{error || "The session ID provided does not match any recent assessments."}</p>
        <Link to="/app/tools/assessment" className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-indigo-700 transition">
          Start New Assessment
        </Link>
      </div>
    );
  }

  // Extract explanation data from the correct path
  const narrative = assessment.explanation?.risk_narrative || '';
  const summaryData = assessment.explanation?.summary || {};
  const strengths = summaryData.strengths || [];
  const concerns = summaryData.concerns || [];
  const recommendation = summaryData.recommendation || 'Review';

  return (
    <div className="text-slate-900 pb-24 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <Link to="/app/tools/assessment" className="inline-flex items-center gap-2 text-slate-600 font-medium hover:text-indigo-700 transition py-1.5 rounded-lg">
          <ChevronLeft className="w-5 h-5" /> Back to Assessment
        </Link>
        
        <div className="flex items-center gap-4">
          <button
            onClick={handleDownloadPdf}
            disabled={isExporting}
            className="flex items-center gap-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 px-4 py-1.5 rounded-lg text-sm font-bold transition-all disabled:opacity-50"
          >
            {isExporting ? (
              <><div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div> Exporting...</>
            ) : (
              <><Download className="w-4 h-4" /> Export Document</>
            )}
          </button>
          <div className="text-sm font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-full font-mono hidden sm:block">
            ID: {assessment.assessment_id?.split('-')[0].toUpperCase()}
          </div>
        </div>
      </div>

      <div ref={contentRef} className="print-content">
        <div id="report-content" className="max-w-6xl mx-auto">
          
          <header className="mb-8 p-4">
          <h1 className="text-3xl font-extrabold text-slate-900 mb-2">KIRA Underwriting Report</h1>
          <p className="text-slate-600">Generated automatically via visual and spatial signal fusion.</p>
        </header>

        {/* AI Narrative — reads from explanation.risk_narrative */}
        {narrative && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-8 transform hover:-translate-y-1 transition duration-300">
            <div className="bg-gradient-to-r from-red-600 to-rose-600 px-6 py-4 border-b border-red-700">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <AlertCircle className="w-6 h-6" /> Artificial Intelligence Narrative
              </h2>
            </div>
            <div className="p-6">
              <div className="prose prose-slate max-w-none text-slate-700 leading-relaxed space-y-4">
                {narrative.split('\n').map((paragraph, index) => (
                  paragraph.trim() ? <p key={index}>{paragraph}</p> : null
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Fraud Checking */}
        <FraudFlagBanner 
          isFlagged={assessment.fraud_detection?.is_flagged} 
          fraudScore={assessment.fraud_detection?.fraud_score}
          flags={assessment.fraud_detection?.flags}
        />

        {/* Top Level Cards */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          <RiskScoreCard 
            riskBand={assessment.risk_assessment?.risk_band}
            riskScore={assessment.risk_assessment?.risk_score}
            confidence={assessment.risk_assessment?.confidence}
          />
          <LoanOfferCard 
            eligible={assessment.loan_recommendation?.eligible}
            loanRange={assessment.loan_recommendation?.loan_range}
            recommendedAmount={assessment.loan_recommendation?.recommended_amount}
            suggestedTenure={assessment.loan_recommendation?.suggested_tenure_months}
            estimatedEmi={assessment.loan_recommendation?.estimated_emi}
            emiToIncomeRatio={assessment.loan_recommendation?.emi_to_income_ratio}
            repaymentCadence={assessment.loan_recommendation?.repayment_cadence}
            estimatedInstallment={assessment.loan_recommendation?.estimated_installment}
            pricingRecommendation={assessment.loan_recommendation?.pricing_recommendation}
          />
        </div>

        {/* Detail Breakdown */}
        <div className="flex flex-col gap-6 mb-8">
          <div className="w-full">
            <ResultsDashboard 
              revenueEstimate={assessment.revenue_estimate}
              cvSignals={assessment.cv_signals}
              geoSignals={assessment.geo_signals}
            />
          </div>

          {/* Peer Benchmark + Seasonality */}
          <div className="grid lg:grid-cols-2 gap-6">
            <PeerBenchmarkCard peerBenchmark={assessment.peer_benchmark} />
            <SeasonalityStressCard
              seasonalityForecast={assessment.seasonality_forecast}
              stressScenarios={assessment.stress_scenarios}
            />
          </div>
          
          <div className="w-full">
            {/* AI Summary Card */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
              <h2 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-4 flex items-center gap-2 border-b pb-4">
                <FileText className="w-4 h-4 text-indigo-600"/> AI Narrative Summary
              </h2>
              
              {narrative && (
                <div className="text-base text-slate-600 leading-relaxed mb-8 bg-slate-50 p-6 rounded-xl border border-slate-100 italic">
                  "{narrative}"
                </div>
              )}

              {(strengths.length > 0 || concerns.length > 0) && (
                <div className="grid md:grid-cols-2 gap-8 mb-6">
                  <div>
                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-4 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Key Strengths
                    </h3>
                    <ul className="space-y-3">
                      {strengths.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm font-medium text-slate-700 border-l-2 border-emerald-200 pl-3">
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-4 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-500" /> Concerns / Risks
                    </h3>
                    <ul className="space-y-3">
                      {concerns.map((c, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm font-medium text-slate-700 border-l-2 border-amber-200 pl-3">
                          {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
                
              <div className="pt-6 border-t border-slate-200 mt-4">
                <div className="text-xs font-bold uppercase text-slate-500 mb-2">Final Bot Recommendation</div>
                <div className="font-bold text-indigo-700 bg-indigo-50 p-4 rounded-xl text-lg text-center border border-indigo-100">
                  {recommendation}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}

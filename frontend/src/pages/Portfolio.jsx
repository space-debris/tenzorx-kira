import { useCallback, useEffect, useState } from 'react';
import { Loader2, PieChart } from 'lucide-react';
import PortfolioKpiStrip from '../components/PortfolioKpiStrip';
import LoanTable from '../components/LoanTable';
import RiskHeatmap from '../components/RiskHeatmap';
import CohortChart from '../components/CohortChart';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Portfolio({ orgId, onSelectLoan }) {
  const [portfolio, setPortfolio] = useState(null);
  const [cohorts, setCohorts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const [portRes, cohortRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/platform/orgs/${orgId}/portfolio`),
        fetch(`${API_BASE}/api/v1/platform/orgs/${orgId}/portfolio/cohorts`),
      ]);

      if (!portRes.ok) throw new Error(`Portfolio load failed (${portRes.status})`);
      if (!cohortRes.ok) throw new Error(`Cohort load failed (${cohortRes.status})`);

      setPortfolio(await portRes.json());
      setCohorts(await cohortRes.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-center text-red-700">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <PieChart className="w-5 h-5 text-indigo-600" />
        <h1 className="text-lg font-black text-slate-900">Portfolio Command Center</h1>
      </div>

      {/* KPI Strip */}
      {portfolio?.kpis && <PortfolioKpiStrip kpis={portfolio.kpis} />}

      {/* Risk Heatmap */}
      {portfolio && (
        <RiskHeatmap
          riskDistribution={portfolio.risk_distribution}
          exposureByRisk={portfolio.exposure_by_risk}
          geographicConcentration={portfolio.geographic_concentration}
        />
      )}

      {/* Cohort Analysis */}
      {cohorts && (
        <CohortChart cohortData={cohorts} benchmarks={cohorts.benchmarks} />
      )}

      {/* Loan Table */}
      {portfolio?.top_exposures && (
        <LoanTable
          loans={portfolio.top_exposures}
          onSelectLoan={onSelectLoan}
        />
      )}
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { BarChart3, Loader2, AlertTriangle, MapPinned, ShieldAlert, Wallet } from 'lucide-react';
import { getOrganizationDashboard, listOrganizationCases, listOrganizationKiranas } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';
import { formatCurrency } from '../utils/caseUtils';

export default function Portfolio() {
  const { org } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [cases, setCases] = useState([]);
  const [kiranas, setKiranas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const [dashboardRes, casesRes, kiranasRes] = await Promise.all([
          getOrganizationDashboard(org.id),
          listOrganizationCases(org.id),
          listOrganizationKiranas(org.id),
        ]);
        setDashboard(dashboardRes.data);
        setCases(casesRes.data || []);
        setKiranas(kiranasRes.data || []);
      } catch (err) {
        console.error('Failed to load portfolio view:', err);
        setError('Failed to load portfolio metrics.');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  const riskCounts = useMemo(() => {
    const counts = { LOW: 0, MEDIUM: 0, HIGH: 0, VERY_HIGH: 0 };
    cases.forEach((caseItem) => {
      if (caseItem.latest_risk_band) counts[caseItem.latest_risk_band] += 1;
    });
    return counts;
  }, [cases]);

  const districtBreakdown = useMemo(() => {
    const counts = {};
    kiranas.forEach((kirana) => {
      const key = kirana.location?.district || 'Unknown';
      counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [kiranas]);

  const totalExposure = useMemo(
    () => cases.reduce((sum, caseItem) => sum + (caseItem.latest_loan_range?.high || 0), 0),
    [cases],
  );

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error}</p></div>;
  }

  const cards = [
    { label: 'Kiranas Onboarded', value: dashboard?.summary?.total_kiranas ?? 0, icon: MapPinned },
    { label: 'Cases in System', value: dashboard?.summary?.total_cases ?? 0, icon: BarChart3 },
    { label: 'Open Alerts', value: dashboard?.summary?.open_alerts ?? 0, icon: ShieldAlert },
    { label: 'Exposure Ceiling', value: formatCurrency(totalExposure), icon: Wallet },
  ];

  return (
    <div className="animate-fade-in max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-slate-900">Portfolio</h1>
        <p className="text-slate-500 font-medium mt-1">A portfolio-wide readout using the cases, borrower records, and alerts already stored in the workspace.</p>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8 stagger-children">
        {cards.map((card) => (
          <div key={card.label} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="w-11 h-11 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center mb-4">
              <card.icon className="w-5 h-5" />
            </div>
            <div className="text-2xl font-black text-slate-900">{card.value}</div>
            <div className="text-xs uppercase font-bold tracking-wide text-slate-400 mt-2">{card.label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-5">Risk Distribution</h2>
          <div className="space-y-4">
            {Object.entries(riskCounts).map(([band, count]) => (
              <div key={band}>
                <div className="flex items-center justify-between text-sm font-semibold text-slate-700 mb-1">
                  <span>{band.replace('_', ' ')}</span>
                  <span>{count}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary-500"
                    style={{ width: `${cases.length ? (count / cases.length) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-5">Top Districts</h2>
          <div className="space-y-4">
            {districtBreakdown.map(([district, count]) => (
              <div key={district} className="flex items-center justify-between border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
                <div>
                  <div className="font-semibold text-slate-800">{district}</div>
                  <div className="text-xs text-slate-400">Borrower concentration</div>
                </div>
                <div className="text-lg font-black text-primary-700">{count}</div>
              </div>
            ))}
            {districtBreakdown.length === 0 && <div className="text-sm text-slate-400">No location data available yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

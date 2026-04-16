import { useEffect, useState } from 'react';
import { FolderKanban, Loader2, AlertTriangle } from 'lucide-react';
import { exportCaseDocuments, getCaseDocuments, listOrganizationCases } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';
import DocumentCenter from '../components/DocumentCenter';

export default function Documents() {
  const { org, user } = useAuth();
  const [bundle, setBundle] = useState(null);
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const casesRes = await listOrganizationCases(org.id);
        const nextCases = casesRes.data || [];
        setCases(nextCases);
        if (nextCases[0]?.id) {
          setSelectedCaseId(nextCases[0].id);
        }
      } catch (err) {
        console.error('Failed to load document center:', err);
        setError('Failed to load document center.');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  useEffect(() => {
    if (!selectedCaseId) return;

    async function loadBundle() {
      try {
        const res = await getCaseDocuments(selectedCaseId);
        setBundle(res.data);
      } catch (err) {
        console.error('Failed to load case documents:', err);
        setError('Failed to load case documents.');
      }
    }

    loadBundle();
  }, [selectedCaseId]);

  const handleExport = async () => {
    if (!selectedCaseId) return;
    try {
      setExporting(true);
      const res = await exportCaseDocuments(selectedCaseId, user?.id);
      setBundle(res.data);
    } catch (err) {
      console.error('Failed to export case documents:', err);
      setError('Failed to export case bundle.');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error}</p></div>;
  }

  return (
    <div className="animate-fade-in max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
          <FolderKanban className="w-6 h-6 text-primary-600" /> Documents
        </h1>
        <p className="text-slate-500 font-medium mt-1">Deterministic loan-file bundles, sanction packets, and audit-ready exports.</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm mb-6">
        <label className="text-xs uppercase tracking-wide font-bold text-slate-400">Case</label>
        <select
          value={selectedCaseId}
          onChange={(event) => setSelectedCaseId(event.target.value)}
          className="mt-2 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white"
        >
          {cases.map((caseItem) => (
            <option key={caseItem.id} value={caseItem.id}>
              {caseItem.id.slice(0, 8)} • {caseItem.status}
            </option>
          ))}
        </select>
      </div>

      {bundle && <DocumentCenter bundle={bundle} onExport={handleExport} isExporting={exporting} />}
    </div>
  );
}

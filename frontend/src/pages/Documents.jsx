import { useEffect, useMemo, useState } from 'react';
import { FolderKanban, Loader2, AlertTriangle, FileText, Sparkles } from 'lucide-react';
import { getPlatformDemoSnapshot } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';

export default function Documents() {
  const { org } = useAuth();
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await getPlatformDemoSnapshot();
        setSnapshot(res.data);
      } catch (err) {
        console.error('Failed to load document center:', err);
        setError('Failed to load document center.');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const bundles = useMemo(() => {
    const allBundles = snapshot?.document_bundles || [];
    return allBundles.filter((bundle) => !org?.id || bundle.org_id === org.id);
  }, [snapshot, org?.id]);

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
        <p className="text-slate-500 font-medium mt-1">Workspace document bundles and export placeholders. Full packet generation lands in Phase 13.</p>
      </div>

      {bundles.length > 0 ? (
        <div className="grid gap-4">
          {bundles.map((bundle) => (
            <div key={bundle.id} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-lg font-bold text-slate-900">Case {bundle.case_id?.slice?.(0, 8) || bundle.case_id}</div>
                  <div className="text-sm text-slate-500">Created {new Date(bundle.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                </div>
                <FileText className="w-6 h-6 text-primary-500" />
              </div>
              <div className="space-y-2">
                {Object.entries(bundle.documents || {}).map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between text-sm border border-slate-100 rounded-lg px-3 py-2">
                    <span className="font-medium text-slate-700">{label}</span>
                    <span className="text-slate-400">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white border border-dashed border-slate-300 rounded-2xl p-10 text-center">
          <div className="w-16 h-16 mx-auto rounded-full bg-primary-50 text-primary-600 flex items-center justify-center mb-5">
            <Sparkles className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Document center is ready for bundles</h2>
          <p className="text-sm text-slate-500 mt-2 max-w-lg mx-auto">
            Your workspace already has persistent case records. Once deterministic document generation is added, sanction notes,
            case summaries, and audit exports will appear here automatically.
          </p>
        </div>
      )}
    </div>
  );
}

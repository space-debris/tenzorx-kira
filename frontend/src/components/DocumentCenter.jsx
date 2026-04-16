import { Download, RefreshCcw } from 'lucide-react';
import AuditLogTable from './AuditLogTable';

export default function DocumentCenter({ bundle, onExport, isExporting = false }) {
  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Document Bundle</h2>
            <p className="text-sm text-slate-500 mt-1">Deterministic loan-file packet generated from stored platform data.</p>
          </div>
          <button
            type="button"
            onClick={onExport}
            disabled={isExporting}
            className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-300 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition"
          >
            {isExporting ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Export Bundle
          </button>
        </div>
        <div className="grid gap-3">
          {Object.entries(bundle?.bundle?.documents || {}).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3 text-sm">
              <span className="font-medium text-slate-700">{key.replaceAll('_', ' ')}</span>
              <span className="text-slate-400">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Audit Export Preview</h2>
        <AuditLogTable
          events={(bundle?.payload?.audit_event_export || []).map((event, index) => ({
            id: `${event.created_at}-${index}`,
            created_at: event.created_at,
            action: event.action,
            entity_type: 'case',
            description: event.description,
            actor_name: event.actor_name,
          }))}
        />
      </div>
    </div>
  );
}

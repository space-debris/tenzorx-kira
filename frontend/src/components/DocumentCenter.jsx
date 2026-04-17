import { Download, RefreshCcw } from 'lucide-react';
import AuditLogTable from './AuditLogTable';

const STATUS_STYLES = {
  generated: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  pending: 'border-amber-200 bg-amber-50 text-amber-700',
  not_required: 'border-slate-200 bg-slate-100 text-slate-600',
};

export default function DocumentCenter({ bundle, onExport, isExporting = false }) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Document bundle</h2>
            <p className="text-sm text-slate-600 mt-1">Deterministic loan-file packet generated from stored platform data.</p>
          </div>
          <button
            type="button"
            onClick={onExport}
            disabled={isExporting}
            className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-lg disabled:translate-y-0 disabled:bg-slate-300 disabled:shadow-none"
          >
            {isExporting ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Export Bundle
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(bundle?.bundle?.documents || {}).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-700">{key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
              <span className={`rounded-full border px-2.5 py-1 text-xs font-bold ${STATUS_STYLES[String(value)] || 'border-slate-200 bg-slate-100 text-slate-600'}`}>
                {String(value).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 mb-4">Audit export preview</h2>
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

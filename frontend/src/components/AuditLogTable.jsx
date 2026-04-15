import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Download,
  Filter,
  Loader2,
  ScrollText,
  Search,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const ACTION_COLORS = {
  created: 'bg-emerald-100 text-emerald-800',
  updated: 'bg-blue-100 text-blue-800',
  status_changed: 'bg-amber-100 text-amber-800',
  underwriting_overridden: 'bg-indigo-100 text-indigo-800',
  assessment_linked: 'bg-violet-100 text-violet-800',
  loan_booked: 'bg-emerald-100 text-emerald-800',
  loan_status_changed: 'bg-amber-100 text-amber-800',
  loan_closed: 'bg-slate-100 text-slate-700',
  statement_uploaded: 'bg-blue-100 text-blue-800',
  statement_parsed: 'bg-emerald-100 text-emerald-800',
  monitoring_run_started: 'bg-indigo-100 text-indigo-800',
  monitoring_run_completed: 'bg-emerald-100 text-emerald-800',
  alert_raised: 'bg-amber-100 text-amber-800',
  restructuring_suggested: 'bg-orange-100 text-orange-800',
  seeded: 'bg-slate-100 text-slate-600',
  exported: 'bg-slate-100 text-slate-600',
};

export default function AuditLogTable({ orgId, entityId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [sortDir, setSortDir] = useState('desc');
  const [expandedId, setExpandedId] = useState(null);

  const fetchEvents = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      let url = `${API_BASE}/api/v1/platform/orgs/${orgId}/audit/export?limit=500`;
      if (entityId) url += `&entity_id=${entityId}`;
      if (actionFilter) url += `&action=${actionFilter}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed to load audit log (${res.status})`);
      const data = await res.json();
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [orgId, entityId, actionFilter]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const filtered = useMemo(() => {
    let result = [...events];

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (e) =>
          e.description?.toLowerCase().includes(q) ||
          e.action?.toLowerCase().includes(q) ||
          e.actor?.toLowerCase().includes(q) ||
          e.entity_id?.toLowerCase().includes(q)
      );
    }

    if (entityFilter) {
      result = result.filter((e) => e.entity_type === entityFilter);
    }

    result.sort((a, b) => {
      const diff = new Date(a.timestamp) - new Date(b.timestamp);
      return sortDir === 'desc' ? -diff : diff;
    });

    return result;
  }, [events, search, entityFilter, sortDir]);

  const actions = [...new Set(events.map((e) => e.action))].sort();
  const entityTypes = [...new Set(events.map((e) => e.entity_type))].sort();

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${orgId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex items-center gap-2 flex-1">
            <ScrollText className="w-5 h-5 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Audit Log
            </h2>
            <span className="ml-2 px-2 py-0.5 rounded-full bg-slate-100 text-[11px] font-bold text-slate-600">
              {filtered.length}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search events..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 pr-3 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-indigo-400 w-44"
              />
            </div>
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm outline-none bg-white"
            >
              <option value="">All Actions</option>
              {actions.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
            <select
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm outline-none bg-white"
            >
              <option value="">All Entities</option>
              {entityTypes.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <button
              onClick={() => setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              {sortDir === 'desc' ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={downloadJson}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-indigo-200 bg-indigo-50 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Event List */}
      <div className="max-h-[600px] overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No audit events match the current filters.
          </div>
        ) : (
          filtered.map((event, i) => {
            const isExpanded = expandedId === event.event_id;
            return (
              <div
                key={event.event_id || i}
                className="border-b border-slate-50 hover:bg-slate-50 transition"
              >
                <div
                  className="flex items-center gap-3 px-4 py-3 cursor-pointer"
                  onClick={() =>
                    setExpandedId(isExpanded ? null : event.event_id)
                  }
                >
                  <span className="text-xs font-mono text-slate-400 w-28 shrink-0">
                    {formatDate(event.timestamp)}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase shrink-0 ${
                      ACTION_COLORS[event.action] || 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {event.action}
                  </span>
                  <span className="text-sm text-slate-700 truncate flex-1">
                    {event.description}
                  </span>
                  <span className="text-xs text-slate-500 shrink-0">
                    {event.actor}
                  </span>
                </div>

                {isExpanded && (
                  <div className="px-4 pb-3">
                    <div className="rounded-lg bg-slate-50 border border-slate-100 p-3 text-xs">
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        <div>
                          <span className="font-bold text-slate-500">Entity Type: </span>
                          <span className="text-slate-700">{event.entity_type}</span>
                        </div>
                        <div>
                          <span className="font-bold text-slate-500">Entity ID: </span>
                          <span className="text-slate-700 font-mono">
                            {event.entity_id?.slice(0, 8)}...
                          </span>
                        </div>
                      </div>
                      {event.metadata && Object.keys(event.metadata).length > 0 && (
                        <div>
                          <span className="font-bold text-slate-500">Metadata: </span>
                          <pre className="mt-1 text-slate-600 whitespace-pre-wrap font-mono text-[11px]">
                            {JSON.stringify(event.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

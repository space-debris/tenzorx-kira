import { useCallback, useState } from 'react';
import {
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  ScrollText,
  ShieldCheck,
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

const DOC_ICONS = {
  underwriting_summary: ScrollText,
  sanction_note: ShieldCheck,
  monitoring_summary: FileText,
};

export default function DocumentCenter({ caseId, orgId }) {
  const [packet, setPacket] = useState(null);
  const [complianceReport, setComplianceReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState(null);

  const generatePacket = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/platform/cases/${caseId}/file-packet`
      );
      if (!res.ok) throw new Error(`Failed to generate packet (${res.status})`);
      setPacket(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const generateReport = useCallback(async () => {
    if (!orgId) return;
    setReportLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/platform/orgs/${orgId}/compliance/report`
      );
      if (!res.ok) throw new Error(`Failed to generate report (${res.status})`);
      setComplianceReport(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setReportLoading(false);
    }
  }, [orgId]);

  const downloadJson = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-5">
        <FileText className="w-5 h-5 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
          Document Center
        </h2>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3 mb-5">
        {caseId && (
          <button
            onClick={generatePacket}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <ScrollText className="w-4 h-4" />
                Generate Case File Packet
              </>
            )}
          </button>
        )}

        {orgId && (
          <button
            onClick={generateReport}
            disabled={reportLoading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-sm font-bold transition disabled:opacity-50"
          >
            {reportLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                Compliance Report
              </>
            )}
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Generated Case File Packet */}
      {packet && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Case File: {packet.kirana_name}
            </div>
            <button
              onClick={() =>
                downloadJson(packet, `case-file-${packet.case_id}.json`)
              }
              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
            >
              <Download className="w-3 h-3" />
              Export JSON
            </button>
          </div>

          <div className="space-y-3">
            {packet.documents?.map((doc, i) => {
              const DocIcon = DOC_ICONS[doc.document_type] || FileText;
              return (
                <div
                  key={i}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <DocIcon className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm font-bold text-slate-800">
                      {doc.title}
                    </span>
                    <span className="ml-auto text-[10px] text-slate-400">
                      {formatDate(doc.generated_at)}
                    </span>
                  </div>
                  <div className="space-y-3">
                    {doc.sections?.map((section, j) => (
                      <div key={j}>
                        <div className="text-[11px] font-bold uppercase text-slate-500 mb-1">
                          {section.title}
                        </div>
                        <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed bg-white rounded-lg border border-slate-100 p-3">
                          {section.content}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Audit Trail in Packet */}
          {packet.audit_bundle?.events?.length > 0 && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Audit Trail ({packet.audit_bundle.total_events} events)
              </div>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {packet.audit_bundle.events.slice(0, 20).map((event, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs text-slate-600 py-1"
                  >
                    <CheckCircle2 className="w-3 h-3 text-slate-400 shrink-0" />
                    <span className="font-mono text-[10px] text-slate-400 w-32 shrink-0">
                      {event.timestamp?.slice(0, 16)}
                    </span>
                    <span className="font-semibold text-slate-700">
                      {event.action}
                    </span>
                    <span className="truncate">{event.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Compliance Report */}
      {complianceReport && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Compliance Report: {complianceReport.org_name}
            </div>
            <button
              onClick={() =>
                downloadJson(
                  complianceReport,
                  `compliance-report-${complianceReport.org_id}.json`
                )
              }
              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
            >
              <Download className="w-3 h-3" />
              Export JSON
            </button>
          </div>

          <div className="grid md:grid-cols-3 gap-3 mb-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
              <div className="text-[10px] font-bold uppercase text-slate-400">Total Cases</div>
              <div className="text-xl font-black text-slate-800">{complianceReport.total_cases}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
              <div className="text-[10px] font-bold uppercase text-slate-400">Override Rate</div>
              <div className="text-xl font-black text-slate-800">
                {complianceReport.override_rate_pct?.toFixed(1)}%
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
              <div className="text-[10px] font-bold uppercase text-slate-400">Audit Events</div>
              <div className="text-xl font-black text-slate-800">
                {complianceReport.total_audit_events}
              </div>
            </div>
          </div>

          {complianceReport.policy_exceptions?.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-3">
              <div className="text-xs font-bold uppercase text-amber-700 mb-2">
                Policy Exceptions ({complianceReport.policy_exceptions.length})
              </div>
              <div className="space-y-2">
                {complianceReport.policy_exceptions.map((ex, i) => (
                  <div key={i} className="text-xs text-amber-800">
                    <span className="font-semibold">Case {ex.case_id?.slice(0, 8)}:</span>{' '}
                    {ex.flags?.join(', ')} — {ex.reason}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

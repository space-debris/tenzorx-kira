import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  ShieldAlert,
  TrendingDown,
  XCircle,
} from 'lucide-react';

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

function formatPercent(value) {
  if (value == null) return '—';
  return `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(1)}%`;
}

const STATUS_ICONS = {
  completed: CheckCircle2,
  running: Activity,
  pending: Clock,
  failed: XCircle,
};

const STATUS_COLORS = {
  completed: 'text-emerald-600',
  running: 'text-indigo-600',
  pending: 'text-amber-600',
  failed: 'text-red-600',
};

const RISK_COLORS = {
  LOW: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  MEDIUM: 'bg-amber-100 text-amber-800 border-amber-200',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
  VERY_HIGH: 'bg-red-100 text-red-800 border-red-200',
};

const SEVERITY_STYLES = {
  critical: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
};

export default function RiskTimeline({ monitoringRuns = [], alerts = [] }) {
  // Merge and sort events chronologically (most recent first)
  const timelineItems = [];

  for (const run of monitoringRuns) {
    timelineItems.push({
      type: 'monitoring_run',
      date: run.completed_at || run.created_at,
      data: run,
    });
  }

  for (const alert of alerts) {
    timelineItems.push({
      type: 'alert',
      date: alert.created_at,
      data: alert,
    });
  }

  timelineItems.sort((a, b) => new Date(b.date) - new Date(a.date));

  if (timelineItems.length === 0) {
    return (
      <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-5 h-5 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
            Risk Timeline
          </h2>
        </div>
        <p className="text-sm text-slate-500">
          No monitoring events yet. Upload a statement and run a monitoring cycle to populate the timeline.
        </p>
      </section>
    );
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-5">
        <Activity className="w-5 h-5 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
          Risk Timeline
        </h2>
        <span className="ml-auto px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-bold text-slate-600">
          {timelineItems.length} events
        </span>
      </div>

      <div className="relative">
        {/* Vertical timeline line */}
        <div className="absolute left-5 top-0 bottom-0 w-px bg-slate-200" />

        <div className="space-y-4">
          {timelineItems.map((item, index) => (
            <div key={`${item.type}-${index}`} className="relative pl-12">
              {item.type === 'monitoring_run' ? (
                <MonitoringRunCard run={item.data} />
              ) : (
                <AlertCard alert={item.data} />
              )}
              {/* Timeline dot */}
              <div
                className={`absolute left-3.5 top-4 w-3 h-3 rounded-full border-2 border-white shadow-sm ${
                  item.type === 'alert' ? 'bg-amber-400' : 'bg-indigo-400'
                }`}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function MonitoringRunCard({ run }) {
  const StatusIcon = STATUS_ICONS[run.status] || Clock;
  const statusColor = STATUS_COLORS[run.status] || 'text-slate-500';
  const inflowChange = run.inflow_velocity_change_pct;
  const isNegative = inflowChange != null && inflowChange < 0;
  const InflowIcon = isNegative ? ArrowDownRight : ArrowUpRight;

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon className={`w-4 h-4 ${statusColor}`} />
          <span className="text-sm font-bold text-slate-800">
            Monitoring Run
          </span>
        </div>
        <span className="text-xs text-slate-500">{formatDate(run.completed_at || run.created_at)}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        {/* Risk Band */}
        {run.new_risk_band && (
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-400 mb-1">Risk</div>
            <span
              className={`inline-block px-2 py-0.5 rounded-full border text-[11px] font-bold ${
                RISK_COLORS[run.new_risk_band] || RISK_COLORS.MEDIUM
              }`}
            >
              {run.new_risk_band}
            </span>
          </div>
        )}

        {/* Risk Score */}
        {run.new_risk_score != null && (
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-400 mb-1">Score</div>
            <span className="text-sm font-black text-slate-800">
              {(run.new_risk_score * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* Inflow Change */}
        {inflowChange != null && (
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-400 mb-1">Inflow</div>
            <span
              className={`inline-flex items-center gap-1 text-sm font-bold ${
                isNegative ? 'text-red-600' : 'text-emerald-600'
              }`}
            >
              <InflowIcon className="w-3 h-3" />
              {formatPercent(inflowChange)}
            </span>
          </div>
        )}

        {/* Alerts */}
        {run.alerts_raised?.length > 0 && (
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-400 mb-1">Alerts</div>
            <span className="text-sm font-bold text-amber-600">
              {run.alerts_raised.length}
            </span>
          </div>
        )}
      </div>

      {/* Utilization */}
      {run.utilization && (
        <div className="mb-3">
          <div className="text-[10px] font-bold uppercase text-slate-400 mb-2">Utilization</div>
          <div className="flex h-3 rounded-full overflow-hidden bg-slate-200">
            <div
              className="bg-indigo-500"
              style={{ width: `${run.utilization.supplier_inventory_pct || 0}%` }}
              title={`Supplier: ${run.utilization.supplier_inventory_pct}%`}
            />
            <div
              className="bg-blue-400"
              style={{ width: `${run.utilization.transfer_wallet_pct || 0}%` }}
              title={`Transfer: ${run.utilization.transfer_wallet_pct}%`}
            />
            <div
              className="bg-amber-400"
              style={{ width: `${run.utilization.personal_cash_pct || 0}%` }}
              title={`Personal: ${run.utilization.personal_cash_pct}%`}
            />
            <div
              className="bg-slate-300"
              style={{ width: `${run.utilization.unknown_pct || 0}%` }}
              title={`Unknown: ${run.utilization.unknown_pct}%`}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>Supplier {run.utilization.supplier_inventory_pct?.toFixed(0)}%</span>
            <span>Transfer {run.utilization.transfer_wallet_pct?.toFixed(0)}%</span>
            <span>Personal {run.utilization.personal_cash_pct?.toFixed(0)}%</span>
            <span>Other {run.utilization.unknown_pct?.toFixed(0)}%</span>
          </div>
          {run.utilization.diversion_risk && run.utilization.diversion_risk !== 'low' && (
            <div className="mt-2 flex items-center gap-1 text-xs font-semibold text-amber-700">
              <ShieldAlert className="w-3 h-3" />
              Diversion risk: {run.utilization.diversion_risk}
            </div>
          )}
        </div>
      )}

      {/* Restructuring Suggestion */}
      {run.restructuring_suggestion && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 mt-2">
          <div className="flex items-center gap-1 text-xs font-bold text-amber-800 mb-1">
            <TrendingDown className="w-3 h-3" />
            Restructuring Suggested
          </div>
          <p className="text-xs text-amber-700">{run.restructuring_suggestion.rationale}</p>
          {run.restructuring_suggestion.suggested_tenure_extension_months && (
            <span className="mt-2 inline-block px-2 py-0.5 rounded-full bg-white border border-amber-200 text-[10px] font-bold text-amber-700">
              +{run.restructuring_suggestion.suggested_tenure_extension_months}m extension
            </span>
          )}
          {run.restructuring_suggestion.suggested_moratorium_months && (
            <span className="mt-2 ml-1 inline-block px-2 py-0.5 rounded-full bg-white border border-amber-200 text-[10px] font-bold text-amber-700">
              {run.restructuring_suggestion.suggested_moratorium_months}m moratorium
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function AlertCard({ alert }) {
  const style = SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.info;

  return (
    <div className={`rounded-xl border p-4 ${style}`}>
      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm font-bold">{alert.title}</span>
        </div>
        <span className="text-xs opacity-70">{formatDate(alert.created_at)}</span>
      </div>
      {alert.description !== alert.title && (
        <p className="text-xs mt-1 opacity-80">{alert.description}</p>
      )}
      <div className="flex items-center gap-2 mt-2">
        <span className="px-2 py-0.5 rounded-full bg-white/60 border text-[10px] font-bold uppercase">
          {alert.severity}
        </span>
        <span className="px-2 py-0.5 rounded-full bg-white/60 border text-[10px] font-bold uppercase">
          {alert.status}
        </span>
      </div>
    </div>
  );
}

/**
 * KIRA — Case Timeline Component
 *
 * Vertical timeline displaying audit events for a case.
 * Color-coded by action type with icons.
 *
 * Owner: Frontend Lead
 * Phase: 9 (component)
 *
 * Props:
 *   events (array) — Audit event objects with { id, action, description, actor_name, created_at, entity_type }
 */

import {
  PlusCircle, ArrowRightLeft, Link2, UserCheck, Sparkles,
  Download, Clock, Activity
} from 'lucide-react';

const ACTION_CONFIG = {
  created: { icon: PlusCircle, color: 'text-blue-500', bg: 'bg-blue-100', border: 'border-blue-200' },
  updated: { icon: ArrowRightLeft, color: 'text-purple-500', bg: 'bg-purple-100', border: 'border-purple-200' },
  status_changed: { icon: Activity, color: 'text-indigo-500', bg: 'bg-indigo-100', border: 'border-indigo-200' },
  assessment_linked: { icon: Link2, color: 'text-emerald-500', bg: 'bg-emerald-100', border: 'border-emerald-200' },
  assigned: { icon: UserCheck, color: 'text-amber-500', bg: 'bg-amber-100', border: 'border-amber-200' },
  seeded: { icon: Sparkles, color: 'text-pink-500', bg: 'bg-pink-100', border: 'border-pink-200' },
  exported: { icon: Download, color: 'text-teal-500', bg: 'bg-teal-100', border: 'border-teal-200' },
};

function parseUTCDate(iso) {
  if (!iso) return null;
  let str = iso;
  // If naive datetime from backend (no Z, no offset), assume UTC
  if (str.includes('T') && !str.endsWith('Z') && !str.match(/[+-]\d{2}:\d{2}$/)) {
    str += 'Z';
  }
  return new Date(str);
}

function formatDateTime(iso) {
  if (!iso) return '';
  const d = parseUTCDate(iso);
  return d.toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatRelativeTime(iso) {
  if (!iso) return '';
  const now = new Date();
  const then = parseUTCDate(iso);
  const diff = Math.floor((now - then) / 1000);

  if (diff < 0) return 'Just now'; // Safety for slight clock skew
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return formatDateTime(iso);
}

export default function CaseTimeline({ events = [] }) {
  if (events.length === 0) {
    return (
      <div className="text-center py-10 text-slate-400">
        <Clock className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-sm font-medium">No activity recorded yet</p>
      </div>
    );
  }

  // Sort events newest first
  const sorted = [...events].sort((a, b) =>
    parseUTCDate(b.created_at) - parseUTCDate(a.created_at)
  );

  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-slate-200 rounded" />

      <div className="space-y-5">
        {sorted.map((event, idx) => {
          const config = ACTION_CONFIG[event.action] || ACTION_CONFIG.created;
          const Icon = config.icon;

          return (
            <div key={event.id || idx} className="relative flex gap-4 group">
              {/* Dot / Icon */}
              <div className={`absolute -left-6 w-6 h-6 rounded-full ${config.bg} ${config.border} border flex items-center justify-center shrink-0 z-10`}>
                <Icon className={`w-3 h-3 ${config.color}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pb-1">
                <p className="text-sm text-slate-700 font-medium leading-snug">
                  {event.description}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  {event.actor_name && (
                    <span className="text-xs font-semibold text-slate-500">{event.actor_name}</span>
                  )}
                  <span className="text-xs text-slate-400" title={formatDateTime(event.created_at)}>
                    {formatRelativeTime(event.created_at)}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

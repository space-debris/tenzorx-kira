/**
 * KIRA — Fraud Flag Banner Component
 *
 * Conditional warning banner displayed only when fraud detection
 * flags the assessment (is_flagged: true). Lists specific flags.
 *
 * Owner: Frontend Lead
 * Phase: 5.7
 *
 * Props:
 *   isFlagged (boolean) — Whether to show the banner
 *   fraudScore (number) — 0-1 fraud score
 *   flags (array) — List of specific fraud flag strings
 */

import { AlertTriangle, ShieldAlert } from 'lucide-react';

export default function FraudFlagBanner({ isFlagged, fraudScore, flags = [] }) {
  if (!isFlagged) return null;

  return (
    <div className="bg-amber-50 border border-amber-300 rounded-xl p-6 mb-8 shadow-sm">
      <div className="flex items-start gap-4">
        <div className="bg-amber-100 p-3 rounded-full text-amber-600 shrink-0">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-bold text-amber-900">Assessment Flagged for Review</h3>
            <div className="flex items-center gap-1.5 bg-amber-200 text-amber-900 px-3 py-1 rounded-full text-sm font-bold">
              <ShieldAlert className="w-4 h-4" />
              Risk Score: {Math.round(fraudScore * 100)}/100
            </div>
          </div>
          <p className="text-amber-800 font-medium mb-3">
            Our fusion engine has detected anomalies in the submitted data. Manual underwriting review is recommended before finalizing this loan offer.
          </p>
          {flags.length > 0 && (
            <ul className="space-y-1">
              {flags.map((flag, idx) => (
                <li key={idx} className="flex items-center gap-2 text-sm text-amber-700 font-medium before:content-['—']">
                  {flag.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

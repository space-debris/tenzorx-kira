/**
 * KIRA — Risk Score Card Component
 *
 * Circular/gauge risk score display with risk band label,
 * confidence indicator, and color-coded presentation.
 *
 * Owner: Frontend Lead
 * Phase: 5.5
 *
 * Props:
 *   riskBand (string) — "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH"
 *   riskScore (number) — 0-1 continuous risk score
 *   confidence (number) — 0-1 assessment confidence
 */

import { Activity, ShieldCheck, ShieldAlert, AlertOctagon } from 'lucide-react';

export default function RiskScoreCard({ riskBand, riskScore, confidence }) {
  
  // Style and Icon mapping based on risk band
  const getBandStyles = (band) => {
    switch (band?.toUpperCase()) {
      case 'LOW':
        return { 
          color: 'text-emerald-600', 
          bg: 'bg-emerald-50', 
          border: 'border-emerald-200',
          gradient: 'from-emerald-500 to-emerald-400',
          Icon: ShieldCheck,
          label: 'Low Risk'
        };
      case 'MEDIUM':
        return { 
          color: 'text-blue-600', 
          bg: 'bg-blue-50', 
          border: 'border-blue-200',
          gradient: 'from-blue-500 to-blue-400',
          Icon: Activity,
          label: 'Medium Risk'
        };
      case 'HIGH':
        return { 
          color: 'text-amber-600', 
          bg: 'bg-amber-50', 
          border: 'border-amber-200',
          gradient: 'from-amber-500 to-amber-400',
          Icon: ShieldAlert,
          label: 'High Risk'
        };
      case 'VERY_HIGH':
      case 'VERY_HIGH_RISK':
        return { 
          color: 'text-red-600', 
          bg: 'bg-red-50', 
          border: 'border-red-200',
          gradient: 'from-red-600 to-red-500',
          Icon: AlertOctagon,
          label: 'Very High Risk'
        };
      default:
        return { 
          color: 'text-slate-600', 
          bg: 'bg-slate-50', 
          border: 'border-slate-200',
          gradient: 'from-slate-400 to-slate-300',
          Icon: Activity,
          label: 'Unknown'
        };
    }
  };

  const styles = getBandStyles(riskBand);
  const Icon = styles.Icon;
  const scorePercent = Math.round(riskScore * 100);
  const confPercent = Math.round((confidence || 0) * 100);

  return (
    <div className={`border rounded-2xl p-6 shadow-sm flex flex-col justify-between ${styles.bg} ${styles.border}`}>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-1">Underwriting Profile</h2>
          <div className={`text-2xl font-black flex items-center gap-2 ${styles.color}`}>
            <Icon className="w-6 h-6" />
            {styles.label}
          </div>
        </div>
        
        {/* Simple Ring visualization using Tailwind/CSS */}
        <div className="relative w-20 h-20 flex items-center justify-center rounded-full bg-white shadow-sm border border-slate-100">
          <div className="absolute inset-0 rounded-full" 
               style={{
                 background: `conic-gradient(var(--tw-gradient-from) ${scorePercent}%, transparent ${scorePercent}%)`,
                 opacity: 0.2
               }}>
          </div>
          <div className="relative z-10 flex flex-col items-center">
            <span className={`text-xl font-black leading-none ${styles.color}`}>{scorePercent}</span>
            <span className="text-[10px] font-bold text-slate-400">SCORE</span>
          </div>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-sm font-semibold text-slate-600 mb-1.5">
          <span>AI Confidence</span>
          <span>{confPercent}%</span>
        </div>
        <div className="w-full bg-black/5 rounded-full h-2 overflow-hidden">
          <div className={`h-full bg-gradient-to-r ${styles.gradient} rounded-full`} style={{ width: `${confPercent}%` }}></div>
        </div>
      </div>
    </div>
  );
}

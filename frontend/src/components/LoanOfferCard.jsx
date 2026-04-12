/**
 * KIRA — Loan Offer Card Component
 *
 * Displays loan recommendation: range, tenure, EMI, eligibility.
 *
 * Owner: Frontend Lead
 * Phase: 5.6
 *
 * Props:
 *   eligible (boolean) — Whether the store qualifies
 *   loanRange (object) — { min, max } in INR
 *   suggestedTenure (number) — Months
 *   estimatedEmi (number) — Monthly EMI in INR
 *   emiToIncomeRatio (number) — 0-1
 */

import { CheckCircle2, XCircle, CreditCard, Calendar, Wallet } from 'lucide-react';

export default function LoanOfferCard({ eligible, loanRange, suggestedTenure, estimatedEmi, emiToIncomeRatio }) {
  
  const formatCurrency = (num) => {
    if (!num) return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(num);
  };

  if (!eligible) {
    return (
      <div className="bg-white border rounded-2xl p-6 shadow-sm">
        <h2 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-4 border-b pb-4">Loan Decision</h2>
        <div className="text-center py-6">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-slate-800 mb-2">Not Eligible</h3>
          <p className="text-slate-600 max-w-sm mx-auto">
            Based on the current visual and spatial signals, this store does not meet the minimum underwriting requirements for a Working Capital Loan.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-indigo-900 text-white rounded-2xl p-6 shadow-lg relative overflow-hidden">
      {/* Decorative background shapes */}
      <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-indigo-600 opacity-20 rounded-full blur-2xl"></div>
      <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-40 h-40 bg-purple-600 opacity-20 rounded-full blur-2xl"></div>
      
      <div className="relative z-10">
        <div className="flex items-center gap-2 mb-6 border-b border-indigo-700 pb-4">
          <CheckCircle2 className="text-emerald-400 w-6 h-6" />
          <h2 className="text-indigo-100 font-bold text-sm uppercase tracking-wider">Approved Working Capital</h2>
        </div>

        <div className="mb-8">
          <p className="text-indigo-200 text-sm font-medium mb-1">Recommended Credit Line</p>
          <div className="text-4xl font-black text-white tracking-tight">
            {formatCurrency(loanRange?.min ?? loanRange?.low)} - {formatCurrency(loanRange?.max ?? loanRange?.high)}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 bg-indigo-800/50 rounded-xl p-4">
          <div className="flex flex-col gap-1">
            <span className="text-indigo-300 text-xs font-semibold flex items-center gap-1"><Calendar className="w-3.5 h-3.5"/> Recommended Tenure</span>
            <span className="text-xl font-bold text-white">{suggestedTenure} Months</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-indigo-300 text-xs font-semibold flex items-center gap-1"><CreditCard className="w-3.5 h-3.5"/> Est. Max EMI</span>
            <span className="text-xl font-bold text-white">{formatCurrency(estimatedEmi)}</span>
          </div>
        </div>
        
        <div className="mt-4 flex items-center justify-between text-xs font-medium">
          <span className="text-indigo-300">EMI to Income Ratio</span>
          <span className={`px-2 py-1 rounded-md ${emiToIncomeRatio < 0.25 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
            {Math.round(emiToIncomeRatio * 100)}% (Healthy)
          </span>
        </div>
      </div>
    </div>
  );
}

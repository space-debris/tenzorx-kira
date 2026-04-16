import { Link } from 'react-router-dom';
import { formatCurrency } from '../utils/caseUtils';

export default function LoanTable({ loans = [] }) {
  if (!loans.length) {
    return <div className="text-sm text-slate-400">No loans available for current filters.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 text-left">
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Borrower</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Location</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Status</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Risk</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Exposure</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Stress</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {loans.map((loan) => (
            <tr key={loan.case_id} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <div className="font-semibold text-slate-900 text-sm">{loan.store_name}</div>
                <div className="text-xs text-slate-400">{loan.borrower_name}</div>
              </td>
              <td className="px-4 py-3 text-sm text-slate-600">
                {[loan.district, loan.state, loan.pin_code].filter(Boolean).join(' • ')}
              </td>
              <td className="px-4 py-3 text-sm font-medium text-slate-700 capitalize">{loan.status.replace('_', ' ')}</td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-700">{loan.risk_band || '-'}</td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-700">{formatCurrency(loan.exposure)}</td>
              <td className="px-4 py-3 text-sm text-slate-600">{Math.round((loan.stress_score || 0) * 100)}</td>
              <td className="px-4 py-3 text-right">
                <Link to={loan.loan_account_id ? `/app/loan-accounts/${loan.case_id}` : `/app/cases/${loan.case_id}`} className="text-primary-600 hover:text-primary-700 text-sm font-semibold">
                  Open
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

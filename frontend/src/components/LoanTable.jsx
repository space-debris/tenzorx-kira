import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, CreditCard, Search } from 'lucide-react';

function formatCurrency(value) {
  if (value == null) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

const STATUS_COLORS = {
  active: 'bg-emerald-100 text-emerald-800',
  current: 'bg-emerald-100 text-emerald-800',
  overdue: 'bg-amber-100 text-amber-800',
  npa: 'bg-red-100 text-red-800',
  restructured: 'bg-orange-100 text-orange-800',
  closed: 'bg-slate-100 text-slate-600',
  written_off: 'bg-red-100 text-red-800',
};

const RISK_COLORS = {
  LOW: 'bg-emerald-100 text-emerald-800',
  MEDIUM: 'bg-amber-100 text-amber-800',
  HIGH: 'bg-orange-100 text-orange-800',
  VERY_HIGH: 'bg-red-100 text-red-800',
};

export default function LoanTable({ loans = [], onSelectLoan }) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('outstanding');
  const [sortDir, setSortDir] = useState('desc');
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');

  const filtered = useMemo(() => {
    let result = [...loans];

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (l) =>
          (l.kirana_name || '').toLowerCase().includes(q) ||
          (l.loan_id || '').toLowerCase().includes(q)
      );
    }

    if (statusFilter) {
      result = result.filter((l) => l.status === statusFilter);
    }

    if (riskFilter) {
      result = result.filter((l) => l.risk_band === riskFilter);
    }

    result.sort((a, b) => {
      let aVal = a[sortKey] ?? 0;
      let bVal = b[sortKey] ?? 0;
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [loans, search, sortKey, sortDir, statusFilter, riskFilter]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return null;
    return sortDir === 'asc' ? (
      <ChevronUp className="w-3 h-3 inline ml-0.5" />
    ) : (
      <ChevronDown className="w-3 h-3 inline ml-0.5" />
    );
  };

  const statuses = [...new Set(loans.map((l) => l.status).filter(Boolean))];
  const risks = [...new Set(loans.map((l) => l.risk_band).filter(Boolean))];

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header & Filters */}
      <div className="p-4 border-b border-slate-100">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex items-center gap-2 flex-1">
            <CreditCard className="w-5 h-5 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Loan Book
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
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 pr-3 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-indigo-400 w-44"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm outline-none bg-white"
            >
              <option value="">All Status</option>
              {statuses.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm outline-none bg-white"
            >
              <option value="">All Risk</option>
              {risks.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              <th
                className="text-left px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider cursor-pointer hover:text-slate-700"
                onClick={() => handleSort('kirana_name')}
              >
                Store <SortIcon col="kirana_name" />
              </th>
              <th className="text-left px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider">
                State
              </th>
              <th
                className="text-right px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider cursor-pointer hover:text-slate-700"
                onClick={() => handleSort('principal')}
              >
                Principal <SortIcon col="principal" />
              </th>
              <th
                className="text-right px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider cursor-pointer hover:text-slate-700"
                onClick={() => handleSort('outstanding')}
              >
                Outstanding <SortIcon col="outstanding" />
              </th>
              <th className="text-center px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider">
                Risk
              </th>
              <th
                className="text-center px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider cursor-pointer hover:text-slate-700"
                onClick={() => handleSort('days_past_due')}
              >
                DPD <SortIcon col="days_past_due" />
              </th>
              <th className="text-center px-4 py-3 font-bold text-slate-500 uppercase text-[11px] tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  No loans match the current filters.
                </td>
              </tr>
            ) : (
              filtered.map((loan) => (
                <tr
                  key={loan.loan_id}
                  className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition"
                  onClick={() => onSelectLoan?.(loan.loan_id)}
                >
                  <td className="px-4 py-3 font-semibold text-slate-800">
                    {loan.kirana_name || '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{loan.state || '—'}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-700">
                    {formatCurrency(loan.principal)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-bold text-slate-800">
                    {formatCurrency(loan.outstanding)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        RISK_COLORS[loan.risk_band] || 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {loan.risk_band || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`font-bold ${
                        loan.days_past_due > 30
                          ? 'text-red-600'
                          : loan.days_past_due > 0
                          ? 'text-amber-600'
                          : 'text-emerald-600'
                      }`}
                    >
                      {loan.days_past_due}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        STATUS_COLORS[loan.status] || 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {loan.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

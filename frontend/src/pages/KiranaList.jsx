/**
 * KIRA — Kirana List Page
 *
 * Searchable directory of all kirana borrower profiles.
 * Fetches from GET /platform/orgs/{org_id}/kiranas.
 *
 * Owner: Frontend Lead
 * Phase: 9.3
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { listOrganizationCases, listOrganizationKiranas } from '../api/kiraApi';
import {
  Users, Search, MapPin, Store, ArrowRight,
  Loader2, AlertTriangle, Filter
} from 'lucide-react';
import { getCaseNextAction } from '../utils/caseUtils';

const CASE_STATUS_STYLES = {
  draft: 'bg-slate-100 text-slate-700 border-slate-200',
  submitted: 'bg-blue-50 text-blue-700 border-blue-200',
  under_review: 'bg-violet-50 text-violet-700 border-violet-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  disbursed: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  monitoring: 'bg-amber-50 text-amber-700 border-amber-200',
  restructured: 'bg-rose-50 text-rose-700 border-rose-200',
  closed: 'bg-slate-100 text-slate-600 border-slate-200',
};

function formatStatus(status = '') {
  return String(status).replace(/_/g, ' ');
}

export default function KiranaList() {
  const { org } = useAuth();
  const [kiranas, setKiranas] = useState([]);
  const [latestCaseMap, setLatestCaseMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterState, setFilterState] = useState('');

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const [kiranaRes, caseRes] = await Promise.all([
          listOrganizationKiranas(org.id),
          listOrganizationCases(org.id),
        ]);
        const nextKiranas = kiranaRes.data || [];
        const nextCases = caseRes.data || [];
        setKiranas(nextKiranas);

        const caseMap = {};
        nextCases.forEach((caseItem) => {
          const existing = caseMap[caseItem.kirana_id];
          if (!existing || new Date(caseItem.updated_at) > new Date(existing.updated_at)) {
            caseMap[caseItem.kirana_id] = caseItem;
          }
        });
        setLatestCaseMap(caseMap);
      } catch (err) {
        console.error('Failed to load kiranas:', err);
        setError('Failed to load kirana directory');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  const filteredKiranas = kiranas.filter((k) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch = !q
      || k.store_name?.toLowerCase().includes(q)
      || k.owner_name?.toLowerCase().includes(q)
      || k.location?.district?.toLowerCase().includes(q)
      || k.location?.pin_code?.includes(q)
      || k.location?.locality?.toLowerCase().includes(q);
    const matchesState = !filterState || k.location?.state === filterState;
    return matchesSearch && matchesState;
  });

  const uniqueStates = [...new Set(kiranas.map(k => k.location?.state).filter(Boolean))].sort();
  const kiranasWithCases = Object.keys(latestCaseMap).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <p className="text-slate-600 font-medium">{error}</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in max-w-7xl mx-auto">
      <div className="mb-8 rounded-3xl border border-slate-200 bg-linear-to-br from-white via-slate-50 to-primary-50/40 p-6 shadow-sm">
        <h1 className="text-3xl font-black tracking-tight text-slate-900 mb-1 flex items-center gap-2.5">
          <Users className="w-7 h-7 text-primary-600" /> Kirana Directory
        </h1>
        <p className="text-slate-600 font-medium">Search and monitor borrower storefronts with their latest case context.</p>

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="inline-flex items-center rounded-full border border-primary-200 bg-white px-3 py-1 text-xs font-bold text-primary-700">
            {kiranas.length} total {kiranas.length === 1 ? 'profile' : 'profiles'}
          </span>
          <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
            {kiranasWithCases} with linked cases
          </span>
          <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
            {uniqueStates.length} state{uniqueStates.length === 1 ? '' : 's'} represented
          </span>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by store name, owner, district, locality, or pin code"
              className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-xl outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm"
            />
          </div>

          {uniqueStates.length > 1 && (
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <select
                value={filterState}
                onChange={(e) => setFilterState(e.target.value)}
                className="appearance-none min-w-44 pl-9 pr-8 py-2.5 border border-slate-300 bg-white rounded-xl outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 text-sm font-medium text-slate-700"
              >
                <option value="">All States</option>
                {uniqueStates.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Showing {filteredKiranas.length} of {kiranas.length}
          </p>
          {(searchQuery || filterState) && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setFilterState('');
              }}
              className="text-xs font-bold text-primary-700 hover:text-primary-800"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Kirana Cards Grid */}
      {filteredKiranas.length > 0 ? (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4 stagger-children">
          {filteredKiranas.map((k) => (
            <Link
              key={k.id}
              to={`/app/kiranas/${k.id}`}
              className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-lg"
            >
              <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary-500 via-indigo-400 to-cyan-400" />

              {(() => {
                const latestCase = latestCaseMap[k.id];
                const statusClass = CASE_STATUS_STYLES[latestCase?.status] || 'bg-slate-100 text-slate-700 border-slate-200';

                return (
                  <>
              <div className="flex items-start justify-between mb-4 gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-11 h-11 rounded-xl bg-primary-50 ring-1 ring-primary-100 flex items-center justify-center text-primary-600">
                    <Store className="w-5 h-5 shrink-0" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="truncate font-bold text-slate-900 group-hover:text-primary-700 transition-colors">{k.store_name}</h3>
                    <p className="text-sm text-slate-500">{k.owner_name}</p>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 transition-colors mt-1" />
              </div>

              <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-2">
                <MapPin className="w-3.5 h-3.5" />
                <span>{[k.location?.locality, k.location?.district, k.location?.state].filter(Boolean).join(', ')}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                <span className="rounded-full bg-slate-100 text-slate-700 px-2.5 py-1 font-semibold">PIN: {k.location?.pin_code}</span>
                {k.metadata?.shop_size && (
                  <span className="rounded-full bg-primary-50 text-primary-700 px-2.5 py-1 font-semibold capitalize">{k.metadata.shop_size}</span>
                )}
              </div>
              {latestCase && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-bold uppercase tracking-wide text-slate-400">Latest Case</span>
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold capitalize ${statusClass}`}>
                      {formatStatus(latestCase.status)}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mt-2 line-clamp-2">{getCaseNextAction(latestCase)}</p>
                </div>
              )}
                  </>
                );
              })()}
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-20 bg-white border border-slate-200 rounded-2xl shadow-sm">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
            <Users className="w-7 h-7" />
          </div>
          <p className="text-slate-600 font-semibold mb-1">No kiranas found</p>
          <p className="text-sm text-slate-400">Try adjusting your search or state filter</p>
        </div>
      )}
    </div>
  );
}

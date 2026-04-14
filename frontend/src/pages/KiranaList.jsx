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
import { useAuth } from '../context/AuthContext';
import { listOrganizationKiranas } from '../api/kiraApi';
import {
  Users, Search, MapPin, Store, ArrowRight,
  Loader2, AlertTriangle, Filter
} from 'lucide-react';

export default function KiranaList() {
  const { org } = useAuth();
  const [kiranas, setKiranas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterState, setFilterState] = useState('');

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const res = await listOrganizationKiranas(org.id);
        setKiranas(res.data || []);
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
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-slate-900 mb-1 flex items-center gap-2">
          <Users className="w-6 h-6 text-primary-600" /> Kirana Directory
        </h1>
        <p className="text-slate-500 font-medium">{kiranas.length} borrower {kiranas.length === 1 ? 'profile' : 'profiles'} in your workspace</p>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by store name, owner, district, or pin code…"
            className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-xl outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm"
          />
        </div>
        {uniqueStates.length > 1 && (
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <select
              value={filterState}
              onChange={(e) => setFilterState(e.target.value)}
              className="appearance-none pl-9 pr-8 py-2.5 border border-slate-300 bg-white rounded-xl outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 text-sm font-medium text-slate-700"
            >
              <option value="">All States</option>
              {uniqueStates.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}
      </div>

      {/* Kirana Cards Grid */}
      {filteredKiranas.length > 0 ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 stagger-children">
          {filteredKiranas.map((k) => (
            <Link
              key={k.id}
              to={`/app/kiranas/${k.id}`}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md hover:border-primary-200 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 bg-primary-50 rounded-lg flex items-center justify-center text-primary-600">
                    <Store className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 group-hover:text-primary-700 transition-colors">{k.store_name}</h3>
                    <p className="text-sm text-slate-500">{k.owner_name}</p>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 transition-colors mt-1" />
              </div>

              <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-3">
                <MapPin className="w-3.5 h-3.5" />
                <span>{[k.location?.locality, k.location?.district, k.location?.state].filter(Boolean).join(', ')}</span>
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs">
                <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-semibold">PIN: {k.location?.pin_code}</span>
                {k.metadata?.shop_size && (
                  <span className="bg-primary-50 text-primary-600 px-2 py-0.5 rounded font-semibold capitalize">{k.metadata.shop_size}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-20 bg-white border border-slate-200 rounded-xl">
          <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500 font-medium mb-1">No kiranas found</p>
          <p className="text-sm text-slate-400">Try adjusting your search or filters</p>
        </div>
      )}
    </div>
  );
}

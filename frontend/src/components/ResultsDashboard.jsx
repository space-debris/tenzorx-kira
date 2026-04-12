/**
 * KIRA — Results Dashboard Component
 *
 * Main results display with revenue estimate, CV signals breakdown,
 * and Geo signals breakdown. Uses Recharts for visualizations.
 *
 * Owner: Frontend Lead
 * Phase: 5.4
 *
 * Props:
 *   revenueEstimate (object) — { monthly_low, monthly_high, confidence, methodology }
 *   cvSignals (object) — CV module signal outputs
 *   geoSignals (object) — Geo module signal outputs
 */

import { BarChart, Map, Camera, Box, MoveDiagonal, Tag, Store, Navigation } from 'lucide-react';

export default function ResultsDashboard({ revenueEstimate, cvSignals, geoSignals }) {
  
  const formatCurrency = (num) => {
    if (!num) return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(num);
  };

  // Helper to render a progress bar for 0-1 scores
  const SignalBar = ({ label, score, icon: Icon, desc }) => {
    const pct = Math.round((score || 0) * 100);
    // Color coding logic: >0.7 green, 0.4-0.7 yellow, <0.4 red
    let colorClass = 'bg-emerald-500';
    if (pct < 40) colorClass = 'bg-red-500';
    else if (pct < 70) colorClass = 'bg-amber-500';

    return (
      <div className="mb-5 last:mb-0">
        <div className="flex justify-between items-end mb-1.5">
          <div className="flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-slate-500" />}
            <span className="text-sm font-bold text-slate-700">{label}</span>
          </div>
          <span className="text-sm font-black text-slate-800">{pct}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
          <div className={`h-full rounded-full ${colorClass} transition-all duration-1000`} style={{ width: `${pct}%` }}></div>
        </div>
        {desc && <p className="text-xs text-slate-500 mt-1">{desc}</p>}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Revenue Estimate Block */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-2 flex items-center gap-2">
              <BarChart className="w-4 h-4 text-indigo-600"/> Monthly Revenue Estimate
            </h2>
            <p className="text-slate-500 text-sm max-w-sm">Predicted using AI assessment of {revenueEstimate?.methodology?.replace(/_/g, ' ') || 'visual and spatial factors'}.</p>
          </div>
        </div>
        
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-6 text-center">
          <div className="text-indigo-900 font-medium mb-1">Estimated Range</div>
          <div className="text-4xl md:text-5xl font-black text-indigo-700">
            {formatCurrency(revenueEstimate?.monthly_low)} <span className="text-indigo-300 font-normal">to</span> {formatCurrency(revenueEstimate?.monthly_high)}
          </div>
        </div>
      </div>

      {/* Signals Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        
        {/* Computer Vision Signals */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-6 flex items-center gap-2 border-b pb-4">
            <Camera className="w-4 h-4 text-indigo-600"/> Visual Intelligence
          </h2>
          
          <SignalBar 
            label="Shelf Density" 
            score={cvSignals?.shelf_density} 
            icon={Box}
            desc="Percentage of available shelf space currently stocked."
          />
          <SignalBar 
            label="SKU Diversity" 
            score={cvSignals?.sku_diversity_score} 
            icon={Tag}
            desc="Variety of distinct product categories identified."
          />
          <SignalBar 
            label="Visual Consistency" 
            score={cvSignals?.consistency_score} 
            icon={MoveDiagonal}
            desc="Confidence that the 3-5 images belong to the exact same store."
          />
          
          <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-500 font-medium uppercase mb-1">Store Size</div>
              <div className="font-bold text-slate-800 capitalize">{cvSignals?.store_size_category || 'Unknown'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 font-medium uppercase mb-1">Est. SKUs</div>
              <div className="font-bold text-slate-800">{cvSignals?.estimated_sku_count || 'N/A'}</div>
            </div>
          </div>
        </div>

        {/* Spatial / Geo Signals */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-slate-700 font-bold text-sm uppercase tracking-wider mb-6 flex items-center gap-2 border-b pb-4">
            <Map className="w-4 h-4 text-purple-600"/> Spatial Intelligence
          </h2>
          
          <SignalBar 
            label="Footfall Proxy" 
            score={geoSignals?.footfall_score} 
            icon={Navigation}
            desc="Proximity to transit hubs, schools, and major roads."
          />
          <SignalBar 
            label="Demand Index" 
            score={geoSignals?.demand_index} 
            icon={Store}
            desc="Ratio of catchment population relative to competition."
          />
          <SignalBar 
            label="Competition Saturation" 
            score={geoSignals?.competition_score} 
            icon={Map} // using map as generic
            desc="Density of similar stores in a 500m radius. (Lower represents less saturation/better position)"
          />

          <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-500 font-medium uppercase mb-1">Area Type</div>
              <div className="font-bold text-slate-800 capitalize">{geoSignals?.area_type || 'Unknown'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 font-medium uppercase mb-1">Catchment Pop.</div>
              <div className="font-bold text-slate-800">{geoSignals?.catchment_population?.toLocaleString() || 'N/A'}</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

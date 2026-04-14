/**
 * KIRA — Home Page (Landing)
 *
 * Landing page with product framing, value proposition,
 * "Start Assessment" CTA, and how-it-works section.
 *
 * Owner: Frontend Lead
 * Phase: 5.1
 */

import { Link } from 'react-router-dom';
import { Camera, MapPin, Activity, Store, TrendingUp, Clock } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Navbar */}
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-indigo-700 font-bold text-2xl tracking-tight">
          <Store className="w-8 h-8" />
          KIRA
        </div>
        <div className="hidden sm:flex gap-6 items-center text-sm font-medium text-slate-600">
          <a href="#how-it-works" className="hover:text-indigo-600 transition-colors">How it works</a>
          <a href="#stats" className="hover:text-indigo-600 transition-colors">Impact</a>
          <Link to="/login" className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold transition-all shadow-sm">
            Lender Portal
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="max-w-6xl mx-auto px-6 py-20 text-center">
        <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900 mb-6 tracking-tight leading-tight">
          Remote Cash Flow Underwriting <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
            For India's Kirana Stores
          </span>
        </h1>
        <p className="text-xl text-slate-600 max-w-3xl mx-auto mb-10 leading-relaxed">
          AI-powered creditworthiness assessment relying solely on visual intelligence and spatial data. 
          No GST, no bank statements, no credit history required.
        </p>
        <Link 
          to="/app/tools/assessment" 
          className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-4 rounded-xl font-bold text-lg transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-1"
        >
          <Activity className="w-5 h-5" />
          Start App Assessment
        </Link>
      </main>

      {/* How it Works Section */}
      <section id="how-it-works" className="bg-white py-20 border-y border-slate-200">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-16 text-slate-800">How KIRA Works</h2>
          <div className="grid md:grid-cols-3 gap-10">
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <Camera className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">1. Upload Images</h3>
              <p className="text-slate-600">Snap 3-5 images of the store interior, exterior, and shelves to extract visual signals representing working capital.</p>
            </div>
            
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <MapPin className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">2. Auto-Detect Location</h3>
              <p className="text-slate-600">Capture GPS coordinates to evaluate catchment population, nearby competition, and footfall potential.</p>
            </div>
            
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <Activity className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">3. Get Assessment</h3>
              <p className="text-slate-600">Our Fusion Engine calculates estimated revenue, risk profile, and recommended loan sizing instantly.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section id="stats" className="max-w-6xl mx-auto px-6 py-20">
        <div className="bg-indigo-900 rounded-3xl p-10 md:p-16 text-white text-center shadow-2xl">
          <h2 className="text-3xl font-bold mb-10">Unlocking Credit for the Invisible</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
              <div className="text-4xl font-extrabold text-indigo-300 mb-2">13M+</div>
              <div className="text-indigo-100 font-medium">Kirana Stores</div>
            </div>
            <div>
              <div className="text-4xl font-extrabold text-indigo-300 mb-2">~3 min</div>
              <div className="text-indigo-100 font-medium">Processing Time</div>
            </div>
            <div>
              <div className="text-4xl font-extrabold text-indigo-300 mb-2">Zero</div>
              <div className="text-indigo-100 font-medium">Paperwork</div>
            </div>
            <div>
              <div className="text-4xl font-extrabold text-indigo-300 mb-2">₹12L Cr</div>
              <div className="text-indigo-100 font-medium">Annual Trade</div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-8 text-center text-slate-500 font-medium">
        <p>Built for the Poonawalla Hackathon 2025</p>
      </footer>
    </div>
  );
}

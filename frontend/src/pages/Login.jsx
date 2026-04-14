/**
 * KIRA — Lender Login Page
 *
 * Mocked authentication entry for the lender workspace.
 * Pre-populated with demo user credentials.
 *
 * Supports redirect-back: reads ?redirect query param and navigates
 * the user to their intended page after successful login.
 *
 * Owner: Frontend Lead
 * Phase: 9.1
 */

import { useState } from 'react';
import { useNavigate, useLocation, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Store, LogIn, ArrowLeft, Eye, EyeOff, ShieldCheck } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const [email, setEmail] = useState('maya@democapital.in');
  const [password, setPassword] = useState('demo1234');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState(null);

  // Read ?redirect param so we can send the user back to where they came from
  const params = new URLSearchParams(location.search);
  const redirectPath = params.get('redirect') || '/app/dashboard';

  // Redirect immediately if already authenticated
  if (isAuthenticated) {
    return <Navigate to={redirectPath} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoggingIn(true);

    try {
      const result = await login(email);
      if (result.success) {
        navigate(redirectPath, { replace: true });
      } else {
        setError(result.error || 'Login failed. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-900 via-primary-800 to-primary-950 flex-col justify-between p-12 relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary-600 opacity-10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-purple-600 opacity-10 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4"></div>

        <div className="relative z-10">
          <div className="flex items-center gap-3 text-white mb-4">
            <Store className="w-10 h-10" />
            <span className="text-4xl font-black tracking-tight">KIRA</span>
          </div>
          <p className="text-primary-200 text-lg font-medium">Kirana Intelligence &amp; Risk Assessment</p>
        </div>

        <div className="relative z-10 space-y-8">
          <h2 className="text-3xl font-bold text-white leading-snug">
            AI-powered underwriting<br />
            for India's kirana economy
          </h2>
          <div className="space-y-4">
            {[
              'Visual intelligence from store imagery',
              'Spatial signal fusion from GPS coordinates',
              'Zero paperwork credit assessment',
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 text-primary-100">
                <ShieldCheck className="w-5 h-5 text-primary-300 shrink-0" />
                <span className="font-medium">{item}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-primary-400 text-sm font-medium">
          &copy; 2026 TenzorX — KIRA Platform
        </div>
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md animate-fade-in">
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-primary-600 transition mb-10">
            <ArrowLeft className="w-4 h-4" /> Back to home
          </Link>

          <div className="lg:hidden flex items-center gap-2.5 text-primary-700 mb-8">
            <Store className="w-8 h-8" />
            <span className="text-3xl font-black tracking-tight">KIRA</span>
          </div>

          <h1 className="text-3xl font-extrabold text-slate-900 mb-2">Welcome back</h1>
          <p className="text-slate-500 mb-10 text-lg">Sign in to your lender workspace</p>

          {/* Show which page they were trying to access */}
          {redirectPath !== '/app/dashboard' && (
            <div className="bg-indigo-50 border border-indigo-100 text-indigo-700 p-3 rounded-xl mb-6 text-sm font-medium">
              Sign in to continue to your requested page.
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl mb-6 text-sm font-medium animate-scale-in">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full border border-slate-300 rounded-xl px-4 py-3 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-slate-800 font-medium"
                placeholder="you@lender.in"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full border border-slate-300 rounded-xl px-4 py-3 pr-12 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-slate-800 font-medium"
                  placeholder="Enter password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white py-3.5 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-600/25 hover:shadow-xl hover:shadow-primary-600/30"
            >
              {isLoggingIn ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Connecting…
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Sign In
                </>
              )}
            </button>
          </form>

          <div className="mt-8 p-4 bg-primary-50 border border-primary-100 rounded-xl">
            <p className="text-xs font-bold text-primary-700 uppercase tracking-wide mb-2">Demo Credentials</p>
            <div className="text-sm text-primary-600 space-y-1 font-medium">
              <p>Admin: <span className="font-mono">maya@democapital.in</span></p>
              <p>Officer: <span className="font-mono">rohan@democapital.in</span></p>
              <p className="text-primary-400 text-xs mt-2">Any password works in demo mode</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/useAuth';

// Public pages
import Home from './pages/Home';
import Assessment from './pages/Assessment';
import Results from './pages/Results';
import Login from './pages/Login';

// Lender workspace pages
import LenderShell from './components/layout/LenderShell';
import Dashboard from './pages/Dashboard';
import KiranaList from './pages/KiranaList';
import KiranaDetail from './pages/KiranaDetail';
import CaseList from './pages/CaseList';
import CaseDetail from './pages/CaseDetail';
import NewCase from './pages/NewCase';
import ActiveLoans from './pages/ActiveLoans';
import Portfolio from './pages/Portfolio';
import Documents from './pages/Documents';

/**
 * KIRA — Main Application Component
 *
 * Sets up React Router with:
 *   /           — Home (landing page)
 *   /login      — Lender login
 *   /app/tools/assessment/:sessionId — Results (assessment display)
 *   /app/*      — Lender workspace (protected routes)
 *
 * Both "Start Assessment" (Home) and "Run Assessment" (LenderShell → Tools)
 * route to the same Assessment component nested inside the lender shell
 * at /app/tools/assessment for a consistent workspace feel.
 *
 * Owner: Frontend Lead
 */

/**
 * Guards a route that requires authentication.
 * If not authenticated, redirects to /login with a ?redirect param so the
 * user is returned to the intended page after login.
 */
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Build redirect URL so login can send the user back after auth
    const loginPath = `/login?redirect=${encodeURIComponent(location.pathname + location.search)}`;
    return <Navigate to={loginPath} replace />;
  }

  return children;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          {/* Protected lender workspace */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <LenderShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="kiranas" element={<KiranaList />} />
            <Route path="kiranas/:kiranaId" element={<KiranaDetail />} />
            <Route path="cases" element={<CaseList />} />
            <Route path="cases/:caseId" element={<CaseDetail />} />
            <Route path="active-loans" element={<ActiveLoans />} />
            <Route path="portfolio" element={<Portfolio />} />
            <Route path="documents" element={<Documents />} />
            <Route path="new-case" element={<NewCase />} />
            {/* Tools → Run Assessment — same component, inside lender shell */}
            <Route path="tools/assessment" element={<Assessment />} />
            <Route path="tools/assessment/:sessionId" element={<Results />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;

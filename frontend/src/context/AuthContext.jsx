/**
 * KIRA — Auth Context
 *
 * Provides authentication state for the lender workspace.
 * Fetches real org data from the backend on login.
 */

import { createContext, useState, useCallback } from 'react';
import { getPlatformDemoSnapshot } from '../api/kiraApi';

const AuthContext = createContext(null);

const SESSION_KEY = 'kira_auth_session';

function loadSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return null;
}

function saveSession(session) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    /* ignore */
  }
}

function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }) {
  const initialSession = loadSession();
  const hasInitialSession = Boolean(initialSession?.user && initialSession?.org);
  const [user, setUser] = useState(initialSession?.user ?? null);
  const [org, setOrg] = useState(initialSession?.org ?? null);
  const [isAuthenticated, setIsAuthenticated] = useState(hasInitialSession);
  const [isLoading] = useState(false);

  const login = useCallback(async (email) => {
    try {
      // Try to fetch real snapshot from backend
      let snapshotData = null;
      try {
        const res = await getPlatformDemoSnapshot();
        snapshotData = res.data;
      } catch (err) {
        console.error('Failed to get snapshot', err);
        return { success: false, error: 'Failed to connect to KIRA platform.' };
      }

      if (!snapshotData || !snapshotData.users || !snapshotData.organizations) {
        return { success: false, error: 'Invalid platform data.' };
      }

      const foundUser = snapshotData.users.find(u => u.email === email);
      if (!foundUser) {
         return { success: false, error: 'User email not found in platform snapshot.' };
      }

      const selectedOrg = snapshotData.organizations.find(o => o.id === foundUser.org_id) || snapshotData.organizations[0];

      const session = {
        user: {
          id: foundUser.id,
          full_name: foundUser.full_name,
          email: foundUser.email,
          role: foundUser.role,
          org_id: selectedOrg.id,
        },
        org: {
          id: selectedOrg.id,
          name: selectedOrg.name,
          slug: selectedOrg.slug,
        },
      };

      setUser(session.user);
      setOrg(session.org);
      setIsAuthenticated(true);
      saveSession(session);

      return { success: true };
    } catch (err) {
      console.error('Login failed:', err);
      return { success: false, error: 'Failed to connect to KIRA platform.' };
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setOrg(null);
    setIsAuthenticated(false);
    clearSession();
  }, []);

  return (
    <AuthContext.Provider value={{ user, org, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export default AuthContext;

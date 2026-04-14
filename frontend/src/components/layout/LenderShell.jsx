/**
 * KIRA — Lender Shell Layout
 *
 * Persistent sidebar navigation + top header bar for the lender workspace.
 * Uses React Router <Outlet> for nested page content.
 *
 * Owner: Frontend Lead
 * Phase: 9.2
 */

import { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import {
  Store, LayoutDashboard, Users, Briefcase, PlusCircle,
  LogOut, Menu, X, CreditCard, User, Wallet, LineChart, FolderKanban,
  ChevronDown, Mail, ShieldCheck
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/kiranas', label: 'Kiranas', icon: Users },
  { to: '/app/cases', label: 'Cases', icon: Briefcase },
  { to: '/app/active-loans', label: 'Active Loans', icon: Wallet },
  { to: '/app/portfolio', label: 'Portfolio', icon: LineChart },
  { to: '/app/documents', label: 'Documents', icon: FolderKanban },
  { to: '/app/new-case', label: 'New Case', icon: PlusCircle },
];

const SECONDARY_NAV = [
  { to: '/app/tools/assessment', label: 'Run Assessment', icon: CreditCard },
];

export default function LenderShell() {
  const { user, org, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);

  const handleLogout = () => {
    setProfileMenuOpen(false);
    logout();
    navigate('/', { replace: true });
  };

  const closeSidebar = () => setSidebarOpen(false);

  useEffect(() => {
    function handlePointerDown(event) {
      if (!profileMenuRef.current?.contains(event.target)) {
        setProfileMenuOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setProfileMenuOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  const navLinkClasses = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 group ${
      isActive
        ? 'bg-primary-600/15 text-primary-200 shadow-sm'
        : 'text-sidebar-text hover:bg-sidebar-hover hover:text-white'
    }`;

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={closeSidebar} />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-[260px] bg-sidebar-bg flex flex-col transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-primary-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary-600/30">
              <Store className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-white font-bold text-lg tracking-tight block leading-tight">KIRA</span>
              <span className="text-sidebar-text text-[10px] font-semibold uppercase tracking-widest">Platform</span>
            </div>
          </div>
          <button onClick={closeSidebar} className="lg:hidden text-sidebar-text hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Org badge */}
        <div className="px-5 py-4 border-b border-white/5">
          <div className="flex items-center gap-2 bg-sidebar-hover rounded-lg px-3 py-2.5">
            <div className="w-8 h-8 bg-primary-800 rounded-lg flex items-center justify-center text-primary-300 text-xs font-black">
              {org?.name?.charAt(0) || 'K'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-white text-sm font-semibold truncate">{org?.name || 'Lender'}</div>
              <div className="text-sidebar-text text-xs truncate">Workspace</div>
            </div>
          </div>
        </div>

        {/* Main nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <p className="px-4 text-[10px] font-bold text-sidebar-text/60 uppercase tracking-widest mb-2">Main</p>
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} className={navLinkClasses} onClick={closeSidebar}>
              <item.icon className="w-5 h-5 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}

          <div className="my-4 border-t border-white/5" />

          <p className="px-4 text-[10px] font-bold text-sidebar-text/60 uppercase tracking-widest mb-2">Tools</p>
          {SECONDARY_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={navLinkClasses} onClick={closeSidebar}>
              <item.icon className="w-5 h-5 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="px-3 py-4 border-t border-white/5">
          <div className="flex items-center gap-3 px-3 py-2 mb-2">
            <div className="w-9 h-9 bg-primary-700 rounded-full flex items-center justify-center text-primary-200 font-bold text-sm">
              {user?.full_name?.split(' ').map(n => n[0]).join('') || 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-white text-sm font-semibold truncate">{user?.full_name || 'User'}</div>
              <div className="text-sidebar-text text-xs capitalize">{user?.role?.replace('_', ' ') || 'Role'}</div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Top header */}
        <header className="bg-white border-b border-slate-200 px-4 lg:px-8 py-3.5 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-slate-600 hover:text-slate-900 p-1.5 rounded-lg hover:bg-slate-100 transition"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center gap-3">
            <NavLink
              to="/app/new-case"
              className="hidden sm:flex items-center gap-1.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-all shadow-sm"
            >
              <PlusCircle className="w-4 h-4" /> New Case
            </NavLink>
            <div className="relative" ref={profileMenuRef}>
              <button
                type="button"
                onClick={() => setProfileMenuOpen((open) => !open)}
                className={`flex items-center gap-2 rounded-full border px-1.5 py-1.5 transition-all ${
                  profileMenuOpen
                    ? 'border-primary-200 bg-primary-50 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
                aria-haspopup="menu"
                aria-expanded={profileMenuOpen}
                aria-label="Open account menu"
              >
                <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white font-bold text-xs shadow-sm">
                  {user?.full_name?.split(' ').map((name) => name[0]).join('') || 'U'}
                </div>
                <ChevronDown
                  className={`hidden sm:block w-4 h-4 text-slate-500 transition-transform ${
                    profileMenuOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {profileMenuOpen && (
                <div className="absolute right-0 top-[calc(100%+10px)] w-72 rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10 overflow-hidden z-40 animate-scale-in">
                  <div className="bg-gradient-to-r from-primary-900 via-primary-800 to-primary-700 px-4 py-4 text-white">
                    <div className="flex items-start gap-3">
                      <div className="w-11 h-11 rounded-full bg-white/15 border border-white/20 flex items-center justify-center font-bold text-sm">
                        {user?.full_name?.split(' ').map((name) => name[0]).join('') || 'U'}
                      </div>
                      <div className="min-w-0">
                        <div className="font-bold text-sm truncate">{user?.full_name || 'User'}</div>
                        <div className="text-primary-100 text-xs mt-1 truncate">{org?.name || 'Workspace'}</div>
                      </div>
                    </div>
                  </div>

                  <div className="p-3">
                    <div className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-3 space-y-2">
                      <div className="flex items-center gap-2 text-sm text-slate-700">
                        <Mail className="w-4 h-4 text-slate-400" />
                        <span className="truncate">{user?.email || 'No email available'}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-700">
                        <ShieldCheck className="w-4 h-4 text-slate-400" />
                        <span className="capitalize">{user?.role?.replace('_', ' ') || 'Role'}</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleLogout}
                      className="mt-3 flex items-center gap-2 w-full rounded-xl px-3 py-3 text-sm font-semibold text-red-600 hover:bg-red-50 transition-all"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

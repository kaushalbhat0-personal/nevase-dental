import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from '../components/layout/Sidebar';
import { Topbar } from '../components/layout/Topbar';
import { HealthNews } from '../components/layout/HealthNews';
import type { User } from '../types';

interface MainLayoutProps {
  user: User | null;
  onLogout: () => void;
  children: React.ReactNode;
}

const SIDEBAR_COLLAPSED_KEY = 'sidebar-collapsed';
const SIDEBAR_USER_PREFERENCE_KEY = 'sidebar-user-preference';
const MD_BREAKPOINT = 768;
const LG_BREAKPOINT = 1024;

export function MainLayout({ user, onLogout, children }: MainLayoutProps) {
  // Mobile drawer state
  const [mobileOpen, setMobileOpen] = useState(false);
  // Desktop collapse state
  const [isCollapsed, setIsCollapsed] = useState(false);
  // Track if user has manually set a preference
  const [hasUserPreference, setHasUserPreference] = useState(false);

  // Load collapse state from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    const userPref = localStorage.getItem(SIDEBAR_USER_PREFERENCE_KEY);

    if (saved !== null) {
      setIsCollapsed(saved === 'true');
    }
    if (userPref === 'true') {
      setHasUserPreference(true);
    }
  }, []);

  // Persist collapse state to localStorage
  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed));
  }, [isCollapsed]);

  // Auto-collapse based on screen size (unless user has manually set preference)
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;

      // Mobile: always reset drawer
      if (width >= LG_BREAKPOINT) {
        setMobileOpen(false);
      }

      // Auto-collapse logic (only if no user preference)
      if (!hasUserPreference) {
        if (width < LG_BREAKPOINT && width >= MD_BREAKPOINT) {
          // Medium screens: auto collapse
          setIsCollapsed(true);
        } else if (width >= LG_BREAKPOINT) {
          // Desktop: auto expand
          setIsCollapsed(false);
        }
      }
    };

    // Initial check
    handleResize();

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [hasUserPreference]);

  const toggleCollapse = useCallback(() => {
    setIsCollapsed(prev => {
      const newValue = !prev;
      // Mark that user has manually set preference
      setHasUserPreference(true);
      localStorage.setItem(SIDEBAR_USER_PREFERENCE_KEY, 'true');
      return newValue;
    });
  }, []);

  return (
    <div className="flex min-h-screen w-full overflow-y-auto bg-background">
      {/* Mobile Overlay */}
      <div
        className={`fixed inset-0 bg-black/60 z-40 lg:hidden transition-opacity duration-300 ${
          mobileOpen ? 'opacity-100 visible' : 'opacity-0 invisible pointer-events-none'
        }`}
        onClick={() => setMobileOpen(false)}
      />

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full bg-surface border-r border-border transition-all duration-300 ease-in-out flex-shrink-0
          /* Mobile: drawer behavior with transform */
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          /* Desktop: always visible, no transform */
          lg:static lg:translate-x-0 lg:flex
          /* Width: expanded or collapsed on desktop, full on mobile */
          ${isCollapsed ? 'lg:w-20' : 'lg:w-64'}
          w-64
        `}
      >
        <Sidebar
          user={user}
          onClose={() => setMobileOpen(false)}
          isCollapsed={isCollapsed}
          onToggleCollapse={toggleCollapse}
        />
      </aside>

      {/* Main Content */}
      <main className="flex-1 w-full overflow-x-hidden min-w-0 lg:ml-0">
        <Topbar
          user={user}
          onLogout={onLogout}
          onMenuToggle={() => setMobileOpen(true)}
        />
        <div className="flex w-full">
          <div className="flex-1 min-w-0 p-4 sm:p-6">
            {children}
          </div>
          <aside className="w-80 flex-shrink-0 hidden xl:block p-6 bg-surface border-l border-border">
            <HealthNews />
          </aside>
        </div>
      </main>
    </div>
  );
}

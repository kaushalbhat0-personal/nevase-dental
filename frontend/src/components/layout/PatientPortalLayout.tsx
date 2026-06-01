import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Calendar, Receipt, FileText, LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { cn } from '@/lib/utils';

const navItems = [
  { to: '/patient/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/patient/appointments', label: 'My Appointments', icon: Calendar },
  { to: '/patient/bills', label: 'My Bills', icon: Receipt },
  { to: '/patient/prescriptions', label: 'Prescriptions', icon: FileText },
];

export function PatientPortalLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="flex min-h-screen bg-[#F8FAFC]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 shadow-sm transform transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Sidebar header */}
          <div className="flex items-center justify-between px-5 py-5 border-b border-gray-100">
            <Link to="/patient/dashboard" className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-[#0EA5E9] flex items-center justify-center shadow-sm">
                <span className="text-white font-bold text-lg">N</span>
              </div>
              <div>
                <p className="font-bold text-sm text-[#0F172A]">Nevase Dental</p>
                <p className="text-[10px] text-[#1E293B]/50">Patient Portal</p>
              </div>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Nav items */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-[#0EA5E9]/10 text-[#0EA5E9] shadow-sm'
                      : 'text-[#1E293B]/70 hover:bg-gray-50 hover:text-[#1E293B]'
                  )}
                >
                  <item.icon className={cn('w-5 h-5 shrink-0', isActive ? 'text-[#0EA5E9]' : 'text-[#1E293B]/50')} />
                  <span>{item.label}</span>
                  {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Link>
              );
            })}
          </nav>

          {/* Sidebar footer */}
          <div className="px-4 py-4 border-t border-gray-100">
            <div className="flex items-center gap-3 mb-3 px-2">
              <div className="w-8 h-8 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center text-xs font-medium text-[#0EA5E9]">
                {(user?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[#0F172A] truncate">{user?.full_name || 'Patient'}</p>
                <p className="text-xs text-[#1E293B]/50 truncate">{user?.email || ''}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-4 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-gray-200 shadow-sm">
          <div className="flex items-center justify-between px-4 sm:px-6 h-16">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-100 text-[#1E293B]"
              >
                <Menu className="w-5 h-5" />
              </button>
              <h1 className="text-base sm:text-lg font-semibold text-[#0F172A]">
                Welcome, {user?.full_name?.split(' ')[0] || 'Patient'}
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to="/patient/discover"
                className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-colors"
              >
                Book Appointment
              </Link>
              <button
                onClick={handleLogout}
                className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 px-4 sm:px-6 py-6 sm:py-8 max-w-5xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

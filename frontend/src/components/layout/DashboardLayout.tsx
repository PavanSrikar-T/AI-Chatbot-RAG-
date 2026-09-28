import { useState, type ReactNode } from 'react';
import { 
  Bot, 
  FileText, 
  Home, 
  Briefcase, 
  GraduationCap, 
  Settings, 
  BarChart3, 
  Brain,
  Search,
  Bell,
  Menu,
  X,
  Sparkles,
  ChevronRight,
  UserCheck
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface DashboardLayoutProps {
  children: ReactNode;
}

const navItems = [
  { icon: Home, label: 'Dashboard', path: '/', badge: null, color: 'text-blue-600' },
  { icon: Bot, label: 'AI Chat', path: '/chat', badge: 'Copilot', color: 'text-indigo-600' },
  { icon: FileText, label: 'Resume & Documents', path: '/documents', badge: null, color: 'text-sky-600' },
  { icon: Briefcase, label: 'Job Match & Plan', path: '/jobs', badge: 'Match', color: 'text-emerald-600' },
  { icon: GraduationCap, label: 'Mock Interview', path: '/interview', badge: 'Adaptive', color: 'text-purple-600' },
  { icon: BarChart3, label: 'Weakness Heatmap', path: '/readiness', badge: null, color: 'text-amber-600' },
  { icon: Brain, label: 'Skill Retention', path: '/retention', badge: 'Decay', color: 'text-pink-600' },
];

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Derive current page title
  const currentNav = navItems.find((n) => n.path === location.pathname) || {
    label: 'Overview',
    path: '/'
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-900 font-sans overflow-hidden">
      {/* Mobile Backdrop */}
      {mobileMenuOpen && (
        <div 
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm lg:hidden animate-in fade-in"
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col justify-between
        transition-transform duration-300 ease-in-out lg:static lg:translate-x-0
        ${mobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'}
      `}>
        <div>
          {/* Logo Header */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-100">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-bold tracking-tight text-slate-900 leading-none">
                  Career<span className="text-blue-600">Mind</span>
                </span>
                <span className="text-[10px] text-slate-400 font-medium tracking-wider uppercase mt-0.5">
                  AI Career Copilot
                </span>
              </div>
            </Link>

            <button 
              onClick={() => setMobileMenuOpen(false)}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 lg:hidden"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="py-5 px-3 space-y-1">
            <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Platform Modules
            </div>

            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-semibold shadow-xs border border-blue-100/80'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
                    <span>{item.label}</span>
                  </div>

                  {item.badge && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      isActive 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'bg-slate-100 text-slate-500'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Card / Settings at Bottom */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/50">
          <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white font-semibold text-xs flex items-center justify-center shadow-xs">
                PA
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-slate-800 leading-tight">Pavan Anand</span>
                <span className="text-[10px] text-emerald-600 font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse" />
                  Twin Synced
                </span>
              </div>
            </div>

            <Link 
              to="/readiness"
              title="Career Settings & Readiness"
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Settings className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </aside>

      {/* Main Body */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 lg:hidden"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-400 hidden sm:inline">CareerMind</span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-300 hidden sm:inline" />
              <span className="font-bold text-slate-900">{currentNav.label}</span>
            </div>
          </div>

          {/* Search & Actions */}
          <div className="flex items-center gap-3">
            {/* Search Bar */}
            <div className="relative hidden md:block w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search modules, skills, docs..."
                className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700 placeholder:text-slate-400"
              />
            </div>

            {/* Notification Icon */}
            <Link
              to="/retention"
              title="Skill Retention Alerts"
              className="relative p-2 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-blue-600 ring-2 ring-white" />
            </Link>

            {/* Digital Twin Status Pill */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
              <UserCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Career Digital Twin: <strong className="text-slate-900 font-bold">Active</strong></span>
            </div>
          </div>
        </header>

        {/* Content Container */}
        <main className="flex-1 overflow-auto bg-[#F8FAFC] p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Code2,
  CalendarClock,
  BarChart3,
  CalendarCheck,
  Building2,
  HelpCircle,
  LogOut,
  User,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  Download,
  Tag,
  Trophy,
  Video,
  Award,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import ExportProgress from './common/ExportProgress';
import TagToggle from './common/TagToggle';
import NotificationCenter from './common/NotificationCenter';

const NAV_ITEMS = [
  { id: 'problems',    label: 'Problem Bank',   icon: Code2,         shortcut: 'P' },
  { id: 'challenges',  label: 'Challenges',     icon: Trophy,        shortcut: 'H' },
  { id: 'interview',   label: 'Interview Mode', icon: Video,         shortcut: 'I' },
  { id: 'companies',   label: 'Companies',      icon: Building2,     shortcut: 'C' },
  { id: 'review',      label: "Today's Review", icon: CalendarClock, shortcut: 'R' },
  { id: 'analytics',   label: 'Analytics',      icon: BarChart3,     shortcut: 'A' },
  { id: 'achievements',label: 'Achievements',   icon: Award,         shortcut: 'M' },
  { id: 'study-plan',  label: 'Study Plan',     icon: CalendarCheck, shortcut: 'S' },
];

export default function Navbar({ activeTab, setActiveTab, dueCount = 0, onOpenShortcuts }) {
  const { user, isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = (e) => {
    e.preventDefault();
    logout();
    navigate('/login', { replace: true });
  };

  const sidebarWidth = collapsed ? 72 : 220;

  return (
    <motion.aside
      animate={{ width: sidebarWidth }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className="glass-nav hidden lg:flex flex-col sticky top-0 h-screen z-40 overflow-hidden shrink-0"
      style={{ width: sidebarWidth }}
    >
      {/* Brand */}
      <div className="px-4 py-5 flex items-center justify-between border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 shrink-0 rounded-xl bg-brand-gradient flex items-center justify-center shadow-brand-glow-sm">
            <Code2 className="h-4.5 w-4.5 text-white" style={{ width: 18, height: 18 }} />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="font-bold text-sm text-white leading-tight whitespace-nowrap">DSA Tracker</div>
                <div className="text-[10px] text-slate-500 whitespace-nowrap">Leitner SRS</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        {!collapsed && <NotificationCenter onNavigateTab={setActiveTab} />}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          const hasBadge = item.id === 'review' && dueCount > 0;

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              title={collapsed ? item.label : undefined}
              className={`nav-item w-full ${isActive ? 'active' : ''} ${collapsed ? 'justify-center px-2' : ''}`}
            >
              <div className="relative shrink-0">
                <Icon
                  className={`h-4.5 w-4.5 transition-colors ${isActive ? 'text-indigo-400' : ''}`}
                  style={{ width: 18, height: 18 }}
                />
                {hasBadge && (
                  <span className="absolute -top-1.5 -right-1.5 h-4 min-w-4 px-1 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center leading-none">
                    {dueCount}
                  </span>
                )}
              </div>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -4 }}
                    transition={{ duration: 0.15 }}
                    className="text-sm font-medium whitespace-nowrap flex-1 text-left"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
              {!collapsed && hasBadge && (
                <span className="ml-auto px-1.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 text-[10px] font-bold border border-rose-500/30">
                  {dueCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="p-2 border-t border-white/[0.06] space-y-0.5">
        {/* Tag Toggle */}
        <div className={`nav-item w-full ${collapsed ? 'justify-center px-2' : ''}`}>
          <TagToggle sidebarMode collapsed={collapsed} />
        </div>

        {/* Export Data */}
        <div className={`nav-item w-full ${collapsed ? 'justify-center px-2' : ''}`}>
          <ExportProgress sidebarMode collapsed={collapsed} />
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className={`nav-item w-full ${collapsed ? 'justify-center px-2' : ''}`}
        >
          {theme === 'dark'
            ? <Sun className="h-4 w-4 shrink-0" style={{ width: 16, height: 16 }} />
            : <Moon className="h-4 w-4 shrink-0" style={{ width: 16, height: 16 }} />
          }
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-sm whitespace-nowrap"
              >
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Keyboard Shortcuts */}
        <button
          onClick={onOpenShortcuts}
          title="Keyboard Shortcuts (?)"
          className={`nav-item w-full ${collapsed ? 'justify-center px-2' : ''}`}
        >
          <HelpCircle className="h-4 w-4 shrink-0" style={{ width: 16, height: 16 }} />
          <AnimatePresence>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-sm whitespace-nowrap flex-1 text-left">
                Shortcuts
              </motion.span>
            )}
          </AnimatePresence>
          {!collapsed && <kbd className="ml-auto px-1.5 py-0.5 text-[10px] rounded bg-white/5 text-slate-500 font-mono border border-white/08">?</kbd>}
        </button>

        {/* User */}
        {isAuthenticated && user && (
          <div className={`flex items-center gap-2 px-2 py-2 rounded-xl mt-1 ${collapsed ? 'justify-center' : ''}`}>
            <div className="h-7 w-7 shrink-0 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <User className="h-3.5 w-3.5 text-white" style={{ width: 14, height: 14 }} />
            </div>
            <AnimatePresence>
              {!collapsed && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-slate-300 truncate">{user.username}</div>
                  <div className="text-[10px] text-slate-500 truncate">{user.email}</div>
                </motion.div>
              )}
            </AnimatePresence>
            {!collapsed && (
              <button
                onClick={handleLogout}
                title="Logout"
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
              >
                <LogOut className="h-3.5 w-3.5" style={{ width: 14, height: 14 }} />
              </button>
            )}
          </div>
        )}

        {/* Collapse Toggle */}
        <button
          onClick={() => setCollapsed(c => !c)}
          className={`nav-item w-full mt-1 border-t border-white/[0.06] pt-2 ${collapsed ? 'justify-center px-2' : ''}`}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed
            ? <ChevronRight className="h-4 w-4" style={{ width: 16, height: 16 }} />
            : <ChevronLeft className="h-4 w-4" style={{ width: 16, height: 16 }} />
          }
          <AnimatePresence>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-sm whitespace-nowrap">
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
}
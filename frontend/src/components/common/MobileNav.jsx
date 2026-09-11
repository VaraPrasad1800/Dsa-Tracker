import React from 'react';
import { Code2, CalendarClock, BarChart3, CalendarCheck, Building2 } from 'lucide-react';
import { motion } from 'framer-motion';

const NAV_ITEMS = [
  { id: 'problems',    label: 'Problems',  icon: Code2 },
  { id: 'companies',   label: 'Companies', icon: Building2 },
  { id: 'review',      label: 'Review',    icon: CalendarClock },
  { id: 'analytics',   label: 'Analytics', icon: BarChart3 },
  { id: 'study-plan',  label: 'Plan',      icon: CalendarCheck },
];

export default function MobileNav({ activeTab, setActiveTab, dueCount = 0 }) {
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50">
      {/* Glass background */}
      <div
        className="flex items-center justify-around px-2 py-2 border-t"
        style={{
          background: 'rgba(10, 10, 15, 0.92)',
          backdropFilter: 'blur(24px)',
          borderColor: 'rgba(255,255,255,0.06)',
        }}
      >
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          const hasBadge = item.id === 'review' && dueCount > 0;

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className="relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all duration-200"
            >
              {/* Active pill indicator */}
              {isActive && (
                <motion.div
                  layoutId="mobile-nav-pill"
                  className="absolute inset-0 rounded-xl"
                  style={{
                    background: 'rgba(99,102,241,0.15)',
                    border: '1px solid rgba(99,102,241,0.2)',
                  }}
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}

              <div className="relative">
                <Icon
                  style={{ width: 20, height: 20 }}
                  className={`transition-colors duration-200 ${
                    isActive ? 'text-indigo-400' : 'text-slate-500'
                  }`}
                />
                {hasBadge && (
                  <span className="absolute -top-1.5 -right-1.5 h-4 min-w-4 px-0.5 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center">
                    {dueCount}
                  </span>
                )}
              </div>

              <span
                className={`text-[10px] font-medium relative transition-colors duration-200 ${
                  isActive ? 'text-indigo-400' : 'text-slate-500'
                }`}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
import React, { useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, animate } from 'framer-motion';
import { CheckCircle2, Flame, Clock, AlertTriangle, Trophy } from 'lucide-react';

/* =====================================================
   Animated count-up number hook
   ===================================================== */
function useCountUp(target, duration = 1200) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = null;
    const step = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return display;
}

/* =====================================================
   Progress Ring SVG (donut with gradient + glow)
   ===================================================== */
function ProgressRing({ value, max, color = 'indigo', size = 68, stroke = 5 }) {
  const r = (size - stroke * 2) / 2;
  const circ = 2 * Math.PI * r;
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const offset = circ * (1 - pct);
  const gradId = `ring-grad-${color}-${Math.random().toString(36).slice(2)}`;

  const gradColors = {
    indigo: ['#6366f1', '#8b5cf6'],
    amber: ['#f59e0b', '#fb923c'],
    emerald: ['#10b981', '#14b8a6'],
    rose: ['#f43f5e', '#fb7185'],
    teal: ['#14b8a6', '#06b6d4'],
  }[color] || ['#6366f1', '#8b5cf6'];

  const glowColors = {
    indigo: 'rgba(99,102,241,0.5)',
    amber: 'rgba(245,158,11,0.5)',
    emerald: 'rgba(16,185,129,0.5)',
    rose: 'rgba(244,63,94,0.5)',
    teal: 'rgba(20,184,166,0.5)',
  }[color] || 'rgba(99,102,241,0.5)';

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={gradColors[0]} />
          <stop offset="100%" stopColor={gradColors[1]} />
        </linearGradient>
        <filter id={`glow-${gradId}`}>
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* Track */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none"
        stroke="rgba(255,255,255,0.05)"
        strokeWidth={stroke}
      />
      {/* Progress fill */}
      <motion.circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none"
        stroke={`url(#${gradId})`}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        filter={`url(#glow-${gradId})`}
        style={{ filter: `drop-shadow(0 0 4px ${glowColors})` }}
      />
    </svg>
  );
}

/* =====================================================
   Individual Stat Card
   ===================================================== */
function StatCard({ icon: Icon, label, children, glowClass = '', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
      className="stat-card group cursor-default"
    >
      {/* Background glow */}
      <div className={`absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${glowClass}`} />

      <div className="relative">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>
            {label}
          </span>
          <div className="p-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)' }}>
            <Icon className="h-3.5 w-3.5" style={{ width: 14, height: 14, color: '#64748b' }} />
          </div>
        </div>
        {children}
      </div>
    </motion.div>
  );
}

/* =====================================================
   Main StatsSummary
   ===================================================== */
export default function StatsSummary({ stats, onSelectFilterTopic }) {
  const solved = stats?.total_solved || 0;
  const total = stats?.total_problems || 1;
  const percentage = Math.round((solved / total) * 100);
  const streak = stats?.current_streak || 0;
  const longestStreak = stats?.longest_streak || 0;
  const dueToday = stats?.due_today_count || 0;
  const revisit = stats?.total_revisit || 0;
  const weakTopics = stats?.weak_topics || [];

  const displaySolved = useCountUp(solved);
  const displayStreak = useCountUp(streak);
  const displayDue = useCountUp(dueToday);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[0,1,2,3].map(i => (
          <div key={i} className="glass-card rounded-2xl p-5 h-32 skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {/* Card 1: Problems Solved */}
      <StatCard
        icon={CheckCircle2}
        label="Problems Solved"
        glowClass="bg-stat-glow-emerald"
        delay={0}
      >
        <div className="flex items-center gap-3">
          <ProgressRing value={solved} max={total} color="emerald" />
          <div>
            <div className="text-3xl font-bold text-white tabular-nums">{displaySolved}</div>
            <div className="text-xs mt-0.5" style={{ color: '#475569' }}>
              of {total} ({percentage}%)
            </div>
          </div>
        </div>
      </StatCard>

      {/* Card 2: Streak */}
      <StatCard
        icon={Flame}
        label="Daily Streak"
        glowClass="bg-stat-glow-amber"
        delay={0.08}
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <div
              className="h-[68px] w-[68px] rounded-full flex items-center justify-center shrink-0"
              style={{
                background: 'rgba(245,158,11,0.1)',
                border: '2px solid rgba(245,158,11,0.2)',
                boxShadow: streak > 0 ? '0 0 20px rgba(245,158,11,0.25)' : 'none',
              }}
            >
              <span className="text-3xl" role="img" aria-label="fire">🔥</span>
            </div>
          </div>
          <div>
            <div className="text-3xl font-bold tabular-nums" style={{ color: '#fbbf24' }}>
              {displayStreak}
            </div>
            <div className="text-xs mt-0.5 flex items-center gap-1" style={{ color: '#475569' }}>
              <Trophy style={{ width: 11, height: 11, color: '#f59e0b' }} />
              Best: {longestStreak}d
            </div>
          </div>
        </div>
      </StatCard>

      {/* Card 3: Due for Review */}
      <StatCard
        icon={Clock}
        label="Due for Review"
        glowClass="bg-stat-glow-blue"
        delay={0.16}
      >
        <div className="flex items-center gap-3">
          <ProgressRing value={dueToday} max={Math.max(dueToday + revisit, 1)} color="indigo" />
          <div>
            <div className="text-3xl font-bold tabular-nums" style={{ color: '#a5b4fc' }}>
              {displayDue}
            </div>
            <div className="text-xs mt-0.5" style={{ color: '#475569' }}>
              Revisit queue: <span style={{ color: '#fb7185' }}>{revisit}</span>
            </div>
          </div>
        </div>
      </StatCard>

      {/* Card 4: Focus Areas */}
      <StatCard
        icon={AlertTriangle}
        label="Focus Areas"
        glowClass="bg-stat-glow-rose"
        delay={0.24}
      >
        <div className="flex flex-wrap gap-1.5 mt-1">
          {weakTopics.length > 0 ? (
            <>
              {weakTopics.slice(0, 3).map((topic) => (
                <button
                  key={topic}
                  onClick={() => onSelectFilterTopic?.(topic)}
                  className="text-xs px-2.5 py-1 rounded-lg transition-all duration-150 font-medium"
                  style={{
                    background: 'rgba(244,63,94,0.1)',
                    color: '#fb7185',
                    border: '1px solid rgba(244,63,94,0.2)',
                    boxShadow: 'inset 0 1px 0 rgba(244,63,94,0.1)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(244,63,94,0.18)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(244,63,94,0.1)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  {topic}
                </button>
              ))}
              <div className="text-[11px] w-full mt-1" style={{ color: '#475569' }}>
                Under 50% solved
              </div>
            </>
          ) : (
            <div>
              <div className="text-sm font-semibold" style={{ color: '#34d399' }}>
                ✓ All topics strong!
              </div>
              <div className="text-[11px] mt-1" style={{ color: '#475569' }}>
                Great coverage across all areas
              </div>
            </div>
          )}
        </div>
      </StatCard>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Flame, Trophy, Calendar, Zap, Sparkles } from 'lucide-react';

function useCountUp(target, duration = 1000) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = null;
    const step = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return count;
}

export default function StreakCounter({ streaks }) {
  if (!streaks) return null;

  const currentStreak = streaks.current_streak || 0;
  const longestStreak = streaks.longest_streak || 0;
  const displayCurrent = useCountUp(currentStreak);
  const displayLongest = useCountUp(longestStreak);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {/* Current Streak */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="glass-card rounded-2xl p-5 relative overflow-hidden border border-white/[0.07]"
      >
        <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="flex items-center justify-between text-amber-400 mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Current Streak
          </span>
          <div className="p-1.5 rounded-lg bg-amber-500/15 border border-amber-500/30">
            <Flame className="h-4 w-4 text-amber-400" />
          </div>
        </div>

        <div className="text-4xl font-extrabold text-white flex items-baseline gap-2 tabular-nums">
          <span className="text-amber-400">🔥 {displayCurrent}</span>
          <span className="text-xs text-slate-400 font-normal">days active</span>
        </div>

        <p className="text-xs text-slate-400 mt-2">
          {currentStreak > 0
            ? 'Momentum is high — keep the fire burning!'
            : 'Solve a problem today to ignite your streak!'}
        </p>
      </motion.div>

      {/* Longest Streak */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.08 }}
        className="glass-card rounded-2xl p-5 relative overflow-hidden border border-white/[0.07]"
      >
        <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="flex items-center justify-between text-yellow-400 mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Personal Record
          </span>
          <div className="p-1.5 rounded-lg bg-yellow-500/15 border border-yellow-500/30">
            <Trophy className="h-4 w-4 text-yellow-400" />
          </div>
        </div>

        <div className="text-4xl font-extrabold text-white flex items-baseline gap-2 tabular-nums">
          <span className="text-yellow-300">⚡ {displayLongest}</span>
          <span className="text-xs text-slate-400 font-normal">days all-time high</span>
        </div>

        <p className="text-xs text-slate-400 mt-2">
          {currentStreak >= longestStreak && longestStreak > 0
            ? "🏆 You're at your all-time personal best!"
            : `${longestStreak - currentStreak} days to break your personal record`}
        </p>
      </motion.div>

      {/* Last Solved */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.16 }}
        className="glass-card rounded-2xl p-5 relative overflow-hidden border border-white/[0.07]"
      >
        <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="flex items-center justify-between text-indigo-400 mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Last Activity
          </span>
          <div className="p-1.5 rounded-lg bg-indigo-500/15 border border-indigo-500/30">
            <Calendar className="h-4 w-4 text-indigo-400" />
          </div>
        </div>

        <div className="text-2xl font-bold text-slate-200 mt-1">
          {streaks.last_solved_date
            ? new Date(streaks.last_solved_date).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            : 'No solves recorded'}
        </div>

        <p className="text-xs text-slate-400 mt-2">Latest algorithmic problem completed</p>
      </motion.div>
    </div>
  );
}

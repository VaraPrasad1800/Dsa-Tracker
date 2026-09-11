import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, ArrowRight, X, Sparkles } from 'lucide-react';

export default function ReminderBanner({ dueCount = 0, onStartReview }) {
  const [dismissed, setDismissed] = React.useState(false);

  if (dueCount <= 0 || dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="relative overflow-hidden border-b z-30"
        style={{
          background: 'linear-gradient(90deg, rgba(99,102,241,0.12), rgba(244,63,94,0.12), rgba(245,158,11,0.12))',
          backdropFilter: 'blur(16px)',
          borderColor: 'rgba(245,158,11,0.25)',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="p-1.5 rounded-xl shrink-0 animate-pulse"
              style={{
                background: 'rgba(245,158,11,0.15)',
                color: '#fbbf24',
                border: '1px solid rgba(245,158,11,0.3)',
                boxShadow: '0 0 12px rgba(245,158,11,0.25)',
              }}
            >
              <Bell className="h-4 w-4" />
            </div>
            <p className="text-xs sm:text-sm text-slate-200 truncate">
              <span className="font-semibold text-amber-300">Spaced Repetition:</span>{' '}
              <span className="text-slate-300">You have</span>{' '}
              <span className="font-bold text-white px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">
                {dueCount} {dueCount === 1 ? 'problem' : 'problems'}
              </span>{' '}
              <span className="text-slate-300 hidden sm:inline">due for Leitner review today.</span>
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onStartReview}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl text-slate-950 transition-all duration-150 transform hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
                boxShadow: '0 2px 10px rgba(245,158,11,0.35)',
              }}
            >
              <span>Review Now</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>

            <button
              onClick={() => setDismissed(true)}
              className="p-1 text-slate-400 hover:text-white rounded-lg transition-colors"
              title="Dismiss banner"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

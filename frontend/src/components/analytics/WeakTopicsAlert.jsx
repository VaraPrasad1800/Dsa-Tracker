import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, ArrowRight, Target } from 'lucide-react';

export default function WeakTopicsAlert({ topicData, onSelectTopic }) {
  const weakTopics = (topicData?.topics || []).filter((t) => t.is_weak);

  if (weakTopics.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-2xl p-5 border border-rose-500/20 relative overflow-hidden shadow-glass"
      style={{
        background: 'linear-gradient(135deg, rgba(244,63,94,0.08), rgba(16,16,28,0.85))',
      }}
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-rose-500/15 text-rose-400 border border-rose-500/30 shrink-0 mt-0.5 shadow-[0_0_12px_rgba(244,63,94,0.2)]">
            <AlertTriangle className="h-5 w-5" />
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-white">Focus Recommendation: Weak Patterns Detected</h4>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 font-semibold border border-rose-500/30">
                Action Required
              </span>
            </div>

            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              You've completed under 50% of problems in these patterns. Targeting these will yield the highest interview preparation ROI:
            </p>

            <div className="flex flex-wrap gap-2 pt-2">
              {weakTopics.slice(0, 6).map((t) => (
                <button
                  key={t.id}
                  onClick={() => onSelectTopic && onSelectTopic(t.name)}
                  className="px-3 py-1.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 text-xs font-semibold border border-rose-500/30 transition-all duration-150 flex items-center gap-1.5 hover:scale-[1.02]"
                >
                  <Target className="h-3 w-3 text-rose-400" />
                  <span>{t.name}</span>
                  <span className="text-[10px] text-rose-400/80 font-mono">({t.percentage}%)</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

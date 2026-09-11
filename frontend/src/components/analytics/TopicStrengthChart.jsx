import React from 'react';
import { motion } from 'framer-motion';
import { Tag, AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react';

export default function TopicStrengthChart({ topicData, onTopicClick }) {
  const topics = topicData?.topics || [];

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/[0.07] shadow-glass">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Tag className="h-4 w-4 text-indigo-400" />
            Topic Mastery & Pattern Curves
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Completion rate per data structure & algorithm pattern — click any topic to filter problem bank
          </p>
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
        {topics.map((t, idx) => {
          const isWeak = t.percentage < 50;
          const isMastered = t.percentage >= 80;

          const barGradient = isMastered
            ? 'linear-gradient(90deg, #10b981, #14b8a6)'
            : isWeak
            ? 'linear-gradient(90deg, #f43f5e, #f97316)'
            : 'linear-gradient(90deg, #6366f1, #8b5cf6)';

          const textColor = isMastered
            ? 'text-emerald-400'
            : isWeak
            ? 'text-rose-400'
            : 'text-indigo-300';

          return (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03, duration: 0.2 }}
              onClick={() => onTopicClick && onTopicClick(t.name)}
              className="p-3 rounded-xl border border-white/[0.05] hover:border-indigo-500/40 hover:bg-white/[0.03] transition-all cursor-pointer group"
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
              }}
            >
              <div className="flex items-center justify-between text-xs font-semibold mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-slate-200 group-hover:text-indigo-300 transition-colors font-medium">
                    {t.name}
                  </span>

                  {isMastered && (
                    <span className="text-[10px] px-2 py-0.2 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="h-2.5 w-2.5" /> Mastered
                    </span>
                  )}

                  {isWeak && (
                    <span className="text-[10px] px-2 py-0.2 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1 font-semibold">
                      <AlertTriangle className="h-2.5 w-2.5" /> Weak Pattern
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-mono text-[11px]">
                    {t.solved} / {t.total}
                  </span>
                  <span className={`font-bold font-mono ${textColor}`}>{t.percentage}%</span>
                  <ChevronRight className="h-3 w-3 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>

              {/* Progress track */}
              <div className="w-full bg-black/40 h-2 rounded-full overflow-hidden border border-white/[0.04]">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(t.percentage, 100)}%` }}
                  transition={{ duration: 0.8, delay: idx * 0.02 + 0.1, ease: [0.16, 1, 0.3, 1] }}
                  className="h-full rounded-full"
                  style={{
                    background: barGradient,
                    boxShadow: isMastered
                      ? '0 0 8px rgba(16,185,129,0.4)'
                      : isWeak
                      ? '0 0 8px rgba(244,63,94,0.4)'
                      : '0 0 8px rgba(99,102,241,0.4)',
                  }}
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

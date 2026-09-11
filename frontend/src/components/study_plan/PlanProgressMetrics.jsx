import React from 'react';
import { CheckCircle2, Archive, Sparkles } from 'lucide-react';

export default function PlanProgressMetrics({ progress, plan, onDeactivate, onRegenerate }) {
  if (!progress) return null;

  const total = progress.total_problems || 1;
  const completed = progress.total_completed || 0;
  const pct = Math.round((completed / total) * 100);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-sm mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              Active Study Plan
            </span>
            <span className="text-xs text-slate-400">
              Target: <strong className="text-white">{plan?.target_date}</strong> ({plan?.problems_per_day}/day)
            </span>
          </div>
          <h3 className="text-lg font-bold text-white">Preparation Pace & Readiness</h3>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRegenerate}
            className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 font-semibold text-xs rounded-lg transition border border-indigo-500/30 flex items-center gap-1.5"
          >
            <Sparkles className="h-3.5 w-3.5" />
            New Plan
          </button>
          <button
            onClick={onDeactivate}
            className="px-3 py-1.5 bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 text-xs rounded-lg transition border border-slate-700 hover:border-rose-500/30 flex items-center gap-1.5"
            title="Archive current plan"
          >
            <Archive className="h-3.5 w-3.5" />
            Archive
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {/* On Pace Indicator */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Pace Status</div>
          <div className="flex items-center gap-2 mt-2">
            {progress.on_pace ? (
              <span className="px-2.5 py-1 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> On Pace
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded-lg bg-rose-500/15 text-rose-400 border border-rose-500/30 text-xs font-bold">
                Behind Pace
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">Evaluated against daily quota</div>
        </div>

        {/* Completed Today */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Today's Quota</div>
          <div className="text-2xl font-black text-white mt-1">
            {progress.completed_today || '0/0'}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">Problems finished today</div>
        </div>

        {/* Total Plan Solved */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Plan Progress</div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl font-black text-white">{completed}</span>
            <span className="text-xs text-slate-500">/ {total} ({pct}%)</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full rounded-full"
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
        </div>

        {/* Estimated Readiness */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Estimated Readiness</div>
          <div className="text-2xl font-black text-emerald-400 mt-1 flex items-baseline gap-1">
            {progress.estimated_readiness || 0}%
          </div>
          <div className="text-[11px] text-slate-500 mt-2">Coverage across weak topics</div>
        </div>
      </div>
    </div>
  );
}

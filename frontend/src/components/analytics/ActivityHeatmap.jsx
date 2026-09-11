import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Flame, Sparkles } from 'lucide-react';

export default function ActivityHeatmap({ heatmapData, currentYear, onYearChange }) {
  const [hoveredDay, setHoveredDay] = useState(null);

  const days = heatmapData?.data || [];
  const totalContributions = days.reduce((sum, d) => sum + (d.count || 0), 0);

  // Group days into weeks of 7
  const weeks = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }

  const getColorClass = (count) => {
    if (!count || count === 0) return 'bg-white/[0.03] border-white/[0.04]';
    if (count === 1) return 'bg-emerald-950/80 border-emerald-800/80 shadow-[0_0_4px_rgba(16,185,129,0.2)]';
    if (count === 2) return 'bg-emerald-800 border-emerald-600 shadow-[0_0_6px_rgba(16,185,129,0.3)]';
    if (count === 3) return 'bg-emerald-600 border-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]';
    return 'bg-emerald-400 border-emerald-300 shadow-[0_0_10px_rgba(52,211,153,0.6)] font-bold';
  };

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/[0.07] shadow-glass">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" />
            GitHub-Style Activity Heatmap
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            <strong className="text-emerald-400 font-bold">{totalContributions}</strong> algorithmic problems solved in {currentYear}
          </p>
        </div>

        {/* Year Selector */}
        <div className="flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/[0.08] text-xs self-start sm:self-auto">
          {[2024, 2025, 2026].map((yr) => (
            <button
              key={yr}
              onClick={() => onYearChange(yr)}
              className={`px-3 py-1 rounded-lg font-semibold transition-all duration-150 ${
                currentYear === yr
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {yr}
            </button>
          ))}
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="overflow-x-auto pb-2">
        <div className="inline-flex gap-1.5 min-w-[740px]">
          {weeks.map((week, wIdx) => (
            <div key={wIdx} className="flex flex-col gap-1.5">
              {week.map((day) => (
                <div
                  key={day.date}
                  onMouseEnter={() => setHoveredDay(day)}
                  onMouseLeave={() => setHoveredDay(null)}
                  className={`h-3.5 w-3.5 rounded-sm border cursor-pointer transition-all duration-150 hover:scale-150 hover:z-10 ${getColorClass(
                    day.count
                  )}`}
                  title={`${day.date}: ${day.count} solved`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Footer Info & Legend */}
      <div className="flex flex-wrap items-center justify-between gap-4 mt-4 pt-4 border-t border-white/[0.06] text-xs text-slate-400">
        <div>
          {hoveredDay ? (
            <span className="text-slate-200">
              <strong className="text-emerald-400">{hoveredDay.count} problems</strong> solved on{' '}
              {new Date(hoveredDay.date).toLocaleDateString(undefined, {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
          ) : (
            <span className="text-slate-500">Hover over any day to inspect problem solving volume</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-500">Less</span>
          <div className="h-3 w-3 rounded-sm bg-white/[0.03] border border-white/[0.06]" />
          <div className="h-3 w-3 rounded-sm bg-emerald-950 border border-emerald-800/80" />
          <div className="h-3 w-3 rounded-sm bg-emerald-800 border border-emerald-600" />
          <div className="h-3 w-3 rounded-sm bg-emerald-600 border border-emerald-500" />
          <div className="h-3 w-3 rounded-sm bg-emerald-400 border border-emerald-300" />
          <span className="text-[11px] text-slate-500">More</span>
        </div>
      </div>
    </div>
  );
}

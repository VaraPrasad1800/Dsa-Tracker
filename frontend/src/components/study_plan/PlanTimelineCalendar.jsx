import React from 'react';
import { Calendar, CheckCircle2, Lightbulb } from 'lucide-react';

export default function PlanTimelineCalendar({ planDays = [], onSelectProblem }) {
  const todayStr = new Date().toISOString().split('T')[0];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Calendar className="h-4 w-4 text-indigo-400" />
          Day-by-Day Practice Timeline
        </h3>
        <span className="text-xs text-slate-400">{planDays.length} scheduled days</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {planDays.map((day, idx) => {
          const isToday = day.date === todayStr;
          const isPast = day.date < todayStr;

          return (
            <div
              key={day.id}
              className={`rounded-2xl p-5 border flex flex-col justify-between transition-all ${
                isToday
                  ? 'bg-gradient-to-b from-indigo-950/40 to-slate-900 border-indigo-500/60 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/30'
                  : isPast
                  ? 'bg-slate-950/40 border-slate-800/60 opacity-80'
                  : 'bg-slate-900/80 border-slate-800'
              }`}
            >
              {/* Day Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">Day {idx + 1}</span>
                    <span className="text-xs text-slate-400 font-mono">
                      {new Date(day.date).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  </div>
                  {isToday && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-indigo-500 text-white uppercase tracking-wider animate-pulse">
                      Today
                    </span>
                  )}
                </div>

                {/* Focus Topic & Reason */}
                <div className="mb-3">
                  {day.focus_topic && (
                    <span className="inline-block px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 text-[11px] font-semibold border border-indigo-500/25 mb-1.5">
                      Focus: {day.focus_topic}
                    </span>
                  )}
                  <div className="text-xs text-amber-300/90 font-medium flex items-start gap-1.5 bg-amber-500/10 p-2 rounded-lg border border-amber-500/20">
                    <Lightbulb className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <span className="text-[11px] leading-tight">{day.reason}</span>
                  </div>
                </div>

                {/* Problem List */}
                <div className="space-y-1.5 mt-3">
                  {day.problems?.map((prob) => {
                    const isSolved = prob.user_progress?.status === 'SOLVED';

                    return (
                      <div
                        key={prob.id}
                        onClick={() => onSelectProblem && onSelectProblem(prob)}
                        className="flex items-center justify-between p-2 rounded-lg bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition cursor-pointer group text-xs"
                      >
                        <div className="flex items-center gap-2 truncate pr-2">
                          <CheckCircle2
                            className={`h-3.5 w-3.5 shrink-0 ${
                              isSolved ? 'text-emerald-400' : 'text-slate-600'
                            }`}
                          />
                          <span
                            className={`truncate ${
                              isSolved ? 'line-through text-slate-500' : 'text-slate-200 group-hover:text-indigo-300'
                            }`}
                          >
                            {prob.title}
                          </span>
                        </div>
                        <span
                          className={`text-[10px] font-semibold px-1.5 py-0.2 rounded shrink-0 ${
                            prob.difficulty === 'Easy'
                              ? 'text-emerald-400'
                              : prob.difficulty === 'Medium'
                              ? 'text-amber-400'
                              : 'text-rose-400'
                          }`}
                        >
                          {prob.difficulty}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Footer */}
              <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
                <span>Target: {day.difficulty_target}</span>
                <span>{day.problems?.length || 0} problems</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

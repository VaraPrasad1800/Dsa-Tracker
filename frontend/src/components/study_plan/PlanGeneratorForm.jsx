import React, { useState } from 'react';
import { Calendar, Target, Sparkles, AlertCircle } from 'lucide-react';

export default function PlanGeneratorForm({ onGenerate, loading = false }) {
  // Default target date: 30 days from now
  const defaultDate = new Date();
  defaultDate.setDate(defaultDate.getDate() + 30);
  const defaultDateStr = defaultDate.toISOString().split('T')[0];

  const [targetDate, setTargetDate] = useState(defaultDateStr);
  const [problemsPerDay, setProblemsPerDay] = useState(5);

  const calculateDaysRemaining = () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(targetDate);
    target.setHours(0, 0, 0, 0);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 1;
  };

  const daysRemaining = calculateDaysRemaining();
  const totalCapacity = daysRemaining * problemsPerDay;

  const handleSubmit = (e) => {
    e.preventDefault();
    onGenerate({
      target_date: targetDate,
      problems_per_day: problemsPerDay,
    });
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl max-w-2xl mx-auto">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-400" />
          Generate Rule-Based Study Plan
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Tailored daily practice schedule built with deterministic heuristics: 40% weak topics, 30% spaced revisit, 20% medium, 10% hard.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Date */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-1.5">
            <Calendar className="h-4 w-4 text-indigo-400" />
            <span>Target Interview / Deadline Date</span>
          </label>
          <input
            type="date"
            value={targetDate}
            min={new Date().toISOString().split('T')[0]}
            onChange={(e) => setTargetDate(e.target.value)}
            required
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Problems per Day Slider */}
        <div>
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
            <span className="flex items-center gap-1.5">
              <Target className="h-4 w-4 text-indigo-400" />
              <span>Daily Capacity (Problems / Day)</span>
            </span>
            <span className="text-base font-bold text-indigo-400 font-mono">
              {problemsPerDay} problems
            </span>
          </div>
          <input
            type="range"
            min="1"
            max="15"
            value={problemsPerDay}
            onChange={(e) => setProblemsPerDay(parseInt(e.target.value))}
            className="w-full accent-indigo-500 h-2 bg-slate-950 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-500 mt-1">
            <span>1 (Casual)</span>
            <span>5 (Balanced)</span>
            <span>15 (Intensive)</span>
          </div>
        </div>

        {/* Plan Summary Calculation */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-4 text-xs">
          <div>
            <div className="text-slate-400 font-medium">Days Remaining</div>
            <div className="text-lg font-bold text-white mt-0.5">{daysRemaining} days</div>
          </div>
          <div>
            <div className="text-slate-400 font-medium">Target Problems</div>
            <div className="text-lg font-bold text-indigo-400 mt-0.5">{totalCapacity} problems</div>
          </div>
          <div>
            <div className="text-slate-400 font-medium">Algorithm</div>
            <div className="text-xs font-bold text-emerald-400 mt-0.5">Deterministic Heuristics</div>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Intelligent Plan
            </>
          )}
        </button>
      </form>
    </div>
  );
}

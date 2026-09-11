import React from 'react';
import { Layers, ShieldCheck, ArrowRight } from 'lucide-react';

export default function LeitnerBoxGrid({ stats }) {
  const boxes = [
    { box: 1, interval: '1 Day', count: stats?.box_1_count || 0, desc: 'Daily Review', color: 'from-rose-500/20 to-orange-500/20 border-rose-500/30 text-rose-400' },
    { box: 2, interval: '3 Days', count: stats?.box_2_count || 0, desc: 'Short Term', color: 'from-amber-500/20 to-yellow-500/20 border-amber-500/30 text-amber-400' },
    { box: 3, interval: '7 Days', count: stats?.box_3_count || 0, desc: 'Weekly Review', color: 'from-blue-500/20 to-indigo-500/20 border-blue-500/30 text-blue-400' },
    { box: 4, interval: '14 Days', count: stats?.box_4_count || 0, desc: 'Bi-Weekly', color: 'from-indigo-500/20 to-purple-500/20 border-indigo-500/30 text-indigo-400' },
    { box: 5, interval: '30 Days', count: stats?.box_5_count || 0, desc: 'Mastered', color: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-400' },
  ];

  const totalInBoxes = boxes.reduce((sum, b) => sum + b.count, 0);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-sm mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-400" />
            Leitner 5-Box Memory Engine
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Solve correctly to advance boxes (+1d, +3d, +7d, +14d, +30d). Wrong answers reset to Box 1.
          </p>
        </div>
        <div className="text-xs text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 self-start sm:self-auto">
          Active Memory Cards: <strong className="text-white">{totalInBoxes}</strong>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {boxes.map((b) => (
          <div
            key={b.box}
            className={`rounded-xl border p-4 bg-gradient-to-b ${b.color} relative flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider">Box {b.box}</span>
              <span className="text-[11px] font-mono opacity-80">{b.interval}</span>
            </div>
            <div className="my-3">
              <div className="text-3xl font-black text-white">{b.count}</div>
              <div className="text-[11px] text-slate-300 mt-0.5">{b.desc}</div>
            </div>
            <div className="text-[10px] text-slate-400 flex items-center gap-1 border-t border-slate-800/40 pt-2">
              {b.box === 5 ? (
                <>
                  <ShieldCheck className="h-3 w-3 text-emerald-400" />
                  <span>Permanent memory</span>
                </>
              ) : (
                <>
                  <ArrowRight className="h-3 w-3 opacity-60" />
                  <span>Advance on solve</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

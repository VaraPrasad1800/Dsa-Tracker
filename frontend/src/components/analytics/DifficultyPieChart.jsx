import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Award, Layers } from 'lucide-react';

export default function DifficultyPieChart({ difficultyData }) {
  if (!difficultyData) return null;

  const data = [
    { name: 'Easy', solved: difficultyData.Easy?.solved || 0, total: difficultyData.Easy?.total || 0, color: '#10b981' },
    { name: 'Medium', solved: difficultyData.Medium?.solved || 0, total: difficultyData.Medium?.total || 0, color: '#f59e0b' },
    { name: 'Hard', solved: difficultyData.Hard?.solved || 0, total: difficultyData.Hard?.total || 0, color: '#f43f5e' },
  ];

  const totalSolved = data.reduce((acc, cur) => acc + cur.solved, 0);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="glass-modal p-3 rounded-xl border border-white/[0.08] text-xs space-y-1 shadow-xl">
          <div className="font-bold" style={{ color: d.color }}>{d.name}</div>
          <div className="text-slate-200">
            Solved: <span className="font-bold text-white">{d.solved}</span> / {d.total}
          </div>
          <div className="text-slate-400">
            Ratio: {d.total > 0 ? Math.round((d.solved / d.total) * 100) : 0}%
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/[0.07] flex flex-col justify-between h-full shadow-glass">
      <div>
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Award className="h-4 w-4 text-indigo-400" />
            Difficulty Distribution
          </h3>
          <span className="text-[11px] text-slate-500 font-medium">LeetCode Tiers</span>
        </div>
        <p className="text-xs text-slate-400">Solved problem ratio across difficulty tiers</p>
      </div>

      <div className="h-56 relative flex items-center justify-center my-2">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius={58}
              outerRadius={84}
              paddingAngle={5}
              dataKey="solved"
              stroke="none"
              animationBegin={100}
              animationDuration={1000}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  style={{
                    filter: `drop-shadow(0 0 6px ${entry.color}40)`,
                    outline: 'none',
                  }}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        <div className="absolute text-center pointer-events-none">
          <div className="text-3xl font-black text-white tabular-nums">{totalSolved}</div>
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mt-0.5">
            Total Solved
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-4 border-t border-white/[0.06] text-center text-xs">
        {data.map((d) => {
          const pct = d.total > 0 ? Math.round((d.solved / d.total) * 100) : 0;
          return (
            <div
              key={d.name}
              className="p-2.5 rounded-xl border transition-all"
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                borderColor: 'rgba(255, 255, 255, 0.05)',
              }}
            >
              <div className="font-bold text-[11px]" style={{ color: d.color }}>
                {d.name}
              </div>
              <div className="text-sm font-extrabold text-white mt-0.5">
                {d.solved} <span className="text-[10px] text-slate-500 font-normal">/ {d.total}</span>
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">{pct}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

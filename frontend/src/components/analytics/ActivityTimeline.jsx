import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';

export default function ActivityTimeline({ timelineData }) {
  const data = (timelineData || []).slice(-30);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-modal p-3 rounded-xl border border-white/[0.08] text-xs space-y-1 shadow-xl">
          <div className="font-semibold text-slate-300">
            {new Date(label).toLocaleDateString(undefined, {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            })}
          </div>
          <div className="flex items-center gap-2 text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Solved: <span className="font-bold text-white">{payload[0]?.value || 0}</span>
          </div>
          {payload[1] && (
            <div className="flex items-center gap-2 text-indigo-400">
              <span className="h-2 w-2 rounded-full bg-indigo-400" />
              Attempted: <span className="font-bold text-white">{payload[1]?.value || 0}</span>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/[0.07] shadow-glass h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-teal-400" />
            Daily Solves Velocity (Last 30 Days)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Consistency curves across recent problem completion dates
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>Solved</span>
          </div>
          <div className="flex items-center gap-1.5 text-indigo-400 font-medium">
            <span className="h-2 w-2 rounded-full bg-indigo-400" />
            <span>Attempted</span>
          </div>
        </div>
      </div>

      <div className="h-56 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="solvedGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="attemptedGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />

            <XAxis
              dataKey="date"
              stroke="#475569"
              fontSize={10}
              tickFormatter={(val) => {
                const d = new Date(val);
                return `${d.getMonth() + 1}/${d.getDate()}`;
              }}
            />
            <YAxis stroke="#475569" fontSize={10} allowDecimals={false} />

            <Tooltip content={<CustomTooltip />} />

            <Area
              type="monotone"
              dataKey="problems_solved"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#solvedGradient)"
            />
            <Area
              type="monotone"
              dataKey="problems_attempted"
              stroke="#6366f1"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              fillOpacity={1}
              fill="url(#attemptedGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

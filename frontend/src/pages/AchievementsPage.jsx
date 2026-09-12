import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Trophy, Lock, CheckCircle2, Zap, Sparkles } from 'lucide-react';
import { achievementsApi, pointsApi } from '../api/client';

export default function AchievementsPage() {
  const [filter, setFilter] = useState('all'); // 'all' | 'unlocked' | 'locked'

  // Fetch achievements
  const { data, isLoading } = useQuery({
    queryKey: ['achievements'],
    queryFn: async () => {
      const res = await achievementsApi.getAchievements();
      return res.data;
    },
  });

  // Fetch user points
  const { data: userPoints } = useQuery({
    queryKey: ['points'],
    queryFn: async () => {
      const res = await pointsApi.getPoints();
      return res.data;
    },
  });

  const achievements = data?.achievements || [];
  const unlockedCount = achievements.filter((a) => a.unlocked).length;
  const totalCount = achievements.length;
  const progressPct = totalCount > 0 ? Math.round((unlockedCount / totalCount) * 100) : 0;

  const filtered = achievements.filter((a) => {
    if (filter === 'unlocked') return a.unlocked;
    if (filter === 'locked') return !a.unlocked;
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header & Progress Card */}
      <div className="bg-slate-900/60 backdrop-blur-md p-6 rounded-3xl border border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <Trophy className="h-6 w-6 text-amber-400" />
            Milestones & Achievements
          </h1>
          <p className="text-sm text-slate-400">
            Earn badges and points as you solve problems, build streaks, and conquer challenges.
          </p>
        </div>

        {userPoints && (
          <div className="flex items-center gap-3 bg-slate-950 px-5 py-3 rounded-2xl border border-white/10 shrink-0">
            <div className="h-10 w-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-semibold uppercase">Total Points</div>
              <div className="text-xl font-bold text-white font-mono">{userPoints.total}</div>
            </div>
          </div>
        )}
      </div>

      {/* Progress Bar & Filter */}
      <div className="bg-slate-900/60 backdrop-blur-md p-6 rounded-3xl border border-white/[0.08] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span className="text-sm font-semibold text-white">
              Unlocked {unlockedCount} of {totalCount} Badges ({progressPct}%)
            </span>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-white/5">
            {['all', 'unlocked', 'locked'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition ${
                  filter === f
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="h-2.5 w-full bg-slate-950 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-amber-400 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Achievements Grid */}
      {isLoading ? (
        <div className="text-slate-500 text-sm py-12 text-center">Loading achievements...</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((ach) => (
            <div
              key={ach.code}
              className={`p-5 rounded-3xl border transition-all duration-200 flex flex-col justify-between gap-4 ${
                ach.unlocked
                  ? 'bg-gradient-to-b from-indigo-500/[0.08] to-slate-900/80 border-indigo-500/30 shadow-lg shadow-indigo-500/5'
                  : 'bg-slate-900/30 border-white/[0.04] opacity-75'
              }`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`h-14 w-14 rounded-2xl text-2xl flex items-center justify-center shrink-0 border ${
                    ach.unlocked
                      ? 'bg-indigo-500/20 border-indigo-500/40 shadow-inner'
                      : 'bg-slate-950 border-white/5 grayscale'
                  }`}
                >
                  {ach.unlocked ? ach.icon : <Lock className="h-5 w-5 text-slate-600" />}
                </div>

                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h3 className="font-bold text-white text-sm truncate">{ach.name}</h3>
                    {ach.unlocked && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{ach.description}</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-white/[0.06] text-xs">
                <span className="font-bold text-amber-400 flex items-center gap-1">
                  <Zap className="h-3.5 w-3.5" />
                  +{ach.points} pts
                </span>

                <span className="text-[11px] text-slate-500">
                  {ach.unlocked && ach.unlocked_at
                    ? `Unlocked ${new Date(ach.unlocked_at).toLocaleDateString()}`
                    : 'Locked'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

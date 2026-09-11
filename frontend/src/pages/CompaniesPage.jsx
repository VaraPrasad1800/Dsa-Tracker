import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Building2, ChevronRight, TrendingUp, Sparkles } from 'lucide-react';
import { problemsApi } from '../api/client';
import EmptyState from '../components/common/EmptyState';

export default function CompaniesPage({ onSelectCompany }) {
  const { data: companies = [], isLoading, isError } = useQuery({
    queryKey: ['companies'],
    queryFn: async () => {
      const res = await problemsApi.getCompanies();
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="py-6 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="glass-card rounded-2xl p-5 h-44 skeleton" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-6 max-w-7xl mx-auto">
        <div className="glass-card border-rose-500/30 rounded-2xl p-8 text-center text-rose-300">
          <p className="text-sm">Failed to load companies. Please check your connection and reload.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="py-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Targeted Interview Prep</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <Building2 className="h-7 w-7 text-indigo-400" />
            Interview by Company
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {companies.length} tech giants & high-growth startups tracked — practice the exact problem sets each asks
          </p>
        </div>
      </div>

      {/* Company Grid */}
      {companies.length === 0 ? (
        <div className="glass-card rounded-2xl p-8 border border-white/[0.07]">
          <EmptyState
            preset="noproblems"
            title="No companies tracked yet"
            body="Companies will appear here once problems are linked to company tags."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {companies.map((comp, idx) => {
            const solved = comp.user_progress?.solved || 0;
            const total = comp.problem_count || 0;
            const pct = total > 0 ? Math.round((solved / total) * 100) : 0;

            return (
              <motion.button
                key={comp.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: idx * 0.02 }}
                whileHover={{ y: -3 }}
                onClick={() => onSelectCompany(comp)}
                className="group text-left glass-card rounded-2xl p-5 border border-white/[0.07] transition-all shadow-glass relative overflow-hidden flex flex-col justify-between"
              >
                <div className="flex items-start justify-between">
                  <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/25 flex items-center justify-center shadow-[0_0_12px_rgba(99,102,241,0.2)]">
                    <Building2 className="h-5 w-5 text-indigo-400" />
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                </div>

                <div className="mt-4">
                  <h3 className="font-bold text-white text-base group-hover:text-indigo-300 transition-colors">
                    {comp.name}
                  </h3>

                  <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3.5 w-3.5 text-slate-500" />
                      {total} problems
                    </span>
                    <span className={solved > 0 ? 'text-emerald-400 font-semibold' : 'text-slate-500'}>
                      {solved} solved
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-3 h-2 rounded-full bg-black/40 overflow-hidden border border-white/[0.04]">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        pct >= 100
                          ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                          : pct >= 50
                          ? 'bg-gradient-to-r from-indigo-500 to-violet-400'
                          : 'bg-indigo-600/70'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="mt-1.5 text-[10px] text-slate-500 font-mono">{pct}% complete</div>
                </div>
              </motion.button>
            );
          })}
        </div>
      )}
    </div>
  );
}

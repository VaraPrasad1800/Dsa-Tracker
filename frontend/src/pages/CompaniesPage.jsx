import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Building2, ChevronRight, ChevronLeft, TrendingUp, Sparkles, X, Loader2 } from 'lucide-react';
import { problemsApi } from '../api/client';
import EmptyState from '../components/common/EmptyState';
import SearchBar from '../components/problems/SearchBar';

const PAGE_SIZE = 50;

export default function CompaniesPage({ onSelectCompany }) {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);

  // Debounce search input to avoid hitting API on every keystroke
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['companies', page, debouncedSearch],
    queryFn: async () => {
      const res = await problemsApi.getCompanies({
        page,
        search: debouncedSearch || undefined,
      });
      return res.data;
    },
    keepPreviousData: true,
  });

  const companies = Array.isArray(data) ? data : (data?.results || []);
  const totalCount = data?.count ?? companies.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const handleSelectCompany = (comp) => {
    if (onSelectCompany) {
      onSelectCompany(comp);
    }
    navigate(`/companies/${comp.slug || comp.id}`);
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

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

  const startIdx = totalCount === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const endIdx = Math.min(page * PAGE_SIZE, totalCount);

  return (
    <div className="py-6 space-y-6 w-full">
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
            {totalCount} tech giants & high-growth startups tracked — practice the exact problem sets each asks
          </p>
        </div>
      </div>

      {/* Search and Results Summary */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="w-full sm:max-w-md">
          <SearchBar
            value={search}
            onChange={(val) => {
              setSearch(val);
            }}
            onClear={() => {
              setSearch('');
            }}
            placeholder="Search companies... (e.g. Google, Amazon, Meta)"
          />
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-3 text-xs text-slate-400 px-1">
          {isFetching && (
            <span className="flex items-center gap-1.5 text-indigo-400 text-xs font-medium">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Updating...
            </span>
          )}
          {debouncedSearch ? (
            <span>
              Found <strong className="text-white font-semibold">{totalCount}</strong> matching {totalCount === 1 ? 'company' : 'companies'}
            </span>
          ) : (
            <span>
              Showing <strong className="text-white font-semibold">{startIdx}–{endIdx}</strong> of <strong className="text-white font-semibold">{totalCount}</strong> companies
            </span>
          )}
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition cursor-pointer"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Company Grid / Empty State */}
      {totalCount === 0 && !debouncedSearch ? (
        <div className="glass-card rounded-2xl p-8 border border-white/[0.07]">
          <EmptyState
            preset="noproblems"
            title="No companies tracked yet"
            body="Companies will appear here once problems are linked to company tags."
          />
        </div>
      ) : companies.length === 0 ? (
        <div className="glass-card rounded-2xl p-10 border border-white/[0.07] text-center space-y-3">
          <Building2 className="h-10 w-10 text-slate-500 mx-auto" />
          <h3 className="text-base font-semibold text-white">No companies found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No companies matching &quot;<span className="text-indigo-400 font-semibold">{search.trim()}</span>&quot;.
          </p>
          <button
            type="button"
            onClick={() => setSearch('')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 transition cursor-pointer"
          >
            <X className="h-3.5 w-3.5" />
            Clear search
          </button>
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
                transition={{ duration: 0.2, delay: Math.min(idx * 0.012, 0.25) }}
                whileHover={{ y: -3 }}
                onClick={() => handleSelectCompany(comp)}
                className="group text-left glass-card rounded-2xl p-5 border border-white/[0.07] transition-all shadow-glass relative overflow-hidden flex flex-col justify-between cursor-pointer"
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

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-white/[0.06]">
          <span className="text-xs text-slate-400">
            Page <strong className="text-white font-semibold">{page}</strong> of <strong className="text-white font-semibold">{totalPages}</strong> ({totalCount} total companies)
          </span>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => handlePageChange(page - 1)}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03] text-xs font-semibold text-slate-300 hover:text-white hover:border-white/20 transition disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Previous</span>
            </button>

            {/* Quick page jumps */}
            <div className="hidden sm:flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                .map((p, idx, arr) => {
                  const prevP = arr[idx - 1];
                  const showEllipsis = prevP && p - prevP > 1;
                  return (
                    <React.Fragment key={p}>
                      {showEllipsis && <span className="text-xs text-slate-600 px-1">...</span>}
                      <button
                        type="button"
                        onClick={() => handlePageChange(p)}
                        className={`h-7 min-w-7 px-2 rounded-lg text-xs font-bold transition cursor-pointer ${
                          p === page
                            ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
                            : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                        }`}
                      >
                        {p}
                      </button>
                    </React.Fragment>
                  );
                })}
            </div>

            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => handlePageChange(page + 1)}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03] text-xs font-semibold text-slate-300 hover:text-white hover:border-white/20 transition disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
            >
              <span>Next</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

import React, { useState, Suspense, lazy } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  SlidersHorizontal,
  Shuffle,
  LayoutGrid,
  LayoutList,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Flame,
  CheckCircle2,
} from 'lucide-react';
import { problemsApi, progressApi } from '../api/client';
import StatsSummary from '../components/StatsSummary';
import FilterSidebar from '../components/problems/FilterSidebar';
import SearchBar from '../components/problems/SearchBar';
import ProblemsTable from '../components/problems/ProblemsTable';
import ProblemCard from '../components/problems/ProblemCard';
import ProblemDetailModal from '../components/problems/ProblemDetailModal';
import { ProblemCardGridSkeleton } from '../components/common/SkeletonCard';
import EmptyState from '../components/common/EmptyState';
import { toast } from '../components/common/Toast';

const HeroOrb = lazy(() => import('../components/dashboard/HeroOrb'));

const SORT_OPTIONS = [
  { value: 'frequency', label: 'Most Asked' },
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
  { value: 'question_number', label: 'Problem # (1 → 99)' },
];

export default function ProblemsPage({ activeTopicFilter, onSelectTopicFilter, initialProblemId }) {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filters, setFilters] = useState({
    difficulty: '',
    status: '',
    topic: activeTopicFilter || '',
    company: '',
    bookmarked: '',
  });
  const [sort, setSort] = useState('question_number');
  const [shuffleNonce, setShuffleNonce] = useState(0);
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'
  const [page, setPage] = useState(1);
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [selectedProblem, setSelectedProblem] = useState(null);

  // Sync external initial problem (e.g. from Review or Challenges)
  React.useEffect(() => {
    if (initialProblemId) {
      problemsApi.getProblem(initialProblemId)
        .then((res) => setSelectedProblem(res.data))
        .catch(() => {});
    }
  }, [initialProblemId]);

  // Sync external topic filter
  React.useEffect(() => {
    if (activeTopicFilter) {
      setFilters((prev) => ({ ...prev, topic: activeTopicFilter }));
      setPage(1);
    }
  }, [activeTopicFilter]);

  // Debounce search by 250ms to prevent API flooding on every keystroke
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  // Reset to page 1 on debounced search change
  React.useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  // Problems query with staleTime and placeholderData
  const { data: problemsData, isLoading: loadingProblems } = useQuery({
    queryKey: ['problems', filters, debouncedSearch, page, sort, shuffleNonce],
    queryFn: async () => {
      const params = {
        page,
        sort: sort === 'random' ? 'random' : sort || undefined,
        difficulty: filters.difficulty || undefined,
        status: filters.status || undefined,
        topic: filters.topic || undefined,
        company: filters.company || undefined,
        bookmarked: filters.bookmarked || undefined,
        search: debouncedSearch || undefined,
      };
      const res = await problemsApi.getProblems(params);
      return res.data;
    },
    staleTime: 1000 * 60 * 2,
    placeholderData: (prev) => prev,
  });

  // Tags query
  const { data: tags = [] } = useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      const res = await problemsApi.getTags();
      return res.data;
    },
  });

  // Companies query
  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: async () => {
      const res = await problemsApi.getCompanies();
      return res.data;
    },
  });

  // Stats query
  const { data: userStats } = useQuery({
    queryKey: ['user-stats'],
    queryFn: async () => {
      const res = await progressApi.getStats();
      return res.data;
    },
  });

  // Mutation: Update Progress
  const updateProgressMutation = useMutation({
    mutationFn: async (payload) => {
      const res = await progressApi.saveProgress(payload);
      return res.data;
    },
    onSuccess: (updatedProgress) => {
      queryClient.invalidateQueries(['problems']);
      queryClient.invalidateQueries(['user-stats']);
      queryClient.invalidateQueries(['due-today']);
      queryClient.invalidateQueries(['due-today-count']);
      queryClient.invalidateQueries(['spaced-repetition-stats']);
      queryClient.invalidateQueries(['analytics-heatmap']);
      queryClient.invalidateQueries(['analytics-topic-breakdown']);
      queryClient.invalidateQueries(['analytics-streaks']);
      queryClient.invalidateQueries(['analytics-difficulty-breakdown']);

      if (updatedProgress.status === 'SOLVED') {
        toast.success(`Problem marked as Solved! Box ${updatedProgress.current_box || 1}`);
      } else if (updatedProgress.status === 'NEEDS_REVISIT') {
        toast.error('Added to revisit queue (Box 1)');
      }

      if (selectedProblem && selectedProblem.id === updatedProgress.problem) {
        setSelectedProblem((prev) => ({
          ...prev,
          user_progress: updatedProgress,
        }));
      }
    },
  });

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
    if (key === 'topic' && onSelectTopicFilter) {
      onSelectTopicFilter(value);
    }
  };

  const handleClearFilters = () => {
    setFilters({ difficulty: '', status: '', topic: '', company: '', bookmarked: '' });
    setSearch('');
    setPage(1);
    if (onSelectTopicFilter) onSelectTopicFilter('');
  };

  const handleQuickUpdateStatus = (problemId, newStatus, currentStatus) => {
    let finalStatus = newStatus;
    if (newStatus === 'SOLVED' && currentStatus === 'SOLVED') {
      finalStatus = 'UNSOLVED';
    } else if (newStatus === 'NEEDS_REVISIT' && currentStatus === 'NEEDS_REVISIT') {
      finalStatus = 'UNSOLVED';
    }

    updateProgressMutation.mutate({
      problem_id: problemId,
      status: finalStatus,
    });
  };

  const handleShuffle = () => {
    setSort('random');
    setShuffleNonce((n) => n + 1);
    setPage(1);
    toast('🎲 Shuffled problem set!', { icon: '✨' });
  };

  const handlePracticeTopic = async (topic) => {
    try {
      const toastId = toast.loading(`Finding practice question for ${topic}...`);
      const res = await problemsApi.getTopicPractice(topic);
      toast.dismiss(toastId);
      if (res.data?.target_problem) {
        if (onSolve) {
          onSolve(res.data.target_problem);
        } else {
          handleFilterChange('topic', topic);
        }
      } else {
        toast.error(`No practice questions found for ${topic}`);
        handleFilterChange('topic', topic);
      }
    } catch (err) {
      toast.error(`Could not load practice question for ${topic}`);
      handleFilterChange('topic', topic);
    }
  };

  const rawProblems = problemsData?.results || [];
  const problems = React.useMemo(() => {
    const seen = new Set();
    return rawProblems.filter((p) => {
      if (!p || seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    });
  }, [rawProblems]);
  const totalCount = problemsData?.count || 0;
  const totalPages = Math.ceil(totalCount / 20) || 1;

  return (
    <div className="py-6 space-y-6 w-full">
      {/* 3D Hero Banner Strip */}
      <div
        className="glass-card rounded-3xl p-6 sm:p-8 relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6"
        style={{
          background: 'linear-gradient(135deg, rgba(16,16,28,0.9), rgba(20,20,38,0.7))',
          borderColor: 'rgba(255,255,255,0.08)',
        }}
      >
        <div className="relative z-10 max-w-xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Spaced Repetition & Analytics Engine</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">
            Master Technical Interviews with{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-violet-400">
              Cognitive Science
            </span>
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Personalized Leitner SRS tracks your retention intervals. Solve, review weak patterns, and turn algorithmic thinking into second nature.
          </p>
        </div>

        {/* 3D Decorative Orb */}
        <div className="shrink-0 relative hidden sm:flex items-center justify-center">
          <Suspense
            fallback={
              <div className="h-36 w-36 rounded-full bg-indigo-500/10 animate-pulse" />
            }
          >
            <HeroOrb size={170} />
          </Suspense>
        </div>
      </div>

      {/* Top Stats Summary Cards */}
      <StatsSummary
        stats={userStats}
        onSelectFilterTopic={(topic) => handleFilterChange('topic', topic)}
        onPracticeTopic={handlePracticeTopic}
      />

      {/* Main Layout: Filters Sidebar + Search & Table/Cards */}
      <div className="flex items-start gap-4 sm:gap-5">
        {/* Filter Sidebar */}
        <FilterSidebar
          filters={filters}
          onFilterChange={handleFilterChange}
          onClearFilters={handleClearFilters}
          counts={problemsData?.counts}
          availableTags={tags}
          availableCompanies={companies}
          isOpenMobile={isMobileFilterOpen}
          onCloseMobile={() => setIsMobileFilterOpen(false)}
        />

        {/* Problems Content Area */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Controls Bar: Search, Sort, Shuffle, View Toggle, Mobile Filter */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-[220px]">
              <SearchBar
                value={search}
                onChange={(val) => {
                  setSearch(val);
                  setPage(1);
                }}
                onClear={() => {
                  setSearch('');
                  setPage(1);
                }}
              />
            </div>

            {/* Sort Dropdown */}
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs font-medium rounded-xl transition-all cursor-pointer"
              style={{
                background: 'rgba(16, 16, 28, 0.75)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: '#f1f5f9',
              }}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-slate-900 text-white">
                  {opt.label}
                </option>
              ))}
            </select>

            {/* Shuffle Button */}
            <button
              onClick={handleShuffle}
              title="Surprise me with a fresh shuffle"
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all"
              style={{
                background: 'rgba(16, 16, 28, 0.75)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: '#94a3b8',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#a5b4fc';
                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#94a3b8';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
              }}
            >
              <Shuffle className="h-3.5 w-3.5 text-indigo-400" />
              <span className="hidden sm:inline">Shuffle</span>
            </button>

            {/* View Mode Toggle */}
            <div
              className="flex items-center rounded-xl p-0.5 border"
              style={{
                background: 'rgba(16, 16, 28, 0.75)',
                borderColor: 'rgba(255, 255, 255, 0.08)',
              }}
            >
              <button
                onClick={() => setViewMode('cards')}
                className={`p-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'cards'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Card grid view"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'table'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Data table view"
              >
                <LayoutList className="h-4 w-4" />
              </button>
            </div>

            {/* Mobile Filter Button */}
            <button
              onClick={() => setIsMobileFilterOpen(true)}
              className="lg:hidden flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-200"
              style={{
                background: 'rgba(16, 16, 28, 0.75)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <SlidersHorizontal className="h-4 w-4 text-indigo-400" />
              <span>Filters</span>
            </button>
          </div>

          {/* Cards or Table View */}
          {viewMode === 'table' ? (
            <ProblemsTable
              problems={problems}
              totalCount={totalCount}
              page={page}
              pageSize={20}
              onPageChange={(newPage) => setPage(newPage)}
              onSelectProblem={(prob) => setSelectedProblem(prob)}
              onQuickUpdateStatus={handleQuickUpdateStatus}
              loading={loadingProblems}
            />
          ) : loadingProblems ? (
            <ProblemCardGridSkeleton count={6} />
          ) : problems.length === 0 ? (
            <div className="glass-card rounded-2xl p-8 border border-white/[0.07]">
              <EmptyState
                preset="search"
                title="No problems found"
                body="Try adjusting your search criteria or clearing your filters."
                action={
                  <button
                    onClick={handleClearFilters}
                    className="btn-secondary text-xs px-4 py-2"
                  >
                    Clear All Filters
                  </button>
                }
              />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {problems.map((prob) => (
                  <ProblemCard
                    key={prob.id}
                    problem={prob}
                    onSelect={(p) => setSelectedProblem(p)}
                    onQuickUpdateStatus={handleQuickUpdateStatus}
                  />
                ))}
              </div>

              {/* Pagination footer for cards view */}
              {totalCount > 20 && (
                <div className="flex items-center justify-between px-5 py-3 border border-white/[0.07] glass-card rounded-2xl text-xs text-slate-400">
                  <div>
                    Showing <span className="text-white font-semibold">{(page - 1) * 20 + 1}</span> to{' '}
                    <span className="text-white font-semibold">
                      {Math.min(page * 20, totalCount)}
                    </span>{' '}
                    of <span className="text-indigo-400 font-semibold">{totalCount}</span> problems
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setPage(page - 1)}
                      disabled={page <= 1}
                      className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.04] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="px-2 font-medium text-slate-300">
                      {page} / {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(page + 1)}
                      disabled={page >= totalPages}
                      className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.04] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Detail & Edit Modal */}
      {selectedProblem && (
        <ProblemDetailModal
          problem={selectedProblem}
          onClose={() => setSelectedProblem(null)}
          onSaveProgress={(data) => updateProgressMutation.mutate(data)}
        />
      )}
    </div>
  );
}

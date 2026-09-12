import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowLeft, Building2, SlidersHorizontal, Sparkles } from 'lucide-react';
import { problemsApi, progressApi } from '../api/client';
import FilterSidebar from '../components/problems/FilterSidebar';
import SearchBar from '../components/problems/SearchBar';
import ProblemsTable from '../components/problems/ProblemsTable';
import ProblemDetailModal from '../components/problems/ProblemDetailModal';
import { toast } from '../components/common/Toast';

const SORT_OPTIONS = [
  { value: 'frequency', label: 'Most Asked' },
  { value: 'question_number', label: 'Problem # (1 → 99)' },
  { value: 'title', label: 'Title A → Z' },
  { value: 'difficulty_asc', label: 'Difficulty (Easy first)' },
  { value: 'difficulty_desc', label: 'Difficulty (Hard first)' },
  { value: 'created', label: 'Recently Added' },
];

export default function CompanyProblemsPage({ company, onBack, onNavigateToProblems, onSolve }) {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    difficulty: '',
    status: '',
    topic: '',
    company: '',
    bookmarked: '',
  });
  const [sort, setSort] = useState('frequency');
  const [page, setPage] = useState(1);
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [selectedProblem, setSelectedProblem] = useState(null);

  const companyId = company.slug || company.id;

  const { data: problemsData, isLoading: loadingProblems } = useQuery({
    queryKey: ['company-problems', companyId, filters, search, sort, page],
    queryFn: async () => {
      const params = {
        page,
        sort: sort || undefined,
        difficulty: filters.difficulty || undefined,
        status: filters.status || undefined,
        topic: filters.topic || undefined,
        bookmarked: filters.bookmarked || undefined,
        search: search || undefined,
      };
      const res = await problemsApi.getCompanyProblems(companyId, params);
      return res.data;
    },
  });

  const { data: tags = [] } = useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      const res = await problemsApi.getTags();
      return res.data;
    },
  });

  const updateProgressMutation = useMutation({
    mutationFn: async (payload) => {
      const res = await progressApi.saveProgress(payload);
      return res.data;
    },
    onSuccess: (updatedProgress) => {
      queryClient.invalidateQueries(['company-problems']);
      queryClient.invalidateQueries(['user-stats']);
      queryClient.invalidateQueries(['due-today']);
      queryClient.invalidateQueries(['spaced-repetition-stats']);

      if (updatedProgress.status === 'SOLVED') {
        toast.success('Marked as solved! Progress updated.');
      }

      if (selectedProblem && selectedProblem.id === updatedProgress.problem) {
        setSelectedProblem((prev) => ({ ...prev, user_progress: updatedProgress }));
      }
    },
  });

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const handleClearFilters = () => {
    setFilters({ difficulty: '', status: '', topic: '', company: '', bookmarked: '' });
    setSearch('');
    setPage(1);
  };

  const handleQuickUpdateStatus = (problemId, newStatus) => {
    updateProgressMutation.mutate({ problem_id: problemId, status: newStatus });
  };

  const responseCompany = problemsData?.company || company;
  const totalCount = problemsData?.count || 0;
  const solvedCount =
    responseCompany?.user_progress?.solved ?? company?.user_progress?.solved ?? 0;

  return (
    <div className="py-6 space-y-6 max-w-7xl mx-auto">
      {/* Company Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="p-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-slate-400 hover:text-white hover:border-white/[0.15] transition shrink-0"
            title="Back to all companies"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="min-w-0">
            <h1 className="text-2xl font-extrabold text-white flex items-center gap-2.5 truncate">
              <Building2 className="h-6 w-6 text-indigo-400 shrink-0" />
              {responseCompany.name} Problem Bank
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {totalCount} problems curated •{' '}
              <span className="text-emerald-400 font-semibold">{solvedCount} solved</span>
            </p>
          </div>
        </div>

        <button
          onClick={onNavigateToProblems}
          className="btn-secondary text-xs px-3.5 py-2 self-start sm:self-auto"
        >
          View Full Problem Bank
        </button>
      </div>

      {/* Main Layout: Filters Sidebar + Search & Table */}
      <div className="flex items-start gap-6">
        <FilterSidebar
          filters={filters}
          onFilterChange={handleFilterChange}
          onClearFilters={handleClearFilters}
          counts={problemsData?.counts}
          availableTags={tags}
          availableCompanies={[responseCompany]}
          hideCompanies
          isOpenMobile={isMobileFilterOpen}
          onCloseMobile={() => setIsMobileFilterOpen(false)}
        />

        <div className="flex-1 min-w-0 space-y-4">
          {/* Search, Sort & Mobile Filter Trigger */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-[200px]">
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

            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs font-medium rounded-xl transition cursor-pointer"
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

            <button
              onClick={() => setIsMobileFilterOpen(true)}
              className="lg:hidden flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-200"
              style={{
                background: 'rgba(16, 16, 28, 0.75)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <SlidersHorizontal className="h-4 w-4 text-indigo-400" />
              <span>Filters</span>
            </button>
          </div>

          <ProblemsTable
            problems={problemsData?.results || []}
            totalCount={totalCount}
            page={page}
            pageSize={20}
            onPageChange={(newPage) => setPage(newPage)}
            onSelectProblem={(prob) => setSelectedProblem(prob)}
            onQuickUpdateStatus={handleQuickUpdateStatus}
            onSolve={onSolve}
            loading={loadingProblems}
          />
        </div>
      </div>

      {/* Detail & Edit Modal */}
      {selectedProblem && (
        <ProblemDetailModal
          problem={selectedProblem}
          onClose={() => setSelectedProblem(null)}
          onSaveProgress={(data) => updateProgressMutation.mutate(data)}
          onSolve={onSolve}
        />
      )}
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { CalendarClock, PartyPopper, ArrowRight, Sparkles } from 'lucide-react';
import { spacedRepetitionApi, progressApi } from '../api/client';
import ReviewProblemCard from '../components/spaced_repetition/ReviewProblemCard';
import LeitnerBoxGrid from '../components/spaced_repetition/LeitnerBoxGrid';
import EmptyState from '../components/common/EmptyState';
import { toast } from '../components/common/Toast';

export default function TodaysReviewPage({ onNavigateToProblems }) {
  const queryClient = useQueryClient();
  const [completedCount, setCompletedCount] = useState(0);

  const { data: dueProblems = [], isLoading: loadingDue } = useQuery({
    queryKey: ['due-today'],
    queryFn: async () => {
      const res = await spacedRepetitionApi.getDueToday();
      return res.data;
    },
  });

  const { data: boxStats } = useQuery({
    queryKey: ['spaced-repetition-stats'],
    queryFn: async () => {
      const res = await spacedRepetitionApi.getStats();
      return res.data;
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ problemId, status }) => {
      return await progressApi.saveProgress({ problem_id: problemId, status });
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries(['due-today']);
      queryClient.invalidateQueries(['due-today-count']);
      queryClient.invalidateQueries(['spaced-repetition-stats']);
      queryClient.invalidateQueries(['user-stats']);
      queryClient.invalidateQueries(['problems']);
      setCompletedCount((prev) => prev + 1);

      if (variables.status === 'SOLVED') {
        toast.success('Advanced to next Leitner Box! 🚀');
      } else {
        toast('Reset to Box 1 for reinforcement.', { icon: '🔄' });
      }
    },
  });

  const handleAction = (problemId, status) => {
    updateStatusMutation.mutate({ problemId, status });
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      if (!dueProblems || dueProblems.length === 0) return;

      const currentItem = dueProblems[0];
      if (!currentItem) return;

      if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        handleAction(currentItem.problem.id, 'SOLVED');
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        handleAction(currentItem.problem.id, 'NEEDS_REVISIT');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dueProblems]);

  const totalDueInitial = (dueProblems?.length || 0) + completedCount;
  const progressPercentage =
    totalDueInitial > 0 ? Math.round((completedCount / totalDueInitial) * 100) : 100;

  if (loadingDue) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center text-slate-400">
        <div className="glass-card rounded-2xl p-12 max-w-md mx-auto space-y-4 skeleton">
          <div className="h-10 w-10 mx-auto rounded-full skeleton" />
          <div className="h-4 w-48 mx-auto rounded skeleton" />
        </div>
      </div>
    );
  }

  const currentItem = dueProblems[0];

  return (
    <div className="max-w-4xl mx-auto py-6 space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Spaced Retrieval Queue</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <CalendarClock className="h-7 w-7 text-indigo-400" />
            Today's Review Queue
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Review cards scheduled by Leitner retention decay intervals to convert patterns into long-term memory
          </p>
        </div>

        {totalDueInitial > 0 && (
          <div className="glass-card rounded-2xl px-4 py-2.5 flex items-center gap-3 border border-white/[0.08] shadow-glass">
            <div className="text-xs text-slate-400">
              Reviewed: <strong className="text-white">{completedCount}</strong> / {totalDueInitial}
            </div>
            <div className="w-24 bg-black/40 h-2 rounded-full overflow-hidden border border-white/[0.04]">
              <div
                className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full transition-all duration-500"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
            <span className="text-xs font-bold text-indigo-400">{progressPercentage}%</span>
          </div>
        )}
      </div>

      {/* Main Review Card or Empty State */}
      {currentItem ? (
        <div className="space-y-3">
          <div className="text-xs text-slate-400 flex items-center justify-between px-1">
            <span>
              Card <strong className="text-white">1</strong> of{' '}
              <strong className="text-white">{dueProblems.length}</strong> remaining
            </span>
            <span>
              Shortcut: Press <kbd className="px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-300 font-mono text-[10px] border border-white/[0.08]">S</kbd> to solve, <kbd className="px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-300 font-mono text-[10px] border border-white/[0.08]">R</kbd> to revisit
            </span>
          </div>

          <ReviewProblemCard
            item={currentItem}
            onAction={handleAction}
            loading={updateStatusMutation.isPending}
          />
        </div>
      ) : (
        /* Empty / Finished State */
        <div className="glass-card rounded-3xl p-10 sm:p-14 text-center border border-white/[0.08] shadow-2xl">
          <div className="h-16 w-16 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-emerald-400 mb-4 shadow-[0_0_20px_rgba(16,185,129,0.25)]">
            <PartyPopper className="h-8 w-8" />
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">All Caught Up for Today!</h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto mb-6 leading-relaxed">
            You've reviewed every scheduled problem in your Leitner rotation. Consistent daily reviews are the scientific secret to coding interview confidence.
          </p>

          <div className="flex justify-center">
            <button
              onClick={onNavigateToProblems}
              className="btn-primary flex items-center gap-2 px-5 py-2.5"
            >
              <span>Explore Problem Bank</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Leitner Box System Distribution Grid */}
      <LeitnerBoxGrid stats={boxStats} />
    </div>
  );
}

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ExternalLink,
  Check,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  FileText,
  Clock,
  Sparkles,
  Code2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import TagBadge from '../common/TagBadge';
import TagToggle from '../common/TagToggle';
import BookmarkButton from '../common/BookmarkButton';
import EmptyState from '../common/EmptyState';
import { TableRowSkeleton } from '../common/SkeletonCard';
import { useTags } from '../../context/TagContext';

export default function ProblemsTable({
  problems = [],
  totalCount = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  onSelectProblem,
  onQuickUpdateStatus,
  onSolve,
  loading = false,
}) {
  const { showTags } = useTags();
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  const getDifficultyBadge = (difficulty) => {
    switch (difficulty) {
      case 'Easy':
        return <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-full badge-easy">Easy</span>;
      case 'Medium':
        return <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-full badge-medium">Medium</span>;
      case 'Hard':
        return <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-full badge-hard">Hard</span>;
      default:
        return <span className="px-2.5 py-0.5 text-[11px] rounded-full bg-slate-800 text-slate-400">{difficulty}</span>;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'SOLVED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Solved
          </span>
        );
      case 'NEEDS_REVISIT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
            Revisit
          </span>
        );
      case 'SKIPPED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-medium rounded-full bg-slate-800/80 text-slate-400 border border-slate-700/60">
            Skipped
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
            <Clock className="h-3 w-3" />
            Unsolved
          </span>
        );
    }
  };

  const getBoxBadge = (box, nextReview) => {
    if (!box) return <span className="text-xs text-slate-600">—</span>;
    const isDue = nextReview && new Date(nextReview) <= new Date();
    return (
      <div className="flex items-center gap-1.5">
        <span
          className={`px-2 py-0.5 text-xs font-bold rounded-lg border ${
            box === 5
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
              : box >= 3
              ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
              : 'bg-slate-800/80 text-slate-300 border-slate-700/60'
          }`}
        >
          Box {box}
        </span>
        {isDue && (
          <span
            className="h-2 w-2 rounded-full bg-rose-500 animate-ping"
            title="Due for Leitner review today!"
          />
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="glass-card rounded-2xl overflow-hidden border border-white/[0.07]">
        <table className="data-table">
          <thead>
            <tr>
              <th>Problem Title</th>
              <th>Difficulty</th>
              <th>Topics</th>
              <th className="hidden md:table-cell">Companies</th>
              <th>Leitner Box</th>
              <th className="hidden sm:table-cell">Solved</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 10 }).map((_, i) => (
              <TableRowSkeleton key={i} columns={8} />
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (problems.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-8 border border-white/[0.07]">
        <EmptyState
          preset="search"
          title="No problems found"
          body="Try adjusting your filters, tags, or search keywords to find what you're looking for."
        />
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-white/[0.07] flex flex-col justify-between shadow-glass">
      {/* Sub-header controls bar */}
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-white/[0.06] bg-black/20">
        <span className="text-xs font-medium text-slate-400">
          Showing <span className="text-white font-semibold">{(page - 1) * pageSize + 1}</span>–
          <span className="text-white font-semibold">{Math.min(page * pageSize, totalCount)}</span> of{' '}
          <span className="text-indigo-400 font-semibold">{totalCount}</span> problems
        </span>
        <TagToggle compact />
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Problem Title</th>
              <th>Difficulty</th>
              <th>Topics</th>
              <th className="hidden md:table-cell">Companies</th>
              <th>Leitner Box</th>
              <th className="hidden sm:table-cell">Solved</th>
              <th>Status</th>
              <th className="text-right pr-5">Actions</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {problems.map((prob) => {
                const progress = prob.user_progress;
                const status = progress?.status || 'UNSOLVED';
                const box = progress?.current_box;
                const nextReview = progress?.next_review_date;

                return (
                  <tr
                    key={prob.id}
                    onClick={() => onSelectProblem(prob)}
                    className="hover:bg-white/[0.03] transition-colors group cursor-pointer"
                  >
                    {/* Title */}
                    <td className="font-medium text-slate-100 py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-indigo-400 font-bold text-xs shrink-0">
                          #{prob.question_number || prob.leetcode_id}
                        </span>
                        <span className="group-hover:text-indigo-300 transition-colors font-semibold">
                          {prob.title}
                        </span>

                        {(prob.leetcode_url || prob.source_url) && (
                          <a
                            href={prob.leetcode_url || prob.source_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className={`p-1 rounded-lg transition-colors ${
                              prob.is_premium
                                ? 'text-amber-500/70 hover:text-amber-400'
                                : 'text-slate-500 hover:text-indigo-400'
                            }`}
                            title={prob.is_premium ? 'LeetCode Premium problem' : 'Open on LeetCode'}
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}

                        {prob.solution_api_url && (
                          <Link
                            to={`/problems/${prob.id}/solution`}
                            onClick={(e) => e.stopPropagation()}
                            className="p-1 rounded-lg transition-colors text-slate-500 hover:text-amber-400"
                            title="View Solution"
                          >
                            <FileText className="h-3.5 w-3.5" />
                          </Link>
                        )}

                        {prob.is_premium && (
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            title="LeetCode Premium only"
                          >
                            P
                          </span>
                        )}

                        <BookmarkButton
                          problemId={prob.id}
                          bookmarked={prob.is_bookmarked}
                          className="p-1 rounded-lg"
                        />
                      </div>
                    </td>

                    {/* Difficulty */}
                    <td className="whitespace-nowrap">
                      {getDifficultyBadge(prob.difficulty)}
                    </td>

                    {/* Topics */}
                    <td>
                      {showTags && prob.tags?.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {prob.tags.slice(0, 2).map((t) => (
                            <TagBadge key={t.id} name={t.name} color={t.color} compact />
                          ))}
                          {prob.tags.length > 2 && (
                            <span className="text-[10px] text-slate-500 self-center">
                              +{prob.tags.length - 2}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>

                    {/* Companies */}
                    <td className="hidden md:table-cell">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {prob.companies?.slice(0, 2).map((c) => (
                          <span
                            key={c.id}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-900/50"
                          >
                            {c.name}
                          </span>
                        ))}
                        {prob.companies?.length > 2 && (
                          <span className="text-[10px] text-slate-500 self-center">
                            +{prob.companies.length - 2}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Leitner Box */}
                    <td className="whitespace-nowrap">
                      {getBoxBadge(box, nextReview)}
                    </td>

                    {/* Solved Count */}
                    <td className="whitespace-nowrap hidden sm:table-cell text-xs text-slate-400">
                      {progress?.times_solved ? `${progress.times_solved}×` : '0×'}
                    </td>

                    {/* Status Badge */}
                    <td className="whitespace-nowrap">
                      {getStatusBadge(status)}
                    </td>

                    {/* Inline Action Buttons */}
                    <td
                      className="text-right pr-5 whitespace-nowrap"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        {onSolve && (
                          <motion.button
                            whileTap={{ scale: 0.88 }}
                            onClick={() => onSolve(prob.id)}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/25 transition-all"
                            title="Solve in Online Judge"
                          >
                            <Code2 className="h-3.5 w-3.5" />
                            <span>Solve</span>
                          </motion.button>
                        )}
                        <motion.button
                          whileTap={{ scale: 0.88 }}
                          onClick={() => onQuickUpdateStatus(prob.id, 'SOLVED', status)}
                          className={`p-1.5 rounded-lg transition-all ${
                            status === 'SOLVED'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10'
                          }`}
                          title={status === 'SOLVED' ? 'Unmark Solved' : 'Mark Solved (Advance Box)'}
                        >
                          <Check className="h-4 w-4" />
                        </motion.button>
                        <motion.button
                          whileTap={{ scale: 0.88 }}
                          onClick={() => onQuickUpdateStatus(prob.id, 'NEEDS_REVISIT', status)}
                          className={`p-1.5 rounded-lg transition-all ${
                            status === 'NEEDS_REVISIT'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'text-slate-400 hover:text-rose-400 hover:bg-rose-500/10'
                          }`}
                          title={
                            status === 'NEEDS_REVISIT'
                              ? 'Unmark Needs Revisit'
                              : 'Mark Needs Revisit (Reset Box)'
                          }
                        >
                          <RotateCcw className="h-4 w-4" />
                        </motion.button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.06] bg-black/20 text-xs text-slate-400">
        <div>
          Page <span className="text-white font-semibold">{page}</span> of{' '}
          <span className="text-white font-semibold">{totalPages}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.04] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="px-2 font-medium text-slate-300">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.04] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

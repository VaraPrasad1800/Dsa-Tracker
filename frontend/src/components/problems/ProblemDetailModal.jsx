import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  ExternalLink,
  CheckCircle2,
  RotateCcw,
  MinusCircle,
  Clock,
  FileText,
  Code,
  History,
  Save,
  Play,
  Pause,
  RotateCw,
  Sparkles,
  Link as LinkIcon,
  Tag as TagIcon,
  Building2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { progressApi } from '../../api/client';
import CodeEditor from './CodeEditor';
import TagBadge from '../common/TagBadge';
import BookmarkButton from '../common/BookmarkButton';
import { useTags } from '../../context/TagContext';

export default function ProblemDetailModal({ problem, onClose, onSaveProgress }) {
  const [status, setStatus] = useState('UNSOLVED');
  const [notes, setNotes] = useState('');
  const [codeSolution, setCodeSolution] = useState('');
  const [codeLanguage, setCodeLanguage] = useState('python');
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [timerRunning, setTimerRunning] = useState(false);
  const timerTickRef = useRef(Date.now());
  const [activeSubTab, setActiveSubTab] = useState('notes'); // 'notes' | 'history' | 'related'
  const [historyData, setHistoryData] = useState(null);
  const [saving, setSaving] = useState(false);
  const { showTags } = useTags();

  useEffect(() => {
    if (problem) {
      const p = problem.user_progress;
      setStatus(p?.status || 'UNSOLVED');
      setNotes(p?.notes || '');
      setCodeSolution(p?.code_solution || '');
      setTimerSeconds(0);
      setTimerRunning(false);

      if (p?.id) {
        progressApi
          .getHistory(p.id)
          .then((res) => setHistoryData(res.data))
          .catch((err) => console.error('Failed to load history:', err));
      } else {
        setHistoryData(null);
      }
    }
  }, [problem]);

  // Stopwatch timer interval
  useEffect(() => {
    if (!timerRunning) return;
    timerTickRef.current = Date.now();
    const interval = setInterval(() => {
      const now = Date.now();
      setTimerSeconds((s) => s + Math.floor((now - timerTickRef.current) / 1000));
      timerTickRef.current = now;
    }, 1000);
    return () => clearInterval(interval);
  }, [timerRunning]);

  // Keyboard shortcut listener: S = Solved, R = Revisit, Esc = Close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        handleUpdateStatus('SOLVED');
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        handleUpdateStatus('NEEDS_REVISIT');
      } else if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [problem, notes, codeSolution, timerSeconds]);

  if (!problem) return null;

  const timeSpentMinutes = timerSeconds > 0 ? Math.max(1, Math.round(timerSeconds / 60)) : 0;

  const formatTimer = () => {
    const m = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
    const s = String(timerSeconds % 60).padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleUpdateStatus = async (newStatus) => {
    setSaving(true);
    setStatus(newStatus);
    await onSaveProgress({
      problem_id: problem.id,
      status: newStatus,
      notes,
      code_solution: codeSolution,
      time_spent_minutes: timeSpentMinutes,
    });
    setSaving(false);
  };

  const handleSaveNotesAndCode = async () => {
    setSaving(true);
    await onSaveProgress({
      problem_id: problem.id,
      status,
      notes,
      code_solution: codeSolution,
      code_language: codeLanguage,
      time_spent_minutes: timeSpentMinutes,
    });
    setSaving(false);
  };

  const progress = problem.user_progress;
  const currentBox = progress?.current_box || 1;
  const nextReview = progress?.next_review_date;

  const getDiffBadgeClass = (diff) => {
    if (diff === 'Easy') return 'badge-easy';
    if (diff === 'Medium') return 'badge-medium';
    return 'badge-hard';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-4xl glass-modal rounded-3xl border border-white/[0.08] shadow-2xl overflow-hidden my-4 max-h-[92vh] flex flex-col"
      >
        {/* Modal Header */}
        <div className="p-5 sm:p-6 border-b border-white/[0.07] flex items-start justify-between gap-4 bg-black/30 sticky top-0 z-10">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${getDiffBadgeClass(problem.difficulty)}`}>
                {problem.difficulty}
              </span>
              <span className="text-xs text-slate-400">• {problem.source_platform}</span>
              {progress && (
                <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
                  Leitner Box {currentBox}
                </span>
              )}
            </div>

            <h2 className="text-lg sm:text-xl font-bold text-white flex flex-wrap items-center gap-2 leading-snug">
              <span>{problem.leetcode_id ? `${problem.leetcode_id}. ` : ''}{problem.title}</span>

              {(problem.leetcode_url || problem.source_url) && (
                <a
                  href={problem.leetcode_url || problem.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className={`inline-flex items-center gap-1 text-xs font-normal transition-colors ${
                    problem.is_premium
                      ? 'text-amber-400 hover:text-amber-300'
                      : 'text-slate-400 hover:text-indigo-400'
                  }`}
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  {problem.is_premium ? 'LeetCode Premium' : 'LeetCode'}
                </a>
              )}

              {problem.solution_api_url && (
                <Link
                  to={`/problems/${problem.id}/solution`}
                  className="inline-flex items-center gap-1 text-xs font-normal transition text-indigo-400 hover:text-indigo-300"
                >
                  <FileText className="h-3.5 w-3.5" />
                  Solution Guide
                </Link>
              )}
            </h2>

            {/* Tags & Companies */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {showTags && problem.tags?.map((t) => (
                <TagBadge key={t.id} name={t.name} color={t.color} compact />
              ))}
              {problem.companies?.map((c) => (
                <span
                  key={c.id}
                  className="text-[10px] px-2 py-0.5 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-900/50"
                >
                  {c.name}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <BookmarkButton
              problemId={problem.id}
              bookmarked={problem.is_bookmarked}
              className="p-1.5 rounded-xl text-slate-400 hover:bg-white/5"
            />
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6 flex-1">
          {/* Quick Actions Panel */}
          <div className="glass-card rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 border border-white/[0.06]">
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Leitner Status & Consistency
              </div>
              <div className="text-sm text-slate-200 flex flex-wrap items-center gap-3">
                <span>
                  Status: <strong className="text-white">{status}</strong>
                </span>
                <span>
                  Times Solved: <strong className="text-indigo-400">{progress?.times_solved || 0}</strong>
                </span>
                {nextReview && (
                  <span className="text-xs text-indigo-400 flex items-center gap-1">
                    <Clock className="h-3 w-3" /> Next review: {new Date(nextReview).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>

            {/* Status Buttons */}
            <div className="flex items-center gap-2">
              <motion.button
                whileTap={{ scale: 0.94 }}
                onClick={() => handleUpdateStatus(status === 'SOLVED' ? 'UNSOLVED' : 'SOLVED')}
                disabled={saving}
                className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold rounded-xl transition-all ${
                  status === 'SOLVED'
                    ? 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    : 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-[0_0_12px_rgba(16,185,129,0.3)]'
                }`}
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{status === 'SOLVED' ? 'Unmark Solved' : 'Mark Solved'}</span>
                <kbd className="ml-1 px-1 bg-black/20 rounded text-[10px]">S</kbd>
              </motion.button>

              <motion.button
                whileTap={{ scale: 0.94 }}
                onClick={() => handleUpdateStatus(status === 'NEEDS_REVISIT' ? 'UNSOLVED' : 'NEEDS_REVISIT')}
                disabled={saving}
                className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold rounded-xl transition-all ${
                  status === 'NEEDS_REVISIT'
                    ? 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    : 'bg-gradient-to-r from-rose-500 to-pink-500 text-white shadow-[0_0_12px_rgba(244,63,94,0.3)]'
                }`}
              >
                <RotateCcw className="h-4 w-4" />
                <span>{status === 'NEEDS_REVISIT' ? 'Unmark Revisit' : 'Needs Revisit'}</span>
                <kbd className="ml-1 px-1 bg-black/20 rounded text-[10px]">R</kbd>
              </motion.button>

              <button
                onClick={() => handleUpdateStatus('SKIPPED')}
                disabled={saving}
                className="flex items-center gap-1 px-3 py-2 bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs font-medium rounded-xl transition-colors border border-white/[0.05]"
              >
                <MinusCircle className="h-3.5 w-3.5" />
                <span>Skip</span>
              </button>
            </div>
          </div>

          {/* Stopwatch Timer */}
          <div className="glass-card rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 border border-white/[0.06]">
            <div className="flex items-center gap-3">
              <div
                className={`p-2.5 rounded-xl border ${
                  timerRunning
                    ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                    : 'bg-white/[0.03] border-white/[0.06] text-slate-400'
                }`}
              >
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">
                  Practice Stopwatch
                </div>
                <div className="font-mono text-2xl font-extrabold text-white tabular-nums flex items-center gap-2">
                  <span>{formatTimer()}</span>
                  {timerRunning && (
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setTimerRunning((r) => !r)}
                className={`flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
                  timerRunning
                    ? 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                    : 'btn-primary'
                }`}
              >
                {timerRunning ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                <span>{timerRunning ? 'Pause' : 'Start Timer'}</span>
              </button>

              <button
                onClick={() => {
                  setTimerRunning(false);
                  setTimerSeconds(0);
                }}
                className="flex items-center gap-1.5 px-3 py-2 bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs font-medium rounded-xl transition border border-white/[0.05]"
                title="Reset timer"
              >
                <RotateCw className="h-3.5 w-3.5" />
                <span>Reset</span>
              </button>
            </div>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-white/[0.07] pb-2">
            <button
              onClick={() => setActiveSubTab('notes')}
              className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all ${
                activeSubTab === 'notes'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileText className="h-3.5 w-3.5" /> Solution Notes & Code
            </button>

            <button
              onClick={() => setActiveSubTab('related')}
              className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all ${
                activeSubTab === 'related'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" /> Related Patterns
            </button>

            <button
              onClick={() => setActiveSubTab('history')}
              className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all ${
                activeSubTab === 'history'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <History className="h-3.5 w-3.5" /> Review Transitions
            </button>
          </div>

          {/* Sub Tab: Notes & Code */}
          {activeSubTab === 'notes' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                  <span>Approach, Time & Space Complexity, Mistakes Made</span>
                  <span className="text-[11px] text-slate-500 font-mono">markdown supported</span>
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Record key intuition, edge cases (e.g. empty array, duplicates), and time complexity O(N log N)..."
                  rows={4}
                  className="w-full bg-black/40 border border-white/[0.08] rounded-2xl p-3.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                  <Code className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Code Solution Snippet</span>
                </label>
                <CodeEditor
                  value={codeSolution}
                  onChange={setCodeSolution}
                  language={codeLanguage}
                  onLanguageChange={setCodeLanguage}
                  placeholder="# Paste clean optimal solution implementation..."
                  readOnly={false}
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={handleSaveNotesAndCode}
                  disabled={saving}
                  className="btn-primary"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{saving ? 'Saving...' : 'Save Notes & Code'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Sub Tab: Related Patterns */}
          {activeSubTab === 'related' && (
            <div className="space-y-3">
              <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 leading-relaxed">
                <p className="font-semibold mb-1 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> Algorithmic Pattern Association
                </p>
                Problems sharing tags (
                {problem.tags?.map((t) => t.name).join(', ') || 'General DSA'}
                ) will test similar invariant structures and pointers.
              </div>

              {problem.tags?.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {problem.tags.map((tag) => (
                    <div
                      key={tag.id}
                      className="p-3.5 rounded-xl glass-card border border-white/[0.06] flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <TagIcon className="h-3.5 w-3.5 text-indigo-400" />
                        <span className="text-xs font-semibold text-slate-200">{tag.name}</span>
                      </div>
                      <span className="text-[11px] text-slate-500">
                        {tag.problem_count || 0} curated problems
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No related patterns categorized for this problem yet.
                </div>
              )}
            </div>
          )}

          {/* Sub Tab: History */}
          {activeSubTab === 'history' && (
            <div className="space-y-3">
              {historyData && historyData.box_transitions?.length > 0 ? (
                <div className="space-y-2">
                  {historyData.box_transitions.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3.5 rounded-xl glass-card border border-white/[0.06] text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <span
                          className={`px-2.5 py-0.5 rounded-full font-bold ${
                            item.action === 'SOLVED'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {item.action}
                        </span>
                        <span className="text-slate-300">
                          Transition: <strong>Box {item.old_box}</strong> →{' '}
                          <strong className="text-indigo-400">Box {item.new_box}</strong>
                        </span>
                      </div>
                      <span className="text-slate-500 font-mono">{item.date}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No review transitions recorded yet for this problem.
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

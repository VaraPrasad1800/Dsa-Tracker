import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Trophy,
  Clock,
  Plus,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Timer,
  Target,
  Zap,
  Award,
  Search,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { challengesApi, pointsApi, problemsApi } from '../api/client';

export default function ChallengesPage({ onSolve }) {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New challenge form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('CUSTOM');
  const [targetCount, setTargetCount] = useState(3);
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [selectedProblemIds, setSelectedProblemIds] = useState([]);
  const [problemSearch, setProblemSearch] = useState('');

  // Fetch problems for challenge problem picker
  const { data: pickerProblemsData } = useQuery({
    queryKey: ['challenge_picker_problems', problemSearch],
    queryFn: async () => {
      const params = { page_size: 25, sort: 'question_number' };
      if (problemSearch.trim()) params.search = problemSearch.trim();
      const res = await problemsApi.getProblems(params);
      return res.data;
    },
    enabled: showCreateModal,
  });
  const pickerProblems = pickerProblemsData?.results || [];

  // Fetch challenges
  const { data, isLoading } = useQuery({
    queryKey: ['challenges'],
    queryFn: async () => {
      const res = await challengesApi.getChallenges();
      return res.data;
    },
    refetchInterval: 15000, // auto-refresh active challenges
  });

  // Fetch points summary
  const { data: userPoints } = useQuery({
    queryKey: ['points'],
    queryFn: async () => {
      const res = await pointsApi.getPoints();
      return res.data;
    },
  });

  // Create Challenge Mutation
  const createMutation = useMutation({
    mutationFn: (payload) => challengesApi.createChallenge(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['challenges'] });
      setShowCreateModal(false);
      setTitle('');
      setDescription('');
      setSelectedProblemIds([]);
      setProblemSearch('');
      toast.success('Challenge created! Timer started.');
    },
    onError: (err) => {
      toast.error(err.response?.data?.error || 'Failed to create challenge');
    },
  });

  // Finalize / Complete Mutation
  const completeMutation = useMutation({
    mutationFn: (id) => challengesApi.completeChallenge(id),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['challenges'] });
      queryClient.invalidateQueries({ queryKey: ['points'] });
      toast.success(`Challenge finalized! Earned ${res.data.points_earned || 0} pts`);
    },
  });

  // Cancel Mutation
  const cancelMutation = useMutation({
    mutationFn: (id) => challengesApi.cancelChallenge(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['challenges'] });
      toast.success('Challenge cancelled');
    },
  });

  const handleCreate = (e) => {
    e.preventDefault();
    if (!title.trim()) {
      toast.error('Please enter a challenge title');
      return;
    }
    createMutation.mutate({
      title,
      description,
      template,
      target_count: selectedProblemIds.length > 0 ? selectedProblemIds.length : Number(targetCount),
      duration_minutes: Number(durationMinutes),
      difficulty_filter: difficultyFilter,
      problem_ids: selectedProblemIds,
    });
  };

  const activeChallenges = data?.active || [];
  const historyChallenges = data?.history || [];

  const formatRemaining = (seconds) => {
    if (!seconds || seconds <= 0) return 'Ended';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m remaining`;
    return `${mins}m ${secs}s remaining`;
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header & Points Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 backdrop-blur-md p-6 rounded-3xl border border-white/[0.08]">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <Trophy className="h-6 w-6 text-amber-400" />
            DSA Challenges & Targets
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Set specific targets and deadlines to earn bonus points and level up.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {userPoints && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 font-semibold text-sm">
              <Zap className="h-4 w-4" />
              <span>{userPoints.total} Points</span>
              <span className="text-xs text-slate-400 font-normal">({userPoints.challenge_points} from challenges)</span>
            </div>
          )}

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-gradient-to-r from-indigo-500 to-violet-600 text-white font-bold text-sm shadow-lg shadow-indigo-500/25 hover:brightness-110 transition"
          >
            <Plus className="h-4 w-4" />
            New Challenge
          </button>
        </div>
      </div>

      {/* Active Challenges */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Timer className="h-5 w-5 text-indigo-400" />
          Active Challenges ({activeChallenges.length})
        </h2>

        {isLoading ? (
          <div className="text-slate-500 text-sm">Loading challenges...</div>
        ) : activeChallenges.length === 0 ? (
          <div className="bg-slate-900/40 rounded-2xl p-8 border border-white/[0.06] text-center space-y-3">
            <Target className="h-10 w-10 text-slate-600 mx-auto" />
            <div className="text-slate-300 font-medium">No active challenges right now</div>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Create a challenge to push your skills, earn bonus points, and prepare for interviews under time pressure.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-indigo-400 text-xs font-semibold border border-white/10 transition"
            >
              Create your first challenge
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeChallenges.map((ch) => {
              const pct = Math.min(100, Math.round((ch.completed_count / ch.target_count) * 100));
              return (
                <div
                  key={ch.id}
                  className="bg-slate-900/60 backdrop-blur-md rounded-2xl p-5 border border-white/[0.08] flex flex-col justify-between gap-4"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-white text-base leading-snug">{ch.title}</h3>
                      <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-wider border border-indigo-500/30 shrink-0">
                        {ch.template}
                      </span>
                    </div>

                    {ch.description && (
                      <p className="text-xs text-slate-400 line-clamp-2">{ch.description}</p>
                    )}

                    <div className="flex items-center gap-3 text-xs text-slate-400 pt-1">
                      <span className="flex items-center gap-1 text-amber-400 font-semibold">
                        <Award className="h-3.5 w-3.5" />
                        +{ch.points + ch.bonus_points} pts
                      </span>
                      <span className="flex items-center gap-1 text-slate-300">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        {formatRemaining(ch.time_remaining_seconds)}
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="space-y-1.5 pt-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Progress</span>
                      <span className="font-semibold text-slate-200">
                        {ch.completed_count} / {ch.target_count} solved ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500 rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  {/* Challenge Problems List if explicitly assigned */}
                  {ch.problems && ch.problems.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[11px] font-medium text-slate-400">Assigned Problems:</span>
                      <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
                        {ch.problems.map((cp) => (
                          <button
                            type="button"
                            key={cp.id}
                            onClick={() => onSolve && onSolve(cp.problem || cp.problem_id)}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border transition cursor-pointer ${
                              cp.is_completed
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 line-through'
                                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border-white/[0.06]'
                            }`}
                            title="View and practice problem"
                          >
                            <span className="text-indigo-400 font-mono font-bold">
                              #{cp.question_number || '—'}
                            </span>
                            <span className="truncate max-w-[140px]">{cp.problem_title}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
                    <button
                      onClick={() => completeMutation.mutate(ch.id)}
                      disabled={completeMutation.isPending}
                      className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Finalize / Claim
                    </button>
                    <button
                      onClick={() => cancelMutation.mutate(ch.id)}
                      disabled={cancelMutation.isPending}
                      className="text-xs font-medium text-slate-500 hover:text-rose-400 transition"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Challenge History */}
      {historyChallenges.length > 0 && (
        <div className="space-y-4 pt-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            Challenge History
          </h2>

          <div className="bg-slate-900/60 rounded-2xl border border-white/[0.08] overflow-hidden">
            <div className="divide-y divide-white/[0.06]">
              {historyChallenges.map((ch) => (
                <div key={ch.id} className="p-4 flex items-center justify-between gap-4 text-xs">
                  <div>
                    <div className="font-semibold text-slate-200 text-sm">{ch.title}</div>
                    <div className="text-slate-500 text-[11px] mt-0.5">
                      {ch.completed_count} / {ch.target_count} solved • {new Date(ch.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <span
                      className={`px-2.5 py-1 rounded-full font-bold text-[10px] uppercase tracking-wider ${
                        ch.status === 'COMPLETED'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {ch.status}
                    </span>
                    <span className="font-semibold text-amber-400">
                      +{ch.points_earned} pts
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-white/10 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Target className="h-5 w-5 text-indigo-400" />
                Create New Challenge
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Challenge Title *
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Solve 3 Medium Problems in 1 Hour"
                  className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional goal notes..."
                  rows={2}
                  className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Target Problems
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={targetCount}
                    onChange={(e) => setTargetCount(e.target.value)}
                    className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Duration (Minutes)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="10080"
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(e.target.value)}
                    className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Template
                  </label>
                  <select
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    className="w-full bg-slate-950 px-3 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
                  >
                    <option value="CUSTOM">Custom Target</option>
                    <option value="TIMED">Timed Speedrun</option>
                    <option value="DIFFICULTY">Difficulty Focused</option>
                    <option value="REVIEW">SRS Review Challenge</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Difficulty Filter
                  </label>
                  <select
                    value={difficultyFilter}
                    onChange={(e) => setDifficultyFilter(e.target.value)}
                    className="w-full bg-slate-950 px-3 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
                  >
                    <option value="">Any Difficulty</option>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              {/* Optional Problem Selection with #question_number */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center justify-between">
                  <span>Assign Specific Problems (Optional)</span>
                  {selectedProblemIds.length > 0 && (
                    <span className="text-indigo-400 font-bold">{selectedProblemIds.length} selected</span>
                  )}
                </label>
                <div className="relative mb-2">
                  <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={problemSearch}
                    onChange={(e) => setProblemSearch(e.target.value)}
                    placeholder="Search by question # or title..."
                    className="w-full bg-slate-950 pl-8 pr-3.5 py-2 rounded-xl border border-white/10 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="max-h-36 overflow-y-auto border border-white/10 rounded-xl bg-slate-950/60 divide-y divide-white/[0.05]">
                  {pickerProblems.length === 0 ? (
                    <div className="p-3 text-center text-xs text-slate-500">No problems found</div>
                  ) : (
                    pickerProblems.slice(0, 15).map((p) => {
                      const isSelected = selectedProblemIds.includes(p.id);
                      return (
                        <div
                          key={p.id}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedProblemIds(selectedProblemIds.filter((id) => id !== p.id));
                            } else {
                              setSelectedProblemIds([...selectedProblemIds, p.id]);
                            }
                          }}
                          className={`p-2 px-3 text-xs flex items-center justify-between cursor-pointer transition ${
                            isSelected ? 'bg-indigo-600/20 text-indigo-200' : 'hover:bg-white/[0.04] text-slate-300'
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate mr-2">
                            <span className="font-mono font-bold text-indigo-400">
                              #{p.question_number || '—'}
                            </span>
                            <span className="truncate">{p.title}</span>
                          </div>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0 ${
                            p.difficulty === 'Hard' ? 'text-rose-400 bg-rose-500/10' :
                            p.difficulty === 'Medium' ? 'text-amber-400 bg-amber-500/10' :
                            'text-emerald-400 bg-emerald-500/10'
                          }`}>
                            {p.difficulty}
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 text-white font-bold text-xs shadow-lg shadow-indigo-500/25 hover:brightness-110 transition disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Start Challenge'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

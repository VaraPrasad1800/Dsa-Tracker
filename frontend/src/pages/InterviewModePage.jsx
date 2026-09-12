import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Video,
  Timer,
  Play,
  CheckCircle2,
  XCircle,
  Award,
  AlertTriangle,
  Building2,
  Code2,
  ArrowRight,
  ListOrdered,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { interviewApi, problemsApi } from '../api/client';

export default function InterviewModePage({ onNavigateToProblem }) {
  const queryClient = useQueryClient();

  // New session configuration
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [numProblems, setNumProblems] = useState(2);
  const [difficulty, setDifficulty] = useState('Medium');
  const [companyId, setCompanyId] = useState('');

  // Active session tracking
  const [activeSession, setActiveSession] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);

  // Fetch companies for dropdown
  const { data: companiesData } = useQuery({
    queryKey: ['companies_list'],
    queryFn: async () => {
      const res = await problemsApi.getCompanies();
      return res.data;
    },
  });

  // Fetch past interview sessions
  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['interview_sessions'],
    queryFn: async () => {
      const res = await interviewApi.getSessions();
      return res.data;
    },
  });

  const companies = companiesData || [];
  const pastSessions = sessionsData?.sessions || [];

  // Find active session on load
  useEffect(() => {
    const active = pastSessions.find((s) => s.status === 'ACTIVE');
    if (active) {
      setActiveSession(active);
      const deadline = new Date(active.deadline).getTime();
      const now = new Date().getTime();
      setRemainingSeconds(Math.max(0, Math.floor((deadline - now) / 1000)));
    }
  }, [pastSessions]);

  // Live timer tick
  useEffect(() => {
    if (!activeSession || remainingSeconds <= 0) return;
    const interval = setInterval(() => {
      setRemainingSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [activeSession, remainingSeconds]);

  // Start Session Mutation
  const startMutation = useMutation({
    mutationFn: (payload) => interviewApi.startSession(payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['interview_sessions'] });
      setActiveSession(res.data);
      setRemainingSeconds(res.data.duration_minutes * 60);
      toast.success('Interview simulation started! Good luck.');
    },
    onError: (err) => {
      toast.error(err.response?.data?.error || 'Failed to start simulation');
    },
  });

  // End Session Mutation
  const endMutation = useMutation({
    mutationFn: (id) => interviewApi.endSession(id),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['interview_sessions'] });
      queryClient.invalidateQueries({ queryKey: ['points'] });
      setActiveSession(null);
      toast.success(`Simulation completed! Score: ${res.data.score} pts`);
    },
  });

  const handleStart = (e) => {
    e.preventDefault();
    startMutation.mutate({
      duration_minutes: Number(durationMinutes),
      num_problems: Number(numProblems),
      difficulty,
      company_id: companyId || null,
    });
  };

  const formatTimer = (sec) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/60 backdrop-blur-md p-6 rounded-3xl border border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <Video className="h-6 w-6 text-indigo-400" />
            Interview Simulation Mode
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Simulate realistic timed coding interviews under strict time pressure.
          </p>
        </div>

        {activeSession && (
          <div className="flex items-center gap-4 bg-slate-950 px-5 py-3 rounded-2xl border border-white/10">
            <div className="text-right">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                Time Remaining
              </div>
              <div className="text-xl font-mono font-bold text-rose-400">
                {formatTimer(remainingSeconds)}
              </div>
            </div>

            <button
              onClick={() => endMutation.mutate(activeSession.id)}
              disabled={endMutation.isPending}
              className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs shadow-lg shadow-rose-500/20 transition"
            >
              End Interview
            </button>
          </div>
        )}
      </div>

      {/* Active Session View */}
      {activeSession ? (
        <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl p-6 border border-white/[0.08] space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Code2 className="h-5 w-5 text-indigo-400" />
              Interview Problems ({activeSession.interview_problems?.length})
            </h2>
            <div className="text-xs text-slate-400">
              Target Difficulty: <span className="font-semibold text-slate-200">{activeSession.difficulty}</span>
              {activeSession.company_name && (
                <span className="ml-3">Company: <span className="font-semibold text-indigo-400">{activeSession.company_name}</span></span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeSession.interview_problems?.map((ip, index) => (
              <div
                key={ip.id}
                className="p-5 rounded-2xl bg-slate-950/60 border border-white/[0.06] flex flex-col justify-between gap-4"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono text-slate-500">Problem #{index + 1}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        ip.solved
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}
                    >
                      {ip.solved ? 'Solved ✓' : 'Unsolved'}
                    </span>
                  </div>
                  <h3 className="font-bold text-white text-base mt-2 flex items-center gap-2">
                    {ip.question_number && (
                      <span className="font-mono text-indigo-400 font-bold">
                        #{ip.question_number}
                      </span>
                    )}
                    <span>{ip.problem_title}</span>
                  </h3>
                  <div className="text-xs text-slate-400 mt-1">
                    Difficulty: <span className="text-slate-300 font-medium">{ip.problem_difficulty}</span>
                  </div>
                </div>

                <button
                  onClick={() => onNavigateToProblem && onNavigateToProblem(ip.problem)}
                  className="w-full py-2.5 rounded-xl bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 text-xs font-bold border border-indigo-500/30 flex items-center justify-center gap-1.5 transition"
                >
                  <span>Solve in Online Judge</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Configuration Form to Start Interview */
        <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl p-6 border border-white/[0.08] space-y-6">
          <div>
            <h2 className="text-lg font-bold text-white">Start New Interview Simulation</h2>
            <p className="text-xs text-slate-400 mt-1">
              Select interview length, problem difficulty, and company target to begin a timed round.
            </p>
          </div>

          <form onSubmit={handleStart} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Duration (Minutes)
              </label>
              <select
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(e.target.value)}
                className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
              >
                <option value={30}>30 Minutes (Speedrun)</option>
                <option value={45}>45 Minutes (Standard Technical)</option>
                <option value={60}>60 Minutes (Full Round)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Number of Problems
              </label>
              <select
                value={numProblems}
                onChange={(e) => setNumProblems(e.target.value)}
                className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
              >
                <option value={1}>1 Problem</option>
                <option value={2}>2 Problems (Recommended)</option>
                <option value={3}>3 Problems</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
              >
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
                <option value="Mixed">Mixed (Realistic)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Target Company
              </label>
              <select
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                className="w-full bg-slate-950 px-3.5 py-2.5 rounded-xl border border-white/10 text-white text-xs focus:outline-none"
              >
                <option value="">Any / General</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-4 pt-2">
              <button
                type="submit"
                disabled={startMutation.isPending}
                className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-violet-600 text-white font-bold text-sm shadow-xl shadow-indigo-500/25 hover:brightness-110 transition disabled:opacity-50"
              >
                <Play className="h-4 w-4 fill-white" />
                <span>{startMutation.isPending ? 'Preparing Session...' : 'Start Interview Simulation'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Past Sessions History */}
      {pastSessions.length > 0 && (
        <div className="space-y-4 pt-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ListOrdered className="h-5 w-5 text-slate-400" />
            Past Simulation Rounds
          </h2>

          <div className="bg-slate-900/60 rounded-3xl border border-white/[0.08] overflow-hidden">
            <div className="divide-y divide-white/[0.06]">
              {pastSessions.map((s) => (
                <div key={s.id} className="p-4 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-slate-200 text-sm">
                      {s.difficulty} Round • {s.duration_minutes} mins
                      {s.company_name && <span className="text-indigo-400 ml-2">({s.company_name})</span>}
                    </div>
                    <div className="text-slate-500 text-[11px] mt-0.5">
                      Solved {s.problems_solved} / {s.num_problems} problems • {new Date(s.started_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <span
                      className={`px-2.5 py-1 rounded-full font-bold text-[10px] uppercase tracking-wider ${
                        s.status === 'COMPLETED'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {s.status}
                    </span>
                    <span className="font-semibold text-amber-400">+{s.score} pts</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

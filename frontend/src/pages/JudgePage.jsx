import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  RotateCcw,
  Terminal,
  History,
  FileText,
  BookOpen,
  Eye,
  X,
  Copy,
  AlertTriangle,
  ExternalLink,
  LayoutGrid,
  Loader2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import MonacoCodeEditor from '../components/judge/CodeEditor';
import ProblemSelector from '../components/judge/ProblemSelector';
import ProblemStatement from '../components/judge/ProblemStatement';
import SolutionViewer from '../components/judge/SolutionViewer';
import ResizableDivider from '../components/judge/ResizableDivider';
import { problemsApi, judgeApi } from '../api/client';

const LAYOUT_STORAGE_KEY = 'dsa_judge_split_layout_v1';
const DEFAULT_LAYOUT = {
  leftWidthPercent: 42,
  editorHeightPercent: 60,
};

const getFallbackTemplate = (problem, language) => {
  if (problem && !problem.is_judge_ready) {
    const isCStyle = ['c', 'cpp', 'java'].includes(language);
    const comment = isCStyle ? '//' : '#';
    return `${comment} Online Judge configuration unavailable for #${problem.question_number || ''} ${problem.title || ''}.\n${comment} Test cases and execution harness are not yet configured for this problem.\n${comment} Please refer to the problem statement or practice on LeetCode.`;
  }
  return DEFAULT_TEMPLATES[language] || '';
};

const DEFAULT_TEMPLATES = {
  python: `# Write your solution below
import sys

def solve():
    lines = sys.stdin.read().split()
    if not lines:
        return
    # TODO: Write code

if __name__ == '__main__':
    solve()
`,
  cpp: `#include <iostream>
using namespace std;

int main() {
    // TODO: Write code
    return 0;
}
`,
  c: `#include <stdio.h>

int main() {
    // TODO: Write code
    return 0;
}
`,
  java: `import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // TODO: Write code
    }
}
`,
};

export default function JudgePage({ initialProblemId }) {
  const queryClient = useQueryClient();

  // Problem selection state
  const [selectedProblemId, setSelectedProblemId] = useState(initialProblemId || '');
  const [selectedLanguage, setSelectedLanguage] = useState('python');
  const [code, setCode] = useState('');
  const [customStdin, setCustomStdin] = useState('');

  // Per-(problem, language) code cache to prevent overwriting user progress
  const [codeCache, setCodeCache] = useState({});

  // Navigation tabs
  const [activeLeftTab, setActiveLeftTab] = useState('description'); // 'description' | 'editorial'
  const [activeBottomTab, setActiveBottomTab] = useState('testcases'); // 'testcases' | 'result' | 'history' | 'custom_input'

  // Run/Submit results & submission viewer
  const [runResult, setRunResult] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);
  const [viewingSubmission, setViewingSubmission] = useState(null);
  const [viewingLoading, setViewingLoading] = useState(false);
  const [pollingSubmissionId, setPollingSubmissionId] = useState(null);
  const [pollingStartTime, setPollingStartTime] = useState(null);

  // Split layout container refs & state
  const containerRef = useRef(null);
  const rightPaneRef = useRef(null);

  const [layout, setLayout] = useState(() => {
    try {
      const saved = localStorage.getItem(LAYOUT_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.leftWidthPercent === 'number' && typeof parsed.editorHeightPercent === 'number') {
          return {
            leftWidthPercent: Math.min(Math.max(parsed.leftWidthPercent, 20), 75),
            editorHeightPercent: Math.min(Math.max(parsed.editorHeightPercent, 25), 80),
          };
        }
      }
    } catch (e) {}
    return DEFAULT_LAYOUT;
  });

  const [isDraggingH, setIsDraggingH] = useState(false);
  const [isDraggingV, setIsDraggingV] = useState(false);
  const [isDesktop, setIsDesktop] = useState(typeof window !== 'undefined' ? window.innerWidth >= 1024 : true);

  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout));
    } catch (e) {}
  }, [layout]);

  // Horizontal drag handler: Left vs Right panes
  useEffect(() => {
    if (!isDraggingH) return;

    const handleMouseMove = (e) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const offsetX = clientX - rect.left;
      let newPercent = (offsetX / rect.width) * 100;
      newPercent = Math.min(Math.max(newPercent, 20), 75);
      setLayout((prev) => ({ ...prev, leftWidthPercent: newPercent }));
    };

    const handleMouseUp = () => {
      setIsDraggingH(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleMouseMove);
    window.addEventListener('touchend', handleMouseUp);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleMouseMove);
      window.removeEventListener('touchend', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDraggingH]);

  // Vertical drag handler: Editor vs Bottom Console
  useEffect(() => {
    if (!isDraggingV) return;

    const handleMouseMove = (e) => {
      if (!rightPaneRef.current) return;
      const rect = rightPaneRef.current.getBoundingClientRect();
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const offsetY = clientY - rect.top;
      let newPercent = (offsetY / rect.height) * 100;
      newPercent = Math.min(Math.max(newPercent, 25), 80);
      setLayout((prev) => ({ ...prev, editorHeightPercent: newPercent }));
    };

    const handleMouseUp = () => {
      setIsDraggingV(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleMouseMove);
    window.addEventListener('touchend', handleMouseUp);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'row-resize';

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleMouseMove);
      window.removeEventListener('touchend', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDraggingV]);

  const handleResetLayout = () => {
    setLayout(DEFAULT_LAYOUT);
    toast.success('Reset layout to defaults');
  };

  const cacheKey = `${selectedProblemId}:${selectedLanguage}`;

  // Fetch initial problem fallback if none selected
  const { data: problemsData } = useQuery({
    queryKey: ['problems_initial_fallback'],
    queryFn: async () => {
      const res = await problemsApi.getProblems({ page_size: 1, sort: 'question_number' });
      return res.data;
    },
    enabled: !selectedProblemId,
  });

  const problems = problemsData?.results || [];

  // If no initial problem, pick the first one once loaded
  useEffect(() => {
    if (!selectedProblemId && problems.length > 0) {
      setSelectedProblemId(problems[0].id);
    }
  }, [problems, selectedProblemId]);

  // Fetch current problem details
  const { data: currentProblem, isLoading: loadingProblem } = useQuery({
    queryKey: ['problem_detail', selectedProblemId],
    queryFn: async () => {
      if (!selectedProblemId) return null;
      const res = await problemsApi.getProblem(selectedProblemId);
      return res.data;
    },
    enabled: !!selectedProblemId,
  });

  // Fetch starter template when problem or language changes
  const { data: templateData } = useQuery({
    queryKey: ['starter_template', selectedProblemId, selectedLanguage],
    queryFn: async () => {
      if (!selectedProblemId) return null;
      const res = await judgeApi.getTemplate(selectedProblemId, selectedLanguage);
      return res.data;
    },
    enabled: !!selectedProblemId,
  });

  // Synchronize editor code with cache or newly fetched template
  useEffect(() => {
    if (!selectedProblemId) return;

    if (codeCache[cacheKey] !== undefined) {
      setCode(codeCache[cacheKey]);
    } else if (templateData?.starter_code) {
      setCode(templateData.starter_code);
      setCodeCache((prev) => ({ ...prev, [cacheKey]: templateData.starter_code }));
    } else {
      const fallback = getFallbackTemplate(currentProblem, selectedLanguage);
      setCode(fallback);
      setCodeCache((prev) => ({ ...prev, [cacheKey]: fallback }));
    }
  }, [templateData, selectedProblemId, selectedLanguage, currentProblem]);

  // Fetch visible test cases
  const { data: testCasesData } = useQuery({
    queryKey: ['test_cases', selectedProblemId],
    queryFn: async () => {
      if (!selectedProblemId) return null;
      const res = await judgeApi.getTestCases(selectedProblemId);
      return res.data;
    },
    enabled: !!selectedProblemId,
  });

  // Pre-fill custom stdin with the problem's first visible test case input
  useEffect(() => {
    const firstInput = testCasesData?.test_cases?.[0]?.input_text;
    if (firstInput !== undefined && firstInput !== null) {
      setCustomStdin((prev) => (!prev.trim() ? firstInput : prev));
    }
  }, [testCasesData, selectedProblemId]);

  // Fetch submission history
  const { data: submissionsData } = useQuery({
    queryKey: ['submissions_history', selectedProblemId],
    queryFn: async () => {
      if (!selectedProblemId) return null;
      const res = await judgeApi.getSubmissions(selectedProblemId);
      return res.data;
    },
    enabled: !!selectedProblemId,
  });

  // Run Code Mutation
  const runCodeMutation = useMutation({
    mutationFn: (payload) => judgeApi.runCode(payload),
    onSuccess: (res) => {
      setRunResult(res.data);
      setSubmitResult(null);
      setActiveBottomTab('result');
      toast.success('Code executed');
    },
    onError: (err) => {
      toast.error(err.response?.data?.error || 'Execution failed');
    },
  });

  // Polling query for async judge status
  const { data: statusData } = useQuery({
    queryKey: ['submission_status', pollingSubmissionId],
    queryFn: async () => {
      if (!pollingSubmissionId) return null;
      const res = await judgeApi.getSubmissionStatus(pollingSubmissionId);
      return res.data;
    },
    enabled: !!pollingSubmissionId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!pollingSubmissionId) return false;
      if (!data || data.verdict === 'PENDING') {
        if (pollingStartTime && Date.now() - pollingStartTime > 45000) {
          return false;
        }
        return 1500;
      }
      return false;
    },
  });

  // Effect: When async evaluation completes, fetch full submission detail
  useEffect(() => {
    if (!pollingSubmissionId || !statusData) return;

    if (statusData.verdict && statusData.verdict !== 'PENDING') {
      const subId = pollingSubmissionId;
      setPollingSubmissionId(null);
      setPollingStartTime(null);

      judgeApi
        .getSubmissionDetail(subId)
        .then((res) => {
          setSubmitResult(res.data);
          setRunResult(null);
          setActiveBottomTab('result');

          queryClient.invalidateQueries({ queryKey: ['submissions_history', selectedProblemId] });
          queryClient.invalidateQueries({ queryKey: ['points'] });
          queryClient.invalidateQueries({ queryKey: ['achievements'] });
          queryClient.invalidateQueries({ queryKey: ['user_progress_stats'] });

          if (res.data.verdict === 'ACCEPTED') {
            toast.success('Accepted! Problem solved successfully.', { icon: '🎉' });
          } else {
            toast.error(`Verdict: ${res.data.verdict}`);
          }
        })
        .catch(() => {
          toast.error('Failed to load final submission details');
        });
    }
  }, [statusData, pollingSubmissionId, selectedProblemId, queryClient]);

  // Submit Code Mutation
  const submitCodeMutation = useMutation({
    mutationFn: (payload) => judgeApi.submitCode(payload),
    onSuccess: (res) => {
      const subId = res.data.submission_id;
      setRunResult(null);
      setSubmitResult(null);
      setActiveBottomTab('result');

      // If already finished synchronously (e.g. eager Celery mode)
      if (res.data.verdict && res.data.verdict !== 'PENDING') {
        setSubmitResult(res.data);
        queryClient.invalidateQueries({ queryKey: ['submissions_history', selectedProblemId] });
        queryClient.invalidateQueries({ queryKey: ['points'] });
        queryClient.invalidateQueries({ queryKey: ['achievements'] });
        queryClient.invalidateQueries({ queryKey: ['user_progress_stats'] });

        if (res.data.verdict === 'ACCEPTED') {
          toast.success(`Accepted! +${res.data.points_awarded || 0} pts`, { icon: '🎉' });
        } else {
          toast.error(`Verdict: ${res.data.verdict}`);
        }
        return;
      }

      // Begin polling until evaluation finishes
      setPollingSubmissionId(subId);
      setPollingStartTime(Date.now());
    },
    onError: (err) => {
      setPollingSubmissionId(null);
      toast.error(err.response?.data?.error || 'Submission failed');
    },
  });

  const handleCodeChange = (newCode) => {
    setCode(newCode);
    if (cacheKey) {
      setCodeCache((prev) => ({ ...prev, [cacheKey]: newCode }));
    }
  };

  const handleRun = () => {
    if (!selectedProblemId) return;
    if (currentProblem && !currentProblem.is_judge_ready) {
      toast.error('Online Judge configuration unavailable for this problem.');
      return;
    }
    if (!code.trim()) {
      toast.error('Code cannot be empty');
      return;
    }
    runCodeMutation.mutate({
      language: selectedLanguage,
      source_code: code,
      stdin: customStdin,
      problem_id: selectedProblemId,
    });
  };

  const handleSubmit = () => {
    if (!selectedProblemId) return;
    if (currentProblem && !currentProblem.is_judge_ready) {
      toast.error('Online Judge configuration unavailable for this problem.');
      return;
    }
    if (!code.trim()) {
      toast.error('Code cannot be empty');
      return;
    }
    submitCodeMutation.mutate({
      language: selectedLanguage,
      source_code: code,
      problem_id: selectedProblemId,
    });
  };

  const handleResetStarter = () => {
    const starter = templateData?.starter_code || getFallbackTemplate(currentProblem, selectedLanguage);
    setCode(starter);
    if (cacheKey) {
      setCodeCache((prev) => ({ ...prev, [cacheKey]: starter }));
    }
    toast.success('Reset code to starter template');
  };

  const handleSelectProblem = (prob) => {
    setSelectedProblemId(prob.id);
    setRunResult(null);
    setSubmitResult(null);
    setActiveBottomTab('testcases');
    setCustomStdin('');
  };

  const handleOpenSubmissionDetail = async (subId) => {
    try {
      setViewingLoading(true);
      const res = await judgeApi.getSubmissionDetail(subId);
      setViewingSubmission(res.data);
    } catch (err) {
      toast.error('Could not load submission detail');
    } finally {
      setViewingLoading(false);
    }
  };

  const testCases = testCasesData?.test_cases || [];
  const submissions = submissionsData?.submissions || [];

  return (
    <div className="h-[calc(100vh-5rem)] flex flex-col gap-3 p-4">
      {/* Top Bar: Problem selector & Actions */}
      <div className="relative z-30 flex flex-wrap items-center justify-between gap-3 bg-slate-900/95 backdrop-blur-md p-3 rounded-2xl border border-white/[0.08] shadow-lg">
        <div className="flex items-center gap-3">
          <ProblemSelector
            selectedProblem={currentProblem}
            onSelectProblem={handleSelectProblem}
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Language selector */}
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="bg-slate-800 text-xs font-semibold text-slate-200 rounded-xl px-3 py-2 border border-white/10 focus:outline-none cursor-pointer hover:bg-slate-700/80 transition"
          >
            <option value="python">Python 3</option>
            <option value="cpp">C++ (G++)</option>
            <option value="c">C (GCC)</option>
            <option value="java">Java (OpenJDK)</option>
          </select>

          {/* Reset Starter */}
          <button
            onClick={handleResetStarter}
            title="Reset to starter code"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.06] transition"
          >
            <RotateCcw className="h-4 w-4" />
          </button>

          {/* Reset Layout */}
          <button
            onClick={handleResetLayout}
            title="Reset panels to default layout"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.06] transition hidden lg:flex items-center gap-1"
          >
            <LayoutGrid className="h-4 w-4" />
          </button>

          {/* Run Code */}
          <button
            onClick={handleRun}
            disabled={!currentProblem?.is_judge_ready || runCodeMutation.isPending || submitCodeMutation.isPending || !!pollingSubmissionId}
            title={!currentProblem?.is_judge_ready ? "Online Judge configuration unavailable for this problem" : "Run Code"}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs font-semibold border border-white/10 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {runCodeMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 text-emerald-400 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 text-emerald-400 fill-emerald-400" />
            )}
            <span>{runCodeMutation.isPending ? 'Running...' : 'Run Code'}</span>
          </button>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!currentProblem?.is_judge_ready || runCodeMutation.isPending || submitCodeMutation.isPending || !!pollingSubmissionId}
            title={!currentProblem?.is_judge_ready ? "Online Judge configuration unavailable for this problem" : "Submit Code"}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-xs font-bold shadow-lg shadow-emerald-500/20 hover:brightness-110 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitCodeMutation.isPending || !!pollingSubmissionId ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            <span>{submitCodeMutation.isPending || !!pollingSubmissionId ? 'Judging...' : 'Submit'}</span>
          </button>
        </div>
      </div>

      {/* Configuration Required Banner */}
      {currentProblem && !currentProblem.is_judge_ready && (
        <div className="relative z-20 flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/25 text-amber-200 text-xs shadow-sm shrink-0">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong className="text-amber-300 font-semibold">Online Judge configuration unavailable for this problem.</strong>
              {currentProblem.missing_configuration?.length > 0 && (
                <span className="text-slate-300 ml-1.5">
                  Missing: <span className="text-amber-200/90 font-medium">{currentProblem.missing_configuration.join(' • ')}</span>
                </span>
              )}
            </span>
          </div>
          {(currentProblem.leetcode_url || currentProblem.source_url) && (
            <a
              href={currentProblem.leetcode_url || currentProblem.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-amber-400 hover:text-amber-300 font-semibold hover:underline shrink-0"
            >
              <span>Practice on LeetCode</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      )}

      {/* Main Split View: Left (Description / Editorial) & Right (Code Editor + Console) */}
      <div
        ref={containerRef}
        className="relative z-10 flex-1 flex flex-col lg:flex-row min-h-0 w-full overflow-hidden gap-0"
      >
        {/* Left Pane: Problem Description / Editorial Tabs */}
        <div
          style={isDesktop ? { width: `calc(${layout.leftWidthPercent}% - 6px)` } : undefined}
          className="bg-slate-900/40 backdrop-blur-md rounded-2xl border border-white/[0.08] flex flex-col overflow-hidden shadow-sm w-full lg:min-w-[280px] lg:max-w-[75%] mb-3 lg:mb-0 shrink-0"
        >
          {/* Left Pane Header Tabs */}
          <div className="flex items-center justify-between border-b border-white/[0.08] px-4 py-2.5 bg-slate-950/50 shrink-0">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveLeftTab('description')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                  activeLeftTab === 'description'
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                <span>Description</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveLeftTab('editorial')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                  activeLeftTab === 'editorial'
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                <BookOpen className="h-3.5 w-3.5" />
                <span>Editorial & Solution</span>
                {currentProblem?.has_solution && (
                  <span
                    title="Solution available"
                    className="w-1.5 h-1.5 rounded-full bg-emerald-400 ring-2 ring-emerald-400/20 ml-0.5"
                  />
                )}
              </button>
            </div>
          </div>

          {/* Left Pane Content */}
          <div className="flex-1 p-5 overflow-y-auto">
            {loadingProblem ? (
              <div className="animate-pulse space-y-4">
                <div className="h-6 bg-slate-800 rounded w-2/3" />
                <div className="h-4 bg-slate-800 rounded w-1/4" />
                <div className="space-y-2 pt-4">
                  <div className="h-4 bg-slate-800 rounded w-full" />
                  <div className="h-4 bg-slate-800 rounded w-5/6" />
                  <div className="h-4 bg-slate-800 rounded w-4/6" />
                </div>
              </div>
            ) : activeLeftTab === 'editorial' ? (
              <SolutionViewer problemId={selectedProblemId} />
            ) : (
              <ProblemStatement problem={currentProblem} testCases={testCases} />
            )}
          </div>
        </div>

        {/* Vertical Separator between Left and Right Panes */}
        <div className="hidden lg:flex items-stretch px-1">
          <ResizableDivider
            direction="horizontal"
            isDragging={isDraggingH}
            onMouseDown={() => setIsDraggingH(true)}
            onTouchStart={() => setIsDraggingH(true)}
          />
        </div>

        {/* Right Pane: Code Editor + Tabs */}
        <div
          ref={rightPaneRef}
          style={isDesktop ? { width: `calc(${100 - layout.leftWidthPercent}% - 6px)` } : undefined}
          className="flex flex-col min-h-0 w-full lg:min-w-[320px] lg:max-w-[80%] flex-1"
        >
          {/* Monaco Editor Container */}
          <div
            style={isDesktop ? { height: `calc(${layout.editorHeightPercent}% - 6px)` } : undefined}
            className="w-full min-h-[220px] flex flex-col overflow-hidden mb-3 lg:mb-0 shrink-0"
          >
            <div className="flex-1 h-full w-full min-h-[200px]">
              <MonacoCodeEditor
                value={code}
                onChange={handleCodeChange}
                language={selectedLanguage}
                onRun={handleRun}
                onSubmit={handleSubmit}
              />
            </div>
          </div>

          {/* Horizontal Separator between Editor and Console */}
          <div className="hidden lg:flex items-stretch py-1">
            <ResizableDivider
              direction="vertical"
              isDragging={isDraggingV}
              onMouseDown={() => setIsDraggingV(true)}
              onTouchStart={() => setIsDraggingV(true)}
            />
          </div>

          {/* Bottom Console Tabs */}
          <div
            style={isDesktop ? { height: `calc(${100 - layout.editorHeightPercent}% - 6px)` } : undefined}
            className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-white/[0.08] flex flex-col overflow-hidden w-full min-h-[160px] h-64 lg:h-auto flex-1"
          >
            {/* Tab header */}
            <div className="flex items-center justify-between border-b border-white/[0.08] px-3 py-2 bg-slate-950/40">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveBottomTab('testcases')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    activeBottomTab === 'testcases'
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="h-3.5 w-3.5" />
                  Test Cases
                </button>

                <button
                  type="button"
                  onClick={() => setActiveBottomTab('custom_input')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    activeBottomTab === 'custom_input'
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Terminal className="h-3.5 w-3.5" />
                  Custom Stdin
                </button>

                <button
                  type="button"
                  onClick={() => setActiveBottomTab('result')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    activeBottomTab === 'result'
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Play className="h-3.5 w-3.5" />
                  Result
                </button>

                <button
                  type="button"
                  onClick={() => setActiveBottomTab('history')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    activeBottomTab === 'history'
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <History className="h-3.5 w-3.5" />
                  Submissions ({submissions.length})
                </button>
              </div>
            </div>

            {/* Tab content */}
            <div className="flex-1 p-4 overflow-y-auto text-xs font-mono">
              {/* Test Cases Tab */}
              {activeBottomTab === 'testcases' && (
                <div className="space-y-3">
                  {currentProblem && !currentProblem.is_judge_ready ? (
                    <div className="p-4 text-center text-slate-400 bg-slate-950/40 rounded-xl border border-white/5 space-y-1">
                      <div className="font-semibold text-slate-300">Test Cases Unavailable</div>
                      <div className="text-[11px] text-slate-500">
                        Online Judge test cases have not yet been configured for this problem.
                      </div>
                    </div>
                  ) : testCases.length === 0 ? (
                    <div className="text-slate-500">No test cases found for this problem.</div>
                  ) : (
                    testCases.map((tc, i) => (
                      <div key={tc.id} className="p-2.5 rounded-lg bg-slate-950/60 border border-white/5 space-y-1">
                        <div className="text-slate-400 font-semibold font-sans">Test Case #{i + 1}</div>
                        <div><span className="text-slate-500 font-sans">Input:</span> {tc.input_text || '(empty)'}</div>
                        <div><span className="text-slate-500 font-sans">Expected:</span> <span className="text-emerald-400">{tc.expected_output}</span></div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Custom Stdin Tab */}
              {activeBottomTab === 'custom_input' && (
                <div className="h-full flex flex-col">
                  <textarea
                    value={customStdin}
                    onChange={(e) => setCustomStdin(e.target.value)}
                    placeholder="Enter custom standard input here... Press Run Code to test."
                    className="w-full h-full bg-slate-950/60 p-2.5 rounded-xl border border-white/10 text-slate-200 focus:outline-none resize-none font-mono text-xs"
                  />
                </div>
              )}

              {/* Result Tab */}
              {activeBottomTab === 'result' && (
                <div>
                  {pollingSubmissionId && !submitResult ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-3">
                      <Loader2 className="h-8 w-8 text-emerald-400 animate-spin" />
                      <div className="text-sm font-semibold text-slate-200">Evaluating your solution...</div>
                      <div className="text-xs text-slate-500">Running against test cases in the sandbox</div>
                    </div>
                  ) : submitResult ? (
                    <div className="space-y-3">
                      {/* Verdict header banner */}
                      <div
                        className={`p-3 rounded-xl flex items-center justify-between ${
                          submitResult.verdict === 'ACCEPTED'
                            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                            : (submitResult.verdict === 'TIME_LIMIT_EXCEEDED' || submitResult.verdict === 'TLE')
                            ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
                            : 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {submitResult.verdict === 'ACCEPTED' ? (
                            <CheckCircle2 className="h-5 w-5" />
                          ) : (submitResult.verdict === 'TIME_LIMIT_EXCEEDED' || submitResult.verdict === 'TLE') ? (
                            <Clock className="h-5 w-5 text-amber-400" />
                          ) : (
                            <XCircle className="h-5 w-5" />
                          )}
                          <span className="text-sm font-bold">
                            {submitResult.verdict === 'TLE' ? 'TIME LIMIT EXCEEDED' : submitResult.verdict}
                          </span>
                          <span className="text-xs text-slate-400 ml-2">
                            ({submitResult.tests_passed}/{submitResult.tests_total} passed)
                          </span>
                        </div>

                        <div className="flex items-center gap-4 text-xs text-slate-300">
                          <span className="flex items-center gap-1" title="Measured program execution time">
                            <Clock className="h-3.5 w-3.5 text-slate-400" />
                            {submitResult.execution_time_ms} ms
                            {submitResult.time_limit_ms ? (
                              <span className="text-slate-500 font-sans text-[11px]">/ {submitResult.time_limit_ms}ms limit</span>
                            ) : null}
                          </span>
                          <span className="flex items-center gap-1">
                            <Cpu className="h-3.5 w-3.5 text-slate-400" />
                            {Math.round(submitResult.memory_kb / 1024)} MB
                          </span>
                        </div>
                      </div>

                      {/* Diagnostic details if compilation or test error */}
                      {submitResult.compile_error && (
                        <div className="p-3 bg-rose-950/40 rounded-xl border border-rose-500/20 text-rose-300 whitespace-pre-wrap leading-relaxed font-mono">
                          <div className="font-bold text-rose-400 mb-1">Error Diagnostic:</div>
                          {submitResult.compile_error}
                        </div>
                      )}
                    </div>
                  ) : runResult ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-3 text-slate-400 pb-2 border-b border-white/5">
                        <span className="font-semibold text-white">Status: {runResult.status}</span>
                        <span>{runResult.execution_time_ms} ms</span>
                        {runResult.time_limit_ms ? (
                          <span className="text-slate-500 font-sans text-[11px]">(Limit: {runResult.time_limit_ms}ms)</span>
                        ) : null}
                      </div>
                      {runResult.stdout && (
                        <div>
                          <div className="text-slate-500 text-[10px] uppercase font-bold">Standard Output:</div>
                          <div className="p-2.5 rounded-lg bg-slate-950 text-slate-200 whitespace-pre-wrap mt-1">
                            {runResult.stdout}
                          </div>
                        </div>
                      )}
                      {runResult.stderr && (
                        <div>
                          <div className="text-rose-400 text-[10px] uppercase font-bold">Standard Error:</div>
                          <div className="p-2.5 rounded-lg bg-rose-950/40 text-rose-300 whitespace-pre-wrap mt-1">
                            {runResult.stderr}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-slate-500 text-center py-8">
                      Press "Run Code" or "Submit" to see execution results.
                    </div>
                  )}
                </div>
              )}

              {/* Submissions History Tab */}
              {activeBottomTab === 'history' && (
                <div className="space-y-2">
                  {submissions.length === 0 ? (
                    <div className="text-slate-500 text-center py-6">No previous submissions yet.</div>
                  ) : (
                    submissions.map((sub) => (
                      <div
                        key={sub.id}
                        className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-between gap-3 hover:border-white/10 transition"
                      >
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`font-semibold ${
                              sub.verdict === 'ACCEPTED' ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {sub.verdict}
                          </span>
                          <span className="text-slate-500">
                            ({sub.tests_passed}/{sub.tests_total})
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-slate-400 uppercase">
                            {sub.language}
                          </span>
                          <span className="text-slate-500 text-[11px] hidden sm:inline">
                            {sub.execution_time_ms} ms
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-slate-500 text-[11px]">
                            {new Date(sub.created_at).toLocaleDateString()} {new Date(sub.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleOpenSubmissionDetail(sub.id)}
                            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-sans font-medium transition"
                            title="View code and details"
                          >
                            <Eye className="h-3 w-3" />
                            <span>View</span>
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Invisible overlay while dragging to catch mouse/touch events over Monaco */}
      {(isDraggingH || isDraggingV) && (
        <div
          className={`fixed inset-0 z-50 select-none bg-transparent ${
            isDraggingH ? 'cursor-col-resize' : 'cursor-row-resize'
          }`}
        />
      )}

      {/* View Submission Code Modal */}
      {viewingSubmission && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 bg-slate-950/70 shrink-0">
              <div className="flex items-center gap-3">
                <span
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold ${
                    viewingSubmission.verdict === 'ACCEPTED'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  }`}
                >
                  {viewingSubmission.verdict}
                </span>
                <span className="text-sm font-semibold text-white">
                  Submission Detail
                </span>
                <span className="px-2 py-0.5 rounded bg-white/5 text-[11px] font-mono text-slate-300 uppercase">
                  {viewingSubmission.language}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setViewingSubmission(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto space-y-4 flex-1">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 rounded-xl bg-slate-950/50 border border-white/5">
                  <span className="text-slate-400 block text-[11px]">Tests Passed</span>
                  <span className="text-white font-bold text-sm">
                    {viewingSubmission.tests_passed} / {viewingSubmission.tests_total}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/50 border border-white/5">
                  <span className="text-slate-400 block text-[11px]">Runtime</span>
                  <span className="text-white font-bold text-sm">
                    {viewingSubmission.execution_time_ms} ms
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/50 border border-white/5">
                  <span className="text-slate-400 block text-[11px]">Memory</span>
                  <span className="text-white font-bold text-sm">
                    {Math.round((viewingSubmission.memory_kb || 0) / 1024)} MB
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/50 border border-white/5">
                  <span className="text-slate-400 block text-[11px]">Submitted</span>
                  <span className="text-slate-200 font-medium">
                    {new Date(viewingSubmission.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>

              {viewingSubmission.compile_error && (
                <div className="p-3 bg-rose-950/40 rounded-xl border border-rose-500/20 text-rose-300 font-mono text-xs whitespace-pre-wrap">
                  <div className="font-bold text-rose-400 mb-1">Diagnostic Output:</div>
                  {viewingSubmission.compile_error}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300">Submitted Code:</span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(viewingSubmission.source_code);
                      toast.success('Code copied to clipboard');
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Copy Code
                  </button>
                </div>
                <div className="relative rounded-xl border border-white/10 bg-[#161b22] overflow-hidden">
                  <pre className="p-4 text-xs font-mono text-slate-100 overflow-x-auto max-h-72 leading-relaxed whitespace-pre">
                    <code>{viewingSubmission.source_code}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

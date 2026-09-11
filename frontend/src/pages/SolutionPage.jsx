import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  ExternalLink,
  Clock,
  MemoryStick,
  Copy,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from 'lucide-react';
import { problemsApi } from '../api/client';
import CodeBlock from '../components/common/CodeBlock';

export default function SolutionPage() {
  const { id } = useParams();
  const [showFullExplanation, setShowFullExplanation] = useState(false);
  const [activeTab, setActiveTab] = useState('code'); // 'description' | 'code' | 'explanation'

  // Fetch solution from our internal API
  const { data: solution, isLoading, error, refetch } = useQuery({
    queryKey: ['solution', id],
    queryFn: async () => {
      const res = await problemsApi.getProblemSolution(id);
      return res.data;
    },
    enabled: !!id,
    retry: 1,
    staleTime: 1000 * 60 * 30, // 30 minutes
  });

  // Also fetch basic problem info for the title/link
  const { data: problem } = useQuery({
    queryKey: ['problem', id],
    queryFn: async () => {
      const res = await problemsApi.getProblem(id);
      return res.data;
    },
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mb-4"></div>
          <p className="text-slate-400">Loading solution...</p>
        </div>
      </div>
    );
  }

  if (error || !solution || solution.available === false) {
    const message = solution?.message || 'Solution not available';
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <AlertTriangle className="h-16 w-16 text-amber-500/50 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Solution Not Available</h1>
          <p className="text-slate-400 mb-6 max-w-md mx-auto">
            {message}
          </p>
          {problem && (
            <Link
              to={`/problems/${problem.id}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Problem
            </Link>
          )}
        </div>
      </div>
    );
  }

  const {
    question_number,
    title,
    description,
    code,
    language,
    explanation,
    time_complexity,
    space_complexity,
    source_url,
    solution_source_url,
  } = solution;

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch (e) {
      console.error('Copy failed:', e);
    }
  };

  const truncatedExplanation = explanation.length > 300
    ? explanation.slice(0, 300) + '...'
    : explanation;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header with back link and problem title */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              to={problem ? `/problems/${problem.id}` : '/'}
              className="p-2 rounded-lg border border-slate-800 text-slate-400 hover:text-white hover:border-slate-600 transition"
              title="Back to problem"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Solution</p>
              <h1 className="text-2xl font-bold text-white truncate max-w-[500px]">
                {question_number ? `${question_number}. ` : ''}{title}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {problem?.leetcode_url && (
              <a
                href={problem.leetcode_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900 text-xs font-medium text-slate-300 hover:border-indigo-500/50 hover:text-indigo-400 transition"
                title="View on LeetCode"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">View on LeetCode</span>
              </a>
            )}
            {(solution_source_url || source_url) && (
              <a
                href={solution_source_url || source_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-xs font-medium text-amber-300 hover:bg-amber-500/20 transition"
                title="Source: scraped server-side from leetcode.ca — content is displayed internally"
              >
                <MemoryStick className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Source</span>
              </a>
            )}
          </div>
        </div>

        {/* Metadata badges */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-sm">
            <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
              language === 'python' ? 'bg-blue-500/20 text-blue-400' :
              language === 'javascript' ? 'bg-yellow-500/20 text-yellow-400' :
              language === 'java' ? 'bg-red-500/20 text-red-400' :
              language === 'cpp' ? 'bg-purple-500/20 text-purple-400' :
              language === 'c' ? 'bg-cyan-500/20 text-cyan-400' :
              language === 'go' ? 'bg-teal-500/20 text-teal-400' :
              'bg-slate-700 text-slate-300'
            }`}>
              {language}
            </span>
          </span>
          {time_complexity && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-sm">
              <Clock className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-mono">Time: {time_complexity}</span>
            </span>
          )}
          {space_complexity && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-sm">
              <MemoryStick className="h-3.5 w-3.5 text-blue-400" />
              <span className="text-blue-400 font-mono">Space: {space_complexity}</span>
            </span>
          )}
        </div>

        {/* Tab navigation */}
        <div className="flex border-b border-slate-800">
          <button
            onClick={() => setActiveTab('description')}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === 'description'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            Description
          </button>
          <button
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === 'code'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            Code
          </button>
          <button
            onClick={() => setActiveTab('explanation')}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === 'explanation'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            Explanation
          </button>
        </div>

        {/* Tab panels */}
        {activeTab === 'description' ? (
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Problem Description</h3>
            <div className="space-y-4 text-slate-200 leading-relaxed whitespace-pre-wrap">
              {description || 'Problem description not available.'}
            </div>
          </div>
        ) : activeTab === 'code' ? (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-500">Solution Code</span>
              <button
                onClick={copyCode}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 hover:border-slate-700 hover:text-white transition"
              >
                <Copy className="h-3.5 w-3.5" />
                <span>Copy</span>
              </button>
            </div>
            <CodeBlock code={code} language={language} />
          </div>
        ) : (
          <div className="prose prose-invert max-w-none">
            <div className="space-y-4 text-slate-300 leading-relaxed">
              {showFullExplanation || explanation.length <= 300 ? (
                <>
                  <div className="whitespace-pre-wrap">{explanation}</div>
                </>
              ) : (
                <>
                  <div className="whitespace-pre-wrap">{truncatedExplanation}</div>
                  <button
                    onClick={() => setShowFullExplanation(true)}
                    className="text-indigo-400 hover:text-indigo-300 text-sm font-medium underline"
                  >
                    Read more
                  </button>
                </>
              )}
            </div>
            {(time_complexity || space_complexity) && (
              <div className="mt-6 p-4 bg-slate-900/50 border border-slate-800 rounded-xl space-y-3">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Complexity Analysis</h3>
                <dl className="space-y-2">
                  {time_complexity && (
                    <div className="flex items-center gap-3">
                      <dt className="text-xs text-slate-400 uppercase tracking-wider min-w-[80px]">Time</dt>
                      <dd className="font-mono text-emerald-400">{time_complexity}</dd>
                    </div>
                  )}
                  {space_complexity && (
                    <div className="flex items-center gap-3">
                      <dt className="text-xs text-slate-400 uppercase tracking-wider min-w-[80px]">Space</dt>
                      <dd className="font-mono text-blue-400">{space_complexity}</dd>
                    </div>
                  )}
                </dl>
              </div>
            )}
          </div>
        )}

        {/* Footer note about source */}
        <div className="pt-4 border-t border-slate-800 text-xs text-slate-500">
          <p>Solution content is scraped server-side from leetcode.ca and cached — never proxied directly to your browser.</p>
        </div>
      </div>
    </div>
  );
}
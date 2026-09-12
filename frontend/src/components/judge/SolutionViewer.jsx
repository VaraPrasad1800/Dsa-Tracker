import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  Cpu,
  Copy,
  Check,
  ExternalLink,
  BookOpen,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { problemsApi } from '../../api/client';

const LANGUAGE_LABELS = {
  python: 'Python 3',
  cpp: 'C++',
  'c++': 'C++',
  java: 'Java',
  c: 'C',
  javascript: 'JavaScript',
  go: 'Go',
};

export default function SolutionViewer({ problemId }) {
  const [selectedLang, setSelectedLang] = useState('python');
  const [copied, setCopied] = useState(false);

  const { data: solution, isLoading, error } = useQuery({
    queryKey: ['problem_solution_viewer', problemId],
    queryFn: async () => {
      if (!problemId) return null;
      const res = await problemsApi.getProblemSolution(problemId);
      return res.data;
    },
    enabled: !!problemId,
    staleTime: 1000 * 60 * 15,
    retry: 1,
  });

  // Extract available languages from code_by_language or fallback
  const availableLanguages = useMemo(() => {
    if (!solution) return ['python'];
    const cbl = solution.code_by_language || {};
    const langs = Object.keys(cbl);
    if (langs.length > 0) return langs;
    if (solution.language && solution.code) return [solution.language];
    return ['python'];
  }, [solution]);

  // Ensure selected language is valid
  const currentLang = availableLanguages.includes(selectedLang)
    ? selectedLang
    : availableLanguages[0] || 'python';

  // Get code for selected language
  const activeCode = useMemo(() => {
    if (!solution) return '';
    const cbl = solution.code_by_language || {};
    if (cbl[currentLang]) return cbl[currentLang];
    if (solution.code && (solution.language === currentLang || !cbl[currentLang])) {
      return solution.code;
    }
    return '// Solution code not available for this language.';
  }, [solution, currentLang]);

  const handleCopy = async () => {
    if (!activeCode) return;
    try {
      await navigator.clipboard.writeText(activeCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy solution code', e);
    }
  };

  if (isLoading) {
    return (
      <div className="py-12 flex flex-col items-center justify-center space-y-3">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500" />
        <span className="text-xs text-slate-400 font-medium">Loading editorial solution...</span>
      </div>
    );
  }

  if (error || !solution || solution.available === false) {
    return (
      <div className="py-10 text-center space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto text-amber-400">
          <BookOpen className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">
          No Editorial Solution Available
        </h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          An official editorial has not been indexed for this problem yet. Try solving it or check discussions.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-6 text-sm text-slate-300 font-sans leading-relaxed">
      {/* Editorial Header */}
      <div className="border-b border-white/[0.08] pb-4 space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Editorial & Optimal Solution</h2>
          </div>

          {solution.solution_source_url && (
            <a
              href={solution.solution_source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition font-medium"
            >
              <span>Source Editorial</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>

        {/* Complexity Badges */}
        <div className="flex items-center gap-3 flex-wrap text-xs">
          {solution.time_complexity && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono">
              <Clock className="h-3.5 w-3.5" />
              <span>Time: <strong>{solution.time_complexity}</strong></span>
            </div>
          )}
          {solution.space_complexity && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 font-mono">
              <Cpu className="h-3.5 w-3.5" />
              <span>Space: <strong>{solution.space_complexity}</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* Language Tabs & Copy Button */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 border-b border-white/[0.08] pb-1">
          <div className="flex items-center gap-1 overflow-x-auto">
            {availableLanguages.map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => setSelectedLang(lang)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  currentLang === lang
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                {LANGUAGE_LABELS[lang.toLowerCase()] || lang.toUpperCase()}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-slate-700 text-xs font-medium text-slate-300 transition border border-white/10 shrink-0"
            title="Copy solution code"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-slate-400" />
                <span>Copy Code</span>
              </>
            )}
          </button>
        </div>

        {/* Read-only Code Display */}
        <div className="relative rounded-xl border border-white/10 bg-[#161b22] overflow-hidden shadow-inner">
          <pre className="p-4 text-xs font-mono text-slate-100 overflow-x-auto max-h-[380px] leading-relaxed whitespace-pre">
            <code>{activeCode}</code>
          </pre>
        </div>
      </div>

      {/* Explanation Section */}
      {solution.explanation && (
        <div className="space-y-2 pt-3 border-t border-white/[0.08]">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Approach & Algorithm
          </h3>
          <div className="text-xs text-slate-300 space-y-2 leading-relaxed whitespace-pre-wrap bg-slate-950/40 p-3.5 rounded-xl border border-white/[0.06]">
            {solution.explanation}
          </div>
        </div>
      )}
    </div>
  );
}

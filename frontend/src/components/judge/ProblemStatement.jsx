import React from 'react';
import { ExternalLink, Code2, Clock, Cpu } from 'lucide-react';

export default function ProblemStatement({ problem, testCases = [] }) {
  if (!problem) {
    return (
      <div className="text-slate-500 text-sm py-8 text-center">
        Select a problem to view its description.
      </div>
    );
  }

  const getDifficultyClass = (diff) => {
    switch (diff) {
      case 'Easy':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25';
      case 'Medium':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/25';
      case 'Hard':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/25';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  // Helper to format inline code in markdown style `foo`
  const renderFormattedText = (text) => {
    if (!text) return null;
    const parts = text.split(/(`[^`]+`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 rounded bg-slate-800/80 text-indigo-300 font-mono text-[12px] border border-white/5"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  // Use clean_description if provided by backend, else description
  const descriptionText = problem.clean_description || problem.description || '';
  // Split into paragraphs
  const paragraphs = descriptionText
    .split(/\n\s*\n+/)
    .map((p) => p.trim())
    .filter((p) => p && !p.startsWith('Example') && !p.startsWith('Constraints'));

  const examples = Array.isArray(problem.examples) && problem.examples.length > 0
    ? problem.examples
    : null;

  const constraints = Array.isArray(problem.constraints) && problem.constraints.length > 0
    ? problem.constraints
    : [];

  return (
    <div className="space-y-6 pb-6 text-sm text-slate-300 leading-relaxed font-sans">
      {/* Title & Meta */}
      <div className="border-b border-white/[0.08] pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="text-xl font-mono font-bold text-indigo-400 shrink-0">
                #{problem.question_number || problem.leetcode_id}
              </span>
              <h1 className="text-xl font-bold text-white leading-tight">
                {problem.title}
              </h1>
              <span
                className={`px-2.5 py-0.5 rounded-md text-xs font-bold border shrink-0 ${getDifficultyClass(
                  problem.difficulty
                )}`}
              >
                {problem.difficulty}
              </span>
            </div>

            {/* Execution mode badge */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-[11px] font-mono border border-indigo-500/20">
                <Code2 className="h-3 w-3" />
                {problem.execution_mode === 'FUNCTION'
                  ? `Method: ${problem.function_name || 'solve'}()`
                  : 'Standard I/O (stdin/stdout)'}
              </span>

              {/* Time Limit Badge */}
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[11px] font-mono border border-amber-500/20" title="Authoritative execution time limit per test case">
                <Clock className="h-3 w-3" />
                Time: {problem.time_limit_ms ? `${(problem.time_limit_ms / 1000).toFixed(1)}s` : '2.0s'}
              </span>

              {/* Memory Limit Badge */}
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 text-[11px] font-mono border border-cyan-500/20" title="Execution memory limit">
                <Cpu className="h-3 w-3" />
                Mem: {problem.memory_limit_mb || 128} MB
              </span>

              {problem.leetcode_url && (
                <a
                  href={problem.leetcode_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-300 transition"
                  title="View on LeetCode"
                >
                  <ExternalLink className="h-3 w-3" />
                  <span>LeetCode</span>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Tags */}
        {problem.tags?.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mt-3">
            {problem.tags.map((t) => (
              <span
                key={t.id}
                className="px-2 py-0.5 rounded-md bg-white/[0.04] text-slate-400 hover:text-slate-200 text-[11px] font-medium border border-white/[0.06] transition"
              >
                {t.name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Description Paragraphs */}
      <div className="space-y-3 text-slate-300">
        {paragraphs.length > 0 ? (
          paragraphs.map((para, idx) => (
            <p key={idx} className="leading-relaxed">
              {renderFormattedText(para)}
            </p>
          ))
        ) : (
          <p className="text-slate-400 italic">
            {problem.execution_mode === 'FUNCTION'
              ? 'Complete the function according to the problem requirements.'
              : 'Read standard input (stdin) and print output to standard output (stdout).'}
          </p>
        )}
      </div>

      {/* Structured Examples */}
      {examples ? (
        <div className="space-y-4 pt-2">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Examples
          </h3>
          <div className="space-y-3">
            {examples.map((ex, idx) => (
              <div
                key={idx}
                className="bg-slate-950/60 rounded-xl p-3.5 border border-white/[0.07] text-xs font-mono space-y-2 shadow-sm"
              >
                <div className="text-slate-400 font-semibold font-sans">
                  Example {idx + 1}:
                </div>
                <div className="space-y-1">
                  <div className="text-slate-400">
                    <span className="font-semibold text-slate-300 font-sans">Input: </span>
                    <span className="text-slate-200 bg-slate-900/90 px-1.5 py-0.5 rounded border border-white/5 inline-block">
                      {ex.input}
                    </span>
                  </div>
                  <div className="text-slate-400">
                    <span className="font-semibold text-slate-300 font-sans">Output: </span>
                    <span className="text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded border border-emerald-500/20 inline-block font-semibold">
                      {ex.output}
                    </span>
                  </div>
                  {ex.explanation && (
                    <div className="text-slate-400 pt-1 font-sans text-xs leading-normal">
                      <span className="font-semibold text-slate-300">Explanation: </span>
                      {renderFormattedText(ex.explanation)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : testCases.length > 0 ? (
        /* Fallback to visible test cases if no structured examples */
        <div className="space-y-3 pt-2">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Sample Cases
          </h3>
          <div className="space-y-2.5">
            {testCases.map((tc, idx) => (
              <div
                key={tc.id || idx}
                className="bg-slate-950/60 rounded-xl p-3.5 border border-white/[0.07] text-xs font-mono space-y-1.5 shadow-sm"
              >
                <div className="text-slate-400 font-semibold font-sans">Case #{idx + 1}</div>
                <div>
                  <span className="text-slate-400 font-sans">Input: </span>
                  <span className="text-slate-200">{tc.input_text || '(empty)'}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-sans">Output: </span>
                  <span className="text-emerald-400 font-semibold">{tc.expected_output}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Input / Output Format (Standard I/O) */}
      {(problem.input_format || problem.output_format) && (
        <div className="space-y-4 pt-2 border-t border-white/[0.08]">
          {problem.input_format && (
            <div className="space-y-1.5">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Input Format (stdin)
              </h3>
              <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-line bg-slate-950/40 p-3 rounded-lg border border-white/[0.05]">
                {renderFormattedText(problem.input_format)}
              </div>
            </div>
          )}

          {problem.output_format && (
            <div className="space-y-1.5">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Output Format (stdout)
              </h3>
              <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-line bg-slate-950/40 p-3 rounded-lg border border-white/[0.05]">
                {renderFormattedText(problem.output_format)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Constraints */}
      {constraints.length > 0 && (
        <div className="space-y-2.5 pt-2 border-t border-white/[0.08]">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Constraints
          </h3>
          <ul className="space-y-1.5 list-disc list-inside text-xs text-slate-300">
            {constraints.map((c, idx) => (
              <li key={idx} className="leading-relaxed">
                {renderFormattedText(c)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

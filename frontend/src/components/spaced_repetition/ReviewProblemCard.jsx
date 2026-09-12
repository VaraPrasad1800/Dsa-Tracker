import React, { useState } from 'react';
import { 
  CheckCircle2, 
  RotateCcw, 
  MinusCircle, 
  ExternalLink, 
  Eye, 
  EyeOff, 
  Layers, 
  Clock, 
  Code,
  FileText
} from 'lucide-react';

export default function ReviewProblemCard({
  item,
  onAction,
  onSolve,
  loading = false,
}) {
  const [showNotes, setShowNotes] = useState(false);
  const problem = item.problem;
  const currentBox = item.current_box || 1;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative">
      {/* Box & Difficulty header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-bold flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            Currently in Box {currentBox}
          </span>
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ${
            problem.difficulty === 'Easy' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
            problem.difficulty === 'Medium' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' :
            'bg-rose-500/15 text-rose-400 border border-rose-500/30'
          }`}>
            {problem.difficulty}
          </span>
          <span className="text-xs text-slate-400">• {problem.source_platform}</span>
        </div>

        {item.next_review_date && (
          <div className="text-xs text-rose-400 flex items-center gap-1 bg-rose-500/10 px-2.5 py-1 rounded-md border border-rose-500/20">
            <Clock className="h-3.5 w-3.5 animate-pulse" />
            Due for Review
          </div>
        )}
      </div>

      {/* Title & External Link */}
      <div className="mb-6">
        <h2 className="text-2xl font-black text-white flex items-center gap-3">
          {problem.question_number && (
            <span className="text-indigo-400 font-mono text-xl">
              #{problem.question_number}
            </span>
          )}
          <span>{problem.title}</span>
          {problem.source_url && (
            <a
              href={problem.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-slate-400 hover:text-indigo-400 transition p-1 hover:bg-slate-800 rounded-lg inline-flex items-center gap-1 text-xs font-normal"
              title="Open Problem on LeetCode"
            >
              <ExternalLink className="h-4 w-4" />
              LeetCode
            </a>
          )}
        </h2>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {problem.tags?.map((tag) => (
            <span key={tag.id} className="text-xs px-2.5 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
              {tag.name}
            </span>
          ))}
          {problem.companies?.map((comp) => (
            <span key={comp.id} className="text-xs px-2.5 py-0.5 rounded-md bg-indigo-950/60 text-indigo-300 border border-indigo-900/60">
              {comp.name}
            </span>
          ))}
        </div>
      </div>

      {/* Solution & Notes Reveal Toggle */}
      <div className="border-t border-b border-slate-800/80 py-4 my-6">
        <button
          onClick={() => setShowNotes(!showNotes)}
          className="flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-indigo-400 transition"
        >
          {showNotes ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          <span>{showNotes ? 'Hide Solution Notes & Code' : 'Reveal Solution Notes & Code'}</span>
        </button>

        {showNotes && (
          <div className="mt-4 space-y-4 animate-fadeIn">
            {item.notes ? (
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-sm text-slate-200">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Your Solution Notes</span>
                </div>
                <p className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-slate-300">{item.notes}</p>
              </div>
            ) : (
              <div className="text-xs text-slate-500 italic">No personal notes recorded yet.</div>
            )}

            {item.code_solution && (
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                  <Code className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Code Solution</span>
                </div>
                <pre className="font-mono text-xs text-emerald-400 overflow-x-auto leading-relaxed">
                  {item.code_solution}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Review Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
        <div className="text-xs text-slate-400 text-center sm:text-left">
          Times Solved: <strong className="text-white">{item.times_solved || 0}</strong> • Times Attempted:{' '}
          <strong className="text-white">{item.times_attempted || 0}</strong>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3 w-full sm:w-auto">
          {/* Solve in Online Judge */}
          {onSolve && (
            <button
              onClick={() => onSolve(item.problem.id)}
              className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-indigo-600/20 cursor-pointer"
              title="Open and solve in Online Judge"
            >
              <Code className="h-4 w-4" />
              <span>Solve in Judge</span>
            </button>
          )}

          {/* Solved */}
          <button
            onClick={() => onAction(item.problem.id, 'SOLVED')}
            disabled={loading}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-emerald-600/20"
          >
            <CheckCircle2 className="h-4 w-4" />
            Solved (+Box)
            <kbd className="ml-1 px-1.5 py-0.5 bg-emerald-700 rounded text-[10px]">S</kbd>
          </button>

          {/* Needs Revisit */}
          <button
            onClick={() => onAction(item.problem.id, 'NEEDS_REVISIT')}
            disabled={loading}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-rose-600/20"
          >
            <RotateCcw className="h-4 w-4" />
            Needs Revisit (Box 1)
            <kbd className="ml-1 px-1.5 py-0.5 bg-rose-700 rounded text-[10px]">R</kbd>
          </button>

          {/* Skip */}
          <button
            onClick={() => onAction(item.problem.id, 'SKIPPED')}
            disabled={loading}
            className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs rounded-xl transition border border-slate-700"
          >
            <MinusCircle className="h-3.5 w-3.5" />
            Skip
          </button>
        </div>
      </div>
    </div>
  );
}

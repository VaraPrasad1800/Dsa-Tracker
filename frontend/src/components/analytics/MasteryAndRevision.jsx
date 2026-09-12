import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, AlertCircle, ArrowRight, BookOpen, Layers } from 'lucide-react';
import { extendedAnalyticsApi } from '../../api/client';

const MASTERY_COLORS = {
  Mastered: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  Strong: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
  Practicing: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  Familiar: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  Beginner: 'bg-slate-800 text-slate-400 border-white/5',
};

export default function MasteryAndRevision({ onSelectTopic, onSelectProblem }) {
  const { data: masteryData } = useQuery({
    queryKey: ['analytics_mastery'],
    queryFn: async () => {
      const res = await extendedAnalyticsApi.getMastery();
      return res.data;
    },
  });

  const { data: revisionData } = useQuery({
    queryKey: ['analytics_revision_queue'],
    queryFn: async () => {
      const res = await extendedAnalyticsApi.getRevisionQueue();
      return res.data;
    },
  });

  const topics = masteryData?.topics || [];
  const queue = revisionData?.revision_queue || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Topic Mastery Levels */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl p-6 border border-white/[0.08] space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Algorithmic Topic Mastery</h2>
          </div>
          <span className="text-xs text-slate-400">{topics.length} Topics Tracked</span>
        </div>

        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {topics.length === 0 ? (
            <div className="text-slate-500 text-xs py-8 text-center">No topic data yet</div>
          ) : (
            topics.map((t) => (
              <div
                key={t.id}
                onClick={() => onSelectTopic && onSelectTopic(t.name)}
                className="p-3.5 rounded-2xl bg-slate-950/60 border border-white/[0.04] hover:border-indigo-500/30 transition cursor-pointer flex items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-xs">{t.name}</span>
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                        MASTERY_COLORS[t.mastery_level] || MASTERY_COLORS.Beginner
                      }`}
                    >
                      {t.mastery_level}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Solved {t.solved} / {t.total} ({t.percentage}%) • {t.medium_hard_solved} Medium/Hard
                  </div>
                </div>

                <div className="w-16 text-right">
                  <div className="text-xs font-bold text-slate-300">{t.percentage}%</div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full mt-1 overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${Math.min(100, t.percentage)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Priority Revision Queue */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl p-6 border border-white/[0.08] space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-amber-400" />
            <h2 className="text-base font-bold text-white">Smart Revision Queue</h2>
          </div>
          <span className="text-xs text-amber-400/90 font-medium">
            {queue.length} Due or Recommended
          </span>
        </div>

        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {queue.length === 0 ? (
            <div className="text-slate-500 text-xs py-8 text-center">
              All caught up! No overdue cards or revisits in queue.
            </div>
          ) : (
            queue.map((item, idx) => (
              <div
                key={`${item.problem_id}-${idx}`}
                className="p-3.5 rounded-2xl bg-slate-950/60 border border-white/[0.04] flex items-center justify-between gap-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 truncate">
                    {item.question_number && (
                      <span className="font-mono text-indigo-400 font-bold text-xs shrink-0">
                        #{item.question_number}
                      </span>
                    )}
                    <span className="font-semibold text-white text-xs truncate">
                      {item.problem_title}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 ${
                        item.difficulty === 'Easy'
                          ? 'text-emerald-400 bg-emerald-500/10'
                          : item.difficulty === 'Medium'
                          ? 'text-amber-400 bg-amber-500/10'
                          : 'text-rose-400 bg-rose-500/10'
                      }`}
                    >
                      {item.difficulty}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-400 mt-1 capitalize">
                    Reason: <span className="text-slate-300">{item.reason.replace(/_/g, ' ')}</span>
                    {item.leitner_box && (
                      <span className="ml-2 text-indigo-400 font-medium">
                        (Box {item.leitner_box})
                      </span>
                    )}
                  </div>
                </div>

                {onSelectProblem && (
                  <button
                    onClick={() => onSelectProblem(item.problem_id)}
                    className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-indigo-400 transition shrink-0"
                    title="Practice Now"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

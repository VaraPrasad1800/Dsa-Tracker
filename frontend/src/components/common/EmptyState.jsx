import React from 'react';
import { Search, Inbox, BarChart3, CalendarX, BookOpen } from 'lucide-react';

const PRESETS = {
  search: {
    Icon: Search,
    title: 'No results found',
    body: 'Try adjusting your search or clearing active filters.',
    iconColor: 'text-slate-500',
    iconBg: 'bg-slate-800/50',
  },
  noproblems: {
    Icon: Inbox,
    title: 'No problems here yet',
    body: "Problems you add will show up here. Start by exploring the full problem bank.",
    iconColor: 'text-indigo-400',
    iconBg: 'bg-indigo-500/10',
  },
  noanalytics: {
    Icon: BarChart3,
    title: 'Nothing to analyze yet',
    body: 'Solve a few problems to start seeing your performance trends and insights.',
    iconColor: 'text-violet-400',
    iconBg: 'bg-violet-500/10',
  },
  noreview: {
    Icon: CalendarX,
    title: "You're all caught up!",
    body: "No problems are due for spaced review today. Check back tomorrow to keep your streak alive. 🎉",
    iconColor: 'text-emerald-400',
    iconBg: 'bg-emerald-500/10',
  },
  nostudyplan: {
    Icon: BookOpen,
    title: 'No active study plan',
    body: 'Generate a personalized study plan based on your current skill gaps and target timeline.',
    iconColor: 'text-blue-400',
    iconBg: 'bg-blue-500/10',
  },
  recent: {
    Icon: Inbox,
    title: 'No recent activity',
    body: 'Start solving problems to track your progress here.',
    iconColor: 'text-slate-500',
    iconBg: 'bg-slate-800/50',
  },
};

/**
 * Designed empty state with illustration and friendly copy.
 *
 * @param {'search'|'noproblems'|'noanalytics'|'noreview'|'nostudyplan'|'recent'} preset
 * @param {string} [title] - Override preset title
 * @param {string} [body] - Override preset body
 * @param {React.ReactNode} [action] - Optional CTA button
 * @param {'sm'|'md'|'lg'} [size]
 */
export default function EmptyState({ preset = 'search', title, body, action, size = 'md' }) {
  const p = PRESETS[preset] ?? PRESETS.search;
  const Icon = p.Icon;

  const sizeClasses = {
    sm: 'py-8',
    md: 'py-14',
    lg: 'py-20',
  };

  const iconSizes = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
  };

  const iconPadding = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-5',
  };

  return (
    <div className={`flex flex-col items-center justify-center text-center ${sizeClasses[size]}`}>
      {/* Icon container with radial glow */}
      <div className="relative mb-5">
        <div
          className={`${iconPadding[size]} rounded-2xl ${p.iconBg} border border-white/5 mb-1`}
          style={{ boxShadow: '0 0 40px rgba(0,0,0,0.3)' }}
        >
          <Icon className={`${iconSizes[size]} ${p.iconColor}`} />
        </div>
        {/* Subtle glow behind icon */}
        <div
          className="absolute inset-0 rounded-2xl blur-xl opacity-30"
          style={{ background: 'inherit' }}
        />
      </div>

      <h3 className="text-base font-semibold text-slate-200 mb-1.5">
        {title ?? p.title}
      </h3>
      <p className="text-sm text-slate-500 max-w-sm leading-relaxed">
        {body ?? p.body}
      </p>

      {action && (
        <div className="mt-5">{action}</div>
      )}
    </div>
  );
}

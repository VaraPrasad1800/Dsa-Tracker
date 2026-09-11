import React from 'react';
import { Tag as TagIcon, EyeOff } from 'lucide-react';
import { useTags } from '../../context/TagContext';

/**
 * Compact switch for showing/hiding topic tags across problem tables and modals.
 * The preference is persisted globally via TagContext (localStorage dsa_show_tags).
 */
export default function TagToggle({ compact = false, sidebarMode = false, collapsed = false }) {
  const { showTags, toggleShowTags } = useTags();

  if (sidebarMode) {
    return (
      <button
        onClick={toggleShowTags}
        title={showTags ? 'Hide topic tags (spoilers)' : 'Show topic tags'}
        className={`w-full flex items-center gap-3 transition-colors ${
          collapsed ? 'justify-center' : ''
        }`}
      >
        {showTags ? (
          <TagIcon className="h-4 w-4 shrink-0 text-indigo-400" style={{ width: 16, height: 16 }} />
        ) : (
          <EyeOff className="h-4 w-4 shrink-0 text-slate-500" style={{ width: 16, height: 16 }} />
        )}
        {!collapsed && (
          <span className="text-sm whitespace-nowrap">
            {showTags ? 'Tags Visible' : 'Tags Hidden'}
          </span>
        )}
      </button>
    );
  }

  return (
    <button
      onClick={toggleShowTags}
      title={showTags ? 'Hide topic tags to avoid spoilers' : 'Show topic tags'}
      className={`flex items-center gap-1.5 rounded-xl border transition-all duration-150 ${
        compact ? 'px-2.5 py-1 text-[11px]' : 'px-3 py-1.5 text-xs font-medium'
      } ${
        showTags
          ? 'bg-indigo-600/15 text-indigo-300 border-indigo-500/30 hover:bg-indigo-600/25'
          : 'bg-white/[0.03] text-slate-400 border-white/[0.06] hover:text-slate-200 hover:border-white/[0.12]'
      }`}
    >
      {showTags ? (
        <TagIcon className={compact ? 'h-3 w-3 text-indigo-400' : 'h-3.5 w-3.5 text-indigo-400'} />
      ) : (
        <EyeOff className={compact ? 'h-3 w-3 text-slate-500' : 'h-3.5 w-3.5 text-slate-500'} />
      )}
      <span className="font-medium">{showTags ? 'Tags On' : 'Tags Hidden'}</span>
    </button>
  );
}

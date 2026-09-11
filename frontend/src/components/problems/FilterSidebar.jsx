import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Filter,
  X,
  Building2,
  Tag as TagIcon,
  Star,
  ChevronDown,
  ChevronUp,
  Zap,
  Clock,
  Save,
  Trash2,
  Sparkles,
} from 'lucide-react';

const SORT_OPTIONS = [
  { value: 'random', label: 'Surprise Me (Shuffle)' },
  { value: 'frequency', label: 'Frequency (High → Low)' },
  { value: 'title', label: 'Title (A → Z)' },
  { value: '-title', label: 'Title (Z → A)' },
  { value: 'difficulty_asc', label: 'Difficulty (Easy → Hard)' },
  { value: 'difficulty_desc', label: 'Difficulty (Hard → Easy)' },
  { value: 'created', label: 'Newest First' },
];

const FILTER_PRESETS = [
  { id: 'unsolved', name: 'Unsolved', filters: { status: 'UNSOLVED' }, icon: Zap, color: 'text-indigo-400' },
  { id: 'revisit', name: 'Revisit Due', filters: { status: 'NEEDS_REVISIT' }, icon: Clock, color: 'text-rose-400' },
  { id: 'solved', name: 'Solved', filters: { status: 'SOLVED' }, icon: Zap, color: 'text-emerald-400' },
  { id: 'bookmarked', name: 'Bookmarked', filters: { bookmarked: 'true' }, icon: Star, color: 'text-amber-400' },
  { id: 'easy', name: 'Easy First', filters: { difficulty: 'Easy' }, icon: Zap, color: 'text-emerald-400' },
  { id: 'medium', name: 'Mediums', filters: { difficulty: 'Medium' }, icon: Zap, color: 'text-amber-400' },
  { id: 'hard', name: 'Hard Core', filters: { difficulty: 'Hard' }, icon: Zap, color: 'text-rose-400' },
];

export default function FilterSidebar({
  filters,
  onFilterChange,
  onClearFilters,
  onApplyPreset,
  onSavePreset,
  onDeletePreset,
  counts,
  availableTags = [],
  availableCompanies = [],
  hideCompanies = false,
  isOpenMobile,
  onCloseMobile,
  sortBy,
  onSortChange,
  customPresets = [],
}) {
  const [expandedSections, setExpandedSections] = useState({
    presets: true,
    difficulty: true,
    status: true,
    bookmarks: true,
    topics: true,
    companies: false,
  });

  const difficulties = [
    { value: '', label: 'All', count: counts?.total },
    { value: 'Easy', label: 'Easy', count: counts?.easy },
    { value: 'Medium', label: 'Medium', count: counts?.medium },
    { value: 'Hard', label: 'Hard', count: counts?.hard },
  ];

  const statuses = [
    { value: '', label: 'All Statuses', count: counts?.total },
    { value: 'UNSOLVED', label: 'Unsolved', count: counts?.unsolved },
    { value: 'SOLVED', label: 'Solved', count: counts?.solved },
    { value: 'NEEDS_REVISIT', label: 'Needs Revisit', count: counts?.needs_revisit },
    { value: 'SKIPPED', label: 'Skipped', count: counts?.skipped },
  ];

  const hasActiveFilters = Boolean(
    filters.difficulty || filters.status || filters.topic || filters.company || filters.bookmarked
  );

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const renderSection = ({ title, icon: Icon, children, sectionKey, count, iconColor = 'text-indigo-400' }) => (
    <div className="border-b border-white/[0.05] pb-3.5 last:border-b-0">
      <button
        onClick={() => toggleSection(sectionKey)}
        className="flex items-center gap-2 w-full py-1 text-left group"
      >
        <Icon className={`h-3.5 w-3.5 ${iconColor}`} />
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 group-hover:text-slate-200 transition-colors flex-1">
          {title}
        </span>
        {count !== undefined && (
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/[0.05] text-slate-400 font-medium">
            {count}
          </span>
        )}
        {expandedSections[sectionKey] ? (
          <ChevronUp className="h-3.5 w-3.5 text-slate-500" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {expandedSections[sectionKey] && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden pt-2.5 space-y-2"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );

  const sidebarContent = (
    <div className="space-y-4 text-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.07]">
        <div className="flex items-center gap-2 font-semibold text-white text-sm">
          <Filter className="h-4 w-4 text-indigo-400" />
          <span>Filters & Presets</span>
        </div>
        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors px-2 py-0.5 rounded-lg hover:bg-white/[0.05]"
          >
            <X className="h-3 w-3" /> Clear
          </button>
        )}
      </div>

      {/* Quick Presets */}
      {renderSection({
        title: 'Quick Presets',
        icon: Zap,
        iconColor: 'text-indigo-400',
        sectionKey: 'presets',
        children: (
          <div className="grid grid-cols-2 gap-1.5">
            {FILTER_PRESETS.map((preset) => {
              const Icon = preset.icon;
              const isActive = Object.entries(preset.filters).every(
                ([k, v]) => filters[k] === v
              );
              return (
                <button
                  key={preset.id}
                  onClick={() => onApplyPreset ? onApplyPreset(preset.filters) : onFilterChange(Object.keys(preset.filters)[0], Object.values(preset.filters)[0])}
                  className={`px-2.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 border transition-all duration-150 ${
                    isActive
                      ? 'bg-indigo-600/30 text-indigo-200 border-indigo-500/40 shadow-[0_0_10px_rgba(99,102,241,0.2)]'
                      : 'bg-white/[0.03] text-slate-400 border-white/[0.05] hover:border-white/[0.12] hover:text-slate-200'
                  }`}
                >
                  <Icon className={`h-3 w-3 ${preset.color}`} />
                  <span className="truncate">{preset.name}</span>
                </button>
              );
            })}
          </div>
        ),
      })}

      {/* Difficulty */}
      {renderSection({
        title: 'Difficulty',
        icon: Zap,
        iconColor: 'text-indigo-400',
        sectionKey: 'difficulty',
        count: counts?.total,
        children: (
          <div className="grid grid-cols-2 gap-1.5">
            {difficulties.map((d) => {
              const isSelected = (filters.difficulty || '') === d.value;
              return (
                <button
                  key={d.value}
                  onClick={() => onFilterChange('difficulty', d.value)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center justify-between border transition-all duration-150 ${
                    isSelected
                      ? 'bg-indigo-600/30 text-white border-indigo-500/50 shadow-[0_0_12px_rgba(99,102,241,0.25)]'
                      : 'bg-white/[0.03] text-slate-300 border-white/[0.05] hover:border-white/[0.12]'
                  }`}
                >
                  <span>{d.label}</span>
                  {d.count !== undefined && (
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-white/[0.05] text-slate-500'
                      }`}
                    >
                      {d.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ),
      })}

      {/* Status */}
      {renderSection({
        title: 'Status',
        icon: Clock,
        iconColor: 'text-rose-400',
        sectionKey: 'status',
        count: counts?.total,
        children: (
          <div className="space-y-1">
            {statuses.map((s) => {
              const isSelected = (filters.status || '') === s.value;
              return (
                <button
                  key={s.value}
                  onClick={() => onFilterChange('status', s.value)}
                  className={`w-full px-3 py-1.5 rounded-xl text-xs font-medium flex items-center justify-between border transition-all duration-150 ${
                    isSelected
                      ? 'bg-indigo-600/30 text-white border-indigo-500/50 shadow-[0_0_12px_rgba(99,102,241,0.25)]'
                      : 'bg-white/[0.03] text-slate-300 border-white/[0.05] hover:border-white/[0.12]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        s.value === 'SOLVED'
                          ? 'bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.5)]'
                          : s.value === 'NEEDS_REVISIT'
                          ? 'bg-rose-400 shadow-[0_0_6px_rgba(244,63,94,0.5)]'
                          : 'bg-slate-600'
                      }`}
                    />
                    <span>{s.label}</span>
                  </div>
                  {s.count !== undefined && (
                    <span className="text-[10px] text-slate-500">{s.count}</span>
                  )}
                </button>
              );
            })}
          </div>
        ),
      })}

      {/* Bookmarks */}
      {renderSection({
        title: 'Bookmarks',
        icon: Star,
        iconColor: 'text-amber-400',
        sectionKey: 'bookmarks',
        count: counts?.bookmarked,
        children: (
          <button
            onClick={() =>
              onFilterChange('bookmarked', filters.bookmarked === 'true' ? '' : 'true')
            }
            className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between border transition-all duration-150 ${
              filters.bookmarked === 'true'
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                : 'bg-white/[0.03] text-slate-300 border-white/[0.05] hover:border-white/[0.12]'
            }`}
          >
            <div className="flex items-center gap-2">
              <Star
                className={`h-3.5 w-3.5 ${
                  filters.bookmarked === 'true' ? 'fill-amber-400 text-amber-400' : 'text-slate-500'
                }`}
              />
              <span>Bookmarked only</span>
            </div>
            {counts?.bookmarked !== undefined && (
              <span className="text-[10px] text-slate-400">{counts.bookmarked}</span>
            )}
          </button>
        ),
      })}

      {/* Topics */}
      {renderSection({
        title: 'Topic / Pattern',
        icon: TagIcon,
        iconColor: 'text-indigo-400',
        sectionKey: 'topics',
        count: availableTags.length,
        children: (
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
            {availableTags.map((tag) => {
              const isSelected = filters.topic === tag.name;
              return (
                <button
                  key={tag.id}
                  onClick={() => onFilterChange('topic', isSelected ? '' : tag.name)}
                  className={`px-2.5 py-1 rounded-lg text-xs transition-all duration-150 border ${
                    isSelected
                      ? 'bg-indigo-600 text-white border-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.3)]'
                      : 'bg-white/[0.03] text-slate-400 border-white/[0.05] hover:border-white/[0.12] hover:text-slate-200'
                  }`}
                >
                  {tag.name}
                  {tag.problem_count ? (
                    <span className="ml-1 opacity-60 text-[10px]">({tag.problem_count})</span>
                  ) : null}
                </button>
              );
            })}
          </div>
        ),
      })}

      {/* Companies */}
      {!hideCompanies &&
        availableCompanies.length > 0 &&
        renderSection({
          title: 'Target Company',
          icon: Building2,
          iconColor: 'text-violet-400',
          sectionKey: 'companies',
          count: availableCompanies.length,
          children: (
            <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pr-1">
              {availableCompanies.map((comp) => {
                const isSelected = filters.company === comp.name;
                return (
                  <button
                    key={comp.id}
                    onClick={() => onFilterChange('company', isSelected ? '' : comp.name)}
                    className={`px-2.5 py-1 rounded-lg text-xs transition-all duration-150 border ${
                      isSelected
                        ? 'bg-violet-600 text-white border-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.3)]'
                        : 'bg-white/[0.03] text-slate-400 border-white/[0.05] hover:border-white/[0.12] hover:text-slate-200'
                    }`}
                  >
                    {comp.name}
                  </button>
                );
              })}
            </div>
          ),
        })}
    </div>
  );

  return (
    <>
      {/* Desktop Sticky Sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 glass-card rounded-2xl p-4 self-start sticky top-6 border border-white/[0.07]">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {isOpenMobile && (
          <div className="fixed inset-0 z-50 lg:hidden flex">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm"
              onClick={onCloseMobile}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="relative w-80 max-w-full glass-modal p-5 overflow-y-auto z-10 h-full"
            >
              <div className="flex justify-end mb-3">
                <button
                  onClick={onCloseMobile}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              {sidebarContent}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}

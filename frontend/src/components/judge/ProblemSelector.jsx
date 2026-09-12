import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, ChevronDown, Check, X } from 'lucide-react';
import { problemsApi } from '../../api/client';

export default function ProblemSelector({ selectedProblem, onSelectProblem }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const itemRefs = useRef([]);

  // Fetch problems dynamically based on search & difficulty filter
  const { data, isLoading } = useQuery({
    queryKey: ['problem_selector_search', searchTerm, difficultyFilter],
    queryFn: async () => {
      const params = {
        page_size: 50,
        sort: 'question_number',
      };
      if (searchTerm.trim()) {
        params.search = searchTerm.trim();
      }
      if (difficultyFilter) {
        params.difficulty = difficultyFilter;
      }
      const res = await problemsApi.getProblems(params);
      return res.data;
    },
    enabled: isOpen,
    staleTime: 1000 * 30,
  });

  const problems = data?.results || [];

  // Reset highlight when problem list changes
  useEffect(() => {
    setHighlightedIndex(0);
    itemRefs.current = [];
  }, [problems]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 40);
    }
  }, [isOpen]);

  // Scroll active item into view
  useEffect(() => {
    if (isOpen && itemRefs.current[highlightedIndex]) {
      itemRefs.current[highlightedIndex]?.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [highlightedIndex, isOpen]);

  // Close and select problem
  const handleSelect = useCallback(
    (prob) => {
      onSelectProblem(prob);
      setIsOpen(false);
      triggerRef.current?.focus();
    },
    [onSelectProblem]
  );

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) => (problems.length > 0 ? (prev + 1) % problems.length : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          problems.length > 0 ? (prev - 1 + problems.length) % problems.length : 0
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (problems[highlightedIndex]) {
          handleSelect(problems[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
        break;
      case 'Tab':
        setIsOpen(false);
        break;
      default:
        break;
    }
  };

  // Global Escape and capture-phase outside click handling
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(e) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target)
      ) {
        setIsOpen(false);
      }
    }

    function handleGlobalKeyDown(e) {
      if (e.key === 'Escape') {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener('mousedown', handleClickOutside, true);
    document.addEventListener('touchstart', handleClickOutside, true);
    document.addEventListener('keydown', handleGlobalKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true);
      document.removeEventListener('touchstart', handleClickOutside, true);
      document.removeEventListener('keydown', handleGlobalKeyDown);
    };
  }, [isOpen]);

  const getDifficultyClass = (diff) => {
    switch (diff) {
      case 'Easy':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'Medium':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'Hard':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      default:
        return 'text-slate-400 bg-slate-800';
    }
  };

  return (
    <div className="relative inline-block">
      {/* Selector Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className="flex items-center gap-2.5 bg-slate-950/90 hover:bg-slate-900 border border-white/10 hover:border-indigo-500/50 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold text-white transition max-w-xs sm:max-w-md md:max-w-lg truncate shadow-sm group focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
      >
        {selectedProblem ? (
          <div className="flex items-center gap-2 truncate">
            <span className="font-mono text-indigo-400 font-bold shrink-0">
              #{selectedProblem.question_number || selectedProblem.leetcode_id}
            </span>
            <span className="truncate text-slate-100">{selectedProblem.title}</span>
            <span className="text-slate-500 shrink-0">—</span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold border shrink-0 ${getDifficultyClass(
                selectedProblem.difficulty
              )}`}
            >
              {selectedProblem.difficulty}
            </span>
          </div>
        ) : (
          <span className="text-slate-400">Select a problem...</span>
        )}
        <ChevronDown
          className={`h-4 w-4 text-slate-400 group-hover:text-white transition ml-auto shrink-0 duration-200 ${
            isOpen ? 'rotate-180 text-indigo-400' : ''
          }`}
        />
      </button>

      {/* Dropdown Overlay Layering */}
      {isOpen && (
        <>
          {/* Subtle dismiss backdrop behind dropdown (z-40) */}
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px]"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Solid Popover Dropdown Panel (z-50) */}
          <div
            ref={dropdownRef}
            onKeyDown={handleKeyDown}
            role="listbox"
            tabIndex={-1}
            style={{ backgroundColor: '#0f172a' }}
            className="absolute left-0 top-full mt-2 w-[360px] sm:w-[480px] md:w-[540px] max-w-[calc(100vw-2rem)] border border-white/15 rounded-2xl shadow-2xl shadow-black/80 z-50 overflow-hidden flex flex-col max-h-[min(480px,calc(100vh-12rem))] focus:outline-none animate-in fade-in duration-150"
          >
            {/* Search Header */}
            <div
              style={{ backgroundColor: '#090d16' }}
              className="p-3 border-b border-white/[0.08] space-y-2.5"
            >
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400 pointer-events-none" />
                <input
                  ref={inputRef}
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search question # (e.g. 42) or title..."
                  className="w-full bg-slate-950 text-white text-xs sm:text-sm pl-9 pr-8 py-2 rounded-xl border border-white/10 focus:outline-none focus:border-indigo-500 placeholder:text-slate-500 font-mono"
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchTerm('');
                      inputRef.current?.focus();
                    }}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-white p-0.5"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              {/* Quick Difficulty Filter Pills */}
              <div className="flex items-center gap-1.5 text-[11px]">
                <span className="text-slate-400 font-medium mr-1">Filter:</span>
                {['', 'Easy', 'Medium', 'Hard'].map((diff) => (
                  <button
                    key={diff || 'all'}
                    type="button"
                    onClick={() => setDifficultyFilter(diff)}
                    className={`px-2.5 py-0.5 rounded-lg font-medium transition ${
                      difficultyFilter === diff
                        ? 'bg-indigo-500 text-white font-bold shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 bg-white/[0.04] hover:bg-white/[0.08]'
                    }`}
                  >
                    {diff || 'All'}
                  </button>
                ))}
              </div>
            </div>

            {/* Scrollable Results List */}
            <div
              ref={listRef}
              className="flex-1 overflow-y-auto p-1.5 divide-y divide-white/[0.03] overscroll-contain"
            >
              {isLoading ? (
                <div className="p-8 text-center text-xs text-slate-400 font-medium animate-pulse">
                  Searching problems...
                </div>
              ) : problems.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  No problems found matching{' '}
                  <span className="text-indigo-400 font-mono font-bold">"{searchTerm}"</span>.
                </div>
              ) : (
                problems.map((p, index) => {
                  const isSelected = selectedProblem?.id === p.id;
                  const isHighlighted = highlightedIndex === index;

                  return (
                    <button
                      key={p.id}
                      ref={(el) => (itemRefs.current[index] = el)}
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => handleSelect(p)}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      className={`w-full text-left px-3 py-2.5 rounded-xl text-xs sm:text-sm transition flex items-center justify-between gap-3 group cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-600/25 border border-indigo-500/40 text-white'
                          : isHighlighted
                          ? 'bg-white/[0.08] text-white'
                          : 'hover:bg-white/[0.05] text-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 truncate">
                        <span className="font-mono text-indigo-400 font-bold shrink-0 w-12 text-left">
                          #{p.question_number || p.leetcode_id}
                        </span>
                        <span
                          className={`font-semibold truncate ${
                            isSelected || isHighlighted ? 'text-white' : 'text-slate-200'
                          }`}
                        >
                          {p.title}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {p.is_judge_ready ? (
                          <span
                            className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            title="Fully configured for Online Judge"
                          >
                            Ready
                          </span>
                        ) : (
                          <span
                            className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-slate-800 text-slate-400 border border-white/5"
                            title="Configuration required for Online Judge"
                          >
                            Config Req
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getDifficultyClass(
                            p.difficulty
                          )}`}
                        >
                          {p.difficulty}
                        </span>
                        {isSelected && <Check className="h-4 w-4 text-indigo-400 shrink-0" />}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

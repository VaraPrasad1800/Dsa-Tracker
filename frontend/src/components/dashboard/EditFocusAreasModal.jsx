import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, X, Check, AlertCircle, RotateCcw, Target, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { problemsApi, focusTopicsApi } from '../../api/client';

export default function EditFocusAreasModal({ isOpen, onClose }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');

  // Fetch all available tags
  const { data: allTags = [], isLoading: loadingTags } = useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      const res = await problemsApi.getTags();
      return res.data;
    },
    enabled: isOpen,
  });

  // Fetch current user focus topics
  const { data: focusData, isLoading: loadingFocus } = useQuery({
    queryKey: ['user-focus-topics'],
    queryFn: async () => {
      const res = await focusTopicsApi.getFocusTopics();
      return res.data;
    },
    enabled: isOpen,
  });

  const [selectedIds, setSelectedIds] = useState([]);
  const [hasInitialized, setHasInitialized] = useState(false);

  // Initialize selected IDs when data loads
  React.useEffect(() => {
    if (isOpen && focusData?.focus_topics && !hasInitialized) {
      // If user had custom focus topics, preselect them
      if (focusData.is_custom) {
        setSelectedIds(focusData.focus_topics.map((t) => t.id));
      } else {
        setSelectedIds([]);
      }
      setHasInitialized(true);
    }
  }, [isOpen, focusData, hasInitialized]);

  // Reset initialization state on close
  React.useEffect(() => {
    if (!isOpen) {
      setHasInitialized(false);
      setSearch('');
    }
  }, [isOpen]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (topicIds) => {
      const res = await focusTopicsApi.updateFocusTopics(topicIds);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-stats'] });
      queryClient.invalidateQueries({ queryKey: ['user-focus-topics'] });
      toast.success(
        data.is_custom
          ? `Saved ${selectedIds.length} target focus areas!`
          : 'Reverted to automatic weak-topic detection'
      );
      onClose();
    },
    onError: (err) => {
      toast.error(err.response?.data?.error || 'Failed to save focus areas');
    },
  });

  const handleToggle = (tagId) => {
    if (selectedIds.includes(tagId)) {
      setSelectedIds(selectedIds.filter((id) => id !== tagId));
    } else {
      if (selectedIds.length >= 5) {
        toast.error('You can select a maximum of 5 focus areas');
        return;
      }
      setSelectedIds([...selectedIds, tagId]);
    }
  };

  const handleSave = () => {
    saveMutation.mutate(selectedIds);
  };

  const handleResetToAuto = () => {
    saveMutation.mutate([]);
  };

  const filteredTags = useMemo(() => {
    if (!search.trim()) return allTags;
    const q = search.toLowerCase().trim();
    return allTags.filter(
      (t) => t.name.toLowerCase().includes(q) || t.slug.toLowerCase().includes(q)
    );
  }, [allTags, search]);

  const selectedTagObjects = useMemo(() => {
    const idSet = new Set(selectedIds);
    return allTags.filter((t) => idSet.has(t.id));
  }, [allTags, selectedIds]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 bg-slate-950/70 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Target className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Customize Focus Areas
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Target up to 5 specific topics to track and practice on your dashboard.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Selected Badges Bar */}
        <div className="px-5 py-3 border-b border-white/[0.06] bg-slate-950/30 shrink-0">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="font-semibold text-slate-300">
              Selected Focus Areas
            </span>
            <span
              className={`font-mono font-bold ${
                selectedIds.length === 5 ? 'text-amber-400' : 'text-indigo-400'
              }`}
            >
              {selectedIds.length} / 5 selected
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5 min-h-[30px] items-center">
            {selectedTagObjects.length > 0 ? (
              selectedTagObjects.map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                >
                  <span>{tag.name}</span>
                  <button
                    type="button"
                    onClick={() => handleToggle(tag.id)}
                    className="hover:text-white text-indigo-400/80 transition"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500 italic">
                No custom topics chosen yet. Automatic weak topics are used by default.
              </span>
            )}
          </div>
        </div>

        {/* Search Filter */}
        <div className="px-5 py-3 border-b border-white/[0.06] bg-slate-900 shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search topics (e.g. Dynamic Programming, Trees, Graphs)..."
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-800/80 border border-white/10 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
        </div>

        {/* Topics List */}
        <div className="flex-1 p-5 overflow-y-auto space-y-1.5">
          {loadingTags || loadingFocus ? (
            <div className="space-y-2 py-4">
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="h-10 rounded-xl bg-slate-800/50 animate-pulse" />
              ))}
            </div>
          ) : filteredTags.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No matching topics found for "{search}".
            </div>
          ) : (
            filteredTags.map((tag) => {
              const isSelected = selectedIds.includes(tag.id);
              const isMaxReached = selectedIds.length >= 5 && !isSelected;
              const solvedCount = tag.user_progress?.solved || 0;
              const totalCount = tag.problem_count || 0;
              const pct = totalCount > 0 ? Math.round((solvedCount / totalCount) * 100) : 0;

              return (
                <button
                  key={tag.id}
                  type="button"
                  disabled={isMaxReached}
                  onClick={() => handleToggle(tag.id)}
                  className={`w-full flex items-center justify-between p-2.5 rounded-xl border text-left transition ${
                    isSelected
                      ? 'bg-indigo-500/15 border-indigo-500/40 text-white shadow-sm'
                      : isMaxReached
                      ? 'opacity-40 cursor-not-allowed border-white/5 bg-slate-900/40 text-slate-500'
                      : 'border-white/5 bg-slate-950/40 hover:bg-slate-800/50 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 transition ${
                        isSelected
                          ? 'bg-indigo-600 border-indigo-500 text-white'
                          : 'border-white/20 bg-slate-900'
                      }`}
                    >
                      {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                    </div>

                    <div className="truncate">
                      <div className="text-xs font-semibold truncate">{tag.name}</div>
                      <div className="text-[10px] text-slate-500">
                        {totalCount} problems • {solvedCount} solved ({pct}%)
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] font-mono shrink-0 ml-3 text-right">
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                        pct < 50
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}
                    >
                      {pct}% solved
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-white/10 bg-slate-950/70 shrink-0">
          <button
            type="button"
            onClick={handleResetToAuto}
            disabled={saveMutation.isPending}
            title="Clear manual selection and use automatic weak topic algorithm"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/5 transition"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset to Auto</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saveMutation.isPending}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-300 hover:bg-white/5 transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 text-white text-xs font-bold shadow-lg shadow-indigo-500/20 hover:brightness-110 transition disabled:opacity-50"
            >
              {saveMutation.isPending ? 'Saving...' : 'Save Focus Areas'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

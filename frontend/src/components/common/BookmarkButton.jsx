import React, { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { bookmarksApi } from '../../api/client';

/**
 * Star toggle for bookmarking a problem. Optimistic local state, rolls back
 * on error, and invalidates problem/company queries so lists stay in sync.
 *
 * Props:
 *   problemId – the problem UUID
 *   bookmarked – current server-side bookmark state
 *   className – extra classes for the button (sizing, etc.)
 */
export default function BookmarkButton({ problemId, bookmarked = false, className = '' }) {
  const queryClient = useQueryClient();
  const [isBookmarked, setIsBookmarked] = useState(bookmarked);

  // Keep local state in sync when the prop changes after a refetch.
  useEffect(() => {
    setIsBookmarked(bookmarked);
  }, [bookmarked]);

  const toggleMutation = useMutation({
    mutationFn: () => bookmarksApi.toggle(problemId),
    onMutate: () => {
      setIsBookmarked((prev) => !prev); // optimistic
    },
    onError: () => {
      setIsBookmarked((prev) => !prev); // roll back
    },
    onSuccess: (res) => {
      setIsBookmarked(res.data.bookmarked);
      queryClient.invalidateQueries(['problems']);
      queryClient.invalidateQueries(['company-problems']);
      queryClient.invalidateQueries(['bookmarks']);
    },
  });

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        toggleMutation.mutate();
      }}
      className={`transition ${className}`}
      title={isBookmarked ? 'Remove bookmark' : 'Bookmark this problem'}
    >
      <Star
        className={`h-3.5 w-3.5 transition ${
          isBookmarked
            ? 'fill-amber-400 text-amber-400'
            : 'text-slate-500 hover:text-amber-400'
        }`}
      />
    </button>
  );
}

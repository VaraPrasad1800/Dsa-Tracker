import React from 'react';

/**
 * Skeleton placeholder for loading states — shimmer effect.
 * Props:
 *  - className: additional sizing/positioning classes
 *  - rounded: border-radius variant ('sm'|'md'|'lg'|'xl'|'full')
 */
export function Skeleton({ className = '', rounded = 'md' }) {
  const radii = {
    sm: 'rounded',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
    '2xl': 'rounded-2xl',
    full: 'rounded-full',
  };
  return (
    <div
      className={`skeleton ${radii[rounded] ?? 'rounded-md'} ${className}`}
      aria-hidden="true"
    />
  );
}

/**
 * Skeleton version of a stat card (4-up row on dashboard).
 */
export function StatCardSkeleton() {
  return (
    <div className="glass-card rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-24" rounded="full" />
        <Skeleton className="h-5 w-5" rounded="full" />
      </div>
      <Skeleton className="h-8 w-16" rounded="lg" />
      <Skeleton className="h-2 w-full" rounded="full" />
    </div>
  );
}

/**
 * Skeleton version of a problem card.
 */
export function ProblemCardSkeleton() {
  return (
    <div className="glass-card rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-16" rounded="full" />
        <Skeleton className="h-4 w-4" rounded="full" />
      </div>
      <Skeleton className="h-4 w-4/5" rounded="md" />
      <Skeleton className="h-3 w-3/5" rounded="md" />
      <div className="flex gap-1.5 pt-1">
        <Skeleton className="h-5 w-14" rounded="full" />
        <Skeleton className="h-5 w-20" rounded="full" />
        <Skeleton className="h-5 w-12" rounded="full" />
      </div>
      <div className="pt-2 border-t border-white/5 flex items-center justify-between">
        <Skeleton className="h-4 w-20" rounded="md" />
        <div className="flex gap-1.5">
          <Skeleton className="h-7 w-7" rounded="lg" />
          <Skeleton className="h-7 w-7" rounded="lg" />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton grid of problem cards.
 */
export function ProblemCardGridSkeleton({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <ProblemCardSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * Skeleton table rows.
 */
export function TableRowSkeleton({ columns = 7 }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-3 px-4">
          <Skeleton className={`h-4 ${i === 0 ? 'w-36' : i === 1 ? 'w-14' : 'w-20'}`} rounded="md" />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton analytics chart block.
 */
export function ChartSkeleton({ height = 'h-48' }) {
  return (
    <div className={`glass-card rounded-2xl p-5 ${height} flex flex-col gap-3`}>
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-4" rounded="full" />
        <Skeleton className="h-4 w-32" rounded="md" />
      </div>
      <div className="flex-1 flex items-end gap-1.5 pt-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            style={{ height: `${20 + Math.random() * 70}%` }}
            rounded="sm"
          />
        ))}
      </div>
    </div>
  );
}

export default Skeleton;

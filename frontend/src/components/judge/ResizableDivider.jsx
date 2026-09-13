import React from 'react';
import { GripVertical, GripHorizontal } from 'lucide-react';

export default function ResizableDivider({
  direction = 'horizontal', // 'horizontal' divides left/right (vertical bar), 'vertical' divides top/bottom (horizontal bar)
  onMouseDown,
  onTouchStart,
  isDragging = false,
  className = '',
}) {
  const isHorizontalSplit = direction === 'horizontal';

  return (
    <div
      role="separator"
      tabIndex={0}
      aria-orientation={isHorizontalSplit ? 'vertical' : 'horizontal'}
      onMouseDown={onMouseDown}
      onTouchStart={onTouchStart}
      className={`relative group shrink-0 select-none flex items-center justify-center transition-colors duration-150 ${
        isHorizontalSplit
          ? 'w-2 cursor-col-resize hover:w-2 py-2'
          : 'h-2 cursor-row-resize hover:h-2 px-2'
      } ${
        isDragging
          ? 'bg-indigo-500/50 shadow-[0_0_8px_rgba(99,102,241,0.5)]'
          : 'bg-white/[0.04] hover:bg-indigo-500/30'
      } rounded-full ${className}`}
    >
      {/* Visual pill/dots grip indicator in center */}
      <div
        className={`rounded-full transition-all duration-150 ${
          isHorizontalSplit
            ? 'w-1 h-8 group-hover:h-12'
            : 'h-1 w-8 group-hover:w-12'
        } ${
          isDragging ? 'bg-indigo-400' : 'bg-slate-600 group-hover:bg-indigo-300'
        }`}
      />
    </div>
  );
}

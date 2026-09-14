import React from 'react';

// Convert a hex color to rgba with an alpha component (0-1 range).
// Handles #RGB, #RRGGBB, and raw fallbacks gracefully.
const hexToRgba = (hex, alpha = 1) => {
  if (!hex || typeof hex !== 'string') return `rgba(148,163,184,${alpha})`; // slate-400 fallback
  let h = hex.replace('#', '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  const num = parseInt(h, 16);
  const r = (num >> 16) & 0xff;
  const g = (num >> 8) & 0xff;
  const b = num & 0xff;
  return `rgba(${r},${g},${b},${alpha})`;
};

/**
 * Colored badge for a problem tag.
 *
 * Props:
 *   name    – tag name string
 *   color   – hex color (e.g. "#3b82f6") — falls back to slate if absent
 *   compact – use smaller sizing (11px text vs 11px with slightly more padding)
 */
export default function TagBadge({ name, color, compact = false, className = '' }) {
  const baseColor = hexToRgba(color || '#94a3b8', 1);
  const bgColor = hexToRgba(color || '#94a3b8', 0.12);
  const borderColor = hexToRgba(color || '#94a3b8', 0.28);

  return (
    <span
      style={{
        color: baseColor,
        backgroundColor: bgColor,
        borderColor: borderColor,
      }}
      className={`inline-flex items-center rounded border font-medium leading-none select-none ${
        compact ? 'text-[10px] px-1.5 py-[3px]' : 'text-[11px] px-2 py-[3px]'
      } ${className}`}
      title={name}
    >
      <span className="truncate">{name}</span>
    </span>
  );
}

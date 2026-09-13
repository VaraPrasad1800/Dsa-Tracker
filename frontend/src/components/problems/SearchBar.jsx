import React, { useRef, useEffect } from 'react';
import { Search, X, Sparkles } from 'lucide-react';

export default function SearchBar({
  value,
  onChange,
  onClear,
  placeholder = "Search by title, pattern, company... (Press / to focus)",
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key === 'k')) && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative w-full group">
      <div className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none transition-colors duration-150 text-slate-500 group-focus-within:text-indigo-400">
        <Search className="h-4 w-4" />
      </div>

      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-10 pr-16 py-2.5 text-xs sm:text-sm rounded-xl transition-all duration-200"
        style={{
          background: 'rgba(16, 16, 28, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          color: '#f1f5f9',
          boxShadow: '0 2px 12px rgba(0, 0, 0, 0.25)',
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
          e.currentTarget.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.12), 0 4px 20px rgba(0, 0, 0, 0.35)';
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
          e.currentTarget.style.boxShadow = '0 2px 12px rgba(0, 0, 0, 0.25)';
        }}
      />

      <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
        {value ? (
          <button
            onClick={onClear}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
            title="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : (
          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-slate-500 bg-white/[0.04] border border-white/[0.08] rounded">
            /
          </kbd>
        )}
      </div>
    </div>
  );
}

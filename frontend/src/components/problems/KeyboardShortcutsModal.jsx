import React from 'react';
import { X, Keyboard } from 'lucide-react';

export default function KeyboardShortcutsModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const shortcuts = [
    { key: 'S', desc: 'Mark problem Solved (Promote Leitner box by +1)' },
    { key: 'R', desc: 'Mark Needs Revisit (Reset problem to Box 1 for next-day review)' },
    { key: 'Esc', desc: 'Close any open modal or drawer' },
    { key: '?', desc: 'Open this keyboard shortcuts reference guide' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl relative">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2 text-white font-bold text-base">
            <Keyboard className="h-5 w-5 text-indigo-400" />
            <span>Keyboard Shortcuts</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded transition">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3 text-sm">
          {shortcuts.map((s, idx) => (
            <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-300">{s.desc}</span>
              <kbd className="px-2.5 py-1 rounded bg-slate-800 text-indigo-300 font-mono font-bold text-xs border border-slate-700">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={onClose}
            className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-md shadow-indigo-600/20"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

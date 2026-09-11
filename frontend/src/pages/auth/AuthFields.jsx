import React from 'react';
import { motion } from 'framer-motion';

export function Field({ label, id, type = 'text', value, onChange, placeholder, required = false, autoComplete, hint }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        autoComplete={autoComplete}
        className="w-full px-3.5 py-2.5 rounded-xl text-sm transition-all duration-200"
        style={{
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          color: '#f1f5f9',
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
          e.currentTarget.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.12)';
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
          e.currentTarget.style.boxShadow = 'none';
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
        }}
      />
      {hint && <p className="text-[11px] text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

export function SubmitButton({ children, disabled = false }) {
  return (
    <motion.button
      type="submit"
      whileTap={{ scale: 0.98 }}
      disabled={disabled}
      className="btn-primary w-full py-2.5 px-4 text-sm font-semibold rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed"
    >
      {children}
    </motion.button>
  );
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium leading-relaxed">
      {message}
    </div>
  );
}

export function SuccessBanner({ message }) {
  if (!message) return null;
  return (
    <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium leading-relaxed">
      {message}
    </div>
  );
}
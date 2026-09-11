import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Code2, Sparkles, ArrowLeft } from 'lucide-react';

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="min-h-screen aurora-bg text-slate-100 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glowing orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md relative z-10"
      >
        {/* Brand Header */}
        <div className="flex flex-col items-center mb-6">
          <Link to="/" className="group flex flex-col items-center">
            <div className="h-14 w-14 rounded-2xl bg-brand-gradient flex items-center justify-center shadow-brand-glow mb-3 group-hover:scale-105 transition-transform duration-200">
              <Code2 className="h-7 w-7 text-white" />
            </div>
            <h1 className="font-extrabold text-2xl text-white tracking-tight">DSA Tracker</h1>
          </Link>
          {subtitle && (
            <p className="text-slate-400 text-xs sm:text-sm mt-1 text-center max-w-xs">{subtitle}</p>
          )}
        </div>

        {/* Form Card */}
        <div className="glass-modal rounded-3xl p-6 sm:p-8 border border-white/[0.08] shadow-2xl relative overflow-hidden">
          {title && <h2 className="text-xl font-bold text-white mb-2">{title}</h2>}
          {children}
        </div>

        <p className="text-center text-xs text-slate-500 mt-6 flex items-center justify-center gap-1.5">
          <Link to="/" className="hover:text-indigo-400 transition flex items-center gap-1">
            <ArrowLeft className="h-3 w-3" /> Back to DSA Problem Bank
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
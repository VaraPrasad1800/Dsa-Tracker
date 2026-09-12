import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ExternalLink,
  Check,
  RotateCcw,
  Clock,
  Building2,
  FileText,
  Bookmark,
  BookmarkCheck,
  Code2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import TagBadge from '../common/TagBadge';
import BookmarkButton from '../common/BookmarkButton';
import { useTags } from '../../context/TagContext';

/* =============================================
   Difficulty badge — 3D embossed look
   ============================================= */
function DiffBadge({ difficulty }) {
  const cls = {
    Easy: 'badge-easy',
    Medium: 'badge-medium',
    Hard: 'badge-hard',
  }[difficulty] || 'badge-easy';

  return (
    <span className={`px-2.5 py-0.5 text-[11px] font-semibold rounded-full ${cls}`}>
      {difficulty}
    </span>
  );
}

/* =============================================
   Status indicator dot
   ============================================= */
function StatusDot({ status }) {
  const config = {
    SOLVED: { color: '#10b981', label: 'Solved', glow: 'rgba(16,185,129,0.5)' },
    NEEDS_REVISIT: { color: '#f43f5e', label: 'Revisit', glow: 'rgba(244,63,94,0.5)' },
    SKIPPED: { color: '#475569', label: 'Skipped', glow: 'none' },
    UNSOLVED: { color: '#334155', label: null, glow: 'none' },
  }[status] || { color: '#334155', label: null, glow: 'none' };

  return (
    <span className="flex items-center gap-1.5 text-[11px] font-medium" style={{ color: config.color }}>
      <span
        className="h-1.5 w-1.5 rounded-full shrink-0"
        style={{
          background: config.color,
          boxShadow: config.glow !== 'none' ? `0 0 6px ${config.glow}` : 'none',
        }}
      />
      {config.label}
    </span>
  );
}

function ProblemCardInner({ problem, onSelect, onQuickUpdateStatus, onSolve }) {
  const { showTags } = useTags();
  const [justSolved, setJustSolved] = useState(false);
  const status = problem.user_progress?.status || 'UNSOLVED';
  const box = problem.user_progress?.current_box;
  const link = problem.leetcode_url || problem.source_url;

  const handleAction = (e, newStatus, currentStatus) => {
    e.stopPropagation();
    if (newStatus === 'SOLVED' && currentStatus !== 'SOLVED') {
      setJustSolved(true);
      setTimeout(() => setJustSolved(false), 800);
    }
    onQuickUpdateStatus?.(problem.id, newStatus, currentStatus);
  };

  return (
    <motion.div
      onClick={() => onSelect?.(problem)}
      whileHover={{ y: -3 }}
      transition={{ type: 'spring', stiffness: 400, damping: 28 }}
      className="glass-card rounded-2xl p-4 cursor-pointer flex flex-col gap-3 relative overflow-hidden"
    >
      {/* Subtle top gradient accent */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(99,102,241,0.3), transparent)' }}
      />

      {/* Top row: difficulty + box + links */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <DiffBadge difficulty={problem.difficulty} />
          {box && (
            <span
              className="px-2 py-0.5 text-[10px] font-bold rounded-full"
              style={{
                background: 'rgba(99,102,241,0.12)',
                color: '#a5b4fc',
                border: '1px solid rgba(99,102,241,0.2)',
              }}
            >
              Box {box}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {problem.is_premium && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold"
              style={{
                background: 'rgba(245,158,11,0.12)',
                color: '#fbbf24',
                border: '1px solid rgba(245,158,11,0.25)',
              }}
            >
              P
            </span>
          )}
          {link && (
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              onClick={e => e.stopPropagation()}
              className="p-1 rounded-lg transition-colors"
              style={{ color: '#475569' }}
              onMouseEnter={e => e.currentTarget.style.color = '#6366f1'}
              onMouseLeave={e => e.currentTarget.style.color = '#475569'}
              title="Open on LeetCode"
            >
              <ExternalLink style={{ width: 13, height: 13 }} />
            </a>
          )}
          {problem.solution_api_url && (
            <Link
              to={`/problems/${problem.id}/solution`}
              onClick={e => e.stopPropagation()}
              className="p-1 rounded-lg transition-colors"
              style={{ color: '#475569' }}
              onMouseEnter={e => e.currentTarget.style.color = '#f59e0b'}
              onMouseLeave={e => e.currentTarget.style.color = '#475569'}
              title="View Solution"
            >
              <FileText style={{ width: 13, height: 13 }} />
            </Link>
          )}
          <BookmarkButton
            problemId={problem.id}
            bookmarked={problem.is_bookmarked}
            className="p-1 rounded-lg"
          />
        </div>
      </div>

      {/* Title */}
      <h3
        className="font-semibold text-sm leading-snug transition-colors duration-150 flex items-baseline gap-1.5"
        style={{ color: '#e2e8f0' }}
        onMouseEnter={e => e.currentTarget.style.color = '#a5b4fc'}
        onMouseLeave={e => e.currentTarget.style.color = '#e2e8f0'}
      >
        <span className="font-mono text-indigo-400 font-bold text-xs shrink-0">
          #{problem.question_number || problem.leetcode_id}
        </span>
        <span className="truncate">{problem.title}</span>
      </h3>

      {/* Tags */}
      {showTags && problem.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {problem.tags.slice(0, 4).map(t => (
            <TagBadge key={t.id} name={t.name} color={t.color} compact />
          ))}
          {problem.tags.length > 4 && (
            <span className="text-[10px]" style={{ color: '#475569', alignSelf: 'center' }}>
              +{problem.tags.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Companies */}
      {problem.companies?.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <Building2 style={{ width: 11, height: 11, color: '#334155', flexShrink: 0 }} />
          {problem.companies.slice(0, 3).map(c => (
            <span
              key={c.id}
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{
                background: 'rgba(99,102,241,0.08)',
                color: '#818cf8',
                border: '1px solid rgba(99,102,241,0.15)',
              }}
            >
              {c.name}
            </span>
          ))}
          {problem.companies.length > 3 && (
            <span className="text-[10px]" style={{ color: '#475569' }}>
              +{problem.companies.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer: status + quick actions */}
      <div
        className="mt-auto pt-2.5 flex items-center justify-between"
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
      >
        <div className="flex items-center gap-1.5">
          {status === 'SOLVED' ? (
            <StatusDot status="SOLVED" />
          ) : status === 'NEEDS_REVISIT' ? (
            <StatusDot status="NEEDS_REVISIT" />
          ) : (
            <span className="text-[11px]" style={{ color: '#334155' }}>
              <Clock style={{ width: 11, height: 11, display: 'inline', marginRight: 3 }} />
              Unsolved
            </span>
          )}
          {status === 'SOLVED' && problem.user_progress?.times_solved > 1 && (
            <span className="text-[10px]" style={{ color: '#475569' }}>
              ×{problem.user_progress.times_solved}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {onSolve && (
            <motion.button
              onClick={(e) => {
                e.stopPropagation();
                onSolve(problem.id);
              }}
              whileTap={{ scale: 0.9 }}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all duration-150"
              style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(168,85,247,0.25) 100%)',
                color: '#c084fc',
                border: '1px solid rgba(168,85,247,0.35)',
              }}
              title="Solve in Online Judge"
            >
              <Code2 style={{ width: 13, height: 13 }} />
              <span>Solve</span>
            </motion.button>
          )}

          {/* Solve button with pop animation */}
          <motion.button
            onClick={e => handleAction(e, 'SOLVED', status)}
            whileTap={{ scale: 0.85 }}
            animate={justSolved ? { scale: [1, 1.35, 1] } : {}}
            transition={{ duration: 0.35, type: 'spring', stiffness: 500 }}
            className="p-1.5 rounded-lg transition-all duration-150"
            style={{
              background: status === 'SOLVED' ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.04)',
              color: status === 'SOLVED' ? '#10b981' : '#475569',
              border: status === 'SOLVED' ? '1px solid rgba(16,185,129,0.3)' : '1px solid transparent',
              boxShadow: status === 'SOLVED' ? '0 0 10px rgba(16,185,129,0.2)' : 'none',
            }}
            title={status === 'SOLVED' ? 'Unmark Solved' : 'Mark Solved'}
          >
            <Check style={{ width: 14, height: 14 }} />
          </motion.button>

          <motion.button
            onClick={e => handleAction(e, 'NEEDS_REVISIT', status)}
            whileTap={{ scale: 0.85 }}
            className="p-1.5 rounded-lg transition-all duration-150"
            style={{
              background: status === 'NEEDS_REVISIT' ? 'rgba(244,63,94,0.15)' : 'rgba(255,255,255,0.04)',
              color: status === 'NEEDS_REVISIT' ? '#f43f5e' : '#475569',
              border: status === 'NEEDS_REVISIT' ? '1px solid rgba(244,63,94,0.3)' : '1px solid transparent',
            }}
            title={status === 'NEEDS_REVISIT' ? 'Unmark Needs Revisit' : 'Mark Needs Revisit'}
          >
            <RotateCcw style={{ width: 14, height: 14 }} />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

const ProblemCard = React.memo(ProblemCardInner);
export default ProblemCard;

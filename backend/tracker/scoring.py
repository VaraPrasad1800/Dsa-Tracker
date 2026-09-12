"""
DSA Tracker — Deterministic Scoring Constants
=============================================
All point values are defined here as named constants so they are easy to
configure without hunting through the codebase.  Nothing is magic-numbered.

RULE SUMMARY
------------
- Points are awarded server-side only; the frontend cannot forge a score.
- Duplicate events (e.g. solving the same problem twice) do NOT award points
  a second time for the base solve reward — only the first Accepted counts.
- Challenge completion bonus is awarded once per challenge.
- Streak milestone points are awarded once per milestone threshold.
- Achievements are unlocked once; duplicate unlock attempts are silently ignored.
- Run Code NEVER awards points.
- Wrong Answer NEVER awards points.
"""

# ---------------------------------------------------------------------------
# Base solve points (awarded on first Accepted submission per problem)
# ---------------------------------------------------------------------------
POINTS_EASY_SOLVE = 10
POINTS_MEDIUM_SOLVE = 25
POINTS_HARD_SOLVE = 50

# ---------------------------------------------------------------------------
# Review / Leitner points
# ---------------------------------------------------------------------------
POINTS_REVIEW_COMPLETED = 5   # Completing a due Leitner card review

# ---------------------------------------------------------------------------
# Challenge points
# ---------------------------------------------------------------------------
POINTS_CHALLENGE_COMPLETION = 50   # Completing all target problems in a challenge
POINTS_CHALLENGE_ON_TIME_BONUS = 25  # Extra bonus when completed before deadline

# ---------------------------------------------------------------------------
# Streak milestone points (awarded once per threshold)
# ---------------------------------------------------------------------------
POINTS_STREAK_7_DAY = 25
POINTS_STREAK_30_DAY = 100
POINTS_STREAK_100_DAY = 500

# ---------------------------------------------------------------------------
# Interview simulation
# ---------------------------------------------------------------------------
POINTS_INTERVIEW_PROBLEM_SOLVED = 30   # Per problem solved in interview simulation
POINTS_INTERVIEW_PERFECT = 75          # Bonus for solving all problems in a session

# ---------------------------------------------------------------------------
# Achievement unlock points (additional on top of achievement display)
# ---------------------------------------------------------------------------
POINTS_ACHIEVEMENT_UNLOCK = 15

# ---------------------------------------------------------------------------
# Judge limits (shared defaults — per-problem overrides stored on TestCase)
# ---------------------------------------------------------------------------
JUDGE_DEFAULT_TIME_LIMIT_SECONDS = 5
JUDGE_DEFAULT_MEMORY_LIMIT_MB = 128
JUDGE_MAX_SOURCE_SIZE_BYTES = 64 * 1024      # 64 KB
JUDGE_MAX_STDIN_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB

# ---------------------------------------------------------------------------
# Topic mastery thresholds (deterministic — no AI)
# Each level requires meeting ALL conditions in its row.
# ---------------------------------------------------------------------------
# Level name → (min_solved_pct, min_solved_count, min_medium_or_hard_solved)
MASTERY_LEVELS = [
    ("Beginner",   0,   0,  0),
    ("Familiar",  20,   2,  0),
    ("Practicing", 40,  5,  1),
    ("Strong",    65,  10,  3),
    ("Mastered",  85,  15,  5),
]
# MASTERY_LEVELS is ordered from strongest to weakest so we iterate in reverse
# and take the first level whose thresholds are all met.

# ---------------------------------------------------------------------------
# Weak topic threshold — topics below this solved-percentage are considered weak
# ---------------------------------------------------------------------------
WEAK_TOPIC_THRESHOLD_PCT = 50

# ---------------------------------------------------------------------------
# Revision queue ordering weights (lower = shown sooner)
# ---------------------------------------------------------------------------
REVISION_ORDER_OVERDUE_BOX1 = 0
REVISION_ORDER_OVERDUE_HIGHER_BOX = 1
REVISION_ORDER_NEEDS_REVISIT = 2
REVISION_ORDER_FAILED_SUBMISSION = 3
REVISION_ORDER_RECENTLY_SOLVED = 4

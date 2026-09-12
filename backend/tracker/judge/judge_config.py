"""
Centralized Judge Configuration & Authoritative Timing Policy
============================================================
Single authoritative source for execution time and memory limits across the Online Judge.

Key Principles:
1. The backend is 100% authoritative; the frontend can never override execution limits.
2. Per-problem configuration (`Problem.time_limit_ms`) takes precedence when configured.
3. Explicit fallback to difficulty-aware platform defaults when unconfigured:
   - Easy: 1,000 ms
   - Medium: 2,000 ms
   - Hard: 3,000 ms
4. Language execution policies (multipliers and JVM/interpreter startup allowances) are
   applied centrally so interpreted/bytecode languages are not penalized by false TLE.
5. Dual Timeout Protection:
   - Per-test-case timeout
   - Cumulative test suite timeout cap (preventing server runaway on large test suites)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tracker.models import Problem


# Platform-wide defaults by problem difficulty (in milliseconds)
DEFAULT_TIME_LIMIT_BY_DIFFICULTY = {
    'Easy': 1000,
    'Medium': 2000,
    'Hard': 3000,
}

PLATFORM_DEFAULT_TIME_LIMIT_MS = 2000
PLATFORM_DEFAULT_MEMORY_LIMIT_MB = 128

MIN_ALLOWED_TIME_LIMIT_MS = 100
MAX_ALLOWED_TIME_LIMIT_MS = 15000

# Centralized Language Execution Policy
# Accounts for interpreter (Python) and JVM (Java) startup and execution characteristics
LANGUAGE_TIME_MULTIPLIERS = {
    'c': 1.0,
    'cpp': 1.0,
    'java': 1.5,
    'python': 2.0,
}

LANGUAGE_BASE_STARTUP_MS = {
    'c': 0,
    'cpp': 0,
    'java': 150,     # JVM startup allowance
    'python': 80,    # Python interpreter boot allowance
}

# Maximum cumulative time permitted for an entire test suite execution
MAX_CUMULATIVE_SUBMISSION_TIME_MS = 30000


@dataclass(frozen=True)
class TimingConfig:
    base_time_limit_ms: int
    effective_time_limit_ms: int
    effective_time_limit_seconds: float
    memory_limit_mb: int
    cumulative_time_limit_ms: int
    is_explicit: bool
    source: str


def resolve_execution_timing(
    problem: Optional[Problem],
    language: str,
    total_tests: int = 1,
) -> TimingConfig:
    """
    Authoritatively resolves execution time and memory limits for a problem and language.

    The frontend cannot specify or override this limit.
    """
    # 1. Base time limit
    explicit_limit = getattr(problem, 'time_limit_ms', None) if problem else None
    if explicit_limit and MIN_ALLOWED_TIME_LIMIT_MS <= explicit_limit <= MAX_ALLOWED_TIME_LIMIT_MS:
        base_ms = explicit_limit
        is_explicit = True
        source = "problem_override"
    else:
        difficulty = getattr(problem, 'difficulty', 'Medium') if problem else 'Medium'
        base_ms = DEFAULT_TIME_LIMIT_BY_DIFFICULTY.get(difficulty, PLATFORM_DEFAULT_TIME_LIMIT_MS)
        is_explicit = False
        source = f"difficulty_default:{difficulty}"

    # 2. Apply centralized language execution policy
    lang_key = (language or 'python').lower()
    multiplier = LANGUAGE_TIME_MULTIPLIERS.get(lang_key, 1.0)
    startup_allowance = LANGUAGE_BASE_STARTUP_MS.get(lang_key, 0)

    effective_ms = int(base_ms * multiplier + startup_allowance)
    effective_ms = max(MIN_ALLOWED_TIME_LIMIT_MS, min(effective_ms, MAX_ALLOWED_TIME_LIMIT_MS))
    effective_seconds = round(effective_ms / 1000.0, 3)

    # 3. Memory limit
    explicit_mem = getattr(problem, 'memory_limit_mb', None) if problem else None
    mem_mb = explicit_mem if (explicit_mem and explicit_mem >= 16) else PLATFORM_DEFAULT_MEMORY_LIMIT_MB

    # 4. Cumulative submission cap across all tests
    tests_count = max(1, total_tests)
    cumulative_ms = min(tests_count * effective_ms, MAX_CUMULATIVE_SUBMISSION_TIME_MS)

    return TimingConfig(
        base_time_limit_ms=base_ms,
        effective_time_limit_ms=effective_ms,
        effective_time_limit_seconds=effective_seconds,
        memory_limit_mb=mem_mb,
        cumulative_time_limit_ms=cumulative_ms,
        is_explicit=is_explicit,
        source=source,
    )

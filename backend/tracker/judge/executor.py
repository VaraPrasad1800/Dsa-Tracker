"""
Judge executor — the bridge between the service layer and the sandbox.

This module:
  1. Looks up the language config (from languages.py)
  2. Builds the executor callable for the sandbox
  3. Exposes a clean run_code() function for "Run Code" (custom input, no progress)
  4. Exposes execute_against_tests() for use by the verdict engine
"""

from __future__ import annotations
from functools import partial
from typing import Optional

from tracker.judge.languages import get_language_config, SUPPORTED_LANGUAGES
from tracker.judge.sandbox import execute, ExecutionResult


def _make_executor(language: str, time_limit: float, memory_limit_mb: int):
    """Return a callable(source_code, stdin) -> ExecutionResult for this language."""
    cfg = get_language_config(language)
    eff_time = float(time_limit)
    eff_mem = int(memory_limit_mb)

    def _execute(source_code: str, stdin: str) -> ExecutionResult:
        return execute(
            language_config=cfg,
            source_code=source_code,
            stdin=stdin,
            time_limit_seconds=eff_time,
            memory_limit_mb=eff_mem,
        )

    return _execute


def run_code(
    language: str,
    source_code: str,
    stdin: str = "",
    time_limit_seconds: Optional[float] = None,
    memory_limit_mb: Optional[int] = None,
) -> ExecutionResult:
    """
    Execute *source_code* with *stdin* — used by the "Run Code" button.

    This DOES NOT compare against test cases and DOES NOT modify any progress.
    Returns an ExecutionResult with stdout / stderr / status.
    """
    cfg = get_language_config(language)   # raises ValueError for unsupported
    tl = time_limit_seconds or cfg["timeout_seconds"]
    ml = memory_limit_mb or cfg["memory_limit_mb"]
    executor = _make_executor(language, tl, ml)
    return executor(source_code, stdin)


def get_test_executor(
    language: str,
    time_limit_seconds: Optional[float] = None,
    memory_limit_mb: Optional[int] = None,
):
    """
    Return a (source_code, stdin) -> ExecutionResult callable for use
    by verdict.run_against_test_cases().
    """
    cfg = get_language_config(language)
    tl = time_limit_seconds or cfg["timeout_seconds"]
    ml = memory_limit_mb or cfg["memory_limit_mb"]
    return _make_executor(language, tl, ml)

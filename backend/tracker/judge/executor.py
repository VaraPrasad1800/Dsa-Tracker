"""
Judge executor — the bridge between the service layer and the sandbox.

This module:
  1. Looks up the language config (from languages.py)
  2. Builds the executor callable for the sandbox
  3. Exposes a clean run_code() function for "Run Code" (custom input, no progress)
  4. Exposes execute_against_tests() for use by the verdict engine
"""

from __future__ import annotations
import logging
from functools import partial
from typing import Optional

from tracker.judge.languages import get_language_config, SUPPORTED_LANGUAGES
from tracker.judge.sandbox import execute, ExecutionResult, BatchExecutionSandbox
from tracker.judge.judge0 import is_judge0_configured, execute_judge0

logger = logging.getLogger(__name__)


def _make_executor(language: str, time_limit: float, memory_limit_mb: int):
    """Return a callable(source_code, stdin) -> ExecutionResult for this language."""
    cfg = get_language_config(language)
    eff_time = float(time_limit)
    eff_mem = int(memory_limit_mb)

    def _execute(source_code: str, stdin: str) -> ExecutionResult:
        if is_judge0_configured():
            try:
                return execute_judge0(
                    language=language,
                    source_code=source_code,
                    stdin=stdin,
                    time_limit_seconds=eff_time,
                    memory_limit_mb=eff_mem,
                )
            except Exception as exc:
                logger.warning("Judge0 execution failed (%s); falling back to local sandbox.", exc)

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
    tl = float(time_limit_seconds) if time_limit_seconds is not None else float(cfg["timeout_seconds"])
    ml = int(memory_limit_mb) if memory_limit_mb is not None else int(cfg["memory_limit_mb"])
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
    Uses Judge0 when configured, or BatchExecutionSandbox for single-compilation local execution.
    """
    cfg = get_language_config(language)
    tl = float(time_limit_seconds) if time_limit_seconds is not None else float(cfg["timeout_seconds"])
    ml = int(memory_limit_mb) if memory_limit_mb is not None else int(cfg["memory_limit_mb"])

    if is_judge0_configured():
        return _make_executor(language, tl, ml)

    return BatchExecutionSandbox(cfg, tl, ml)



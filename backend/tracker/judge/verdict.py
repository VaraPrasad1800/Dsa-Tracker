"""
Verdict engine — compares actual vs expected output and aggregates results.

OUTPUT COMPARISON STRATEGIES
-----------------------------
Each problem carries an `output_checker` field that selects one of:

  EXACT                   Exact character match after stripping leading/trailing whitespace.
  NORMALIZED / NORMALIZED_TEXT
                          Whitespace-normalised line comparison (handles CRLF, trailing spaces,
                          extra blank lines).
  ALTERNATIVES            Pipe-separated acceptable answers (e.g. "bab|aba").
  BOOLEAN                 true/True/1 == true; false/False/0 == false.
  INTEGER                 Numeric integer equality (strips whitespace).
  FLOAT_WITH_TOLERANCE    Numeric float within 1e-5 relative/absolute tolerance.
  ARRAY                   Ordered space-separated tokens comparison.
  ORDER_INSENSITIVE_ARRAY Multiset equality (any order).
  JSON                    Recursive JSON equality.

VERDICT PRECEDENCE (highest priority first)
-------------------------------------------
COMPILE_ERROR     → stop immediately, no tests run
SYSTEM_ERROR      → internal judge failure
TLE               → time limit exceeded on at least one test
MLE               → memory limit exceeded
RUNTIME_ERROR     → non-zero exit on at least one test
WRONG_ANSWER      → output mismatch on at least one test
ACCEPTED          → all tests passed
"""

from __future__ import annotations
import re
import json
import math
from dataclasses import dataclass
from typing import Optional


VERDICT_PRIORITY = [
    "COMPILE_ERROR",
    "SYSTEM_ERROR",
    "EXECUTION_ERROR",
    "TLE",
    "MLE",
    "RUNTIME_ERROR",
    "WRONG_ANSWER",
    "ACCEPTED",
]


@dataclass
class TestCaseResult:
    test_index: int
    passed: bool
    verdict: str       # 'ACCEPTED', 'WRONG_ANSWER', 'TLE', 'MLE', 'RUNTIME_ERROR', etc.
    execution_time_ms: int
    memory_kb: int
    # Safe error message — never include hidden test expected output
    error_message: str = ""


@dataclass
class JudgeResult:
    final_verdict: str
    tests_passed: int
    tests_total: int
    execution_time_ms: int   # max across all test cases
    memory_kb: int           # max across all test cases
    # Only safe messages — no hidden test inputs/expected outputs
    error_message: str = ""
    compile_error: str = ""
    # Per-visible-test results (hidden tests: only pass/fail, never I/O)
    test_results: list[TestCaseResult] = None

    def __post_init__(self):
        if self.test_results is None:
            self.test_results = []


# ---------------------------------------------------------------------------
# Internal normalization helpers
# ---------------------------------------------------------------------------

def _normalize_output(raw: str) -> list[str]:
    """
    Normalize output to a list of stripped lines.
    Handles trailing newlines, CRLF, and trailing spaces.
    """
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _tokenize(s: str) -> list[str]:
    """Split on any whitespace and strip brackets/commas (for array-like outputs)."""
    return [t for t in re.sub(r'[\[\],\'"]', ' ', s).split() if t]


# ---------------------------------------------------------------------------
# Per-strategy comparison functions
# ---------------------------------------------------------------------------

def _check_exact(actual: str, expected: str) -> bool:
    return actual.strip() == expected.strip()


def _check_normalized_text(actual: str, expected: str) -> bool:
    if actual.strip() == expected.strip():
        return True
    return _normalize_output(actual) == _normalize_output(expected)


def _check_alternatives(actual: str, expected: str) -> bool:
    """Pipe-separated alternatives: any one matching → accepted."""
    alternatives = expected.split('|')
    for alt in alternatives:
        if _outputs_match(actual, alt.strip(), strategy='NORMALIZED_TEXT'):
            return True
    return False


def _check_boolean(actual: str, expected: str) -> bool:
    bool_map = {
        'true': True, '1': True,
        'false': False, '0': False,
    }
    a = actual.strip().lower()
    e = expected.strip().lower()
    if a in bool_map and e in bool_map:
        return bool_map[a] == bool_map[e]
    # Fallback: normalised text
    return _check_normalized_text(actual, expected)


def _check_integer(actual: str, expected: str) -> bool:
    try:
        return int(actual.strip()) == int(expected.strip())
    except (ValueError, TypeError):
        return _check_normalized_text(actual, expected)


def _check_float_with_tolerance(actual: str, expected: str, tol: float = 1e-5) -> bool:
    try:
        a = float(actual.strip())
        e = float(expected.strip())
        # Both NaN
        if math.isnan(a) and math.isnan(e):
            return True
        # Relative + absolute tolerance (same as math.isclose defaults)
        return math.isclose(a, e, rel_tol=tol, abs_tol=tol)
    except (ValueError, TypeError):
        return _check_normalized_text(actual, expected)


def _check_array(actual: str, expected: str) -> bool:
    """Ordered array: token-by-token comparison after stripping brackets/commas."""
    act_tokens = _tokenize(actual.strip())
    exp_tokens = _tokenize(expected.strip())
    if act_tokens == exp_tokens:
        return True
    # Also try JSON parse comparison (handles "[0, 1]" vs "0 1")
    try:
        act_j = json.loads(actual.strip())
        exp_j = json.loads(expected.strip())
        if isinstance(act_j, list) and isinstance(exp_j, list):
            return act_j == exp_j
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return False


def _check_order_insensitive_array(actual: str, expected: str) -> bool:
    """Multiset equality: same elements in any order."""
    act_tokens = _tokenize(actual.strip())
    exp_tokens = _tokenize(expected.strip())
    # Try numeric sort first (integers)
    try:
        act_nums = sorted(int(t) for t in act_tokens)
        exp_nums = sorted(int(t) for t in exp_tokens)
        if act_nums == exp_nums:
            return True
    except (ValueError, TypeError):
        pass
    # Float sort
    try:
        act_nums = sorted(float(t) for t in act_tokens)
        exp_nums = sorted(float(t) for t in exp_tokens)
        if act_nums == exp_nums:
            return True
    except (ValueError, TypeError):
        pass
    # String sort
    if sorted(act_tokens) == sorted(exp_tokens):
        return True
    # Also try JSON parse
    try:
        act_j = sorted(json.loads(actual.strip())) if actual.strip().startswith('[') else sorted(act_tokens)
        exp_j = sorted(json.loads(expected.strip())) if expected.strip().startswith('[') else sorted(exp_tokens)
        if act_j == exp_j:
            return True
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return False


def _check_json(actual: str, expected: str) -> bool:
    try:
        act_j = json.loads(actual.strip())
        exp_j = json.loads(expected.strip())
        return act_j == exp_j
    except (json.JSONDecodeError, ValueError, TypeError):
        return _check_normalized_text(actual, expected)


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

_STRATEGY_MAP = {
    'EXACT': _check_exact,
    'NORMALIZED': _check_normalized_text,
    'NORMALIZED_TEXT': _check_normalized_text,
    'BOOLEAN': _check_boolean,
    'INTEGER': _check_integer,
    'FLOAT_WITH_TOLERANCE': _check_float_with_tolerance,
    'ARRAY': _check_array,
    'ORDER_INSENSITIVE_ARRAY': _check_order_insensitive_array,
    'JSON': _check_json,
    'ALTERNATIVES': _check_alternatives,
}


def _outputs_match(actual: str, expected: str, strategy: str = 'NORMALIZED_TEXT') -> bool:
    """
    Return True if actual output matches expected under the given strategy.

    Strategy is one of the OUTPUT_CHECKER_CHOICES keys on Problem.output_checker.
    Defaults to NORMALIZED_TEXT if the strategy is unrecognised.

    The ALTERNATIVES strategy is automatically applied when expected contains '|'
    regardless of the strategy field, to preserve backwards compatibility.
    """
    # Always respect pipe-separated alternatives if expected contains '|' and
    # the chosen strategy is not itself ALTERNATIVES (avoid infinite recursion).
    if '|' in expected and strategy != 'ALTERNATIVES':
        return _check_alternatives(actual, expected)

    checker = _STRATEGY_MAP.get(strategy, _check_normalized_text)
    return checker(actual, expected)


# ---------------------------------------------------------------------------
# Verdict helpers
# ---------------------------------------------------------------------------

def _pick_worst_verdict(verdicts: list[str]) -> str:
    """Return the verdict with the highest priority (lowest index in VERDICT_PRIORITY)."""
    for v in VERDICT_PRIORITY:
        if v in verdicts:
            return v
    return "ACCEPTED"


def _sandbox_status_to_verdict(status: str) -> str:
    """Map sandbox ExecutionResult.status to a judge verdict string."""
    mapping = {
        "OK": "ACCEPTED",           # tentative — output comparison still needed
        "COMPILE_ERROR": "COMPILE_ERROR",
        "TLE": "TLE",
        "MLE": "MLE",
        "RUNTIME_ERROR": "RUNTIME_ERROR",
        "SYSTEM_ERROR": "SYSTEM_ERROR",
    }
    return mapping.get(status, "SYSTEM_ERROR")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_against_test_cases(
    executor_fn,          # callable(source, stdin) -> ExecutionResult
    test_cases: list,     # list of (input_text, expected_output, is_hidden, index)
    source_code: str,
    return_visible_details: bool = True,
    cumulative_time_limit_ms: Optional[int] = None,
    output_checker: str = 'NORMALIZED_TEXT',
) -> JudgeResult:
    """
    Run *source_code* against all *test_cases* using *executor_fn*.

    Args:
        executor_fn: function(source_code: str, stdin: str) -> ExecutionResult
        test_cases: list of (input_text, expected_output, is_hidden, test_index)
        source_code: the user's code
        return_visible_details: if True, include per-visible-test I/O in results.
                                  Hidden test I/O is NEVER returned regardless.
        cumulative_time_limit_ms: optional total cumulative runtime ceiling across all tests.
        output_checker: strategy key from Problem.output_checker (default: NORMALIZED_TEXT).

    Returns:
        JudgeResult with verdict, counts, and safe diagnostics.
    """
    if not test_cases:
        return JudgeResult(
            final_verdict="EXECUTION_ERROR",
            tests_passed=0,
            tests_total=0,
            execution_time_ms=0,
            memory_kb=0,
            error_message="No test cases configured for this problem.",
        )

    verdicts = []
    test_results = []
    tests_passed = 0
    max_time_ms = 0
    total_time_ms = 0
    max_memory_kb = 0
    compile_error = ""

    try:
        for input_text, expected_output, is_hidden, idx in test_cases:
            result = executor_fn(source_code, input_text)

            max_time_ms = max(max_time_ms, result.execution_time_ms)
            total_time_ms += result.execution_time_ms
            max_memory_kb = max(max_memory_kb, result.memory_kb)

            if result.status == "COMPILE_ERROR":
                # Compilation failed — no point running more tests
                compile_error = result.compile_error
                return JudgeResult(
                    final_verdict="COMPILE_ERROR",
                    tests_passed=0,
                    tests_total=len(test_cases),
                    execution_time_ms=max_time_ms,
                    memory_kb=max_memory_kb,
                    compile_error=compile_error[:2048],
                )

            sandbox_verdict = _sandbox_status_to_verdict(result.status)

            if sandbox_verdict == "ACCEPTED":
                # Compare output using the problem's configured strategy
                if _outputs_match(result.stdout, expected_output, strategy=output_checker):
                    verdict = "ACCEPTED"
                    tests_passed += 1
                else:
                    verdict = "WRONG_ANSWER"
            else:
                verdict = sandbox_verdict

            verdicts.append(verdict)

            # Safe per-test result
            tc_result = TestCaseResult(
                test_index=idx,
                passed=(verdict == "ACCEPTED"),
                verdict=verdict,
                execution_time_ms=result.execution_time_ms,
                memory_kb=result.memory_kb,
            )
            if verdict != "ACCEPTED" and not is_hidden:
                # Visible test: safe to show limited stderr
                tc_result.error_message = result.stderr[:256] if result.stderr else ""
            # Hidden tests: no details ever
            if not is_hidden and return_visible_details:
                test_results.append(tc_result)
            elif is_hidden:
                # Append minimal info (no I/O)
                test_results.append(tc_result)

            # Check cumulative submission timeout across tests
            if cumulative_time_limit_ms and total_time_ms > cumulative_time_limit_ms:
                verdicts.append("TLE")
                break

        final_verdict = _pick_worst_verdict(verdicts)

        return JudgeResult(
            final_verdict=final_verdict,
            tests_passed=tests_passed,
            tests_total=len(test_cases),
            execution_time_ms=max_time_ms,
            memory_kb=max_memory_kb,
            test_results=test_results,
        )
    finally:
        if hasattr(executor_fn, 'cleanup'):
            try:
                executor_fn.cleanup()
            except Exception:
                pass

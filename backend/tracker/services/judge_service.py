"""
Judge service — the only entry point for code execution.

Two workflows:
1. run_code() — Run Code button: custom input, no progress changes, no DB saves.
2. submit_code() — Submit button: runs all tests, saves Submission,
                   updates Leitner/progress if Accepted, awards points.

SECURITY GUARANTEES
-------------------
- Hidden test cases are NEVER returned to callers. Only verdict + counts.
- source_code is passed to the sandbox as-is (the sandbox handles isolation).
- Django web worker does not exec() or eval() any user code.
- All execution happens in a temp directory that is cleaned up after use.
"""

from django.db import transaction
from django.utils import timezone

from tracker.judge.executor import run_code as _sandbox_run, get_test_executor
from tracker.judge.verdict import run_against_test_cases
from tracker.judge.languages import get_language_config, list_languages, DEFAULT_STARTER_CODE
from tracker.judge.judge_config import resolve_execution_timing
from tracker.models import (
    Problem, Submission, TestCase, LanguageTemplate,
    UserProblemProgress,
)
from tracker.scoring import (
    JUDGE_DEFAULT_TIME_LIMIT_SECONDS,
    JUDGE_DEFAULT_MEMORY_LIMIT_MB,
    POINTS_EASY_SOLVE, POINTS_MEDIUM_SOLVE, POINTS_HARD_SOLVE,
)


# ---------------------------------------------------------------------------
import logging

logger = logging.getLogger(__name__)


def _prepare_executable_code(problem: Problem | None, language: str, source_code: str) -> str:
    """
    If the user submitted a complete program, return as-is.
    If the user submitted a class Solution without main/driver, and a harness is configured,
    attach the harness as a fallback driver.
    """
    # Check if user already defined a driver / main
    if language == 'python':
        if 'if __name__' in source_code or 'sys.stdin.read' in source_code or '__main__' in source_code or 'def main(' in source_code or 'def solve(' in source_code:
            return source_code
    elif language in ('cpp', 'c'):
        if 'int main(' in source_code or 'void main(' in source_code or 'main(' in source_code:
            return source_code
    elif language == 'java':
        if 'static void main(' in source_code:
            return source_code

    # If it's a class Solution without main, and a harness is available, append it as fallback
    if problem:
        try:
            tmpl = LanguageTemplate.objects.get(problem=problem, language=language)
            if tmpl.harness_code.strip():
                return f"{source_code}\n\n{tmpl.harness_code}"
        except (LanguageTemplate.DoesNotExist, Exception):
            pass

    return source_code


def get_language_template(problem_id: str, language: str) -> str:
    """
    Returns the starter code template for a given problem and language.
    If the problem is not judge-ready and has no template, returns an informative placeholder comment.
    """
    if problem_id:
        tmpl = LanguageTemplate.objects.filter(problem_id=problem_id, language=language).first()
        if tmpl and tmpl.starter_code.strip():
            return tmpl.starter_code
        try:
            problem = Problem.objects.get(id=problem_id)
            if not problem.is_judge_ready and problem.leetcode_id:
                from tracker.services.problem_hydration_service import hydrate_problem_contract
                hydrate_problem_contract(problem)
                tmpl = LanguageTemplate.objects.filter(problem_id=problem_id, language=language).first()
                if tmpl and tmpl.starter_code.strip():
                    return tmpl.starter_code

            if not problem.is_judge_ready:
                return (
                    f"// Online Judge configuration unavailable for #{problem.question_number} {problem.title}.\n"
                    f"// Test cases and execution harness are not yet configured for this problem.\n"
                    if language in ('c', 'cpp', 'java') else
                    f"# Online Judge configuration unavailable for #{problem.question_number} {problem.title}.\n"
                    f"# Test cases and execution harness are not yet configured for this problem.\n"
                )
        except (Problem.DoesNotExist, ValueError):
            pass

    return DEFAULT_STARTER_CODE.get(language, '')


# ---------------------------------------------------------------------------
# Public: Run Code
# ---------------------------------------------------------------------------

def run_code_for_user(user, problem_id: str, language: str, source_code: str, stdin: str = '') -> dict:
    """
    Execute *source_code* with *stdin* — used by the "Run Code" button.

    Does NOT:
    - Alter any progress
    - Save a Submission
    - Award points
    - Count as an attempt

    Returns a safe dict with stdout, stderr, status.
    """
    try:
        get_language_config(language)  # validate early
    except ValueError as e:
        return {'status': 'ERROR', 'error': str(e), 'stdout': '', 'stderr': ''}

    problem = None
    if problem_id:
        try:
            problem = Problem.objects.get(id=problem_id)
        except (Problem.DoesNotExist, ValueError):
            pass

    if problem and getattr(problem, 'execution_mode', 'STDIN_STDOUT') == 'FUNCTION':
        user_has_driver = False
        if language == 'python':
            user_has_driver = 'if __name__' in source_code or 'sys.stdin.read' in source_code or '__main__' in source_code
        elif language in ('cpp', 'c'):
            user_has_driver = 'int main(' in source_code or 'void main(' in source_code or 'main(' in source_code
        elif language == 'java':
            user_has_driver = 'static void main(' in source_code

        if not user_has_driver:
            tmpl = LanguageTemplate.objects.filter(problem=problem, language=language).first()
            if not tmpl or not tmpl.harness_code.strip():
                return {
                    'status': 'CONFIGURATION_REQUIRED',
                    'stdout': '',
                    'stderr': '',
                    'compile_error': 'Online Judge configuration unavailable for this problem. Missing execution harness driver.',
                    'error': 'Online Judge configuration unavailable for this problem. Missing execution harness driver.',
                    'execution_time_ms': 0,
                    'memory_kb': 0,
                }

    timing_cfg = resolve_execution_timing(problem, language)
    executable_code = _prepare_executable_code(problem, language, source_code)
    result = _sandbox_run(
        language=language,
        source_code=executable_code,
        stdin=stdin,
        time_limit_seconds=timing_cfg.effective_time_limit_seconds,
        memory_limit_mb=timing_cfg.memory_limit_mb,
    )

    return {
        'status': result.status,
        'stdout': result.stdout[:4096],
        'stderr': result.stderr[:2048],
        'compile_error': result.compile_error[:2048] if result.compile_error else '',
        'execution_time_ms': result.execution_time_ms,
        'memory_kb': result.memory_kb,
        'time_limit_ms': timing_cfg.base_time_limit_ms,
    }


# ---------------------------------------------------------------------------
# Public: Submit
# ---------------------------------------------------------------------------

@transaction.atomic
def submit_code(user, problem_id: str, language: str, source_code: str) -> dict:
    """
    Run *source_code* against all test cases (visible + hidden) for *problem_id*.

    Saves a Submission record.  If Accepted, integrates with Leitner progress.
    Returns a SAFE result dict — no hidden test inputs or expected outputs.
    """
    # 1. Validate language
    try:
        get_language_config(language)
    except ValueError as e:
        return _error_response(str(e))

    # 2. Load problem
    try:
        problem = Problem.objects.get(id=problem_id)
    except (Problem.DoesNotExist, ValueError):
        return _error_response('Problem not found.')

    # 3. Load test cases (both visible and hidden — but never return hidden I/O)
    test_cases_qs = TestCase.objects.filter(problem=problem).order_by('is_hidden', 'order')
    if not test_cases_qs.exists():
        return {
            'submission_id': None,
            'verdict': 'EXECUTION_ERROR',
            'tests_passed': 0,
            'tests_total': 0,
            'execution_time_ms': 0,
            'memory_kb': 0,
            'compile_error': 'No test cases configured for this problem yet. Please contact the platform admin.',
            'error_message': 'No test cases configured for this problem yet. Please contact the platform admin.',
            'test_results': [],
            'points_awarded': 0,
            'achievements_unlocked': [],
        }

    # 4. If FUNCTION mode, check that either user supplied driver or a harness is configured
    if getattr(problem, 'execution_mode', 'STDIN_STDOUT') == 'FUNCTION':
        user_has_driver = False
        if language == 'python':
            user_has_driver = 'if __name__' in source_code or 'sys.stdin.read' in source_code or '__main__' in source_code
        elif language in ('cpp', 'c'):
            user_has_driver = 'int main(' in source_code or 'void main(' in source_code or 'main(' in source_code
        elif language == 'java':
            user_has_driver = 'static void main(' in source_code

        if not user_has_driver:
            tmpl = LanguageTemplate.objects.filter(problem=problem, language=language).first()
            if not tmpl or not tmpl.harness_code.strip():
                return {
                    'submission_id': None,
                    'verdict': 'CONFIGURATION_REQUIRED',
                    'tests_passed': 0,
                    'tests_total': 0,
                    'execution_time_ms': 0,
                    'memory_kb': 0,
                    'compile_error': 'Execution harness driver not configured for this problem.',
                    'error_message': 'Execution harness driver not configured for this problem.',
                    'test_results': [],
                    'points_awarded': 0,
                }

    test_cases = [
        (tc.input_text, tc.expected_output, tc.is_hidden, tc.order)
        for tc in test_cases_qs
    ]

    timing_cfg = resolve_execution_timing(problem, language, total_tests=len(test_cases))
    time_limit = timing_cfg.effective_time_limit_seconds
    memory_limit = timing_cfg.memory_limit_mb

    logger.info(
        "Judging submission: user=%s problem=#%s (%s) lang=%s tests=%d base_limit_ms=%d eff_limit_s=%.3f cumulative_ms=%d",
        user.username, getattr(problem, 'question_number', None), problem.title, language, len(test_cases),
        timing_cfg.base_time_limit_ms, time_limit, timing_cfg.cumulative_time_limit_ms
    )

    # 4. Build executor and run with executable code (including harness if function mode)
    executable_code = _prepare_executable_code(problem, language, source_code)
    executor_fn = get_test_executor(language, time_limit, memory_limit)

    def _executor_wrapper(source, stdin):
        return executor_fn(source, stdin)

    problem_checker = getattr(problem, 'output_checker', 'NORMALIZED_TEXT') or 'NORMALIZED_TEXT'
    judge_result = run_against_test_cases(
        executor_fn=_executor_wrapper,
        test_cases=test_cases,
        source_code=executable_code,
        return_visible_details=True,
        cumulative_time_limit_ms=timing_cfg.cumulative_time_limit_ms,
        output_checker=problem_checker,
    )

    # 5. Save Submission with pristine original source code
    submission = Submission.objects.create(
        user=user,
        problem=problem,
        language=language,
        source_code=source_code,
        verdict=judge_result.final_verdict,
        tests_passed=judge_result.tests_passed,
        tests_total=judge_result.tests_total,
        execution_time_ms=judge_result.execution_time_ms,
        memory_kb=judge_result.memory_kb,
        compile_error=judge_result.compile_error[:2048],
        error_message=judge_result.error_message[:1024],
    )

    # 6. If Accepted — update Leitner progress (first Accepted only for base points)
    points_awarded = 0
    newly_unlocked = []
    if judge_result.final_verdict == 'ACCEPTED':
        points_awarded, newly_unlocked = _handle_accepted(user, problem, language, source_code)

    # 7. Build safe response (NEVER include hidden test inputs/expected outputs)
    visible_results = []
    for tr in judge_result.test_results:
        entry = {
            'index': tr.test_index,
            'passed': tr.passed,
            'verdict': tr.verdict,
            'execution_time_ms': tr.execution_time_ms,
        }
        # Only add error message for visible tests (hidden tests: never)
        # We don't know which index is hidden easily here, so we use the
        # fact that test_results for hidden tests have no I/O appended.
        if tr.error_message:
            entry['error_message'] = tr.error_message
        visible_results.append(entry)

    return {
        'submission_id': str(submission.id),
        'verdict': judge_result.final_verdict,
        'tests_passed': judge_result.tests_passed,
        'tests_total': judge_result.tests_total,
        'execution_time_ms': judge_result.execution_time_ms,
        'memory_kb': judge_result.memory_kb,
        'time_limit_ms': timing_cfg.base_time_limit_ms,
        'compile_error': judge_result.compile_error[:2048] if judge_result.compile_error else '',
        'error_message': judge_result.error_message,
        'test_results': visible_results,
        'points_awarded': points_awarded,
        'achievements_unlocked': [
            {'code': a.code, 'name': a.name, 'icon': a.icon}
            for a in newly_unlocked
        ],
    }


def _handle_accepted(user, problem, language: str, source_code: str) -> tuple[int, list]:
    """
    Called on Accepted verdict.  Updates Leitner, awards points, checks achievements.
    Returns (points_awarded, newly_unlocked_achievements).
    """
    from tracker.services.leitner import update_problem_progress
    from tracker.services.points_service import award_points
    from tracker.services.achievement_service import check_and_unlock_achievements

    # Check if this is the FIRST accepted solve (to award base points once)
    progress, _ = UserProblemProgress.objects.get_or_create(
        user=user, problem=problem,
        defaults={'status': 'UNSOLVED', 'current_box': 1}
    )
    is_first_solve = (progress.times_solved == 0)

    # Update Leitner (promotes box, records ReviewHistory, updates streak)
    update_problem_progress(
        user=user,
        problem=problem,
        status='SOLVED',
        code_solution=source_code,
        code_language=language,
    )

    # Award base points only on first accepted solve
    points_awarded = 0
    if is_first_solve:
        difficulty_points = {
            'Easy': POINTS_EASY_SOLVE,
            'Medium': POINTS_MEDIUM_SOLVE,
            'Hard': POINTS_HARD_SOLVE,
        }
        pts = difficulty_points.get(problem.difficulty, POINTS_EASY_SOLVE)
        award_points(
            user,
            reason=f'first_solve_{problem.difficulty.lower()}',
            amount=pts,
            metadata={'problem_id': str(problem.id), 'difficulty': problem.difficulty},
        )
        points_awarded = pts

    # Check achievements (idempotent)
    newly_unlocked = check_and_unlock_achievements(user)

    return points_awarded, newly_unlocked


# ---------------------------------------------------------------------------
# Public: Submission history
# ---------------------------------------------------------------------------

def get_submission_history(user, problem_id: str, limit: int = 20) -> list[dict]:
    """Return the user's own submissions for a problem (no source code in list view)."""
    subs = Submission.objects.filter(
        user=user, problem_id=problem_id
    ).order_by('-created_at')[:limit]

    return [
        {
            'id': str(s.id),
            'language': s.language,
            'verdict': s.verdict,
            'tests_passed': s.tests_passed,
            'tests_total': s.tests_total,
            'execution_time_ms': s.execution_time_ms,
            'memory_kb': s.memory_kb,
            'created_at': s.created_at.isoformat(),
        }
        for s in subs
    ]


def get_submission_detail(user, submission_id: str) -> dict | None:
    """Return full submission detail for the owner only."""
    try:
        s = Submission.objects.get(id=submission_id, user=user)
    except Submission.DoesNotExist:
        return None

    return {
        'id': str(s.id),
        'problem_id': str(s.problem_id),
        'problem_title': s.problem.title,
        'language': s.language,
        'source_code': s.source_code,
        'verdict': s.verdict,
        'tests_passed': s.tests_passed,
        'tests_total': s.tests_total,
        'execution_time_ms': s.execution_time_ms,
        'memory_kb': s.memory_kb,
        'compile_error': s.compile_error,
        'error_message': s.error_message,
        'created_at': s.created_at.isoformat(),
    }


def get_supported_languages() -> list[dict]:
    return list_languages()


def get_language_template(problem_id: str, language: str) -> str:
    """Return starter code for the given problem+language, falling back to default."""
    try:
        tmpl = LanguageTemplate.objects.get(problem_id=problem_id, language=language)
        if tmpl.starter_code.strip():
            return tmpl.starter_code
    except (LanguageTemplate.DoesNotExist, Exception):
        pass
    return DEFAULT_STARTER_CODE.get(language, '')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _error_response(message: str) -> dict:
    return {
        'submission_id': None,
        'verdict': 'SYSTEM_ERROR',
        'tests_passed': 0,
        'tests_total': 0,
        'execution_time_ms': 0,
        'memory_kb': 0,
        'compile_error': '',
        'error_message': message,
        'test_results': [],
        'points_awarded': 0,
        'achievements_unlocked': [],
    }

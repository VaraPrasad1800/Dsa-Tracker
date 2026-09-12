import time
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tracker.models import Problem, TestCase as ProblemTestCase, Submission
from tracker.judge.judge_config import (
    resolve_execution_timing,
    DEFAULT_TIME_LIMIT_BY_DIFFICULTY,
    MAX_CUMULATIVE_SUBMISSION_TIME_MS,
)
from tracker.services.judge_service import run_code_for_user, submit_code
from tracker.serializers import ProblemSerializer, ProblemListSerializer

User = get_user_model()


class ProblemTimeLimitsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.easy_problem = Problem.objects.create(
            question_number=901,
            title='Easy Timing Test',
            slug='easy-timing-test',
            difficulty='Easy',
            execution_mode='STDIN_STDOUT',
            time_limit_ms=1000,
            memory_limit_mb=128,
        )
        self.medium_problem = Problem.objects.create(
            question_number=902,
            title='Medium Timing Test',
            slug='medium-timing-test',
            difficulty='Medium',
            execution_mode='STDIN_STDOUT',
            time_limit_ms=2000,
            memory_limit_mb=128,
        )
        self.hard_problem = Problem.objects.create(
            question_number=903,
            title='Hard Timing Test',
            slug='hard-timing-test',
            difficulty='Hard',
            execution_mode='STDIN_STDOUT',
            time_limit_ms=3000,
            memory_limit_mb=128,
        )
        self.custom_problem = Problem.objects.create(
            question_number=904,
            title='Custom Override Test',
            slug='custom-override-test',
            difficulty='Medium',
            execution_mode='STDIN_STDOUT',
            time_limit_ms=300,
            memory_limit_mb=64,
        )

        ProblemTestCase.objects.create(
            problem=self.easy_problem,
            input_text='5',
            expected_output='10',
            is_hidden=False,
            order=1,
        )
        ProblemTestCase.objects.create(
            problem=self.custom_problem,
            input_text='7',
            expected_output='14',
            is_hidden=False,
            order=1,
        )

    def test_model_validators_reject_invalid_limits(self):
        """Database validators reject limits outside [100, 15000]ms and [16, 1024]MB."""
        invalid_p1 = Problem(
            title='Too Fast',
            slug='too-fast',
            time_limit_ms=50,  # Below min 100ms
        )
        with self.assertRaises(ValidationError):
            invalid_p1.full_clean()

        invalid_p2 = Problem(
            title='Too Slow',
            slug='too-slow',
            time_limit_ms=20000,  # Above max 15000ms
        )
        with self.assertRaises(ValidationError):
            invalid_p2.full_clean()

        invalid_mem = Problem(
            title='Too Little Memory',
            slug='too-little-mem',
            memory_limit_mb=8,  # Below min 16MB
        )
        with self.assertRaises(ValidationError):
            invalid_mem.full_clean()

    def test_difficulty_aware_defaults(self):
        """Unconfigured problems correctly resolve to difficulty-aware platform defaults."""
        unconfigured = Problem.objects.create(
            title='Unconfigured Easy',
            slug='unconfigured-easy',
            difficulty='Easy',
            time_limit_ms=None,
        )
        cfg_c = resolve_execution_timing(unconfigured, 'c')
        self.assertEqual(cfg_c.base_time_limit_ms, 1000)
        self.assertEqual(cfg_c.effective_time_limit_ms, 1000)
        self.assertEqual(cfg_c.is_explicit, False)

        unconfigured_hard = Problem.objects.create(
            title='Unconfigured Hard',
            slug='unconfigured-hard',
            difficulty='Hard',
            time_limit_ms=None,
        )
        cfg_hard_cpp = resolve_execution_timing(unconfigured_hard, 'cpp')
        self.assertEqual(cfg_hard_cpp.base_time_limit_ms, 3000)
        self.assertEqual(cfg_hard_cpp.effective_time_limit_ms, 3000)

    def test_language_execution_policy(self):
        """Python and Java receive proper multipliers and startup allowances."""
        cfg_py = resolve_execution_timing(self.easy_problem, 'python')
        # Base: 1000ms -> Python multiplier 2.0 + 80ms startup = 2080ms
        self.assertEqual(cfg_py.base_time_limit_ms, 1000)
        self.assertEqual(cfg_py.effective_time_limit_ms, 2080)
        self.assertEqual(cfg_py.effective_time_limit_seconds, 2.08)

        cfg_java = resolve_execution_timing(self.easy_problem, 'java')
        # Base: 1000ms -> Java multiplier 1.5 + 150ms startup = 1650ms
        self.assertEqual(cfg_java.base_time_limit_ms, 1000)
        self.assertEqual(cfg_java.effective_time_limit_ms, 1650)
        self.assertEqual(cfg_java.effective_time_limit_seconds, 1.65)

        cfg_cpp = resolve_execution_timing(self.easy_problem, 'cpp')
        # Base: 1000ms -> C++ multiplier 1.0 + 0ms startup = 1000ms
        self.assertEqual(cfg_cpp.base_time_limit_ms, 1000)
        self.assertEqual(cfg_cpp.effective_time_limit_ms, 1000)
        self.assertEqual(cfg_cpp.effective_time_limit_seconds, 1.0)

    def test_per_problem_configured_override(self):
        """Configured per-problem limit overrides difficulty default."""
        cfg = resolve_execution_timing(self.custom_problem, 'cpp')
        self.assertEqual(cfg.base_time_limit_ms, 300)
        self.assertEqual(cfg.effective_time_limit_ms, 300)
        self.assertEqual(cfg.effective_time_limit_seconds, 0.3)
        self.assertEqual(cfg.is_explicit, True)

    def test_frontend_cannot_override_time_limit(self):
        """API ignores any client-supplied time_limit arguments."""
        # Attempt to supply massive timeout to bypass TLE
        payload = {
            'problem_id': str(self.custom_problem.id),
            'language': 'python',
            'source_code': "import time\ntime.sleep(2)\nprint(14)",
            'time_limit': 99999,
            'time_limit_ms': 99999,
        }
        res = self.client.post('/api/submit/', payload, format='json')
        self.assertEqual(res.status_code, 200)
        # Authoritative limit on custom_problem is 300ms base (effective Python: 680ms).
        # Sleeping 2s must exceed the limit and produce TLE.
        self.assertEqual(res.data['verdict'], 'TLE')

    def test_time_limit_exceeded_verdict(self):
        """Long-running or infinite loop produces TLE verdict."""
        # Custom problem has 300ms base limit (680ms effective for Python)
        infinite_code = "import time\ntime.sleep(1.5)\nprint(14)"
        result = submit_code(self.user, str(self.custom_problem.id), 'python', infinite_code)
        self.assertEqual(result['verdict'], 'TLE')
        self.assertEqual(result['tests_passed'], 0)

        # Verify Submission record was persisted with correct verdict
        sub = Submission.objects.get(id=result['submission_id'])
        self.assertEqual(sub.verdict, 'TLE')

    def test_efficient_solution_passes(self):
        """Efficient solution passes within authoritative time limit."""
        efficient_code = "import sys\nx = int(sys.stdin.read().strip())\nprint(x * 2)"
        result = submit_code(self.user, str(self.easy_problem.id), 'python', efficient_code)
        self.assertEqual(result['verdict'], 'ACCEPTED')
        self.assertEqual(result['tests_passed'], 1)
        self.assertEqual(result['tests_total'], 1)
        self.assertLess(result['execution_time_ms'], 1000)

    def test_hidden_test_cases_respect_time_limit(self):
        """Hidden test cases enforce the time limit without leaking inputs."""
        ProblemTestCase.objects.create(
            problem=self.easy_problem,
            input_text='100',
            expected_output='200',
            is_hidden=True,
            order=2,
        )
        # Passes for input '5', but loops on input '100'
        conditional_slow_code = """
import sys
x = int(sys.stdin.read().strip())
if x == 100:
    import time
    time.sleep(4)
print(x * 2)
"""
        result = submit_code(self.user, str(self.easy_problem.id), 'python', conditional_slow_code)
        self.assertEqual(result['verdict'], 'TLE')
        self.assertEqual(result['tests_passed'], 1)
        self.assertEqual(result['tests_total'], 2)

        # Guarantee no hidden test input/output is returned in test_results
        for tr in result['test_results']:
            self.assertNotIn('input', tr)
            self.assertNotIn('expected_output', tr)

    def test_cumulative_timeout_cap(self):
        """Cumulative timeout config caps multi-test execution."""
        cfg = resolve_execution_timing(self.easy_problem, 'python', total_tests=50)
        # 50 * 2080ms = 104,000ms, which must be capped at MAX_CUMULATIVE_SUBMISSION_TIME_MS (30,000ms)
        self.assertEqual(cfg.cumulative_time_limit_ms, MAX_CUMULATIVE_SUBMISSION_TIME_MS)

    def test_serializers_include_time_and_memory_limits(self):
        """Serializers expose authoritative time_limit_ms and memory_limit_mb."""
        ser = ProblemSerializer(self.easy_problem)
        self.assertEqual(ser.data['time_limit_ms'], 1000)
        self.assertEqual(ser.data['memory_limit_mb'], 128)

        list_ser = ProblemListSerializer(self.custom_problem)
        self.assertEqual(list_ser.data['time_limit_ms'], 300)
        self.assertEqual(list_ser.data['memory_limit_mb'], 64)

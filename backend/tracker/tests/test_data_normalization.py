"""
test_data_normalization.py — Regression tests for the canonical data contract pipeline.

Tests:
  1. canonical_serialization — parse, serialize, strategy detection
  2. verdict strategy dispatcher — each output_checker strategy
  3. run_against_test_cases — output_checker parameter threading
  4. normalize_judge_data command — dry-run behavior
  5. End-to-end regression: #1 Two Sum, #9 Palindrome Number, #20 Valid Parentheses

No hardcoded answers per problem — tests verify generic pipeline behavior.
"""

from django.test import TestCase as DjangoTestCase
from unittest.mock import MagicMock, patch


# ===========================================================================
# 1. canonical_serialization tests
# ===========================================================================

class TestParseRawValue(DjangoTestCase):
    """parse_raw_value correctly types various input strings."""

    def _parse(self, s, hint=''):
        from tracker.judge.canonical_serialization import parse_raw_value
        return parse_raw_value(s, hint)

    def test_integer(self):
        self.assertEqual(self._parse('9'), 9)

    def test_negative_integer(self):
        self.assertEqual(self._parse('-3'), -3)

    def test_float(self):
        self.assertAlmostEqual(self._parse('3.14'), 3.14)

    def test_boolean_true(self):
        self.assertIs(self._parse('true'), True)

    def test_boolean_false(self):
        self.assertIs(self._parse('false'), False)

    def test_quoted_string(self):
        self.assertEqual(self._parse('"hello"'), 'hello')

    def test_1d_array_int(self):
        self.assertEqual(self._parse('[2,7,11,15]'), [2, 7, 11, 15])

    def test_1d_array_empty(self):
        self.assertEqual(self._parse('[]'), [])

    def test_2d_array(self):
        self.assertEqual(self._parse('[[1,2],[3,4]]'), [[1, 2], [3, 4]])

    def test_plain_string(self):
        self.assertEqual(self._parse('hello'), 'hello')


class TestParseExampleArguments(DjangoTestCase):
    """parse_example_arguments extracts named/positional arguments."""

    def _parse(self, raw):
        from tracker.judge.canonical_serialization import parse_example_arguments
        return parse_example_arguments(raw)

    def test_named_two_args(self):
        args = self._parse('nums = [2,7,11,15], target = 9')
        names = [a[0] for a in args]
        vals = [a[1] for a in args]
        self.assertEqual(names, ['nums', 'target'])
        self.assertEqual(vals, [[2, 7, 11, 15], 9])

    def test_single_arg_no_equals(self):
        args = self._parse('[1,2,3]')
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0][1], [1, 2, 3])

    def test_empty_input(self):
        args = self._parse('')
        self.assertEqual(args, [])

    def test_boolean_arg(self):
        args = self._parse('flag = true')
        self.assertEqual(args[0][1], True)

    def test_string_arg(self):
        args = self._parse('s = "babad"')
        self.assertEqual(args[0][1], 'babad')


class TestSerializeToStdin(DjangoTestCase):
    """serialize_to_stdin produces canonical STDIN without brackets."""

    def _serialize(self, args):
        from tracker.judge.canonical_serialization import serialize_to_stdin
        return serialize_to_stdin(args)

    def test_two_sum_format(self):
        # nums=[2,7,11,15], target=9 → "4\n2 7 11 15\n9"
        stdin = self._serialize([('nums', [2, 7, 11, 15]), ('target', 9)])
        lines = stdin.splitlines()
        self.assertEqual(lines[0], '4')           # length of array
        self.assertEqual(lines[1], '2 7 11 15')   # space-separated elements
        self.assertEqual(lines[2], '9')            # scalar

    def test_empty_array(self):
        stdin = self._serialize([('nums', [])])
        lines = stdin.splitlines()
        self.assertEqual(lines[0], '0')

    def test_boolean(self):
        stdin = self._serialize([('flag', True)])
        self.assertEqual(stdin.strip(), 'true')

    def test_string(self):
        stdin = self._serialize([('s', 'hello')])
        self.assertEqual(stdin.strip(), 'hello')

    def test_2d_array(self):
        stdin = self._serialize([('matrix', [[1, 2], [3, 4]])])
        lines = stdin.splitlines()
        self.assertEqual(lines[0], '2 2')   # R C
        self.assertEqual(lines[1], '1 2')
        self.assertEqual(lines[2], '3 4')

    def test_no_brackets_in_output(self):
        stdin = self._serialize([('nums', [2, 7, 11, 15]), ('target', 9)])
        self.assertNotIn('[', stdin)
        self.assertNotIn(']', stdin)


class TestSerializeToExpectedStdout(DjangoTestCase):
    """serialize_to_expected_stdout produces canonical STDOUT."""

    def _serialize(self, raw_out, hint=''):
        from tracker.judge.canonical_serialization import serialize_to_expected_stdout
        return serialize_to_expected_stdout(raw_out, hint)

    def test_array_output(self):
        self.assertEqual(self._serialize('[0, 1]'), '0 1')

    def test_array_no_spaces(self):
        self.assertEqual(self._serialize('[0,1]'), '0 1')

    def test_boolean_true(self):
        self.assertEqual(self._serialize('true'), 'true')

    def test_boolean_false(self):
        self.assertEqual(self._serialize('false'), 'false')

    def test_integer(self):
        self.assertEqual(self._serialize('42'), '42')

    def test_string(self):
        self.assertEqual(self._serialize('"bab"'), 'bab')

    def test_2d_array(self):
        out = self._serialize('[[1,2],[3,4]]')
        lines = out.splitlines()
        self.assertEqual(lines[0], '1 2')
        self.assertEqual(lines[1], '3 4')


class TestDetermineOutputChecker(DjangoTestCase):
    """determine_output_checker selects correct strategy from problem context."""

    def _checker(self, desc='', ret='', examples=None):
        from tracker.judge.canonical_serialization import determine_output_checker
        return determine_output_checker(desc, ret, examples or [])

    def test_any_order_description(self):
        checker = self._checker(desc='Return the answer in any order.')
        self.assertEqual(checker, 'ORDER_INSENSITIVE_ARRAY')

    def test_bool_return_type(self):
        checker = self._checker(ret='bool')
        self.assertEqual(checker, 'BOOLEAN')

    def test_float_return_type(self):
        checker = self._checker(ret='double')
        self.assertEqual(checker, 'FLOAT_WITH_TOLERANCE')

    def test_list_return_type(self):
        checker = self._checker(ret='vector<int>')
        self.assertEqual(checker, 'ARRAY')

    def test_int_return_type(self):
        checker = self._checker(ret='int')
        self.assertEqual(checker, 'INTEGER')

    def test_example_output_array(self):
        checker = self._checker(examples=[{'output': '[0,1]'}])
        self.assertEqual(checker, 'ARRAY')

    def test_example_output_bool(self):
        checker = self._checker(examples=[{'output': 'true'}])
        self.assertEqual(checker, 'BOOLEAN')

    def test_example_output_integer(self):
        checker = self._checker(examples=[{'output': '42'}])
        self.assertEqual(checker, 'INTEGER')


# ===========================================================================
# 2. verdict strategy dispatcher tests
# ===========================================================================

class TestVerdictStrategies(DjangoTestCase):
    """Each output_checker strategy produces correct match/mismatch decisions."""

    def _match(self, actual, expected, strategy):
        from tracker.judge.verdict import _outputs_match
        return _outputs_match(actual, expected, strategy=strategy)

    # EXACT
    def test_exact_match(self):
        self.assertTrue(self._match('hello', 'hello', 'EXACT'))

    def test_exact_mismatch(self):
        self.assertFalse(self._match('hello', 'Hello', 'EXACT'))

    def test_exact_strips_whitespace(self):
        self.assertTrue(self._match('  42  ', '42', 'EXACT'))

    # NORMALIZED_TEXT
    def test_normalized_crlf(self):
        self.assertTrue(self._match('hello\r\n', 'hello\n', 'NORMALIZED_TEXT'))

    def test_normalized_trailing_space(self):
        self.assertTrue(self._match('hello   ', 'hello', 'NORMALIZED_TEXT'))

    # BOOLEAN
    def test_boolean_true_variations(self):
        self.assertTrue(self._match('True', 'true', 'BOOLEAN'))
        self.assertTrue(self._match('1', 'true', 'BOOLEAN'))

    def test_boolean_false_variations(self):
        self.assertTrue(self._match('False', 'false', 'BOOLEAN'))
        self.assertTrue(self._match('0', 'false', 'BOOLEAN'))

    def test_boolean_mismatch(self):
        self.assertFalse(self._match('true', 'false', 'BOOLEAN'))

    # INTEGER
    def test_integer_match(self):
        self.assertTrue(self._match('42', '42', 'INTEGER'))

    def test_integer_mismatch(self):
        self.assertFalse(self._match('42', '43', 'INTEGER'))

    def test_integer_leading_space(self):
        self.assertTrue(self._match('  42  ', '42', 'INTEGER'))

    # FLOAT_WITH_TOLERANCE
    def test_float_exact(self):
        self.assertTrue(self._match('3.14159', '3.14159', 'FLOAT_WITH_TOLERANCE'))

    def test_float_within_tolerance(self):
        self.assertTrue(self._match('0.00001', '0.00000', 'FLOAT_WITH_TOLERANCE'))

    def test_float_outside_tolerance(self):
        self.assertFalse(self._match('1.0', '2.0', 'FLOAT_WITH_TOLERANCE'))

    # ARRAY
    def test_array_space_separated(self):
        self.assertTrue(self._match('0 1', '0 1', 'ARRAY'))

    def test_array_bracket_vs_space(self):
        self.assertTrue(self._match('0 1', '[0, 1]', 'ARRAY'))

    def test_array_order_matters(self):
        # ARRAY is order-sensitive — [1, 0] != [0, 1]
        self.assertFalse(self._match('1 0', '0 1', 'ARRAY'))

    # ORDER_INSENSITIVE_ARRAY
    def test_order_insensitive_any_order(self):
        self.assertTrue(self._match('1 0', '0 1', 'ORDER_INSENSITIVE_ARRAY'))

    def test_order_insensitive_match(self):
        self.assertTrue(self._match('2 1 4 3 5', '1 2 3 4 5', 'ORDER_INSENSITIVE_ARRAY'))

    def test_order_insensitive_different_elements(self):
        self.assertFalse(self._match('0 1', '0 2', 'ORDER_INSENSITIVE_ARRAY'))

    # ALTERNATIVES (pipe-separated)
    def test_alternatives_first(self):
        self.assertTrue(self._match('bab', 'bab|aba', 'ALTERNATIVES'))

    def test_alternatives_second(self):
        self.assertTrue(self._match('aba', 'bab|aba', 'ALTERNATIVES'))

    def test_alternatives_none_match(self):
        self.assertFalse(self._match('xyz', 'bab|aba', 'ALTERNATIVES'))

    # Auto-detect pipe-separated regardless of strategy
    def test_auto_pipe_detection(self):
        from tracker.judge.verdict import _outputs_match
        self.assertTrue(_outputs_match('aba', 'bab|aba', strategy='NORMALIZED_TEXT'))

    # JSON
    def test_json_equality(self):
        self.assertTrue(self._match('[0,1]', '[0, 1]', 'JSON'))

    def test_json_mismatch(self):
        self.assertFalse(self._match('[0,1]', '[1,0]', 'JSON'))


# ===========================================================================
# 3. run_against_test_cases — output_checker threading
# ===========================================================================

class TestRunAgainstTestCasesChecker(DjangoTestCase):
    """run_against_test_cases passes output_checker through correctly."""

    def _make_executor(self, stdout):
        """Return an executor_fn that always produces the given stdout."""
        result = MagicMock()
        result.status = 'OK'
        result.stdout = stdout
        result.stderr = ''
        result.compile_error = ''
        result.execution_time_ms = 10
        result.memory_kb = 1024
        return lambda source, stdin: result

    def test_order_insensitive_accepts_any_order(self):
        from tracker.judge.verdict import run_against_test_cases
        executor = self._make_executor('1 0')
        # expected is "0 1" but program outputs "1 0" — ORDER_INSENSITIVE_ARRAY should accept
        test_cases = [('4\n2 7 11 15\n9', '0 1', False, 1)]
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=test_cases,
            source_code='',
            output_checker='ORDER_INSENSITIVE_ARRAY',
        )
        self.assertEqual(result.final_verdict, 'ACCEPTED')

    def test_array_rejects_wrong_order(self):
        from tracker.judge.verdict import run_against_test_cases
        executor = self._make_executor('1 0')
        # ARRAY is order-sensitive — "1 0" != "0 1"
        test_cases = [('4\n2 7 11 15\n9', '0 1', False, 1)]
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=test_cases,
            source_code='',
            output_checker='ARRAY',
        )
        self.assertEqual(result.final_verdict, 'WRONG_ANSWER')

    def test_boolean_accepts_case_insensitive(self):
        from tracker.judge.verdict import run_against_test_cases
        executor = self._make_executor('True')
        test_cases = [('some input', 'true', False, 1)]
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=test_cases,
            source_code='',
            output_checker='BOOLEAN',
        )
        self.assertEqual(result.final_verdict, 'ACCEPTED')

    def test_default_checker_normalized_text(self):
        from tracker.judge.verdict import run_against_test_cases
        executor = self._make_executor('hello\r\n')
        test_cases = [('input', 'hello', False, 1)]
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=test_cases,
            source_code='',
            # no output_checker → defaults to NORMALIZED_TEXT
        )
        self.assertEqual(result.final_verdict, 'ACCEPTED')

    def test_no_test_cases_returns_execution_error(self):
        from tracker.judge.verdict import run_against_test_cases
        executor = self._make_executor('anything')
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=[],
            source_code='',
        )
        self.assertEqual(result.final_verdict, 'EXECUTION_ERROR')

    def test_compile_error_propagates(self):
        from tracker.judge.verdict import run_against_test_cases
        err_result = MagicMock()
        err_result.status = 'COMPILE_ERROR'
        err_result.stdout = ''
        err_result.stderr = ''
        err_result.compile_error = 'syntax error on line 1'
        err_result.execution_time_ms = 0
        err_result.memory_kb = 0
        executor = lambda source, stdin: err_result

        test_cases = [('input', 'expected', False, 1)]
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=test_cases,
            source_code='',
        )
        self.assertEqual(result.final_verdict, 'COMPILE_ERROR')
        self.assertIn('syntax error', result.compile_error)


# ===========================================================================
# 4. End-to-end stdin format regression
# ===========================================================================

class TestCanonicalStdinRegression(DjangoTestCase):
    """
    Regression tests for specific problem input/output patterns.
    NOT hardcoded expected values per problem — tests the generic pipeline behavior
    with the same category of data each problem type represents.
    """

    def test_two_sum_style_input_no_brackets(self):
        """Array + scalar argument produces bracket-free STDIN."""
        from tracker.judge.canonical_serialization import parse_example_arguments, serialize_to_stdin
        # Pattern: nums = [2,7,11,15], target = 9  (Two Sum style)
        args = parse_example_arguments('nums = [2,7,11,15], target = 9')
        stdin = serialize_to_stdin(args)
        self.assertNotIn('[', stdin)
        self.assertNotIn(']', stdin)
        lines = stdin.splitlines()
        # First line: array length
        self.assertEqual(lines[0], '4')
        # Second line: space-separated elements
        self.assertIn('2', lines[1])
        self.assertIn('15', lines[1])
        # Third line: scalar target
        self.assertEqual(lines[2], '9')

    def test_palindrome_number_style_input(self):
        """Single integer argument produces single line STDIN."""
        from tracker.judge.canonical_serialization import parse_example_arguments, serialize_to_stdin
        # Pattern: x = 121  (Palindrome Number style)
        args = parse_example_arguments('x = 121')
        stdin = serialize_to_stdin(args)
        self.assertEqual(stdin.strip(), '121')

    def test_valid_parentheses_style_input(self):
        """Single string argument produces single line STDIN."""
        from tracker.judge.canonical_serialization import parse_example_arguments, serialize_to_stdin
        # Pattern: s = "()"  (Valid Parentheses style)
        args = parse_example_arguments('s = "()"')
        stdin = serialize_to_stdin(args)
        self.assertEqual(stdin.strip(), '()')

    def test_array_output_space_separated(self):
        """Array output [0, 1] becomes '0 1' in canonical STDOUT."""
        from tracker.judge.canonical_serialization import serialize_to_expected_stdout
        out = serialize_to_expected_stdout('[0, 1]')
        self.assertEqual(out, '0 1')

    def test_boolean_output_lowercase(self):
        """Boolean output True → 'true' in canonical STDOUT."""
        from tracker.judge.canonical_serialization import serialize_to_expected_stdout
        out = serialize_to_expected_stdout('true')
        self.assertEqual(out, 'true')

    def test_integer_output_clean(self):
        """Integer output '42' stays '42'."""
        from tracker.judge.canonical_serialization import serialize_to_expected_stdout
        out = serialize_to_expected_stdout('42')
        self.assertEqual(out, '42')


# ===========================================================================
# 5. normalize_judge_data command — basic behavior
# ===========================================================================

class TestNormalizeJudgeDataCommand(DjangoTestCase):
    """
    Tests for the normalize_judge_data management command.
    Uses in-memory test problems — no external HTTP requests.
    """
    fixtures = []  # no fixtures needed; we create objects in setUp

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user('testuser_norm', password='pass')

    def _create_test_problem(self, qnum, examples, return_type='int', desc=''):
        from tracker.models import Problem
        p = Problem.objects.create(
            question_number=qnum,
            title=f'Test Problem {qnum}',
            description=desc or f'Test problem {qnum}',
            examples=examples,
            return_type=return_type,
            is_judge_ready=False,
            judge_readiness_status='CONFIGURATION_REQUIRED',
            execution_mode='STDIN_STDOUT',
            function_name='solve',
        )
        return p

    def test_command_dry_run_does_not_write(self):
        """--dry-run flag must not write any DB changes."""
        from tracker.models import Problem, TestCase
        p = self._create_test_problem(
            qnum=9999,
            examples=[{'input': 'x = 121', 'output': 'true'}],
            return_type='bool',
        )
        original_tc_count = TestCase.objects.filter(problem=p).count()
        self.assertEqual(original_tc_count, 0)

        from django.core.management import call_command
        call_command('normalize_judge_data', question_number=9999, dry_run=True, verbosity=0)

        # Should still be 0 — dry run doesn't write
        self.assertEqual(TestCase.objects.filter(problem=p).count(), 0)

    def test_command_creates_test_cases(self):
        """normalize_judge_data creates TestCase records for a problem with examples."""
        from tracker.models import Problem, TestCase
        p = self._create_test_problem(
            qnum=9998,
            examples=[
                {'input': 'nums = [2,7,11,15], target = 9', 'output': '[0, 1]'},
                {'input': 'nums = [3,2,4], target = 6', 'output': '[1, 2]'},
            ],
            return_type='vector<int>',
            desc='Return indices. The answer in any order.',
        )
        from django.core.management import call_command
        call_command('normalize_judge_data', question_number=9998, verbosity=0)

        tcs = TestCase.objects.filter(problem=p)
        self.assertGreaterEqual(tcs.count(), 1)

        # All test case inputs must be bracket-free
        for tc in tcs:
            self.assertNotIn('[', tc.input_text,
                             f"Bracket found in test case input_text: {tc.input_text!r}")

    def test_command_sets_output_checker(self):
        """normalize_judge_data sets output_checker based on problem semantics."""
        from tracker.models import Problem
        p = self._create_test_problem(
            qnum=9997,
            examples=[{'input': 'x = 121', 'output': 'true'}],
            return_type='bool',
        )
        from django.core.management import call_command
        call_command('normalize_judge_data', question_number=9997, verbosity=0)

        p.refresh_from_db()
        self.assertEqual(p.output_checker, 'BOOLEAN')

    def test_command_no_examples_marks_config_required(self):
        """A problem with no examples stays CONFIGURATION_REQUIRED and no test cases created."""
        from tracker.models import Problem, TestCase
        p = self._create_test_problem(qnum=9996, examples=[])
        from django.core.management import call_command
        call_command('normalize_judge_data', question_number=9996, force=True, verbosity=0)

        p.refresh_from_db()
        self.assertFalse(p.is_judge_ready)
        self.assertEqual(TestCase.objects.filter(problem=p).count(), 0)

    def test_command_idempotent(self):
        """Running the command twice produces the same result (idempotent)."""
        from tracker.models import Problem, TestCase
        p = self._create_test_problem(
            qnum=9995,
            examples=[{'input': 'x = 121', 'output': 'true'}],
            return_type='bool',
        )
        from django.core.management import call_command
        call_command('normalize_judge_data', question_number=9995, verbosity=0)
        count_after_first = TestCase.objects.filter(problem=p).count()

        call_command('normalize_judge_data', question_number=9995, force=True, verbosity=0)
        count_after_second = TestCase.objects.filter(problem=p).count()

        self.assertEqual(count_after_first, count_after_second)

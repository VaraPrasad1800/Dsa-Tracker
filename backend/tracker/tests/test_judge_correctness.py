"""
test_judge_correctness.py — Regression tests for Online Judge correctness fixes.

Tests:
  1. clean_raw_output_text — strips polluted Explanation/Note/Clarification blocks
  2. Verdict comparator enhancements — quoted strings, array format tolerance, alternatives
  3. Starter code input format — token-based parsing for all languages
  4. End-to-end: known-correct Python solutions produce ACCEPTED verdicts
  5. Problem contract — SQL/Database problems blocked from judge
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase as DjangoTestCase


# ===========================================================================
# 1. clean_raw_output_text tests
# ===========================================================================

class TestCleanRawOutputText(DjangoTestCase):
    """clean_raw_output_text correctly strips polluted output text."""

    def _clean(self, s):
        from tracker.judge.canonical_serialization import clean_raw_output_text
        return clean_raw_output_text(s)

    def test_clean_value_unchanged(self):
        self.assertEqual(self._clean('0 1'), '0 1')

    def test_integer_unchanged(self):
        self.assertEqual(self._clean('42'), '42')

    def test_true_unchanged(self):
        self.assertEqual(self._clean('true'), 'true')

    def test_explanation_block_stripped(self):
        raw = 'true\nExplanation\n: Possible partition [1, 1],[2, 2]'
        self.assertEqual(self._clean(raw), 'true')

    def test_explanation_colon_stripped(self):
        raw = '4\nExplanation\n:\n4, 9, 121, and 484 are superpalindromes.'
        self.assertEqual(self._clean(raw), '4')

    def test_explanation_inline_stripped(self):
        raw = '3\nExplanation\n:\nThe longest subsequence is fibonacci-like.'
        self.assertEqual(self._clean(raw), '3')

    def test_note_stripped(self):
        raw = '4\nExplanation\n: something\nNote that 676 is not...'
        # Note is inside the Explanation block — full block stripped
        self.assertEqual(self._clean(raw), '4')

    def test_clarification_stripped(self):
        raw = '-1\n\nClarification:\n\nWhat should we return when needle is empty'
        self.assertEqual(self._clean(raw), '-1')

    def test_return_pattern_integer(self):
        raw = 'Return 6, and the first 6 characters of the input array should be...'
        self.assertEqual(self._clean(raw), '6')

    def test_empty_string(self):
        self.assertEqual(self._clean(''), '')

    def test_none_becomes_empty(self):
        self.assertEqual(self._clean(None), '')

    def test_array_not_affected(self):
        self.assertEqual(self._clean('[0, 1]'), '[0, 1]')

    def test_explanation_variation_space(self):
        raw = '1\n Explanation : \nSearching for value 7 is guaranteed.'
        self.assertEqual(self._clean(raw), '1')


class TestSerializeToExpectedStdoutCleaning(DjangoTestCase):
    """serialize_to_expected_stdout sanitizes polluted raw outputs before serializing."""

    def _serialize(self, raw, hint=''):
        from tracker.judge.canonical_serialization import serialize_to_expected_stdout
        return serialize_to_expected_stdout(raw, hint)

    def test_true_with_explanation(self):
        raw = 'true\nExplanation\n: Possible partition [1, 1],[2, 2],[3, 3],[4, 4]'
        self.assertEqual(self._serialize(raw), 'true')

    def test_integer_with_explanation(self):
        raw = '3\nExplanation\n:\nThe longest subsequence...'
        self.assertEqual(self._serialize(raw), '3')

    def test_clean_array(self):
        self.assertEqual(self._serialize('[0, 1]'), '0 1')

    def test_clean_boolean(self):
        self.assertEqual(self._serialize('false'), 'false')


# ===========================================================================
# 2. Verdict comparator enhancement tests
# ===========================================================================

class TestVerdictComparatorEnhancements(DjangoTestCase):
    """Enhancements to verdict comparator: quoted strings, array tokens, alternatives."""

    def _match(self, actual, expected, strategy='NORMALIZED_TEXT'):
        from tracker.judge.verdict import _outputs_match
        return _outputs_match(actual, expected, strategy=strategy)

    # --- Quoted string stripping ---
    def test_quoted_actual_matches_unquoted_expected(self):
        self.assertTrue(self._match('"bab"', 'bab'))

    def test_unquoted_actual_matches_quoted_expected(self):
        self.assertTrue(self._match('bab', '"bab"'))

    def test_single_quoted_match(self):
        self.assertTrue(self._match("'bab'", 'bab'))

    def test_different_strings_no_match(self):
        self.assertFalse(self._match('"aba"', 'bab'))

    # --- Array token tolerance ---
    def test_bracket_array_vs_space_separated(self):
        self.assertTrue(self._match('[0, 1]', '0 1'))

    def test_space_separated_vs_bracket_array(self):
        self.assertTrue(self._match('0 1', '[0, 1]'))

    def test_different_arrays_no_match(self):
        self.assertFalse(self._match('[0, 2]', '0 1'))

    # --- Alternatives with strategy preservation ---
    def test_alternatives_first_match(self):
        self.assertTrue(self._match('bab', 'bab|aba', 'ALTERNATIVES'))

    def test_alternatives_second_match(self):
        self.assertTrue(self._match('aba', 'bab|aba', 'ALTERNATIVES'))

    def test_alternatives_no_match(self):
        self.assertFalse(self._match('xyz', 'bab|aba', 'ALTERNATIVES'))

    def test_alternatives_auto_detect_pipe(self):
        # Pipe-separated alternatives auto-detected regardless of strategy
        self.assertTrue(self._match('aba', 'bab|aba', 'NORMALIZED_TEXT'))

    def test_alternatives_array_strategy_preserved(self):
        # Strategy passed to alternatives
        self.assertTrue(self._match('1 0', '0 1|1 0', 'ORDER_INSENSITIVE_ARRAY'))


# ===========================================================================
# 3. Starter code input format tests
# ===========================================================================

class TestStarterCodeInputFormat(DjangoTestCase):
    """Starter code templates correctly handle token-based STDIN format."""

    def _build(self, params, cls='Solution', fn='solve'):
        from tracker.services.problem_hydration_service import _build_python, _build_cpp
        meta = {'class_name': cls, 'function_name': fn, 'parameters_meta': params, 'return_type': 'vector<int>'}
        return _build_python(meta, {}), _build_cpp(meta, {})

    def test_python_array_uses_token_based_parsing(self):
        """Python starter should read array length N then N elements from tokens."""
        (py_starter, _), _ = self._build([
            {'name': 'nums', 'type': 'List[int]'},
            {'name': 'target', 'type': 'int'}
        ])
        # Token-based parsing
        self.assertIn('tokens = sys.stdin.read().split()', py_starter)
        self.assertIn('n_nums = int(tokens[it])', py_starter)
        self.assertIn('nums = [int(tokens[it + i]) for i in range(n_nums)]', py_starter)
        self.assertIn('target = int(tokens[it])', py_starter)

    def test_python_no_json_loads_in_multi_param_starter(self):
        """Multi-param Python starter should not assume JSON array on line 0."""
        (py_starter, _), _ = self._build([
            {'name': 'nums', 'type': 'List[int]'},
            {'name': 'target', 'type': 'int'}
        ])
        # Should NOT have json.loads which was the old buggy approach
        self.assertNotIn('json.loads(lines[0])', py_starter)
        self.assertNotIn('lines[0]', py_starter)

    def test_cpp_array_uses_n_prefix(self):
        """C++ starter should read int n then vector of n elements."""
        _, (cpp_starter, _) = self._build([
            {'name': 'nums', 'type': 'vector<int>'},
            {'name': 'target', 'type': 'int'}
        ])
        self.assertIn('n_nums', cpp_starter)
        self.assertIn('cin >> n_nums', cpp_starter)
        self.assertIn('vector<int> nums(n_nums)', cpp_starter)

    def test_generate_input_format_describes_n_prefix(self):
        """generate_input_format should describe N on its own line for arrays."""
        from tracker.services.problem_hydration_service import generate_input_format
        meta = {'parameters_meta': [
            {'name': 'nums', 'type': 'List[int]'},
            {'name': 'target', 'type': 'int'}
        ]}
        fmt = generate_input_format(meta, [])
        self.assertIn('N', fmt)  # Should mention N (array size)
        self.assertIn('nums', fmt)
        self.assertIn('target', fmt)


# ===========================================================================
# 4. End-to-end execution with known-correct solutions
# ===========================================================================

class TestJudgeEndToEndCorrectness(DjangoTestCase):
    """Known-correct solutions produce ACCEPTED on real test cases."""

    def _run(self, problem_qnum, source_code, language='python'):
        """Run source_code against the first 3 test cases of the problem."""
        from tracker.models import Problem
        from tracker.judge.executor import get_test_executor
        from tracker.judge.verdict import run_against_test_cases

        try:
            p = Problem.objects.get(question_number=problem_qnum)
        except Problem.DoesNotExist:
            self.skipTest(f"Problem {problem_qnum} not in test database")

        tcs = list(p.test_cases.order_by('is_hidden', 'order')[:3])
        if not tcs:
            self.skipTest(f"Problem {problem_qnum} has no test cases")

        executor = get_test_executor(language)
        tc_tuples = [(tc.input_text, tc.expected_output, tc.is_hidden, i) for i, tc in enumerate(tcs)]
        result = run_against_test_cases(
            executor_fn=executor,
            test_cases=tc_tuples,
            source_code=source_code,
            output_checker=p.output_checker or 'NORMALIZED_TEXT',
        )
        return result

    def test_two_sum_python_accepted(self):
        """Two Sum: correct Python solution → ACCEPTED (token-based STDIN)."""
        code = """import sys

def solve():
    tokens = sys.stdin.read().split()
    n = int(tokens[0])
    nums = [int(tokens[1 + i]) for i in range(n)]
    target = int(tokens[1 + n])
    d = {}
    for i, v in enumerate(nums):
        if target - v in d:
            print(d[target - v], i)
            return
        d[v] = i

if __name__ == '__main__':
    solve()
"""
        result = self._run(1, code)
        self.assertEqual(result.final_verdict, 'ACCEPTED',
            f"Expected ACCEPTED but got {result.final_verdict}: {result.error_message}")
        self.assertEqual(result.tests_passed, result.tests_total)

    def test_valid_parentheses_python_accepted(self):
        """Valid Parentheses: correct Python solution → ACCEPTED."""
        code = """import sys

def solve():
    tokens = sys.stdin.read().split()
    s = tokens[0]
    stack = []
    for c in s:
        if c in '({[':
            stack.append(c)
        elif not stack or {')':'(', '}':'{', ']':'['}[c] != stack[-1]:
            print('false')
            return
        else:
            stack.pop()
    print('true' if not stack else 'false')

if __name__ == '__main__':
    solve()
"""
        result = self._run(20, code)
        self.assertEqual(result.final_verdict, 'ACCEPTED',
            f"Expected ACCEPTED but got {result.final_verdict}: {result.error_message}")

    def test_climbing_stairs_python_accepted(self):
        """Climbing Stairs: correct Python solution → ACCEPTED."""
        code = """import sys

def solve():
    tokens = sys.stdin.read().split()
    n = int(tokens[0])
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    print(b)

if __name__ == '__main__':
    solve()
"""
        result = self._run(70, code)
        self.assertEqual(result.final_verdict, 'ACCEPTED',
            f"Expected ACCEPTED but got {result.final_verdict}: {result.error_message}")

    def test_maximum_subarray_python_accepted(self):
        """Maximum Subarray: correct Python solution → ACCEPTED."""
        code = """import sys

def solve():
    tokens = sys.stdin.read().split()
    n = int(tokens[0])
    nums = [int(tokens[1 + i]) for i in range(n)]
    best = cur = nums[0]
    for v in nums[1:]:
        cur = max(v, cur + v)
        best = max(best, cur)
    print(best)

if __name__ == '__main__':
    solve()
"""
        result = self._run(53, code)
        self.assertEqual(result.final_verdict, 'ACCEPTED',
            f"Expected ACCEPTED but got {result.final_verdict}: {result.error_message}")

    def test_palindrome_number_python_accepted(self):
        """Palindrome Number: correct Python solution → ACCEPTED."""
        code = """import sys

def solve():
    tokens = sys.stdin.read().split()
    x = int(tokens[0])
    print('true' if str(x) == str(x)[::-1] else 'false')

if __name__ == '__main__':
    solve()
"""
        result = self._run(9, code)
        self.assertEqual(result.final_verdict, 'ACCEPTED',
            f"Expected ACCEPTED but got {result.final_verdict}: {result.error_message}")

    def test_wrong_solution_not_accepted(self):
        """A provably wrong solution must NOT be ACCEPTED."""
        code = """import sys
sys.stdin.read()
print(-1)  # Always wrong
"""
        result = self._run(53, code)  # Maximum Subarray answer is never -1 in these test cases
        self.assertNotEqual(result.final_verdict, 'ACCEPTED',
            "A provably wrong solution should not be accepted")


# ===========================================================================
# 5. Problem contract — SQL/Database problems
# ===========================================================================

class TestProblemContractSQLExclusion(DjangoTestCase):
    """SQL/Database problems are not marked judge-ready."""

    def _make_problem(self, qnum, tags=None, description='', test_output=''):
        from tracker.models import Problem, TestCase, Tag
        p = Problem.objects.create(
            question_number=qnum,
            title=f'Test Problem {qnum}',
            difficulty='Easy',
            execution_mode='STDIN_STDOUT',
            input_format='Line 1: n',
            output_format='Print result.',
        )
        if tags:
            for tag_name in tags:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                p.tags.add(tag)
        if test_output:
            TestCase.objects.create(
                problem=p,
                input_text='1',
                expected_output=test_output,
                is_hidden=False,
                order=1,
            )
        return p

    def test_database_tagged_problem_is_not_judge_ready(self):
        from tracker.services.problem_contract_service import evaluate_problem_contract
        p = self._make_problem(99991, tags=['Database'])
        result = evaluate_problem_contract(p)
        self.assertFalse(result['is_judge_ready'])
        self.assertEqual(result['judge_readiness_status'], 'NON_ALGORITHMIC_SQL')

    def test_sql_table_output_problem_is_not_judge_ready(self):
        from tracker.services.problem_contract_service import evaluate_problem_contract
        p = self._make_problem(99992, test_output='+----+------------------+\n| id | email |\n+----+------------------+')
        result = evaluate_problem_contract(p)
        self.assertFalse(result['is_judge_ready'])
        self.assertEqual(result['judge_readiness_status'], 'NON_ALGORITHMIC_SQL')

    def test_normal_algorithmic_problem_not_blocked(self):
        from tracker.services.problem_contract_service import evaluate_problem_contract
        from tracker.models import TestCase, LanguageTemplate
        p = self._make_problem(99993, test_output='42')
        TestCase.objects.create(problem=p, input_text='5', expected_output='42', is_hidden=True, order=2)
        LanguageTemplate.objects.create(problem=p, language='python', starter_code='print(42)', harness_code='')
        LanguageTemplate.objects.create(problem=p, language='cpp', starter_code='int main(){return 0;}', harness_code='')
        result = evaluate_problem_contract(p)
        # Should not be blocked as SQL
        self.assertNotEqual(result['judge_readiness_status'], 'NON_ALGORITHMIC_SQL')

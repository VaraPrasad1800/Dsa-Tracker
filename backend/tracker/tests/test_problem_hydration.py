"""
Tests for Problem Contract Hydration and Premium Flags Audit.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from tracker.models import Problem, TestCase as DBTestCase, LanguageTemplate, Solution
from tracker.services.problem_hydration_service import (
    hydrate_problem_contract,
    extract_input_arguments,
    clean_output_value,
)
from tracker.services.judge_service import run_code_for_user, submit_code

User = get_user_model()


class ProblemHydrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='hydra_tester', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_extract_input_arguments_multi_parameter(self):
        # Two parameters
        inp = "nums = [2,7,11,15], target = 9"
        parsed = extract_input_arguments(inp)
        self.assertEqual(parsed, "[2,7,11,15]\n9")

        # Single string parameter
        inp_str = 's = "()"'
        self.assertEqual(extract_input_arguments(inp_str), '"()"')

        # Raw string without assignment
        self.assertEqual(extract_input_arguments('"abc"'), '"abc"')

    def test_clean_output_value(self):
        self.assertEqual(clean_output_value("true\nExplanation: valid"), "true")
        self.assertEqual(clean_output_value("  [0, 1]  "), "[0, 1]")

    def test_hydrate_valid_parentheses_contract(self):
        p = Problem.objects.create(
            question_number=20,
            title='Valid Parentheses',
            slug='valid-parentheses',
            difficulty='Easy',
            leetcode_id=20,
            is_premium=False,
        )

        p, ok, msg = hydrate_problem_contract(p, force=True)
        self.assertTrue(ok)
        self.assertTrue(p.is_judge_ready)
        self.assertEqual(p.judge_readiness_status, 'JUDGE_READY')
        self.assertEqual(p.function_name, 'isValid')
        self.assertEqual(p.class_name, 'Solution')

        # Verify test cases
        visible_cases = DBTestCase.objects.filter(problem=p, is_hidden=False)
        hidden_cases = DBTestCase.objects.filter(problem=p, is_hidden=True)
        self.assertGreaterEqual(visible_cases.count(), 1)
        self.assertGreaterEqual(hidden_cases.count(), 1)

        # Verify templates
        self.assertTrue(LanguageTemplate.objects.filter(problem=p, language='python').exists())
        self.assertTrue(LanguageTemplate.objects.filter(problem=p, language='cpp').exists())

        # Test execution with LeetCode class Solution
        valid_py = (
            "class Solution:\n"
            "    def isValid(self, s: str) -> bool:\n"
            "        stk = []\n"
            "        d = {'()', '[]', '{}'}\n"
            "        for c in s:\n"
            "            if c in '({[': stk.append(c)\n"
            "            elif not stk or stk.pop() + c not in d: return False\n"
            "        return not stk\n"
        )
        res = submit_code(self.user, str(p.id), 'python', valid_py)
        self.assertEqual(res.get('verdict'), 'ACCEPTED')

        # Test execution with Universal Complete Program (Standard I/O)
        complete_py = (
            "import sys\n"
            "def solve():\n"
            "    lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]\n"
            "    if not lines: return\n"
            "    s = lines[0]\n"
            "    if s.startswith('\"') and s.endswith('\"'): s = s[1:-1]\n"
            "    stk = []\n"
            "    d = {'()', '[]', '{}'}\n"
            "    for c in s:\n"
            "        if c in '({[': stk.append(c)\n"
            "        elif not stk or stk.pop() + c not in d: print('false'); return\n"
            "    print('true' if not stk else 'false')\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        )
        res2 = submit_code(self.user, str(p.id), 'python', complete_py)
        self.assertEqual(res2.get('verdict'), 'ACCEPTED')

    def test_on_demand_hydration_via_api(self):
        p = Problem.objects.create(
            question_number=20,
            title='Valid Parentheses',
            slug='valid-parentheses',
            difficulty='Easy',
            leetcode_id=20,
            is_judge_ready=False,
        )

        # Calling problem detail triggers on-demand hydration
        res = self.client.get(f'/api/problems/{p.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        p.refresh_from_db()
        self.assertTrue(p.is_judge_ready)
        self.assertEqual(p.function_name, 'isValid')

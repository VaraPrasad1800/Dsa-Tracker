from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tracker.models import Problem, TestCase as ProblemTestCase, Submission, Solution, LanguageTemplate
from tracker.services.judge_service import run_code_for_user, submit_code
from tracker.serializers import ProblemSerializer

User = get_user_model()

class JudgeSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='judge_user', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.problem = Problem.objects.create(
            question_number=101,
            title='Add Two Numbers',
            slug='add-two-numbers',
            difficulty='Easy',
            execution_mode='STDIN_STDOUT',
            description="Given two integers nums[\n0\n] and nums[\n1\n], return\nthe\nsum.",
        )

        # Visible test case
        self.tc1 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_text='2 3',
            expected_output='5',
            is_hidden=False,
            order=1
        )
        # Hidden test case
        self.tc2 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_text='10 20',
            expected_output='30',
            is_hidden=True,
            order=2
        )

    def test_run_code_does_not_save_submission(self):
        code = "import sys\na, b = map(int, sys.stdin.read().split())\nprint(a + b)"
        result = run_code_for_user(self.user, str(self.problem.id), 'python', code, stdin='4 5')
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['stdout'].strip(), '9')
        self.assertEqual(Submission.objects.count(), 0)

    def test_submit_code_accepted(self):
        code = "import sys\na, b = map(int, sys.stdin.read().split())\nprint(a + b)"
        result = submit_code(self.user, str(self.problem.id), 'python', code)
        self.assertEqual(result['verdict'], 'ACCEPTED')
        self.assertEqual(result['tests_passed'], 2)
        self.assertEqual(result['tests_total'], 2)
        self.assertGreater(result['points_awarded'], 0)
        self.assertEqual(Submission.objects.filter(user=self.user, verdict='ACCEPTED').count(), 1)

    def test_submit_code_wrong_answer(self):
        code = "print(0)"
        result = submit_code(self.user, str(self.problem.id), 'python', code)
        self.assertEqual(result['verdict'], 'WRONG_ANSWER')
        self.assertEqual(result['tests_passed'], 0)
        self.assertEqual(result['points_awarded'], 0)

    def test_submit_code_compile_error(self):
        code = "def syntax_error("
        result = submit_code(self.user, str(self.problem.id), 'python', code)
        self.assertEqual(result['verdict'], 'COMPILE_ERROR')
        self.assertTrue(bool(result.get('compile_error')))

    def test_hidden_test_cases_never_leaked_via_api(self):
        response = self.client.get(f'/api/problems/{self.problem.id}/test-cases/')
        self.assertEqual(response.status_code, 200)
        cases = response.data.get('test_cases', [])
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]['input_text'], '2 3')
        # Ensure hidden test case input and output are nowhere in data
        for c in cases:
            self.assertNotEqual(c['input_text'], '10 20')
            self.assertNotEqual(c['expected_output'], '30')

    def test_hidden_test_cases_never_leaked_via_submission_result(self):
        code = "print(0)"
        result = submit_code(self.user, str(self.problem.id), 'python', code)
        # Verify hidden test input/output are not leaked in verdict dict
        sanitized_result = {k: v for k, v in result.items() if k != 'submission_id'}
        result_str = str(sanitized_result)
        self.assertNotIn('10 20', result_str)
        self.assertNotIn('30', result_str)

    def test_no_test_cases_configured_returns_clean_verdict(self):
        empty_problem = Problem.objects.create(
            question_number=999,
            title='No Test Problem',
            slug='no-test-problem',
            difficulty='Medium',
        )
        code = "print('hello')"
        result = submit_code(self.user, str(empty_problem.id), 'python', code)
        self.assertEqual(result['verdict'], 'EXECUTION_ERROR')
        self.assertIn('No test cases configured', result['compile_error'])

    def test_function_mode_execution_with_harness(self):
        func_problem = Problem.objects.create(
            question_number=202,
            title='Two Sum Method',
            slug='two-sum-method',
            difficulty='Easy',
            execution_mode='FUNCTION',
            function_name='twoSum',
        )
        # Create LanguageTemplate with harness
        harness = (
            "\nimport sys, json\n"
            "if __name__ == '__main__':\n"
            "    lines = sys.stdin.read().strip().split('\\n')\n"
            "    if lines and lines[0].strip():\n"
            "        nums = json.loads(lines[0])\n"
            "        target = int(lines[1])\n"
            "        print(json.dumps(Solution().twoSum(nums, target)))\n"
        )
        LanguageTemplate.objects.create(
            problem=func_problem,
            language='python',
            starter_code="class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        pass\n",
            harness_code=harness,
        )
        ProblemTestCase.objects.create(
            problem=func_problem,
            input_text="[2, 7, 11, 15]\n9",
            expected_output="[0, 1]",
            is_hidden=False,
            order=1,
        )

        user_code = (
            "class Solution:\n"
            "    def twoSum(self, nums: list[int], target: int) -> list[int]:\n"
            "        seen = {}\n"
            "        for i, n in enumerate(nums):\n"
            "            diff = target - n\n"
            "            if diff in seen:\n"
            "                return [seen[diff], i]\n"
            "            seen[n] = i\n"
            "        return []\n"
        )
        result = submit_code(self.user, str(func_problem.id), 'python', user_code)
        self.assertEqual(result['verdict'], 'ACCEPTED')
        self.assertEqual(result['tests_passed'], 1)
        self.assertEqual(result['tests_total'], 1)

    def test_problem_serializer_structured_fields(self):
        serializer = ProblemSerializer(self.problem)
        data = serializer.data
        self.assertEqual(data['question_number'], 101)
        self.assertEqual(data['execution_mode'], 'STDIN_STDOUT')
        self.assertIn('clean_description', data)
        # Broken newlines "nums[\n0\n]" should be repaired to "nums[0]"
        self.assertNotIn('[\n0\n]', data['clean_description'])

    def test_problem_solution_view_multi_language(self):
        Solution.objects.create(
            problem=self.problem,
            question_number=101,
            title='Add Two Numbers',
            code="def add(a, b): return a + b",
            language='python',
            code_by_language={
                'python': 'def add(a, b): return a + b',
                'cpp': 'int add(int a, int b) { return a + b; }',
                'java': 'public int add(int a, int b) { return a + b; }',
                'c': 'int add(int a, int b) { return a + b; }',
            },
            explanation='Direct arithmetic summation.',
            time_complexity='O(1)',
            space_complexity='O(1)',
        )
        response = self.client.get(f'/api/problems/{self.problem.id}/solution/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('available'))
        cbl = response.data.get('code_by_language', {})
        self.assertIn('python', cbl)
        self.assertIn('cpp', cbl)
        self.assertIn('java', cbl)
        self.assertIn('c', cbl)
        self.assertEqual(response.data.get('time_complexity'), 'O(1)')

    def test_batch_execution_sandbox_compiles_once_and_cleans_up(self):
        import os
        from tracker.judge.executor import get_test_executor
        from tracker.judge.sandbox import BatchExecutionSandbox

        exec_obj = get_test_executor('cpp', 2.0, 128)
        self.assertIsInstance(exec_obj, BatchExecutionSandbox)

        cpp_code = (
            "#include <iostream>\n"
            "using namespace std;\n"
            "int main() {\n"
            "    int a, b;\n"
            "    if (cin >> a >> b) cout << (a + b) << endl;\n"
            "    return 0;\n"
            "}\n"
        )
        res1 = exec_obj(cpp_code, '2 3')
        self.assertEqual(res1.status, 'OK')
        self.assertEqual(res1.stdout.strip(), '5')
        self.assertTrue(exec_obj.is_compiled)
        workdir = exec_obj.workdir
        self.assertTrue(os.path.exists(workdir))

        # Second test execution must reuse compiled binary without recompiling
        res2 = exec_obj(cpp_code, '10 20')
        self.assertEqual(res2.status, 'OK')
        self.assertEqual(res2.stdout.strip(), '30')

        # Cleanup must safely delete workdir
        exec_obj.cleanup()
        self.assertFalse(os.path.exists(workdir))


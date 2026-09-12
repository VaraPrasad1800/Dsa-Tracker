from django.test import TestCase
from django.core.management import call_command
from tracker.models import Problem, TestCase as ProblemTestCase, LanguageTemplate
from tracker.services.problem_contract_service import evaluate_problem_contract
from tracker.serializers import ProblemSerializer, ProblemListSerializer


class ProblemContractTests(TestCase):
    def setUp(self):
        self.problem = Problem.objects.create(
            question_number=501,
            title='Test Contract Problem',
            slug='test-contract-problem',
            difficulty='Medium',
            execution_mode='FUNCTION',
            function_name='contractSolve',
        )

    def test_unconfigured_problem_fails_contract(self):
        res = evaluate_problem_contract(self.problem, save=True)
        self.assertFalse(res['is_judge_ready'])
        self.assertEqual(res['judge_readiness_status'], 'CONFIGURATION_REQUIRED')
        self.assertIn("Missing visible test cases", res['missing_configuration'])
        self.assertIn("Missing hidden test cases", res['missing_configuration'])
        self.problem.refresh_from_db()
        self.assertFalse(self.problem.is_judge_ready)
        self.assertEqual(self.problem.judge_readiness_status, 'CONFIGURATION_REQUIRED')

    def test_fully_configured_problem_passes_contract(self):
        ProblemTestCase.objects.create(
            problem=self.problem,
            input_text='1 2',
            expected_output='3',
            is_hidden=False,
            order=1,
        )
        ProblemTestCase.objects.create(
            problem=self.problem,
            input_text='5 5',
            expected_output='10',
            is_hidden=True,
            order=2,
        )
        LanguageTemplate.objects.create(
            problem=self.problem,
            language='python',
            starter_code='class Solution:\n    def contractSolve(self):\n        pass',
            harness_code='import sys\nif __name__ == "__main__":\n    print(Solution().contractSolve())',
        )
        LanguageTemplate.objects.create(
            problem=self.problem,
            language='cpp',
            starter_code='class Solution {\npublic:\n    int contractSolve() {}\n};',
            harness_code='int main() { return 0; }',
        )

        res = evaluate_problem_contract(self.problem, save=True)
        self.assertTrue(res['is_judge_ready'])
        self.assertEqual(res['judge_readiness_status'], 'JUDGE_READY')
        self.assertEqual(len(res['missing_configuration']), 0)
        self.problem.refresh_from_db()
        self.assertTrue(self.problem.is_judge_ready)
        self.assertEqual(self.problem.judge_readiness_status, 'JUDGE_READY')

    def test_problem_serializer_exposes_contract_fields(self):
        serializer = ProblemSerializer(self.problem)
        data = serializer.data
        self.assertIn('is_judge_ready', data)
        self.assertIn('judge_readiness_status', data)
        self.assertIn('class_name', data)
        self.assertIn('parameters_meta', data)
        self.assertIn('return_type', data)
        self.assertIn('output_checker', data)
        self.assertIn('missing_configuration', data)

    def test_problem_list_serializer_exposes_contract_fields(self):
        serializer = ProblemListSerializer(self.problem)
        data = serializer.data
        self.assertIn('is_judge_ready', data)
        self.assertIn('judge_readiness_status', data)

    def test_management_commands_execute_cleanly(self):
        # Test audit command
        call_command('audit_problem_dataset')
        # Test sync command
        call_command('sync_problem_contracts', batch_size=100)

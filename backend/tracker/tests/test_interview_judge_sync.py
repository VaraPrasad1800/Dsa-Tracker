from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from tracker.models import Problem, Submission, UserProblemProgress, TestCase as ProblemTestCase, InterviewSession, InterviewProblem
from tracker.services.judge_service import submit_code, execute_submission, get_language_template, _prepare_executable_code

User = get_user_model()


class InterviewJudgeSyncTests(TestCase):
    """
    Regression tests verifying that Online Judge solves correctly synchronize
    with active Interview Sessions, while non-accepted verdicts never mark solved.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='candidate', password='Password123!')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.problem1 = Problem.objects.create(
            title='Two Sum Simulation',
            difficulty='Easy',
            question_number=901,
            is_judge_ready=True,
        )
        ProblemTestCase.objects.create(
            problem=self.problem1,
            order=1,
            input_text='2 3\n',
            expected_output='5\n',
            is_hidden=False,
        )
        ProblemTestCase.objects.create(
            problem=self.problem1,
            order=2,
            input_text='10 20\n',
            expected_output='30\n',
            is_hidden=True,
        )

        self.problem2 = Problem.objects.create(
            title='Multiply Numbers',
            difficulty='Medium',
            question_number=902,
            is_judge_ready=True,
        )
        ProblemTestCase.objects.create(
            problem=self.problem2,
            order=1,
            input_text='3 4\n',
            expected_output='12\n',
            is_hidden=False,
        )

        # Create active interview session with both problems
        self.session = InterviewSession.objects.create(
            user=self.user,
            duration_minutes=45,
            num_problems=2,
            difficulty='Mixed',
            status='ACTIVE',
        )
        self.ip1 = InterviewProblem.objects.create(session=self.session, problem=self.problem1)
        self.ip2 = InterviewProblem.objects.create(session=self.session, problem=self.problem2)

    def test_standalone_execution_model_contract(self):
        """Universal standalone model must return pristine source code without appending harnesses."""
        code = "print('hello')"
        prepared = _prepare_executable_code(self.problem1, 'python', code)
        self.assertEqual(prepared, code)

        tmpl = get_language_template(str(self.problem1.id), 'python')
        self.assertIn('def solve', tmpl)

    def test_wrong_answer_does_not_mark_interview_problem_solved(self):
        """Non-accepted submission (WA) must NOT mark solved, but must increment attempts."""
        wa_code = "print('999')\n"
        res = submit_code(self.user, str(self.problem1.id), 'python', wa_code)
        self.assertEqual(res['verdict'], 'WRONG_ANSWER')

        self.ip1.refresh_from_db()
        self.session.refresh_from_db()
        self.assertFalse(self.ip1.solved)
        self.assertEqual(self.ip1.attempts, 1)
        self.assertEqual(self.session.problems_solved, 0)

        # UserProblemProgress must not be marked SOLVED
        progress = UserProblemProgress.objects.filter(user=self.user, problem=self.problem1).first()
        if progress:
            self.assertNotEqual(progress.status, 'SOLVED')

    def test_compile_error_does_not_mark_interview_problem_solved(self):
        """Compilation error must NOT mark solved, but increments attempts."""
        ce_code = "def invalid syntax(: print(1)"
        res = submit_code(self.user, str(self.problem1.id), 'python', ce_code)
        self.assertEqual(res['verdict'], 'COMPILE_ERROR')

        self.ip1.refresh_from_db()
        self.session.refresh_from_db()
        self.assertFalse(self.ip1.solved)
        self.assertEqual(self.ip1.attempts, 1)
        self.assertEqual(self.session.problems_solved, 0)

    def test_accepted_submission_marks_interview_problem_solved(self):
        """Accepted submission must mark InterviewProblem solved, record submission, and increment problems_solved."""
        ac_code = """import sys
lines = sys.stdin.read().split()
if lines:
    a, b = int(lines[0]), int(lines[1])
    print(a + b)
"""
        res = submit_code(self.user, str(self.problem1.id), 'python', ac_code)
        self.assertEqual(res['verdict'], 'ACCEPTED')
        self.assertEqual(res['tests_passed'], 2)

        self.ip1.refresh_from_db()
        self.session.refresh_from_db()
        self.assertTrue(self.ip1.solved)
        self.assertEqual(self.ip1.attempts, 1)
        self.assertIsNotNone(self.ip1.submission)
        self.assertEqual(str(self.ip1.submission.id), res['submission_id'])
        self.assertEqual(self.session.problems_solved, 1)

        # Canonical UserProblemProgress must be SOLVED
        progress = UserProblemProgress.objects.get(user=self.user, problem=self.problem1)
        self.assertEqual(progress.status, 'SOLVED')
        self.assertEqual(progress.times_solved, 1)

    def test_interview_session_end_with_solved_problems(self):
        """Ending interview session must compute score based on canonical solved problems."""
        ac_code1 = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) + int(lines[1]))
"""
        submit_code(self.user, str(self.problem1.id), 'python', ac_code1)

        # End session via API endpoint
        url = f'/api/interview-sessions/{self.session.id}/end/'
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'COMPLETED')
        self.assertEqual(res.data['problems_solved'], 1)
        self.assertGreater(res.data['score'], 0)

    def test_interview_problem_solve_endpoint_syncs_submission_and_count(self):
        """Solve endpoint marks problem solved, links submission if present, and updates problems_solved."""
        ac_code = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) + int(lines[1]))
"""
        sub_res = submit_code(self.user, str(self.problem1.id), 'python', ac_code)

        url = f'/api/interview-sessions/{self.session.id}/problems/{self.problem1.id}/solve/'
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['solved'])
        self.assertEqual(res.data['problems_solved'], 1)

        self.ip1.refresh_from_db()
        self.assertTrue(self.ip1.solved)
        self.assertEqual(str(self.ip1.submission_id), sub_res['submission_id'])

    def test_interview_problem_serializer_reflects_solved_status(self):
        """InterviewProblemSerializer must serialize solved=True when problem was solved."""
        ac_code = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) + int(lines[1]))
"""
        submit_code(self.user, str(self.problem1.id), 'python', ac_code)

        url = f'/api/interview-sessions/{self.session.id}/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        probs = res.data['interview_problems']
        p1_data = next(p for p in probs if str(p['problem']) == str(self.problem1.id))
        p2_data = next(p for p in probs if str(p['problem']) == str(self.problem2.id))

        self.assertTrue(p1_data['solved'])
        self.assertFalse(p2_data['solved'])

    def test_prior_solve_outside_interview_does_not_mark_new_interview_solved(self):
        """Solving a problem prior to starting an interview session must NOT mark it solved in the interview."""
        ac_code2 = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) * int(lines[1]))
"""
        # User solves problem 2 outside any interview
        prior_res = submit_code(self.user, str(self.problem2.id), 'python', ac_code2)
        self.assertEqual(prior_res['verdict'], 'ACCEPTED')

        # Now start a brand new interview containing problem 2
        new_session = InterviewSession.objects.create(
            user=self.user,
            duration_minutes=30,
            num_problems=1,
            difficulty='Medium',
            status='ACTIVE',
        )
        new_ip = InterviewProblem.objects.create(session=new_session, problem=self.problem2)

        # In DB, it must be unsolved
        self.assertFalse(new_ip.solved)
        self.assertIsNone(new_ip.submission)

        # Serializer must NOT self-heal from the prior solve
        url = f'/api/interview-sessions/{new_session.id}/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ip_data = res.data['interview_problems'][0]
        self.assertFalse(ip_data['solved'])

        # Ending the session must have 0 problems solved
        end_url = f'/api/interview-sessions/{new_session.id}/end/'
        end_res = self.client.post(end_url)
        self.assertEqual(end_res.data['problems_solved'], 0)
        self.assertEqual(end_res.data['score'], 0)

    def test_user_isolation_in_interview_judge_sync(self):
        """Another user's submission must NEVER mark this user's interview problem solved."""
        other_user = User.objects.create_user(username='other_candidate', password='Password123!')
        ac_code1 = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) + int(lines[1]))
"""
        # Other user submits accepted solution
        res = submit_code(other_user, str(self.problem1.id), 'python', ac_code1)
        self.assertEqual(res['verdict'], 'ACCEPTED')

        self.ip1.refresh_from_db()
        self.session.refresh_from_db()
        self.assertFalse(self.ip1.solved)
        self.assertEqual(self.ip1.attempts, 0)
        self.assertEqual(self.session.problems_solved, 0)

    def test_attempt_count_idempotency_between_judge_and_solve_view(self):
        """Attempts must NOT be double-counted when judge runs and solve view is subsequently called."""
        ac_code1 = """import sys
lines = sys.stdin.read().split()
if lines:
    print(int(lines[0]) + int(lines[1]))
"""
        # 1. First attempt fails (WA)
        submit_code(self.user, str(self.problem1.id), 'python', "print(0)\n")
        self.ip1.refresh_from_db()
        self.assertEqual(self.ip1.attempts, 1)
        self.assertFalse(self.ip1.solved)

        # 2. Second attempt succeeds (ACCEPTED) via judge
        submit_code(self.user, str(self.problem1.id), 'python', ac_code1)
        self.ip1.refresh_from_db()
        self.assertEqual(self.ip1.attempts, 2)
        self.assertTrue(self.ip1.solved)

        # 3. Solve endpoint called on the same problem
        url = f'/api/interview-sessions/{self.session.id}/problems/{self.problem1.id}/solve/'
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.ip1.refresh_from_db()
        # Attempts must STILL be 2, NOT 3!
        self.assertEqual(self.ip1.attempts, 2)
        self.assertTrue(self.ip1.solved)

    def test_runtime_error_increments_attempts_without_marking_solved(self):
        """Runtime error must increment attempts and keep solved=False."""
        re_code = "print(1 / 0)\n"
        res = submit_code(self.user, str(self.problem1.id), 'python', re_code)
        self.assertEqual(res['verdict'], 'RUNTIME_ERROR')

        self.ip1.refresh_from_db()
        self.session.refresh_from_db()
        self.assertFalse(self.ip1.solved)
        self.assertEqual(self.ip1.attempts, 1)
        self.assertEqual(self.session.problems_solved, 0)


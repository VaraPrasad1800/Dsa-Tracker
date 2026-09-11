from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from tracker.models import Problem, UserProblemProgress
from tracker.services.leitner import update_problem_progress, get_leitner_box_stats

User = get_user_model()

class LeitnerSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='leitner_user', password='password')
        self.problem = Problem.objects.create(
            title='Invert Binary Tree', slug='invert-binary-tree', difficulty='Easy'
        )

    def test_box_progression_on_solved(self):
        # Solve 1: Box 1 -> Box 2 (+3 days)
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        self.assertEqual(p.current_box, 2)
        self.assertEqual(p.times_solved, 1)
        self.assertGreater(p.next_review_date, timezone.now() + timedelta(days=2))

        # Solve 2: Box 2 -> Box 3 (+7 days)
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        self.assertEqual(p.current_box, 3)

        # Solve 3: Box 3 -> Box 4 (+14 days)
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        self.assertEqual(p.current_box, 4)

        # Solve 4: Box 4 -> Box 5 (+30 days)
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        self.assertEqual(p.current_box, 5)

        # Solve 5: Box 5 stays at Box 5 (doesn't overflow)
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        self.assertEqual(p.current_box, 5)

    def test_box_reset_on_needs_revisit(self):
        # Advance to box 3
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        self.assertEqual(p.current_box, 3)

        # Mark Needs Revisit -> resets to Box 1, due tomorrow (+1 day)
        p = update_problem_progress(self.user, self.problem, status='NEEDS_REVISIT')
        self.assertEqual(p.current_box, 1)
        self.assertEqual(p.status, 'NEEDS_REVISIT')
        self.assertLessEqual(p.next_review_date, timezone.now() + timedelta(days=1, minutes=5))

    def test_due_today_count(self):
        p = update_problem_progress(self.user, self.problem, status='SOLVED')
        # Manually set review date in past
        p.next_review_date = timezone.now() - timedelta(hours=1)
        p.save()

        stats = get_leitner_box_stats(self.user)
        self.assertEqual(stats['due_today_count'], 1)
        self.assertEqual(stats['box_2_count'], 1)

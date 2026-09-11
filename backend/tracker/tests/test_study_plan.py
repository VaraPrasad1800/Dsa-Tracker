from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from tracker.models import Problem, Tag, UserProblemProgress
from tracker.services.study_plan import generate_study_plan, get_study_plan_progress
from tracker.services.leitner import update_problem_progress

User = get_user_model()

class StudyPlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='plan_user', password='password')
        self.tag = Tag.objects.create(name='DP', slug='dp')

        for i in range(15):
            p = Problem.objects.create(
                title=f'Problem {i}',
                slug=f'problem-{i}',
                difficulty='Medium' if i % 2 == 0 else 'Hard'
            )
            p.tags.add(self.tag)

    def test_study_plan_generation(self):
        target_date = timezone.now().date() + timedelta(days=5)
        plan = generate_study_plan(self.user, target_date, problems_per_day=3)
        self.assertEqual(plan.days.count(), 5)

        for day in plan.days.all():
            self.assertGreater(day.problems.count(), 0)

        progress = get_study_plan_progress(plan, self.user)
        self.assertIn('completed_today', progress)
        self.assertTrue(progress['on_pace'])

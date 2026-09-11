import os
from datetime import timedelta
import random
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from tracker.models import Problem, UserProblemProgress, ReviewHistory, DailyStat, UserStreak
from tracker.services.study_plan import generate_study_plan
from tracker.services.analytics import invalidate_user_analytics_cache

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed database with sample problems, demo users, realistic spaced repetition data, and analytics'

    def handle(self, *args, **options):
        # 1. Import problems
        csv_file = os.path.join(settings.BASE_DIR, 'data', 'sample_problems.csv')
        call_command('import_dsa_problems', csv=csv_file)

        # 2. Create demo users
        demo_user, _ = User.objects.get_or_create(username='demo_user', defaults={'email': 'demo@example.com'})
        demo_user.set_password('password123')
        demo_user.save()

        test_user, _ = User.objects.get_or_create(username='test_user', defaults={'email': 'test@example.com'})
        test_user.set_password('password123')
        test_user.save()

        # 3. Seed demo_user progress
        problems = list(Problem.objects.all().order_by('id'))
        now = timezone.now()

        # Solved in various boxes
        for i, problem in enumerate(problems[:35]):
            box = (i % 5) + 1
            # Make some due today (box 1 and 2 review dates in past)
            if i % 3 == 0:
                review_date = now - timedelta(hours=random.randint(1, 12))
            else:
                review_date = now + timedelta(days=box * 2)

            progress, _ = UserProblemProgress.objects.update_or_create(
                user=demo_user,
                problem=problem,
                defaults={
                    'status': 'SOLVED',
                    'current_box': box,
                    'next_review_date': review_date,
                    'times_solved': random.randint(1, 4),
                    'times_attempted': random.randint(1, 5),
                    'last_solved': now - timedelta(days=random.randint(1, 10)),
                    'last_attempted': now - timedelta(days=random.randint(0, 5)),
                    'notes': 'Key insight: Use two pointers or hash map. Optimal O(N) approach.',
                    'code_solution': f'# Solution for {problem.title}\ndef solve():\n    pass\n',
                    'reviews_count': box
                }
            )
            ReviewHistory.objects.get_or_create(
                progress=progress,
                old_box=max(1, box - 1),
                new_box=box,
                action='SOLVED',
                defaults={'notes': f'Promoted to Box {box}'}
            )

        # Some Needs Revisit (due today)
        for problem in problems[35:42]:
            UserProblemProgress.objects.update_or_create(
                user=demo_user,
                problem=problem,
                defaults={
                    'status': 'NEEDS_REVISIT',
                    'current_box': 1,
                    'next_review_date': now - timedelta(hours=2),
                    'times_solved': 0,
                    'times_attempted': 2,
                    'last_attempted': now - timedelta(days=1),
                    'notes': 'Struggled with edge cases and off-by-one errors.',
                }
            )

        # 4. Generate daily stats over the last 60 days
        curr = now.date() - timedelta(days=60)
        today = now.date()
        while curr <= today:
            if random.random() > 0.35 or (today - curr).days <= 7:
                solved = random.randint(1, 5)
                attempted = solved + random.randint(0, 2)
                DailyStat.objects.update_or_create(
                    user=demo_user,
                    date=curr,
                    defaults={
                        'problems_solved': solved,
                        'problems_attempted': attempted,
                        'total_time_minutes': solved * 25,
                        'by_topic': {'Array': random.randint(1, 3), 'Dynamic Programming': 1}
                    }
                )
            curr += timedelta(days=1)

        # Set streak
        UserStreak.objects.update_or_create(
            user=demo_user,
            defaults={
                'current_streak': 7,
                'longest_streak': 18,
                'last_solved_date': today
            }
        )

        # 5. Generate active study plan for demo_user
        target_date = today + timedelta(days=30)
        generate_study_plan(demo_user, target_date, problems_per_day=4)

        invalidate_user_analytics_cache(demo_user.id)
        invalidate_user_analytics_cache(test_user.id)

        self.stdout.write(self.style.SUCCESS(
            'Successfully seeded database! Demo users created: demo_user, test_user'
        ))

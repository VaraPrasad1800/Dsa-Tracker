import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from tracker.models import Problem, UserProblemProgress, StudyPlan, StudyPlanDay, Tag
from tracker.services.analytics import get_user_topic_breakdown, get_user_streaks, get_user_dashboard
from tracker.services.leitner import get_leitner_box_stats

def generate_study_plan(user, target_date, problems_per_day=5):
    today = timezone.now().date()
    days_remaining = (target_date - today).days
    if days_remaining <= 0:
        days_remaining = 1

    # Deactivate existing active plans
    StudyPlan.objects.filter(user=user, is_active=True).update(is_active=False)

    plan = StudyPlan.objects.create(
        user=user,
        target_date=target_date,
        problems_per_day=problems_per_day,
        is_active=True
    )

    # 1. Topic breakdown & weak topics
    topic_data = get_user_topic_breakdown(user)
    weak_topics = [t['name'] for t in topic_data['topics'] if t['is_weak']]

    # 1b. Weak companies (from placement-readiness dashboard) for company drilling
    dashboard = get_user_dashboard(user)
    weak_companies = [c for c in dashboard.get('weak_companies', []) if c.get('percentage', 100) < 50.0]
    weak_company_slugs = [c['slug'] for c in weak_companies]

    # 2. Box statistics & streaks
    box_stats = get_leitner_box_stats(user)
    streak_data = get_user_streaks(user)
    current_streak = streak_data['current_streak']

    # 3. Problem pools
    # Revisit pool: Box 1-2 or NEEDS_REVISIT
    revisit_problem_ids = list(UserProblemProgress.objects.filter(
        user=user
    ).filter(
        Q(current_box__in=[1, 2]) | Q(status='NEEDS_REVISIT')
    ).values_list('problem_id', flat=True))

    solved_problem_ids = set(UserProblemProgress.objects.filter(
        user=user, status='SOLVED'
    ).values_list('problem_id', flat=True))

    # All available problems
    all_problems = list(Problem.objects.all())
    if not all_problems:
        return plan

    # Available unsolved/revisit problems
    unsolved_problems = [p for p in all_problems if p.id not in solved_problem_ids]
    if not unsolved_problems:
        unsolved_problems = all_problems  # Fallback if user solved everything

    # Day-by-day generation
    for day_offset in range(days_remaining):
        day_date = today + timedelta(days=day_offset)
        selected_problems = []
        day_reason = 'Balanced practice'
        day_focus_topic = None
        day_difficulty = 'Medium'

        # Rule heuristics:
        # Rule A: If current_streak == 0 and first 2 days -> schedule Easy to build momentum
        if current_streak == 0 and day_offset < 2:
            day_reason = 'Build momentum with foundational problems'
            day_difficulty = 'Easy'
            easy_pool = [p for p in unsolved_problems if p.difficulty == 'Easy']
            sample_size = min(problems_per_day, len(easy_pool))
            selected_problems.extend(random.sample(easy_pool, sample_size) if sample_size > 0 else [])

        # Rule B: Final week crunch (days_remaining < 7) -> Hard push
        elif days_remaining < 7 or (days_remaining >= 7 and day_offset >= days_remaining - 7):
            day_reason = 'Final push: Interview-level Hard & Medium problems'
            day_difficulty = 'Hard'
            hard_pool = [p for p in unsolved_problems if p.difficulty in ['Medium', 'Hard']]
            sample_size = min(problems_per_day, len(hard_pool))
            selected_problems.extend(random.sample(hard_pool, sample_size) if sample_size > 0 else [])

        # Rule C: Box 1 count > 20 and day is weekly review day
        elif box_stats['box_1_count'] > 20 and (day_offset % 4 == 0) and revisit_problem_ids:
            day_reason = 'Spaced Repetition: Clear Box 1 revisit backlog'
            day_difficulty = 'Medium'
            revisit_pool = [p for p in all_problems if p.id in revisit_problem_ids]
            sample_size = min(problems_per_day, len(revisit_pool))
            selected_problems.extend(random.sample(revisit_pool, sample_size) if sample_size > 0 else [])

        # Rule E: Weak company drilling (every 3rd day, alternate with weak topics)
        elif weak_company_slugs and (day_offset % 3 == 0):
            focus_idx = (day_offset // 3) % len(weak_company_slugs)
            focus_company_slug = weak_company_slugs[focus_idx]
            day_reason = f'Drill on weak company: {focus_company_slug}'
            company_pool = [p for p in unsolved_problems if p.companies.filter(slug=focus_company_slug).exists()]
            sample_size = min(problems_per_day, len(company_pool))
            selected_problems.extend(random.sample(company_pool, sample_size) if sample_size > 0 else [])

        # Rule D: Weak topics prioritization (40% target)
        elif weak_topics:
            focus_idx = day_offset % len(weak_topics)
            day_focus_topic = weak_topics[focus_idx]
            day_reason = f'Master weak topic: {day_focus_topic}'
            topic_pool = [p for p in unsolved_problems if p.tags.filter(name=day_focus_topic).exists()]
            sample_size = min(problems_per_day, len(topic_pool))
            selected_problems.extend(random.sample(topic_pool, sample_size) if sample_size > 0 else [])

        # Fill remaining slots with balanced mix
        if len(selected_problems) < problems_per_day:
            needed = problems_per_day - len(selected_problems)
            available = [p for p in unsolved_problems if p not in selected_problems]
            if len(available) < needed:
                available = [p for p in all_problems if p not in selected_problems]
            if available:
                selected_problems.extend(random.sample(available, min(needed, len(available))))

        day_obj = StudyPlanDay.objects.create(
            plan=plan,
            date=day_date,
            focus_topic=day_focus_topic,
            difficulty_target=day_difficulty,
            reason=day_reason
        )
        if selected_problems:
            day_obj.problems.set(selected_problems)

    return plan

def get_study_plan_progress(plan, user):
    today = timezone.now().date()
    days = plan.days.all()
    today_day = days.filter(date=today).first()
    
    today_solved = 0
    today_total = 0
    if today_day:
        today_total = today_day.problems.count()
        today_solved = UserProblemProgress.objects.filter(
            user=user,
            problem__in=today_day.problems.all(),
            status='SOLVED'
        ).count()

    total_plan_problems = sum(d.problems.count() for d in days)
    total_solved = UserProblemProgress.objects.filter(
        user=user,
        problem__in=Problem.objects.filter(plan_days__plan=plan).distinct(),
        status='SOLVED'
    ).count()

    # Calculate on-pace indicator: problems solved vs problems expected from past days
    past_days = [d for d in days if d.date < today]
    expected_solved = sum(d.problems.count() for d in past_days)
    on_pace = total_solved >= expected_solved

    # Readiness score heuristic based on % of weak topics covered and problem completion
    topic_data = get_user_topic_breakdown(user)
    weak_count = sum(1 for t in topic_data['topics'] if t['is_weak'])
    total_topics = len(topic_data['topics']) or 1
    mastered_ratio = (total_topics - weak_count) / total_topics
    completion_ratio = (total_solved / total_plan_problems) if total_plan_problems > 0 else 0
    estimated_readiness = round((0.6 * mastered_ratio + 0.4 * completion_ratio) * 100, 1)

    return {
        'plan_id': plan.id,
        'completed_today': f'{today_solved}/{today_total}',
        'completed_today_count': today_solved,
        'total_today_count': today_total,
        'total_completed': total_solved,
        'total_problems': total_plan_problems,
        'on_pace': on_pace,
        'estimated_readiness': min(estimated_readiness, 100.0),
    }

from datetime import timedelta
from django.utils import timezone
from tracker.models import UserProblemProgress, ReviewHistory
from tracker.services.analytics import record_daily_stat, invalidate_user_analytics_cache

BOX_INTERVALS = {
    1: timedelta(days=1),
    2: timedelta(days=3),
    3: timedelta(days=7),
    4: timedelta(days=14),
    5: timedelta(days=30),
}

def update_problem_progress(user, problem, status, notes=None, code_solution=None, code_language=None, time_spent_minutes=0):
    progress, created = UserProblemProgress.objects.get_or_create(
        user=user,
        problem=problem,
        defaults={'status': 'UNSOLVED', 'current_box': 1}
    )

    old_box = progress.current_box
    old_status = progress.status
    now = timezone.now()

    progress.times_attempted += 1
    progress.last_attempted = now

    if notes is not None:
        progress.notes = notes
    if code_solution is not None:
        progress.code_solution = code_solution
    if code_language is not None:
        progress.code_language = code_language
    if time_spent_minutes:
        progress.total_time_spent_minutes += time_spent_minutes

    is_solved = False

    if status == 'SOLVED':
        is_solved = True
        progress.status = 'SOLVED'
        progress.times_solved += 1
        progress.reviews_count += 1
        progress.last_solved = now

        if progress.current_box < 5:
            progress.current_box += 1
        else:
            progress.current_box = 5  # Edge case: Box 5 stays at 30 days and doesn't overflow

        progress.next_review_date = now + BOX_INTERVALS[progress.current_box]

        ReviewHistory.objects.create(
            progress=progress,
            old_box=old_box,
            new_box=progress.current_box,
            action='SOLVED',
            notes=f'Promoted to Box {progress.current_box}' if progress.current_box > old_box else 'Maintained Box 5'
        )

    elif status == 'NEEDS_REVISIT':
        progress.status = 'NEEDS_REVISIT'
        progress.reviews_count += 1
        progress.current_box = 1
        progress.next_review_date = now + BOX_INTERVALS[1]

        ReviewHistory.objects.create(
            progress=progress,
            old_box=old_box,
            new_box=1,
            action='NEEDS_REVISIT',
            notes='Reset to Box 1 for next-day review'
        )

    elif status == 'SKIPPED':
        progress.status = 'SKIPPED'
        ReviewHistory.objects.create(
            progress=progress,
            old_box=old_box,
            new_box=progress.current_box,
            action='SKIPPED',
            notes='Skipped review'
        )

    elif status == 'UNSOLVED':
        progress.status = 'UNSOLVED'

    progress.save()

    # Record daily stat and streak
    record_daily_stat(user=user, is_solved=is_solved, problem=problem, time_minutes=time_spent_minutes)
    invalidate_user_analytics_cache(user.id)

    return progress

def get_leitner_box_stats(user):
    boxes = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    progresses = UserProblemProgress.objects.filter(user=user)
    for p in progresses:
        if 1 <= p.current_box <= 5:
            boxes[p.current_box] += 1

    due_today_count = UserProblemProgress.objects.filter(
        user=user,
        next_review_date__lte=timezone.now()
    ).count()

    return {
        'box_1_count': boxes[1],
        'box_2_count': boxes[2],
        'box_3_count': boxes[3],
        'box_4_count': boxes[4],
        'box_5_count': boxes[5],
        'due_today_count': due_today_count,
    }
